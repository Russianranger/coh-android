#!/usr/bin/env python3
"""Only the new complete BaseDetail inventory identity qualification."""
import argparse,ast,ctypes as C,gzip,hashlib,json,os,re,subprocess,sys,tempfile,types,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ARCHIVE='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'
MEMBERS={'data/bin/Salvage.bin':(70568,'bb351fc475d654578d8f613c38a07d2fb8bb05424853114a80c1fccc68b054ee'),'data/bin/InvSalvage.bin':(11284,'eb65b811238a17be8311d882c2b548b734da1e9f65f9af7ab882d468ff4b939c'),'data/bin/details.bin':(401216,'11e5104e0210fa5cbbc910932e5df461a34853e9a30d43f890d31510cdf2ce28'),'data/bin/InvBaseDetail.bin':(77652,'80990b0300deab77613b2ab8a0abf56ecbe4e14840346a79fad17283d228e75d')}
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,s):
 if not ok:raise ValueError(s)
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,timeout=120,**kw)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')[-2000:]+p.stderr.decode(errors='replace')[-5000:])
 return p.stdout
LOCKED={}
def module(n,p):
 p=p.resolve();b=p.read_bytes();need(LOCKED.get(p)==sha(b),'unadmitted helper');m=types.ModuleType(n);m.__file__=str(p);exec(compile(b,str(p),'exec'),m.__dict__);return m

