"""Actual retained attribute schema using whole original Parse6 read/write+CRC.
Host allocation/layout dispatch shells inherited explicitly from small-input
qualification; no runtime shared-cache branch or semantic attribute application.
"""
import ctypes as C,hashlib,importlib.util,json,re,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
EXTRA=['Common/entity/attrib_description.c','Common/entity/attrib_description.h','Common/entity/character_attribs.h','libs/UtilitiesLib/include/utilitieslib/utils/structDefines.h']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def build(root,work):
 small=module('attribute_small_input',HERE/'../costume-inputs/oracle.py');prior=work/'small';prior.mkdir();_,proof=small.build(root,prior);code=(prior/'original.c').read_text();src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in small.PATHS+EXTRA}
 for n in('original_decode','original_result_size'):code=code.replace(small.extract(code,n),'')
 header=src[EXTRA[1]];decl=header[header.index('typedef enum AttribType'):header.index('extern SERVER_SHARED_MEMORY')]
 decl=decl[:decl.index('typedef struct CombatMonitorStat')]if 'typedef struct CombatMonitorStat'in decl else decl
 defines=src[EXTRA[3]];start=defines.index('#define DM_END');end=defines.index('// use this to embed')
 code+='\n#define bool U8\ntypedef struct BasePower BasePower;\n'+decl+'\n'
 code+='\n#define U32_TO_PTR(v) ((void*)(uintptr_t)(U32)(v))\n#define PTR_TO_S32(v) ((int32_t)(intptr_t)(v))\n'+defines[start:end]
 text=src[EXTRA[0]];tables={}
 for n in('AttribTypeEnum','AttribStyleEnum'):
  body=re.search(r'StaticDefineInt '+n+r'\[\]\s*=\s*\{.*?\n};',text,re.S).group();tables[n]=sha(body.encode());code+='\n'+body
 code+='\n#define TOK_BOOL(s,m,d) TOK_BOOL_X,offsetof(s,m),d\n'
 for n in('ParseAttribDescription','ParseAttribCategory','ParseAttribCategoryList'):
  body=re.search(r'TokenizerParseInfo '+n+r'\[\]\s*=\s*\{.*?\n};',text,re.S).group();tables[n]=sha(body.encode());code+='\n'+body
 code=code.replace('case TOK_BOOLFLAG_X:return(Handler)','case TOK_BOOL_X:case TOK_BOOLFLAG_X:return(Handler)').replace('case TOK_END:return(Handler)','case TOK_START:case TOK_END:return(Handler)')
 # Exact original CRC functions, including original static define traversal.
 crc=module('attribute_crc',HERE/'../costume-tree/crc_provider.py');crc_code,crcproof=crc.generate(root,src[small.PATHS[5]],small.extract)
 crc_code=crc_code.replace('static void UpdateCrcFromStaticDefines(void*p){(void)p;assert(0);}','static void UpdateCrcFromStaticDefines(StaticDefine*);')
 crc_code=crc_code.replace('case TOK_INT_X:case TOK_F32_X:case TOK_BOOLFLAG_X:','case TOK_INT_X:case TOK_F32_X:case TOK_BOOL_X:case TOK_BOOLFLAG_X:').replace('case TOK_END:return(CrcHandler)','case TOK_START:case TOK_END:return(CrcHandler)')
 crc_code=crc_code[:crc_code.index('unsigned original_tree_crc(')];at=crc_code.index('static void UpdateCRCFromParseInfo(');crc_code=crc_code[:at]+small.extract(src[small.PATHS[5]],'UpdateCrcFromStaticDefines')+crc_code[at:];code+='\n'+crc_code+'\nunsigned original_attribute_crc(void){return(U32)ParseTableCRC(ParseAttribCategoryList,NULL);}\n'
 code+='''
int original_attribute_tree(const unsigned char*bytes,unsigned size,unsigned begin,unsigned char*roundtrip,unsigned*words,char*strings,unsigned*textbytes){
 SimpleBuffer in={0},wr={0};AttribCategoryList list={0};int sum=0;unsigned n=0,at=0,total=0;assert(size<=65536&&begin<size);memcpy(in.data,bytes,size);in.filesize=size;in.curposition=begin;reset();
 if(!ParserReadBinaryTable(&in,ParseAttribCategoryList,&list,&sum)||in.curposition!=(int)size){reset();return 0;}
 Vec*categories=(Vec*)list.ppCategories;words[n++]=categories->size;words[n++]=0;
 for(int i=categories->size-1;i>=0;i--){AttribCategory*cat=categories->items[i];Vec*attrs=(Vec*)cat->ppAttrib;for(int j=(attrs?attrs->size:0)-1;j>=0;j--){AttribDescription*d=attrs->items[j];assert(n+8<=4096);words[n++]=i;words[n++]=j;words[n++]=d->eType;words[n++]=d->eStyle;words[n++]=d->iKey;words[n++]=d->offAttrib;words[n++]=d->bShowBase;words[n++]=attrs->size;const char*names[]={cat->pchDisplayName,d->pchName,d->pchDisplayName,d->pchToolTip};for(unsigned k=0;k<4;k++){unsigned len=names[k]?strlen(names[k]):0;assert(at+len+1<=131072);if(names[k])memcpy(strings+at,names[k],len);strings[at+len]=0;at+=len+1;}total++;}}
 words[1]=total;*textbytes=at;wr.curposition=begin;wr.filesize=begin;memcpy(wr.data,bytes,begin);sum=0;int ok=ParserWriteBinaryTable(&wr,ParseAttribCategoryList,&list,&sum,0,0);if(ok)memcpy(roundtrip,wr.data,wr.filesize);unsigned result=ok?wr.filesize:0;reset();return result;
}
'''
 variant=small.extract(code,'original_attribute_tree').replace('original_attribute_tree(', 'original_attribute_variant(',1).replace('unsigned*textbytes){','unsigned*textbytes,unsigned scenario){',1)
 variant=variant.replace('Vec*categories=(Vec*)list.ppCategories;', '''Vec*categories=(Vec*)list.ppCategories;if(scenario){assert(scenario<=4&&categories->size>0);AttribCategory*cat=categories->items[0];Vec*v=(Vec*)cat->ppAttrib;assert(v&&v->size>1);AttribDescription*d=v->items[0];if(scenario==1)d->pchName="UnknownRawName";if(scenario==2){d->eType=-1;d->eStyle=0x7fffffff;d->iKey=-1;d->offAttrib=(int)0x80000000u;d->bShowBase=255;}if(scenario==3)v->size=0;if(scenario==4)v->items[1]=v->items[0];}''')
 code+='\n'+variant
 for qualified,expected in proof['function_sha256_lf'].items():
  path,name=qualified.rsplit(':',1);assert sha(small.extract(code,name).encode())==expected,(name,'changed')
 (work/'original-attributes.c').write_text(code);subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),work/'original-attributes.c','-lz','-o',work/'original-attributes.so'],check=True)
 lib=C.CDLL(str(work/'original-attributes.so'));lib.original_attribute_tree.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_void_p,C.c_void_p];lib.original_attribute_variant.argtypes=lib.original_attribute_tree.argtypes+[C.c_uint]
 return lib,{'small_original_provider':proof,'source_sha256_lf':{p:sha(t.encode())for p,t in src.items()},'actual_tables_sha256_lf':tables,'crc':crcproof,'UpdateCrcFromStaticDefines_sha256_lf':sha(small.extract(src[small.PATHS[5]],'UpdateCrcFromStaticDefines').encode()),'generated_c_sha256':sha(code.encode()),'host_storage_shells':True,'original_runtime_cache_branch':False,'original_preprocessor_applied':False}
