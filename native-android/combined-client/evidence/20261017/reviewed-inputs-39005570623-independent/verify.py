#!/usr/bin/env python3
"""Read-only admission of the exact retained two-job qualification artifacts."""
import argparse,hashlib,io,json,re,struct,subprocess,zipfile
from pathlib import Path,PureWindowsPath
COMMIT='d6ef33b3306c496e6d6a9ee2f8c9ab12ffdfbc05'
TREE='c28a0de2a49e1612e1bfc161854ca029ae621ed2'
ARTIFACTS={'12090976855':(2020,'dcc711abdf9031570ed4161dea519b75ef2eb062cc825e85bbcf799b89961da9'),
 '12090613318':(4986,'a9435c960839c4a4b93174d527b5d1c294ed9f964ed507ccd943cd9676e40c23')}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def check(value,message):
 if not value:raise ValueError(message)
def members(raw,expected):
 check((len(raw),sha(raw))==expected,'Exact Actions artifact ZIP identity differs')
 with zipfile.ZipFile(io.BytesIO(raw))as z:
  items=z.infolist();check(len(items)==len({x.filename for x in items})<=8 and sum(x.file_size for x in items)<=128*1024,'Artifact member bounds')
  check(z.testzip()is None,'Artifact ZIP CRC')
  return {x.filename:z.read(x)for x in items}
