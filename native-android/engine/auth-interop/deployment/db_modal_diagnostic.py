"""Failure-only original Db dialog classifier; all raw control text stays private."""
import hashlib
import json
import ntpath
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import zipfile

import hosted_auth_stage as prior

HERE=Path(__file__).resolve().parent
CATALOG_PATH='native-android/engine/auth-interop/deployment/db_modal_pe_source_catalog.json'
CATALOG_SHA='1543a4a3c30e0272c19093a8e75ef4fa04ac5c0e07d0d9d13143c08e30f86eab'
FILENAME_LITERAL_MAX=1024
FILENAME_TOTAL_MAX=65536
SOURCE_FILE_MAX=1024*1024
SOURCE_TOTAL_MAX=8*1024*1024
EXPRESSION_LITERAL_MAX=4096
EXPRESSION_TOTAL_MAX=256*1024
MACRO_FORWARD_PATH='libs/UtilitiesLib/include/utilitieslib/utils/SuperAssert.h'
MACRO_FORWARD_SHA='105305fab92cb2dc8651c4a4d102a8f5428ecb378f8cde46b3c409970845227b'
PE_ARCHIVE='native-android/engine/auth-interop/evidence/independent-db-build-39000395572/artifact.zip'
PE_ARCHIVE_SHA='2eb66715cb8b35d82580971b60734a92b48c91e2a557cb253d39b7fdafef6ee7'
PE_SHA='9dd91e456484c3fde1d9832163c2bbdad97d6a3f4db4db6a7773fddffe3319c3'
PE_VARIANTS={
 'thread_wake_event':'m_wake != ((HANDLE)(LONG_PTR)-1)',
 'thread_awoke_event':'m_awoke != ((HANDLE)(LONG_PTR)-1)',
 'thread_create_handle':'m_thread != ((HANDLE)(LONG_PTR)-1)',
 'pool_alignment_offset':'offset < (16)'}
FILE_ENUMS={'SuperAssert.c':'super_assert','sql_fifo.c':'sql_fifo','sqltask.cpp':'sql_task',
 'ring.hpp':'ring','taskthread.hpp':'task_thread','semaphoreworkerpool.hpp':'semaphore_pool',
 'ringchain.cpp':'ring_chain','threadedpoolallocator.cpp':'threaded_allocator','MemoryPool.c':'memory_pool'}
SOURCE_PINS={
 'libs/UtilitiesLib/src/utils/SuperAssert.c':'9cc084d112dec11a9c2bf0b585869d069c0628594979420c4448bbcb5802fef6',
 'DBServer/src/sql_fifo.c':'345d23a5f8d92ac3eae7f23dc7282709ee198e62aec05938d8adff1b53e36879',
 'Common/sql/sqltask.cpp':'d826eb394b9a98bd09b430c84ee84edec705c8cdffc96d0c78cff171df96ca02',
 'libs/UtilitiesLib/include/utilitieslib/UtilsCXX/ring.hpp':'ddd91659f95b96e4b714f652e0ed7879be9498776a081df6ff287124efb091c7',
 'libs/UtilitiesLib/include/utilitieslib/UtilsCXX/taskthread.hpp':'70a7f4bfbe172ba3a7ee7f9daf77e2d8504176e66c61016fa29d9e99c038c2de',
 'libs/UtilitiesLib/include/utilitieslib/UtilsCXX/semaphoreworkerpool.hpp':'eb198c0712120799ff9ea47bec5ca1634c3a6526acf824bee4a4380f217ebf81',
 'libs/UtilitiesLib/src/UtilsCXX/ringchain.cpp':'e7ce6ebd9c14097d65830fd1390408b9a1c9c2a46ee992a47d8d483478a46d0e',
 'libs/UtilitiesLib/src/UtilsCXX/threadedpoolallocator.cpp':'bd7b305155d3b133973211814842e8c5260da53c76bef168410a20045a7b4110',
 'libs/UtilitiesLib/src/components/MemoryPool.c':'5d9db8f7a27d9fea371e7b948b02433ce2846f6e029dc24b1803623ddab01e83'}
