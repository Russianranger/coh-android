#!/usr/bin/env python3
"""Focused new InteropNative Android13 UI/JNI/socket qualification.

Only source-layout scripted peers run. The accepted old framework driver is
imported for small ADB/UI/SAF helpers; its run()/old suites are never invoked.
"""
import argparse,contextlib,hashlib,json,re,selectors,subprocess,threading,time,zipfile
from pathlib import Path
from emulator_check import Check,PACKAGE,MAIN,retained_launcher,installed_apk_contract
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
IDLE_REPORT={'schema':'coh-native-initial-interop-numeric-v1','phase':'IDLE','world_authority':False}
AUTHORITY=('authserver_authenticated','normal_version_admitted','checksum_reference_admitted','source_generation_admitted','complete_initial_character','actor_publication','ack_permitted','sends_ready','sends_received_character','sends_full_update_ack','world_authority','live_world_rendered')
TOP_NUMBERS=('capture_phase status last_status failure groups_observations allents_observations reqallents_sent groups_lease_callbacks initial_lease_callbacks observer_status groups_bytes groups_bits initial_bytes initial_bits initial_post_command_cursor db_phase map_phase attempts character_lists character_choices map_handoffs opened_sockets closed_sockets edit_messages_handled edit_message_last_type edit_message_last_bytes').split()
TOP_BOOLS=('diagnostic_only local_development_auth server_identity_bound selected_owner_bound groups_observed raw_allents_observed cleanup_verified suspend_requested disconnect_requested packet_copy_retained refused_command_valid request_tx_available').split()
TOP_STRINGS=('schema phase failure_code cleanup_scope refused_command_kind').split()
def need(ok,message):
 if not ok:raise ValueError(message)
