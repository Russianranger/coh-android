#!/usr/bin/env python3
"""Source-ordered initial GLOBAL suffix diagnostic; never an ACK certificate."""
from pathlib import Path
import ctypes as C,argparse,hashlib,json,os,re,sys,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'../entities'));import check_teammate_buffs as common
import fixture_builder
SOURCES={
'initial-suffix':['coh_initial_suffix.c'],
'entities':['coh_character_outer.c','coh_character_tail.c','coh_character_creation.c','coh_character_initial.c','coh_character_prefix.c','coh_character_ui.c','coh_entities.c'],
'character-data':['coh_character_data.c'],'replication':['coh_replication.c'],
'entity-globals':['coh_power_info.c','coh_entity_globals.c','coh_badges.c'],
'entity-inventory':['coh_inventory.c','coh_invention.c','coh_inventory_phase.c'],
'entity-team':['coh_team.c'],'entity-superstats':['coh_superstats.c'],'entity-social':['coh_social.c'],
'entity-attributes':['coh_attrib_monitor.c'],'entity-dynamic':['coh_dynamic.c'],'entity-view':['coh_view.c']}
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--oracle-root',type=Path,default=ROOT);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 sources=[HERE.parent/d/n for d,names in SOURCES.items() for n in names]+[HERE/'test_suffix.c']
 inputs=set(sources)|{HERE/'check.py',HERE/'fixture_builder.py',HERE/'CONTRACT.md',HERE/'source-order-pins.json',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/tools/protocol_fixture/prepare.py'}
 for directory in SOURCES:
  for pattern in ('*.h','*.py','*.inc','*.json'):inputs.update((HERE.parent/directory).glob(pattern))
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(inputs)};revision=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip()
 provider=a.oracle_root/'native-android/combined-client/diagnostics';provider_paths=[]
 for directory,names in [('character-outer-20261017',['qualify_outer.py','independent.py','source-pins.json','host-proof.json','group4_oracle.py','group56_oracle.py','group56_independent.py','group56-source-pins.json']),('allents-tail-20261017',['inventory_oracle.py','update_oracle.py','update-source-pins.json','active_invention_oracle.py','active-invention-source-pins.json','member_oracle.py','team_oracle.py','team-source-pins.json','superstats_oracle.py','superstats-source-pins.json','attribute_monitor_oracle.py','attribute-monitor-source-pins.json','dynamic_wire_oracle.py','dynamic-wire-source-pins.json','sky_oracle.py','sky-source-pins.json'])]:provider_paths.extend(provider/directory/n for n in names)
 provider_hashes={str(p.relative_to(a.oracle_root)):sha(p.read_bytes()) for p in provider_paths}
 order={n:common.source(n) for n in json.loads((HERE/'source-order-pins.json').read_text())};pins={n:sha(t.encode()) for n,t in order.items()}
 if pins!=json.loads((HERE/'source-order-pins.json').read_text()):raise ValueError('source order changed')
 send=common.extract(order['MapServer/src/entity/entsend.c'],'entSendUpdate');recv=common.extract(order['Game/src/entity/entrecv.c'],'entReceiveUpdate')
 for text,names in [(send,['sendCharacterToClient(pak, player_ent);','entity_SendPowerInfoUpdate(player_ent, pak);','entity_SendPowerModeUpdate(player_ent, pak);','entity_SendBadgeUpdate(player_ent, pak, full_update);','badgeMonitor_SendInfo(player_ent, pak);','entity_SendInvUpdate( player_ent, pak );','entity_SendInventionUpdate( player_ent, pak );','pktSendString(pak, player_ent->pl->workshopInteracting);','team_sendList( pak, player_ent, full_update );','sgroup_sendList( pak, player_ent, full_update);','league_sendList( pak, player_ent, full_update );','sendAttribDescription( player_ent, pak, 1 );','groupDynSend(pak, full_update)','sendSkyFade(pak);']), (recv,['receiveCharacterFromServer(pak, player);','entity_ReceivePowerInfoUpdate(player, pak);','entity_ReceivePowerModeUpdate(player, pak);','entity_ReceiveBadgeUpdate(player, pak);','badgeMonitor_ReceiveInfo(player, pak);','entity_ReceiveInvUpdate(player, pak);','entity_ReceiveInventionUpdate(player, pak);','strncpy( player->pl->workshopInteracting, pktGetString(pak), 32);','receiveTeamList(pak, playerPtr());','receiveSuperStats(pak, playerPtr());','receiveLeagueList(pak, playerPtr());','receiveAttribDescription(playerPtr(), pak, 1, 0 );','groupDynReceive(pak);','receiveSkyFade(pak);'])]:
  positions=[text.index(n) for n in names]
  if positions!=sorted(positions):raise ValueError('original source order changed')
 zpath=Path(common.run(['cc','-print-file-name=libz.so']).strip()).resolve()
 if not zpath.is_file():raise ValueError('cannot bind linked host zlib')
 zhash=sha(zpath.read_bytes());zlib=C.CDLL(str(zpath));zlib.zlibVersion.restype=C.c_char_p;zlib.zlibCompileFlags.restype=C.c_ulong;zidentity={'path':str(zpath),'sha256':zhash,'version':zlib.zlibVersion().decode(),'compile_flags':zlib.zlibCompileFlags(),'library_rebuilt_with_sanitizers':False,'external_library_stack_measured':False}
 with tempfile.TemporaryDirectory(prefix='coh-initial-suffix-') as tmp:
  work=Path(tmp);fixtures,original=fixture_builder.build(ROOT,a.oracle_root,work);(work/'fixtures.h').write_text(fixtures);checks={};stack=[];binaries={}
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
   exe=work/mode;common.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,'-lm','-lz','-o',exe]);checks[mode]=json.loads(common.run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe.read_bytes())
   linked=re.search(r'libz\.so\.1 => (\S+)',common.run(['ldd',exe]))
   if not linked or Path(linked.group(1)).resolve()!=zpath:raise ValueError('executed zlib identity mismatch')
  stats_calls={'coh_ent_character_stats','character_stats','stats_leaf','pack','read_n','flag','require','signed_bits','check_reader','fail','clear_failure'}
  for p in work.glob('*.su'):
   for line in p.read_text().splitlines():
    location,size,bound=line.split('\t');fn=location.rsplit(':',1)[-1];admitted=('coh_entities.c:' not in location or fn.split('.')[0] in stats_calls) and 'test_suffix.c:' not in location and ('coh_replication.c:' not in location or fn.split('.')[0] in {'valid','coh_rep_read','coh_rep_pack','coh_rep_string'})
    if admitted:stack.append({'function':fn,'bytes':int(size),'bound':bound})
  if not stack or any(r['bound'] not in {'static','dynamic,bounded'} for r in stack) or sum(r['bytes'] for r in stack)>65536:raise ValueError('native stack reserve not justified')
  if any(c!=checks['release'] for c in checks.values()):raise ValueError('mode mismatch')
  cpp=work/'link.cpp';cpp.write_text('#include "coh_initial_suffix.h"\nint main(){return coh_initial_suffix_stage_bytes(COH_SUFFIX_CHARACTER)>0?0:1;}\n');objects=[]
  for i,path in enumerate(sources[:-1]):
   obj=work/(str(i)+'.o');common.run(['cc','-std=c99','-O2','-c',path,'-o',obj]);objects.append(obj)
  common.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-lz','-o',work/'cpp-link']);common.run([work/'cpp-link'])
  if sha(zpath.read_bytes())!=zhash:raise ValueError('host zlib changed')
  if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(inputs)} or provider_hashes!={n:sha((a.oracle_root/n).read_bytes()) for n in provider_hashes} or revision!=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip():raise ValueError('input changed')
  result={'schema':'coh-initial-global-suffix-diagnostic-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'provider_sha256':provider_hashes,'source_order_sha256_lf':pins,'entSendUpdate_sha256_lf':sha(send.encode()),'entReceiveUpdate_sha256_lf':sha(recv.encode()),'original':original,'fixtures_sha256':sha(fixtures.encode()),'checks':checks,'binary_sha256':binaries,'native_stack_frames':stack,'cpp_link_passed':True,'scratch_policy':'serialized explicitly charged loans released before next stage; no persistent6MiB union omitted from badge4MiB budget','host_zlib':zidentity,'dependency_stack_and_sanitizer_closure':False,'selected_entity_prefix_verified':False,'packet_transport_end_verified':False,'whole_initial_update_complete':False,'actor_publication':False,'acknowledgments_enabled':False,'android_built':False,'android_executed':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks}))
if __name__=='__main__':main()
