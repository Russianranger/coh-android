#!/usr/bin/env python3
"""Read fixed published Git text only; no project imports, compiler or runtime."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[5]
REV='f3ee9db6bc8a323c896769f0952dd242fc79e2f4'
FUNCTIONS={
 'upstream/ouroboros/Game/src/clientcomm/dbclient.c':['dbChoosePlayer'],
 'upstream/ouroboros/DBServer/src/clientcomm.c':['determineStartMapId','determinePlayerType','determinePraetorianProgress','s_finishHandleChoosePlayer','handleChoosePlayer','handlePlayerContainerLoaded','doneWaitingChoosePlayerFailed'],
 'upstream/ouroboros/DBServer/src/mapxfer.c':['startMapIfStatic','setNewMap','finishSetNewMap','sendLoginInfoToGameClient'],
 'upstream/ouroboros/DBServer/src/dbdispatch.c':['handleContainerAck'],
 'upstream/ouroboros/Game/src/gameComm/initClient.c':['sendCharacterCreate','checkForCharacterCreate'],
 'upstream/ouroboros/Game/src/clientcomm/clientcomm.c':['commStart'],
 'upstream/ouroboros/Game/src/entity/entrecv.c':['sendCharacterToServer'],
 'upstream/ouroboros/Game/src/entity/character_net_client.c':['character_SendCreate'],
 'upstream/ouroboros/Common/entity/character_net.c':['basepower_Send','basepower_Receive'],
 'upstream/ouroboros/Common/gameComm/trayCommon.c':['sendTray','receiveTray'],
 'upstream/ouroboros/Common/entity/costume.c':['costume_send','costume_receive'],
 'upstream/ouroboros/Common/entity/power_customization.c':['powerCustList_send','powerCustList_receive'],
 'upstream/ouroboros/Common/entity/entStrings.c':['sendEntStrings','receiveEntStrings'],
 'upstream/ouroboros/MapServer/src/container/containercallbacks.c':['containerHandleEntity'],
 'upstream/ouroboros/MapServer/src/entity/entserver.c':['entFromLoginCookie','receiveCharacterFromClient'],
 'upstream/ouroboros/MapServer/src/svr/svr_tick.c':['svrHandleClientMsg'],
 'upstream/ouroboros/MapServer/src/player/parseClientInput.c':['parseClientInput'],
 'upstream/ouroboros/MapServer/src/entity/character_net_server.c':['character_ReceiveCreate','character_ReceiveCreateClassOrigin','character_ReceiveCreatePowers'],
 'upstream/ouroboros/MapServer/src/dbcomm/dbcomm.c':['dbRegister','dbReadyForPlayers'],
 'native-android/engine/dbclient/coh_dbclient.c':['coh_db_choose_encode','coh_db_player_choose'],
 'native-android/engine/dbclient/coh_db_session.c':['coh_db_session_choose','coh_db_session_take_handoff_owner_alloc'],
 'native-android/engine/mapclient/coh_mapclient.c':['coh_map_serialize'],
}
EXTRA=['upstream/ouroboros/Common/comm_backend.h','native-android/engine/dbclient/coh_db_handoff_owner.h',
 'native-android/engine/mapclient/coh_mapclient.h','native-android/engine/auth-interop/deployment/windows/auth_db_development_owner.c',
 'native-android/engine/auth-interop/deployment/windows/auth_db_development_owner.h']

def sha(b):return hashlib.sha256(b).hexdigest()
def git(name):return subprocess.check_output(['git','-C',str(ROOT),'show',REV+':'+name],stderr=subprocess.DEVNULL)

def mask(raw):
    # Keep byte positions/newlines; erase comments and quoted C literals before
    # balancing definition braces. No preprocessing or executable evaluation.
    out=bytearray(raw);i=0;n=len(raw)
    while i<n:
        begin=i
        if raw[i:i+2]==b'//':
            end=raw.find(b'\n',i);i=n if end<0 else end
        elif raw[i:i+2]==b'/*':
            end=raw.find(b'*/',i+2)
            if end<0:raise ValueError('unterminated_comment')
            i=end+2
        elif raw[i] in (34,39):
            quote=raw[i];i+=1
            while i<n:
                if raw[i]==92:i+=2
                elif raw[i]==quote:i+=1;break
                else:i+=1
            else:raise ValueError('unterminated_literal')
        else:i+=1;continue
        for j in range(begin,min(i,n)):
            if raw[j] not in (10,13):out[j]=32
    return bytes(out)

def function(raw,name):
    clean=mask(raw);hits=[]
    pattern=rb'(?m)^[A-Za-z_][A-Za-z0-9_ \t*]*\b'+name.encode()+rb'[ \t]*\('
    for m in re.finditer(pattern,clean):
        pos=clean.index(b'(',m.start());depth=1;pos+=1
        while pos<len(clean) and depth:
            if clean[pos]==40:depth+=1
            if clean[pos]==41:depth-=1
            pos+=1
        while pos<len(clean) and clean[pos] in b' \t\r\n':pos+=1
        if pos==len(clean) or clean[pos]!=123:continue
        depth=1;pos+=1
        while pos<len(clean) and depth:
            if clean[pos]==123:depth+=1
            if clean[pos]==125:depth-=1
            pos+=1
        if depth:raise ValueError('unbalanced_function')
        if raw[pos:pos+1]==b'\n':pos+=1
        hits.append((m.start(),pos))
    if len(hits)!=1:raise ValueError('nonunique_function_'+name)
    start,end=hits[0]
    return {'offset':start,'bytes':end-start,'line':raw[:start].count(b'\n')+1,'sha256':sha(raw[start:end])}

def audit():
    files={};spans={}
    for name in sorted(set(FUNCTIONS)|set(EXTRA)):
        raw=git(name);files[name]={'bytes':len(raw),'sha256':sha(raw)}
        if name in FUNCTIONS:spans[name]={f:function(raw,f) for f in FUNCTIONS[name]}
    return {'schema':'coh-original-fresh-character-source-scope-v1','repository_commit':REV,
      'source_files':files,'whole_function_spans':spans,'source_file_count':len(files),
      'whole_function_count':sum(map(len,spans.values())),
      'source_only':True,'project_imports_tests_compilers_servers_registry_or_network_executed':False,
      'original_sendCharacterCreate_definition_present':True,
      'existing_choose_rejects_empty_slot':True,'existing_map_connect_emits_newCharacter_zero':True,
      'server_allocates_fresh_dbid_from_authenticated_empty_slot':True,
      'fresh_allocated_container_is_not_initialized_character':True,
      'proposal_scope':'new opaque fresh-auth to server-allocated uninitialized-container handoff; no Map client connect',
      'creation_map_connect_body_source_chain':['sendCharacterCreate','sendCharacterToServer','character_SendCreate',
        'sendTray','costume_send','powerCustList_send','sendEntStrings'],
      'actual_creation_or_map_handoff_executed':False,'normal_version_checksum_reference_admitted':False,
      'historical_fixture_identity_or_sql_ownership_transfer_proposed':False}

if __name__=='__main__':print(json.dumps(audit(),indent=2,sort_keys=True))
