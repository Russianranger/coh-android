#!/usr/bin/env python3
"""Read-only pinned CLIENT category/shared-set traversal; no runtime lease."""
import collections,hashlib,json,pathlib,re,subprocess
TOKEN=re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|[{}]|[^\s{}"]+')
def unquote(t):return t[1:-1]if t.startswith('"')and t.endswith('"')else t
def collect(root):
 root=pathlib.Path(root);tracked=subprocess.check_output(['git','ls-files','upstream/i24/data/defs/powers/'],cwd=root,text=True).splitlines();paths=sorted(p for p in tracked if p.endswith(('.powersets','.categories')));proc=subprocess.Popen(['git','cat-file','--batch'],cwd=root,stdin=subprocess.PIPE,stdout=subprocess.PIPE);rows=[];cats=[];hashes={}
 for path in paths:
  proc.stdin.write(('HEAD:'+path+'\n').encode());proc.stdin.flush();header=proc.stdout.readline().decode().split();assert len(header)==3 and header[1]=='blob';raw=proc.stdout.read(int(header[2]));assert proc.stdout.read(1)==b'\n';hashes[path]=hashlib.sha256(raw).hexdigest();text=raw.decode('utf-8-sig');ts=[(m.group(),m.start())for m in TOKEN.finditer(text)if not m.group().startswith(('//','/*'))];depth=0;current=None
  for i,(t,pos)in enumerate(ts):
   if t=='{':depth+=1;continue
   if t=='}':
    depth-=1
    if depth==0 and current is not None:(cats if current['kind']=='PowerCategory'else rows).append(current);current=None
    assert depth>=0;continue
   first=not text[text.rfind('\n',0,pos)+1:pos].strip()
   if depth==0 and first and t in('PowerSet','PowerCategory'):
    assert current is None;current={'kind':t,'name':unquote(ts[i+1][0]),'path':path,'line':text.count('\n',0,pos)+1,'shared':False,'refs':[],'shared_fields':0};continue
   if depth==1 and first and current is not None:
    if t=='Shared':
     value=unquote(ts[i+1][0]);assert value.lower()in('true','false','1','0');current['shared']=value.lower()in('true','1');current['shared_fields']+=1;assert current['shared_fields']==1
    if t=='PowerSets':current['refs'].append(unquote(ts[i+1][0]))
  assert depth==0 and current is None,path
 proc.stdin.close();assert proc.wait()==0
 assert all(v==1 for v in collections.Counter(r['name'].casefold()for r in rows).values());assert all(v==1 for v in collections.Counter(r['name']for r in cats).values());lookup={r['name'].casefold():r for r in rows};shared=[r for r in rows if r['shared']];ordered=[];missing=[]
 for c in sorted(cats,key=lambda r:r['name'].encode('ascii')):
  for ref in c['refs']:
   r=lookup.get(ref.casefold())
   if r is None:missing.append({'category':c['name'],'reference':ref});continue
   if r['shared']:ordered.append({'category':c['name'],'set':r['name'],'path':r['path'],'line':r['line']})
 reachable={r['set'].casefold()for r in ordered};canonical=json.dumps(hashes,sort_keys=True,separators=(',',':')).encode();profile=hashlib.sha256(canonical).hexdigest()
 return {'input_sha256':hashes,'canonical_inputs_sha256':profile,'source_profile_token':int.from_bytes(bytes.fromhex(profile)[:4],'little'),'powerset_files':sum(p.endswith('.powersets')for p in paths),'category_files':sum(p.endswith('.categories')for p in paths),'powerset_rows':len(rows),'categories':len(cats),'allocated_shared':len(shared),'reachable_shared_references':len(ordered),'shared_order':ordered,'unreachable_shared':[r['name']for r in shared if r['name'].casefold()not in reachable],'missing_references':missing,'shared_by_category':dict(collections.Counter(r['category']for r in ordered)),'startup_sources':['upstream/ouroboros/Game/src/main.c','upstream/ouroboros/Game/src/game.c','upstream/ouroboros/Common/entity/load_def.c','upstream/ouroboros/Common/entity/powers.c','upstream/ouroboros/Common/entity/powers_load.c']}
if __name__=='__main__':
 import sys
 result=collect(sys.argv[1]);text=json.dumps(result,indent=2)+'\n'
 if len(sys.argv)>2:pathlib.Path(sys.argv[2]).write_text(text)
 else:print(text,end='')