def sha(data):return hashlib.sha256(data).hexdigest()
def numeric_snapshot(value):
 need(isinstance(value,dict)and set(value)==set(TOP_NUMBERS+TOP_BOOLS+TOP_STRINGS+list(AUTHORITY))|{'first_failure','map_protocol','request_tx'},'unexpected interop public keys')
 need(value['schema']=='coh-native-initial-interop-numeric-v1'and value['cleanup_scope']=='owned_transport_counters','wrong report scope')
 need(value['diagnostic_only']is True and value['packet_copy_retained']is False,'unexpected packet retention')
 need(all(value[k]is False for k in AUTHORITY),'unqualified authority claim')
 need(all(type(value[k])is bool for k in TOP_BOOLS),'invalid boolean')
 need(all(type(value[k])is int and 0<=value[k]<(1<<53)for k in TOP_NUMBERS),'invalid numeric observation')
 need(value['phase']in('IDLE','DB_CONNECTING','CHARACTERS_READY','MAP_CONNECTING','WAIT_GROUPS','WAIT_ALLENTS','INITIAL_OBSERVED','TIMED_OUT','SUSPENDED','CANCELLED','CLOSED','FAILED','UNSUPPORTED'),'invalid phase')
 need(value['failure_code']in('NONE','INPUT','OWNER','PROTOCOL','GROUPS','REQUEST','COMMAND','HEADER','OBSERVER','RELEASE','TIMEOUT','CANCELLED','MEMORY'),'invalid failure enum')
 need(re.fullmatch('[A-Z_]{1,96}',value['refused_command_kind'])is not None,'nonfixed refused command')
 need(all(value[k]<=7 for k in('status','last_status','observer_status')),'invalid status')
 need(value['groups_observations']<=1 and value['allents_observations']<=1 and value['reqallents_sent']<=1 and value['groups_lease_callbacks']<=1 and value['initial_lease_callbacks']<=1,'duplicate publication')
 need(value['groups_bytes']<=4194304 and value['initial_bytes']<=4194304 and value['groups_bits']<=8*value['groups_bytes'] and value['initial_post_command_cursor']<=value['initial_bits']<=8*value['initial_bytes'],'invalid observed lengths')
 first=value['first_failure'];need(set(first)=={'valid','local_phase','db_phase','map_phase','status','failure'}and type(first['valid'])is bool,'invalid first failure')
 need(all(type(first[k])is int and 0<=first[k]<=maximum for k,maximum in(('local_phase',10),('db_phase',12),('map_phase',10),('status',7),('failure',12))),'invalid first failure values')
 need(value['capture_phase']<=7 and value['failure']<=12 and value['db_phase']<=12 and value['map_phase']<=10,'invalid module enum')
 mapping=value['map_protocol'];need(set(mapping)=={'phase','stage','last_status','scene_structures','udp'},'invalid map diagnostics')
 udp=mapping['udp'];need(set(udp)=={'state','datagrams_sent','datagrams_received','send_would_block','interrupted','io_errors','link'},'invalid UDP diagnostics')
 link=udp['link'];need(set(link)=={'sent','received','retransmits','acknowledged','tx_pending'},'invalid link diagnostics')
 need(all(type(v)is int and 0<=v<(1<<53)for d in(mapping,udp,link)for v in d.values()if not isinstance(v,dict)),'invalid nested numeric diagnostics')
 tx=value['request_tx']
 if not value['request_tx_available']:need(tx is None,'unavailable request witness retained data')
 else:
  booleans=('diagnostic_only','valid','witness_retired','queue_attempted','queue_succeeded','first_send_accepted','peer_transport_ack_observed','command_specific_emission_proved','server_receipt_proved','ack_permitted','world_authority')
  counts=('first_send_attempts','retry_send_attempts','successful_retries','deferred_send_callbacks','failed_send_callbacks');offsets=('queue_offset_ms','first_send_offset_ms','last_send_offset_ms','retirement_offset_ms')
  need(isinstance(tx,dict)and set(tx)==set(booleans+counts+offsets+('queue_status','refusal','retirement')),'unexpected request witness keys')
  need(all(type(tx[k])is bool for k in booleans)and tx['diagnostic_only']is True,'invalid request witness booleans')
  need(all(tx[k]is False for k in('command_specific_emission_proved','server_receipt_proved','ack_permitted','world_authority')),'request witness granted authority')
  need(all(type(tx[k])is int and 0<=tx[k]<=1000000 for k in counts)and all(type(tx[k])is int and 0<=tx[k]<=600000 for k in offsets),'request witness bounds')
  need(type(tx['queue_status'])is int and 0<=tx['queue_status']<=7 and type(tx['refusal'])is int and 0<=tx['refusal']<=5 and type(tx['retirement'])is int and 0<=tx['retirement']<=7,'request witness enums')
 return value
