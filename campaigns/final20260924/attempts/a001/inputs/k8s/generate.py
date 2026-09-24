"""Generate only isolated homelab experiment resources; JSON is valid Kubernetes input."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--namespace", required=True)
parser.add_argument("--owner", required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
NS = args.namespace
pin_file=ROOT/"k8s/image-pins.json"
PINS=json.loads(pin_file.read_text()) if pin_file.exists() else {}
items = [{"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": NS, "labels": {"purpose": "message-reliability-paper", "evidence-owner": args.owner}}}]

def add(kind, name, **fields):
    item = {"apiVersion": "v1", "kind": kind, "metadata": {"name": name, "namespace": NS}, **fields}
    items.append(item)

for engine in ("redis", "nats"):
    for mode in ("memory", "periodic", "always"):
        name = f"{engine}-{mode}"
        if engine == "redis":
            image = "redis:7.4.2-alpine"
            config = 'bind 0.0.0.0\nprotected-mode no\nport 6379\nsave ""\ndir /data\nmaxmemory 768mb\nmaxmemory-policy noeviction\nauto-aof-rewrite-percentage 0\nno-appendfsync-on-rewrite no\n'
            config += "appendonly no\n" if mode == "memory" else f"appendonly yes\nappendfsync {'everysec' if mode == 'periodic' else 'always'}\n"
            command = ["redis-server", "/config/server.conf"]
            port = 6379
        else:
            image = "nats:2.10.24-alpine"
            interval = "always" if mode == "always" else "1s"
            config = f'port: 4222\nhttp_port: 8222\njetstream {{\n  store_dir: /data\n  max_memory_store: 512MB\n  max_file_store: 2GB\n  sync_interval: {interval}\n}}\n'
            command = ["nats-server", "-c", "/config/server.conf"]
            port = 4222
        add("ConfigMap", name, data={"server.conf": config})
        add("Pod", name, spec={
            "nodeSelector": {"kubernetes.io/hostname": "homelab-01"},
            "automountServiceAccountToken": False,
            "terminationGracePeriodSeconds": 5,
            "containers": [{"name": "server", "image": PINS.get(image,image), "command": command,
                "resources": {"requests": {"cpu": "100m", "memory": "128Mi"}, "limits": {"cpu": "2", "memory": "1Gi"}},
                "ports": [{"containerPort": port}],
                "readinessProbe": {"tcpSocket": {"port": port}, "initialDelaySeconds": 1, "periodSeconds": 2},
                "volumeMounts": [{"name": "config", "mountPath": "/config", "readOnly": True}, {"name": "data", "mountPath": "/data"}]}],
            "volumes": [{"name": "config", "configMap": {"name": name}}, {"name": "data", "emptyDir": {"sizeLimit": "4Gi"}}]
        })
        items[-1]["metadata"]["labels"] = {"app": name}
        add("Service", name, spec={"selector": {"app": name}, "ports": [{"port": port, "targetPort": port}]})

add("Pod", "runner", spec={
    "nodeSelector": {"kubernetes.io/hostname": "homelab-02"},
    "tolerations": [{"key": "node-role.kubernetes.io/control-plane", "operator": "Exists", "effect": "NoSchedule"}],
    "automountServiceAccountToken": False,
    "containers": [{"name": "runner", "image": PINS.get("golang:1.24.4-bookworm","golang:1.24.4-bookworm"), "command": ["sleep", "86400"],
        "resources": {"requests": {"cpu": "250m", "memory": "256Mi"}, "limits": {"cpu": "2", "memory": "2Gi"}},
        "volumeMounts": [{"name": "work", "mountPath": "/work"}]}],
    "volumes": [{"name": "work", "emptyDir": {"sizeLimit": "8Gi"}}]
})
items.append({"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy", "metadata": {"name": "namespace-only-ingress", "namespace": NS},
    "spec": {"podSelector": {}, "policyTypes": ["Ingress"], "ingress": [{"from": [{"podSelector": {}}]}]}})
with args.output.open("x") as output:
    output.write(json.dumps({"apiVersion": "v1", "kind": "List", "items": items}, indent=2) + "\n")
