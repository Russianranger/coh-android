#!/usr/bin/env python3
"""Build only a scripted Android x86_64 initial-observation peer.

Source fixture producer functions execute; no old qualifier main, server, auth
login, APK or Android process executes here. Peer execution is a separate scope.
"""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];NATIVE=ROOT/'native-android'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(ok,message):
 if not ok:raise ValueError(message)
def module(path):
 spec=importlib.util.spec_from_file_location('interop_'+path.stem,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def run(command):
 p=subprocess.run(list(map(str,command)),capture_output=True,timeout=120)
 need(p.returncode==0,'peer build command failed: '+p.stderr.decode(errors='replace')[-6000:]);return p.stdout

def produce_fixtures(work):
 """Only deterministic original-source writers, never qualifier test mains."""
 db=module(NATIVE/'engine/dbclient/check.py');oracle,_=db.oracle(ROOT,work);db.fixtures(oracle,work);maps=module(NATIVE/'engine/mapclient/check.py');maps.command_fixtures(ROOT,work);groups=maps.groups_fixtures(ROOT,work);accounts=module(NATIVE/'engine/dbclient/tests/account_controls_oracle.py').produce(ROOT,work);inventory=module(NATIVE/'engine/dbclient/tests/inventory_oracle.py').produce(ROOT,work)
 need(len(accounts['whole_source_sha256_lf'])==10 and len(inventory['whole_source_sha256_lf'])==17,'complete account/inventory fixtures required')
 with(work/'server-command-fixtures.h').open('a')as f:f.write('\n#ifdef COH_INITIAL_PEER_RENAME_MAIN\n#define main accepted_ui_peer_main\n#endif\n')
 return groups,accounts,inventory

def main():
 need(__debug__ and not os.environ.get('PYTHONOPTIMIZE'),'Python assertions must be enabled');sys.dont_write_bytecode=True
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--ndk',type=Path,required=True);ap.add_argument('--crypto-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--fragment-compat',action='store_true',help='Build only the 0.1.9 original-form fragment peer role');a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False);a.ndk=a.ndk.resolve();a.crypto_root=a.crypto_root.resolve()
 need('Pkg.Revision = 28.2.13676358'in(a.ndk/'source.properties').read_text(),'pinned NDK28c required')
 receipt=json.loads((a.crypto_root/'receipt.json').read_bytes());need(receipt['abi']=='x86_64'and receipt['status']=='PASS'and receipt['ndk_revision']=='28.2.13676358','qualified x86_64 crypto required')
 pin=NATIVE/'engine/auth/android/openssl-source.json';need(receipt['source_pin_sha256']==sha(pin),'crypto source pin changed')
 for p,h in receipt['native_source_sha256'].items():need(sha(NATIVE/p)==h,'qualified crypto producer changed')
 for p,h in receipt['artifacts_sha256'].items():
  path=(a.crypto_root/p).resolve();need(a.crypto_root in path.parents and sha(path)==h,'crypto artifact differs')
 helpers=[HERE/'check_local_initial_capture.py',NATIVE/'engine/dbclient/check.py',NATIVE/'engine/mapclient/check.py',NATIVE/'engine/replication/check.py',NATIVE/'engine/replication/groups_oracle.py',NATIVE/'engine/dbclient/tests/account_controls_oracle.py',NATIVE/'engine/dbclient/tests/inventory_oracle.py',NATIVE/'tools/protocol_fixture/prepare.py',Path(__file__)]
 inputs={p.resolve()for p in helpers}|{pin.resolve()};manifests=['dbclient/source-pins.json','mapclient/source-pins.json','replication/source-pins.json','replication/groups-source-pins.json','dbclient/tests/account-controls-source-pins.json','dbclient/tests/inventory-source-pins.json']
 for name in manifests:
  p=NATIVE/'engine'/name;inputs.add(p.resolve());j=json.loads(p.read_bytes())
  for name in j['sha256_lf']:inputs.add((ROOT/name if name.startswith(('upstream/','android/'))else ROOT/'upstream/ouroboros'/name).resolve())
 if a.fragment_compat:inputs.add((HERE/'fragment_fixture.py').resolve())
 original_inputs={str(p.relative_to(ROOT)):sha(p)for p in sorted(inputs)};crypto_inputs={str(p.relative_to(a.crypto_root)):sha(p)for p in sorted(a.crypto_root.rglob('*'))if p.is_file()and(p.suffix=='.h'or p.name=='receipt.json'or p.name=='libcrypto.a')}
 helper=module(helpers[0]);sources=[NATIVE/p for p in helper.RELATIVE];peer=NATIVE/('engine/initial-capture/test_initial_fragment_peer.c'if a.fragment_compat else'engine/initial-capture/test_initial_inventory_peer.c')
 with tempfile.TemporaryDirectory(prefix='coh-interop-peer-')as tmp:
  work=Path(tmp);groups,accounts,inventory=produce_fixtures(work);fragment=module(HERE/'fragment_fixture.py').produce(work)if a.fragment_compat else None
  compiler=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/x86_64-linux-android26-clang';flags=['-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(NATIVE/'include'),'-I'+str(work),'-I'+str(a.crypto_root/'include')]
  for source in[*sources,peer]:
   dependency=run([compiler,*flags,'-MM',source]).decode().replace('\\\n',' ').partition(':')[2]
   for name in dependency.split():
    p=Path(name).resolve()
    if p.is_relative_to(ROOT):inputs.add(p)
    else:need(p.is_relative_to(work)or p.is_relative_to(a.crypto_root),'unadmitted peer dependency')
  source_pins={str(p.relative_to(ROOT)):sha(p)for p in sorted(inputs)};fixture_pins={p.name:sha(p)for p in sorted(work.glob('*.h'))};exe=a.output/'coh-initial-interop-peer-x86_64'
  objects=[];commands=[]
  for index,source in enumerate(sources):
   obj=work/('peer-'+str(index)+'.o');options=['-O0']if source.name in('coh_protocol.c','coh_blowfish.c')else[];command=[compiler,*flags,*options,'-c',source,'-o',obj];run(command);objects.append(obj);commands.append(list(map(str,command)))
  command=[compiler,*flags,peer,*objects,a.crypto_root/'lib/libcrypto.a','-lz','-lm','-ldl','-Wl,--no-undefined','-o',exe];run(command);commands.append(list(map(str,command)));data=exe.read_bytes();need(data[:6]==b'\x7fELF\x02\x01'and int.from_bytes(data[18:20],'little')==62,'peer not ELF64x86_64')
  need(source_pins=={str(p.relative_to(ROOT)):sha(p)for p in sorted(inputs)},'compiled peer inputs changed');need(fixture_pins=={p.name:sha(p)for p in sorted(work.glob('*.h'))},'fixture changed')
 need(all(sha(ROOT/p)==h for p,h in original_inputs.items()),'fixture producer inputs changed');need(crypto_inputs=={str(p.relative_to(a.crypto_root)):sha(p)for p in sorted(a.crypto_root.rglob('*'))if p.is_file()and(p.suffix=='.h'or p.name=='receipt.json'or p.name=='libcrypto.a')},'crypto input changed')
 value={'schema':'coh-android-initial-interop-peer-build-v1','passed':True,'source_revision':run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'abi':'x86_64','api':26,'ndk_revision':'28.2.13676358','peer':{'file':exe.name,'bytes':len(data),'sha256':sha(exe)},'source_sha256':source_pins,'compiler_commands':commands,'protocol_and_Blowfish_O0_preserved':True,'fixture_sha256':fixture_pins,'crypto_receipt_sha256':sha(a.crypto_root/'receipt.json'),'crypto_inputs_sha256':crypto_inputs,'fragment_compatibility_role':a.fragment_compat,'fragment_fixture':fragment,'scripted_source_layout':True,'real_server_interoperability':False,'original_auth_db_map_services_executed':False,'whole_original_ALLENTS_producer':False,'old_qualifier_entrypoints_executed':False,'android_executed':False,'world_authority':False,'fixture_producer_scopes':{'GROUPS':groups,'account_controls':accounts,'inventory':inventory}}
 (a.output/'build.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps({'passed':True,'peer':value['peer'],'source_files':len(source_pins),'android_executed':False}))
if __name__=='__main__':main()
