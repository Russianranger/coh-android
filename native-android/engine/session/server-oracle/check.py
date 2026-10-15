#!/usr/bin/env python3
"""Real UDP exchange against pinned original NetLink function bodies.

This is an original-function oracle, not a full CoH server or login witness.
Original x86-oriented functions receive only trusted native-produced fixtures,
run O0 with no_sanitize attributes; new native client, shims and socket wrapper
are independently ASan/UBSan checked.
"""
import argparse, hashlib, json, os, re, subprocess, tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
FUNCTIONS={
 'components/BitStream.c':['initBitStream','bsSetByteAlignment','bsWriteBits','bsReadBits','bsWriteBitsArray','bsReadBitsArray','bsWriteBitsPack','bsReadBitsPack','bsRewind','bsAlignByte','bsGetCursorBitPosition','bsGetBitLength','bsSetCursorBitPosition','bsSetEndOfStreamPosition','bsGetLengthWriteBits','bsGetLengthWriteBitsPack','bsEnded'],
 'network/net_packet.c':['pktSetByteAlignment','pktSetCompression','pktSetOrdered','pktSendBits','pktGetBits','pktGetBitsArray','pktSendBitsArray','pktSendBitsPack','pktGetBitsPack','pktAlignBitsArray','pktEnd'],
 'network/net_packetutil.c':['pktSendBitsAuto','pktGetBitsAuto'],
 'network/netio_core.c':['pktSendAcks','pktWrap','pktUnwrap','blowfishPad'],
 'network/net_version.c':['applyNetworkVersionToLink','applyNetworkVersionToPacket'],
 'network/net_link.c':['netAckConnect','netAckDisconnect','handleControlCommand','pktCreateControlCmd']}
def sha(b):return hashlib.sha256(b).hexdigest()
def extract(text,name):
 m=re.search(r'^(?:static\s+)?(?:unsigned\s+int|void|int|U32|Packet\s*\*)\s*'+re.escape(name)+r'\s*\([^;{}]*\)\s*(?://[^\n]*\n\s*)?\{',text,re.M)
 if not m:raise ValueError('Missing source function '+name)
 begin=text.index('{',m.start());depth=1;at=begin+1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 return text[m.start():at]+'\n'
def run(cmd,**kw):
 r=subprocess.run(list(map(str,cmd)),text=True,capture_output=True,**kw)
 if r.returncode:raise RuntimeError(repr(cmd)+'\n'+r.stdout+r.stderr)
 return r

