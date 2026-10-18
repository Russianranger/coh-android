#!/usr/bin/env python3
"""Focused retained Proficiency/ID source finalization, no old qualifier entrypoint."""
import argparse,ctypes as C,gzip,hashlib,json,os,re,struct,subprocess,tempfile,types,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
DONOR_SHA='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'
MEMBERS={'data/bin/Proficiencies.bin':(2748,'24837a0390efcc3f7be2696c49514998f74df0aca9c07de6ec5c24fd8f32188b'),'data/bin/ProficiencyIds.bin':(704,'6d3e893c0b7591935aad9c7422bc681e2f42af5c5850d79ae50d5b3b69c4002f')}
def sha(b):return hashlib.sha256(b).hexdigest()
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120,**kw)
 if p.returncode:raise RuntimeError(p.stdout[-4000:]+p.stderr[-8000:])
 return p.stdout
LOCKED={}
def module(n,p):
 p=p.resolve();b=p.read_bytes()
 if LOCKED.get(p)!=sha(b):raise ValueError('unadmitted helper')
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(b,str(p),'exec'),m.__dict__);return m
def string(b):return struct.pack('<H',len(b))+b+b'\0'*((4-(len(b)+2)%4)%4)
def wrap(crc,records):
 f=struct.pack('<I',0);r=struct.pack('<I',len(records))+b''.join(struct.pack('<I',len(x))+x for x in records)
 return b'CrypticS'+struct.pack('<I',crc)+string(b'Parse6')+string(b'Files1')+struct.pack('<I',len(f))+f+struct.pack('<I',len(r))+r
def decode(raw,kind):
 at=12
 def word():
  nonlocal at
  n=struct.unpack_from('<I',raw,at)[0];at+=4;return n
 def text():
  nonlocal at
  n=struct.unpack_from('<H',raw,at)[0];at+=2;b=raw[at:at+n];at+=n+(4-(n+2)%4)%4;return b
 assert raw[:8]==b'CrypticS' and text()==b'Parse6' and text()==b'Files1'
 end=at+4+struct.unpack_from('<I',raw,at)[0];word();deps=word()
 for _ in range(deps):text();word()
 assert at==end;begin=at;end=at+4+struct.unpack_from('<I',raw,at)[0];word();n=word();rows=[]
 for _ in range(n):
  rend=at+4+struct.unpack_from('<I',raw,at)[0];word()
  if kind:rows.append((struct.unpack('<i',struct.pack('<I',word()))[0],text()))
  else:rows.append(tuple(text() for _ in range(5))+(struct.unpack('<i',struct.pack('<I',word()))[0],struct.unpack('<i',struct.pack('<I',word()))[0]))
  assert at==rend
 assert at==end==len(raw)
 return begin,rows

