#!/usr/bin/env python3
"""Actual local cache pin, whole-original costume continuation and pose JNI."""
import argparse,hashlib,json,os,pathlib,shlex,shutil,subprocess,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[3];TOOLS=pathlib.Path('native-android/combined-client/tools')
PROBES=['create','pose','sequence','triggered','aianim','netfx','costume','reward','reward_list','costume_slots','costume_body','appearance','sgcolors','scales','partcount']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,**kw):
 r=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,timeout=180,**kw)
 if r.returncode:raise RuntimeError(repr(args)+'\n'+r.stdout[-1200:]+r.stderr[-4000:])
 return r.stdout

def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();work=a.work.resolve();work.mkdir(parents=True,exist_ok=False)
 archive=ROOT/'native-android/engine/entities/qualification/costume-export-20261017/exact-client-dictionary-bins.zip';assert sha(archive)=='350c7ad531209a7e3959cb2f4ae044d8551820cc03e9d40ce17c3aae2a5e3241'
 with zipfile.ZipFile(archive)as z:data=z.read('data/bin/BodyParts.bin')
 assert len(data)==2584 and hashlib.sha256(data).hexdigest()=='b0955c46731ed0cb54ad01d96015b301e583bd0224f8d872f50cfefeb08f6beb'
 inputs=[]
 for name,content in [('BodyParts.bin',data),('mismatch.bin',data[:-1]+bytes([data[-1]^1])),('short.bin',data[:-1]),('long.bin',data+b'\0')]:
  f=work/name;f.write_bytes(content);inputs.append(f)
 timestamp=bytearray(data);timestamp[60:64]=b'\x12\x34\x56\x78';f=work/'timestamp-only.bin';f.write_bytes(timestamp);inputs.append(f)
 flags=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-fno-pie','-no-pie','-fstack-usage','-DCOH_INTEROP_REQUEST_TX=1','-I','native-android/combined-client/diagnostics/interop-adapter-20261018/test-include','-I','native-android/engine/initial-capture','-I','native-android/engine/entities','-I','native-android/engine/session','-I','native-android/include']
 sources=[TOOLS/'test_bodypart_continuation.c',*[pathlib.Path('native-android/engine/initial-capture/coh_initial_'+x+'_probe.c')for x in PROBES],pathlib.Path('native-android/engine/initial-capture/coh_local_bodypart_default.c'),pathlib.Path('native-android/engine/entities/coh_original_costume_receive.c'),pathlib.Path('native-android/engine/entities/coh_entities.c'),pathlib.Path('native-android/engine/replication/coh_replication.c')]
 deps=run([*flags,'-M',*sources]);frozen={pathlib.Path(__file__).resolve():pathlib.Path(__file__).read_bytes(),archive:archive.read_bytes()}
 for line in deps.replace('\\\n',' ').splitlines():
  for name in shlex.split(line.split(':',1)[1]):
   f=pathlib.Path(name);f=(f if f.is_absolute()else ROOT/f).resolve()
   if f.is_relative_to(ROOT):frozen[f]=f.read_bytes()
 modes={};frames=[];env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 for mode,options in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
  target=work/mode;command=[*flags,*options,*sources,'-Wl,--wrap=calloc,--wrap=free,--wrap=open,--wrap=close,--wrap=read,--wrap=__read_chk','-lcrypto','-lm','-o',target];(work/(mode+'-command.json')).write_text(json.dumps(list(map(str,command))))
  run(command);result=run([target,*inputs],env=env);(work/(mode+'.stdout')).write_text(result);modes[mode]={'checks':json.loads(result),'binary_sha256':sha(target)}
 for f in work.glob('release-*.su'):
  for line in f.read_text().splitlines():
   location,size,bound=line.split('\t')
   if any(x in location for x in ['coh_local_bodypart_default.c:','interop_network.c:','coh_original_costume_receive.c:']):frames.append({'function':location.rsplit(':',1)[-1],'bytes':int(size),'bound':bound})
 assert all(p.read_bytes()==data for p,data in frozen.items())
 assert len({json.dumps(v['checks'],sort_keys=True)for v in modes.values()})==1
 a.output.parent.mkdir(parents=True,exist_ok=True);receipt={'schema':'coh-local-bodypart-shipping-continuation-v1','passed':True,'source_head':run(['git','rev-parse','HEAD']).strip(),'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(data).hexdigest()for p,data in sorted(frozen.items())},'modes':modes,'stack_frames':frames,'cache_pin':{'bytes':2584,'sha256':hashlib.sha256(data).hexdigest(),'ordered_source_count':28,'actual_device_server_file_verified':False},'memory':{'interop_owned_bytes':modes['release']['checks']['interop_owned_bytes'],'workspace_bytes':65536,'cache_input_stack_bytes':2584,'initial_ceiling':8388608,'decoded_message_ceiling':4194304,'device_RSS_PSS':None,'external_crypto_and_sanitizer_stack_not_measured':True},'scope':'Shipping configure verifies complete actual local cache file pin and passes28 to whole original receiver. Host uses exact source-layout packet fixture plus JNI/transport doubles. Unknown first geometry dictionary stops BEFORE index Pack; no guessed capacity or skipped bytes. Actual serverfile hash and real packet continuation await Thor test. Selected-self observed pose getter is independent of later costume completeness.','physical_packet_replayed':False,'costume_dictionary_guessed':False,'application_ACK':False,'world_authority':False};a.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'checks':{k:v['checks']for k,v in modes.items()}}))
if __name__=='__main__':main()