# Stable output IDs, never strings copied out of a dialog. These are exact
# assertions on the observed pre-worker source boundary, not an open parser.
ASSERTIONS={
 'fifo_not_running':('sql_fifo.c','!sqlfifo.running'),
 'fifo_cleanup_registration':('sql_fifo.c','!atexit(s_fifo_flush)'),
 'task_workers_nonzero':('sqltask.cpp','workers'),
 'task_queue_nonzero':('sqltask.cpp','count'),
 'task_not_initialized':('sqltask.cpp','!sqltask.num_workers'),
 'ring_buffer_unset':('ring.hpp','!m_base'),
 'ring_size_power_of_two':('ring.hpp','!(size & (size-1))'),
 'ring_data_nonnull':('ring.hpp','data'),
 'allocator_size_nonzero':('threadedpoolallocator.cpp','structSize'),
 'thread_wake_event':('taskthread.hpp','m_wake != INVALID_HANDLE_VALUE'),
 'thread_awoke_event':('taskthread.hpp','m_awoke != INVALID_HANDLE_VALUE'),
 'thread_create_handle':('taskthread.hpp','m_thread != INVALID_HANDLE_VALUE'),
 'pool_not_initialized':('MemoryPool.c','!pool->structSize && !pool->structCount'),
 'pool_size_nonzero':('MemoryPool.c','structSize && structCount'),
 'pool_alignment_offset':('MemoryPool.c','offset < CHUNK_ALIGNMENT'),
 'pool_nonnull':('MemoryPool.c','pool'),
 'pool_address_aligned':('MemoryPool.c','!((intptr_t)address & 3)'),
 'pool_freelist_address':('MemoryPool.c','addr == memory'),
 'pool_chunk_present':('MemoryPool.c','pool->chunkTable.size'),
 'pool_allocations_positive':('MemoryPool.c','pool->allocationCount > 0'),
 'worker_no_inflight':('semaphoreworkerpool.hpp','!m_inFlight')}


def normalized(value):
    # Compiler #expression semantics collapse code whitespace, while literal
    # spelling/escapes/raw contents remain exact. Never erase literal spaces.
    regions=[]
    masked=lexical_mask(value,mask_strings=False,regions=regions)
    if masked is None:return None
    chunks=[];at=0;pending=False
    def code(value):
        nonlocal pending
        for char in value:
            if char.isspace():pending=True
            else:
                if pending and chunks:chunks.append(' ')
                chunks.append(char);pending=False
    for start,end,comment in regions:
        code(masked[at:start])
        if comment:pending=True
        else:
            if pending and chunks:chunks.append(' ')
            chunks.append(value[start:end]);pending=False
        at=end
    code(masked[at:])
    return ''.join(chunks)


def lexical_mask(text,mask_strings=True,regions=None):
    """Keep offsets/newlines; hide C/C++ comments and escaped/ordinary/raw strings."""
    out=list(text);i=0
    def hide(start,end):
        for at in range(start,end):
            if out[at]!='\n':out[at]=' '
    while i<len(text):
        start=i;comment=False
        if text.startswith('//',i):
            comment=True;end=text.find('\n',i+2)
            while end>=0 and text[:end].rstrip('\r').endswith('\\'):
                end=text.find('\n',end+1)
            end=len(text) if end<0 else end
        elif text.startswith('/*',i):
            comment=True
            end=text.find('*/',i+2)
            if end<0:return None
            end+=2
        elif text.startswith('R"',i):
            match=re.match(r'R"([^\s()\\]{0,16})\(',text[i:])
            if not match:return None
            stop=')'+match[1]+'"';end=text.find(stop,i+match.end())
            if end<0:return None
            end+=len(stop)
        elif text[i] in ('"',"'"):
            quote=text[i];end=i+1
            while end<len(text):
                if text[end]=='\\':end+=2;continue
                if text[end]==quote:end+=1;break
                if text[end]=='\n':return None
                end+=1
            else:return None
        else:i+=1;continue
        if comment or mask_strings:hide(start,min(end,len(text)))
        if regions is not None:regions.append((start,min(end,len(text)),comment))
        i=end
    return ''.join(out)


def assertion_calls(text):
    """Return exact first-argument spans; malformed/ambiguous lexing is unknown."""
    masked=lexical_mask(text)
    comments_removed=lexical_mask(text,mask_strings=False)
    if masked is None or comments_removed is None:return None
    calls=[]
    for match in re.finditer(r'\b(?:dev)?assert(?:msgf?)?\s*\(',masked):
        at=match.end();start=at;rounds=1;braces=squares=0;argument_end=None
        while at<len(masked):
            c=masked[at]
            if c=='(':rounds+=1
            elif c==')':
                rounds-=1
                if rounds==0:
                    if braces or squares:return None
                    argument_end=at if argument_end is None else argument_end
                    break
            elif c=='{':braces+=1
            elif c=='}':braces-=1
            elif c=='[':squares+=1
            elif c==']':squares-=1
            elif c==',' and rounds==1 and braces==0 and squares==0 and argument_end is None:argument_end=at
            if min(rounds,braces,squares)<0:return None
            at+=1
        else:return None
        expression=comments_removed[start:argument_end].strip()
        if not expression or len(expression.encode())>EXPRESSION_LITERAL_MAX:return None
        expression=normalized(expression)
        if expression is None:return None
        calls.append({'line':masked.count('\n',0,match.start())+1,'expression':expression})
    return calls


