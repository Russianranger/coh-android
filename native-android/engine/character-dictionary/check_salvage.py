#!/usr/bin/env python3
"""New complete Salvage/ID/Details-name source qualification only."""
import argparse,ast,ctypes as C,gzip,hashlib,json,os,re,subprocess,sys,tempfile,types,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ARCHIVE='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'
MEMBERS={'data/bin/Salvage.bin':(70568,'bb351fc475d654578d8f613c38a07d2fb8bb05424853114a80c1fccc68b054ee'),'data/bin/InvSalvage.bin':(11284,'eb65b811238a17be8311d882c2b548b734da1e9f65f9af7ab882d468ff4b939c'),'data/bin/details.bin':(401216,'11e5104e0210fa5cbbc910932e5df461a34853e9a30d43f890d31510cdf2ce28')}
def sha(b):return hashlib.sha256(b).hexdigest()
def need(ok,why):
 if not ok:raise ValueError(why)
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,timeout=120,**kw)
 if p.returncode:raise ValueError(p.stdout.decode(errors='replace')[-2000:]+p.stderr.decode(errors='replace')[-6000:])
 return p.stdout
LOCKED={}
def module(n,p):
 p=p.resolve();b=p.read_bytes();need(LOCKED.get(p)==sha(b),'unadmitted helper');m=types.ModuleType(n);m.__file__=str(p);exec(compile(b,str(p),'exec'),m.__dict__);return m

def string(b):return len(b).to_bytes(2,'little')+b+b'\0'*((4-(len(b)+2)%4)%4)
def word(n):return (n&0xffffffff).to_bytes(4,'little')
def wrap(crc,rows):
 r=word(len(rows))+b''.join(word(len(r))+r for r in rows);return b'CrypticS'+word(crc)+string(b'Parse6')+string(b'Files1')+word(4)+word(0)+word(len(r))+r

def parse(raw,kind):
 at=12;records=[]
 def u():
  nonlocal at
  v=int.from_bytes(raw[at:at+4],'little');at+=4;return v
 def text():
  nonlocal at
  n=int.from_bytes(raw[at:at+2],'little');at+=2;b=raw[at:at+n];at+=n+(4-(n+2)%4)%4;return b
 need(raw[:8]==b'CrypticS' and text()==b'Parse6' and text()==b'Files1','cache header');end=at+4+int.from_bytes(raw[at:at+4],'little');u();n=u()
 for _ in range(n):text();u()
 need(at==end,'cache files');begin=at;end=at+4+int.from_bytes(raw[at:at+4],'little');u();count=u()
 for _ in range(count):
  n=u();record=raw[at:at+n];at+=n;records.append(record)
 need(at==end==len(raw),'complete root');return begin,records

