#!/usr/bin/env python3
"""Focused authentic Details resource projection; no prior suites or world test."""
import argparse,ctypes as C,hashlib,importlib.util,io,json,os,re,subprocess,tarfile,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,s):
 if not ok:raise ValueError(s)
def word(n):return(n&0xffffffff).to_bytes(4,'little')
def text(b):return len(b).to_bytes(2,'little')+b+b'\0'*((4-(len(b)+2)%4)%4)
def main():
 if not __debug__ or os.environ.get('PYTHONOPTIMIZE'):raise ValueError('Python optimization unsupported')
 ap=argparse.ArgumentParser();ap.add_argument('--details-bin',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 raw=a.details_bin.read_bytes();need(len(raw)==401216 and sha(raw)=='11e5104e0210fa5cbbc910932e5df461a34853e9a30d43f890d31510cdf2ce28','exact complete original Details input')
 # Track the actual complete local #include closure, original immutable pins and
 # all provider inputs admitted by the unchanged existing provider manifests.
 source_paths=set(HERE.glob('*.c'))|set(HERE.glob('*.h'))|set(HERE.glob('*.py'))|{HERE/'source-pins.json',HERE/'CONTRACT.md'}
 pending=list(p for p in source_paths if p.suffix in('.c','.h'))
 while pending:
  p=pending.pop().resolve()
  for n in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):
   q=(p.parent/n).resolve()
   if q.is_file()and q not in source_paths:source_paths.add(q);pending.append(q)
 manifest=json.loads((HERE/'source-pins.json').read_bytes());source_paths|={ROOT/p for p in manifest['source_sha256_raw']}
 for filename in ('salvage-source-pins.json',):
  p=HERE/'../character-dictionary'/filename;pin=json.loads(p.read_bytes());source_paths.add(p.resolve());source_paths|={ROOT/'upstream/ouroboros'/n for n in pin['source_sha256_raw']};source_paths|={ROOT/n for n in pin['helper_sha256_raw']}
 source_paths={p.resolve()for p in source_paths};before={str(p.relative_to(ROOT)):sha(p.read_bytes())for p in sorted(source_paths)}
 revision=subprocess.check_output(['git','-C',ROOT,'rev-parse','HEAD'],text=True).strip()
 spec=importlib.util.spec_from_file_location('resources_oracle',HERE/'resource_oracle.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
 src=(ROOT/'upstream/ouroboros/Common/bases/basedata.c').read_text();table=src[src.index('static TokenizerParseInfo ParseDetail[]'):src.index('TokenizerParseInfo ParseDetailDict[]')];ops=[]
 for line in table.splitlines():
  if 'PARSE_NAME_AND_HELP'in line:ops.extend((n,'S')for n in('Name','DisplayName','DisplayHelp','DisplayShortHelp'))
  m=re.match(r'\s*\{ "([^"]+)"\s*,\s*TOK_(\w+)\(',line)
  if m:ops.append((m[1],{'STRING':'S','STRINGARRAY':'A','INT':'W','BOOL':'W','BOOLFLAG':'W','F32':'W'}[m[2]]))
 need(len(ops)==47,'complete original schema')
 schema=[x for x in re.findall(r"'([SWA])'",(HERE/'../character-dictionary/salvage_details_schema.inc').read_text())];need(schema==[k for _,k in ops],'complete native grammar order')
 def wire(rows):
  data=[]
  for fields in rows:
   r=b''
   for name,kind in ops:
    v=fields.get(name,-1 if name=='Surface'else b''if kind=='S'else []if kind=='A'else 0)
    r+=text(v)if kind=='S'else word(len(v))+b''.join(text(s)for s in v)if kind=='A'else word(v)
   data.append(word(len(r))+r)
  b=word(len(rows))+b''.join(data);return b'CrypticS'+word(0x326ad4e9)+text(b'Parse6')+text(b'Files1')+word(4)+word(0)+word(len(b))+b
 def f(**kw):return dict(Name=b'Alpha',GroupName=b'Floor_f',**kw)
 def case(label,rows,status=0,original=True):return(label,wire(rows),status,original)
 cases=[('authentic',raw,0,True),case('normal-floor',[f()]),case('mounted-animated',[f(Mounted=1,AnimatedEnt=1)]),case('upper-suffix',[dict(Name=b'Upper',GroupName=b'Ceiling_C')]),case('explicit-overrides',[f(GroupNameUnpowered=b'dim',GroupNameDestroyed=b'*Destroyed',GroupNameMount=b'ExplicitMount',GroupNameUnpoweredMount=b'dIm',GroupNameBaseEdit=b'Editor')]),case('literal-root',[dict(Name=b'Exact',GroupName=b'*Raw_w')]),case('no-suffix',[dict(Name=b'Exact',GroupName=b'Plain',Surface=27)]),case('u8-source-truncation',[f(Mounted=256,AnimatedEnt=257)]),case('short-suffix',[dict(Name=b'Short',GroupName=b'_w')]),case('star-only',[dict(Name=b'EmptyEscaped',GroupName=b'*')]),case('empty-root-explicit-surface',[dict(Name=b'NoRoot',GroupName=b'',Surface=0)]),case('complete-opaque-arrays',[f(Requires=[b'opaque',b''],AuxAllowed=[b'x'],FunctionParams=[b'y'])]),case('ordered-duplicate-names',[f(),dict(Name=b'alpha',GroupName=b'Second_c')]),case('missing-root-stays-persisted',[dict(Name=b'Missing')]),case('name-limit',[dict(Name=b'A'*128,GroupName=b'Raw')],2,False),case('resource-limit',[dict(Name=b'A',GroupName=b'R'*1024)],2,False),case('long-cache-root-no-expansion',[dict(Name=b'A',GroupName=b'R'*1017+b'_f')]),case('nonascii-resource',[dict(Name=b'A',GroupName=b'\xff')],2,False)]
 class Text(C.Structure):_fields_=[('offset',C.c_uint32),('size',C.c_uint32)]
 class Row(C.Structure):_fields_=[('name',Text),('groups',Text*6),('surface',C.c_int32),('mounted',C.c_uint32),('animated',C.c_uint32)]
 class Owner(C.Structure):_fields_=[('sha256',C.c_uint8*32),('provenance',C.c_uint64),('schema_crc',C.c_uint32),('dependencies',C.c_uint32),('count',C.c_uint32),('text_bytes',C.c_uint32),('complete',C.c_uint32),('runtime_generation',C.c_uint32),('actor_authority',C.c_uint32),('rows',Row*4096),('text',C.c_char*524288)]
 def begin(b):
  at=12
  for _ in range(2):n=int.from_bytes(b[at:at+2],'little');at+=2+n+(4-(n+2)%4)%4
  return at+4+int.from_bytes(b[at:at+4],'little')
 def canonical(out):
  b=word(out.count);base=C.addressof(out)+Owner.text.offset
  for i in range(out.count):
   row=out.rows[i];b+=word(row.surface)+word(row.mounted)+word(row.animated)
   for t in[row.name,*row.groups]:b+=word(t.size)+C.string_at(base+t.offset,t.size)
  return b
 proof={'scope':'complete original Details BIN persisted resource projection, copied owner only','source_revision':revision,'source_sha256_raw':before,'authentic_details':{'bytes':len(raw),'sha256':sha(raw)},'original':{},'cases':[],'modes':{},'mutations':{},'world_authority':False,'current_CLIENT_cache_family':False,'geometry_loaded':False,'android_executed':False,'global_memory_or_RSS_fit':False,'old_qualifiers_executed':False}
 def run(label,args,**kw):
  p=subprocess.run(list(map(str,args)),capture_output=True,timeout=60,**kw);(a.output/(label+'.stdout')).write_bytes(p.stdout);(a.output/(label+'.stderr')).write_bytes(p.stderr)
  need(p.returncode==0,label+' failed');return p.stdout
 artifacts={}
 with tempfile.TemporaryDirectory(prefix='coh-bd-resources-')as tmp:
  work=Path(tmp);lib,proof['original']=oracle.build(work);need(lib.resources_sizeof()==C.sizeof(Owner),'original/native host adapter ABI');lines=[];fixtures=[]
  for i,(label,b,status,execute)in enumerate(cases):
   expected=bytes(32)
   if execute:
    out=Owner();buf=C.create_string_buffer(b);need(lib.original_resources(buf,len(b),begin(b),C.byref(out))==1,'original preprocess');expected=hashlib.sha256(canonical(out)).digest()
   lines.append('static const uint8_t input_%u[]={%s};'%(i,','.join(map(str,b))))
   fixtures.append('{input_%u,%u,%u,{%s}}'%(i,len(b),status,','.join(map(str,expected))))
   proof['cases'].append({'name':label,'bytes':len(b),'sha256':sha(b),'status':status,'original_complete_BIN_table_reader_executed':execute,'projection_sha256':expected.hex()if execute else None})
  fp=work/'resource_fixtures.h';fp.write_text('\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+','.join(fixtures)+'};\n');fixture_hash=sha(fp.read_bytes())
  for mode,options in(('release',['-O2','-fstack-usage']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])):
   exe=work/mode;run(mode+'-build',['cc','-std=c99','-pedantic','-Wall','-Wextra','-Werror',*options,'-I'+str(work),HERE/'coh_bd_resources.c',HERE/'test_resources.c','-lcrypto','-o',exe]);h=sha(exe.read_bytes());result=json.loads(run(mode,[exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));need(h==sha(exe.read_bytes()),'binary changed');proof['modes'][mode]={'binary_sha256_pre_post':h,'result':result};artifacts[mode]=exe.read_bytes()
  source=(HERE/'coh_bd_resources.c').read_text()
  replacements={'unnormalized-provider-status':('return (unsigned)status<=COH_STATE?status:COH_INVALID;','return status;'),'skip-source-hash':('if(memcmp(v->sha256,p->expected_sha256,32))return COH_STATE;',''),'wrong-group-slot':('row->groups[j-6]=copy(r,d,b,0)','row->groups[(j-5)%6]=copy(r,d,b,0)'),'wrong-U8-copy':('row->mounted=(uint8_t)u','row->mounted=u'),'invent-surface':('if(j==12)memcpy(&row->surface,&u,4);','if(j==12){memcpy(&row->surface,&u,4);if(row->surface==-1)row->surface=0;}'),'strip-cache-root-escape':('row->groups[j-6]=copy(r,d,b,0)','{row->groups[j-6]=copy(r,d,b,0);if(j==6&&b.size&&b.data[0]==42){row->groups[0].offset++;row->groups[0].size--;}}')}

  for name,(old,new)in replacements.items():
   need(source.count(old)==1,'mutation unique');mp=work/(name+'.c');mp.write_text(source.replace(old,new));exe=work/name;run(name+'-build',['cc','-std=c99','-O2','-I'+str(work),'-I'+str(HERE),mp,HERE/'test_resources.c','-lcrypto','-o',exe]);p=subprocess.run([exe],capture_output=True,timeout=30);(a.output/(name+'.stdout')).write_bytes(p.stdout);(a.output/(name+'.stderr')).write_bytes(p.stderr);need(p.returncode!=0,'mutation survived');proof['mutations'][name]={'rejected':True,'returncode':p.returncode,'mutant_source_sha256':sha(mp.read_bytes())}
  stack=[]
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    if '/coh_bd_resources.c:'in line:
     loc,size,kind=line.split('\t');stack.append({'function':loc.rsplit(':',1)[-1],'bytes':int(size),'kind':kind})
  need(stack and sum(x['bytes']for x in stack)<16384 and all(x['kind']in('static','dynamic,bounded')for x in stack),'module stack bound');proof['native_module_stack']=stack;proof['fixture_header_sha256']=fixture_hash;need(sha(fp.read_bytes())==fixture_hash,'fixture changed')
 with tarfile.open(a.output/'executed-native-artifacts.tar.gz','w:gz')as archive:
  for name,data in artifacts.items():
   info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o755;info.mtime=0;archive.addfile(info,io.BytesIO(data))
 proof['retained_native_artifacts']={'archive_sha256':sha((a.output/'executed-native-artifacts.tar.gz').read_bytes()),'members':{n:{'bytes':len(b),'sha256':sha(b)}for n,b in artifacts.items()}}
 need(before=={str(p.relative_to(ROOT)):sha(p.read_bytes())for p in sorted(source_paths)},'source changed');need(all(p['result']==proof['modes']['release']['result']for p in proof['modes'].values()),'mode mismatch');proof['source_bytes_unchanged']=True;proof['passed']=True;proof['asan_leak_detector_enabled']=False;(a.output/'qualification.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':{k:v['result']for k,v in proof['modes'].items()},'mutations_rejected':len(proof['mutations'])}))
if __name__=='__main__':main()
