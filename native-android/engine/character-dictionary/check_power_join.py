#!/usr/bin/env python3
"""Bounded three-cache join and exact original forward/backpointer projections."""
import argparse,ctypes as C,gzip,hashlib,json,os,re,struct,subprocess,tempfile,types,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];LOCKED={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def module(name,path):
 path=path.resolve();body=path.read_bytes();assert LOCKED[path]==hashlib.sha256(body).hexdigest(),'helper changed before execution'
 m=types.ModuleType(name);m.__file__=str(path);exec(compile(body,str(path),'exec'),m.__dict__);return m
def run(args,**kw):
 r=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=240,**kw)
 if r.returncode:raise RuntimeError(str(args)+'\n'+r.stdout[-4000:]+r.stderr[-6000:])
 return r.stdout
def pascal(text):
 b=text.encode('ascii');return struct.pack('<H',len(b))+b+bytes((4-(len(b)+2)%4)%4)
def container(crc,records):
 body=struct.pack('<I',len(records))+b''.join(records)
 return b'CrypticS'+struct.pack('<I',crc)+pascal('Parse6')+pascal('Files1')+struct.pack('<II',4,0)+struct.pack('<I',len(body))+body
def rec(body):return struct.pack('<I',len(body))+body
def set_cache(specs,fields):
 records=[]
 for name,refs in specs:
  body=bytearray()
  for i,f in enumerate(fields):
   if f['kind']==1:body.extend(pascal(name if i==1 else ''))
   elif f['kind']==2:body.extend(struct.pack('<I',len(refs)if i==21 else 0));body.extend(b''.join(map(pascal,refs))if i==21 else b'')
   else:body.extend(struct.pack('<I',0))
  records.append(rec(body))
 return container(0x2fe0d52d,records)
def category_cache(specs):return container(0x59248ecb,[rec(b''.join(map(pascal,['fixture',name,'','','']))+struct.pack('<I',len(refs))+b''.join(map(pascal,refs))+struct.pack('<I',0))for name,refs in specs])
CRC_TABLE=[]
for i in range(256):
 h=i
 for _ in range(8):h=(h>>1)^(0x82f63b78 if h&1 else 0)
 CRC_TABLE.append(h)
def crc(name):
 h=0
 for b in name.lower().replace('\\','/').encode('ascii'):h=CRC_TABLE[(h^b)&255]^(h>>8)
 return h
