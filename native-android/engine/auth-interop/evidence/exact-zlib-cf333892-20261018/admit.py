#!/usr/bin/env python3
"""Read-only source admission. No extraction, patch application or C execution."""
import argparse,hashlib,json,re,tarfile
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
COMMIT='cf333892c34ab6dbaed37c38a1d5aa6da7b2f99d'
TREE='62224db151a2af4f2c66110d634ef8dc3607a155'
PINS={
 'source.tar.gz':(306531,'2f776d3abe636e302a98216fc81410622feb1be958315223d0d3442496365938'),
 'commit.json':(1645,'f27da76043e1ffc76c0da5f07d36adc3b34b659cf98ae092ae897ef1d9317eda'),
 'tree.json':(6025,'2b03a4e4d7edd236b5e1185b5a76013af77135355cd4342e8f347a5cbe7bb527'),
 'admission.json':(51645,'d104eafafe30e26d63072adef5a454e86d83d7280513c1add3d8478b1feebfd6'),
 'Zlib.cmake':(281,'dbabf749271e73e4bb5eb62c5d914ace1259520f6e8b52bbcf2600371b5d50be'),
 'chromium-zlib-cmake.patch':(2337,'55273bf390fd1093718d28f1141979fa97d23d1f071a1d90653f801cd425a107')}
def need(ok,code):
 if not ok:raise ValueError(code)
def exact(path,size,digest):
 need(not path.is_symlink() and path.is_file(),'REGULAR_INPUT')
 with path.open('rb') as stream:raw=stream.read(size+1)
 need(len(raw)==size and hashlib.sha256(raw).hexdigest()==digest,'EXACT_INPUT_BYTES');return raw
def decode(raw,xssi=False):
 if xssi:need(raw.startswith(b")]}'\n"),'PRIMARY_JSON_PREFIX');raw=raw[5:]
 def pairs(rows):
  result={}
  for key,value in rows:need(key not in result,'DUPLICATE_JSON');result[key]=value
  return result
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:need(False,'NONFINITE_JSON'))
def git_object(kind,raw):return hashlib.sha1(kind+b' '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def admit(materialized=None):
 inputs={name:exact(HERE/name,*pin) for name,pin in PINS.items()}
 receipt=decode(inputs['admission.json']);commit=decode(inputs['commit.json'],True);primary=decode(inputs['tree.json'],True)
 need(commit['commit']==COMMIT and commit['tree']==primary['id']==TREE,'PRIMARY_COMMIT_TREE')
 need(receipt['commit']==COMMIT and receipt['computed_archive_tree_sha1']==TREE and receipt['source_admitted']is True,'SOURCE_RECEIPT_SCOPE')
 need(receipt['compiler_executed']is False and receipt['runtime_executed']is False
      and receipt['static_x64_library_built']is False and receipt['existing_patch_applied']is False,'NO_BUILD_OR_PATCH_AUTHORITY')
 files={};total=0;count=0
 with tarfile.open(HERE/'source.tar.gz','r:gz') as archive:
  for member in archive:
   count+=1;need(count<=10000,'MEMBER_LIMIT');name=member.name.rstrip('/');parts=PurePosixPath(name)
   need(name and name.isascii() and not parts.is_absolute() and '\\' not in name
        and all(p not in ('','.','..') for p in parts.parts),'CANONICAL_ARCHIVE_PATH')
   if member.isdir():continue
   need(member.isfile() and name not in files and 0<=member.size<=20*1024**2,'REGULAR_UNIQUE_MEMBER')
   total+=member.size;need(total<=20*1024**2,'SOURCE_BYTE_LIMIT')
   with archive.extractfile(member) as stream:raw=stream.read(member.size+1)
   need(len(raw)==member.size,'MEMBER_EXTENT')
   row={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'git_blob_sha1':git_object(b'blob',raw),
        'git_mode':'100755' if member.mode&0o111 else '100644'}
   need(receipt['files'].get(name)==row,'EXACT_BLOB_MODE_INVENTORY');files[name]=row
 need(len(files)==111 and total==1216944 and count==receipt['archive_members'] and files==receipt['files'],'COMPLETE_SOURCE_INVENTORY')
 need(len({name.lower() for name in files})==len(files),'CASEFOLD_SOURCE_COLLISION')
 trees={}
 def tree(prefix=''):
  children={}
  for name,row in files.items():
   if not name.startswith(prefix):continue
   head,separator,_=name[len(prefix):].partition('/')
   children[head]=('40000',None) if separator else (row['git_mode'],row['git_blob_sha1'])
  body=b'';entries=[]
  for name,(mode,oid) in sorted(children.items(),key=lambda item:(item[0]+('/' if item[1][0]=='40000' else '')).encode()):
   if mode=='40000':oid=tree(prefix+name+'/')
   body+=mode.encode()+b' '+name.encode()+b'\0'+bytes.fromhex(oid)
   entries.append({'name':name,'mode':int(mode,8),'type':'tree' if mode=='40000' else 'blob','id':oid})
  oid=git_object(b'tree',body);trees[prefix.rstrip('/') or '.']={'git_tree_sha1':oid,'entries':entries};return oid
 need(tree()==TREE and trees==receipt['trees'],'EXACT_RECURSIVE_GIT_TREES')
 need(sorted(trees['.']['entries'],key=lambda row:row['name'])==sorted(primary['entries'],key=lambda row:row['name']),'PRIMARY_ROOT_ENTRIES')
 required=list(dict.fromkeys(re.findall(r'^\+\s+([A-Za-z0-9_/.]+\.c)\s*$',inputs['chromium-zlib-cmake.patch'].decode(),re.M)))
 need(len(required)==21 and required==receipt['x64_recipe_translation_units'] and all(name in files for name in required),'EXACT_X64_PATCH_SOURCES')
 headers=sorted(name for name in files if name.endswith('.h'));need(len(headers)==32 and headers==receipt['headers'],'EXACT_HEADER_INVENTORY')
 for name in ('Zlib.cmake','chromium-zlib-cmake.patch'):
  relative='cmake/'+('dependencies/' if name=='Zlib.cmake' else 'patches/')+name
  need(exact(ROOT/'upstream/ouroboros'/relative,*PINS[name])==inputs[name],'UNCHANGED_PROJECT_RECIPE_PATCH')
 if materialized is not None:
  materialized=materialized.resolve();need(materialized.is_dir(),'MATERIALIZED_SOURCE_ROOT')
  for name,row in files.items():
   path=materialized/name;exact(path,row['bytes'],row['sha256'])
   need(bool(path.stat().st_mode&0o111)==(row['git_mode']=='100755'),'MATERIALIZED_EXECUTABLE_MODE')
  need({p.relative_to(materialized).as_posix() for p in materialized.rglob('*') if p.is_file()}==set(files),'MATERIALIZED_EXACT_INVENTORY')
 for name,pin in PINS.items():exact(HERE/name,*pin)
 return {'schema':'coh-exact-chromium-zlib-source-readmission-v1','passed':True,'commit':COMMIT,'tree':TREE,
         'regular_files':111,'headers':32,'x64_translation_units':21,'source_bytes':total,
         'materialized_source_readmitted':materialized is not None,'patch_applied':False,'compiler_executed':False,
         'runtime_executed':False,'static_x64_library_built':False,'Windows_platform_closure_qualified':False}
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--materialized-root',type=Path);args=parser.parse_args()
 print(json.dumps(admit(args.materialized_root),sort_keys=True))
if __name__=='__main__':main()
