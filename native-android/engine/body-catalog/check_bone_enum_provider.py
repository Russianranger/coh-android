#!/usr/bin/env python3
"""Qualify the actual original StructParser bone-enum provider, source-only."""
import argparse,hashlib,importlib.util,json,os,re,shlex,shutil,struct,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
QUERY_MAX=259
ROW_MAX=256
QUERY_COUNT_MAX=4096
RESULT_MAX=4096

def sha(raw):return hashlib.sha256(raw).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError('BONE_ENUM_QUALIFICATION_REFUSED\n'+p.stdout+p.stderr)
 return p
def module(path):
 spec=importlib.util.spec_from_file_location('qualified_bone_enum_provider',path)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def compiler_identity(name,work):
 found=shutil.which(name)
 if not found:raise ValueError('Required host compiler unavailable')
 path=Path(found).resolve();raw=path.read_bytes();version=run([path,'--version'])
 if version.stderr or len(version.stdout.encode())>8192:raise ValueError('Compiler version diagnostic bound')
 (work/(name+'-version.stdout')).write_text(version.stdout)
 return {'command':name,'resolved_path':str(path),'executable_bytes':len(raw),'executable_sha256':sha(raw),'version_first_line':version.stdout.splitlines()[0],'version_stdout_sha256':sha(version.stdout.encode())}
def refusal_controls(provider,root,work,reference):
 header=(root/provider.BONES).read_text().replace('\r\n','\n')
 controls=[('missing-auto-enum',header.replace('AUTO_ENUM;','',1)),('invalid-sentinel',header.replace('BONEID_INVALID = -1','BONEID_INVALID = 0',1)),('default-alias',header.replace('BONEID_DEFAULT = 0','BONEID_DEFAULT = 1',1)),('first-ordinal',header.replace('BONEID_HIPS,','BONEID_HIPS = 1,',1)),('duplicate-symbol',header.replace('BONEID_WAIST,','BONEID_HIPS,',1)),('unsupported-expression',header.replace('BONEID_HEAD,','BONEID_HEAD = 1 << 4,',1)),('count-ordinal',header.replace('BONEID_COUNT,','BONEID_COUNT = 100,',1)),('missing-end',header.replace('} BoneId;','} Broken;',1))]
 refused=[]
 for name,changed in controls:
  if changed==header:raise ValueError('Refusal control did not mutate header')
  try:provider.parse_reference(changed)
  except ValueError:refused.append(name)
  else:raise ValueError('Reference mutation accepted: '+name)
 if provider.parse_reference('/* qualification whitespace */\n'+header)!=reference:raise ValueError('Comment-only independent reference differs')
 pins=json.loads((HERE/'source-pins.json').read_text());name=next(iter(pins['files']));original=(root/name).read_bytes()
 for case,changed in [('same-size-byte-mutation',bytes([original[0]^1])+original[1:]),('extent-mutation',original+b'\n')]:
  control=work/('refuse-'+case);fake=control/'root';path=fake/name;path.parent.mkdir(parents=True);path.write_bytes(changed)
  try:provider.build(fake,control/'tool-work')
  except ValueError:refused.append(case)
  else:raise ValueError('Changed pinned source accepted')
 return {'refused':refused,'refusal_count':len(refused),'comment_only_reference_control':True,'mutation_generator_rebuilds':0,'scope':'Synthetic malformed reference/header and mutated exact source-pin controls; no original source files changed.'}
