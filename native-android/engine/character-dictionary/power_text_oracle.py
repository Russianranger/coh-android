"""Original tokenizer/hash bodies with bounded, offline-only POSIX file shims."""
import ctypes,hashlib,re,subprocess
from pathlib import Path
from power_join_oracle import extract

SOURCE_PATHS=('upstream/ouroboros/libs/UtilitiesLib/src/utils/structTokenizer.c',
              'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/structTokenizer.h',
              'upstream/ouroboros/libs/UtilitiesLib/src/network/crc32c.cpp',
              'upstream/ouroboros/Common/entity/powers.c',
              'upstream/ouroboros/Common/entity/powers_load.c')

def generate(root):
    raw={p:subprocess.check_output(['git','-C',str(root),'show','HEAD:'+p]) for p in SOURCE_PATHS}
    texts={p:b.decode().replace('\r\n','\n') for p,b in raw.items()};tok=texts[SOURCE_PATHS[0]];header=texts[SOURCE_PATHS[1]]
    powers=texts[SOURCE_PATHS[4]]
    # FullName is an explicit struct parameter, not derived from a filename.
    assert re.search(r'"FullName",\s*TOK_STRUCTPARAM\s*\|\s*TOK_STRING\(BasePower,\s*pchFullName,\s*0\)',powers)
    assert re.search(r'"Power",\s*TOK_STRUCT\(PowerDictionary,\s*ppPowers,\s*ParseBasePower\)',powers)
    defs='\n'.join(re.search(r'^#define '+n+r'[^\n]*',header,re.M).group() for n in ('MAX_TOKEN_LENGTH','MAX_STRING_LENGTH','TOKEN_BUFFER_LENGTH'))
    declarations=re.search(r'typedef struct TokenizerContext\b.*?} Tokenizer;',tok,re.S).group()
    code=r'''
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <ctype.h>
#include <assert.h>
#include <alloca.h>
#include <unistd.h>
typedef uint32_t U32;typedef uint8_t U8;typedef void DefineContext;typedef void StaticDefine;typedef void*TokenizerHandle;
#define MAX_PATH 260
#define _alloca alloca
#define _strnicmp strncasecmp
#define min(a,b) ((a)<(b)?(a):(b))
static int g_parseerr,g_parselist;
#define ErrorFilenamef(...) (g_parseerr=1)
static void FileListInsert(void*a,const char*b,int c){(void)a;(void)b;(void)c;g_parseerr=1;}
static int FolderCacheMatchesIgnorePrefixAnywhere(const char*s){(void)s;return 0;}
static void forwardSlashes(char*s){for(;*s;s++)if(*s=='\\')*s='/';}
static const char*DefineLookup(void*a,const char*b){(void)a;(void)b;g_parseerr=1;return NULL;}
static const char*StaticDefineLookup(void*a,const char*b){return DefineLookup(a,b);}
static void strncpy_s(char*d,size_t cap,const char*s,size_t n){assert(n<cap);memcpy(d,s,n);d[n]=0;}
'''+defs+'\n'+declarations+r'''
static char g_comma[]=",",g_eol[]="\n",g_delims[]=" ,\n\t\r";
static const char*TokenizerGetFileName(TokenizerHandle p){(void)p;return "offline source";}
static const char*TokenizerGetFileAndLine(TokenizerHandle p){return TokenizerGetFileName(p);}
/* Includes and define substitution need their original owners. Never open a
 * guessed include path or synthesize a replacement in this text-only tool. */
static TokenizerContext*OpenTokenFile(const char*p){(void)p;g_parseerr=1;return NULL;}
static void CloseTokenFile(TokenizerContext*p){if(p->handle)fclose(p->handle);free(p);}
'''
    names=('TokenizerInit','LoadBuffer','TokenizerUnescape','TokenizerPeek','TokenizerGet')
    functions={}
    for name in names:
        body=extract(tok,name);functions[name]=hashlib.sha256(body.encode()).hexdigest();code+='\n'+body
    crc=texts[SOURCE_PATHS[2]]
    code+='\n'+re.search(r'static const U32 s_crc32c\[0x100\].*?\n};',crc,re.S).group()
    for name in ('Crc32c_cpu','Crc32c','Crc32cLowerStringHash'):
        body=extract(crc,name);functions[name]=hashlib.sha256(body.encode()).hexdigest();code+='\n'+body
    code+='\ntypedef struct {const char*pchFullName;} BasePower;\n'
    body=extract(texts[SOURCE_PATHS[3]],'powerdict_GetCRCOfBasePower');functions['powerdict_GetCRCOfBasePower']=hashlib.sha256(body.encode()).hexdigest();code+='\n'+body
    code+=r'''
void*ptm_open(int source){
 Tokenizer*t=calloc(1,sizeof(*t));TokenizerContext*c=calloc(1,sizeof(*c));
 if(!t||!c){free(t);free(c);return NULL;}TokenizerInit(t);
 int fd=dup(source);if(fd<0){free(t);free(c);return NULL;}
 c->handle=fdopen(fd,"rb");if(!c->handle){close(fd);free(t);free(c);return NULL;}
 c->curline=c->nextline=1;t->context=c;g_parseerr=0;
 unsigned char bom[3];size_t n=fread(bom,1,3,c->handle);
 long start=n==3&&bom[0]==0xef&&bom[1]==0xbb&&bom[2]==0xbf?3:0;
 LoadBuffer(t,start);return t;
}
int ptm_next(void*owner,char*out,unsigned capacity,int*line,int*quoted){
 Tokenizer*t=owner;if(!t||g_parseerr)return -1;
 const char*token=TokenizerPeek(t,1,1);if(g_parseerr||ferror(t->context->handle))return -1;if(!token)return 0;
 *quoted=t->instring||t->inescape;token=TokenizerGet(t,1,1);*line=t->context->curline;
 if(g_parseerr)return -1;size_t n=strnlen(token,MAX_STRING_LENGTH+1);
 if(n>=capacity||n>MAX_STRING_LENGTH)return -1;memcpy(out,token,n+1);return 1;
}
void ptm_close(void*owner){Tokenizer*t=owner;if(t){CloseTokenFile(t->context);free(t);}}
U32 ptm_crc(const char*full){if(!full||strlen(full)>=260)return 0;BasePower p={full};return(U32)powerdict_GetCRCOfBasePower(&p);}
size_t ptm_owner_bytes(void){return sizeof(Tokenizer)+sizeof(TokenizerContext);}
'''
    return code,{'source_sha256':{p:hashlib.sha256(b).hexdigest() for p,b in raw.items()},'original_function_sha256_lf':functions,
                 'fullname':'ParseBasePower.FullName TOK_STRUCTPARAM; no filename inference',
                 'hash':'original powerdict_GetCRCOfBasePower and Crc32cLowerStringHash(0, full_name)',
                 'includes_and_defines':'not supplied; explicit parse error if encountered'}

