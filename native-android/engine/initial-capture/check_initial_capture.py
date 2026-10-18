#!/usr/bin/env python3
"""Focused NONSHIPPING capture tests on synthetic source-layout UDP peers."""
from pathlib import Path
import argparse,hashlib,importlib.abc,importlib.util,json,os,re,shlex,subprocess,tempfile,types
HERE=Path(__file__).resolve().parent

def require(value,message):
 if not value:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def command(args,**kw):
 result=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=120,**kw)
 if result.returncode:raise RuntimeError(repr(args)+'\n'+result.stdout+result.stderr)
 return result.stdout

def command_fixture(root,work,frozen):
 pins=json.loads(frozen[(HERE/'command-source-pins.json').resolve()])['sha256_lf'];texts={}
 for name,expected in pins.items():
  raw=frozen[(root/'upstream/ouroboros'/name).resolve()].replace(b'\r\n',b'\n');require(digest(raw)==expected,'command original source pin: '+name);texts[name]=raw.decode()
 text=texts['Common/comm_game.h'];net=texts['libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h']
 require(re.search(r'COMM_MAX_CMD\s*=\s*2\s*,',net)and re.search(r'COMM_OLDMAX_CMD\s+7\b',net),'command source profile constants')
 enum=text[text.index('typedef enum ServerCommCmd'):text.index('} ServerCommCmd;')+len('} ServerCommCmd;')]
 clean=re.sub(r'/\*.*?\*/|//[^\n]*','',enum,flags=re.S);require(re.fullmatch(r'\s*typedef enum ServerCommCmd\s*\{\s*SERVER_UPDATE\s*=\s*COMM_MAX_CMD\s*,(?:\s*SERVER_[A-Z0-9_]+\s*,)+\s*\}\s*ServerCommCmd;',clean),'unsupported command enum syntax')
 names=re.findall(r'\bSERVER_[A-Z0-9_]+\b',clean);require(names[-1]=='SERVER_CMD_COUNT'and len(names)==len(set(names)),'command enum names');expected=[(name,i+2)for i,name in enumerate(names[:-1])]
 def validate_map(raw):
  data=re.sub(r'/\*.*?\*/','',raw,flags=re.S);rows=[]
  for line in data.splitlines():
   if not line.strip():continue
   row=re.fullmatch(r'COH_INITIAL_CAPTURE_COMMAND\((SERVER_[A-Z0-9_]+), ([0-9]+)\)',line);require(row,'unexpected command map text');rows.append((row[1],int(row[2])))
  require(rows==expected,'command map differs from whole source enum')
 table=frozen[(HERE/'coh_initial_command_kinds.inc').resolve()].decode();validate_map(table);controls=0
 for changed in (table.replace('SERVER_UPDATE, 2','SERVER_UPDATE, 3'),table.replace('SERVER_UPDATE, 2','SERVER_UNTRUSTED, 2'),table+'\nCOH_INITIAL_CAPTURE_COMMAND(SERVER_UNTRUSTED, 9999)\n'):
  try:validate_map(changed)
  except ValueError:controls+=1
  else:raise ValueError('mutated command map accepted')
 start=text.index('const char* getServerCmdName(');at=text.index('{',start)+1;depth=1
 while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
 function=text[start:at]+'\n'
 code='#define _POSIX_C_SOURCE 200809L\n#include <assert.h>\n#include <stdio.h>\n#include <string.h>\n#define ARRAY_SIZE(a) ((int)(sizeof(a)/sizeof((a)[0])))\n#define assertmsg(value,message) assert(value)\n#define PERFINFO_AUTO_START(a,b) ((void)0)\n#define PERFINFO_AUTO_STOP() ((void)0)\nenum { COMM_CONTROLCOMMAND=0, COMM_CONNECT=1, COMM_MAX_CMD=2 };\n'+enum+'\n'+function+'\nint main(void){int i;for(i=SERVER_UPDATE;i<SERVER_CMD_COUNT;i++)printf("%u %s\\n",(unsigned)i,getServerCmdName(i));return 0;}\n'
 source=work/'command-original.c';exe=work/'command-original';source.write_text(code);command(['cc','-std=gnu99','-O2','-w',source,'-o',exe]);rows=[]
 for line in command([exe]).splitlines():
  row=re.fullmatch(r'([0-9]+) (SERVER_[A-Z0-9_]+)',line);require(row,'unexpected original command output');rows.append((row[2],int(row[1])))
 require(rows==expected,'original name function differs from enum')
 header='static const struct {uint32_t id;const char*name;} source_command_names[]={\n'+''.join('{'+str(i)+'u,"'+name+'"},\n'for name,i in rows)+'};\n';(work/'command-fixtures.h').write_text(header)
 return {'source_sha256_lf':pins,'whole_ServerCommCmd_sha256_lf':digest(enum.encode()),'whole_getServerCmdName_sha256_lf':digest(function.encode()),'whole_original_name_function_executed':True,'known_whitelist_names':len(expected),'sentinel_excluded':True,'map_mutation_refusals':controls,'generated_oracle_sha256':digest(code.encode()),'original_oracle_binary_sha256':digest(exe.read_bytes()),'no_packet_body_parser_or_protocol_policy_change':True,'runtime_observed':False}