OBSERVED=('groups_observed','raw_allents_observed','groups_observations','allents_observations','reqallents_sent','groups_lease_callbacks','initial_lease_callbacks','groups_bytes','groups_bits','initial_bytes','initial_bits','initial_post_command_cursor','first_failure')
def unchanged_observations(before,after):need(all(before[k]==after[k]for k in OBSERVED),'retained observation changed')
class InteropCheck(Check):
 def world(self,phase,label,seconds=60):
  report=self.wait_report('native-client-report.json',lambda x:x.get('connection_mode')=='WORLD_HANDOFF'and x.get('world_handoff',{}).get('phase')in phase,label,seconds=seconds)
  need(report.get('preview_is_server_world')is False,'preview became authoritative');numeric_snapshot(report['world_handoff']);return report
 def record_snapshot(self,label,report):
  value=numeric_snapshot(report['world_handoff']);(self.args.output/(label+'-world-handoff.json')).write_text(json.dumps(value,indent=2)+'\n');return value
 def mapped_interop(self):
  pid=self.text('shell','pidof','-s',PACKAGE).strip();need(re.fullmatch('[1-9][0-9]*',pid)is not None,'app process absent')
  maps=self.adb('exec-out','run-as',PACKAGE,'cat','/proc/'+pid+'/maps').stdout;need(len(maps)<=4<<20,'map inventory exceeds bound')
  names=set()
  for line in maps.decode().splitlines():
   parts=line.split(None,5)
   if len(parts)==6 and parts[5].endswith('/libcoh_combined_interop.so'):names.add(parts[5])
  need(len(names)==1,'new JNI DSO not mapped exactly once');data=self.adb('exec-out','run-as',PACKAGE,'cat',next(iter(names))).stdout
  need(sha(data)==self.interop_sha and len(data)==self.interop_bytes,'mapped DSO differs from APK');self.record('actual new InteropNative JNI DSO mapped in app process',bytes=len(data),sha256=sha(data),abi='x86_64')
 @contextlib.contextmanager
 def peer(self,label,mode):
  remote='/data/local/tmp/coh-initial-interop-peer';report=remote+'-'+label+'.json';staging=remote+'-policy.json';self.adb('push',self.args.peer,remote);self.adb('shell','chmod','700',remote);self.adb('shell','rm','-f',report)
  log=(self.args.output/(label+'-peer.stderr')).open('wb');child=None;ready=None;errors=[];stop=threading.Event();thread=None
  first_error=None
  try:
   child=subprocess.Popen([self.args.adb,'-s',self.args.serial,'shell',remote,'--serve','--report',report,'--mode',mode],stdout=subprocess.PIPE,stderr=log)
   raw=b''
   with selectors.DefaultSelector()as selector:
    selector.register(child.stdout,selectors.EVENT_READ);deadline=time.monotonic()+30
    while b'\n'not in raw and time.monotonic()<deadline:
     if selector.select(.5):
      data=child.stdout.read1(4096)
      if not data:break
      raw+=data;need(len(raw)<=4096,'peer readiness too large')
   need(b'\n'in raw,'peer did not become ready');ready=json.loads(raw.splitlines()[0]);need(ready.get('scripted_source_layout')is True and ready.get('real_server_interoperability')is False,'unbound peer scope');need(all(type(ready.get(k))is int and 0<ready[k]<=65535 for k in('db_port','map_port'))and type(ready.get('pid'))is int and ready['pid']>0,'invalid peer readiness')
   def refresh():
    elapsed=int(float(self.adb('shell','cat','/proc/uptime',timeout=5).stdout.split()[0])*1000);policy={'schema':'coh-native-local-policy-v1','state':'ready','db_address':'127.0.0.1','db_port':ready['db_port'],'net_version':5,'account':'Fixture','server_session_id':'f'*32,'import_generation':'e'*32,'ready_elapsed_ms':elapsed,'encryption_required':False,'outbound_compressed':False};path=self.args.output/(label+'-synthetic-policy.json');path.write_text(json.dumps(policy)+'\n');self.adb('push',path,staging,timeout=5);self.adb('shell','run-as',PACKAGE,'cp',staging,'files/native-session-policy.json.tmp',timeout=5);self.adb('shell','run-as',PACKAGE,'mv','files/native-session-policy.json.tmp','files/native-session-policy.json',timeout=5)
   refresh()
   def maintain():
    while not stop.wait(2):
     try:refresh()
     except Exception as failure:errors.append(type(failure).__name__);return
   thread=threading.Thread(target=maintain,daemon=True);thread.start();yield ready
  except BaseException as failure:
   first_error=failure;raise
  finally:
   stop.set()
   if thread:
    thread.join(timeout=20)
    if thread.is_alive():errors.append('policy refresher did not stop')
   if ready:
    try:
     cmdline=self.adb('exec-out','cat','/proc/'+str(ready['pid'])+'/cmdline',check=False).stdout
     if cmdline.split(b'\0')[0]==remote.encode():self.adb('shell','kill','-TERM',ready['pid'],check=False)
    except Exception:errors.append('owned peer termination observation failed')
   if child:
    try:
     tail,_=child.communicate(timeout=10)
     (self.args.output/(label+'-peer-final.stdout')).write_bytes(tail)
    except subprocess.TimeoutExpired:
     child.terminate()
     try:child.communicate(timeout=5)
     except subprocess.TimeoutExpired:errors.append('adb peer supervisor did not exit')
     errors.append('peer process exit timeout')
   log.close()
   if ready:
    try:
     result=self.adb('exec-out','cat',report,check=False);need(result.returncode==0 and len(result.stdout)<=16384,'peer final report absent/oversized');peer=json.loads(result.stdout);(self.args.output/(label+'-peer.json')).write_bytes(result.stdout)
     need(child.returncode==0 and peer['failed']is False and peer['opened_sockets']==peer['closed_sockets']==2,'peer cleanup failed');need(peer['reqallents_unique']==1 and peer['character_lists']==peer['character_choices']==peer['map_handoffs']==1,'scripted transaction incomplete');need(all(peer[k]==0 for k in('forbidden_application_commands','ready_commands','received_character_commands','full_update_ack_commands')),'forbidden application command sent');need(peer['real_server_interoperability']is False and peer['whole_original_allents_producer_executed']is False,'peer authority scope changed');self.record('scripted OS UDP transaction and peer cleanup',scenario=label,mode=mode,reqallents_unique=1,opened_sockets=2,closed_sockets=2,scripted_only=True,world_authority=False)
    except Exception as failure:errors.append('final peer receipt: '+str(failure)[:200])
   for command in(('shell','run-as',PACKAGE,'rm','-f','files/native-session-policy.json','files/native-session-policy.json.tmp'),('shell','rm','-f',remote,report,staging)):
    try:
     if self.adb(*command,check=False).returncode:errors.append('fixture cleanup refused')
    except Exception:errors.append('fixture cleanup failed')
   if errors:
    (self.args.output/(label+'-cleanup-failure.json')).write_text(json.dumps({'failures':errors,'original_failure_preserved':first_error is not None})+'\n')
    if first_error is None:raise ValueError('peer/policy lifetime failed: '+repr(errors))

 def choose(self,label):
  self.tap('Test world handoff');characters=self.world({'CHARACTERS_READY'},label+' actual new JNI character list');need(characters['world_handoff']['attempts']==1 and characters['world_handoff']['character_lists']==1,'unexpected list transaction');self.tap('Native Fixture',prefix=True);return characters
 def observed(self,label):
  report=self.world({'INITIAL_OBSERVED'},label+' raw initial numeric observation');v=self.record_snapshot(label,report)
  need(v['groups_observed']is True and v['raw_allents_observed']is True and v['reqallents_sent']==v['groups_observations']==v['allents_observations']==v['groups_lease_callbacks']==v['initial_lease_callbacks']==1,'missing observation sequence');need(v['initial_bytes']==65536 and v['initial_bits']==524288 and v['initial_post_command_cursor']>0,'wrong synthetic initial fixture');need(v['status']==2 and v['failure_code']=='NONE'and v['first_failure']['valid']is False,'initial observation mislabeled accepted');
  if v['request_tx_available']:need(v['request_tx']['valid']is True and v['request_tx']['witness_retired']is True and v['request_tx']['refusal']==0,'request witness refused synthetic captured transaction')
  need(v['cleanup_verified']is True and v['opened_sockets']==v['closed_sockets']==2,'initial owner transport cleanup absent');self.record('new Android JNI GROUPS then REQALLENTS then bounded raw initial observation',scenario=label,initial_bytes=v['initial_bytes'],initial_bits=v['initial_bits'],status=2,world_authority=False);return report
 def resume_recents(self,session):
  self.adb('shell','input','keyevent','KEYCODE_APP_SWITCH');time.sleep(.5);root=self.dump();card=next((n for n in root.iter('node')if n.attrib.get('resource-id','').endswith('/snapshot')),None)
  if card is None:self.adb('shell','input','keyevent','KEYCODE_APP_SWITCH')
  else:
   xy=self.bounds(card);need(xy is not None,'recent card has no bounds');self.adb('shell','input','tap',(xy[0]+xy[2])//2,(xy[1]+xy[3])//2)
  return self.wait_report('native-client-report.json',lambda x:x.get('session_id')==session and x.get('resumed')is True,'same native Activity resumes from Home',seconds=60)
 def run_focused(self):
  need(self.text('shell','getprop','ro.boot.qemu').strip()=='1'and self.text('shell','getprop','ro.product.cpu.abi').strip()=='x86_64'and self.text('shell','getprop','ro.build.version.sdk').strip()=='33','fresh Android13x86_64 emulator required');need(not self.text('shell','pm','list','packages','--user','0',PACKAGE).strip(),'never clear an existing app')
  time.sleep(30);need(re.search(r'^Success\s*$',self.text('install','-g',self.args.apk),re.M)is not None,'APK install failed');self.launch(MAIN);self.wait_report('combined-report.json',lambda x:x.get('installed_apk_status')=='ready','installed APK identity');initial=self.report('combined-report.json');installed_apk_contract(initial,sha(self.args.apk.read_bytes()),self.args.apk.stat().st_size);self.launcher_baseline=self.activity_state('initial-launcher');self.tap('Launch native client');native=self.wait_report('native-client-report.json',lambda x:x.get('assets_verified')is True and x.get('native',{}).get('frames',0)>=30,'new APK native Activity preview');session=native['session_id'];need(native['world_handoff']==IDLE_REPORT,'handoff began without explicit button')
  with self.peer('captured','captured'):
   self.choose('captured');captured=self.observed('captured');self.mapped_interop();self.export_native();exported=json.loads((self.args.output/'exported-native-report.json').read_bytes());need(exported['connection_mode']=='WORLD_HANDOFF','export lost mode');numeric_snapshot(exported['world_handoff']);unchanged_observations(captured['world_handoff'],exported['world_handoff']);self.record('actual SAF export retains immutable mode-tagged numeric world handoff',world_authority=False)
   self.tap('Disconnect client');closed=self.world({'CLOSED'},'explicit new-mode disconnect');unchanged_observations(captured['world_handoff'],closed['world_handoff']);need(closed['world_handoff']['cleanup_verified']is True,'disconnect cleanup absent')
  with self.peer('cancelled-wait','none'):
   self.choose('cancelled wait');waiting=self.world({'WAIT_ALLENTS'},'GROUPS and one REQALLENTS before Home');before=self.record_snapshot('waiting',waiting);need(before['groups_observed']is True and before['raw_allents_observed']is False and before['reqallents_sent']==1,'waiting scope wrong');self.adb('shell','input','keyevent','KEYCODE_HOME');home=self.world({'SUSPENDED'},'Home cancels active new JNI owner');after=self.record_snapshot('home-cancelled',home);need(home['resumed']is False and after['cleanup_verified']is True and after['opened_sockets']==after['closed_sockets']==2,'Home left sockets active');need(after['first_failure']['valid']is True and after['failure_code']=='CANCELLED','Home cancellation missing');need(after['groups_bytes']==before['groups_bytes']and after['reqallents_sent']==1 and after['initial_bytes']==0,'Home lost prior observation');self.resume_recents(session);resumed=self.world({'SUSPENDED'},'Home return requires explicit reconnect');unchanged_observations(after,resumed['world_handoff']);self.tap('Return to launcher');self.wait_report('native-client-report.json',lambda x:x.get('session_id')==session and x.get('resumed')is False and any(e.get('type')=='return_to_launcher_ready'for e in x.get('events',[])),'explicit new-mode Return capture')
   deadline=time.monotonic()+20
   while time.monotonic()<deadline:
    state=self.activity_state('returned-launcher')
    if retained_launcher(self.launcher_baseline,state):break
    time.sleep(.2)
   else:raise ValueError('Return did not retain original launcher/task/process')
   self.record('Home cancellation and explicit Return preserve launcher and retained numeric evidence',opened_sockets=2,closed_sockets=2,automatic_reconnect=False)
  self.tap('Launch native client');fresh=self.wait_report('native-client-report.json',lambda x:x.get('session_id')!=session and x.get('assets_verified')is True and x.get('native',{}).get('frames',0)>=30,'fresh native Activity after Return',seconds=60);need(fresh['world_handoff']==IDLE_REPORT,'fresh Activity reconnected automatically')
  with self.peer('fresh-reconnect','captured'):
   self.choose('fresh reconnect');self.observed('fresh-reconnect');self.tap('Disconnect client');closed=self.world({'CLOSED'},'fresh owner explicit disconnect');need(closed['world_handoff']['cleanup_verified']is True,'fresh owner cleanup absent')
  self.native_fault_evidence('interop-final');self.record('new-mode Android13 application has no crash or ANR')
  receipt={'schema':'coh-android-initial-interop-focused-v1','passed':True,'checks':self.proofs,'apk':self.package_receipt['apk'],'package_receipt':self.package_receipt,'peer_receipt_sha256':sha(self.args.peer_receipt.read_bytes()),'source_revision':subprocess.check_output(['git','-C',ROOT,'rev-parse','HEAD'],text=True).strip(),'driver_sha256':sha(Path(__file__).read_bytes()),'device':{'api':33,'abi':'x86_64','emulator':True,'build_fingerprint':self.text('shell','getprop','ro.build.fingerprint').strip()},'actual_Android_JNI_and_OS_UDP':True,'scripted_source_layout_only':True,'original_Auth_Db_Map_service_execution':False,'normal_version_checksum_policy_qualified':False,'complete_initial_character':False,'actor_publication':False,'ACK_authority':False,'world_authority':False,'physical_Thor_qualified':False,'timeout_qualified':False,'old_framework_suite_executed':False};(self.args.output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def main():
 need(__debug__,'Python assertions must be enabled');ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--adb',default='adb');ap.add_argument('--serial',required=True);ap.add_argument('--apk',type=Path,required=True);ap.add_argument('--peer',type=Path,required=True);ap.add_argument('--peer-receipt',type=Path,required=True);ap.add_argument('--package-receipt',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();need(not a.output.exists(),'fresh output required');peer=json.loads(a.peer_receipt.read_bytes());need(peer['passed']is True and peer['abi']=='x86_64'and peer['scripted_source_layout']is True and peer['real_server_interoperability']is False,'unadmitted peer receipt');need(peer['peer']=={'file':a.peer.name,'bytes':a.peer.stat().st_size,'sha256':sha(a.peer.read_bytes())},'peer executable differs');package=json.loads(a.package_receipt.read_bytes());need(package['status']=='passed'and package['abi']=='x86_64'and package['apk']['bytes']==a.apk.stat().st_size and package['apk']['sha256']==sha(a.apk.read_bytes()),'APK receipt differs');need(package['signer_certificate_sha256']=='9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522','unexpected public test signer')
 with zipfile.ZipFile(a.apk)as z:data=z.read('lib/x86_64/libcoh_combined_interop.so')
 need(data[:6]==b'\x7fELF\x02\x01'and int.from_bytes(data[18:20],'little')==62,'wrong JNI ABI');driver=InteropCheck(a);driver.package_receipt=package;driver.interop_sha=sha(data);driver.interop_bytes=len(data)
 try:driver.run_focused()
 except Exception as failure:
  (a.output/'failure.json').write_text(json.dumps({'type':type(failure).__name__,'message':str(failure)[:3000],'scripted_only':True,'world_authority':False},indent=2)+'\n')
  for label,args in(('anr',('shell','dumpsys','activity','lastanr')),('crash',('logcat','-d','-b','crash'))):
   try:(a.output/('failure-'+label+'.txt')).write_bytes(driver.adb(*args,check=False).stdout)
   except Exception:pass
  raise
if __name__=='__main__':main()
