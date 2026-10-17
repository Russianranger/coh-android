"""Whole original origins Parse6 reader/writer/CRC and reverse lookup.
Explicit host TokenStore/allocation/layout adapters inherited from small-inputs;
no runtime shared-cache selection or source/server-generation admission.
"""
import ctypes as C,hashlib,importlib.util,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/origins.h','Common/entity/origins.c','Common/entity/load_def.c','Common/entity/classes.c','MapServer/src/entity/entsend.c','Game/src/entity/entrecv.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(n,p):
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),"exec"),m.__dict__);return m
def build(root,work):
 small=module('origin_small',HERE/'../costume-inputs/oracle.py');prior=work/'small';prior.mkdir();_,proof=small.build(root,prior);code=(prior/'original.c').read_text();src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in small.PATHS+EXTRA}
 for n in('original_decode','original_result_size'):code=code.replace(small.extract(code,n),'')
 header=src[EXTRA[0]];code+='\n#include <strings.h>\n#define stricmp strcasecmp\n'+re.search(r'typedef struct CharacterOrigin\b.*?} CharacterOrigin;',header,re.S).group()+'\n'+re.search(r'typedef struct CharacterOrigins\b.*?} CharacterOrigins;',header,re.S).group()+'\n';tables={}
 for name in('ParseCharacterOrigin','ParseCharacterOrigins'):
  body=re.search(r'TokenizerParseInfo '+name+r'\[\]\s*=.*?\n};',header,re.S).group();tables[name]=sha(body.encode());code+='\n'+body
 code=code.replace('case TOK_END:return(Handler)','case TOK_START:case TOK_END:return(Handler)')
 crc=module('origin_crc',HERE/'../costume-tree/crc_provider.py');crc_code,crcproof=crc.generate(root,src[small.PATHS[5]],small.extract);crc_code=crc_code[:crc_code.index('unsigned original_tree_crc(')];crc_code=crc_code.replace('case TOK_END:return(CrcHandler)','case TOK_START:case TOK_END:return(CrcHandler)');code+='\n'+crc_code+'\nunsigned original_origin_crc(void){return(U32)ParseTableCRC(ParseCharacterOrigins,NULL);}\n'
 code+='\n#define eaSize(pp) (*(pp)?((Vec*)((char*)*(pp)-offsetof(Vec,items)))->size:0)\n'
 functions={}
 for name in('origins_GetPtrFromName','origins_GetIndexFromName','origins_GetIndexFromPtr'):
  body=small.extract(src[EXTRA[1]],name);functions[name]=sha(body.encode());code+='\n'+body
 code+='''
int original_origin_tree(const unsigned char*bytes,unsigned size,unsigned begin,unsigned char*roundtrip,unsigned*words,char*strings,unsigned*textbytes,unsigned scenario){
 SimpleBuffer in={0},wr={0};CharacterOrigins list={0};int sum=0;unsigned n=0,at=0;assert(size<=65536&&begin<size);memcpy(in.data,bytes,size);in.filesize=size;in.curposition=begin;reset();
 if(!ParserReadBinaryTable(&in,ParseCharacterOrigins,&list,&sum)||in.curposition!=(int)size){reset();return 0;}
 Vec*v=(Vec*)list.ppOrigins;assert(v&&v->size<=128);if(scenario){assert(scenario<=6&&v->size);CharacterOrigin*first=v->items[0];if(scenario==1)first->pchName="Unknown_Origin";if(scenario==2&&v->size>1)((CharacterOrigin*)v->items[v->size-1])->pchName=first->pchName;if(scenario==3)v->size=0;if(scenario==4||scenario==5){v->size=scenario==4?128:129;for(int j=0;j<v->size;j++)v->items[j]=first;}if(scenario==6)first->pchName="";}
 CharacterOrigins lookup={(const CharacterOrigin**)v->items};words[n++]=v->size;for(int i=0;i<v->size;i++){CharacterOrigin*d=v->items[i];const char*fields[]={d->pchName,d->pchDisplayName,d->pchDisplayHelp,d->pchDisplayShortHelp,d->pchIcon};for(unsigned k=0;k<5;k++){unsigned len=fields[k]?strlen(fields[k]):0;assert(at+len+1<=65536);if(fields[k])memcpy(strings+at,fields[k],len);strings[at+len]=0;at+=len+1;}words[n++]=origins_GetIndexFromName(&lookup,d->pchName);words[n++]=origins_GetIndexFromPtr(&lookup,origins_GetPtrFromName(&lookup,d->pchName));}
 words[n++]=origins_GetIndexFromName(&lookup,"unknown_missing_origin");*textbytes=at;wr.curposition=begin;wr.filesize=begin;memcpy(wr.data,bytes,begin);sum=0;int ok=ParserWriteBinaryTable(&wr,ParseCharacterOrigins,&list,&sum,0,0);if(ok)memcpy(roundtrip,wr.data,wr.filesize);unsigned result=ok?wr.filesize:0;reset();return result;
}
'''
 (work/'original-origins.c').write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),work/'original-origins.c','-lz','-o',work/'original-origins.so'],check=True);lib=C.CDLL(str(work/'original-origins.so'));lib.original_origin_tree.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p,C.c_uint]
 return lib,{'small_original_provider':proof,'source_sha256_lf':{p:sha(t.encode())for p,t in src.items()},'actual_tables_sha256_lf':tables,'whole_lookup_functions_sha256_lf':functions,'crc':crcproof,'generated_c_sha256':sha(code.encode()),'storage_shells':True,'runtime_cache_branch':False}
