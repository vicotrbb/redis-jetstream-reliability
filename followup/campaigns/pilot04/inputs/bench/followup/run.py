"""Isolated homelab-only follow-up collection with an exclusive input snapshot."""
import argparse
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parents[2]
K = ["kubectl", "--context", "homelab"]
VERSIONS = {"redis": {"old": "7.4.2", "current": "8.10.2"},
            "nats": {"old": "2.10.24", "current": "2.15.0"}}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write(path, data):
    with Path(path).open("x") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def execute(args, **kwargs):
    return subprocess.run(K + args, check=True, **kwargs)


def make_plan(campaign, seed, pilot):
    rng = random.Random(seed)
    cells = []
    def add(kind, engine, version, profile, **kwargs):
        cells.append(dict(campaign=campaign, kind=kind, engine=engine,
                          version=VERSIONS[engine][version], host=f"{engine}-{version}",
                          profile=profile, publishers=16, consumers=0, cpus=2,
                          seconds=15, count=65536, payload="compressible",
                          compression="inherited", trace=False, recovery="",
                          delta_ms=250, age=.1, kill=True, seed=seed, pilot=pilot,
                          **kwargs))
    # Randomization is fixed before any measured result is observed.
    for block in range(3 if not pilot else 1):
        group = []
        for engine in VERSIONS:
            for version in ("old", "current"):
                for profile in ("memory", "periodic", "always"):
                    for pubs in (1, 16):
                        add("publication", engine, version, profile, block=block)
                        cells[-1]["publishers"] = pubs
                        group.append(cells.pop())
        rng.shuffle(group)
        cells.extend(group)
    if not pilot:
        for block in range(2):
            group = []
            for engine in VERSIONS:
                for profile in ("memory", "periodic"):
                    for consumers in (1, 16):
                        for cpus in (2, 4):
                            add("drain", engine, "current", profile, block=block)
                            cells[-1].update(consumers=consumers, cpus=cpus)
                            group.append(cells.pop())
            rng.shuffle(group)
            cells.extend(group)
        for block in range(2):
            group = []
            for engine, version, policy in (("redis", "old", "autoclaim"),
                    ("redis", "current", "autoclaim"), ("redis", "current", "claim"),
                    ("nats", "old", "jetstream"), ("nats", "current", "jetstream")):
                for delta in (250, 1000):
                    for age in (.1, .75):
                        for kill in (False, True):
                            add("recovery", engine, version, "periodic", block=block)
                            cells[-1].update(delta_ms=delta, age=age, kill=kill, recovery=policy)
                            group.append(cells.pop())
            rng.shuffle(group)
            cells.extend(group)
        for version in ("old", "current"):
            for block in range(2):
                add("recovery", "redis", version, "periodic", block=block)
                cells[-1].update(recovery="none")
        diagnostic = []
        for engine in VERSIONS:
            for pubs in (1, 16):
                for traced in (False, True):
                    add("trace", engine, "current", "always", block=0)
                    cells[-1].update(publishers=pubs, trace=traced)
                    diagnostic.append(cells.pop())
            for payload in ("compressible", "random"):
                for compression in ("inherited", "off"):
                    add("compression", engine, "current", "always", block=0)
                    cells[-1].update(payload=payload, compression=compression)
                    diagnostic.append(cells.pop())
        rng.shuffle(diagnostic)
        cells.extend(diagnostic)
    else:
        for engine in VERSIONS:
            add("drain", engine, "current", "memory", block=0)
            cells[-1].update(consumers=16, count=1024, cpus=4)
            add("trace", engine, "current", "always", block=0)
            cells[-1].update(trace=True)
            add("compression", engine, "current", "always", block=0)
            cells[-1].update(compression="off", payload="random")
        for engine, version, policy, kill in (("redis", "current", "claim", True),
                ("redis", "current", "autoclaim", False), ("redis", "old", "none", True),
                ("nats", "current", "jetstream", False), ("nats", "old", "jetstream", True)):
            add("recovery", engine, version, "periodic", block=0)
            cells[-1].update(recovery=policy, kill=kill)
    for i, cell in enumerate(cells, 1):
        cell["id"] = f"F{i:04d}"
        cell["seed"] += i
        if pilot:
            cell["seconds"] = 1
    return cells