def main():
 if not __debug__ or os.environ.get('PYTHONOPTIMIZE'):raise ValueError('Python optimization unsupported')
 ap=argparse.ArgumentParser();ap.add_argument('--actual-caches-zip',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args();need(not a.output.exists(),'new output required')
 revision=run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip()
 helpers=[HERE/'salvage_oracle.py',HERE/'salvage-source-pins.json',HERE/'../costume-inputs/oracle.py',HERE/'../costume-inputs/source-pins.json',HERE/'../costume-inputs/coh_costume_inputs.h',HERE/'../costume-tree/crc_provider.py']
 # Read fixed helper inventories as data before any project helper executes.
 def inventory(p,key):return ast.literal_eval(re.search(r'^'+key+r'=(\[.*\])$',p.read_text(),re.M).group(1))
 originals=list(dict.fromkeys(inventory(helpers[0],'EXTRA')+inventory(helpers[2],'PATHS')+inventory(helpers[-1],'PATHS')))
 paths={p.resolve() for p in helpers}|{ROOT/'upstream/ouroboros'/p for p in originals}|{HERE/n for n in ('coh_salvage.c','coh_salvage.h','salvage_details_schema.inc','test_salvage.c','check_salvage.py','SALVAGE.md')}
 pending=[HERE/'coh_salvage.c',HERE/'test_salvage.c',HERE/'coh_salvage.h',helpers[4]];seen=set()
 while pending:
  p=pending.pop().resolve()
  if p in seen:continue
  seen.add(p);paths.add(p)
  for name in re.findall(r'^#include "([^"]+)"',p.read_text(),re.M):
   q=(p.parent/name).resolve()
   if q.is_file():pending.append(q)
 hashes={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(paths)}
 for p,d in hashes.items():need(sha(run(['git','-C',ROOT,'show',revision+':'+p]))==d,'uncommitted qualification source')
 LOCKED.update({p.resolve():sha(p.read_bytes()) for p in helpers});oracle=module('salvage_original',helpers[0]);oracle.module=module
 h=hashlib.sha256();total=0
 with a.actual_caches_zip.open('rb') as f:
  while True:
   b=f.read(65536)
   if not b:break
   total+=len(b);h.update(b)
 need(total==27071659 and h.hexdigest()==ARCHIVE,'exact donor ZIP');donor=[]
 with zipfile.ZipFile(a.actual_caches_zip) as z:
  for n,(size,digest) in MEMBERS.items():
   need(z.namelist().count(n)==1 and z.getinfo(n).file_size==size,'bounded unique member')
   with z.open(n) as f:b=f.read(524289)
   need(len(b)==size and sha(b)==digest,'exact donor member');donor.append(b)
 # This descriptor is a source-derived complete typed walk, not a byte skip.
 ops=[];source=(ROOT/'upstream/ouroboros/Common/bases/basedata.c').read_text();table=source[source.index('static TokenizerParseInfo ParseDetail[]'):source.index('TokenizerParseInfo ParseDetailDict[]')]
 for line in table.splitlines():
  if 'PARSE_NAME_AND_HELP' in line:ops.extend((n,'S') for n in ('Name','DisplayName','DisplayHelp','DisplayShortHelp'))
  m=re.match(r'\s*\{ "([^"]+)"\s*,\s*TOK_(\w+)\(',line)
  if m:ops.append((m[1],{'STRING':'S','STRINGARRAY':'A','INT':'W','BOOL':'W','BOOLFLAG':'W','F32':'W'}[m[2]]))
 expected='/* Complete persisted ParseDetail field order; source checked by qualifier. */\n'+''.join(" '%s', /* %s */\n"%(op,n) for n,op in ops)
 need((HERE/'salvage_details_schema.inc').read_text()==expected and len(ops)==47,'complete Details schema')
 def detail(name):return b''.join(word(0) if op in ('W','A') else string(name if field=='Name' else b'') for field,op in ops)
 def item(name,tab=b'Tab',workshops=(),open=(),auction=(),display=b'display'):
  fields=(name,display,b'help',b'short',b'icon',tab,b'drop');arrays=(workshops,(b'Reward_Table',),open,auction)
  return b''.join(string(s) for s in fields)+word(1)+word(1)+word(len(arrays[0]))+b''.join(string(s) for s in arrays[0])+word(-3)+b''.join(word(len(v))+b''.join(string(s) for s in v) for v in arrays[1:])+string(b'failed')+b''.join(word(v) for v in (3,100,7,31))+string(b'Product')
 def wire(items,ids,details):return [wrap(0x5b9c4ac0,items),wrap(0x6f0830ea,[word(n)+string(name) for n,name in ids]),wrap(0x326ad4e9,[detail(n) for n in details])]
 alpha=item(b'Alpha',workshops=(b'Workshop_A',));beta=item(b'Beta',tab=b'tAB',workshops=(b'Workshop_B',));base=wire([alpha,beta],[(1,b'Alpha'),(2,b'Beta')],[b'Workshop_A',b'Workshop_B'])
 cases=[('authentic',donor,0,True),('simple',base,0,True),('id-collision',wire([alpha,beta],[(7,b'Alpha'),(7,b'Beta')],[b'Workshop_A',b'Workshop_B']),0,True),('map-first-and-max',wire([alpha,beta],[(2,b'ALPHA'),(99,b'alpha')],[b'Workshop_A',b'Workshop_B']),0,True),('nonpositive-and-removed',wire([alpha,beta],[(-1,b'Alpha'),(0,b'Beta'),(100,b'Removed')],[b'Workshop_A',b'Workshop_B']),0,True),('last-details-winner',wire([alpha],[(1,b'Alpha')],[b'Workshop_A',b'Workshop_A']),0,True),('duplicate-item',wire([alpha,item(b'aLPHa')],[(1,b'Alpha')],[b'Workshop_A']),7,True),('bad-item-name',wire([item(b'Bad-Name')],[(1,b'Bad-Name')],[b'Workshop_A']),7,True),('unresolved-workshop',wire([alpha],[(1,b'Alpha')],[b'Other']),3,False),('open-expression',wire([item(b'Alpha',open=(b'1',))],[(1,b'Alpha')],[]),2,True),('auction-expression',wire([item(b'Alpha',auction=(b'1',))],[(1,b'Alpha')],[]),2,True),('no-positive-ids',wire([item(b'Alpha')],[(0,b'Alpha')],[]),7,True),('item-count-limit',wire([item(b'Alpha')]*1025,[(1,b'Alpha')],[]),4,False),('key-nonascii',wire([item(b'\xff')],[(1,b'Alpha')],[]),2,False),('key-empty',wire([item(b'')],[(1,b'Alpha')],[]),2,False),('id-limit',wire([item(b'Alpha')],[(8192,b'Alpha')],[]),4,False)]
 # Complete source-valid records whose deterministic native comparison work
 # exceeds policy; the original cached StructLink projection remains bounded.
 names=[b'P'*76+('%04d'%k).encode() for k in range(1900)];items=[item(('Salvage%013d'%k).encode(),workshops=(names[0],)) for k in range(512)];ids=[(k+1,('Salvage%013d'%k).encode()) for k in range(512)];cases.append(('work-policy',wire(items,ids,names),4,True))
 # Last admitted slot and raw link spelling must survive the complete original
 # finalizers; link text is observed independently from the selected Name.
 cases.append(('last-valid-id',wire([item(b'Alpha')],[(8191,b'Alpha')],[]),0,True))
 cases.append(('link-spelling-and-last-details',wire([item(b'Alpha',workshops=(b'wOrKsHoP_a',))],[(1,b'Alpha')],[b'Workshop_A',b'WORKSHOP_A']),0,True))
 cases.append(('last-valid-key',wire([item(b'Alpha',tab=b'T'*127)],[(1,b'Alpha')],[]),0,True))
 cases.append(('last-valid-string',wire([item(b'Alpha',display=b'S'*11999)],[(1,b'Alpha')],[]),0,True))
 cases.append(('last-valid-array',wire([item(b'Alpha',workshops=(b'Workshop_A',)*8191)],[(1,b'Alpha')],[b'Workshop_A']),0,True))
 # These inputs are complete grammar but exceed native output-adapter policy.
 # Do not call an original projection whose fixed result has the same caps.
 cases.append(('array-policy',wire([item(b'Alpha',workshops=(b'Workshop_A',)*8193)],[(1,b'Alpha')],[b'Workshop_A']),4,False))
 cases.append(('string-policy',wire([item(b'Alpha',display=b'S'*12000)],[(1,b'Alpha')],[]),4,False))
 def longrow():
  return b''.join(string(s) for s in (b'Alpha',*[b'L'*11000]*4,b'Tab',b'D'*11000))+word(1)+word(1)+word(0)+word(0)+word(0)*3+string(b'failed')+word(0)*4+string(b'Product')
 cases.append(('text-policy',wire([longrow()]*5,[(1,b'Alpha')],[]),4,False))
 checks={};binaries={};lines=[];fixture_rows=[];recorded=[];blobs={};stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-salvage-') as tmp:
  work=Path(tmp);ow=work/'oracle';ow.mkdir();lib,original=oracle.build(ROOT,ow);lib.original_salvage_sizeof.restype=C.c_size_t;owner_bytes=lib.original_salvage_sizeof();need([lib.original_salvage_crc(k)&0xffffffff for k in range(3)]==[0x5b9c4ac0,0x6f0830ea,0x326ad4e9],'original schema CRCs')
  guard=[]
  for flags,env in [(['-O'],{}),(['-OO'],{}),([] ,{'PYTHONOPTIMIZE':'1'})]:
   absent=work/'must-not-read.zip';p=subprocess.run([sys.executable,*flags,__file__,'--actual-caches-zip',str(absent),'--output',str(work/'must-not-write')],capture_output=True,env=dict(os.environ,**env),timeout=10);need(p.returncode!=0 and not p.stdout and b'Python optimization unsupported' in p.stderr and not (work/'must-not-write').exists(),'optimization guard');guard.append(True)
  for name,bodies,status,execute in cases:
   expected_hash=b'\0'*32;original_ok=None;equal=[];original_errors=None;roundtrip_sizes=[]
   if execute:
    buffers=[C.create_string_buffer(b) for b in bodies];pointers=(C.c_void_p*3)(*[C.addressof(b) for b in buffers]);sizes=(C.c_uint*3)(*[len(b) for b in bodies]);begins=(C.c_uint*3)(*[parse(b,k)[0] for k,b in enumerate(bodies)]);project=C.create_string_buffer(owner_bytes);roundtrips=[C.create_string_buffer(len(b)) for b in bodies];rp=(C.c_void_p*3)(*[C.addressof(b) for b in roundtrips]);original_ok=lib.original_salvage(pointers,sizes,begins,project,rp);original_errors=lib.original_salvage_error_count();roundtrip_sizes=[lib.original_salvage_roundtrip_size(k) for k in range(3)];equal=[r.raw[:len(b)]==b for r,b in zip(roundtrips,bodies)];need(all(equal) and roundtrip_sizes==list(sizes),'complete original roundtrip');expected_hash=bytes.fromhex(sha(project.raw));need(status!=0 or original_ok==1,'original finalizer result')
    if name in ('duplicate-item','bad-item-name'):need(original_ok==0 and original_errors>0,'original finalization error')
   labels=[]
   for body in bodies:
    digest=sha(body)
    if digest not in blobs:
     label='body_'+str(len(blobs));blobs[digest]=label;lines.append('static const uint8_t '+label+'[]={'+','.join(map(str,body))+'};')
    labels.append(blobs[digest])
   fixture_rows.append('{{'+','.join(labels)+'},{'+','.join(str(len(b)) for b in bodies)+'},'+str(status)+',{'+','.join(map(str,expected_hash))+'}}')
   recorded.append({'name':name,'input_sha256':[sha(b) for b in bodies],'input_bytes':[len(b) for b in bodies],'expected_status':status,'original_executed':execute,'original_finalizer_success':original_ok,'original_error_count':original_errors,'original_roundtrip_equal':equal,'original_roundtrip_bytes':roundtrip_sizes,'expected_projection_sha256':expected_hash.hex() if execute else None})
  fixture='\n'.join(lines)+'\nstatic const Fixture fixtures[]={'+','.join(fixture_rows)+'};\n';(work/'salvage-fixtures.h').write_text(fixture)
  def unchanged():
   need(run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip()==revision,'HEAD changed');need(hashes=={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(paths)},'source changed');need(sha((work/'salvage-fixtures.h').read_bytes())==sha(fixture.encode()),'fixture changed')
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
   unchanged();exe=work/mode;run(['cc','-std=c99','-pedantic','-Wall','-Wextra','-Werror',*flags,'-I'+str(work),HERE/'coh_salvage.c',HERE/'test_salvage.c','-lcrypto','-o',exe]);before=sha(exe.read_bytes());checks[mode]=json.loads(run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));need(sha(exe.read_bytes())==before,'executable changed');binaries[mode]=before;unchanged()
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,size,kind=line.split('\t')
    if '/coh_salvage.c:' in location:stack.append({'function':location.split('coh_salvage.c:',1)[1],'bytes':int(size),'kind':kind})
  need(stack and sum(x['bytes'] for x in stack)<16384 and all(x['kind'] in ('static','dynamic,bounded') for x in stack),'native stack reserve');unchanged()
 need(all(v==checks['release'] for v in checks.values()),'mode result mismatch')
 result={'schema':'coh-complete-salvage-focused-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'donor':{'bytes':27071659,'sha256':ARCHIVE,'members':{n:{'bytes':size,'sha256':digest} for n,(size,digest) in MEMBERS.items()},'stream_chunk_bytes':65536},'original':original,'cases':recorded,'checks':checks,'binary_sha256_pre_and_post':binaries,'optimized_python_refusals':guard,'native_stack':stack,'fixture_header_sha256':sha(fixture.encode()),'policy_budget_bytes':16777216,'test_scaffolding_RSS_admitted':False,'Details_name_identity_only':True,'Details_gameplay_finalizers':False,'geometry_or_resources':False,'current_cache_family_verified':False,'runtime_generation':False,'actor_authority':False,'ACK_authority':False,'old_qualifier_entrypoints_executed':False,'asan_leak_detector_enabled':False,'android_executed':False}
 with a.output.open('xb') as f:
  with gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as z:z.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'checks':checks,'source_files':len(hashes)}))
if __name__=='__main__':main()