def fixture(reference,path):
 entries=reference['entries'];bone_count=reference['bone_count']
 if not 0<bone_count<ROW_MAX or not bone_count<len(entries)<=ROW_MAX:raise ValueError('Reference bounds')
 names={}
 for row in entries:
  if set(row)!={'symbol','name','value'}or not isinstance(row['name'],str)or not row['name'].isascii()or not 0<len(row['name'])<=QUERY_MAX or '\0'in row['name']or type(row['value'])is not int:raise ValueError('Reference row')
  key=row['name'].lower()
  if key in names:raise ValueError('Ambiguous reference name')
  names[key]=row['value']
 if names.get('default')!=0 or names.get('invalid')!=-1 or names.get('count')!=bone_count:raise ValueError('Source sentinel/alias mapping')
 queries=[];seen=set()
 def add(name,kind):
  raw=name.encode('ascii')
  if len(raw)>QUERY_MAX:raise ValueError('Query bounds')
  if raw not in seen:queries.append((raw,names.get(name.lower(),-1),kind));seen.add(raw)
 for row in entries:
  name=row['name'];add(name,0)
  for variant in(name.lower(),name.upper(),''.join(c.lower()if i&1 else c.upper()for i,c in enumerate(name))):add(variant,1)
  # Independent header reference computes expected answers even if a mutation
  # happens to form another real alias/name. No table-to-itself expectation.
  for i in sorted({0,len(name)//2,len(name)-1}):
   add(name[:i]+'!'+name[i+1:],2);add(name[:i]+name[i+1:],2)
  add('BONEID_'+name,3)
 for name in('', 'not_a_bone', '1','0','-1','COUNT!',' INVALID','DEFAULT ','BONEID_HIPS','!','9'*QUERY_MAX):add(name,3)
 if not 0<len(queries)<=QUERY_COUNT_MAX:raise ValueError('Query count bound')
 with path.open('xb')as out:
  out.write(struct.pack('<4I',0x31454243,bone_count,len(entries),len(queries)))
  for row in entries:
   name=row['name'].encode('ascii');out.write(struct.pack('<Ii',len(name),row['value']));out.write(name)
  for raw,value,kind in queries:out.write(struct.pack('<IiI',len(raw),value,kind));out.write(raw)
 if path.stat().st_size>2*1024*1024:raise ValueError('Fixture size bound')
 return {'sha256':sha(path.read_bytes()),'bytes':path.stat().st_size,'rows':len(entries),'queries':len(queries),'query_max':QUERY_MAX,'query_count_max':QUERY_COUNT_MAX,'reference_sha256':sha(json.dumps(reference,sort_keys=True,separators=(',',':')).encode()),'expectation_origin':'Independently parsed original AUTO_ENUM header symbols/order/decimal values and source-defined generator key-prefix transformation; not read back from generated table.','default_is_original_HIPS_alias':True,'COUNT_INVALID_unknown_are_not_numeric_bone_ids':True,'synthetic_controls':'Bounded ASCII case variants, inserted/deleted/substituted characters, prefixed/unknown/numeric/whitespace/maximum-length queries.'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence-directory',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if not __debug__:raise ValueError('Python assertions required')
 if a.output.exists():raise ValueError('Fresh output required')
 if a.evidence_directory and a.evidence_directory.exists():raise ValueError('Fresh evidence directory required')
 provider_path=HERE/'bone_enum_provider.py';provider=module(provider_path)
 project_inputs=[Path(__file__).resolve(),HERE/'test_bone_enum_provider.c',provider_path,HERE/'source-pins.json']
 initial={path.resolve():path.read_bytes()for path in project_inputs}
 evidence=a.evidence_directory.resolve()if a.evidence_directory else None
 temporary=tempfile.TemporaryDirectory(prefix='coh-bone-enum-')if evidence is None else None
 work=Path(temporary.name)if temporary else evidence
 if evidence:evidence.mkdir(parents=True)
 try:
  compilers={name:compiler_identity(name,work)for name in('cc','c++')}
  generated,origin,reference=provider.build(root,work)
  generated=Path(generated);manifest_sources=origin['source_sha256']
  inputs=set(initial)
  for name,digest in manifest_sources.items():
   path=(root/name).resolve()
   if sha(path.read_bytes())!=digest:raise ValueError('Provider source pin mismatch')
   inputs.add(path)
  for name in project_inputs:
   if name.read_bytes()!=initial[name.resolve()]:raise ValueError('Source changed during generator qualification')
  sources={path:path.read_bytes()for path in inputs}
  generated_bytes=generated.read_bytes()
  def verify():
   if any(path.read_bytes()!=raw for path,raw in sources.items())or generated.read_bytes()!=generated_bytes:raise ValueError('Source changed during bone qualification')
   for name,identity in compilers.items():
    if Path(shutil.which(name)).resolve()!=Path(identity['resolved_path'])or sha(Path(identity['resolved_path']).read_bytes())!=identity['executable_sha256']:raise ValueError('Host compiler changed during qualification')
  verify();controls=refusal_controls(provider,root,work,reference);wire=work/'lookup-fixtures.bin';proof=fixture(reference,wire)
  (work/'independent-reference.json').write_text(json.dumps(reference,indent=2)+'\n')
  checks={};binaries={};commands=[];stack=[];modes=[('release',['-O2','-fstack-usage'])]
  if a.sanitize:modes +=[('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LC_ALL='C')
  for mode,flags in modes:
   exe=work/('lookup-'+mode)
   cmd=['cc','-std=c99','-Wall','-Wextra','-Werror','-Wno-missing-field-initializers','-pedantic','-fno-strict-aliasing',*flags,str(generated),str(HERE/'test_bone_enum_provider.c'),'-o',str(exe)]
   commands.append({'mode':mode,'argv':cmd});compiled=run(cmd)
   (work/(mode+'-compile.stdout')).write_text(compiled.stdout);(work/(mode+'-compile.stderr')).write_text(compiled.stderr)
   got=run([exe,wire],env=env)
   if len(got.stdout.encode())>RESULT_MAX or got.stderr:raise ValueError('Unexpected native output')
   (work/(mode+'.stdout')).write_text(got.stdout);(work/(mode+'.stderr')).write_text(got.stderr)
   checks[mode]=json.loads(got.stdout);binaries[mode]=sha(exe.read_bytes());verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('Native modes differ')
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t');stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(row['bound']not in('static','dynamic,bounded')for row in stack):raise ValueError('Unbounded native stack')
  verify();(work/'native-commands.json').write_text(json.dumps(commands,indent=2)+'\n')
  # Full generator/native evidence lives alongside the compact receipt in the
  # workflow artifact. Paths are relative to that artifact's evidence directory.
  evidence_files={str(path.relative_to(work)):{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}for path in sorted(work.rglob('*'))if path.is_file()}
  result={'schema':'coh-original-bone-enum-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).stdout.strip(),'source_sha256':{str(path.relative_to(root)):sha(raw)for path,raw in sorted(sources.items())},'source_stable_before_after':True,'host_compiler_identities':compilers,'host_compilers_stable_before_after':True,'original_provider':origin,'independent_reference_fixture':proof,'refusal_controls':controls,'checks':checks,'binary_sha256':binaries,'native_stack_frames':stack,'evidence_files':evidence_files,'scope':'Actual original StructParser enum generation and original bone_IdFromName/StaticDefine lookup prerequisite only. No original ParseBoneNames callback, complete Parse6 body/builder, current Map runtime, body-catalog or dictionary import/generation/character/authority/application ACK admission. Bounded query profile is qualification policy, not original grammar. DEFAULT maps to original numeric0 alias; it is unrelated to unresolved costume default part count.','old_checker_mains_executed':False,'old_native_suites_executed':False,'original_parse_bone_names_executed':False,'original_full_parse6_executed':False,'current_map_runtime_executed':False,'runtime_catalog_admitted':False,'dictionary_imported':False,'source_generation_admitted':False,'server_owned_character_bound':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps({'passed':True,'checks':checks,'generated_rows':proof['rows'],'queries':proof['queries']}))
 finally:
  if temporary:temporary.cleanup()
if __name__=='__main__':main()
