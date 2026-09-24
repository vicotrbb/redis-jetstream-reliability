"""New campaigns use fresh namespaces and sealed collections, never the paper's data/."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys

from campaign_identity import ROOT, check_record, identity, seal, write_new

K = ["kubectl", "--context", "homelab"]


def run(*args, **kwargs):
    return subprocess.run(K + list(args), check=True, **kwargs)


def location(campaign_id, attempt_id):
    return ROOT / "campaigns" / campaign_id / "attempts" / attempt_id


def load_attempt(campaign_id, attempt_id):
    expected = identity(campaign_id, attempt_id)
    folder = location(campaign_id, attempt_id)
    record = json.loads((folder / "identity.json").read_text())
    check_record(record, expected)
    if record["namespace"] != expected["namespace"] or record["context"] != "homelab":
        raise ValueError("Invalid namespace or context in attempt identity")
    return folder, record


def owned_namespace(record):
    p = run("get", "namespace", record["namespace"], "-o", "json", capture_output=True, text=True)
    namespace = json.loads(p.stdout)
    if namespace["metadata"].get("labels", {}).get("evidence-owner") != record["owner_token"]:
        raise ValueError("Namespace ownership does not match this attempt")


def collect(folder, record):
    owned_namespace(record)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = folder / "collections" / stamp
    destination.mkdir(parents=True, exist_ok=False)
    raw = destination / "data/raw"
    raw.mkdir(parents=True)
    environment = destination / "environment"
    environment.mkdir()
    write_new(destination / "identity.json", record)
    ns = record["namespace"]
    receipts = []
    command = K + ["cp", f"{ns}/runner:/work/results/.", str(raw)]
    result = subprocess.run(command, capture_output=True, text=True)
    receipts.append({"command": command, "returncode": result.returncode,
                     "stdout": result.stdout, "stderr": result.stderr})
    for label, args in [
        ("pods", ["get", "pods", "-n", ns, "-o", "json"]),
        ("nodes", ["get", "nodes", "-o", "json"]),
        ("driver", ["exec", "-n", ns, "runner", "--", "sh", "-c",
                    "go version; uname -a; sha256sum /work/bench/*.go /work/bench/go.mod /work/bench/go.sum"]),
    ]:
        p = subprocess.run(K + args, capture_output=True, text=True)
        write_new(environment / f"{label}.json", {**record, "returncode": p.returncode,
                  "stdout": p.stdout, "stderr": p.stderr})
    for name in [f"{e}-{m}" for e in ("redis", "nats") for m in ("memory", "periodic", "always")]:
        args = (["redis-cli", "INFO", "persistence"] if name.startswith("redis")
                else ["cat", "/config/server.conf"])
        p = subprocess.run(K + ["exec", "-n", ns, name, "--"] + args,
                           capture_output=True, text=True)
        write_new(environment / f"{name}.json", {**record, "returncode": p.returncode,
                  "stdout": p.stdout, "stderr": p.stderr})
    for name in ("run.log", "run-result.json"):
        if (folder / name).is_file():
            shutil.copyfile(folder / name, destination / name)
    write_new(destination / "collection-receipts.json", {**record, "operations": receipts})
    sealed = seal(destination, record)
    print(json.dumps({"collection": str(destination), "sealed_files": len(sealed["files"])}))
    if result.returncode:
        raise RuntimeError("Collection has a recorded copy error; it is not a complete dataset")
    return destination


def prepare(campaign_id, attempt_id, mode):
    record = {**identity(campaign_id, attempt_id), "mode": mode,
              "owner_token": secrets.token_hex(12),
              "created_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
    folder = location(campaign_id, attempt_id)
    folder.mkdir(parents=True, exist_ok=False)
    write_new(folder / "identity.json", record)
    inputs = folder / "inputs"
    inputs.mkdir()
    for name in ("bench", "formal", "k8s"):
        shutil.copytree(ROOT / name, inputs / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.olean"))
    subprocess.run([sys.executable, str(inputs / "k8s/generate.py"),
                    "--namespace", record["namespace"], "--owner", record["owner_token"],
                    "--output", str(inputs / "experiment.json")], check=True)
    seal(inputs, record)
    return folder, record


def execute(folder, record):
    ns = record["namespace"]
    manifest = json.loads((folder / "inputs/experiment.json").read_text())
    namespace = next(x for x in manifest["items"] if x["kind"] == "Namespace")
    # create is intentionally exclusive; an existing namespace must never be reused.
    run("create", "-f", "-", input=json.dumps(namespace), text=True)
    resources = {**manifest, "items": [x for x in manifest["items"] if x["kind"] != "Namespace"]}
    run("create", "-f", "-", input=json.dumps(resources), text=True)
    run("wait", "-n", ns, "--for=condition=Ready", "pod", "--all", "--timeout=180s")
    run("cp", str(folder / "inputs/bench"), f"{ns}/runner:/work/bench")
    run("cp", str(folder / "inputs/formal"), f"{ns}/runner:/work/formal")
    env = ["env", f"MSGREL_CAMPAIGN_ID={record['campaign_id']}",
           f"MSGREL_ATTEMPT_ID={record['attempt_id']}", "GOMAXPROCS=2"]
    if record["mode"] == "validation":
        command = ("cd /work/bench && sh prepare_modules.sh && go test -race -count=1 -v ./... && "
                   "python3 -m unittest discover -s tests -v && "
                   "go build -o /work/bench-driver . && "
                   "/work/bench-driver validation /work/results/validation")
    else:
        command = "cd /work/bench && sh prepare_modules.sh && go build -o /work/bench-driver ."
        for series in ("pilot", "main", "durability", "serial", "recovery"):
            command += f" && /work/bench-driver {series} /work/results/{series}"
    with (folder / "run.log").open("x") as log:
        result = subprocess.run(K + ["exec", "-n", ns, "runner", "--"] + env +
                                ["sh", "-c", command], stdout=log, stderr=subprocess.STDOUT)
        log.flush()
        os.fsync(log.fileno())
    write_new(folder / "run-result.json", {**record, "exit_code": result.returncode,
              "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat()})
    collect(folder, record)
    if result.returncode:
        raise RuntimeError(f"Attempt failed ({result.returncode}); evidence retained, no automatic replay")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "validation", "collect", "cleanup"])
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    if args.action in ("run", "validation"):
        folder, record = prepare(args.campaign, args.attempt, args.action)
        execute(folder, record)
    else:
        folder, record = load_attempt(args.campaign, args.attempt)
        if args.action == "collect":
            collect(folder, record)
        else:
            owned_namespace(record)
            run("delete", "namespace", record["namespace"], "--wait=true", "--timeout=120s")


if __name__ == "__main__":
    main()
