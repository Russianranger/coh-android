#!/usr/bin/env python3
"""Bounded original ParseBoneNames on exact retained CLIENT body-cache rows."""
import argparse,hashlib,importlib.util,json,os,shlex,shutil,struct,subprocess,tempfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ARCHIVE='native-android/engine/entities/qualification/costume-export-20261017/exact-client-dictionary-bins.zip'
ARCHIVE_SHA='350c7ad531209a7e3959cb2f4ae044d8551820cc03e9d40ce17c3aae2a5e3241'
ARCHIVE_BLOB='606fd1e17751fbdf6d7c903dee4eaea40c2014f3'
BODY_SHA='b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb'
def sha(value):return hashlib.sha256(value).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if p.returncode:raise RuntimeError('PARSE_BONE_NAMES_QUALIFICATION_REFUSED\n'+p.stdout+p.stderr)
 return p
def module(path):
 s=importlib.util.spec_from_file_location('qualified_parse_bone_names_provider',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def compiler(name,work):
 found=shutil.which(name)
 if not found:raise ValueError('Required host compiler unavailable')
 path=Path(found).resolve();raw=path.read_bytes();version=run([path,'--version'])
 if version.stderr or len(version.stdout.encode())>8192:raise ValueError('Compiler diagnostic bound')
 (work/(name+'-version.stdout')).write_text(version.stdout)
 return {'command':name,'resolved_path':str(path),'executable_bytes':len(raw),'executable_sha256':sha(raw),'version_first_line':version.stdout.splitlines()[0],'version_stdout_sha256':sha(version.stdout.encode())}
def authentic(root,work):
 path=root/ARCHIVE;data=path.read_bytes()
 if len(data)!=2253704 or sha(data)!=ARCHIVE_SHA or run(['git','-C',root,'rev-parse','HEAD:'+ARCHIVE]).stdout.strip()!=ARCHIVE_BLOB:raise ValueError('Retained exact CLIENT archive changed')
 with zipfile.ZipFile(path)as z:
  members=z.infolist();expected={'data/bin/BodyParts.bin':2584,'data/bin/costume.bin':17691352,'data/bin/supergroupColors.bin':2664}
  if len(members)!=3 or {i.filename:i.file_size for i in members}!=expected or any(i.flag_bits&1 or i.is_dir()for i in members):raise ValueError('Retained subset inventory changed')
  body=z.read('data/bin/BodyParts.bin')
 if len(body)!=2584 or sha(body)!=BODY_SHA:raise ValueError('Exact CLIENT BodyParts bytes changed')
 (work/'BodyParts.bin').write_bytes(body)
 return body,{'archive_path':ARCHIVE,'archive_bytes':len(data),'archive_sha256':ARCHIVE_SHA,'archive_git_blob_sha1':ARCHIVE_BLOB,'member':'data/bin/BodyParts.bin','member_bytes':len(body),'member_sha256':BODY_SHA,'retained_origin_run_id':36707839624,'retained_origin_artifact_id':11092897979,'scope':'Exact committed subset of independently retained authentic CLIENT caches. No regeneration or claim current MapServer consumed these bytes.','new_donor_generation':False,'current_server_consumption_verified':False}
class TrustedProjection:
 """Independent valid-fixture projection, not a replacement cache decoder."""
 def __init__(self,raw):self.raw=raw;self.at=0
 def take(self,n):
  if n<0 or n>len(self.raw)-self.at:raise ValueError('Trusted fixture extent')
  raw=self.raw[self.at:self.at+n];self.at+=n;return raw
 def word(self):return struct.unpack('<I',self.take(4))[0]
 def text(self):
  n=struct.unpack('<H',self.take(2))[0];value=self.take(n)
  if n>259 or b'\0'in value or not value.isascii():raise ValueError('Trusted fixture string profile')
  self.take((4-(n+2)%4)%4);return value
 def end(self):return self.word()+self.at
def fixture(body,reference,work):
 p=TrustedProjection(body)
 if p.take(8)!=b'CrypticS'or p.word()!=0xcf27aba3 or p.text()!=b'Parse6'or p.text()!=b'Files1':raise ValueError('Trusted body envelope')
 dep_end=p.end();deps=p.word()
 if deps!=1:raise ValueError('Trusted dependency count')
 dep=p.text();stamp=p.word()
 if p.at!=dep_end or p.at!=64 or dep!=b'Defs/UI/bodyparts.bp':raise ValueError('Trusted dependency identity')
 end=p.end();count=p.word()
 if count!=28 or end!=len(body):raise ValueError('Trusted body count')
 lookup={row['name'].lower():row['value']for row in reference['entries']};rows=[]
 for index in range(count):
  row_end=p.end();name=p.text();source=p.text();first=p.word();influence=p.word();geometry=p.text();texture=p.text();base=p.text();last=p.word();dont=p.word();b0=p.word();b1=p.word();part_index=p.word()
  if p.at!=row_end or last not in(1,2):raise ValueError('Trusted body row')
  get=lambda value:lookup.get(value.decode('ascii').lower(),-1)
  derived=[get(geometry),signed(b1)]if last==1 else[get(geometry+b'R'),get(geometry+b'L')]
  rows.append({'strings':[name,source,geometry,texture,base],'raw':[first,influence,last,dont,b0,b1,part_index],'expected':[*derived,index]})
 if p.at!=end:raise ValueError('Trusted body end')
 out=work/'callback-fixtures.bin'
 with out.open('xb')as f:
  f.write(struct.pack('<III',0x314e5043,len(body),count));f.write(bytes.fromhex(BODY_SHA));f.write(body)
  for row in rows:
   for value in row['strings']:f.write(struct.pack('<I',len(value)));f.write(value)
   f.write(struct.pack('<7I3i',*row['raw'],*row['expected']))
 (work/'trusted-row-reference.json').write_text(json.dumps([{'index':i,'name':r['strings'][0].decode(),'geometry':r['strings'][2].decode(),'num_parts':r['raw'][2],'raw_bones':[signed(r['raw'][4]),signed(r['raw'][5])],'raw_part_index':signed(r['raw'][6]),'expected_bones':r['expected'][:2],'expected_part_index':r['expected'][2]}for i,r in enumerate(rows)],indent=2)+'\n')
 return out,{'bytes':out.stat().st_size,'sha256':sha(out.read_bytes()),'authentic_rows':count,'paired_rows':sum(r['raw'][2]==2 for r in rows),'expected_lookup_calls':sum(r['raw'][2]for r in rows),'unknown_first_bone_results':sum(r['expected'][0]==-1 for r in rows),'dependency_timestamp':stamp,'expectation_origin':'Independent field projection of only the exact SHA-pinned trusted CLIENT cache; derived names and indices evaluated using independently parsed original enum reference. Each native mode separately decodes full bytes using the unchanged already-qualified native input reader and checks every retained raw field.','raw_cached_bones_are_not_callback_proof':True,'duplicate_BoneCount_callback_uses_last':True}
def signed(value):return value if value<0x80000000 else value-0x100000000
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence-directory',type=Path);p.add_argument('--sanitize',action='store_true');a=p.parse_args();root=a.source_root.resolve()
 if not __debug__:raise ValueError('Python assertions required')
 if a.output.exists()or(a.evidence_directory and a.evidence_directory.exists()):raise ValueError('Fresh output/evidence required')
 provider=module(HERE/'parse_bone_names_provider.py')
 new_inputs=[Path(__file__).resolve(),HERE/'test_parse_bone_names.c',HERE/'parse_bone_names_provider.py',HERE/'parse-bone-names-source-pins.json',HERE/'bone_enum_provider.py',HERE/'source-pins.json',root/ARCHIVE,root/'native-android/engine/costume-inputs/coh_costume_inputs.c',root/'native-android/engine/costume-inputs/coh_costume_inputs.h',root/'native-android/engine/costume-inputs/source-pins.json']
 initial={path.resolve():path.read_bytes()for path in new_inputs}
 temporary=tempfile.TemporaryDirectory(prefix='coh-parse-bones-')if not a.evidence_directory else None;work=Path(temporary.name)if temporary else a.evidence_directory.resolve()
 if not temporary:work.mkdir(parents=True)
 try:
  compilers={name:compiler(name,work)for name in('cc','c++')};body,cache=authentic(root,work);generated,origin,reference=provider.build(root,work);generated=Path(generated)
  inputs=set(initial)
  for name,digest in origin['source_sha256'].items():
   path=(root/name).resolve()
   if sha(path.read_bytes())!=digest:raise ValueError('Source provider pin changed')
   inputs.add(path)
  decoder=root/'native-android/engine/costume-inputs/coh_costume_inputs.c';test=HERE/'test_parse_bone_names.c'
  for source in(decoder,test,generated):
   deps=run(['cc','-std=c99','-I'+str(work),'-MM',source]).stdout.replace('\\\n',' ').split(':',1)[1]
   inputs.update(Path(name).resolve()for name in shlex.split(deps)if Path(name).resolve().is_relative_to(root))
  if any(path.read_bytes()!=raw for path,raw in initial.items()):raise ValueError('Source changed during provider generation')
  sources={path:path.read_bytes()for path in inputs};generated_bytes=generated.read_bytes()
  def verify():
   if any(path.read_bytes()!=raw for path,raw in sources.items())or generated.read_bytes()!=generated_bytes:raise ValueError('Source changed during callback qualification')
   for name,identity in compilers.items():
    if Path(shutil.which(name)).resolve()!=Path(identity['resolved_path'])or sha(Path(identity['resolved_path']).read_bytes())!=identity['executable_sha256']:raise ValueError('Compiler changed during callback qualification')
  verify();wire,projection=fixture(body,reference,work);checks={};binaries={};commands=[];stack=[];modes=[('release',['-O2','-fstack-usage'])]
  if a.sanitize:modes +=[('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1',LC_ALL='C')
  for mode,flags in modes:
   exe=work/('callback-'+mode);cmd=['cc','-std=c99','-Wall','-Wextra','-Werror','-Wno-missing-field-initializers','-Wno-unused-parameter','-pedantic','-fno-strict-aliasing',*flags,'-I'+str(work),str(generated),str(decoder),str(test),'-lcrypto','-lm','-o',str(exe)];commands.append({'mode':mode,'argv':cmd});built=run(cmd);(work/(mode+'-compile.stdout')).write_text(built.stdout);(work/(mode+'-compile.stderr')).write_text(built.stderr);result=run([exe,wire],env=env)
   if result.stderr or len(result.stdout.encode())>4096:raise ValueError('Unexpected bounded native result')
   (work/(mode+'.stdout')).write_text(result.stdout);(work/(mode+'.stderr')).write_text(result.stderr);checks[mode]=json.loads(result.stdout);binaries[mode]=sha(exe.read_bytes());verify()
  if any(value!=checks['release']for value in checks.values()):raise ValueError('Native mode results differ')
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t');stack.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
  if not stack or any(row['bound']not in('static','dynamic,bounded')for row in stack):raise ValueError('Unbounded native stack')
  verify();(work/'native-commands.json').write_text(json.dumps(commands,indent=2)+'\n');files={str(path.relative_to(work)):{'bytes':path.stat().st_size,'sha256':sha(path.read_bytes())}for path in sorted(work.rglob('*'))if path.is_file()}
  proof={'schema':'coh-original-parse-bone-names-qualification-v1','passed':True,'source_revision':run(['git','-C',root,'rev-parse','HEAD']).stdout.strip(),'source_sha256':{str(path.relative_to(root)):sha(raw)for path,raw in sorted(sources.items())},'source_stable_before_after':True,'host_compiler_identities':compilers,'host_compilers_stable_before_after':True,'original_callback_provider':origin,'retained_authentic_CLIENT_input':cache,'trusted_fixture_projection':projection,'checks':checks,'binary_sha256':binaries,'native_stack_frames':stack,'evidence_files':files,'scope':'Original ParseBoneNames callback on 28 rows decoded from exact retained authentic CLIENT cache by the unchanged already-qualified native reader, plus explicit synthetic bounded profile controls. Accepted actual generated BoneIdEnum provider rebuilt only as a dependency; no old checker/native suite replay. No original full Parse6 parser/loader, full startup, current Map/runtime catalog, dictionary generation/import, character, authority or application ACK acceptance. Original MAX_BODYPARTS is60;29 is narrower qualification/native policy. Unknown -1 and COUNT results are preserved rather than newly rejected.','external_crypto_sanitizer_or_stack_closure':False,'old_checker_mains_executed':False,'old_native_suites_executed':False,'original_full_parse6_executed':False,'current_map_runtime_executed':False,'runtime_catalog_admitted':False,'dictionary_imported':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks,'authentic_rows':projection['authentic_rows']}))
 finally:
  if temporary:temporary.cleanup()
if __name__=='__main__':main()
