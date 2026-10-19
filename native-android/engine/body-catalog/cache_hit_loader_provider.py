"""Exact original production ParserLoadFiles cache-hit handle composition.

The older loader fixture-token/nativeDTO bridges are never emitted here.
"""
from pathlib import Path
import hashlib, importlib.util, json, re
HERE=Path(__file__).resolve().parent

def sha(raw): return hashlib.sha256(raw).hexdigest()
def module(name):
 spec=importlib.util.spec_from_file_location('cache_hit_'+name,HERE/(name+'.py'))
 result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def once(text,old,new,count=1):
 if text.count(old)!=count:raise ValueError('Cache-hit adapter boundary changed: '+old[:100])
 return text.replace(old,new,count)
def names(text):
 return text.replace('UnopenedBinary','CacheHitLoader').replace('UNOPENED_BINARY','CACHE_HIT_LOADER').replace('unopened_binary','cache_hit_loader').replace('unopened-binary','cache-hit-loader')

ADAPTERS=r'''
/* Explicit immutable production/SMAR_Error/path shells, never FS selection. */
#include <stdarg.h>
#include <stdlib.h>
typedef char loader_host64[(sizeof(intptr_t)==8&&sizeof(size_t)==8)?1:-1];
typedef int bool;
#define false 0
#define true 1
#define SHARED_MEMORY_PARAM
#define PERFINFO_AUTO_START(a,b) ((void)0)
#define PERFINFO_AUTO_STOP() ((void)0)
#define PERFINFO_AUTO_STOP_START(a,b) ((void)0)
#define OUTPUT_DEBUG 0
#define OUTPUT_VERBOSE 1
#define TODO() ((void)0)
typedef struct{int updated;}ParserLoadInfo;
typedef int(*ParserLoadPreProcessFunc)(ParseTable*,void*);
typedef int(*ParserLoadPostProcessFunc)(ParseTable*,void*);
typedef int(*ParserLoadFinalProcessFunc)(ParseTable*,void*,bool);
typedef struct SharedMemoryHandle{int unused;}SharedMemoryHandle;
static char*lf_filemasks[16];static ParseTable*lf_pti;static void*lf_structptr;
static DefineContext*lf_globaldefines;static int lf_loadedok,lf_ignoreempty;
static int lf_loadedonefile,lf_forcebincreate;static FileList g_parselist,lf_filedates;
static const char*g_StdAdditionalFilePrefixes[]={""};
/* The source's function-static old_filemask has this permanent owned lifetime. */
static char oldmask_arena[MAX_PATH];
static int same(const char*a,const char*b){return a&&b&&!strcmp(a,b);}
static void loader_forbidden(void){assert(!"unqualified loader/development/shared/text branch");abort();}
static void loader_trace(uint32_t value){assert(owner.active&&owner.receipt.trace_count<32);owner.receipt.trace[owner.receipt.trace_count++]=value;}
static int loader_globals_idle(void){
 return !lf_pti&&!lf_structptr&&!lf_globaldefines&&!lf_loadedok&&!lf_ignoreempty&&!lf_loadedonefile&&!lf_forcebincreate&&!g_parselist&&!lf_filedates&&zeros(lf_filemasks,sizeof(lf_filemasks))&&zeros(oldmask_arena,sizeof(oldmask_arena));
}
static void loader_globals_cleanup(void){
 lf_pti=NULL;lf_structptr=NULL;lf_globaldefines=NULL;lf_loadedok=lf_ignoreempty=lf_loadedonefile=lf_forcebincreate=0;
 g_parselist=lf_filedates=NULL;body_wipe(lf_filemasks,sizeof(lf_filemasks));body_wipe(oldmask_arena,sizeof(oldmask_arena));
}
static void loader_free(void*p){assert(!p||p==oldmask_arena);body_wipe(oldmask_arena,sizeof(oldmask_arena));}
static char*loader_strdup(const char*s){assert(same(s,".bp"));memcpy(oldmask_arena,s,4);return oldmask_arena;}
static char*strtok_quoted(char*s,const char*a,const char*b){assert(same(a,";")&&same(b,";"));if(s){assert(s==oldmask_arena&&same(s,".bp"));return s;}return NULL;}
static int loader_easize(const void*p){
 assert(owner.active);if(p==&owner.root.bodyParts){assert(!owner.nodes||owner.root.bodyParts==owner.pointers);return(int)owner.nodes;}loader_forbidden();return 0;
}
#define eaSize(p) loader_easize((const void*)(p))
static void loader_table(ParseTable*t){assert(owner.active&&t==ParseBodyPartBegin);}
#define TEST_PARSE_TABLE(p) loader_table(p)
static bool ParseBoneNames(ParseTable*t,void*r){(void)t;(void)r;owner.receipt.callback_calls++;loader_forbidden();return 0;}
static void writeConsole(int level,const char*format,...){assert(owner.active&&level==OUTPUT_DEBUG&&same(format,"\tParsing %s from %s"));}
static void verbose_printf(const char*format,...){
 assert(owner.active);va_list args;va_start(args,format);const char*name=va_arg(args,const char*);
 if(same(format,"bin file %s is incorrect version\n")){assert(same(name,"bin/BodyParts.bin"));owner.receipt.selector_diagnostics++;}
 else{assert(same(name,"BodyParts.bin")&&(same(format,"ParserLoadFiles: error loading %s, loading text files instead\n")||same(format,"ParserLoadFiles: %s outdated, loading text files instead\n")||same(format,"ParserLoadFiles: couldn't find %s, loading text files instead\n")));owner.receipt.loader_diagnostics++;}
 va_end(args);
}
static SM_AcquireResult sharedMemoryAcquire(SharedMemoryHandle**h,const char*n){assert(owner.active&&same(n,"SM_BodyParts.bin"));loader_trace(3);owner.receipt.acquire_calls++;*h=NULL;return SMAR_Error;}
static char*fileLocateRead(const char*n,char*b){assert(owner.active&&same(n,"bin/BodyParts.bin"));loader_trace(6);owner.receipt.locate_calls++;if(owner.fault==4)return NULL;memcpy(b,n,18);return b;}
/* Qualified safe owned clear dependency for the production return0 branch.
 * This is not original StructClear or engine allocator/destructor qualification. */
static void StructClear(ParseTable*t,void*r){assert(owner.active&&!owner.opened&&!parser_relpath&&t==ParseBodyPartBegin&&r==&owner.root);loader_trace(13);owner.receipt.struct_clear_calls++;owner.root.bodyParts=NULL;}
static void FileListDestroy(FileList*p){(void)p;loader_forbidden();}
static void FileListInsert(FileList*p,const char*n,__time32_t d){(void)p;(void)n;(void)d;loader_forbidden();}
static FileEntry*FileListFind(FileList*p,const char*n){(void)p;(void)n;loader_forbidden();return NULL;}
static int fileDatesEqual(__time32_t a,__time32_t b,int n){(void)a;(void)b;(void)n;loader_forbidden();return 0;}
static __time32_t fileLastChanged(const char*n){(void)n;loader_forbidden();return 0;}
static void DateCheckCallback(void){loader_forbidden();}
static char*addFilePrefix(const char*n,const char*p){(void)n;(void)p;loader_forbidden();return NULL;}
static int fileExists(const char*n){(void)n;loader_forbidden();return 0;}
static void fileScanAllDataDirs(const char*n,void(*callback)(void)){(void)n;(void)callback;loader_forbidden();}
static int ParserLoadFile(const char*n,int e){(void)n;(void)e;loader_forbidden();return 0;}
static void ParserLoadCallback(void){loader_forbidden();}
static char*fileLocateWrite(const char*n,char*b){(void)n;(void)b;loader_forbidden();return NULL;}
static void mkdirtree(const char*n){(void)n;loader_forbidden();}
static int ParserWriteBinaryFile(const char*n,ParseTable*t,void*r,FileList*l,DefineContext*d,int v,StructTypeField f){(void)n;(void)t;(void)r;(void)l;(void)d;(void)v;(void)f;loader_forbidden();return 0;}
static void Errorf(const char*format,...){(void)format;loader_forbidden();}
static void FatalErrorf(const char*format,...){(void)format;loader_forbidden();}
static int loader_printf_forbidden(const char*format,...){(void)format;loader_forbidden();return 0;}
#define printf loader_printf_forbidden
static void*sharedMemoryGetDataPtr(SharedMemoryHandle*h){(void)h;loader_forbidden();return NULL;}
static void sharedMemorySetMode(SharedMemoryMode m){(void)m;loader_forbidden();}
static size_t StructGetMemoryUsage(ParseTable*t,void*r,size_t n){(void)t;(void)r;(void)n;loader_forbidden();return 0;}
static void sharedMemorySetSize(SharedMemoryHandle*h,size_t n){(void)h;(void)n;loader_forbidden();}
static void*sharedMemoryAlloc(SharedMemoryHandle*h,size_t n){(void)h;(void)n;loader_forbidden();return NULL;}
static void*StructCompress(ParseTable*t,void*r,size_t n,void*a,void*(*alloc)(void*,size_t),void*h){(void)t;(void)r;(void)n;(void)a;(void)alloc;(void)h;loader_forbidden();return NULL;}
static void sharedMemoryCommit(SharedMemoryHandle*h){(void)h;loader_forbidden();}
static void sharedMemoryUnlock(SharedMemoryHandle*h){(void)h;loader_forbidden();}
static void sharedHeapMemoryManagerLock(void){loader_forbidden();}
static void sharedHeapMemoryManagerUnlock(void){loader_forbidden();}
'''
OBSERVE_PERSIST=r'''
static SimpleBufHandle observed_ParserIsPersistNewer(const char*d,const char*m,const char*n,ParseTable*t,DefineContext*defs){
 assert(owner.active&&same(d,"Defs\\UI")&&same(m,".bp")&&same(n,"bin/BodyParts.bin")&&t==ParseBodyPartBegin&&!defs);loader_trace(7);owner.receipt.persist_calls++;
 SimpleBufHandle h=ParserIsPersistNewer(d,m,n,t,defs);
 if(h){assert(owner.opened&&h==(SimpleBufHandle)&owner.buffer&&SimpleBufTell(h)>0);owner.receipt.selected_handle=1;owner.receipt.header_end=(uint32_t)SimpleBufTell(h);loader_trace(10);}
 return h;
}
#define ParserIsPersistNewer observed_ParserIsPersistNewer
static int observed_ParserReadBinaryFile(SimpleBufHandle h,char*n,ParseTable*t,void*r,FileList*l,DefineContext*d){
 assert(owner.active&&owner.opened&&owner.receipt.selected_handle==1&&h==(SimpleBufHandle)&owner.buffer&&same(n,"bin/BodyParts.bin")&&t==ParseBodyPartBegin&&r==&owner.root&&!l&&!d);
 loader_trace(11);owner.receipt.binary_calls++;owner.receipt.supplied_handle_matched=1;int accepted=ParserReadBinaryFile(h,n,t,r,l,d);
 owner.receipt.source_result=(uint32_t)accepted;return accepted;
}
#define ParserReadBinaryFile observed_ParserReadBinaryFile
'''
OBSERVE_LOAD=r'''
#undef free
#undef strdup
static bool observed_ParserLoadFiles(const char*d,const char*m,const char*n,int f,ParseTable*t,void*r,DefineContext*defs,ParserLoadInfo*i,ParserLoadPreProcessFunc pre){
 assert(owner.active&&same(d,"Defs\\UI")&&same(m,".bp")&&same(n,"BodyParts.bin")&&!f&&t==ParseBodyPartBegin&&r==&owner.root&&!defs&&!i&&pre==ParseBoneNames);loader_trace(4);owner.receipt.load_calls++;return ParserLoadFiles(d,m,n,f,t,r,defs,i,pre);
}
#define ParserLoadFiles observed_ParserLoadFiles
'''
OBSERVE_SHARED=r'''
#undef ParserLoadFiles
static bool observed_ParserLoadFilesShared(const char*s,const char*d,const char*m,const char*n,int f,ParseTable*t,void*r,size_t size,DefineContext*defs,ParserLoadInfo*i,ParserLoadPreProcessFunc pre,ParserLoadPostProcessFunc post,ParserLoadFinalProcessFunc final){
 assert(owner.active&&same(s,"SM_BodyParts.bin")&&same(d,"Defs\\UI")&&same(m,".bp")&&same(n,"BodyParts.bin")&&!f&&t==ParseBodyPartBegin&&r==&owner.root&&size==sizeof(BodyPartList)&&!defs&&!i&&pre==ParseBoneNames&&!post&&!final);loader_trace(2);owner.receipt.shared_calls++;
 int result=ParserLoadFilesShared(s,d,m,n,f,t,r,size,defs,i,pre,post,final);owner.receipt.loader_return=(uint32_t)result;loader_trace(16);return result;
}
#define ParserLoadFilesShared observed_ParserLoadFilesShared
'''