def filename_formatter_source(original):
    for definition in ('#define FILEINTRO   "File: "','#define MAXLINELEN 60',
            '#define DOTDOTDOTSZ 3','#define NEWLINESZ   1'):
        if original.count(definition)!=1:raise ValueError('db_modal_original_filename_formatter')
    start='    Strncatt( assertbuf, FILEINTRO );'
    end='    Strncatt( assertbuf, newline );'
    if original.count(start)!=1:raise ValueError('db_modal_original_filename_formatter')
    block=original[original.index(start):]
    if end not in block:raise ValueError('db_modal_original_filename_formatter')
    return block[:block.index(end)]


def render_source_filename(filename):
    """Exact pinned SuperAssert.c File formatter, including separator in p."""
    if type(filename) is not str or not 1<=len(filename)<=FILENAME_LITERAL_MAX or any(not 32<=ord(char)<=126 for char in filename):
        raise ValueError('db_modal_compiled_filename_shape')
    size=len(filename)
    if 7+size+1<=60:return filename
    ffn=52;p=1
    while filename[size-p] not in '\\/' and p<size:p+=1
    if (ffn-ffn//3)<(size-p) and ffn//3>p:
        return filename[:ffn-3-p]+'...'+filename[size-p:]
    if ffn-ffn//3>size-p:
        p//=2
        # Original size_t subtraction underflows for an overlong basename.
        # Such a candidate cannot be safely modeled as a bounded alias.
        if ffn-3-p<0:raise ValueError('db_modal_original_filename_copy_underflow')
        return filename[:ffn-3-p]+'...'+filename[size-p:]
    return filename[:ffn-ffn//3-3]+'...'+filename[size-p:size-p+ffn//6-1]+'...'+filename[size-(ffn//3-ffn//6-2):]


def pe_filename_literals(binary):
    # Exact retained PE32 address inventory, not maximal printable runs: a
    # preceding printable hash byte must never become part of __FILE__.
    pe=struct.unpack_from('<I',binary,60)[0]
    if binary[:2]!=b'MZ' or binary[pe:pe+4]!=b'PE\0\0':raise ValueError('db_modal_filename_pe_shape')
    count=struct.unpack_from('<H',binary,pe+6)[0];optional=struct.unpack_from('<H',binary,pe+20)[0]
    if not 1<=count<=32 or struct.unpack_from('<H',binary,pe+24)[0]!=0x10b:
        raise ValueError('db_modal_filename_pe_shape')
    image=struct.unpack_from('<I',binary,pe+52)[0];sections=[]
    for i in range(count):
        at=pe+24+optional+40*i
        rva,size,raw=struct.unpack_from('<III',binary,at+12)
        if raw+size>len(binary):raise ValueError('db_modal_filename_pe_section_bound')
        if binary[at:at+8].rstrip(b'\0')==b'.rdata':sections.append((rva,size,raw))
    result=[]
    for match in re.finditer(rb'[A-Za-z]:[\\/][\x20-\x7e]*\.(?:c|cpp|cxx|h|hpp|inl)\x00',binary,re.I):
        section=[s for s in sections if s[2]<=match.start() and match.end()<=s[2]+s[1]]
        if len(section)!=1:raise ValueError('db_modal_filename_literal_section')
        rva=section[0][0]+match.start()-section[0][2]
        result.append({'value':match.group()[:-1].decode('ascii'),'pe_filename_offset':match.start(),
            'pe_filename_rva':rva,'pointer_reference_count':binary.count(struct.pack('<I',image+rva))})
    return result


def compiled_filename_policy(literals,catalog):
    aliases={};index={}
    candidates=sorted(item['value'] for item in literals)
    if len(candidates)!=126 or sum(len(v) for v in candidates)>FILENAME_TOTAL_MAX or any(len(v)>FILENAME_LITERAL_MAX for v in candidates):
        raise ValueError('db_modal_compiled_filename_inventory_bound')
    upstream=sorted(v for v in candidates if '/upstream/ouroboros/' in v.replace('\\','/').casefold())
    if hashlib.sha256(json.dumps(upstream).encode()).hexdigest()!=catalog['upstream_filename_catalog_sha256']:
        raise ValueError('db_modal_compiled_filename_catalog_identity')
    used=set()
    for entry in catalog['upstream_files']+catalog['external_files']:
        matches=[v for v in candidates if hashlib.sha256(v.encode()).hexdigest()==entry['pe_filename_sha256']]
        if len(matches)!=1:raise ValueError('db_modal_compiled_filename_candidates')
        candidate=matches[0]
        records=[record for record in literals if record['value']==candidate]
        if len(records)!=1 or any(records[0][key]!=entry[key] for key in ('pe_filename_offset','pe_filename_rva','pointer_reference_count')):
            raise ValueError('db_modal_compiled_filename_literal_identity')
        if 'source_path' in entry:
            if entry['pointer_reference_count']<1:raise ValueError('db_modal_compiled_filename_pointer_unverified')
            if not candidate.replace('\\','/').casefold().endswith('/upstream/ouroboros/'+entry['source_path'].casefold()):
                raise ValueError('db_modal_compiled_filename_source_suffix')
            key=Path(entry['source_path']).name.casefold()
        else:key=entry['enum']
        rendered=render_source_filename(candidate)
        if rendered in aliases or candidate in used:raise ValueError('db_modal_rendered_file_alias_collision')
        aliases[rendered]=[key];used.add(candidate)
        index[entry['enum']]={'compiled_filename_sha256':entry['pe_filename_sha256'],
            'rendered_filename_sha256':hashlib.sha256(rendered.encode()).hexdigest()}
    if len(used)!=126:raise ValueError('db_modal_compiled_filename_catalog_incomplete')
    return aliases,hashlib.sha256(json.dumps(index,sort_keys=True).encode()).hexdigest()


def compiled_variant_policy(root,catalog):
    archive=root/PE_ARCHIVE
    if archive.is_symlink() or archive.stat().st_size!=1088820 or prior.sha(archive)!=PE_ARCHIVE_SHA:
        raise ValueError('db_modal_compiled_archive_identity')
    with zipfile.ZipFile(archive) as value:
        info=value.getinfo('DbServer-checksum-candidate.exe')
        if info.file_size>32*1024*1024:raise ValueError('db_modal_compiled_binary_bound')
        binary=value.read(info)
    if hashlib.sha256(binary).hexdigest()!=PE_SHA:raise ValueError('db_modal_compiled_binary_identity')
    strings={v.decode('ascii') for v in re.findall(rb'[\x20-\x7e]{3,}',binary)}
    if any(v not in strings for v in PE_VARIANTS.values()):
        raise ValueError('db_modal_compiled_variant_not_present')
    maximal=sorted(v for v in strings if '/upstream/ouroboros/' in v.replace('\\','/').casefold() and re.search(r'\.(?:c|cpp|h|hpp)$',v,re.I))
    if hashlib.sha256(json.dumps(maximal).encode()).hexdigest()!=catalog['upstream_maximal_ascii_catalog_sha256']:
        raise ValueError('db_modal_maximal_ascii_filename_catalog_identity')
    aliases,alias_index=compiled_filename_policy(pe_filename_literals(binary),catalog)
    return {key:normalized(value) for key,value in PE_VARIANTS.items()},aliases,alias_index


def policy(root):
    catalog_path=root/CATALOG_PATH
    if catalog_path.is_symlink() or catalog_path.stat().st_size>128*1024 or prior.sha(catalog_path)!=CATALOG_SHA:
        raise ValueError('db_modal_source_catalog_identity')
    catalog=json.loads(catalog_path.read_text())
    if (catalog['pe_sha256']!=PE_SHA or len(catalog['upstream_files'])!=122 or len(catalog['external_files'])!=4):
        raise ValueError('db_modal_source_catalog_shape')
    sources={};source_pins={};file_enums={};total=0
    for entry in catalog['upstream_files']:
        name,pin=entry['source_path'],entry['source_sha256']
        path=root/'upstream/ouroboros'/name
        if path.is_symlink() or path.stat().st_size>SOURCE_FILE_MAX or prior.sha(path)!=pin:raise ValueError('db_modal_original_source_identity')
        basename=Path(name).name
        if basename.casefold() in file_enums:raise ValueError('db_modal_source_basename_ambiguity')
        total+=path.stat().st_size
        if total>SOURCE_TOTAL_MAX:raise ValueError('db_modal_source_total_bound')
        sources[basename]=path.read_text(encoding='utf-8');source_pins[name]=pin;file_enums[basename.casefold()]=entry['enum']
    external_files={entry['enum'] for entry in catalog['external_files']}
    for key in external_files:file_enums[key]=key
    original=sources['SuperAssert.c']
    formatter=filename_formatter_source(original)
    forward=root/'upstream/ouroboros'/MACRO_FORWARD_PATH
    if forward.is_symlink() or prior.sha(forward)!=MACRO_FORWARD_SHA:
        raise ValueError('db_modal_macro_forward_source_identity')
    forwarding=forward.read_text(encoding='utf-8')
    if any(v not in forwarding for v in ('superassertf(#exp, msg, __FILE__, __LINE__',
            '#define assert(exp)    assertmsg(exp, 0)','#define assertmsg(exp, msg)    assertmsgf(exp, msg)')):
        raise ValueError('db_modal_macro_forward_policy')
    if any(value not in original for value in ('#define IDC_MAINTEXT 10','"Assertion failed"','"File: "',
            '"Line: "','"Expression: "','"Exception caught: %s\\n"','"Assertion Failure"')):
        raise ValueError('db_modal_original_dialog_policy')
    exceptions=set(re.findall(r'^\s+EXCPT_NAME\((EXCEPTION_[A-Z_]+)\)',original,re.M))
    if len(exceptions)!=22:raise ValueError('db_modal_original_exception_policy')
    calls_by_file={name:assertion_calls(source) for name,source in sources.items()}
    if any(calls is None for calls in calls_by_file.values()):
        raise ValueError('db_modal_source_index_lexically_ambiguous')
    points={}
    for key,(basename,expression) in ASSERTIONS.items():
        expr=normalized(expression)
        lines=[call['line'] for call in calls_by_file[basename] if call['expression']==expr]
        if not lines:raise ValueError('db_modal_original_assertion_policy')
        points[key]={'file':basename.casefold(),'expression':expr,'lines':lines}
    variants,aliases,alias_index=compiled_variant_policy(root,catalog)
    sites={};public_index={}
    for basename,calls in calls_by_file.items():
        for ordinal,call in enumerate(calls,1):
            key=file_enums[basename.casefold()]+'_assert_'+str(ordinal).zfill(3)
            legacy=[name for name,point in points.items() if point['file']==basename.casefold()
                and call['line'] in point['lines'] and call['expression']==point['expression']]
            if len(legacy)>1:raise ValueError('db_modal_source_index_legacy_ambiguity')
            sites[key]=dict(call,file=basename.casefold(),file_enum=file_enums[basename.casefold()],legacy=legacy[0] if legacy else None,predicate_eligible=True)
            public_index[key]={'file_enum':file_enums[basename.casefold()],'source_line':call['line'],
                'source_expression_sha256':hashlib.sha256(call['expression'].encode()).hexdigest()}
    if len(sites)!=1409 or sum(len(site['expression'].encode()) for site in sites.values())>EXPRESSION_TOTAL_MAX:
        raise ValueError('db_modal_source_index_count_or_byte_bound')
    location_sites={}
    for basename,source in sources.items():
        masked=lexical_mask(source)
        for ordinal,match in enumerate(re.finditer(r'\b(?:onlydevassert|onlyfulldebugdevassert|verify)\s*\(',masked),1):
            key=file_enums[basename.casefold()]+'_location_'+str(ordinal).zfill(3)
            location_sites[key]={'file':basename.casefold(),'file_enum':file_enums[basename.casefold()],
                'line':masked.count('\n',0,match.start())+1,'expression':None,'legacy':None,'predicate_eligible':False}
    if len(location_sites)!=28:raise ValueError('db_modal_unverified_location_site_count')
    return {'exceptions':exceptions,'points':points,'sites':sites,'location_sites':location_sites,
        'variants':variants,'rendered_files':aliases,'file_enums':file_enums,'source_pins':source_pins,
        'external_files':external_files,'catalog':catalog,
        'location_index_sha256':hashlib.sha256(json.dumps(location_sites,sort_keys=True).encode()).hexdigest(),
        'filename_alias_index_sha256':alias_index,'filename_formatter_sha256':hashlib.sha256(formatter.encode()).hexdigest(),
        'site_index_sha256':hashlib.sha256(json.dumps(public_index,sort_keys=True).encode()).hexdigest()}


def classify_text(text,source_policy):
    # Ignore unrelated lines, including program/IP/user/stack/extra-info fields.
    # Never return slices, expressions, numeric codes or hashes of raw text.
    lines=text.replace('\r\n','\n').split('\n')
    result={'kind':'unknown','exception_enum':'none','assertion_enum':'none',
        'source_assertion_line_verified':False,'source_file_enum':'unknown','source_site_enum':'unknown',
        'source_file_verified':False,'source_file_mapping':'unknown',
        'source_call_site_verified':False,'source_expression_match':False,'compiled_expression_variant_match':False,
        'structure_flags':{'file_field_unique':False,'line_field_unique':False,'expression_field_unique':False,'line_shape_known':False}}
    if lines[0].startswith('Exception caught: '):
        name=lines[0][len('Exception caught: '):]
        result['kind']='source_exception'
        result['exception_enum']=name if name in source_policy['exceptions'] else 'unknown_exception'
    elif lines[0]=='Assertion failed':
        result['kind']='source_assertion_unknown'
        fields={}
        for prefix in ('File: ','Line: ','Expression: '):
            values=[line[len(prefix):] for line in lines if line.startswith(prefix)]
            if len(values)==1:fields[prefix]=values[0]
        for prefix,key in (('File: ','file_field_unique'),('Line: ','line_field_unique'),('Expression: ','expression_field_unique')):
            result['structure_flags'][key]=prefix in fields
        files=source_policy['rendered_files'].get(fields.get('File: '),[])
        if len(files)==1:
            external=files[0] in source_policy['external_files']
            result.update(source_file_enum=source_policy['file_enums'][files[0]],source_file_verified=not external,
                source_file_mapping='external_source_unavailable' if external else 'upstream_source')
        elif len(files)>1:result['source_file_enum']='ambiguous_source_file'
        if 'Line: ' in fields:result['structure_flags']['line_shape_known']=bool(re.fullmatch('[0-9]{1,5}',fields['Line: ']))
        if len(files)==1 and 'Line: ' in fields and re.fullmatch('[0-9]{1,5}',fields['Line: ']):
            basename=files[0]
            expr=normalized(fields.get('Expression: ',''));line=int(fields['Line: '])
            all_sites=dict(source_policy['sites'],**source_policy['location_sites'])
            matches=[key for key,site in all_sites.items() if site['file']==basename and site['line']==line]
            if len(matches)>1:result['source_site_enum']='ambiguous_source_site'
            elif len(matches)==1:
                key=matches[0];site=all_sites[key]
                result.update(source_site_enum=key,source_call_site_verified=True,
                    source_expression_match=site['predicate_eligible'] and expr==site['expression'],
                    compiled_expression_variant_match=site['predicate_eligible'] and site['legacy'] in source_policy['variants'] and expr==source_policy['variants'][site['legacy']])
                if result['source_expression_match'] or result['compiled_expression_variant_match']:
                    result.update(kind='source_assertion',assertion_enum=site['legacy'] or key,source_assertion_line_verified=True)
    return result


def admit(value,pid,source_policy):
    keys={'pid','rows','enumerated_top_level','deadline_reached','inventory_bound_reached','text_bound_reached','owner_changed_count','top_level_enumeration_completed'}
    if (type(pid) is not int or not 1<=pid<=0x7fffffff or not isinstance(value,dict) or set(value)!=keys
            or type(value.get('pid')) is not int or value['pid']!=pid
            or type(value.get('enumerated_top_level')) is not int or not 0<=value['enumerated_top_level']<=513
            or type(value.get('owner_changed_count')) is not int or not 0<=value['owner_changed_count']<=80
            or any(type(value.get(k)) is not bool for k in ('deadline_reached','inventory_bound_reached','text_bound_reached','top_level_enumeration_completed'))
            or not isinstance(value.get('rows'),list) or len(value['rows'])>80):
        raise ValueError('db_modal_observation_shape')
    statuses={'ok','timeout','truncated','owner_changed'};counts={key:0 for key in sorted(statuses)}
    classes={'#32770':'dialog','Static':'static','Button':'button','Edit':'edit','ComboBox':'combo','ListBox':'list'}
    class_counts={key:0 for key in (*classes.values(),'unknown')}
    matches=[];characters=0;tops=0;children=0;main_controls=0
    for row in value['rows']:
        if (not isinstance(row,dict) or set(row)!={'pid','top_level','class_name','control_id','text','text_status'}
                or type(row.get('pid')) is not int or row['pid']!=pid or type(row.get('top_level')) is not bool
                or type(row.get('class_name')) is not str or len(row['class_name'])>255
                or type(row.get('control_id')) is not int or not -1<=row['control_id']<=0xffff
                or type(row.get('text')) is not str or len(row['text'])>32768
                or type(row.get('text_status')) is not str or row.get('text_status') not in statuses):
            raise ValueError('db_modal_control_shape')
        characters+=len(row['text']);tops+=row['top_level'];children+=not row['top_level']
        counts[row['text_status']]+=1;class_counts[classes.get(row['class_name'],'unknown')]+=1
        main_controls+=not row['top_level'] and row['class_name']=='Static' and row['control_id']==10
        # Original SuperAssert's pinned resource uses Static IDC_MAINTEXT=10.
        # An owned title/button/edit control cannot masquerade as its body.
        if row['text_status']=='ok' and not row['top_level'] and row['class_name']=='Static' and row['control_id']==10:
            match=classify_text(row['text'],source_policy)
            if match['kind']!='unknown':matches.append(match)
    if characters>65536 or tops>16 or children>64 or counts['owner_changed']!=value['owner_changed_count']:
        raise ValueError('db_modal_observation_counts')
    if not value['top_level_enumeration_completed'] and not (value['deadline_reached'] or value['inventory_bound_reached']):
        raise ValueError('db_modal_native_enumeration_failed')
    return {'schema':'coh-owned-db-modal-classifier-v1','pid':pid,'current_desktop_only':True,
        'read_only':True,'raw_titles_controls_or_stacks_exported':False,
        'owned_top_level_count':tops,'owned_child_count':children,'dialog_class_count':class_counts['dialog'],
        'source_main_text_control_count':main_controls,'top_level_enumeration_completed':value['top_level_enumeration_completed'],
        'class_enum_counts':class_counts,'text_status_counts':counts,'inspected_characters':characters,
        'source_matches':matches,'unknown_control_count':len(value['rows'])-len(matches),
        'deadline_reached':value['deadline_reached'],'inventory_bound_reached':value['inventory_bound_reached'],
        'text_bound_reached':value['text_bound_reached'],'owner_changed_count':value['owner_changed_count']}


def policy_identity(source_policy):
    return {'original_source_sha256':dict(source_policy['source_pins'],**{MACRO_FORWARD_PATH:MACRO_FORWARD_SHA}),
        'source_call_site_count':len(source_policy['sites']),'source_call_site_index_sha256':source_policy['site_index_sha256'],
        'source_verified_file_count':len(source_policy['source_pins']),
        'external_unverified_file_count':len(source_policy['external_files']),
        'unverified_location_site_count':len(source_policy['location_sites']),
        'unverified_location_site_index_sha256':source_policy['location_index_sha256'],
        'lexical_index_does_not_prove_compiled_runtime_coverage':True,
        'pe_source_catalog_sha256':CATALOG_SHA,
        'upstream_filename_literal_catalog_sha256':source_policy['catalog']['upstream_filename_catalog_sha256'],
        'upstream_maximal_ascii_catalog_sha256':source_policy['catalog']['upstream_maximal_ascii_catalog_sha256'],
        'compiled_variant_count':len(source_policy['variants']),'compiled_variant_pe_sha256':PE_SHA,
        'compiled_variant_archive_sha256':PE_ARCHIVE_SHA,
        'rendered_filename_alias_count':len(source_policy['rendered_files']),
        'rendered_filename_alias_index_sha256':source_policy['filename_alias_index_sha256'],
        'filename_formatter_block_sha256':source_policy['filename_formatter_sha256'],
        'literal_byte_bounds':{'filename':FILENAME_LITERAL_MAX,'filenames_total':FILENAME_TOTAL_MAX,
            'source_file':SOURCE_FILE_MAX,'source_total':SOURCE_TOTAL_MAX,
            'expression':EXPRESSION_LITERAL_MAX,'expressions_total':EXPRESSION_TOTAL_MAX}}


def helper_sources(root):
    helper_inputs={}
    for relative in ('deployment/db_modal_diagnostic.py','deployment/windows/db_modal_observer.cs','deployment/db_modal_pe_source_catalog.json'):
        name='native-android/engine/auth-interop/'+relative
        raw=subprocess.check_output(['git','-C',str(root),'show','HEAD:'+name],stderr=subprocess.DEVNULL,timeout=30)
        path=root/name
        if path.is_symlink() or path.read_bytes()!=raw:raise ValueError('db_modal_helper_not_owned_by_head')
        helper_inputs[name]=hashlib.sha256(raw).hexdigest()
    if Path(__file__).resolve()!=root/'native-android/engine/auth-interop/deployment/db_modal_diagnostic.py':
        raise ValueError('db_modal_helper_checkout_layout')
    return helper_inputs


def reader_script(root):
    reader=root/'native-android/engine/auth-interop/deployment/windows/db_modal_observer.cs'
    if "'" in str(reader):raise ValueError('db_modal_reader_path')
    return "$ErrorActionPreference='Stop';Add-Type -TypeDefinition (Get-Content -LiteralPath '"+str(reader)+"' -Raw);"


def observe(root,pid,directory):
    if type(pid) is not int or not 1<=pid<=0x7fffffff:raise ValueError('db_modal_owned_pid')
    source_policy=policy(root);helper_inputs=helper_sources(root)
    script=reader_script(root)+"[CohDbModalReader]::Observe("+str(pid)+")|ConvertTo-Json -Compress -Depth 6"
    with tempfile.TemporaryFile(dir=directory) as output:
        child=subprocess.run(['pwsh','-NoProfile','-NonInteractive','-Command',script],stdout=output,
            stderr=subprocess.DEVNULL,timeout=30,env=dict(os.environ,TEMP=str(directory),TMP=str(directory)))
        if child.returncode or os.fstat(output.fileno()).st_size>1024*1024:
            raise ValueError('db_modal_private_observer_failed')
        output.seek(0);value=json.loads(output.read(1024*1024+1).decode('utf-8-sig'))
    result=admit(value,pid,source_policy)
    result.update(policy_identity(source_policy))
    result['classifier_source_sha256']=helper_inputs
    return result


def preflight(root,directory):
    """Compile/read APIs against this fresh owned PowerShell child before SQL.

    The benign child observes only its own PID on the current desktop. An empty
    owned inventory is valid; this is not evidence that DB assertions are absent.
    """
    import hosted_auth_login as login
    source_policy=policy(root);helper_inputs=helper_sources(root)
    script=reader_script(root)+("$before=[long]([Diagnostics.Process]::GetCurrentProcess().StartTime.ToUniversalTime().Ticks);"
        "$value=[CohDbModalReader]::Observe($PID);$after=[long]([Diagnostics.Process]::GetCurrentProcess().StartTime.ToUniversalTime().Ticks);"
        "[pscustomobject]@{before=$before;after=$after;observation=$value}|ConvertTo-Json -Compress -Depth 7")
    job=login.OwnedJob();child=None;clean=False
    try:
        with tempfile.TemporaryFile(dir=directory) as output:
            child=subprocess.Popen(['pwsh','-NoProfile','-NonInteractive','-Command',script],
                stdout=output,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,
                env=dict(os.environ,TEMP=str(directory),TMP=str(directory)))
            job.assign(child);child.wait(timeout=30)
            if child.returncode or os.fstat(output.fileno()).st_size>1024*1024:
                raise ValueError('db_modal_private_preflight_failed')
            output.seek(0);value=json.loads(output.read(1024*1024+1).decode('utf-8-sig'))
            if (not isinstance(value,dict) or set(value)!={'before','after','observation'}
                    or type(value.get('before')) is not int or not 0<value['before']<=3155378975999999999
                    or type(value.get('after')) is not int or value['before']!=value['after']):
                raise ValueError('db_modal_preflight_process_generation')
            result=admit(value['observation'],child.pid,source_policy)
    finally:
        if child is not None:
            try:clean=job.stop(child)
            finally:
                if job.handle:
                    try:job.kernel.CloseHandle(job.handle)
                    finally:job.handle=None
        elif job.handle:
            clean=bool(job.kernel.CloseHandle(job.handle));job.handle=None
    if not clean:raise ValueError('db_modal_preflight_cleanup_failed')
    return {'schema':'coh-owned-db-modal-api-preflight-v1','passed':True,'owned_pid':child.pid,
        'owned_started_utc_ticks':value['before'],'owned_cleanup_complete':True,
        **policy_identity(source_policy),'classifier_source_sha256':helper_inputs,
        'benign_self_observation':result,'auth_or_sql_services_started':False}
