#!/usr/bin/env python3
"""Focused raw replay sink: actual payload streaming, bounds, IO and cleanup."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 source=Path(__file__).with_name('test_post_ready_replay.c');header=ROOT/'native-android/combined-client/app/src/main/cpp/post_ready_replay.h';interop=header.with_name('interop_network.c');wiring=Path(__file__).with_name('test_post_ready_wiring.c');native_java=ROOT/'native-android/combined-client/app/src/main/java/org/coh/nativecombined/InteropNative.java';paths=[Path(__file__).resolve(),source,header,interop,wiring,native_java];
 text=interop.read_text();begin=text.index('static void save_post_ready_message(');end=text.index('\n#endif\nstatic CohStatus observe',begin);methods=text[begin:end];assert methods.count('JNIEXPORT')==1
 assert 'if(event->kind==COH_INITIAL_CAPTURE_RAW_POST) {save_post_ready_message(h,&lease);}' in text;assert text.count('save_post_ready_message(h,&lease)')==1
 map_source=ROOT/'native-android/engine/initial-capture/coh_request_tx_map.c';capture_header=map_source.with_name('coh_initial_capture.h');paths.extend([map_source,capture_header,map_source.with_name('coh_initial_map.c')]);rawmap=map_source.read_text();post=rawmap[rawmap.index('static CohStatus ic_post('):rawmap.index('static int ic_cancel(',rawmap.index('static CohStatus ic_post('))];assert post.count('ic_observe(x,COH_INITIAL_CAPTURE_RAW_POST)')==1;assert post.index('ic_observe(x,COH_INITIAL_CAPTURE_RAW_POST)')<post.index('coh_rep_update_prefix(');assert 'x->d.continuation.client_ready_sent&&reader.bytes.data' in post
 assert 'post_replay_reconcile(&h->post_replay,d.continuation.post_ready_messages)'in text;assert 'post_replay_finish(&h->post_replay,d.continuation.post_observation_complete)'in text and text.count('post_replay_finish(&h->post_replay,0)')==2
 tap=Path(__file__).with_name('test_post_ready_tap.c');paths.append(tap);generated_tap=out/'test_post_tap.c';generated_tap.write_text(tap.read_text().replace('/* SHIPPED_POST */',post[:post.rindex('\n#endif')]))
 generated=out/'test_post_wiring.c';generated.write_text(wiring.read_text().replace('/* SHIPPED_METHODS */',methods));pins={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest()for x in paths};results={}
 for mode,extra in [('release',['-O2']),('asan',['-O1','-fsanitize=address','-fno-omit-frame-pointer']),('ubsan',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  binary=out/mode;cmd=['cc','-std=c11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fstack-usage','-fno-pie','-no-pie',*extra,str(source),'-lcrypto','-o',str(binary)];c=subprocess.run(cmd,capture_output=True,text=True);(out/(mode+'-compile.log')).write_text(c.stdout+c.stderr);assert c.returncode==0,(mode,'compile')
  e=subprocess.run([str(binary)],capture_output=True,text=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'},timeout=30);(out/(mode+'-run.log')).write_text(e.stdout+e.stderr);assert e.returncode==0,(mode,'run');results[mode]=json.loads(e.stdout)
  wired=out/(mode+'-wiring');c=subprocess.run([*cmd[:cmd.index(str(source))],'-I',str(wiring.parent),str(generated),'-lcrypto','-o',str(wired)],capture_output=True,text=True);(out/(mode+'-wiring-compile.log')).write_text(c.stdout+c.stderr);assert c.returncode==0,(mode,'wiring compile')
  e=subprocess.run([str(wired)],capture_output=True,text=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'},timeout=30);(out/(mode+'-wiring-run.log')).write_text(e.stdout+e.stderr);assert e.returncode==0,(mode,'wiring run');results[mode+'_wiring']=json.loads(e.stdout)
  tapped=out/(mode+'-tap');c=subprocess.run([*cmd[:cmd.index(str(source))],'-I',str(wiring.parent),str(generated_tap),'-lcrypto','-o',str(tapped)],capture_output=True,text=True);(out/(mode+'-tap-compile.log')).write_text(c.stdout+c.stderr);assert c.returncode==0,(mode,'tap compile')
  e=subprocess.run([str(tapped)],capture_output=True,text=True,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0'},timeout=30);(out/(mode+'-tap-run.log')).write_text(e.stdout+e.stderr);assert e.returncode==0,(mode,'tap run');results[mode+'_tap']=json.loads(e.stdout)
 fixture=out/'native-synthetic-fixture.bin';e=subprocess.run([str(out/'release'),str(fixture)],capture_output=True,text=True);assert e.returncode==0
 java=ROOT/'native-android/combined-client/app/src/main/java/org/coh/nativecombined/PostReadyReplayStore.java';test=Path(__file__).with_name('TestPostReadyReplayStore.java');classes=out/'classes';classes.mkdir()
 c=subprocess.run(['java','-Xmx128m','com.sun.tools.javac.Main','--release','8','-Xlint:all','-Werror','-d',str(classes),str(java),str(test)],capture_output=True,text=True);(out/'java-compile.log').write_text(c.stdout+c.stderr);assert c.returncode==0,'Java compile'
 e=subprocess.run(['java','-Xmx64m','-cp',str(classes),'org.coh.nativecombined.TestPostReadyReplayStore',str(out),str(fixture)],capture_output=True,text=True);(out/'java-run.log').write_text(e.stdout+e.stderr);assert e.returncode==0,'Java run';results['java']=json.loads(e.stdout)
 pins.update({str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest()for x in [java,test]})
 assert pins=={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest()for x in [*paths,java,test]}
 result={'passed':True,'source_sha256':pins,'results':results,'scope':'Original byte spans and real FD writes; no JNI/network/server/Thor or Java export claim. No new decode.'};(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'results':results}))
if __name__=='__main__':main()
