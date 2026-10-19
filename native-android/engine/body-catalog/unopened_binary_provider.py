"""Whole unchanged unopened ParserReadBinaryFile with exact fixed source schema."""
from pathlib import Path
import hashlib, importlib.util, json, re

HERE = Path(__file__).resolve().parent

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def module(name):
    spec = importlib.util.spec_from_file_location('unopened_' + name, HERE / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

def once(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError('Composition adapter boundary changed: ' + old[:80])
    return text.replace(old, new, count)

def names(text):
    return text.replace('BodyRead', 'UnopenedBinary').replace('BODYREAD', 'UNOPENED_BINARY').replace('bodyread', 'unopened_binary').replace('body-read', 'unopened-binary')

CRC_ADAPTERS = r'''
typedef ParseInfoFieldUsage(*interpretfield_f)(ParseTable*,int,ParseInfoField);
typedef struct{int active;SchemaCrcResult candidate;}UnopenedCrcOwner;
static UnopenedCrcOwner crc_owner;
static void UpdateCrcFromDefineList(DefineContext*p){(void)p;assert(!"unqualified dynamic defines");}
static void UpdateCrcFromStaticDefines(void*p){(void)p;assert(!"unqualified static defines");}
void cryptAdler32Init(void);void cryptAdler32Update(const U8*,int);U32 cryptAdler32Final(void);
int schema_adler_is_idle(void);void schema_adler_cleanup(void);size_t schema_adler_object_bytes(void);
static void observed_update(const U8*data,int len){
 assert(owner.active&&crc_owner.active&&len>=0&&(data||!len));SchemaCrcResult*r=&crc_owner.candidate;
 assert(r->update_calls<SCHEMA_CRC_UPDATE_MAX&&(uint32_t)len<=SCHEMA_CRC_TRACE_MAX-r->stream_bytes);
 r->update_lengths[r->update_calls++]=(uint32_t)len;
 if(len)memcpy(r->stream+r->stream_bytes,data,(size_t)len);
 r->stream_bytes+=(uint32_t)len;
 if(len==4){
  for(unsigned i=0;i<1;i++)if(data==(const U8*)&ParseBodyPartBegin[i].type)r->visited_fields++;
  for(unsigned i=0;i<13;i++)if(data==(const U8*)&ParseBodyPart[i].type)r->visited_fields++;
 }
 cryptAdler32Update(data,len);
}
#define cryptAdler32Update observed_update
'''

CRC_BRIDGE = r'''
#undef cryptAdler32Update
static int unopened_original_crc(ParseTable*t,DefineContext*d){
 assert(owner.active&&t==ParseBodyPartBegin&&!d&&!crc_owner.active);
 owner.receipt.crc_calls++;crc_owner.active=1;int value=ParseTableCRC(t,d);
 memcpy(&owner.receipt.source_crc,&value,4);return value;
}
/* Immutable fixture shell, not the production helper or engine globals. */
static int isProductionMode(void){assert(owner.active);owner.receipt.mode_calls++;return 1;}
#define ParseTableCRC unopened_original_crc
'''

def build(root, work):
    root, work = Path(root).resolve(), Path(work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    pins_path = HERE / 'unopened-binary-source-pins.json'
    pins = json.loads(pins_path.read_text())
    frozen = {}
    for name, pin in pins['files'].items():
        raw = (root / name).read_bytes()
        if (len(raw) != pin['bytes'] or sha(raw) != pin['sha256'] or
                hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() != pin['blob_sha1']):
            raise ValueError('Unopened original source pin changed: ' + name)
        frozen[name] = raw
    body, schema = module('body_read_provider'), module('schema_crc_provider')
    body_path, body_proof = body.build(root, work)
    schema_path, schema_proof = schema.build(root, work)
    body_code = Path(body_path).read_text()
    if not body_code.endswith(body.WRAPPER):
        raise ValueError('Body composition boundary changed')
    code = body_code[:-len(body.WRAPPER)]
    # Changes below affect explicit adapters/dispatch holders only. Every source
    # function is subsequently checked byte-for-byte against the pinned original.
    trap = 'static int ParseTableCRC(ParseTable*t,void*d){(void)t;(void)d;assert(!"actual ParseTableCRC unavailable");return 0;}\nstatic int isProductionMode(void){assert(!"unopened ParserReadBinaryFile route unavailable");return 0;}\n'
    if code.count(trap) != 1:
        raise ValueError('Unopened trap boundary changed')
    code = once(code, trap, '', 1)
    code = once(code, 'int active,opened;size_t input_size;', 'int active,opened;uint32_t fault;size_t input_size;', 1)
    code = once(code, 'owner.receipt.open_calls++;\n owner.buffer.data=', 'owner.receipt.open_calls++;\n if(owner.fault==1)return NULL;\n owner.buffer.data=', 1)
    code = once(code, 'return !parser_relpath&&zeros(&owner,sizeof(owner));', 'return !parser_relpath&&zeros(&owner,sizeof(owner))&&zeros(&crc_owner,sizeof(crc_owner))&&schema_adler_is_idle();', 1)
    # Forward definition is needed by idle/budget diagnostics before the body
    # adapters. The only additional original declarations are the CRC enums.
    schema_text = Path(schema_path).read_text()
    extra = []
    for name in ('ParseInfoField', 'ParseInfoFieldUsage'):
        match = re.search(r'typedef enum ' + name + r'\s*\{.*?\}\s*' + name + ';', schema_text, re.S)
        if not match:
            raise ValueError('Missing CRC enum ' + name)
        extra.append(match[0])
    extra.append('#define TOK_STRUCTPARAM (1 << 20)')
    # Audit the source macro instead of silently inventing an option value.
    original_macro = re.search(r'^#define\s+TOK_STRUCTPARAM[^\n]*', frozen[body.PARSER_H].decode(), re.M)[0]
    extra[-1] = original_macro
    typedef_at = code.index('typedef int(*readbin_f)')
    owner_decl = 'typedef struct{int active;SchemaCrcResult candidate;}UnopenedCrcOwner;\nstatic UnopenedCrcOwner crc_owner;\nint schema_adler_is_idle(void);\n'
    code = code[:typedef_at] + '\n#include "schema-crc-provider.h"\n' + '\n'.join(extra) + '\n' + owner_decl + code[typedef_at:]
    code = once(code, 'typedef struct{readbin_f readbin;}BodyHandler;', 'typedef ParseInfoFieldUsage(*interpretfield_f)(ParseTable*,int,ParseInfoField);\ntypedef struct{readbin_f readbin;interpretfield_f interpretfield;}BodyHandler;', 1)
    crc_adapters = CRC_ADAPTERS.replace('typedef ParseInfoFieldUsage(*interpretfield_f)(ParseTable*,int,ParseInfoField);\n', '').replace('typedef struct{int active;SchemaCrcResult candidate;}UnopenedCrcOwner;\nstatic UnopenedCrcOwner crc_owner;\n', '')
    # Insert originals before the already source-audited readbin dispatch.
    dispatch_at = code.index('static const BodyHandler g_arraytable[3]={{nonarray_readbin}')
    originals = ''.join(schema.extract(frozen[schema.PARSER_C].decode().replace('\r\n', '\n'), n) for n in ('ignore_interpretfield', 'number_interpretfield', 'string_interpretfield', 'struct_interpretfield'))
    observers = ''.join('static ParseInfoFieldUsage observed_' + n + '(ParseTable*t,int c,ParseInfoField f){assert(owner.active&&crc_owner.active);crc_owner.candidate.interpret_calls++;return ' + n + '(t,c,f);}\n' for n in ('ignore_interpretfield', 'number_interpretfield', 'string_interpretfield', 'struct_interpretfield'))
    code = code[:dispatch_at] + crc_adapters + originals + observers + code[dispatch_at:]
    mapping = schema_proof['dispatch_source_audit']['interpretfield_tokens']
    for token, function in mapping.items():
        pattern = r'(\[' + re.escape(token) + r'\]=\{[^{}]+)(\})'
        code, count = re.subn(pattern, r'\1,observed_' + function + r'\2', code)
        if count != 1:
            raise ValueError('Combined exact dispatch absent ' + token)
    crc_functions = ''.join(schema.extract(frozen[schema.PARSER_C].decode().replace('\r\n', '\n'), n) for n in ('UpdateCRCFromParseInfo', 'ParseTableCRC'))
    file_function = body.extract(frozen[body.PARSER_C].decode().replace('\r\n', '\n'), 'ParserReadBinaryFile')
    if not code.endswith(file_function):
        raise ValueError('Original unopened file boundary changed')
    code = code[:-len(file_function)] + crc_functions + CRC_BRIDGE + file_function + '\n#undef ParseTableCRC\n'
    wrapper = body.WRAPPER
    wrapper = once(wrapper, 'size_t charge=sizeof(owner)+BODYREAD_STACK_RESERVE;', 'size_t charge=unopened_binary_owner_bytes()+BODYREAD_STACK_RESERVE+schema_adler_object_bytes();')
    wrapper = once(wrapper, 'if(ignore_crc>1||', 'if(ignore_crc!=1||build_crc>3||')
    wrapper = once(wrapper, 'status=framing(bytes,build_crc,ignore_crc,&result);', 'status=framing(bytes,0,1,&result);')
    wrapper = once(wrapper, 'result.stage=BODYREAD_STAGE_DIGEST;', 'if(build_crc>=2){result.stage=BODYREAD_STAGE_RESERVATION;result.status=COH_LIMIT;*receipt=result;return COH_LIMIT;}\n result.stage=BODYREAD_STAGE_DIGEST;')
    wrapper = once(wrapper, 'owner.active=1;owner.input_size=', 'owner.active=1;owner.fault=build_crc;owner.input_size=', 1)
    begin = wrapper.index(' int compare_build;')
    end = wrapper.index(' BodyReadResult candidate;', begin)
    wrapper = wrapper[:begin] + '\n' + wrapper[end:]
    begin = wrapper.index(' if(!handle)')
    end = wrapper.index('  owner.receipt.source_result=', begin)
    wrapper = wrapper[:begin] + ' owner.receipt.source_calls++;\n {\n  int accepted=ParserReadBinaryFile(NULL,"bin/BodyParts.bin",ParseBodyPartBegin,&owner.root,NULL,NULL);\n' + wrapper[end:]
    wrapper = once(wrapper, 'if(accepted){\n   candidate.header_end=', 'if(accepted){\n   candidate.source_crc=owner.receipt.source_crc;\n   candidate.header_end=', 1)
    wrapper = once(wrapper, '}else{owner.receipt.stage=BODYREAD_STAGE_SOURCE_REJECT;status=COH_UNSUPPORTED;}', '}else{owner.receipt.stage=!owner.receipt.header_accepted?BODYREAD_STAGE_HEADER_REJECT:BODYREAD_STAGE_SOURCE_REJECT;status=COH_UNSUPPORTED;}', 1)
    wrapper = once(wrapper, ' owner.receipt.status=(uint32_t)status;result=owner.receipt;', ' owner.receipt.update_calls=crc_owner.candidate.update_calls;owner.receipt.stream_bytes=crc_owner.candidate.stream_bytes;owner.receipt.visited_fields=crc_owner.candidate.visited_fields;owner.receipt.interpret_calls=crc_owner.candidate.interpret_calls;\n schema_adler_cleanup();owner.receipt.crypto_cleanup_complete=(uint32_t)schema_adler_is_idle();owner.receipt.status=(uint32_t)status;result=owner.receipt;', 1)
    wrapper = once(wrapper, 'body_wipe(&owner,sizeof(owner));result.cleanup_complete=', 'body_wipe(&owner,sizeof(owner));body_wipe(&crc_owner,sizeof(crc_owner));result.cleanup_complete=', 1)
    wrapper = once(wrapper, 'result.cleanup_complete=(uint32_t)bodyread_is_idle();CohStatus', 'result.cleanup_complete=(uint32_t)bodyread_is_idle();result.crypto_cleanup_complete=(uint32_t)schema_adler_is_idle();CohStatus', 1)
    # Header acceptance is measured at FileList entry, after the source open.
    code = once(code, 'assert(owner.active&&!list);owner.receipt.filelist_calls++;', 'assert(owner.active&&!list);owner.receipt.header_accepted=1;owner.receipt.header_end=(uint32_t)SimpleBufTell(file);owner.receipt.filelist_calls++;', 1)
    helper = '\nsize_t unopened_binary_owner_bytes(void){return sizeof(owner)+sizeof(crc_owner)+sizeof(parser_relpath);}\nsize_t unopened_binary_crypto_object_bytes(void){return schema_adler_object_bytes();}\n'
    apply_at = wrapper.index('CohStatus bodyread_apply(')
    wrapper = wrapper[:apply_at] + wrapper[apply_at:].replace('build_crc', 'fault').replace('ignore_crc', 'production_mode')
    code = names(code + helper + wrapper)
    header = names(body.HEADER)
    header = once(header, '#define UNOPENED_BINARY_STAGE_COMPLETE 17u', '#define UNOPENED_BINARY_STAGE_RESERVATION 17u\n#define UNOPENED_BINARY_STAGE_COMPLETE 18u')
    header = once(header, 'uint32_t header_end,dependency_end,body_end,part_count', 'uint32_t source_crc,header_end,dependency_end,body_end,part_count', 1)
    header = once(header, 'uint32_t status,stage,failure_byte,open_calls', 'uint32_t source_crc,source_calls,crc_calls,mode_calls,update_calls,stream_bytes,visited_fields,interpret_calls,crypto_cleanup_complete;\n uint32_t status,stage,failure_byte,open_calls', 1)
    header = once(header, 'Raw CRC argument is fixturedata, not actual ParseTableCRC.', 'Actual original CRC feeds original production ignoreCRC1 open. fault0 normal,1 owned open refusal,2 row-arena reservation refusal,3 crypto-object reservation refusal; reservation refusals precede source entry. Original NULL allocator returns are not recoverable and are not simulated.')
    header = once(header, 'int unopened_binary_is_idle(void);', 'int unopened_binary_is_idle(void);\nsize_t unopened_binary_owner_bytes(void);\nsize_t unopened_binary_crypto_object_bytes(void);')
    # Stage18 is completion; inherited body failure stages1..16 retain meaning.
    output = work / 'unopened-binary-provider.c'
    output.write_text(code)
    (work / 'unopened-binary-provider.h').write_text(header)
    originals_all = body_proof['whole_function_sha256_lf'] | schema_proof['whole_function_sha256_lf']
    for function, digest in originals_all.items():
        if function.startswith('cryptAdler'):
            continue
        candidates = []
        for raw in frozen.values():
            try:
                value = body.extract(raw.decode().replace('\r\n', '\n'), function)
            except ValueError:
                continue
            if sha(value.encode()) == digest:
                candidates.append(value)
        if len(candidates) != 1 or code.count(candidates[0]) != 1:
            raise ValueError('Original function changed or duplicated: ' + function)
    if any((root / name).read_bytes() != raw for name, raw in frozen.items()):
        raise ValueError('Unopened original inputs changed during emission')
    proof = {'schema': 'coh-original-unopened-binary-provider-v1',
             'source_baseline_revision': pins['baseline_revision'],
             'source_sha256': body_proof['source_sha256'] | schema_proof['source_sha256'],
             'source_pins_sha256': sha(pins_path.read_bytes()),
             'source_stable_before_after': True, 'whole_function_sha256_lf': originals_all,
             'body_dependency_source_audits': {k: body_proof[k] for k in ('whole_function_sha256_lf', 'original_declaration_sha256_lf', 'original_macro_sha256_lf', 'original_table_sha256_lf', 'dispatch_source_audit', 'raw_loaded_fields')},
             'schema_dependency_source_audits': {k: schema_proof[k] for k in ('whole_function_sha256_lf', 'original_declaration_sha256_lf', 'original_macro_sha256_lf', 'original_table_sha256_lf', 'dispatch_source_audit', 'source_semantics')},
             'composition': 'Whole unchanged ParserReadBinaryFile(NULL) -> actual ParseTableCRC/CryptoPP -> original SerializeReadOpen(ignoreCRC1) -> FileListRead(NULL) -> ParserReadBinaryTable/readbin -> original SerializeClose. Fixed exact source BodyPart schemas, definesNULL.',
             'explicit_adapters': 'Immutable production1 helper; combined immutable readbin+interpretfield holders audited against original mappings; fixed owned input/row/string storage; native host32/BoneId/time32/little-endian. No real filesystem/runtime helpers or engine ABI.',
             'allocation_failure_scope': 'Fixed arena and crypto object reservation refusal before source, plus owned open refusal after original CRC. Original struct_readbin does not check NULL TokenStoreAlloc; no recoverable source heap/new failure is claimed.',
             'cleanup': 'Source closes every opened handle; actual CryptoPP object deleted/TLS reset; owned body/CRC/trace buffers volatile-wiped before atomic snapshot commit. Complete entered-extent typed preflight, caller/context spans disjoint, overflow-safe owner+stack+actual object+caller/context/digest/retained charge.',
             'actual_ParseTableCRC_computed': True, 'production_ignoreCRC1_preserved': True,
             'stack_reserve_bytes': 98304, 'current_Map_runtime_observed': False,
             'runtime_body_catalog_admitted': False, 'source_generation_admitted': False,
             'authority_or_application_ack': False,
             'adler_cpp_path': schema_proof['adler_cpp_path'],
             'crypto_dependency': schema_proof['crypto_dependency']}
    return output, proof