def verify(root,cache):
 def git(*args):return subprocess.check_output(['git','--no-replace-objects','-C',str(root),*args],timeout=30)
 def blob(path):return git('show',COMMIT+':'+path)
 check(git('rev-parse',COMMIT+'^{tree}').decode().strip()==TREE,'Historical source tree')
 archives={k:members((cache/k/'artifact.zip').read_bytes(),v)for k,v in ARTIFACTS.items()}
 linux=archives['12090976855'];check(set(linux)=={'receipt.json','v5-stdout.bin','v5-stderr.bin','v7-stdout.bin','v7-stderr.bin'},'Exact execution members')
 p=json.loads(linux['receipt.json']);check(p['passed']is True and p['validation_only']is False and p['source_inputs_unchanged']is True and p['source_revision']==COMMIT,'Actual execution scope')
 for name in ['compiler_executed','server_executed','android_executed','apk_rebuilt','material_authority','live_world','thor_accepted']:check(p[name]is False,'Contradictory execution scope')
 expected_paths={'native-android/combined-client/tools/run_retained_original32.py'}
 versions={}
 for version,words,stem in [(5,55,'original-source'),(7,52,'sealed-original32')]:
  base='native-android/engine/world-render-adapter/qualification/rigid-v%d-20261017/'%version
  checksum='original-source-diagnostics-checksums.json'if version==5 else'sealed-original32-checksums.json'
  paths=[base+checksum,base+'expected-v%d-facts.json'%version,base+'expected-v%d-facts.bin'%version,base+stem+'-diagnostics.zip'];expected_paths.update(paths)
  pins=json.loads(blob(paths[0]));facts=json.loads(blob(paths[1]));expected=blob(paths[2]);raw=blob(paths[3]);check(len(raw)==pins['zip_bytes']and sha(raw)==pins['zip_sha256'],'Retained witness archive')
  with zipfile.ZipFile(io.BytesIO(raw))as z:
   check(len(z.infolist())==len(pins['files'])and set(z.namelist())==set(pins['files'])and z.testzip()is None,'Retained witness members')
   for name,row in pins['files'].items():body=z.read(name);check(len(body)==row['bytes']and sha(body)==row['sha256'],'Retained witness member identity')
   binary=z.read('original-read-model');source=z.read('original-read-model.c')
  observed=p['versions'][str(version)]
  check(observed['original32_executed']is True and observed['facts_equal']is True and observed['words']==words and observed['bytes']==words*4,'Executed metadata witness')
  check(len(expected)==words*4 and expected==struct.pack('<'+'I'*words,*facts['expected_u32_le']),'Expected fact words')
  check(linux['v%d-stdout.bin'%version]==expected and not linux['v%d-stderr.bin'%version],'Exact actual stdout and empty stderr')
  for key,value in [('binary_sha256',sha(binary)),('oracle_source_sha256',sha(source)),('archive_sha256',sha(raw)),('stdout_sha256',sha(expected)),('body_sha256',facts['body_sha256']),('row',facts['row']),('model',facts['model'])]:check(observed[key]==value,'Actual/retained witness binding '+key)
  check(facts['original_readModel_binary_sha256']==sha(binary)and facts['generated_oracle_source_sha256']==sha(source),'Expected witness source/binary pin')
  versions[str(version)]=observed
 check(set(p['source_sha256'])==expected_paths,'Complete runner dependency set')
 for path,h in p['source_sha256'].items():check(sha(blob(path))==h,'Execution source Git bytes')
 check(sha(blob('.github/workflows/native-reviewed-inputs.yml'))=='8b9b5b8b999760d85e65efa424c463929d50c8762403bcab068c6bf25d773403','Reviewed workflow')
 windows=archives['12090613318'];check(set(windows)=={'receipt.json'},'Exact inventory members');w=json.loads(windows['receipt.json'])
 check(w['passed']is True and w['repository_commit']==COMMIT and w['repository_tree']==TREE and w['github_run_id']=='39005570623','Actual inventory identity')
 check(w['original_source_tree']==git('rev-parse',COMMIT+':upstream/ouroboros').decode().strip(),'Original source tree')
 check(w['all_tool_inputs_stable']is True and w['source_inputs_unchanged']is True and w['observation_before']==w['observation_after'] and w['input_state_before']==w['input_state_after'],'Actual stable observations')
 state=w['input_state_before'];check(state['commit']==COMMIT and state['tracked_dirty']=='','Actual source clean state')
 eol={}
 for name,h in state['helper_inputs'].items():
  path='native-android/engine/auth-interop/'+name.replace('\\','/');raw=blob(path);crlf=raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
  check(sha(crlf)==h,'Windows checkout source requires exact Git LF to CRLF bytes');eol[path]={'git_sha256':sha(raw),'observed_CRLF_sha256':h}
 check(len(eol)==61 and 'native-android/engine/auth-interop/deployment/windows_tool_inventory.py'in eol,'Complete inventory helper set')
 for name in ['compiler_executed','cmake_executed','source_patched','dependencies_fetched','service_executed','toolchain_reviewed','compile_permit','shipping_runtime_replacement_permit']:check(w[name]is False,'Inventory cannot authorize build/runtime')
 observation=w['observation_before'];check(set(observation['tools'])=={'cl','link','ml','msbuild','git','patch','cmake'},'Seven observed primary tools')
 check(len(w['observed_lock_candidates'])==1,'One complete observed candidate');candidate=w['observed_lock_candidates'][0]
 check(candidate['schema']=='coh-observed-windows-build-tool-lock-v1'and candidate['requires_independent_review']is True,'Unreviewed candidate schema')
 check((w['image_os'],w['image_version'],w['vc_toolset_version'])==('win25-vs2026','20261007.264.1','14.51.36231'),'Actual image/toolset')
 check(observation['file_versions']['cl']=='19.51.36260.0'and observation['file_versions']['cmake']=='4.4.4.0','Actual version resources')
 sdk='10.0.26100.0';check(set(observation['sdks'])=={sdk}and not observation['sdks'][sdk]['missing'],'Complete observed SDK representatives')
 expected=dict(schema='coh-observed-windows-build-tool-lock-v1',requires_independent_review=True,image_os=w['image_os'],image_version=w['image_version'],generator='Visual Studio 18 2026',architecture='Win32',vs_installation=w['vs_installation'],vc_toolset_version=w['vc_toolset_version'],windows_sdk_version=sdk,compiler_version=observation['file_versions']['cl'],cmake_version=observation['file_versions']['cmake'][:-2],tools=dict(observation['tools'],rc=observation['sdks'][sdk]['files']['rc']))
 check(candidate==expected,'Exact observed candidate projection')
 for name,row in candidate['tools'].items():
  path=PureWindowsPath(row['path']);check(path.is_absolute()and str(path)==row['path']and 0<row['bytes']<=256*1024*1024 and re.fullmatch('[0-9a-f]{64}',row['sha256']),'Observed tool record')
  if name in['cl','link','ml','msbuild']:check(path.is_relative_to(PureWindowsPath(w['vs_installation'])),'Observed VS tool ownership')
 return {'passed':True,'run_id':'39005570623','source_commit':COMMIT,'source_tree':TREE,'artifacts':{k:{'bytes':v[0],'sha256':v[1]}for k,v in ARTIFACTS.items()},'original32_receipt_sha256':sha(linux['receipt.json']),'inventory_receipt_sha256':sha(windows['receipt.json']),'executed_original32':versions,'source_dependency_count':len(expected_paths),'inventory_helpers_CRLF_binding':eol,'inventory_candidate':candidate,'actual_inventory_observation_verified':True,'reviewed_tool_lock_generated':False,'compiler_executed':False,'server_executed':False,'android_executed':False,'material_authority':False,'live_world':False,'thor_accepted':False,'scope':'Actual freestanding Linux i386 readModel metadata execution and read-only Windows tool observation; no compiler, Win32 engine, SDK DLL closure, runtime or game-world admission.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--artifact-cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=verify(a.source_root,a.artifact_cache);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'versions':list(result['executed_original32']),'inventory_observed':True}))