def read_string(raw,at):
 n=struct.unpack_from('<H',raw,at)[0];return raw[at+2:at+2+n].decode('ascii'),at+((n+2+3)//4*4)
def replace_power(first,full,short):
 _,at=read_string(first,4);at+=4;source,at=read_string(first,at);_,at=read_string(first,at)
 return rec(pascal(full)+struct.pack('<I',crc(full))+pascal(source)+pascal(short)+first[at:])
def independent(cats,sets,powers):
 sm={};pm={}
 for i,(name,_)in enumerate(sets):sm.setdefault(name.lower(),i)
 for i,(name,_)in enumerate(powers):pm.setdefault(crc(name),i)
 categorysets=[];links={};alternate=0;errors=[]
 for ci,(_,refs)in enumerate(cats):
  for ri,name in enumerate(refs):
   if name.lower()not in sm:errors.append({'kind':'missing-set','category':ci,'reference':ri,'name':name});continue
   si=sm[name.lower()];categorysets.append(si)
   if si in links:continue
   joined=[]
   for pi,declared in enumerate(sets[si][1]):
    if crc(declared)not in pm:errors.append({'kind':'missing-declared','set':si,'reference':pi,'name':declared});continue
    raw=pm[crc(declared)];full=sets[si][0]+'.'+powers[raw][1];chosen=raw
    if full!=powers[raw][0]:
     alternate+=1
     if crc(full)not in pm:errors.append({'kind':'missing-alternate','set':si,'reference':pi,'name':full});continue
     chosen=pm[crc(full)]
    joined.append((raw,chosen))
   links[si]=joined
 setparents=[0xffffffff]*len(sets);powparents=[0xffffffff]*len(powers)
 for ci,(_,refs)in reversed(list(enumerate(cats))):
  for name in reversed(refs):
   si=sm.get(name.lower())
   if si is None:continue
   setparents[si]=ci
   for _,pi in reversed(links[si]):powparents[pi]=si
 return dict(categorysets=categorysets,links=links,setparents=setparents,powparents=powparents,alternate=alternate,errors=errors)
class CatSpec(C.Structure):_fields_=[('name',C.c_char_p),('n',C.c_uint),('refs',C.POINTER(C.c_char_p))]
class SetSpec(C.Structure):_fields_=CatSpec._fields_
class PowSpec(C.Structure):_fields_=[('name',C.c_char_p),('short',C.c_char_p)]
def original(lib,cats,sets,powers):
 keep=[]
 def specs(values,typ):
  out=(typ*len(values))()
  for i,(name,refs)in enumerate(values):
   array=(C.c_char_p*len(refs))(*[s.encode()for s in refs]);keep.append(array);out[i]=typ(name.encode(),len(refs),array)
  return out
 cs=specs(cats,CatSpec);ss=specs(sets,SetSpec);ps=(PowSpec*len(powers))(*[PowSpec(full.encode(),short.encode())for full,short in powers]);arrays=[(C.c_uint*8192)(),(C.c_uint*8192)(),(C.c_uint*32768)(),(C.c_uint*8192)(),(C.c_uint*32768)(),(C.c_uint*16)()];accepted=lib.original_join(cs,len(cats),ss,len(sets),ps,len(powers),*arrays);edges,counts,refs,parents,powparents,stats=arrays
 return {'accepted':bool(accepted),'categorysets':list(edges[:stats[1]]),'counts':list(counts[:len(sets)]),'refs':list(refs[:stats[2]]),'setparents':list(parents[:len(sets)]),'powparents':list(powparents[:len(powers)]),'statistics':list(stats[:4])}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cache-zip',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args();assert not a.output.exists()and __debug__
 helpers=[HERE/p for p in ('power_join_oracle.py','power_categories_independent.py','power_sets_independent.py','power_stream_schema.py','power_record_oracle.py','classes_oracle.py','origins_oracle.py','../costume-inputs/oracle.py','../costume-tree/crc_provider.py')];LOCKED.update({p.resolve():sha(p)for p in helpers});joinoracle=module('join_oracle',helpers[0]);categories=module('join_categories',helpers[1]);setsdecoder=module('join_sets',helpers[2]);stream=module('join_stream',helpers[3]);recordoracle=module('join_record',helpers[4]);recordoracle.module=module
 sourcepaths=set(joinoracle.PATHS+stream.PATHS+recordoracle.EXTRA)
 for helper in helpers[5:]:sourcepaths.update(module('join_paths_'+helper.stem,helper).EXTRA if helper.name.endswith('s_oracle.py')else module('join_paths_'+helper.stem,helper).PATHS)
 sources=[HERE/p for p in ('coh_power_join.c','coh_power_categories.c','coh_power_sets.c','coh_power_stream.c','../stash32/coh_stash32.c')];paths=set(helpers+sources+[HERE/'check_power_join.py',HERE/'test_power_join.c',HERE/'POWER_JOIN.md',HERE/'../costume-inputs/source-pins.json'])|{ROOT/'upstream/ouroboros'/p for p in sourcepaths};pending=[*sources,HERE/'test_power_join.c'];seen=set()
 while pending:
  path=pending.pop().resolve()
  if path in seen:continue
  seen.add(path);paths.add(path)
  for name in re.findall(r'^#include "([^"]+)"',path.read_text(),re.M):
   child=(path.parent/name).resolve()
   if child.is_file():pending.append(child)
 hashes={str(p.relative_to(ROOT)):sha(p)for p in sorted(paths)}
 assert a.cache_zip.stat().st_size==27071659 and sha(a.cache_zip)=='5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'
 texts={p:subprocess.check_output(['git','-C',ROOT,'show','HEAD:upstream/ouroboros/'+p]).decode().replace('\r\n','\n')for p in stream.PATHS};tables,_=stream.schema(texts);fields,_=setsdecoder.schema(texts[stream.PATHS[0]])
 cases=[];modes={};stack=[]
 with tempfile.TemporaryDirectory(prefix='coh-power-join-')as tmp:
  work=Path(tmp);ow=work/'original';ow.mkdir();lib,original_proof=joinoracle.build(ROOT,ow);rw=work/'record';rw.mkdir();rlib,record_proof=recordoracle.build(ROOT,rw);actualpaths=[work/'actual-categories.bin',work/'actual-sets.bin',work/'actual-powers.bin']
  with zipfile.ZipFile(a.cache_zip)as z:
   catsraw=z.read('data/bin/powercats.bin');setsraw=z.read('data/bin/powersets.bin');actualpaths[0].write_bytes(catsraw);actualpaths[1].write_bytes(setsraw)
   with z.open('data/bin/powers.bin')as src,actualpaths[2].open('xb')as dst:
    while chunk:=src.read(65536):dst.write(chunk)
  assert[sha(p)for p in actualpaths]==['67b46915b9bf4440de8f5cf8bf7dd4a9047daee7dc5cb96f2c2be3999f8fc5e7','afadc5f3ae6fc9c9c413924cec75bb911ff5cd4ce37388c6737cdb5786d9d547','25641e747c60e066016fcc7d2ce0a2e72f57d7d3953f7b1ff4b18b69e2d49c6d']
  decodedcats=categories.decode(catsraw);decodedsets=setsdecoder.decode(setsraw,fields)
  with actualpaths[2].open('rb')as src:decodedpowers=stream.inspect(src,actualpaths[2].stat().st_size,tables)
  actualcats=[(r['fields'][1],r['sets'])for r in decodedcats['rows']];actualsets=[(r['fields'][1],r['fields'][21])for r in decodedsets['rows']];actualpowers=[];first=None
  with actualpaths[2].open('rb')as src:
   for row in decodedpowers['rows']:
    src.seek(row['begin']);raw=src.read(row['end']-row['begin']);first=first or raw;full,at=read_string(raw,4);at+=4;_,at=read_string(raw,at);short,_=read_string(raw,at);assert full==row['name']and crc(full)==row['stored_crc'];actualpowers.append((full,short))
  scenarios=[('exact-historical-caches',actualcats,actualsets,actualpowers,actualpaths)]
  small=[
   ('ordered-repeated-set-and-unreached',[('First',['Alpha.S','Alpha.S']),('Second',['Alpha.S'])],[('Alpha.S',['Alpha.S.One','Alpha.S.Two']),('Unreached.S',['Unresolved.Raw'])],[('Alpha.S.One','One'),('Alpha.S.Two','Two'),('Unreached.S.Three','Three')]),
   ('alternate-identity',[('Category',['Target.S'])],[('Target.S',['Source.S.One'])],[('Source.S.One','One'),('Target.S.One','One')]),
   ('missing-alternate',[('Category',['Target.S'])],[('Target.S',['Source.S.One'])],[('Source.S.One','One')]),
   ('missing-declared',[('Category',['Alpha.S'])],[('Alpha.S',['Unknown.S.One'])],[('Alpha.S.One','One')]),
   ('missing-set',[('Category',['Unknown.S'])],[('Alpha.S',['Alpha.S.One'])],[('Alpha.S.One','One')]),
   ('case-sensitive-alternate-decision',[('Category',['ALPHA.S'])],[('ALPHA.S',['alpha.s.one'])],[('Alpha.S.One','One')]),
   ('short-name-contains-period',[('Category',['Alpha.S'])],[('Alpha.S',['Alpha.S.Adv._One'])],[('Alpha.S.Adv._One','Adv._One')]),
   ('slash-normalized-crc',[('Category',['Alpha/S'])],[('Alpha/S',['Alpha\\S.One'])],[('Alpha\\S.One','One')]),
   ('empty-categories',[],[('Unreached.S',['Unknown.S.One'])],[('Alpha.S.One','One')]),
   ('native-long-short-refusal',[('Category',['Alpha.S'])],[('Alpha.S',['Alpha.S.One'])],[('Alpha.S.One','X'*300)]),
   ('native-parent-work-refusal',[('Category',['Alpha.S']*8192)],[('Alpha.S',['Alpha.S.One']*32768)],[('Alpha.S.One','One')]),
   ('cross-source-reference-order',[('CatB',['Target.T','Target.S']),('CatA',['Target.S'])],[('Target.S',['Source.S.Two','Source.S.One']),('Target.T',['Source.S.One'])],[('Source.S.One','One'),('Source.S.Two','Two'),('Target.S.One','One'),('Target.S.Two','Two'),('Target.T.One','One')]),
  ]
  for index,(name,cats,sets,powers)in enumerate(small):
   paths=[work/f'case-{index}-{kind}.bin'for kind in ('cats','sets','powers')];paths[0].write_bytes(category_cache(cats));paths[1].write_bytes(set_cache(sets,fields));records=[]
   for full,short in powers:
    wire=replace_power(first,full,short);buf=C.create_string_buffer(65536);meta=(C.c_uint*16)();n=rlib.original_power_record(wire,len(wire),buf,meta);assert buf.raw[:n]==wire and meta[0]==meta[1]==crc(full);records.append(wire)
   paths[2].write_bytes(container(decodedpowers['schema_crc'],records));scenarios.append((name,cats,sets,powers,paths))
  for name,cats,sets,powers,paths in scenarios:
   if name.startswith('native-'):
    expected=work/(name+'.expected');status=2 if name=='native-long-short-refusal'else 4;expected.write_bytes(struct.pack('<I',status));cases.append({'name':name,'input_sha256':[sha(p)for p in paths],'cats':len(cats),'sets':len(sets),'powers':len(powers),'expected_status':status,'original_join_executed':False,'profile':'explicit bounded native refusal; complete original power codec still roundtrips every record','minimum_parent_work':8192*32768 if status==4 else None,'expected_sha256':sha(expected)});continue
   model=independent(cats,sets,powers);source=original(lib,cats,sets,powers);assert source['accepted']==(not model['errors']);assert source['categorysets']==model['categorysets'];assert source['counts']==[len(model['links'].get(i,[]))for i in range(len(sets))];assert source['refs']==[chosen for i in range(len(sets))for _,chosen in model['links'].get(i,[])];assert source['setparents']==model['setparents']and source['powparents']==model['powparents'];expected=work/(name+'.expected')
   with expected.open('xb')as dst:
    def words(*values):dst.write(struct.pack('<'+'I'*len(values),*values))
    words(3 if model['errors']else 0)
    if not model['errors']:
     words(len(model['categorysets']),sum(map(len,model['links'].values())),model['alternate']);words(*model['categorysets'])
     for i in range(len(sets)):
      links=model['links'].get(i,[]);words(len(links),model['setparents'][i])
      for raw,chosen in links:words(raw,chosen)
     words(*model['powparents']);words(0xabcdef01)
   cases.append({'name':name,'input_sha256':[sha(p)for p in paths],'cats':len(cats),'sets':len(sets),'powers':len(powers),'source':source if name!='exact-historical-caches'else{'accepted':source['accepted'],'statistics':source['statistics'],'projection_sha256':hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()},'alternate_decisions':model['alternate'],'errors':model['errors'],'expected_sha256':sha(expected)})
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]if a.sanitize else[]):
   exe=work/mode;run(['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic',*flags,*sources,HERE/'test_power_join.c','-lcrypto','-o',exe]);modechecks=[]
   for name,_,_,_,paths in scenarios:modechecks.append(json.loads(run([exe,*paths,work/(name+'.expected'),name],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))))
   modes[mode]={'binary_sha256':sha(exe),'checks':modechecks}
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,n,kind=line.split('\t')
    if 'coh_power_join.c:'in location:stack.append({'function':location,'bytes':int(n),'kind':kind})
  assert stack and sum(x['bytes']for x in stack)<16384 and all(x['kind']in ('static','dynamic,bounded')for x in stack)
  cpp=work/'header.cpp';cpp.write_text('#include "coh_power_join.h"\nint main(){return coh_power_join_prepare(nullptr,nullptr,nullptr,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,source in enumerate(sources):obj=work/f'cpp-{i}.o';run(['cc','-std=c11','-O2','-c',source,'-o',obj]);objects.append(obj)
  run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-o',work/'cpp']);run([work/'cpp']);rlib.original_power_records_close()
 for path,digest in hashes.items():assert sha(ROOT/path)==digest,'source changed '+path
 assert all(value['checks']==modes['release']['checks']for value in modes.values())
 result={'schema':'coh-compact-source-power-forward-join-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).strip(),'source_sha256':hashes,'original_forward_backpointer_projection':original_proof,'original_synthetic_power_records':record_proof,'cases':cases,'modes':modes,'native_stack':stack,'cpp_link_passed':True,'runtime_generation':False,'actor_authority':False,'original_hash_constructor_repeated':False,'source_duplicate_missing_powers_executed':False,'native_attribmod_parent_application':False,'complete_dictionary_finalization':False,'android_executed':False,'original_oracle_sanitized':False,'lsan_executed':False}
 a.output.parent.mkdir(parents=True,exist_ok=True)
 with a.output.open('xb')as dst:
  with gzip.GzipFile(fileobj=dst,mode='wb',mtime=0)as gz:gz.write((json.dumps(result,indent=2)+'\n').encode())
 print(json.dumps({'passed':True,'cases':len(cases),'checks_per_mode':sum(x['checks']for x in modes['release']['checks']),'historical_source_errors':cases[0]['errors'],'historical_alternates':cases[0]['alternate_decisions']}))
if __name__=='__main__':main()