def main():
 if not __debug__:raise ValueError('Python optimization disables original fixture assertions')
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--sanitize',action='store_true');a=parser.parse_args();root=a.source_root.resolve();native=root/'native-android';require(not a.output.exists(),'fresh output required')
 sources=[HERE/'coh_initial_map.c',HERE/'coh_initial_local.c']+[native/p for p in ('engine/dbclient/coh_dbclient.c','engine/dbclient/coh_db_session.c','engine/mapclient/coh_mapclient_owned.c','engine/replication/coh_replication.c','engine/replication/coh_groups.c','engine/network/coh_net.c','engine/network/coh_net_frame.c','engine/network/coh_net_zip.c','engine/network/coh_net_udp.c','engine/auth/coh_auth.c','protocol/coh_protocol.c','src/coh_blowfish.c')]
 helpers=[native/p for p in ('engine/dbclient/check.py','tools/protocol_fixture/prepare.py','engine/replication/groups_oracle.py')]
 manifests=[native/'engine/dbclient/source-pins.json',native/'engine/replication/groups-source-pins.json',HERE/'command-source-pins.json']
 files=set(sources+[HERE/'test_initial_capture.c',HERE/'test_initial_capture_owner.c',Path(__file__).resolve(),*helpers,*manifests,native/'engine/replication/tests/groups_oracle_shim.h',native/'engine/replication/tests/groups_oracle_harness.c'])
 for manifest in manifests:
  for name in json.loads(manifest.read_bytes())['sha256_lf']:files.add(root/'upstream/ouroboros'/name)
 for source in sources+[HERE/'test_initial_capture.c',HERE/'test_initial_capture_owner.c']:
  deps=command(['cc','-std=c11','-I'+str(native/'include'),'-MG','-MM',source]).replace('\\\n',' ').split(':',1)[1]
  for name in shlex.split(deps):
   path=Path(name)
   if path.exists():files.add(path.resolve())
 frozen={p.resolve():p.read_bytes()for p in files};revision=command(['git','-C',root,'rev-parse','HEAD']).strip()
 ordinary=['engine/mapclient/coh_mapclient.c','engine/mapclient/coh_mapclient.h','engine/local/coh_local.c','engine/local/coh_local.h','engine/replication/coh_replication.c','engine/replication/coh_replication.h']
 for name in ordinary:
  relative='native-android/'+name;raw=subprocess.check_output(['git','-C',str(root),'show',revision+':'+relative]);require((native/name).read_bytes()==raw,'ordinary source modified: '+relative)
 for path,raw in frozen.items():
  relative=str(path.relative_to(root));committed=subprocess.check_output(['git','-C',str(root),'show',revision+':'+relative]);require(committed==raw,'source differs from committed HEAD: '+relative)
 def verify():
  for path,raw in frozen.items():require(path.read_bytes()==raw,'source changed: '+str(path))
 verify();loaded=[]
 class FrozenLoader(importlib.abc.Loader):
  def __init__(self,path):self.path=path
  def create_module(self,spec):return None
  def exec_module(self,module):
   verify();require(self.path in frozen and self.path.suffix=='.py','unadmitted project helper');module.__file__=str(self.path);module.__cached__=None;exec(compile(frozen[self.path],str(self.path),'exec',dont_inherit=True),module.__dict__);loaded.append(str(self.path.relative_to(root)));verify()
 original=importlib.util.spec_from_file_location
 def spec(name,location,*args,**kwargs):
  path=Path(location).resolve()
  if path.is_relative_to(root):return original(name,str(path),loader=FrozenLoader(path))
  return original(name,location,*args,**kwargs)
 def load(name,path):
  s=spec(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
 modes=[('release',['-O2'])]
 if a.sanitize:modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
 results={};binaries={};env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 importlib.util.spec_from_file_location=spec
 try:
  with tempfile.TemporaryDirectory(prefix='coh-initial-capture-')as tmp:
   work=Path(tmp);command_proof=command_fixture(root,work,frozen);db=load('initial_capture_db',helpers[0]);lib,_=db.oracle(root,work);db.fixtures(lib,work)
   groups=load('initial_capture_groups',helpers[2]);fixtures,groups_proof=groups.produce_fixtures(root,work/'groups');fixture=next(f for f in fixtures if f['name']=='minimal_world_packed');payload=bytes.fromhex(fixture['payload_hex']);(work/'groups-fixtures.h').write_text('static const unsigned char source_groups_minimal_world_packed[]={'+','.join(map(str,payload))+'};\n#define source_groups_minimal_world_packed_bits '+str(fixture['payload_bits'])+'u\n')
   generated={name:digest((work/name).read_bytes())for name in ('fixtures.h','groups-fixtures.h','command-fixtures.h')};flags=['-std=c11','-Wall','-Wextra','-Werror','-I'+str(native/'include'),'-I'+str(work)]
   for mode,options in modes:
    verify();objects=[]
    for index,source in enumerate(sources):
     obj=work/(mode+str(index)+'.o');extra=['-O0']if source.name in ('coh_protocol.c','coh_blowfish.c')else[];command(['cc',*flags,*options,*extra,'-c',source,'-o',obj]);objects.append(obj)
    exe=work/mode;command(['cc',*flags,*options,HERE/'test_initial_capture.c',*objects,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lz','-lm','-o',exe]);results[mode]=json.loads(command([exe],env=env));binaries[mode]=digest(exe.read_bytes());owner_exe=work/(mode+'-owner');command(['cc',*flags,*options,HERE/'test_initial_capture_owner.c',*objects[2:],'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lz','-lm','-o',owner_exe]);results[mode]['owner_faults']=json.loads(command([owner_exe],env=env));binaries[mode+'-owner']=digest(owner_exe.read_bytes());verify();require(generated=={name:digest((work/name).read_bytes())for name in generated},'generated fixtures changed')
 finally:importlib.util.spec_from_file_location=original
 verify();require(command(['git','-C',root,'rev-parse','HEAD']).strip()==revision,'source revision changed')
 proof={'schema':'coh-nonshipping-initial-capture-tests-v1','passed':True,'source_revision':revision,'all_compiled_and_helper_sources_equal_committed_HEAD':True,'global_aggregate_budget_admitted':False,'callback_storage_budgeted_by_caller':True,'source_sha256':{str(p.relative_to(root)):digest(raw)for p,raw in sorted(frozen.items())},'loaded_frozen_helpers':loaded,'generated_fixture_sha256':generated,'groups_original_fixture_producer':groups_proof,'command_classification_original_source':command_proof,'modes':results,'binary_sha256':binaries,'ordinary_map_local_replication_bytes_changed':False,'ordinary_sources_equal_reviewed_HEAD':ordinary,'leak_sanitizer_enabled':False,'leak_sanitizer_limitation':'Executor /proc task-walk is unavailable; native malloc/calloc/free wrappers and per-scenario FD counts verify owned release.','synthetic_peers_only':True,'real_server':False,'live_initial_packet_captured':False,'whole_original_allents_producer_executed':False,'source_generation_admitted':False,'complete_initial_character':False,'actor_publication':False,'ack_permitted':False}
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':results,'source_inputs':len(frozen)}))
if __name__=='__main__':main()
