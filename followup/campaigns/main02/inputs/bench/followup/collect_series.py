"""Run the three already sealed homelab campaigns sequentially; stop on any error."""
from pathlib import Path
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
for campaign in ('main01','main02','main03'):
    folder=ROOT/'followup/campaigns'/campaign
    for action in ('bootstrap','run','cleanup'):
        path=folder/(action+'.log')
        with path.open('x') as log:
            subprocess.run([sys.executable,str(ROOT/'bench/followup/run.py'),action,'--campaign',campaign],
                           cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        print(json.dumps({'campaign':campaign,'stage':action,'status':'complete'}),flush=True)
