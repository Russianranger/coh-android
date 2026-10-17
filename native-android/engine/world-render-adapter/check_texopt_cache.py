#!/usr/bin/env python3
"""Qualify actual retained CLIENT tricks cache framing and immutable prefix input contract."""
import argparse,hashlib,importlib.util,json,os,struct,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);import sys;sys.modules[name]=m;spec.loader.exec_module(m);return m

def oracle(source,internal,extract):
 return r'''#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
typedef uint32_t U32;typedef struct{unsigned char*b;size_t size,pos;}Buffer;typedef Buffer*SimpleBufHandle;
static int SimpleBufRead(void*out,size_t n,SimpleBufHandle f){if(n>f->size-f->pos)return 0;memcpy(out,f->b+f->pos,n);f->pos+=n;return(int)n;}
static int SimpleBufReadU16(unsigned short*out,SimpleBufHandle f){unsigned char b[2];if(!SimpleBufRead(b,2,f))return 0;*out=(unsigned short)(b[0]|b[1]<<8);return 2;}
static int SimpleBufReadU32(U32*out,SimpleBufHandle f){unsigned char b[4];if(!SimpleBufRead(b,4,f))return 0;*out=(U32)b[0]|(U32)b[1]<<8|(U32)b[2]<<16|(U32)b[3]<<24;return 4;}
static void SimpleBufSeek(SimpleBufHandle f,long n,int origin){assert(origin==SEEK_CUR&&n>=0&&(size_t)n<=f->size-f->pos);f->pos+=(size_t)n;}
'''+extract(source,'int ReadPascalString(')+r'''
#define MAX_PATH 260
#define FILELIST_SIG "Files1"
typedef int32_t __time32_t;typedef struct{char path[MAX_PATH];__time32_t date;}FileEntry;typedef FileEntry**FileList;
static unsigned file_count;static void FileListCreate(FileList*l){*l=calloc(4096,sizeof(**l));assert(*l);file_count=0;}
static void eaPush(FileList*l,FileEntry*n){assert(file_count<4096);(*l)[file_count++]=n;}
static int SerializeReadData(SimpleBufHandle f,int n,void*out){return SimpleBufRead(out,(size_t)n,f);}
static int SerializeReadHeader(SimpleBufHandle f,char*s,int n,int*size){return ReadPascalString(f,s,n)&&SimpleBufReadU32((U32*)size,f);}
static void SerializeSkipStruct(SimpleBufHandle f){char name[20];int n;assert(SerializeReadHeader(f,name,20,&n));SimpleBufSeek(f,n,SEEK_CUR);}
'''+extract(internal,'int FileListRead(')+r'''
static void put(FILE*f,const void*p,size_t n){assert(fwrite(p,1,n,f)==n);}
static void num(FILE*f,U32 v){unsigned char b[4]={(unsigned char)v,(unsigned char)(v>>8),(unsigned char)(v>>16),(unsigned char)(v>>24)};put(f,b,4);}
static void text(FILE*f,SimpleBufHandle b){char s[1024];assert(ReadPascalString(b,s,sizeof(s)));num(f,(U32)strlen(s));put(f,s,strlen(s));}
int main(int argc,char**argv){assert(argc==3);FILE*f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0&&n<16*1024*1024);rewind(f);Buffer b={malloc((size_t)n),(size_t)n,20};assert(b.b&&fread(b.b,1,b.size,f)==b.size);fclose(f);FileList list=NULL;assert(FileListRead(&list,&b));FILE*out=fopen(argv[2],"wb");assert(out);num(out,file_count);for(unsigned i=0;i<file_count;i++){num(out,(U32)strlen(list[i]->path));put(out,list[i]->path,strlen(list[i]->path));num(out,(U32)list[i]->date);free(list[i]);}free(list);U32 top,count;assert(SimpleBufReadU32(&top,&b)&&top==b.size-b.pos);assert(SimpleBufReadU32(&count,&b));num(out,count);for(U32 i=0;i<count;i++){U32 size;assert(SimpleBufReadU32(&size,&b));size_t offset=b.pos;num(out,(U32)offset);num(out,size);text(out,&b);text(out,&b);U32 stamp;assert(SimpleBufReadU32(&stamp,&b));num(out,stamp);text(out,&b);num(out,(U32)b.pos);assert(offset+size>=b.pos&&offset+size<=b.size);b.pos=offset+size;}assert(SimpleBufReadU32(&count,&b));num(out,count);for(U32 i=0;i<count;i++){U32 size;assert(SimpleBufReadU32(&size,&b));num(out,(U32)b.pos);num(out,size);assert(size<=b.size-b.pos);b.pos+=size;}assert(b.pos==b.size);assert(!fclose(out));free(b.b);return 0;}
'''
def transcript(c):
 out=bytearray()
 def n(x):out.extend(struct.pack('<I',x))
 def s(x):n(len(x));out.extend(x)
 n(len(c.files))
 for x in c.files:s(x.path);n(x.timestamp)
 n(len(c.texopts))
 for x in c.texopts:n(x.offset);n(x.size);s(x.name);s(x.source_file);n(x.timestamp);s(x.internal_name);n(x.opaque_offset)
 n(len(c.tricks))
 for x in c.tricks:n(x.offset);n(x.size)
 return bytes(out)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--actual-cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError('fresh receipt required')
 deps=[HERE/'CLIENT_TEXOPT_CACHE.md',HERE/'recover_texopt_cache.py',HERE/'texopt_cache_contract.py',HERE/'check_texopt_cache.py',HERE/'check_texname.py',HERE/'texopt-cache-source-pins.json'];deps={str(x.relative_to(ROOT)):sha(x.read_bytes()) for x in deps}
 pins=json.loads((HERE/'texopt-cache-source-pins.json').read_text());sources={x:sha((ROOT/x).read_bytes()) for x in pins['source_sha256']}
 if sources!=pins['source_sha256'] or sha((ROOT/pins['manifest']).read_bytes())!=pins['manifest_sha256']:raise ValueError('exact source/cache manifest differs')
 m=load('texopt_contract_qualified',HERE/'texopt_cache_contract.py');old=load('texopt_original_extract',HERE/'check_texname.py');body=a.actual_cache.read_bytes();c=m.admit(body,pins['cache']);expected=transcript(c)
 checks=0
 def check(value):
  nonlocal checks;checks+=1
  if not value:raise AssertionError('cache contract control '+str(checks))
 check(len(c.files)==1585 and len(c.texopts)==14715 and len(c.tricks)==3644)
 check(all(x.name==x.internal_name for x in c.texopts));check(sum(any(b>127 for b in x.name) for x in c.texopts)==1)
 file_keys={x.path.lower() for x in c.files};check(all(x.source_file.lower() in file_keys for x in c.texopts))
 check([x.ordinal for x in c.texopts if x.name==b'asphalt_squaremask']==[2913])
 check(not any(x.name.lower()==b'bar_vert_sign' for x in c.texopts))
 try:c.files=();raise AssertionError('mutable')
 except (AttributeError,TypeError):checks+=1
 bad=[]
 for n in [0,1,7,12,19,27,31,95347,95348,len(body)-1]:bad.append(body[:n])
 bad.extend([body+b'x',bytes([body[0]^1])+body[1:],body[:8]+b'\0'*4+body[12:],body[:12]+b'\xff\xff'+body[14:],body[:32]+struct.pack('<I',4097)+body[36:],body[:95352]+struct.pack('<I',65537)+body[95356:]])
 for b in bad:
  try:m.admit(b,pins['cache']);raise AssertionError('exact pin admitted malformed')
  except ValueError:checks+=1
 for pos,val in [(28,0xffffffff),(32,4097),(95348,0),(95352,65537),(95356,0xffffffff)]:
  b=body[:pos]+struct.pack('<I',val)+body[pos+4:]
  try:m.frame(b);raise AssertionError('bad framing')
  except ValueError:checks+=1
 try:m.frame(bytearray(body));raise AssertionError('mutable input')
 except ValueError:checks+=1
 util='upstream/ouroboros/libs/UtilitiesLib/src/utils/';code=oracle((ROOT/(util+'serialize.c')).read_text(),(ROOT/(util+'structInternals.c')).read_text(),old.extract);modes={}
 with tempfile.TemporaryDirectory(prefix='coh-texopt-cache-') as directory:
  d=Path(directory);(d/'oracle.c').write_text(code)
  for mode,flags in [('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   old.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-error=maybe-uninitialized','-pedantic',*flags,d/'oracle.c','-o',d/mode]);old.run([d/mode,a.actual_cache,d/(mode+'.bin')],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'));actual=(d/(mode+'.bin')).read_bytes();check(actual==expected);modes[mode]={'leak_sanitizer_enabled':False,'original_filelist_reader_executed':True,'original_pascal_reader_executed':True,'transcript_sha256':sha(actual),'prefixes':14715,'file_entries':1585,'opaque_tricks':3644}
 source=(ROOT/'upstream/ouroboros/Common/seq/tricks.c').read_text();tables={}
 for name in ['parse_tex_opt_fallback','parse_tex_opt','parse_trick','parse_trick_list']:
  start=source.index('TokenizerParseInfo '+name+'[]');end=source.index('\n};',start)+3;tables[name]={'source_sha256_lf':sha(source[start:end].encode()),'declaration_bytes':end-start}
 check(sources=={x:sha((ROOT/x).read_bytes()) for x in sources});check(deps=={x:sha((ROOT/x).read_bytes()) for x in deps});check(sha(a.actual_cache.read_bytes())==c.sha256);check(sha((ROOT/pins['manifest']).read_bytes())==pins['manifest_sha256'])
 proof={'passed':True,'source_revision':old.run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_sha256':sources|deps,'cache':pins['cache'],'schema_tables':tables,'schema_crc_recomputed_from_compiled_tables':False,'controls':checks,'modes':modes,'files':len(c.files),'texopts':len(c.texopts),'tricks':len(c.tricks),'original_compiler_warning_preserved':'FileListRead maybe-uninitialized','opaque_material_payloads':True,'complete_material_grammar_parsed':False,'cache_generation_live_matched':False,'effective_postprocess_executed':False,'material_authority':False,'world_authority':False,'android_execution':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'controls':checks,'files':len(c.files),'texopts':len(c.texopts),'tricks':len(c.tricks),'original_reader_modes':list(modes)}))
if __name__=='__main__':main()
