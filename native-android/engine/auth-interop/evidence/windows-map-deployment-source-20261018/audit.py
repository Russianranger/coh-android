#!/usr/bin/env python3
"""Read one immutable Git revision and one already retained ZIP; never import project code."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import zipfile
import io

REV = 'd9adf2b431a039357f8bfe878d3d0da991a81b19'
BASE = 'upstream/ouroboros/'
FUNCTIONS = {
 'MapServer/src/svr/svr_init.c': ['main','parseArgs0','parseArgs1','parseArgs2','sysInit','serverStateInit','connectToDbserver','svrInit','startupInfo'],
 'MapServer/src/dbcomm/dbcomm.c': ['testClientSetDb','dbTryConnect','dbRegister','dbReadyForPlayers','dbSetupMap','dbExecuteSql'],
 'MapServer/src/dbcomm/logcomm.c': ['logNetInit'],
 'MapServer/src/dbcomm/staticMapInfo.c': ['staticMapInfosLoad'],
 'MapServer/src/beacon/beaconClientServer.c': ['beaconHandleCmdLine','beaconizerIsStarting','beaconizerStart'],
 'MapServer/src/beacon/beaconClient.c': ['beaconClientInstall','beaconClientStartup','beaconClient'],
 'DBServer/src/dbinit.c': ['main','dbInit','getStaticMapList','registerDbClient'],
 'DBServer/src/dbmission.c': ['dbClientReadyForPlayers'],
 'DBServer/src/dbdispatch.c': ['handleInitialConnect','handleStatusReq'],
 'DBServer/src/container.c': ['containerListRegister'],
 'DBServer/src/container_flatfile.c': ['containerListLoadFile','containerListLoad'],
 'DBServer/src/logserver.c': ['logNetInit'],
 'DBServer/src/svrmoncomm.c': ['svrMonSendList'],
 'libs/UtilitiesLib/src/version/AppRegCache.c': ['regSetAppName','regGetAppName','regGetAppKey','regGetCurrentVersion','regGetInstallationDir'],
 'libs/UtilitiesLib/src/version/AppVersion.c': ['isExecutableInInstallDir','getExecutablePatchVersionInternal','getExecutablePatchVersion'],
 'libs/UtilitiesLib/src/utils/RegistryReader.c': ['initRegReader','rrLazyWriteInit','rrWriteString'],
 'libs/UtilitiesLib/src/language/AppLocale.c': ['locIDIsValid','locIDIsValidForPlayers','locGetIDInRegistry','locSetIDInRegistry'],
 'libs/UtilitiesLib/src/utils/utils.c': ['getAutoDbName_s'],
 'libs/UtilitiesLib/src/utils/sysutil.c': ['preloadDLLs','trickGoogleDesktopDll','CreateFileMappingSafe'],
 'libs/UtilitiesLib/src/network/net_link.c': ['netOpenSocketTcp','netConnectEx','netConnect'],
 'libs/UtilitiesLib/src/network/sock.c': ['setHostIpList'],
 'Common/utils/debugUtils.c': ['duGetIntDebugSetting'],
}
EXTRA = [BASE+n for n in ('Common/comm_backend.h','MapServer/CMakeLists.txt','DBServer/src/svrmoncomm.h',
 'libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h')]+[
 'native-android/engine/scenecatalog-server/capture_groups_transaction.py',
 'native-android/engine/scenecatalog-server/fresh_callback_observer/stage.py',
 'native-android/engine/auth-interop/deployment/hosted_db_shard_activation.py',
 'tools/prepare_game_loopback_source.py','patches/game-loopback/0001-game-loopback-bindings.patch']
OLD = 'native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/compile-owner-predicates-20261018/'
ZIP = OLD+'fresh-map-owner-build-39094808520.zip'

def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(root,name):
    raw = subprocess.check_output(['git','-C',str(root),'show',REV+':'+name],stderr=subprocess.DEVNULL)
    if len(raw)>8*1024**2: raise ValueError('bounded_git_input')
    return raw
def mask(raw):
    result=bytearray(raw); i=0
    while i<len(raw):
        begin=i
        if raw[i:i+2]==b'//':
            end=raw.find(b'\n',i); i=len(raw) if end<0 else end
        elif raw[i:i+2]==b'/*':
            end=raw.find(b'*/',i+2)
            if end<0: raise ValueError('comment')
            i=end+2
        elif raw[i] in (34,39):
            quote=raw[i]; i+=1
            while i<len(raw):
                if raw[i]==92: i+=2
                elif raw[i]==quote: i+=1; break
                else: i+=1
            else: raise ValueError('literal')
        else: i+=1; continue
        for j in range(begin,min(i,len(raw))):
            if raw[j] not in (10,13): result[j]=32
    return bytes(result)
def span(raw,name):
    clean=mask(raw); found=[]
    for m in re.finditer(rb'(?m)^[A-Za-z_][A-Za-z0-9_ \t*]*\b'+name.encode()+rb'[ \t]*\(',clean):
        pos=clean.index(b'(',m.start()); depth=1; pos+=1
        while pos<len(clean) and depth:
            depth+=(clean[pos]==40)-(clean[pos]==41); pos+=1
        while pos<len(clean) and clean[pos] in b' \t\r\n': pos+=1
        if pos==len(clean) or clean[pos]!=123: continue
        depth=1; pos+=1
        while pos<len(clean) and depth:
            depth+=(clean[pos]==123)-(clean[pos]==125); pos+=1
        if depth: raise ValueError('brace')
        if raw[pos:pos+1]==b'\n': pos+=1
        found.append((m.start(),pos))
    # Some UtilitiesLib files contain a later #else _XBOX stub with the same
    # name. Pin all definitions; explicitly select the first desktop branch.
    if not found or len(found)>2: raise ValueError('definition_'+name)
    out=[]
    for start,end in found:
        out.append({'offset':start,'bytes':end-start,'line':raw[:start].count(b'\n')+1,'sha256':sha(raw[start:end])})
    return {'desktop_definition_index':0,'definitions':out}
def pe(raw):
    off=struct.unpack_from('<I',raw,60)[0]; machine,count=struct.unpack_from('<HH',raw,off+4)
    opt=off+24; opts=struct.unpack_from('<H',raw,off+20)[0]
    if raw[off:off+4]!=b'PE\0\0' or machine!=0x14c or struct.unpack_from('<H',raw,opt)[0]!=0x10b:
        raise ValueError('pe32')
    sections=[]
    for i in range(count):
        v,va,n,p=struct.unpack_from('<IIII',raw,opt+opts+40*i+8); sections.append((va,max(v,n),n,p))
    def at(rva):
        hits=[p+rva-va for va,span,n,p in sections if va<=rva<va+span and rva-va<n]
        if len(hits)!=1: raise ValueError('rva')
        return hits[0]
    def string(rva):
        p=at(rva); end=raw.index(b'\0',p)
        if end-p>1024: raise ValueError('import')
        return raw[p:end].decode('ascii')
    def imports(index):
        rva,n=struct.unpack_from('<II',raw,opt+96+8*index)
        if not rva: return []
        p=at(rva); output=[]; width=20 if index==1 else 32
        for _ in range(128):
            row=struct.unpack_from('<'+'I'*(width//4),raw,p); p+=width
            if not any(row): return output
            if index!=1 and not row[0]&1: raise ValueError('delay_va')
            output.append(string(row[3] if index==1 else row[1]))
        raise ValueError('import_count')
    return {'bytes':len(raw),'sha256':sha(raw),'machine':'i386','imports':imports(1),'delay_imports':imports(13)}
def audit(root):
    files={}; functions={}
    for name in sorted(set(EXTRA)|{BASE+n for n in FUNCTIONS}):
        raw=read(root,name); files[name]={'bytes':len(raw),'sha256':sha(raw)}
        if name.startswith(BASE) and name[len(BASE):] in FUNCTIONS:
            functions[name]={f:span(raw,f) for f in FUNCTIONS[name[len(BASE):]]}
    retained=read(root,ZIP)
    if sha(retained)!='b3a82a5265322685e035e3b86f44862a59d8fc561852288e3d3ea8bb8371eed6': raise ValueError('old_zip')
    with zipfile.ZipFile(io.BytesIO(retained)) as z:
        binary=pe(z.read('fresh-groups-compile/MapServer.exe'))
        init=z.read('fresh-groups-compile/source/MapServer/src/svr/svr_init.c')
        receipt=z.read('fresh-groups-compile/compile-only-receipt.json')
        assets=z.read('fresh-groups-compile/map-startup-inputs.json')
        old={'archive':{'path':ZIP,'bytes':len(retained),'sha256':sha(retained)},'binary':binary,
             'receipt':{'bytes':len(receipt),'sha256':sha(receipt)},
             'startup_inputs':{'bytes':len(assets),'sha256':sha(assets)},
             'staged_svr_init':{'bytes':len(init),'sha256':sha(init),
               'hardcoded_CoH_count':init.count(b'regSetAppName("CoH")'),
               'TestClient_call_count':init.count(b'testClientSetDb(db_state.server_name)')},
             'build_only':True,'new_A13_binary_admitted_by_this_audit':False}
    return {'schema':'coh-windows-map-deployment-source-audit-v1','repository_commit':REV,
      'source_files':files,'whole_function_spans':functions,'source_file_count':len(files),
      'whole_function_count':sum(len(v) for v in functions.values()),'retained_old_map_compile':old,
      'source_findings':{'map_to_db_tcp_port':6997,'map_to_log_tcp_port':6989,
        'db_map_protocol':20110503,'same_Db_process_serves_log_when_UseLogServer_zero':True,
        'manual_positive_map_registration_requires_existing_map_container':True,
        'zero_launcher_cookie_is_original_manual_registration_branch':True,
        'ready_sent_after_groupLoadMap_dbSetupMap':True,
        'db_ready_handler_clears_starting':True,
        'Map_direct_ODBC_or_PG_imports_in_old_PE':False,
        'fixed_TestClient_CS_write_on_ordinary_startup':True,
        'hardcoded_CoH_installation_getter_can_create_key':True,
        'current_English_locale_guard_takes_no_registry_write':True,
        'beacon_install_write_requires_excluded_beacon_role':True,
        'private_CWD_or_parent_job_isolates_HKCU':False,
        'in_main_override_proves_preentry_DLL_HKCU_isolation':False},
      'source_only':True,'project_imports_tests_compilers_registry_accounts_or_target_processes_executed':False,
      'Map_READY_or_fresh_character_runtime_admitted':False,'normal_version_checksum_reference_admitted':False,
      'SQL_identity_rewrite_or_historical_character_transfer_proposed':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);a=p.parse_args()
    print(json.dumps(audit(a.source_root.resolve()),indent=2,sort_keys=True))