def resources(namespace, pins):
    for tag in [f"{e}:{v}-alpine" for e, versions in VERSIONS.items() for v in versions.values()] + ["golang:1.24.4-bookworm","alpine:3.22"]:
        assert "@sha256:" in pins[tag], ("missing immutable image pin",tag)
    items = [{"apiVersion": "v1", "kind": "Namespace", "metadata": {
        "name": namespace, "labels": {"purpose": "message-reliability-followup", "study-owner": namespace}}}]
    def pod(name, image, cpu, broker=False, engine=""):
        spec = {"nodeSelector": {"kubernetes.io/hostname": "homelab-01" if broker else "homelab-02"},
                "automountServiceAccountToken": False,
                "tolerations": [{"key": "node-role.kubernetes.io/control-plane", "operator": "Exists", "effect": "NoSchedule"}],
                "terminationGracePeriodSeconds": 15,
                "containers": [{"name": "work", "image": image, "command": ["sh", "-c",
                    f"while [ ! -x /tools/followup ]; do sleep 1; done; exec /tools/followup control {engine}" if broker else "sleep 86400"],
                    "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": str(cpu), "memory": "4Gi" if broker else "2Gi"}},
                    "volumeMounts": [{"name": "tools", "mountPath": "/tools"}, {"name": "data", "mountPath": "/data"}, {"name": "work", "mountPath": "/work"}]}],
                "volumes": [{"name": "tools", "emptyDir": {}}, {"name": "data", "emptyDir": {"sizeLimit": "4Gi"}}, {"name": "work", "emptyDir": {"sizeLimit": "8Gi"}}]}
        if broker and name.endswith("current"):
            spec["containers"][0]["securityContext"] = {"capabilities": {"add": ["SYS_PTRACE"]}, "seccompProfile": {"type": "Unconfined"}}
            spec["initContainers"] = [{"name": "trace-tools", "image": pins["alpine:3.22"], "command": ["sh", "-c", "for attempt in 1 2 3 4 5; do apk add --no-cache strace && break; sleep 2; done; test -x /usr/bin/strace && mkdir -p /tools/lib && cp -L /usr/lib/lib*.so* /tools/lib/ && cp -L /lib/lib*.so* /tools/lib/ && cp /usr/bin/strace /tools/strace && strace -V > /tools/strace-version.txt && sha256sum /tools/strace >> /tools/strace-version.txt"], "volumeMounts": [{"name": "tools", "mountPath": "/tools"}]}]
        items.append({"apiVersion": "v1", "kind": "Pod", "metadata": {"name": name, "namespace": namespace, "labels": {"app": name}}, "spec": spec})
        if broker:
            items.append({"apiVersion": "v1", "kind": "Service", "metadata": {"name": name, "namespace": namespace}, "spec": {"selector": {"app": name}, "ports": [{"name": "control", "port": 8088}, {"name": "broker", "port": 6379 if engine == "redis" else 4222}]}})
    for engine, versions in VERSIONS.items():
        for label, version in versions.items():
            image = f"{engine}:{version}-alpine"
            pod(f"{engine}-{label}", pins.get(image, image), 2, True, engine)
    image = pins.get("golang:1.24.4-bookworm", "golang:1.24.4-bookworm")
    for cpu in (2, 4):
        pod(f"runner-{cpu}", image, cpu)
    items.append({"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy", "metadata": {"name": "namespace-only", "namespace": namespace}, "spec": {"podSelector": {}, "policyTypes": ["Ingress"], "ingress": [{"from": [{"podSelector": {}}]}]}})
    return {"apiVersion": "v1", "kind": "List", "items": items}