def prepare(source_root,directory,initialize=False,sanitize=False):
 sources={file:(source_root/'upstream/ouroboros/libs/UtilitiesLib/src'/file).read_bytes().replace(b'\r\n',b'\n').decode() for file in FUNCTIONS}
 snippets=[('__attribute__((no_sanitize_address,no_sanitize_undefined))\n' if sanitize else '')+extract(sources[file],name) for file,names in FUNCTIONS.items() for name in names]
 pins={'schema':'coh-original-netlink-function-pins-v1','upstream_source_commit':json.loads((source_root/'upstream-lock.json').read_text())['commit'],
       'files':{file:sha(text.encode()) for file,text in sources.items()},
       'crypto_audit_files':{file:sha((source_root/'upstream/ouroboros/libs/UtilitiesLib/src/network'/file).read_bytes().replace(b'\r\n',b'\n')) for file in ['crypt.cpp','blowfish.c']},
       'functions':{name:sha(extract(sources[file],name).encode()) for file,names in FUNCTIONS.items() for name in names}}
 path=HERE/'source-pins.json'
 if initialize:path.write_text(json.dumps(pins,indent=2)+'\n')
 elif json.loads(path.read_text())!=pins:raise ValueError('Original source pins differ')
 generated=directory/'original.c';generated.write_text((HERE/'oracle_shims.h').read_text()+'\n'+'\n'.join(snippets)+'\n'+(HERE/'oracle_adapter.c.inc').read_text()+'\n'+(HERE/'server_main.c.inc').read_text())
 # Deliberately no ASan/UBSan on the unchanged legacy pointer/bit functions.
 include=['-I'+str(ROOT/'include'),'-I'+str(ROOT/'engine/auth')]
 common=[ROOT/'protocol/coh_protocol.c',ROOT/'engine/auth/coh_auth.c',ROOT/'engine/auth/coh_auth_openssl.c',ROOT/'src/coh_blowfish.c']
 flags=['-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'] if sanitize else []
 run(['cc','-std=c11','-O0','-w',*flags,*include,generated,*common,'-lcrypto','-lz','-o',directory/'original-server'])
 return pins,sha(generated.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 with tempfile.TemporaryDirectory(prefix='coh-original-server-') as tmp:
  directory=Path(tmp);pins,generated=prepare(a.source_root,directory,a.initialize_pins,a.sanitize)
  rejected=False
  audit=directory/'pin-negative'
  for relative in [Path('upstream-lock.json'),*[Path('upstream/ouroboros/libs/UtilitiesLib/src')/file for file in FUNCTIONS],*[Path('upstream/ouroboros/libs/UtilitiesLib/src/network')/file for file in ['crypt.cpp','blowfish.c']]]:
   target=audit/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((a.source_root/relative).read_bytes())
  changed=audit/'upstream/ouroboros/libs/UtilitiesLib/src/network/net_link.c';changed.write_bytes(changed.read_bytes()+b'\n/* deliberate source-pin negative */\n')
  try:prepare(audit,directory,sanitize=a.sanitize)
  except ValueError as error:
   if str(error)!='Original source pins differ':raise
   rejected=True
  if not rejected:raise ValueError('Mutated source was admitted')
  native=[ROOT/'engine/network'/n for n in ['coh_net.c','coh_net_frame.c','coh_net_zip.c','coh_net_udp.c']]+[ROOT/'protocol/coh_protocol.c',ROOT/'src/coh_blowfish.c',ROOT/'engine/auth/coh_auth.c',ROOT/'engine/auth/coh_auth_openssl.c',ROOT/'engine/session/coh_session_crypto.c',HERE/'native_client.c']
  flags=['-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-I'+str(ROOT/'include'),'-I'+str(ROOT/'protocol'),'-I'+str(ROOT/'engine/network'),'-I'+str(ROOT/'engine/session'),'-I'+str(ROOT/'engine/auth')]
  if a.sanitize:flags+=['-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
  binary=directory/'native-client';run(['cc',*flags,*native,'-lcrypto','-lz','-o',binary])
  cases=[]
  env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:abort_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  for version in [0,2,4,5]:
   for encrypted in [0,1]:
    for drop_first in [0,1]:
     server=subprocess.Popen([str(directory/'original-server'),str(encrypted),str(drop_first)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
     try:
      ready=server.stdout.readline()
      if not ready:raise RuntimeError('Original source server did not start: '+server.stderr.read())
      port=json.loads(ready)['port']
      client=json.loads(run([binary,str(port),str(version),str(encrypted)],env=env,timeout=6).stdout)
      stdout,stderr=server.communicate(timeout=6)
      if server.returncode:raise RuntimeError('Original function server failed '+str((version,encrypted))+'\n'+stdout+stderr)
      stats=json.loads(stdout)
      if not(stats['connected']==1 and stats['encrypt_on']==encrypted and stats['decrypt_on']==encrypted and stats['test_payload_received']==1 and stats['original_ack_calls']>=3 and stats['discarded']==1 and stats['connect_controls']==1 and stats['client_ack_controls']==1 and stats['disconnect_controls']==1 and stats['dropped']==drop_first and stats['negative_datagrams']==3 and stats['sockets_opened']==stats['sockets_closed']==1):raise ValueError('Source witness incomplete '+repr(stats))
      if (client['retransmits']>0)!=bool(drop_first):raise ValueError('Native retry witness differs')
      cases.append({'version':version,'encrypted':bool(encrypted),'dropped_initial_connect':bool(drop_first),'native_negative_datagrams':3,'native':client,'source':stats})
     finally:
      if server.poll() is None:server.kill();server.communicate()
  proof={'schema':'coh-original-netlink-udp-oracle-v1','passed':True,'cases':cases,'source_function_count':sum(map(len,FUNCTIONS.values())),'source_pin_mutation_rejected':rejected,'native_malformed_datagrams':48,'real_os_udp_scenarios':16,'generated_source_sha256':generated,'source_pins_sha256':sha((HERE/'source-pins.json').read_bytes()),'native_sources_sha256':{str(v.relative_to(ROOT)):sha(v.read_bytes()) for v in native},'adapter_sources_sha256':{v.name:sha(v.read_bytes()) for v in [HERE/'oracle_shims.h',HERE/'oracle_adapter.c.inc',HERE/'check.py',HERE/'server_main.c.inc']},'sanitizers':'ASan+UBSan native client and new oracle shims/socket wrapper; original function bodies explicitly no_sanitize; leak sanitizer disabled' if a.sanitize else 'not requested','peer_scope':'unchanged pinned original NetLink handler/producer/unwrap functions behind documented host shims; real loopback UDP','full_original_server':False,'authenticated_session':False,'actual_mapserver_world':False,'gate25_complete':False,'android_execution':False,'physical_thor_accepted':False,'secrets_logged':False,'openssl_version':run(['openssl','version']).stdout.strip()}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'cases':len(cases),'source_functions':proof['source_function_count'],'output':str(a.output)}))
if __name__=='__main__':main()
