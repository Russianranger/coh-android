from pathlib import Path
import yaml,ast,re,subprocess,hashlib,json
import argparse
parser=argparse.ArgumentParser(description='Verify frozen initial progress workflow source and recipe only')
parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();r=args.source_root.resolve();output=args.output.resolve()
if output.exists() or r in output.parents:raise ValueError('fresh external output required')
p=r/'.github/workflows/native-initial-progress-observation.yml';w=yaml.safe_load(p.read_text());s=w['jobs']['matching-original-initial-progress']['steps'];o=yaml.safe_load((r/'.github/workflows/native-scene-stage2-operation.yml').read_text())['jobs']['matching-original-stage2-diagnostic']['steps']
blocks=0
for i,step in enumerate(s):
 if 'run' not in step:continue
 text=step['run'];sh=subprocess.run(['bash','-n'],input=text.encode(),capture_output=True);assert not sh.returncode,(i,sh.stderr)
 for m in re.finditer(r"python3 - <<'([^']+)'\n(.*?)\n\1(?:\n|$)",text,re.S):compile(m[2],f'workflow-step-{i}','exec');blocks+=1
for old_i,new_i in ((3,3),(4,4),(5,5),(6,6),(7,7),(8,8),(11,11)):assert o[old_i]['run']==s[new_i]['run'],(old_i,new_i)
raw=s[2]['run'];body=re.search(r"python3 - <<'PYCURRENTPROGRESS'\n(.*?)\nPYCURRENTPROGRESS",raw,re.S)[1];tree=ast.parse(body);pins=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='pins'for t in n.targets))
for name,digest in pins.items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==digest,name
proof=json.loads((r/'native-android/engine/scenecatalog-server/evidence/progress-role-admission-20261018/qualification.json').read_bytes())
assert all(pins.get(name)==digest for name,digest in proof['source_sha256'].items())
build=json.loads((r/'native-android/engine/initial-capture/qualification/post-queue-progress-20261018/qualification.json').read_bytes())
assert all(pins.get(name)==digest for name,digest in build['source_sha256'].items())
assert s[12]['working-directory']=='current' and '--native-capture "$RUNNER_TEMP/groups-inputs/initial-progress/coh-capture-initial-progress"' in s[12]['run']
assert 'export GITHUB_SHA=' not in s[12]['run'] and s[12]['run'].count('capture_groups_transaction.py')==1
for i in (2,9,10,12,13,14):assert s[i].get('working-directory')=='current'
for step in s:
 text=step.get('run','');assert 'admit_initial_inventory_receiver.py --' not in text
 assert not re.search(r'^python3 .*check_local_initial',text,re.M)
assert len(s[15]['with']['path'].splitlines())==4 and all(x.startswith('current/out/groups-public/') for x in s[15]['with']['path'].splitlines())
for i,delimiter in ((2,'PYCURRENTPROGRESS'),(10,'PYNEWNATIVE')):
 code=re.search("python3 - <<'"+delimiter+"'\\n(.*?)\\n"+delimiter,s[i]['run'],re.S)[1]
 child=subprocess.run(['python','-O','-c',code],cwd=r,capture_output=True)
 assert child.returncode!=0 and b'OPTIMIZED_' in child.stderr and not child.stdout
result={'schema':'coh-initial-progress-workflow-static-review-v1','passed':True,'yaml_steps':len(s),'shell_scripts':sum('run'in x for x in s),'python_heredocs_compiled':blocks,'optimized_gate_refusals':2,'current_declared_nonself_pins':len(pins),'current_declared_raw_sha256':pins,'historical_runtime_steps_byte_identical':7,'one_current_original_transaction':True,'old_receiver_admission_removed':True,'native_rebuild_or_job_launch':False,'actual_new_Git_source_admission_pending_primary_commit':True,'workflow_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in result.items()if k!='current_declared_raw_sha256'}))
