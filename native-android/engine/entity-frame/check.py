#!/usr/bin/env python3
"""Atomic supported full-update header/list/control/delete framing qualification."""
from pathlib import Path
import argparse,hashlib,json,os,sys,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE/'../entities'));import check_teammate_buffs as common
import oracle

def sha(data):return hashlib.sha256(data).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--sanitize',action='store_true');a=ap.parse_args()
 if a.output.exists():ap.error('new output required')
 sources=[HERE/'coh_entity_frame.c',HERE/'../entities/coh_entities.c',HERE/'../entity-control/coh_entity_control.c',HERE/'../replication/coh_replication.c',HERE/'test_frame.c']
 inputs=set(sources)|{HERE/'check.py',HERE/'oracle.py',HERE/'CONTRACT.md',HERE/'source-pins.json',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/tools/protocol_fixture/prepare.py',HERE/'../coh_contracts.h'}
 for d in [HERE,HERE/'../entities',HERE/'../entity-control',HERE/'../replication']:
  for pattern in ['*.h','*.py','*.inc','*.json']:inputs.update(d.glob(pattern))
 hashes={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(inputs)};revision=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip()
 source={n:common.source(n) for n in json.loads((HERE/'source-pins.json').read_text())};pins={n:sha(text.encode()) for n,text in source.items()}
 if pins!=json.loads((HERE/'source-pins.json').read_text()):raise ValueError('original source changed')
 send=common.extract(source['MapServer/src/entity/entsend.c'],'entSendUpdate');recv=common.extract(source['Game/src/entity/entrecv.c'],'entReceiveUpdate');debug=common.extract(source['Game/src/entity/entDebug.c'],'receiveGlobalEntDebugInfo')
 # Verify the whole global-debug function has no wire consumer outside this
 # single outer source guard. This qualifies zero consumption, not debug mode.
 at=debug.index('if(game_state.hasEntDebugInfo)');brace=debug.index('{',at);end=brace+1;depth=1
 while depth:depth+=(debug[end]=='{')-(debug[end]=='}');end+=1
 tail=debug[end:].strip()
 if not tail.startswith('else{') or any(word in tail for word in ('pktGet','bsRead')):raise ValueError('global debug wire reads escape header guard')
 for text,names in [(recv,['cmdOldReceive(pak,&cmd_list,&context);','idx_delta = pktGetBitsPack(pak,1) + 1;','receiveGlobalEntDebugInfo(pak);','playerReceiveControlState(pak);','entReceiveDeletes(pak);','receiveCharacterFromServer(pak, player);']),(send,['pktSendBitsPack(pak,1,SERVER_ALLENTS);','cmdOldServerSend(pak,full_update)','pktSendBitsPack(pak,1,0);','svrPlayerSendControlState(pak,player_ent,link,full_update | re_predict)','entSendDeletes(pak,send_ent.sent_buf,sent_ents_bits)','sendCharacterToClient(pak, player_ent);'])]:
  positions=[text.index(n) for n in names]
  if positions!=sorted(positions):raise ValueError('original prelude order changed')
 with tempfile.TemporaryDirectory(prefix='coh-entity-frame-') as name:
  work=Path(name);fixtures,proof=oracle.build(ROOT,work);(work/'fixtures.h').write_text(fixtures);checks={};binaries={};stack=[]
  for mode,flags in [('release',['-O2','-fstack-usage'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
   exe=work/mode;common.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(work),*sources,'-lm','-o',exe]);checks[mode]=json.loads(common.run([exe],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')));binaries[mode]=sha(exe.read_bytes())
  for path in work.glob('*.su'):
   for line in path.read_text().splitlines():
    location,size,bound=line.split('\t');fn=location.rsplit(':',1)[-1]
    if 'test_frame.c:' not in location:stack.append({'function':fn,'bytes':int(size),'bound':bound})
  if not stack or any(r['bound'] not in {'static','dynamic,bounded'} for r in stack) or sum(r['bytes'] for r in stack)>65536:raise ValueError('stack reserve not justified')
  if any(value!=checks['release'] for value in checks.values()):raise ValueError('mode disagreement')
  cpp=work/'link.cpp';cpp.write_text('#include "coh_entity_frame.h"\nint main(){return coh_entity_frame_read(nullptr,nullptr,nullptr,nullptr,0,nullptr,nullptr,nullptr,0,0)==COH_INVALID?0:1;}\n');objects=[]
  for i,path in enumerate(sources[:-1]):
   obj=work/(str(i)+'.o');common.run(['cc','-std=c99','-O2','-c',path,'-o',obj]);objects.append(obj)
  common.run(['c++','-std=c++11','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-lm','-o',work/'cpp-link']);common.run([work/'cpp-link'])
  if hashes!={str(p.resolve().relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(inputs)} or revision!=common.run(['git','-C',ROOT,'rev-parse','HEAD']).strip():raise ValueError('source inputs changed')
  result={'schema':'coh-supported-entity-prelude-v1','passed':True,'source_revision':revision,'source_sha256':hashes,'original_source_sha256_lf':pins,'original_entSendUpdate_sha256_lf':sha(send.encode()),'original_entReceiveUpdate_sha256_lf':sha(recv.encode()),'nondebug_global_zero_consumption_function_sha256_lf':sha(debug.encode()),'original':proof,'fixtures_sha256':sha(fixtures.encode()),'checks':checks,'binary_sha256':binaries,'native_stack_frames':stack,'cpp_link_passed':True,'source_stable_before_after':True,'debug_mode_supported':False,'original_entity_record_supported_profiles_only':True,'authentic_live_initial_packet_available':False,'all_authentic_self_record_branches_complete':False,'full_character_suffix_composed':False,'dictionary_authority':False,'transport_end_verified':False,'complete_initial_update':False,'actor_publication':False,'ack_permitted':False,'android_built':False,'android_executed':False}
  a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'checks':checks}))
if __name__=='__main__':main()