def build(root,work):
 root,work=Path(root).resolve(),Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
 pins_path=HERE/'cache-hit-loader-source-pins.json';pins=json.loads(pins_path.read_text());frozen={}
 for name,pin in pins['files'].items():
  raw=(root/name).read_bytes()
  if len(raw)!=pin['bytes']or sha(raw)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=pin['blob_sha1']:raise ValueError('Cache-hit source pin changed: '+name)
  frozen[name]=raw
 unopened,body,loader=module('unopened_binary_provider'),module('body_read_provider'),module('body_part_loader_provider')
 path,proof=unopened.build(root,work);code=Path(path).read_text();wrapper=code[code.index('\n#undef FileListRead\n'):];code=code[:-len(wrapper)]
 # Explicit shell mutations only; original source bodies are checked below.
 helper_at=code.index('\nsize_t unopened_binary_owner_bytes(void)');helper=code[helper_at:];code=code[:helper_at]
 code=once(code,'int unopened_binary_is_idle(void){','static int loader_globals_idle(void);\nstatic void loader_globals_cleanup(void);\nstatic void loader_trace(uint32_t);\nint unopened_binary_is_idle(void){')
 code=once(code,'&&schema_adler_is_idle();','&&schema_adler_is_idle()&&loader_globals_idle();')
 code=once(code,'owner.receipt.open_calls++;','owner.receipt.open_calls++;loader_trace(9);')
 code=once(code,'owner.receipt.source_close_calls++;','owner.receipt.source_close_calls++;loader_trace(12);')
 code=once(code,'owner.receipt.crc_calls++;','owner.receipt.crc_calls++;loader_trace(8);')
 code=once(code,'owner.receipt.mode_calls++;return 1;','owner.receipt.mode_calls++;loader_trace(5);return 1;')
 code=once(code,'owner.body_start=(uint32_t)SimpleBufTell(file);','owner.body_start=(uint32_t)SimpleBufTell(file);loader_trace(15);')
 code=once(code,'owner.receipt.filelist_calls++;','owner.receipt.filelist_calls++;loader_trace(14);')
 text={name:raw.decode().replace('\r\n','\n')for name,raw in frozen.items()}
 declarations=[]
 for n in('SM_AcquireResult','SharedMemoryMode'):
  declarations.append(re.search(r'typedef enum '+n+r'\s*\{.*?\}\s*'+n+';',text[loader.SHARED_H],re.S)[0])
 declarations.append(re.search(r'typedef struct PLFSHeader\s*\{.*?\}\s*PLFSHeader\s*;',text[loader.PARSER_C],re.S)[0])
 declarations.extend(re.search(r'^#define\s+'+n+r'[^\n]*',text[loader.PARSER_H],re.M)[0]for n in('TOK_SERVER_ONLY','TOK_CLIENT_ONLY'))
 declarations.append(re.search(r'^#define\s+xcase\s+break;case\s*$',text[loader.STDTYPES_H],re.M)[0])
 declarations.extend(line for line in text[loader.PARSER_H].splitlines()if re.match(r'#define\s+PARSER_[A-Z]+\s',line))
 functions={n:loader.extract(text[p],n)for p,ns in((loader.PARSER_C,('ParserIsPersistNewer','ParserLoadFiles','sharedMemoryAllocAdapter','ParserLoadFilesShared')),(loader.BODY_C,('bpReadBodyPartFiles','GetBodyPartCount')))for n in ns}
 # Restore unobserved source helpers after binary source; loader source gets
 # dedicated observers without altering a character inside any original body.
 code+='\n#undef FileListRead\n#undef ParserReadBinaryTable\n#undef SimpleBufRead\n#undef SimpleBufSeek\n#undef printf\n#undef calloc\n#undef eaCreate\n#undef eaPush\n'+'\n'.join(declarations)+'\n'+ADAPTERS
 code+='#define ParseTableCRC unopened_original_crc\n'+functions['ParserIsPersistNewer']+OBSERVE_PERSIST
 code+='#define free loader_free\n#define strdup loader_strdup\n'+functions['ParserLoadFiles']+OBSERVE_LOAD+functions['sharedMemoryAllocAdapter']+functions['ParserLoadFilesShared']+OBSERVE_SHARED
 code+='#define bodyPartList owner.root\n'+functions['bpReadBodyPartFiles']+'\n#undef ParserLoadFilesShared\n'+functions['GetBodyPartCount']+'\n#undef bodyPartList\n#undef ParseTableCRC\n#undef ParserReadBinaryFile\n#undef ParserIsPersistNewer\n'
 wrapper=helper+wrapper
 wrapper=once(wrapper,'fault>3','fault>4')
 wrapper=once(wrapper,'if(fault>=2){','if(fault==2||fault==3){')
 wrapper=once(wrapper,' int accepted=ParserReadBinaryFile(NULL,"bin/BodyParts.bin",ParseBodyPartBegin,&owner.root,NULL,NULL);',' owner.receipt.entry_calls++;loader_trace(1);bpReadBodyPartFiles();\n  int accepted=(int)owner.receipt.loader_return;')
 wrapper=once(wrapper,'owner.receipt.source_result=(uint32_t)accepted;','owner.receipt.getter_count=accepted?(uint32_t)GetBodyPartCount():0;')
 wrapper=once(wrapper,' owner.receipt.status=(uint32_t)status;', ' owner.receipt.status=(uint32_t)status;')if False else wrapper
 wrapper=once(wrapper,'assert(!owner.opened&&!parser_relpath);body_wipe(&owner', 'assert(!owner.opened&&!parser_relpath);loader_globals_cleanup();body_wipe(&owner')
 # The parent owner-bytes helper is inside wrapper and must include globals.
 wrapper=once(wrapper,'return sizeof(owner)+sizeof(crc_owner)+sizeof(parser_relpath);','return sizeof(owner)+sizeof(crc_owner)+sizeof(parser_relpath)+sizeof(lf_filemasks)+sizeof(lf_pti)+sizeof(lf_structptr)+sizeof(lf_globaldefines)+sizeof(lf_loadedok)+sizeof(lf_ignoreempty)+sizeof(lf_loadedonefile)+sizeof(lf_forcebincreate)+sizeof(g_parselist)+sizeof(lf_filedates)+sizeof(g_StdAdditionalFilePrefixes)+sizeof(oldmask_arena)+sizeof(char*)+sizeof(bool)+sizeof(void*);')
 header=(work/'unopened-binary-provider.h').read_text()
 header=once(header,'uint32_t source_crc,source_calls,','uint32_t entry_calls,shared_calls,acquire_calls,load_calls,locate_calls,persist_calls,binary_calls,callback_calls,struct_clear_calls,loader_return,getter_count,selected_handle,supplied_handle_matched,selector_diagnostics,loader_diagnostics,trace_count,trace[32];\n uint32_t source_crc,source_calls,')
 header=once(header,'fault0 normal,1 owned open refusal,2 row-arena reservation refusal,3 crypto-object reservation refusal;', 'fault0 normal,1 owned open refusal,2 row-arena reservation refusal,3 crypto-object reservation refusal,4 fixture missing-cache path;')
 code=names(code+wrapper);header=names(header)
 (work/'cache-hit-loader-provider.h').write_text(header);output=work/'cache-hit-loader-provider.c';output.write_text(code)
 whole=proof['whole_function_sha256_lf']|{n:sha(v.encode())for n,v in functions.items()}
 for n,digest in whole.items():
  if n.startswith('cryptAdler'):continue
  candidates=[]
  for raw in frozen.values():
   try:v=body.extract(raw.decode().replace('\r\n','\n'),n)
   except ValueError:continue
   if sha(v.encode())==digest:candidates.append(v)
  if len(candidates)!=1 or code.count(candidates[0])!=1:raise ValueError('Original source function changed or duplicated '+n)
 if any((root/n).read_bytes()!=raw for n,raw in frozen.items()):raise ValueError('Source changed during composition')
 return output,{'schema':'coh-original-cache-hit-loader-provider-v1','source_baseline_revision':pins['baseline_revision'],'source_sha256':proof['source_sha256']|{n:sha(v)for n,v in frozen.items()},'source_pins_sha256':sha(pins_path.read_bytes()),'whole_function_sha256_lf':whole,'source_stable_before_after':True,'original_dependency_composition':{k:proof[k]for k in('body_dependency_source_audits','schema_dependency_source_audits','allocation_failure_scope','cleanup')},'composition':'Unchanged bpReadBodyPartFiles -> ParserLoadFilesShared SMAR_Error -> ParserLoadFiles -> actual ParserIsPersistNewer/source CRC/CryptoPP/SerializeReadOpen ignoreCRC1 -> SAME supplied live handle ParserReadBinaryFile -> FileListRead(NULL)/body/SerializeClose. One original open and one source close, no native DTO or fixture-token bridges.','explicit_environment_shells':'Immutable production1/SMAR_Error/fileLocateRead fixture path; safe owned StructClear only on production return0. No filesystem selection, mode helper or original shared memory/allocator qualification. Text/preprocessor/dev/shared-generation helpers trap.','source_token_flags':{'TOK_SERVER_ONLY':'original extracted macro','TOK_CLIENT_ONLY':'original extracted macro','xcase':'original extracted break;case macro'},'global_cleanup':'Permanent oldmask arena survives original static pointer; normal return resets recursive_call. All exposed globals and arena wiped; actual CryptoPP delete/TLS reset; source closes handle. Atomic output after cleanup.','preflight_and_reservations':'Complete typed source-entered extents, span/context and overflow-safe budget preflight inherited. Fixed row/crypto reservation refusals before source; no unsafe original NULL/new failure simulated.','call_order_trace':{'1':'bp entry','2':'shared loader','3':'SMAR_Error acquisition shell','4':'ParserLoadFiles','5':'production mode shell query','6':'fixture locate shell','7':'ParserIsPersistNewer','8':'actual CRC','9':'original open attempt','10':'selected live handle','11':'reader supplied SAME live handle','12':'original close','13':'safe owned clear shell','14':'FileListRead(NULL)','15':'original root binary table','16':'shared source return'},'mutable_static_charge':'Owner/CRC/global/mask storage plus exact sizeof(char*) old_filemask, sizeof(bool) recursive_call and sizeof(void*) C++ TLS Adler pointer; old_filemask intentionally retains only the permanent wiped owned arena.','stack_reserve_bytes':98304,'actual_ParseTableCRC_computed':True,'production_ignoreCRC1_preserved':True,'current_Map_runtime_observed':False,'runtime_body_catalog_admitted':False,'source_generation_admitted':False,'authority_or_application_ack':False,'adler_cpp_path':proof['adler_cpp_path'],'crypto_dependency':proof['crypto_dependency']}