class OriginalText:
    def __init__(self,library):
        self.lib=ctypes.CDLL(str(library));l=self.lib
        l.ptm_open.argtypes=[ctypes.c_int];l.ptm_open.restype=ctypes.c_void_p
        l.ptm_next.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int)]
        l.ptm_close.argtypes=[ctypes.c_void_p];l.ptm_crc.argtypes=[ctypes.c_char_p];l.ptm_crc.restype=ctypes.c_uint32
        l.ptm_owner_bytes.restype=ctypes.c_size_t
    def tokens(self,fd):
        owner=self.lib.ptm_open(fd)
        if not owner:raise ValueError('original tokenizer allocation/open failed')
        out=ctypes.create_string_buffer(12001);line=ctypes.c_int();quoted=ctypes.c_int()
        try:
            while True:
                result=self.lib.ptm_next(owner,out,len(out),ctypes.byref(line),ctypes.byref(quoted))
                if result==0:return
                if result<0:raise ValueError('original tokenizer error or unsupported include/define owner')
                yield out.value,line.value,bool(quoted.value)
        finally:self.lib.ptm_close(owner)
    def crc(self,name):
        if not isinstance(name,bytes) or not 0<len(name)<260 or any(c<32 or c>126 for c in name):raise ValueError('bounded ASCII fullname required')
        value=self.lib.ptm_crc(name)
        if value==0:raise ValueError('original reserved zero CRC')
        return value

def build(root,work):
    code,provenance=generate(root);source=Path(work)/'power-text-original.c';library=Path(work)/'power-text-original.so';source.write_text(code)
    # Serialize the compiler itself; callers must not wrap the entire script in
    # the same lock (the full input scan does not hold a build token).
    subprocess.run(['flock','/tmp/coh-next-build.lock','cc','-std=gnu99','-O2','-shared','-fPIC','-Wall','-Wextra','-Wno-unused-function',str(source),'-o',str(library)],check=True,capture_output=True,text=True)
    return OriginalText(library),provenance,source