def main():
 if not __debug__:raise ValueError('Python optimization unsupported')
 ap=argparse.ArgumentParser();ap.add_argument('--actual-caches-zip',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 revision=run(['git','-C',ROOT,'rev-parse','HEAD']).strip()
 helpers=[HERE/'proficiencies_oracle.py',HERE/'../costume-inputs/oracle.py',HERE/'../costume-inputs/source-pins.json',HERE/'../costume-inputs/coh_costume_inputs.h',HERE/'../costume-tree/crc_provider.py']
 # Fixed source inventory is read without importing any project helper.
 smallpaths=re.search(r'^PATHS=(\[.*\])$',helpers[1].read_text(),re.M).group(1);import ast
 extrapaths=re.search(r'^EXTRA=(\[.*\])$',helpers[0].read_text(),re.M).group(1)
 crcpaths=re.search(r'^PATHS=(\[.*\])$',helpers[-1].read_text(),re.M).group(1)
 original=list(dict.fromkeys(ast.literal_eval(smallpaths)+ast.literal_eval(extrapaths)+ast.literal_eval(crcpaths)))
 paths={p.resolve() for p in helpers}|{ROOT/'upstream/ouroboros'/p for p in original}|{HERE/n for n in ('coh_proficiencies.c','coh_proficiencies.h','test_proficiencies.c','check_proficiencies.py','PROFICIENCIES.md')}
 pending=[HERE/'coh_proficiencies.c',HERE/'test_proficiencies.c']+[p for p in helpers if p.suffix=='.h'];seen=set()
 while pending:
  p=pending.pop().resolve()
  if p in seen:continue
  seen.add(p);paths.add(p)
  for inc in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):
   q=(p.parent/inc).resolve()
   if q.is_file() and q not in seen:pending.append(q)
 hashes={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(paths)}
 for p,d in hashes.items():
  if sha(subprocess.check_output(['git','-C',ROOT,'show',revision+':'+p]))!=d:raise ValueError('source not committed')
 LOCKED.update({p.resolve():sha(p.read_bytes()) for p in helpers});oracle=module('proficiencies_oracle',helpers[0]);oracle.module=module
 h=hashlib.sha256();size=0
 with a.actual_caches_zip.open('rb') as f:
  while True:
   b=f.read(65536)
   if not b:break
   h.update(b);size+=len(b)
 assert size==27071659 and h.hexdigest()==DONOR_SHA
 donor=[]
 with zipfile.ZipFile(a.actual_caches_zip) as z:
  for n,(size,digest) in MEMBERS.items():
   assert z.namelist().count(n)==1 and z.getinfo(n).file_size==size
   with z.open(n) as f:raw=f.read(65537)
   assert len(raw)==size and sha(raw)==digest;donor.append(raw)
 dbegin,defs=decode(donor[0],0);ibegin,ids=decode(donor[1],1)
 cases=[('authentic',defs,ids,0,True)]
 adef=(b'Alpha',b'display',b'help',b'short',b'icon',-9,99);bdef=(b'Beta',b'',b'',b'',b'',2,3)
 cases.extend([
 ('empty-definitions',[],ids,0,True),('case-duplicate',[adef,(b'aLPHa',)+adef[1:],bdef],[(3,b'ALPHA'),(5,b'Beta')],0,True),
 ('id-collision',[adef,bdef],[(7,b'Alpha'),(7,b'Beta')],0,True),
 ('first-map-name-and-max',[adef,bdef],[(2,b'alpha'),(18,b'ALPHA')],0,True),
 ('nonpositive-map',[adef,bdef],[(-1,b'Alpha'),(0,b'Beta'),(4,b'removed')],0,True),
 ('removed-hole',[adef],[(100,b'removed'),(2,b'Alpha')],0,True),
 ('last-slot',[adef],[(4095,b'Alpha')],0,True),('fallback-last',[adef],[(4094,b'removed')],0,True),
 ('fallback-limit',[adef],[(4095,b'removed')],4,True),('id-limit',[adef],[(4096,b'Alpha')],4,True),
 ('full-512',[(('Name%03d'%k).encode(),b'',b'',b'',b'',0,4) for k in range(512)],[(k+1,('Name%03d'%k).encode()) for k in range(512)],0,True),
 ('defs-limit',[adef]*513,[(1,b'Alpha')],4,True),('ids-limit',[adef],[(1,b'Alpha')]*513,4,True),
 ('work-limit',[(b'P'*64+('%06d'%k).encode(),b'',b'',b'',b'',0,0) for k in range(512)],[(k+1,b'P'*64+('%06d'%(1000+k)).encode()) for k in range(380)],4,True),
 ('text-limit',[(b'P'*64+('%06d'%k).encode(),b'',b'',b'',b'',0,0) for k in range(512)],[(k+1,b'P'*64+('%06d'%(1000+k)).encode()) for k in range(400)],4,True),
 ('nonascii-name',[(b'\xff',)+adef[1:]],[(1,b'Alpha')],2,False),('empty-name',[(b'',)+adef[1:]],[(1,b'Alpha')],2,False),
 ('all-map-ignored',[adef],[(0,b'Alpha')],7,True),
 ('oversize-string',[(b'A'*260,)+adef[1:]],[(1,b'Alpha')],4,False)])
 checks={};bins={};stacks=[];recorded=[];lines=[];entries=[]
 with tempfile.TemporaryDirectory(prefix='coh-proficiencies-') as tmp:
  work=Path(tmp);ow=work/'oracle';ow.mkdir();lib,proof=oracle.build(ROOT,ow)
  assert lib.original_proficiency_crc(0)&0xffffffff==0x5b3f53ab and lib.original_proficiency_crc(1)&0xffffffff==0x6f0830ea
  for k,(name,dr,ir,refused,original_exec) in enumerate(cases):
   d=donor[0] if k==0 else wrap(0x5b3f53ab,[b''.join(string(x) for x in r[:5])+struct.pack('<ii',*r[5:]) for r in dr])
   i=donor[1] if k==0 else wrap(0x6f0830ea,[struct.pack('<i',r[0])+string(r[1]) for r in ir])
   words=[]
   if original_exec:
    out=(C.c_uint*16384)();do=C.create_string_buffer(65536);io=C.create_string_buffer(65536)
    n=lib.original_proficiencies(d,len(d),decode(d,0)[0],i,len(i),decode(i,1)[0],out,do,io)
    assert do.raw[:len(d)]==d and io.raw[:len(i)]==i;words=list(out[:n]);assert words[3]==len(dr)
   def arr(label,data):
    lines.append('static const unsigned char '+label+'[]={'+','.join(map(str,data or b'\0'))+'};');return label
   dw=arr('d'+str(k),d);iw=arr('i'+str(k),i)
   lines.append('static const uint32_t w'+str(k)+'[]={'+','.join(map(str,words or [0]))+'};')
   flat=b''.join(x+b'\0' for r in dr for x in r[:5])+b''.join(r[1]+b'\0' for r in ir);tx=arr('t'+str(k),flat)
   meta=[v&0xffffffff for r in dr for v in r[5:]]+[r[0]&0xffffffff for r in ir];lines.append('static const uint32_t m'+str(k)+'[]={'+','.join(map(str,meta or [0]))+'};')
   entries.append('{'+','.join((dw,str(len(d)),iw,str(len(i)),str(refused),'w'+str(k),tx,'m'+str(k),str(len(dr)),str(len(ir))))+'}')
   recorded.append({'name':name,'definitions_sha256':sha(d),'idmap_sha256':sha(i),'definitions_bytes':len(d),'idmap_bytes':len(i),'expected_status':refused,'original_executed':original_exec,'original_projection':words})
  fixture='\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+','.join(entries)+'};\n';(work/'fixtures.h').write_text(fixture)
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
   exe=work/mode;run(['cc','-std=c99','-pedantic','-Wall','-Wextra','-Werror',*flags,'-I'+str(work),HERE/'coh_proficiencies.c',HERE/'test_proficiencies.c','-lcrypto','-o',exe]);checks[mode]=json.loads(run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));bins[mode]=sha(exe.read_bytes())
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    loc,n,kind=line.split('\t')
    if '/coh_proficiencies.c:' in loc:stacks.append({'function':loc.split('coh_proficiencies.c:',1)[1],'bytes':int(n),'kind':kind})
  assert stacks and sum(x['bytes'] for x in stacks)<8192 and all(x['kind'] in ('static','dynamic,bounded') for x in stacks)
 assert all(v==checks['release'] for v in checks.values())
 assert run(['git','-C',ROOT,'rev-parse','HEAD']).strip()==revision
 assert hashes=={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(paths)}
 result={'schema':'coh-proficiencies-complete-focused-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'input_archive':{'bytes':27071659,'sha256':DONOR_SHA,'members':{n:{'bytes':v[0],'sha256':v[1]} for n,v in MEMBERS.items()},'stream_chunk_bytes':65536},'original':proof,'cases':recorded,'checks':checks,'binary_sha256':bins,'native_stack':stacks,'fixture_header_sha256':sha(fixture.encode()),'policy_budget_bytes':524288,'runtime_generation':False,'actor_authority':False,'original_stash_engine_executed':False,'original_parse_table_crc_recomputed':True,'asan_leak_detector_enabled':False,'android_executed':False,'old_qualifiers_executed':False}
 with a.output.open('xb') as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z:z.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'source_files':len(hashes)}))
if __name__=='__main__':main()
