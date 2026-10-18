from pathlib import Path
import yaml,json,hashlib,copy,pprint,ast
import argparse
parser=argparse.ArgumentParser(description='Reproduce frozen initial progress workflow into a fresh external file')
parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();ROOT=args.source_root.resolve();OUT=args.output.resolve()
if OUT.exists() or ROOT in OUT.parents:raise ValueError('fresh external output required')
OLD=ROOT/'.github/workflows/native-scene-stage2-operation.yml'
if hashlib.sha256(OLD.read_bytes()).hexdigest()!='d941c611b550f2f70a1dd6c2963348aee71bb359387c0acb4d5b90baab41f710':raise ValueError('frozen historical workflow source changed')
old=yaml.safe_load(OLD.read_text()); prior=old['jobs']['matching-original-stage2-diagnostic']; steps=prior['steps']
closure_name='native-android/engine/scenecatalog-server/evidence/progress-role-admission-20261018/current-source-closure.json'
closure=json.loads((ROOT/closure_name).read_bytes());pins=dict(closure['source_sha256'])
build_name='native-android/engine/initial-capture/qualification/post-queue-progress-20261018/qualification.json'
gzip_name='native-android/engine/initial-capture/qualification/post-queue-progress-20261018/coh-capture-initial-progress.gz'
proof_name='native-android/engine/scenecatalog-server/evidence/progress-role-admission-20261018/qualification.json'
for name in (closure_name,build_name,gzip_name,proof_name):pins[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
build=json.loads((ROOT/build_name).read_bytes());proof=json.loads((ROOT/proof_name).read_bytes())
for name,digest in proof['source_sha256'].items():
 assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
 pins[name]=digest
rawgate='''python3 - <<'PYCURRENTPROGRESS'
import hashlib,json,os,pathlib,subprocess
if not __debug__ or os.environ.get('PYTHONOPTIMIZE'):raise ValueError('OPTIMIZED_SOURCE_GATE_REFUSED')
assert os.environ['RUNNER_ENVIRONMENT']=='github-hosted' and os.environ['RUNNER_OS']=='Linux' and os.environ['RUNNER_ARCH']=='X64'
assert os.environ['GITHUB_REPOSITORY']=='Russianranger/coh-android' and os.environ['GITHUB_REF']=='refs/heads/native-android'
root=pathlib.Path.cwd().resolve();head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head==os.environ['GITHUB_SHA']
pins=PINS_LITERAL
workflow='.github/workflows/native-initial-progress-observation.yml'
pins[workflow]=hashlib.sha256((root/workflow).read_bytes()).hexdigest()
assert len(pins)==PIN_COUNT and len(pins)<=512
entries=subprocess.check_output(['git','ls-tree','-r','-z','HEAD','--',*sorted(pins)]);blobs={}
for row in entries.split(b'\\0'):
 if not row:continue
 meta,name=row.split(b'\\t',1);mode,kind,digest=meta.split()
 assert kind==b'blob' and mode in (b'100644',b'100755');blobs[name.decode()]=digest.decode()
assert set(blobs)==set(pins)
for name,digest in pins.items():
 path=root/name;relative=pathlib.PurePosixPath(name)
 assert not relative.is_absolute() and all(part not in ('','.','..') for part in relative.parts) and chr(92) not in name and ':' not in name
 assert path.resolve()==path and path.is_file() and not path.is_symlink() and 0<path.stat().st_size<8*1024**2
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==digest
 assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\\0'+raw).hexdigest()==blobs[name]
closure=json.loads((root/CLOSURE_LITERAL).read_bytes());proof=json.loads((root/PROOF_LITERAL).read_bytes());build=json.loads((root/BUILD_LITERAL).read_bytes())
assert closure['schema']=='coh-progress-prospective-current-source-closure-v1' and closure['passed'] is True
assert closure['current_orchestration_required'] is True and closure['historical9c29_or_old_receiver_equivalence_claimed'] is False
assert closure['native_inputs']==51 and closure['orchestration_inputs']==245 and len(closure['source_sha256'])==245
assert all(pins.get(name)==digest for name,digest in closure['source_sha256'].items())
assert proof['schema']=='coh-initial-progress-admission-focused-v1' and proof['passed'] is True and proof['checks']==14 and proof['refusals']==80
assert proof['native_build_receipt_sha256']==pins[BUILD_LITERAL]
assert all(pins.get(name)==digest for name,digest in proof['source_sha256'].items())
assert all(proof[key] is False for key in ('old_suites_or_native_qualifier_replayed','original_server_or_native_binary_executed','historical9c29_receiver_equivalence_claimed','source_generation_admitted','actor_publication','ack_permitted','world_authority'))
assert build['schema']=='coh-initial-progress-focused-v1' and build['passed'] is True and len(build['source_sha256'])==51
assert all(pins.get(name)==digest for name,digest in build['source_sha256'].items())
# The historical control file source is admitted exactly, not inferred current
# receiver/orchestration equivalence. Current validation still runs independently.
name='tools/android/atlasgame/prepare_server_fx_control_fixture.py'
historical=subprocess.check_output(['git','show','9c29e08c8d7e0ab38cff00f2997c39738a56ad07:'+name])
assert hashlib.sha256(historical).hexdigest()==pins[name]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head
receipt={'schema':'coh-initial-progress-current-source-gate-v1','passed':True,'source_revision':head,'source_sha256':pins,
 'current_orchestration_required':True,'historical_runtime_revision':'9c29e08c8d7e0ab38cff00f2997c39738a56ad07',
 'historical_receiver_equivalence_claimed':False,'strict_new_native_admission_pending':True,
 'compiler_or_native_rebuilt':False,'runtime_executed':False,'source_generation_admitted':False,'world_authority':False}
path=pathlib.Path(os.environ['RUNNER_TEMP'])/'initial-progress-current-source-admission.json'
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
with os.fdopen(fd,'w') as stream:json.dump(receipt,stream,sort_keys=True,indent=2);stream.write('\\n');stream.flush();os.fsync(stream.fileno())
print(json.dumps({'current_raw_committed_sources_admitted':True,'current_source_pins':len(pins),'current_orchestration_inputs':245,'native_inputs':51,'historical_receiver_equivalence_claimed':False,'runtime_executed':False}))
PYCURRENTPROGRESS
'''
for key,value in [('PINS_LITERAL',pprint.pformat(pins,sort_dicts=True,width=120)),('PIN_COUNT',str(len(pins)+1)),('CLOSURE_LITERAL',repr(closure_name)),('PROOF_LITERAL',repr(proof_name)),('BUILD_LITERAL',repr(build_name))]:rawgate=rawgate.replace(key,value)
admit='''python3 - <<'PYNEWNATIVE'
import gzip,hashlib,json,os,pathlib,sys
if not __debug__ or os.environ.get('PYTHONOPTIMIZE'):raise ValueError('OPTIMIZED_NATIVE_ADMISSION_REFUSED')
root=pathlib.Path.cwd().resolve();gate_path=pathlib.Path(os.environ['RUNNER_TEMP'])/'initial-progress-current-source-admission.json'
gate=json.loads(gate_path.read_bytes())
assert gate['schema']=='coh-initial-progress-current-source-gate-v1' and gate['passed'] is True and gate['source_revision']==os.environ['GITHUB_SHA']
# Every project source is byte-admitted before imports. Actual native admission
# below independently runs the new source-owned dependency query and Git guard.
for name,digest in gate['source_sha256'].items():
 path=root/name;assert path.resolve()==path and path.is_file() and not path.is_symlink() and hashlib.sha256(path.read_bytes()).hexdigest()==digest
os.umask(0o077);out=pathlib.Path(os.environ['RUNNER_TEMP'])/'groups-inputs/initial-progress';out.mkdir(mode=0o700)
compressed=root/GZIP_LITERAL;receipt=root/BUILD_LITERAL
with gzip.open(compressed,'rb') as source:
 raw=source.read(193217);assert len(raw)==193216 and source.read(1)==b''
assert hashlib.sha256(raw).hexdigest()=='5e423e0255a4b0dcab09b12d875c4a8090ba5c20e16ea0c8cdc189e11471f89a'
binary=out/'coh-capture-initial-progress'
fd=os.open(binary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o700)
with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
build=out/'build.json';fd=os.open(build,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
with os.fdopen(fd,'wb') as stream:stream.write(receipt.read_bytes());stream.flush();os.fsync(stream.fileno())
sys.path.insert(0,str(root/'native-android/engine/scenecatalog-server'))
import capture_groups_transaction as core
import initial_progress_admission as progress
native=core.native_input(binary,build,gate['source_sha256'][BUILD_LITERAL],root)
assert native['build_schema']=='coh-initial-progress-focused-v1' and native['diagnostic_role']=='command_unattributed_post_queue_progress'
assert native['binary']['bytes']==193216 and native['project_dependencies']==51 and native['historical_receiver_equivalence_established'] is False
assert all(gate['source_sha256'].get(name)==digest for name,digest in native['dependencies_sha256'].items())
closure=json.loads((root/CLOSURE_LITERAL).read_bytes())
source_paths=core.orchestration_source_paths({'build_role':'nonshipping_fresh_callback_sealed_groups_observer'},native)
assert source_paths==set(closure['source_sha256'])
pins={name:core.d.hash_file(root/name,8*1024**2)[1] for name in sorted(source_paths)}
assert pins==closure['source_sha256']
core.verify_orchestration(root,pins,os.environ['GITHUB_SHA'])
# Re-admit the retained original Map against CURRENT source helpers independently.
# This keeps all original source/PE guards and never touches the old native ELF.
original,_=core.admit.inspect(pathlib.Path(os.environ['RUNNER_TEMP'])/'groups-inputs/observer/fresh-groups-compile',root,os.environ['FRESH_OBSERVER_RECEIPT_SHA256'])
assert original['build_role']=='nonshipping_fresh_callback_sealed_groups_observer'
assert original['artifacts']['MapServer.exe']=={'bytes':7508480,'sha256':'73e6c724fcdd9b1caaa03bd675d38d075cc452575539cb99b19b6d1124113aba'}
result={'schema':'coh-initial-progress-current-input-admission-v1','passed':True,'source_revision':gate['source_revision'],
 'current_orchestration_inputs':len(pins),'native_source_inputs':51,'native_build_schema':native['build_schema'],
 'retained_new_native_bytes':193216,'historical_receiver_equivalence_claimed':False,'preprocessor_dependency_queries_only':True,
 'old_native_receiver_consumed':False,'native_or_original_server_executed':False,'compiler_or_native_rebuilt':False,
 'source_generation_admitted':False,'actor_publication':False,'world_authority':False}
path=pathlib.Path(os.environ['RUNNER_TEMP'])/'initial-progress-current-input-admission.json'
with path.open('x') as stream:json.dump(result,stream,sort_keys=True,indent=2);stream.write('\\n')
with pathlib.Path(os.environ['GITHUB_ENV']).open('a') as stream:stream.write('INITIAL_PROGRESS_BUILD_SHA256='+gate['source_sha256'][BUILD_LITERAL]+'\\n')
print(json.dumps(result,sort_keys=True))
PYNEWNATIVE
'''
for key,value in [('GZIP_LITERAL',repr(gzip_name)),('BUILD_LITERAL',repr(build_name)),('CLOSURE_LITERAL',repr(closure_name))]:admit=admit.replace(key,value)
job=copy.deepcopy({k:v for k,v in prior.items() if k!='steps'})
job['if']="github.repository == 'Russianranger/coh-android' && github.ref == 'refs/heads/native-android' && (github.event_name == 'workflow_dispatch' || contains(github.event.head_commit.message, '[fresh-initial-progress]'))"
job['steps']=[];s=job['steps']
checkout=copy.deepcopy(steps[0]);checkout['with'].pop('sparse-checkout',None);s.append(checkout);s.append(copy.deepcopy(steps[2]))
s.append({'name':'Admit current raw committed orchestration and explicit new native evidence before any current imports','id':'current_source_admission','working-directory':'current','run':rawgate})
for i in (3,4,5,6,7,8):
 item=copy.deepcopy(steps[i]);
 if i==3:item['name']='Admit historical505 runtime Map and fixture source guards without consuming its native receiver';item['id']='historical_source_admission'
 s.append(item)
tooling=copy.deepcopy(steps[9]);tooling['working-directory']='current';tooling['run']=tooling['run'].replace('export GITHUB_SHA=9c29e08c8d7e0ab38cff00f2997c39738a56ad07\n','');s.append(tooling)
s.append({'name':'Admit retained193216B progress ELF and actual current51 plus245 Git source closure without rebuild or execution','id':'progress_input_admission','working-directory':'current','run':admit})
s.append(copy.deepcopy(steps[11]))
capture=copy.deepcopy(steps[12]);capture['id']='original_transaction';capture['name']='Observe exactly one fresh original transaction with current native progress role and unchanged prepared runtime';capture['working-directory']='current';r=capture['run'].replace('export GITHUB_SHA=9c29e08c8d7e0ab38cff00f2997c39738a56ad07\n','')
r=r.replace("CONTROL_RUNTIME=$(python3 -c \"import json;print(json.load(open('out/groups-control/control-fixture.json'))['runtime_host_path'])\")", "CONTROL_FIXTURE=\"$GITHUB_WORKSPACE/runtime/out/groups-control/control-fixture.json\"\nCONTROL_RUNTIME=$(python3 -c \"import json,sys;print(json.load(open(sys.argv[1]))['runtime_host_path'])\" \"$CONTROL_FIXTURE\")")
r=r.replace('--control-fixture out/groups-control/control-fixture.json','--control-fixture "$CONTROL_FIXTURE"').replace('groups-inputs/initial-capture/coh-capture-local-initial','groups-inputs/initial-progress/coh-capture-initial-progress').replace('groups-inputs/initial-capture/build.json','groups-inputs/initial-progress/build.json').replace('"$INITIAL_BUILD_SHA256"','"$INITIAL_PROGRESS_BUILD_SHA256"');capture['run']=r;s.append(capture)
summary=copy.deepcopy(steps[14]);summary['working-directory']='current';summary['if']="always() && steps.progress_input_admission.outcome == 'success'";summary['run']=summary['run'].replace('export GITHUB_SHA=9c29e08c8d7e0ab38cff00f2997c39738a56ad07\n','');s.append(summary)
s.append({'name':'Export only new fixed command-unattributed progress projection after matching pair and owned cleanup','if':"always() && steps.original_transaction.outcome == 'success'",'working-directory':'current','run':'''python3 native-android/engine/scenecatalog-server/initial_progress_admission.py \\
 --private-output "$RUNNER_TEMP/groups-private-result" \\
 --output out/groups-public/progress.json > out/groups-public/progress-status.json
'''})
s.append({'uses':'actions/upload-artifact@v4','if':'always()','with':{'name':'fresh-initial-progress-public-${{ github.sha }}','path':'current/out/groups-public/summary.json\ncurrent/out/groups-public/tooling.json\ncurrent/out/groups-public/progress.json\ncurrent/out/groups-public/progress-status.json\n','if-no-files-found':'warn','retention-days':90}})
workflow={'name':'Focused original initial request progress observation','on':{'push':{'branches':['native-android'],'paths':['.github/workflows/native-initial-progress-observation.yml']},'workflow_dispatch':{}},'permissions':{'contents':'read','actions':'read'},'concurrency':{'group':'native-initial-progress-observation-${{ github.ref }}','cancel-in-progress':False},'jobs':{'matching-original-initial-progress':job}}
class Dumper(yaml.SafeDumper):pass
def strings(dumper,value):return dumper.represent_scalar('tag:yaml.org,2002:str',value,style='|' if '\n' in value else None)
Dumper.add_representer(str,strings)
OUT.write_text(yaml.dump(workflow,Dumper=Dumper,sort_keys=False,width=120,allow_unicode=True))
print(json.dumps({'workflow':str(OUT),'bytes':OUT.stat().st_size,'sha256':hashlib.sha256(OUT.read_bytes()).hexdigest(),'current_pins_with_dynamic_self':len(pins)+1,'historical_gate_unchanged':s[3]['run']==steps[3]['run'],'steps':len(s)}))