def snapshot(folder):
    inputs = folder / "inputs"
    inputs.mkdir()
    shutil.copytree(ROOT / "bench", inputs / "bench", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copyfile(ROOT / "docs/FOLLOWUP_PROTOCOL.md", inputs / "FOLLOWUP_PROTOCOL.md")
    hashes = {str(p.relative_to(inputs)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(inputs.rglob("*")) if p.is_file()}
    write(inputs / "SHA256.json", hashes)


def verify_snapshot(folder):
    inputs = folder / "inputs"
    for name, digest in json.loads((inputs / "SHA256.json").read_text()).items():
        assert hashlib.sha256((inputs / name).read_bytes()).hexdigest() == digest, name


def collect_trial(ns, runner, trial_id, folder):
    # tar paths are checked before extraction and cannot escape the trial folder.
    p = execute(["exec", "-n", ns, runner, "--", "tar", "-C", "/work/results", "-cf", "-", trial_id], capture_output=True)
    with tarfile.open(fileobj=io.BytesIO(p.stdout)) as archive:
        for member in archive:
            path = Path(member.name)
            assert not path.is_absolute() and ".." not in path.parts and path.parts[0] == trial_id
            target = folder / "raw" / path
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                assert member.isfile()
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as out:
                    shutil.copyfileobj(archive.extractfile(member), out)
    result = json.loads((folder / "raw" / trial_id / "result.json").read_text())
    if result.get("trace"):
        trace = result["trace"]
        assert hashlib.sha256((folder / "raw" / trial_id / trace["path"]).read_bytes()).hexdigest() == trace["sha256"]
    return result


def bootstrap(folder, ns):
    pins = json.loads((folder / "inputs/bench/followup/image-pins.json").read_text())
    manifest = resources(ns, pins)
    write(folder / "resources.json", manifest)
    execute(["create", "-f", "-"], input=json.dumps(manifest), text=True)
    execute(["wait", "-n", ns, "--for=condition=Ready", "pod", "--all", "--timeout=240s"])
    execute(["cp", str(folder / "inputs/bench"), f"{ns}/runner-2:/work/bench"])
    command = "cd /work/bench && sh prepare_modules.sh && gofmt -w followup/*.go && go test -race -count=1 ./followup && CGO_ENABLED=0 go build -trimpath -o /tools/followup ./followup && sha256sum /tools/followup && go version"
    with (folder / "build.log").open("x") as log:
        execute(["exec", "-n", ns, "runner-2", "--", "sh", "-c", command], stdout=log, stderr=subprocess.STDOUT)
    execute(["cp", f"{ns}/runner-2:/tools/followup", str(folder / "followup-linux-amd64")])
    # Keep a receipt, not another large executable in the public data package.
    binary = folder / "followup-linux-amd64"
    binary.chmod(0o755)
    write(folder / "binary.json", {"sha256": hashlib.sha256(binary.read_bytes()).hexdigest(), "execution_context": "homelab", "built_utc": now()})
    for pod in ("runner-4", "redis-old", "redis-current", "nats-old", "nats-current"):
        execute(["cp", str(binary), f"{ns}/{pod}:/tools/followup"])
        execute(["exec", "-n", ns, pod, "--", "chmod", "755", "/tools/followup"])
    binary.unlink()
    time.sleep(2)
    pods = json.loads(execute(["get", "pods", "-n", ns, "-o", "json"], capture_output=True, text=True).stdout)
    write(folder / "pods.json", pods)
    write(folder / "nodes.json", json.loads(execute(["get", "nodes", "-o", "json"], capture_output=True, text=True).stdout))
    for pod in ("redis-old", "redis-current", "nats-old", "nats-current"):
        binary_name = "redis-server" if pod.startswith("redis") else "nats-server"
        version = execute(["exec", "-n", ns, pod, "--", binary_name, "--version"], capture_output=True, text=True)
        write(folder / f"{pod}-version.json", {"stdout":version.stdout,"stderr":version.stderr,"checked_utc":now()})
        p = execute(["exec", "-n", ns, pod, "--", "sh", "-c", "if [ -f /tools/strace-version.txt ]; then cat /tools/strace-version.txt; fi; cat /proc/version; df -T /data; cat /proc/self/mountinfo"], capture_output=True, text=True)
        (folder / f"{pod}-environment.txt").write_text(p.stdout)


def run(folder, ns):
    verify_snapshot(folder)
    identity = json.loads((folder / "identity.json").read_text())
    if not identity["pilot"]:
        assert hashlib.sha256((folder / "plan.json").read_bytes()).hexdigest() == identity["plan_sha256"]
        assert Path(__file__).read_bytes() == (folder / "inputs/bench/followup/run.py").read_bytes(), "Executed runner differs from sealed protocol input"
    readiness = """import json,time,urllib.request
for name in ('redis-old','redis-current','nats-old','nats-current'):
    deadline=time.monotonic()+45
    while True:
        try:
            result=json.load(urllib.request.urlopen('http://'+name+':8088/health',timeout=2))
            assert not result['active'],(name,result)
            print(json.dumps({'controller':name,'health':result}),flush=True)
            break
        except Exception:
            if time.monotonic()>deadline: raise
            time.sleep(.25)
"""
    health = execute(["exec", "-n", ns, "runner-2", "--", "python3", "-c", readiness], capture_output=True, text=True)
    write(folder / ("readiness-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json"), {"checked_utc":now(),"stdout":health.stdout})
    plan = json.loads((folder / "plan.json").read_text())
    completed = {p.parent.name for p in (folder / "raw").glob("*/result.json")}
    with (folder / "progress.jsonl").open("a") as progress:
        for trial in plan:
            if trial["id"] in completed:
                continue
            runner = f"runner-{trial['cpus']}"
            (folder / "invocations").mkdir(exist_ok=True)
            invocation_path = folder / "invocations" / (trial["id"] + ".json")
            assert not invocation_path.exists(), "An incomplete prior invocation exists; no automatic replay"
            assert not (folder / (trial['id']+'-infrastructure-error.json')).exists(), "A prior infrastructure failure exists; no automatic replay"
            start = now()
            try:
                p = subprocess.run(K + ["exec", "-i", "-n", ns, runner, "--", "env", f"GOMAXPROCS={trial['cpus']}", "/tools/followup", "trial", "-", f"/work/results/{trial['id']}"], input=json.dumps(trial), text=True, capture_output=True, timeout=600)
            except subprocess.TimeoutExpired as error:
                def decoded(value):
                    return value.decode(errors="replace") if isinstance(value,bytes) else value
                write(folder / f"{trial['id']}-infrastructure-error.json", {"trial": trial, "started": start, "finished": now(), "error": "controller timeout after 600 seconds", "stdout": decoded(error.stdout), "stderr": decoded(error.stderr)})
                try:
                    collect_trial(ns,runner,trial['id'],folder)
                except Exception as salvage_error:
                    write(folder / f"{trial['id']}-salvage-error.json", {"error":str(salvage_error),"recorded_utc":now()})
                raise RuntimeError("Controller timeout retained; remote state requires inspection, no automatic retry") from error
            (folder / f"{trial['id']}-stderr.log").write_text(p.stderr)
            write(invocation_path,{"trial":trial,"started":start,"finished":now(),"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr})
            if p.returncode not in (0, 2):
                write(folder / f"{trial['id']}-infrastructure-error.json", {"trial": trial, "started": start, "finished": now(), "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr})
                raise RuntimeError("Infrastructure error retained; no automatic retry")
            try:
                result = collect_trial(ns, runner, trial["id"], folder)
            except Exception as error:
                write(folder / f"{trial['id']}-collection-error.json", {"error":str(error),"recorded_utc":now(),"invocation":str(invocation_path.relative_to(folder))})
                raise
            row = {"trial": trial, "started": start, "finished": now(), "status": result["status"], "error": result.get("error"), "throughput_mps": result.get("throughput_mps"), "confirmed": result.get("confirmed")}
            progress.write(json.dumps(row) + "\n")
            progress.flush()
            os.fsync(progress.fileno())
            print(json.dumps(row), flush=True)
            if result.get("stop_error") or result.get("broker_stop", {}).get("cleanup_error") not in (None, "<nil>"):
                raise RuntimeError("Broker reset did not succeed; campaign paused")
    hashes = {str(p.relative_to(folder)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((folder / "raw").rglob("*")) if p.is_file()}
    write(folder / "RAW_SHA256.json", hashes)
    write(folder / "completion.json", {"planned": len(plan), "collected": len(list((folder / "raw").glob("*/result.json"))), "completed_utc": now(), "context": "homelab"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "bootstrap", "run", "cleanup"))
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--seed", type=int, default=20260924)
    parser.add_argument("--pilot", action="store_true")
    args = parser.parse_args()
    assert args.campaign.isalnum() and args.campaign.islower()
    folder = ROOT / "followup/campaigns" / args.campaign
    ns = "msgrel-fup-" + args.campaign
    if args.action == "prepare":
        folder.mkdir(parents=True, exist_ok=False)
        snapshot(folder)
        write(folder / "plan.json", make_plan(args.campaign, args.seed, args.pilot))
        write(folder / "identity.json", {"campaign": args.campaign, "namespace": ns, "context": "homelab", "pilot": args.pilot, "created_utc": now(),"plan_sha256":hashlib.sha256((folder / "plan.json").read_bytes()).hexdigest()})
        print(folder)
    else:
        identity = json.loads((folder / "identity.json").read_text())
        assert identity["namespace"] == ns and identity["context"] == "homelab"
        if args.action == "bootstrap":
            bootstrap(folder, ns)
        else:
            actual = json.loads(execute(["get", "namespace", ns, "-o", "json"], capture_output=True, text=True).stdout)
            assert actual["metadata"]["labels"]["study-owner"] == ns
            if args.action == "run":
                run(folder, ns)
            else:
                execute(["delete", "namespace", ns, "--wait=true", "--timeout=120s"])
                write(folder / "cleanup.json", {"namespace": ns, "deleted_utc": now(), "context": "homelab"})


if __name__ == "__main__":
    main()
