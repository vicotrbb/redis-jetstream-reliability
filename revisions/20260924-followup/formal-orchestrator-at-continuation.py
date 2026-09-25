"""Compile the unchanged abstract model in a disposable homelab pod.

Run only after all three measurement campaigns have completed and been cleaned
up. This script executes no proof compiler or runtime test on the workstation.
"""
import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'revisions/20260924-followup'
NAMESPACE = 'msgrel-fup-proof20260924'
K = ['kubectl', '--context', 'homelab']


def now(): return dt.datetime.now(dt.timezone.utc).isoformat()


def store(name, value):
    path = OUT/name
    with path.open('x') as stream: json.dump(value, stream, indent=2); stream.write('\n')


def run(args, **kwargs):
    return subprocess.run(K+args, check=True, capture_output=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--continue-owned-pod', action='store_true',
                        help='Continue after a documented pre-compilation readiness failure')
    args = parser.parse_args()
    for campaign in ('main01', 'main02', 'main03'):
        folder = ROOT/'followup/campaigns'/campaign
        completion = json.loads((folder/'completion.json').read_text())
        assert completion['planned'] == completion['collected'] == 204
        assert json.loads((folder/'cleanup.json').read_text())['context'] == 'homelab'
    assert not (OUT/'lean-recheck.json').exists()
    assert not (OUT/'lean-invocation.json').exists() and not (OUT/'lean-recheck.log').exists()
    pins = json.loads((ROOT/'bench/followup/image-pins.json').read_text())
    image = pins['golang:1.24.4-bookworm']
    resources = {'apiVersion':'v1','kind':'List','items':[
        {'apiVersion':'v1','kind':'Namespace','metadata':{'name':NAMESPACE,'labels':{'study-owner':NAMESPACE}}},
        {'apiVersion':'v1','kind':'Pod','metadata':{'name':'proof','namespace':NAMESPACE},
         'spec':{'automountServiceAccountToken':False,'restartPolicy':'Never',
                 'nodeSelector':{'kubernetes.io/hostname':'homelab-02'},
                 'tolerations':[{'key':'node-role.kubernetes.io/control-plane','operator':'Exists','effect':'NoSchedule'}],
                 'containers':[{'name':'proof','image':image,'command':['sleep','infinity'],
                                'resources':{'requests':{'cpu':'1','memory':'1Gi'},'limits':{'cpu':'2','memory':'2Gi'}},
                                'volumeMounts':[{'name':'work','mountPath':'/work'}]}],
                 'volumes':[{'name':'work','emptyDir':{}}]}}]}
    if args.continue_owned_pod:
        started = json.loads((OUT/'lean-recheck-started.json').read_text())
        assert started['context'] == 'homelab' and started['namespace'] == NAMESPACE
        namespace = json.loads(run(['get','namespace',NAMESPACE,'-o','json']).stdout)
        assert namespace['metadata']['labels']['study-owner'] == NAMESPACE
        correction = json.loads((OUT/'lean-pod-scheduling-correction.json').read_text())
        observed = json.loads(run(['get','pod','proof','-n',NAMESPACE,'-o','json']).stdout)
        assert observed['metadata']['uid'] == correction['metadata']['uid']
        store('lean-continuation-started.json', {
            'context':'homelab','namespace':NAMESPACE,'started_utc':now(),
            'reason':'Initial readiness wait expired before the missing control-plane scheduling toleration was added to this owned pod. No compiler invocation had begun.',
            'pod_uid':observed['metadata']['uid'],
            'orchestrator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    else:
        assert not (OUT/'lean-recheck-started.json').exists()
        store('lean-recheck-started.json', {'context':'homelab','namespace':NAMESPACE,'started_utc':now()})
        store('lean-resources.json', resources)
        run(['create','-f','-'], input=json.dumps(resources).encode())
    run(['wait','--for=condition=Ready','pod/proof','-n',NAMESPACE,'--timeout=180s'])
    initial = json.loads(run(['get','pod','proof','-n',NAMESPACE,'-o','json']).stdout)
    store('lean-pod-initial.json', initial)
    assert initial['spec']['nodeName'] == 'homelab-02'
    assert initial['status']['containerStatuses'][0]['restartCount'] == 0
    assert initial['status']['containerStatuses'][0]['imageID'].split('@sha256:')[-1] == image.split('@sha256:')[-1]
    payload = io.BytesIO()
    with tarfile.open(fileobj=payload,mode='w') as archive:
        for name in ('DeliveryModel.lean','verify.sh'):
            archive.add(ROOT/'formal'/name,arcname='formal/'+name)
    run(['exec','-i','-n',NAMESPACE,'proof','--','tar','xf','-','-C','/work'],input=payload.getvalue())
    command = K+['exec','-n',NAMESPACE,'proof','--','sh','/work/formal/verify.sh']
    result = subprocess.run(command,capture_output=True,text=True,timeout=1200)
    with (OUT/'lean-recheck.log').open('x') as stream:stream.write(result.stdout+result.stderr)
    store('lean-invocation.json',{'command':command,'finished_utc':now(),'exit_code':result.returncode})
    if result.returncode: raise RuntimeError('Homelab proof compilation failed; namespace and log retained')
    text = result.stdout+result.stderr
    source = hashlib.sha256((ROOT/'formal/DeliveryModel.lean').read_bytes()).hexdigest()
    assert source in text and 'error:' not in text and 'warning:' not in text
    dependencies = {}
    for name, dependency in re.findall(r"'DeliveryModel\.([^']+)' depends on axioms: \[([^\]]*)\]", text):
        dependencies[name] = [v.strip() for v in dependency.split(',') if v.strip()]
    for name in re.findall(r"'DeliveryModel\.([^']+)' does not depend on any axioms",text): dependencies[name] = []
    original = json.loads((ROOT/'formal/verification.json').read_text())
    assert dependencies == original['logical_dependencies']
    assert original['compiler_binary_sha256'] in text and original['compiler_commit'] in text
    receipt = {k:original[k] for k in ('compiler_version','compiler_commit','compiler_binary_sha256','toolchain_archive_sha256','imports')}
    receipt.update(status='pass',exit_code=0,checked_at_utc=now(),execution_context='homelab',namespace=NAMESPACE,
                   pod='proof',execution_after_benchmark_collection=True,source='formal/DeliveryModel.lean',source_sha256=source,
                   container_image=image,command=command,logical_dependencies=dependencies,
                   log='revisions/20260924-followup/lean-recheck.log',
                   scope='Fresh homelab kernel compilation of selected abstract statements, not broker implementation verification.')
    store('lean-recheck.json', receipt)
    store('lean-pod-final.json',json.loads(run(['get','pod','proof','-n',NAMESPACE,'-o','json']).stdout))
    namespace = json.loads(run(['get','namespace',NAMESPACE,'-o','json']).stdout)
    assert namespace['metadata']['labels']['study-owner'] == NAMESPACE
    run(['delete','namespace',NAMESPACE,'--wait=true','--timeout=120s'])
    absent = subprocess.run(K+['get','namespace',NAMESPACE],capture_output=True,text=True)
    assert absent.returncode != 0 and 'NotFound' in absent.stderr
    store('lean-cleanup.json',{'context':'homelab','namespace':NAMESPACE,'deleted_utc':now(),
                               'absence_returncode':absent.returncode,'absence_stderr':absent.stderr})
    print(json.dumps({'status':'pass','declarations':len(dependencies),'namespace_deleted':True}))


if __name__ == '__main__': main()
