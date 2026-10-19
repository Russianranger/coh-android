"""Source-generated BoneIdEnum provider; no runtime catalog or generation admission.

Build the pinned original StructParser target, generate from exact bones.h in an
isolated tree, then expose the original enum/table/lookup closure to qualification.
The generated table is never constructed from a handwritten lookup dictionary.
"""
from pathlib import Path
import hashlib,json,os,re,subprocess

HERE=Path(__file__).resolve().parent
PREFIX='upstream/ouroboros/'
TOOL=PREFIX+'Utilities/StructParser/'
BONES=PREFIX+'Common/seq/bones.h'
BONE_C=PREFIX+'Common/seq/bones.c'
DEFINE_H=PREFIX+'libs/UtilitiesLib/include/utilitieslib/utils/structDefines.h'
DEFINE_C=PREFIX+'libs/UtilitiesLib/src/utils/structDefines.c'
BODY_PART_C=PREFIX+'Common/gameData/BodyPart.c'
ROW_MAX=256
QUERY_MAX=259

def sha(value):return hashlib.sha256(value).hexdigest()

def extract(text,name):
    match=re.search(r'^[^\n{};]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
    if not match:raise ValueError('missing original function '+name)
    at=text.index('{',match.start())+1;depth=1
    while depth:
        if at>=len(text):raise ValueError('unterminated original function '+name)
        depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[match.start():at]+'\n'

def parse_reference(header):
    """Independent restricted original enum projection, never generator input."""
    source=re.sub(r'/\*.*?\*/|//[^\n]*','',header,flags=re.S)
    match=re.search(r'AUTO_ENUM\s*;\s*typedef\s+enum\s+BoneId\s*\{([^{}]*)\}\s*BoneId\s*;',source,re.S)
    if not match:raise ValueError('missing original AUTO_ENUM BoneId')
    entries=[];value=-1
    for member in match[1].split(','):
        member=member.strip()
        if not member:continue
        item=re.fullmatch(r'(BONEID_[A-Z0-9_]+)(?:\s*=\s*(-?[0-9]+))?',member)
        if not item:raise ValueError('unsupported original BoneId expression')
        value=int(item[2])if item[2]is not None else value+1
        if value<-(2**31)or value>=2**31:raise ValueError('original BoneId outside signed32')
        if any(e['symbol']==item[1]for e in entries):raise ValueError('duplicate original BoneId symbol')
        entries.append({'symbol':item[1],'value':value})
    if not entries or len(entries)>ROW_MAX:raise ValueError('original BoneId row bound')
    common=os.path.commonprefix([e['symbol']for e in entries])
    if not common:raise ValueError('original BoneId lacks common prefix')
    for entry in entries:
        entry['name']=entry['symbol'][len(common):]
        if not entry['name']or len(entry['name'])>QUERY_MAX:raise ValueError('original BoneId name bound')
    values={entry['symbol']:entry['value']for entry in entries}
    if not all(name in values for name in('BONEID_COUNT','BONEID_INVALID','BONEID_DEFAULT')):raise ValueError('original BoneId sentinels absent')
    if values['BONEID_INVALID']!=-1 or values['BONEID_DEFAULT']!=0:raise ValueError('original BoneId sentinel semantics changed')
    count=values['BONEID_COUNT']
    if not 0<count<ROW_MAX or [e['value']for e in entries[:count]]!=list(range(count))or entries[count]['symbol']!='BONEID_COUNT':raise ValueError('original BoneId ordinal domain changed')
    return {'entries':entries,'bone_count':count,'query_max':QUERY_MAX,'row_max':ROW_MAX,'stripped_prefix':common}

def _run(command,work,label,timeout=180):
    stdout=work/(label+'.stdout');stderr=work/(label+'.stderr')
    environment=dict(os.environ)
    for name in('CC','CXX','CFLAGS','CXXFLAGS','CPPFLAGS','LDFLAGS','CPATH','CPLUS_INCLUDE_PATH','LIBRARY_PATH','SDKROOT'):
        environment.pop(name,None)
    with stdout.open('wb')as out,stderr.open('wb')as err:
        result=subprocess.run(list(map(str,command)),cwd=work,env=environment,stdout=out,stderr=err,timeout=timeout)
    if stdout.stat().st_size>1024*1024 or stderr.stat().st_size>1024*1024:raise ValueError('provider tool output exceeds diagnostic bound')
    if result.returncode:raise RuntimeError(label+' refused: '+stderr.read_text(errors='replace')[-2000:])
    return stdout,stderr

def build(root,work):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    pins=json.loads((HERE/'source-pins.json').read_text())
    frozen={}
    for name,pin in pins['files'].items():
        data=(root/name).read_bytes()
        if len(data)!=pin['bytes']or sha(data)!=pin['sha256']or hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=pin['blob_sha1']:raise ValueError('original source pin changed: '+name)
        frozen[name]=data
    def verify():
        if any((root/name).read_bytes()!=data for name,data in frozen.items()):raise ValueError('source changed during provider generation')
    text={name:data.decode().replace('\r\n','\n')for name,data in frozen.items()}
    cmake=text[TOOL+'CMakeLists.txt']
    match=re.search(r'set\(STRUCTPARSER_SOURCES\s+(.*?)\)',cmake,re.S)
    if not match or 'target_compile_features(StructParser PRIVATE cxx_std_17)'not in cmake:raise ValueError('original StructParser target changed')
    sources=match[1].split()
    if len(sources)>32 or any(not re.fullmatch(r'src/[A-Za-z0-9_]+\.cpp',name)or TOOL+name not in frozen for name in sources):raise ValueError('original tool target closure refused')
    # Copy the full pinned target closure; generator never writes into upstream.
    isolated=work/'original-tool';isolated.mkdir(exist_ok=True)
    for name,data in frozen.items():
        if name.startswith(TOOL):
            target=isolated/name[len(TOOL):];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    executable=work/'StructParser'
    compile_command=['c++','-std=c++17','-O2',*[str(isolated/name)for name in sources],'-o',str(executable)]
    compile_out,compile_err=_run(compile_command,work,'compile')
    tree=work/'isolated-input';common=tree/'Common';project=tree/'BoneProvider';source=project/'src'
    (common/'seq').mkdir(parents=True,exist_ok=True);source.mkdir(parents=True,exist_ok=True)
    (common/'seq/bones.h').write_bytes(frozen[BONES])
    manifest=tree/'sources.txt';manifest.write_text(str(common/'seq/bones.h')+'\n')
    generate_command=[str(executable),'--target','BoneProvider','--source-dir',str(source),'--common-dir',str(common),'--project-dir',str(project),'--kind','library','--sources-file',str(manifest),'--state-dir',str(work/'parser-state'),'--force']
    generate_out,generate_err=_run(generate_command,work,'generator',60)
    table_path=source/'AutoGen/bones_h_ast.c'
    generated=table_path.read_bytes()
    if len(generated)>65536:raise ValueError('generated BoneIdEnum output exceeds bound')
    generated_text=generated.decode().replace('\r\n','\n')
    table=re.search(r'StaticDefineInt\s+BoneIdEnum\[\]\s*=\s*\{.*?\n\};',generated_text,re.S)
    if not table:raise ValueError('actual generator did not emit BoneIdEnum')
    reference=parse_reference(text[BONES])
    rows=re.findall(r'\{\s*"([^"\\]*)"\s*,\s*(BONEID_[A-Z0-9_]+)\s*\}',table[0])
    if rows!=[(entry['name'],entry['symbol'])for entry in reference['entries']]:raise ValueError('actual generator rows differ from independent original enum projection')
    if table[0].count('DEFINE_INT')!=1 or table[0].count('DEFINE_END')!=1:raise ValueError('actual generator markers changed')
    enum=re.search(r'typedef\s+enum\s+BoneId\s*\{.*?\}\s*BoneId\s*;',text[BONES],re.S)[0]
    types='\n'.join(re.search(r'typedef struct '+name+r'\s*\{.*?\}\s*'+name+r'\s*;',text[DEFINE_H],re.S)[0]for name in('StaticDefine','StaticDefineInt'))
    definitions='\n'.join(line for line in text[DEFINE_H].splitlines()if re.match(r'#define\s+(?:DM_[A-Z]+|DEFINE_INT|DEFINE_END)\s',line))
    functions={'bone_IdFromName':extract(text[BONE_C],'bone_IdFromName'),'bone_IdIsValid':extract(text[BONES],'bone_IdIsValid'),'StaticDefineLookup':extract(text[DEFINE_C],'StaticDefineLookup'),'StaticDefineIntLookup':extract(text[DEFINE_H],'StaticDefineIntLookup'),'StaticDefineIntGetInt':extract(text[DEFINE_H],'StaticDefineIntGetInt')}
    callback=extract(text[BODY_PART_C],'ParseBoneNames')
    if callback.count('bone_IdFromName(')!=3:raise ValueError('original body-part callback dependency changed')
    preamble='''/* Source-provider qualification ONLY. No runtime catalog or generation. */
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <limits.h>
#define INLINEDBG inline
#define STATIC_ASSERT(x) do { typedef char source_assert[(x)?1:-1];(void)sizeof(source_assert); } while(0)
#define U32_TO_PTR(x) ((void*)(uintptr_t)(x))
#define assertmsg(x,m) assert(x)
#define stricmp strcasecmp
typedef void DefineContext;
static const char* DefineLookup(DefineContext*c,const char*k){(void)c;(void)k;assert(0);abort();}
static void FatalErrorf(const char*f,...){(void)f;assert(0);abort();}
/* Explicit host itoa adapter: only signed enum result values, decimal. */
static char* itoa(intptr_t value,char*out,int radix){assert(radix==10&&value>=INT_MIN&&value<=INT_MAX);int n=snprintf(out,200,"%lld",(long long)value);assert(n>0&&n<200);return out;}
'''
    assertions='''
typedef char same_size[(sizeof(StaticDefine)==sizeof(StaticDefineInt))?1:-1];
typedef char same_key[(offsetof(StaticDefine,key)==offsetof(StaticDefineInt,key))?1:-1];
typedef char same_value[(offsetof(StaticDefine,value)==offsetof(StaticDefineInt,value))?1:-1];
typedef char same_display[(offsetof(StaticDefine,display)==offsetof(StaticDefineInt,display))?1:-1];
'''
    accessors='''
int sourcebone_lookup(const char*name){return bone_IdFromName(name);}
int sourcebone_is_valid(int value){return bone_IdIsValid((BoneId)value);}
unsigned sourcebone_row_count(void){return (unsigned)(sizeof(BoneIdEnum)/sizeof(BoneIdEnum[0])-2u);}
const char*sourcebone_row_name(unsigned i){return i<sourcebone_row_count()?BoneIdEnum[i+1u].key:NULL;}
int sourcebone_row_value(unsigned i){return i<sourcebone_row_count()?(int)BoneIdEnum[i+1u].value:INT_MIN;}
'''
    provider=work/'bone-enum-provider.c'
    provider.write_text(preamble+enum+'\n'+types+'\n'+definitions+'\n'+assertions+table[0]+'\n'+functions['StaticDefineLookup']+functions['StaticDefineIntLookup']+functions['StaticDefineIntGetInt']+functions['bone_IdFromName']+functions['bone_IdIsValid']+accessors)
    commands_path=work/'commands.json';commands_path.write_text(json.dumps({'compile':compile_command,'generator':generate_command},indent=2)+'\n')
    verify()
    proof={'schema':'coh-original-bone-enum-provider-v1','source_sha256':{name:sha(data)for name,data in frozen.items()},'source_pins_sha256':sha((HERE/'source-pins.json').read_bytes()),'source_baseline_revision':pins['baseline_revision'],'source_stable_before_after':True,'original_tool_target_sources':sources,'original_tool_target_build':'Direct C++17 compilation of exact source list from pinned original CMake target; CMake not invoked. No tool source modifications.','tool_compiler_command':compile_command,'tool_binary_sha256':sha(executable.read_bytes()),'generator_command':generate_command,'generated_table_sha256':sha(generated),'generated_table_bytes':len(generated),'generated_row_count':len(rows),'provider_c_sha256':sha(provider.read_bytes()),'whole_function_sha256_lf':{name:sha(value.encode())for name,value in functions.items()},'original_BoneIdEnum_table_extracted_unchanged':True,'original_enum_lookup_requires_no_stash':True,'host_adapters':['intptr_t/char* source StaticDefine view with asserted three-field offsets/size; compile -fno-strict-aliasing','stricmp uses host strcasecmp under C locale; ASCII queries only','itoa decimal signed enum result uses bounded snprintf200','unreachable dynamic-list and fatal profile branches trap'],'query_max_is_wrapper_policy':QUERY_MAX,'row_max_is_wrapper_policy':ROW_MAX,'generated_native_lookup_sanitizable':True,'original_generator_sanitized':False,'ParseBoneNames_executed':False,'current_Map_runtime_observed':False,'body_catalog_admitted':False,'source_generation_admitted':False,'authority_or_application_ack':False,'evidence_paths':{'generated_table':str(table_path),'provider_c':str(provider),'compile_stdout':str(compile_out),'compile_stderr':str(compile_err),'generator_stdout':str(generate_out),'generator_stderr':str(generate_err),'commands':str(commands_path)}}
    proof['audited_not_executed_callback']={'path':BODY_PART_C,'function':'ParseBoneNames','sha256_lf':sha(callback.encode()),'bone_IdFromName_callsites':3,'relationship':'Original postload callback resolves name_geo or name_geoR/L through this provider. Callback/runtime initialization is NOT executed or admitted.'}
    return provider,proof,reference
