#!/usr/bin/env python3
"""Read immutable Git and frozen scratch source as data; never import project code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

REV = '9c29e08c8d7e0ab38cff00f2997c39738a56ad07'
BASE = 'upstream/ouroboros/'
FUNCTIONS = {
 'DBServer/src/svrmoncomm.c': ['svrMonConnectCallback','svrMonDelCallback','svrMonSendList',
   'svrMonSendFullUpdate','svrMonHandleConnect','svrMonHandleClientMsg','svrMonInit','svrMonSendUpdates'],
 'DBServer/src/dbmission.c': ['dbClientReadyForPlayers'],
 'DBServer/src/dbinit.c': ['dbInit','registerDbClient','freeMapContainer'],
 'DBServer/src/dbdispatch.c': ['dbHandleClientMsg','handleInitialConnect'],
 'DBServer/src/logserver.c': ['logNetInit'],
 'MapServer/src/dbcomm/dbcomm.c': ['dbTryConnect','dbRegister','dbReadyForPlayers'],
 'MapServer/src/dbcomm/logcomm.c': ['logNetInit'],
 'ServerMonitor/src/serverMonitorNet.c': ['svrMonConnect','handleRecvList','svrMonHandleMsg'],
 'libs/UtilitiesLib/src/utils/structNet.c': ['sdPackStruct','ParserSend','ParserRecv',
   'sdUnpackStruct','sdPackParseInfo','sdUnpackParseInfo'],
 'libs/UtilitiesLib/src/network/net_link.c': ['netConnectEx','netConnect'],
 'libs/UtilitiesLib/src/network/net_version.c': ['getDefaultNetworkVersion','applyNetworkVersionToLink'],
}
EXTRA = ['Common/comm_backend.h','DBServer/src/svrmoncomm.h','DBServer/src/container.h',
 'libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h',
 'libs/UtilitiesLib/include/utilitieslib/utils/structNet.h',
 'libs/UtilitiesLib/include/utilitieslib/utils/structoldnames.h',
 'libs/UtilitiesLib/src/network/netio_receive.c']
CLI_REV = '2b63ae778'
CLI_BASE = 'native-android/engine/auth-interop/fresh-character-owner/probe/'
CLI = ['INTERFACE-PROPOSAL.md','fresh_probe_platform.proposed.h','fresh_character_probe.proposed.c']
HELPER = {
 'OwnedProfileProcess.cs': 'f23a4c57bf82043a586cebd400d5f9feecc4d94bfa1ce895cf722ca8b3244121',
 'InertProfileProbe.cs': '339aa91a99fc3099e421d8a70d16d350c97d1df94728e83c2f1fab367e85a52c',
 'TestOwnedProfileProcess.cs': 'b68929efac7fa145a706524dc4d84e3b6afb6bd29258e636b9902297ca38a378',
 'CONTRACT.md': 'aa62e5cb058caf707a0cfcdee21aa26119e53be611bd158e24f80ff67d63430c',
}

def sha(raw): return hashlib.sha256(raw).hexdigest()
def need(ok, reason):
    if not ok: raise ValueError(reason)
def git(root, revision, name):
    raw = subprocess.check_output(['git','-C',str(root),'show',revision+':'+name])
    need(0 < len(raw) <= 8*1024**2, 'bounded Git input')
    return raw
def mask(raw):
    out=bytearray(raw);i=0
    while i<len(raw):
        begin=i
        if raw[i:i+2]==b'//':
            end=raw.find(b'\n',i);i=len(raw) if end<0 else end
        elif raw[i:i+2]==b'/*':
            end=raw.find(b'*/',i+2);need(end>=0,'comment');i=end+2
        elif raw[i] in (34,39):
            quote=raw[i];i+=1
            while i<len(raw):
                if raw[i]==92:i+=2
                elif raw[i]==quote:i+=1;break
                else:i+=1
            else:raise ValueError('literal')
        else:i+=1;continue
        for j in range(begin,min(i,len(raw))):
            if raw[j] not in (10,13):out[j]=32
    return bytes(out)
def balanced(raw,clean,start):
    cursor=start+1;depth=1
    while cursor<len(clean) and depth:
        depth+=(clean[cursor]==123)-(clean[cursor]==125);cursor+=1
    need(depth==0,'balanced definition')
    return cursor
def span(raw,name):
    clean=mask(raw);out=[]
    pattern=rb'(?m)^[A-Za-z_][A-Za-z0-9_ \t*]*\b'+name.encode()+rb'[ \t]*\('
    for match in re.finditer(pattern,clean):
        cursor=clean.index(b'(',match.start())+1;depth=1
        while cursor<len(clean) and depth:
            depth+=(clean[cursor]==40)-(clean[cursor]==41);cursor+=1
        while cursor<len(clean) and clean[cursor] in b' \t\r\n':cursor+=1
        if cursor==len(clean) or clean[cursor]!=123:continue
        end=balanced(raw,clean,cursor)
        out.append({'offset':match.start(),'bytes':end-match.start(),
          'line':raw[:match.start()].count(b'\n')+1,'sha256':sha(raw[match.start():end])})
    need(1<=len(out)<=2,'definition '+name)
    return {'desktop_definition_index':0,'definitions':out}
def comments_only(raw):
    out=bytearray(raw);i=0
    while i<len(raw):
        begin=i
        if raw[i:i+2]==b'//':
            end=raw.find(b'\n',i);i=len(raw) if end<0 else end
        elif raw[i:i+2]==b'/*':
            end=raw.find(b'*/',i+2);need(end>=0,'schema comment');i=end+2
        elif raw[i] in (34,39):
            quote=raw[i];i+=1
            while i<len(raw):
                if raw[i]==92:i+=2
                elif raw[i]==quote:i+=1;break
                else:i+=1
            else:raise ValueError('schema literal')
            continue
        else:i+=1;continue
        for j in range(begin,min(i,len(raw))):
            if raw[j] not in (10,13):out[j]=32
    return bytes(out)
def table(raw,name):
    matches=list(re.finditer(rb'(?m)^TokenizerParseInfo[ \t]+'+name.encode()+rb'\[\][ \t\r\n]*=',raw))
    need(len(matches)==1,'unique schema definition')
    begin=matches[0].start();start=raw.index(b'{',begin);end=balanced(raw,mask(raw),start)
    block=raw[begin:end]
    return {'offset':begin,'bytes':len(block),'line':raw[:begin].count(b'\n')+1,
            'sha256':sha(block),'ordered_names':[v.decode('ascii') for v in re.findall(rb'\{\s*"([^"]+)"',comments_only(block))]}
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',required=True,type=Path)
    parser.add_argument('--helper-root',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();root=args.source_root.resolve(strict=True)
    need(not args.output.exists(),'fresh data output')
    files={};functions={};raw_files={}
    for name in sorted(set(FUNCTIONS)|set(EXTRA)):
        path=BASE+name;raw=git(root,REV,path)
        need((root/path).read_bytes()==raw,'current original source differs')
        files[path]={'bytes':len(raw),'sha256':sha(raw)}
        lf=raw.replace(b'\r\n',b'\n');raw_files[name]=lf
        if name in FUNCTIONS:functions[path]={f:span(lf,f) for f in FUNCTIONS[name]}
    schema=raw_files['DBServer/src/svrmoncomm.h']
    tables={name:table(schema,name) for name in ['BaseConNetInfo','NetLinkInfo','MapConNetInfo']}
    need({name:len(value['ordered_names']) for name,value in tables.items()} ==
         {'BaseConNetInfo':2,'NetLinkInfo':2,'MapConNetInfo':31},'compiled schema field inventory')
    need(tables['NetLinkInfo']['ordered_names']==['LastRecvTime','IP'],'NetLink live fields')
    need('Starting' in tables['MapConNetInfo']['ordered_names'] and
         'Active' not in tables['MapConNetInfo']['ordered_names'],'Starting without Active schema')
    cli={}
    full_cli_rev=subprocess.check_output(['git','-C',str(root),'rev-parse',CLI_REV]).decode().strip()
    for name in CLI:
        path=CLI_BASE+name;raw=git(root,full_cli_rev,path)
        need((root/path).read_bytes()==raw,'CLI draft changed')
        cli[path]={'bytes':len(raw),'sha256':sha(raw)}
    helper={}
    for name,pin in HELPER.items():
        path=args.helper_root/name;raw=path.read_bytes();need(sha(raw)==pin,'helper frozen scratch source')
        helper[name]={'bytes':len(raw),'sha256':pin,'origin':'frozen scratch source; not executed or imported'}
    record={'schema':'coh-map-ready-observer-source-contract-audit-v2','passed':True,
      'immutable_original_source_revision':REV,'source_files':files,
      'schema_inventory_correction':{'previous_commit':'a63c1098c27e26c7af8e49e7d704243c889deed9',
        'previous_audit_bytes':18172,'previous_audit_sha256':'198238259368ef418194f1db8f057691332c41b93ba81d6e666f6ceed4e6b3bb',
        'raw_schema_hashes_and_whole_functions_unchanged':True,
        'commented_NetLink_names_not_serialized':True,'previous_names':7,'current_names':2},
      'whole_function_spans_lf':functions,'source_file_count':len(files),
      'whole_function_names':sum(map(len,functions.values())),
      'whole_function_definitions':sum(len(p['definitions']) for fs in functions.values() for p in fs.values()),
      'exact_schema_tables_lf':tables,'CLI_draft_revision':full_cli_rev,'CLI_draft_source':cli,
      'frozen_inert_helper_source':helper,
      'findings':{'original_log_listener_is_Db_owned_6989':True,
        'original_monitor_listener_is_Db_owned_6996':True,'Map_service_listener_is_Db_owned_6997':True,
        'monitor_major_and_minor':20110804,'network_default_profile':5,
        'active_field_is_serialized':False,'Starting_field_is_serialized':True,
        'producer_contains_active_or_starting_only':True,'manual_positive_Map1_cookie0_branch_exists':True,
        'ready_handler_checks_map_id_matches_link':False,'ready_command_sender_attributed':False,
        'remote_monitor_PID_is_retained_handle_identity':False,'maps_only_request_exists':False,
        'full_update_first_family_is_MAPSERVERS':True,'schema_receiver_compatibility_fallback_exists':True,
        'CLI_policy_file_alone_is_readiness_proof':False,'frozen_inert_helper_returns_live_Map_lease':False},
      'execution':{'stdlib_Git_source_data_audit_only':True,'project_imports':False,
        'compiler_or_old_qualifier_or_test':False,'native_or_Windows_API':False,'network_or_service':False,
        'registry_account_or_profile_actions':False,'actual_ready_received':False,'world_authority':False}}
    raw=(json.dumps(record,indent=2)+'\n').encode();args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('xb') as f:f.write(raw)
    print(json.dumps({'passed':True,'bytes':len(raw),'sha256':sha(raw),'source_files':len(files),
                      'whole_function_names':record['whole_function_names']}))
if __name__=='__main__':main()
