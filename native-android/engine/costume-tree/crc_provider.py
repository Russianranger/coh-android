"""Whole original table CRC traversal; explicit Crypto++ digest-byte adapter."""
import hashlib,re
from pathlib import Path
PATHS=['libs/UtilitiesLib/include/utilitieslib/utils/structInternals.h','libs/UtilitiesLib/src/network/crypt.cpp']
def generate(root,textparser,extract):
 header=(root/'upstream/ouroboros'/PATHS[0]).read_text();crypt=(root/'upstream/ouroboros'/PATHS[1]).read_text();functions={}
 def f(n):
  t=extract(textparser,n);functions[n]=hashlib.sha256(t.encode()).hexdigest();return t
 enums='\n'.join(re.search(r'typedef enum '+n+r'\s*\{.*?}\s*'+n+';',header,re.S).group()for n in ('ParseInfoField','ParseInfoFieldUsage'))
 code='''\n#include <zlib.h>
'''+enums+'''
typedef void DefineContext;
/* No table in these three actual schemas uses a static define list or global
 * defines; unexpected use refuses rather than synthesizing a dictionary. */
static void UpdateCrcFromStaticDefines(void*p){(void)p;assert(0);}
static void UpdateCrcFromDefineList(void*p){(void)p;assert(0);}
static uLong crc_accumulator;
static void cryptAdler32Init(void){crc_accumulator=adler32(0,NULL,0);}
static void cryptAdler32Update(const void*p,int n){assert(n>=0);crc_accumulator=adler32(crc_accumulator,p,n);}
/* Crypto++ Adler32::Final emits network byte order. Original copies those bytes
 * into U32, on the little-endian donor ABI. Not a host-native numeric checksum. */
static U32 cryptAdler32Final(void){U32 v=(U32)crc_accumulator;return(v>>24)|((v>>8)&0xff00u)|((v<<8)&0xff0000u)|(v<<24);}
'''+''.join(f(n)for n in ('ignore_interpretfield','number_interpretfield','string_interpretfield','struct_interpretfield'))+'''
typedef struct{ParseInfoFieldUsage(*interpretfield)(ParseTable*,int,ParseInfoField);}CrcHandler;
static CrcHandler crcinfo(U32 t){switch(TOK_GET_TYPE(t)){case TOK_INT_X:case TOK_F32_X:case TOK_BOOLFLAG_X:return(CrcHandler){number_interpretfield};case TOK_CURRENTFILE_X:case TOK_STRING_X:return(CrcHandler){string_interpretfield};case TOK_STRUCT_X:return(CrcHandler){struct_interpretfield};case TOK_END:return(CrcHandler){ignore_interpretfield};default:assert(0);return(CrcHandler){0};}}
#undef TYPE_INFO
#define TYPE_INFO(t) crcinfo(t)
'''+f('UpdateCRCFromParseInfo')+f('ParseTableCRC')+'''
unsigned original_tree_crc(unsigned kind){assert(kind<3);return(U32)ParseTableCRC(kind==0?ParseCostumeSet:kind==1?ParseBodyPartBegin:ParseColorPalette,NULL);}
'''
 return code,{'whole_function_sha256_lf':functions,'source_sha256_lf':{p:hashlib.sha256((root/'upstream/ouroboros'/p).read_text().encode()).hexdigest()for p in PATHS},'original_crypto_wrapper_sha256_lf':{n:hashlib.sha256(extract(crypt,n).encode()).hexdigest()for n in ('cryptAdler32Init','cryptAdler32Update','cryptAdler32Final')},'crypto_implementation':'zlib Adler32 adapted to original Crypto++ big-endian digest bytes; original Crypto++ engine not executed','whole_original_runtime_cache_selection':False}