def main():
 if not __debug__ or os.environ.get('PYTHONOPTIMIZE'):raise ValueError('Python optimization unsupported')
 ap=argparse.ArgumentParser();ap.add_argument('--actual-caches-zip',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args();need(not a.output.exists(),'new output required');revision=run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip()
 manifest=json.loads((HERE/'basedetail-inventory-source-pins.json').read_bytes())
 paths={ROOT/'upstream/ouroboros'/p for p in manifest['source_sha256_raw']}|{ROOT/p for p in manifest['helper_sha256_raw']}|{HERE/p for p in ('coh_basedetail_inventory.c','coh_basedetail_inventory.h','basedetail_inventory_oracle.py','basedetail-inventory-source-pins.json','check_basedetail_inventory.py','test_basedetail_inventory.c','BASEDETAIL_INVENTORY.md','coh_salvage.c','coh_salvage.h','salvage_details_schema.inc')}
 pending=[HERE/p for p in ('coh_basedetail_inventory.c','test_basedetail_inventory.c','coh_salvage.c')];seen=set()
 while pending:
  p=pending.pop().resolve()
  if p in seen:continue
  seen.add(p);paths.add(p)
  for n in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):
   q=(p.parent/n).resolve()
   if q.is_file():pending.append(q)
 paths={p.resolve() for p in paths};hashes={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(paths)}
 for p,d in hashes.items():need(sha(run(['git','-C',ROOT,'show',revision+':'+p]))==d,'uncommitted source')
 LOCKED.update({(ROOT/p).resolve():d for p,d in manifest['helper_sha256_raw'].items()});p=HERE/'basedetail_inventory_oracle.py';LOCKED[p]=sha(p.read_bytes());oracle=module('basedetail_original',p);oracle.module=module
 total=0;h=hashlib.sha256()
 with a.actual_caches_zip.open('rb') as f:
  while True:
   b=f.read(65536)
   if not b:break
   total+=len(b);h.update(b)
 need(total==27071659 and h.hexdigest()==ARCHIVE,'exact donor');donor=[]
 with zipfile.ZipFile(a.actual_caches_zip) as z:
  for n,(size,digest) in MEMBERS.items():
   need(z.namelist().count(n)==1 and z.getinfo(n).file_size==size,'bounded unique member')
   with z.open(n) as f:b=f.read(524289)
   need(len(b)==size and sha(b)==digest,'exact member');donor.append(b)
 def word(n):return(n&0xffffffff).to_bytes(4,'little')
 def text(b):return len(b).to_bytes(2,'little')+b+b'\0'*((4-(len(b)+2)%4)%4)
 def wrap(crc,rows):
  r=word(len(rows))+b''.join(word(len(b))+b for b in rows);return b'CrypticS'+word(crc)+text(b'Parse6')+text(b'Files1')+word(4)+word(0)+word(len(r))+r
 ops=[];source=(ROOT/'upstream/ouroboros/Common/bases/basedata.c').read_text();table=source[source.index('static TokenizerParseInfo ParseDetail[]'):source.index('TokenizerParseInfo ParseDetailDict[]')]
 for line in table.splitlines():
  if 'PARSE_NAME_AND_HELP' in line:ops.extend((n,'S')for n in ('Name','DisplayName','DisplayHelp','DisplayShortHelp'))
  m=re.match(r'\s*\{ "([^"]+)"\s*,\s*TOK_(\w+)\(',line)
  if m:ops.append((m[1],{'STRING':'S','STRINGARRAY':'A','INT':'W','BOOL':'W','BOOLFLAG':'W','F32':'W'}[m[2]]))
 need(len(ops)==47,'complete Details schema')
 def wire(names,rows):
  # Complete minimal source producer; all persisted Salvage fields are present.
  s=b''.join(text(b'Alpha' if k==0 else b'Tab' if k==5 else b'') for k in range(7))+word(0)*2+word(0)+word(0)+word(0)*3+text(b'')+word(0)*4+text(b'')
  details=wrap(0x326ad4e9,[b''.join(text(name if n=='Name' else b'')if op=='S' else word(0)for n,op in ops)for name in names]);ids=wrap(0x6f0830ea,[word(i)+text(n)for i,n in rows]);return[wrap(0x5b9c4ac0,[s]),wrap(0x6f0830ea,[word(1)+text(b'Alpha')]),details,ids]
 cases=[('authentic',donor,0,True),('simple',wire([b'Alpha',b'Beta'],[(1,b'Alpha'),(2,b'Beta')]),0,True),('duplicate-definition-first',wire([b'Alpha',b'aLPHa'],[(1,b'Alpha')]),0,True),('id-collision-last',wire([b'Alpha',b'Beta'],[(7,b'Alpha'),(7,b'Beta')]),0,True),('ID-name-first-max-all',wire([b'Alpha',b'Beta'],[(1,b'ALPHA'),(100,b'alpha')]),0,True),('removed-and-nonpositive',wire([b'Alpha',b'Beta'],[(-1,b'Alpha'),(0,b'Beta'),(100,b'Removed')]),0,True),('no-positive-ids',wire([b'Alpha'],[(0,b'Alpha')]),7,True),('no-definitions',wire([],[(100,b'Removed')]),0,True),('last-valid-id',wire([b'Alpha'],[(8191,b'Alpha')]),0,True),('ID-limit',wire([b'Alpha'],[(8192,b'Alpha')]),4,False),('fallback-ID-limit',wire([b'Alpha'],[(8191,b'Removed')]),4,False),('ID-row-limit',wire([b'Alpha'],[(1,b'Alpha')]*4097),4,False),('ID-nonascii',wire([b'Alpha'],[(1,b'\xff')]),2,False),('ID-empty',wire([b'Alpha'],[(1,b'')]),2,False),('ID-key-limit',wire([b'Alpha'],[(1,b'A'*128)]),2,True)]
 cases.append(('last-valid-ID-rows',wire([b'Alpha'],[(1,b'Alpha')]*4096),0,True))
 cases.append(('last-valid-ID-key',wire([b'Alpha'],[(1,b'A'*127)]),0,True))
 names=[b'D'*76+('%04d'%i).encode()for i in range(1000)];cases.append(('work-policy',wire(names,[(i+1,n)for i,n in enumerate(names)]),4,True))
 names=[b'T'*123+('%04d'%i).encode()for i in range(1200)];cases.append(('text-policy',wire(names,[(i+1,b'I'*123+('%04d'%i).encode())for i in range(900)]),4,False))
 checks={};binaries={};recorded=[];blobs={};lines=[];rows=[];stack=[]
 def root_begin(b):
  at=12
  for _ in range(2):
   n=int.from_bytes(b[at:at+2],'little');at+=2+n+(4-(n+2)%4)%4
  return at+4+int.from_bytes(b[at:at+4],'little')
 with tempfile.TemporaryDirectory(prefix='coh-basedetail-')as tmp:
  work=Path(tmp);ow=work/'oracle';ow.mkdir();lib,original=oracle.build(ROOT,ow);need(lib.original_salvage_crc(1)&0xffffffff==0x6f0830ea,'original ID CRC');need(lib.original_salvage_crc(2)&0xffffffff==0x326ad4e9,'original Details CRC');owner_bytes=lib.original_basedetail_sizeof();guard=[]
  for flags,env in [(['-O'],{}),(['-OO'],{}),([] ,{'PYTHONOPTIMIZE':'1'})]:
   p=subprocess.run([sys.executable,*flags,__file__,'--actual-caches-zip',str(work/'absent'),'--output',str(work/'must-not-write')],capture_output=True,env=dict(os.environ,**env),timeout=10);need(p.returncode!=0 and not p.stdout and b'Python optimization unsupported'in p.stderr and not(work/'must-not-write').exists(),'optimization guard');guard.append(True)
  for name,bodies,status,execute in cases:
   expected=b'\0'*32;ok=None;equal=[]
   if execute:
    d,i=bodies[2:];db=C.create_string_buffer(d);ib=C.create_string_buffer(i);dr=C.create_string_buffer(len(d));ir=C.create_string_buffer(len(i));out=C.create_string_buffer(owner_bytes);ok=lib.original_basedetail(db,len(d),root_begin(d),ib,len(i),root_begin(i),out,dr,ir);equal=[dr.raw==d,ir.raw==i];need(all(equal),'whole original roundtrip');need(status!=0 or ok==1,'source finalizer result');expected=bytes.fromhex(sha(out.raw))
   labels=[]
   for b in bodies:
    h=sha(b)
    if h not in blobs:
     label='body_'+str(len(blobs));blobs[h]=label;lines.append('static const uint8_t '+label+'[]={'+','.join(map(str,b))+'};')
    labels.append(blobs[h])
   rows.append('{{'+','.join(labels)+'},{'+','.join(str(len(b))for b in bodies)+'},'+str(status)+',{'+','.join(map(str,expected))+'}}');recorded.append({'name':name,'input_sha256':[sha(b)for b in bodies],'input_bytes':[len(b)for b in bodies],'expected_status':status,'original_executed':execute,'original_attrib_finalizer_success':ok,'original_full_roundtrip_equal':equal,'expected_projection_sha256':expected.hex()if execute else None})
  fixture='\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+','.join(rows)+'};\n';fp=work/'basedetail-fixtures.h';fp.write_text(fixture)
  def unchanged():
   need(run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip()==revision,'HEAD changed');need(hashes=={str(p.relative_to(ROOT)):sha(p.read_bytes())for p in sorted(paths)},'source changed');need(sha(fp.read_bytes())==sha(fixture.encode()),'fixture changed')
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else []):
   unchanged();exe=work/mode;run(['cc','-std=c99','-pedantic','-Wall','-Wextra','-Werror',*flags,'-I'+str(work),HERE/'coh_salvage.c',HERE/'coh_basedetail_inventory.c',HERE/'test_basedetail_inventory.c','-lcrypto','-o',exe]);before=sha(exe.read_bytes());checks[mode]=json.loads(run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));need(sha(exe.read_bytes())==before,'executable changed');binaries[mode]=before;unchanged()
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    loc,size,kind=line.split('\t')
    if '/coh_basedetail_inventory.c:'in loc:stack.append({'function':loc.split('coh_basedetail_inventory.c:',1)[1],'bytes':int(size),'kind':kind})
  need(stack and sum(x['bytes']for x in stack)<16384 and all(x['kind']in('static','dynamic,bounded')for x in stack),'new module stack reserve');unchanged()
 need(all(v==checks['release']for v in checks.values()),'mode mismatch')
 result={'schema':'coh-complete-basedetail-inventory-focused-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'donor':{'bytes':27071659,'sha256':ARCHIVE,'members':{n:{'bytes':size,'sha256':d}for n,(size,d)in MEMBERS.items()},'stream_chunk_bytes':65536},'original':original,'cases':recorded,'checks':checks,'binary_sha256_pre_and_post':binaries,'fixture_header_sha256':sha(fixture.encode()),'native_stack_new_module':stack,'optimized_python_refusals':guard,'policy_budget_bytes':16777216,'fresh_raw_dictionary_finalization_only':True,'original_over_native_projection_limit_not_executed':True,'source_owner_input_reproduced_by_actual_coh_salvage_read':True,'test_scaffolding_RSS_admitted':False,'original_oracle_sanitized':False,'asan_leak_detector_enabled':False,'Details_geometry_or_gameplay':False,'source_packet_dispatcher_executed':False,'current_cache_family':False,'current_generation':False,'actor_authority':False,'ACK_authority':False,'old_qualifier_entrypoints_executed':False,'android_executed':False}
 with a.output.open('xb')as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0)as z:z.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'source_files':len(hashes)}))
if __name__=='__main__':main()
