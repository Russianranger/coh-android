#!/usr/bin/env python3
"""Qualify the bounded JNI report with authentic source-layout probe fixtures."""
import argparse, hashlib, json, os, pathlib, shlex, shutil, subprocess
from report_diagnostic_contract import separate_catalog_boundary
ROOT=pathlib.Path(__file__).resolve().parents[3]
TOOLS=pathlib.Path('native-android/combined-client/tools')
PROBES=['create','pose','sequence','triggered','aianim','netfx','costume','reward','reward_list','costume_slots','costume_body','appearance','sgcolors','scales','partcount']
NAMES=['first_create','first_record_pose','first_record_sequence','first_record_triggered_moves','first_record_ai_animation','first_record_netfx','first_record_costume_prefix','first_reward_string','first_reward_progress']
def need(v,msg):
    if not v: raise ValueError(msg)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check_report(row):
    r=row['report'];need(row['bytes']<7168,'report bound')
    need('catalog_boundary' in r,'essential catalog projection absent')
    separate_catalog_boundary(r)
    need(r['catalog_boundary'] is None, 'obsolete catalog refusal after client admission')
    need(r.get('bodyparts_default') == [0, 28], 'client default unavailable')
    need(r.get('bodyparts_server_cache_status') == 3, 'absent advisory server check invented')
    continuation = r.get('costume_continuation')
    need(isinstance(continuation, list) and len(continuation) == 12
         and all(type(item) is int and item >= 0 for item in continuation), 'continuation numeric shape')
    need(continuation[8] == 1 and continuation[3] in (2, 28)
         and continuation[1] == 3 and continuation[9] == 0, 'client-admitted incomplete geometry continuation')
    need(r['phase']!='REPORT_LIMIT' and 'report_core_limit' not in r,'phase lost')
    need(r['report_limit_bytes']==7168 and r['report_invalid_mask']&~r['report_omitted_mask']==0,'metadata')
    omitted=[name for i,name in enumerate(NAMES) if r['report_omitted_mask']&(1<<i)]
    need(omitted==r['report_omitted_fields'] and bool(omitted)==r['report_truncated'],'omission honesty')
    for i,name in enumerate(NAMES[:8]):
        if r['report_omitted_mask']&(1<<i):need(r[name] is None,'omitted field null')
    for key in ['owner_present','owner_terminal','initial_observation_known','initial_observed','raw_allents_observed','cleanup_verified']:
        need(r[key] is True,'initial cleanup evidence '+key)
    for key in ['groups_present_files','groups_roots','groups_bytes','groups_bits','reqallents_sent','initial_bytes','initial_bits','initial_post_command_cursor','failure','opened_sockets','closed_sockets']:
        need(type(r[key]) is int,'essential numeric '+key)
    need(isinstance(r['request_tx'],dict) and isinstance(r['receive_diagnostics'],dict),'request/receive lost')
    for key in ['source_generation_admitted','complete_initial_character','actor_publication','ack_permitted','world_authority','live_world_rendered']:
        need(r[key] is False,'authority '+key)
    need(not any(x in json.dumps(r) for x in ['PRIVATE_','909090']),'sensitive export')
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path,required=True);args=p.parse_args();out=args.output.resolve();need(not out.exists(),'fresh output');out.mkdir(parents=True)
    cc=pathlib.Path(shutil.which(os.environ.get('CC','cc'))).resolve()
    flags=[str(cc),'-std=c11','-Wall','-Wextra','-Werror','-pedantic','-fno-pie','-no-pie','-fstack-usage','-DCOH_INTEROP_REQUEST_TX=1','-I','native-android/combined-client/diagnostics/interop-adapter-20261018/test-include','-I','native-android/engine/initial-capture','-I','native-android/engine/entities','-I','native-android/engine/session','-I','native-android/include']
    sources=[TOOLS/'test_report_regression.c',*[pathlib.Path('native-android/engine/initial-capture/coh_initial_'+x+'_probe.c') for x in PROBES],pathlib.Path('native-android/engine/initial-capture/coh_local_bodypart_default.c'),pathlib.Path('native-android/engine/entities/coh_original_costume_receive.c'),pathlib.Path('native-android/engine/entities/coh_entities.c'),pathlib.Path('native-android/engine/replication/coh_replication.c')]
    dep=subprocess.run([*flags,'-M',*map(str,sources)],cwd=ROOT,capture_output=True,check=True,text=True);need(not dep.stderr,'dependency diagnostics');(out/'dependencies.txt').write_text(dep.stdout)
    pins={str(TOOLS/name):sha(ROOT/TOOLS/name) for name in ('check_report_regression.py','report_diagnostic_contract.py')};system={str(cc):sha(cc)}
    for line in dep.stdout.replace('\\\n',' ').splitlines():
        for token in shlex.split(line.split(':',1)[1]):
            f=pathlib.Path(token);f=(f if f.is_absolute() else ROOT/f).resolve()
            if f.is_relative_to(ROOT):pins[str(f.relative_to(ROOT))]=sha(f)
            else:system[str(f)]=sha(f)
    env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}
    modes={};commands=[]
    for mode,options in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
        binary=out/('report-'+mode);cmd=[*flags,*options,*map(str,sources),'-Wl,--wrap=calloc','-Wl,--wrap=free','-lcrypto','-lm','-o',str(binary)];commands.append(cmd)
        c=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=90);(out/(mode+'-compile.stderr')).write_bytes(c.stderr);need(c.returncode==0 and not c.stderr,'compile '+mode)
        run=subprocess.run([str(binary)],cwd=ROOT,env=env,capture_output=True,timeout=40);(out/(mode+'-reports.jsonl')).write_bytes(run.stdout);(out/(mode+'-stderr.txt')).write_bytes(run.stderr);need(run.returncode==0 and not run.stderr,'execution '+mode)
        text=run.stdout.decode();rows=[];decoder=json.JSONDecoder()
        while text.strip():
            text=text.lstrip();row,end=decoder.raw_decode(text);rows.append(row);text=text[end:]
        need(rows[-1]['passed'] is True,'receipt')
        for row in rows[:-2]:check_report(row)
        r=rows[0]['report'];need(r['groups_present_files']==508 and r['groups_roots']==33 and r['groups_bytes']==42889 and r['groups_bits']==343112,'Thor regression numeric projection')
        named={x['label']:x for x in rows[:-1]}
        need(named['source-layout-initial-observed']['report']['phase']=='INITIAL_OBSERVED' and named['closed-initial-sticky']['report']['phase']=='CLOSED','capture cleanup phases')
        failure=named['first-failure-retained']['report']['first_failure']
        need(failure['failure']==8 and named['closed-initial-sticky']['report']['first_failure']==failure,'first failure preserved')
        need(named['reward-progress-local-refusal']['report']['report_invalid_mask']&256,'nested local omission')
        first = named['source-layout-initial-observed']['report']
        continuation = first['costume_continuation']
        need(first['first_reward_string']['progress'][1] == 43 and continuation[3] == 2,
             'explicit original framing and admitted count differ')
        omitted = named['maximum-width-scalars']['report']
        need(omitted['costume_continuation'] == continuation and omitted['report_omitted_mask'] & 128,
             'essential admitted continuation lost with optional reward')
        need(named['closed-initial-sticky']['report']['costume_continuation'] == continuation,
             'explicit admitted continuation lost at close')
        default = named['client-default-admitted']['report']
        need(default['first_reward_string']['progress'][1] == 41 and default['costume_continuation'][3] == 28
             and default['costume_continuation'][8] == 1, 'client default did not pass original count validation')
        need(named['client-default-closed']['report']['costume_continuation'] == default['costume_continuation'],
             'client default continuation lost at close')
        need(named['reward-progress-local-refusal']['report']['catalog_boundary'] is None
             and named['reward-progress-local-refusal']['report']['costume_continuation'] == continuation,
             'malformed optional source probe replaced admitted continuation')
        tx=named['maximum-width-scalars']['report']['request_tx']
        for key in ['first_send_attempts','retry_send_attempts','successful_retries','deferred_send_callbacks','failed_send_callbacks']:need(tx[key]==2**32-1,'maximum request count '+key)
        for key in ['queue_offset_ms','first_send_offset_ms','last_send_offset_ms','retirement_offset_ms']:need(tx[key]==2**64-1,'maximum request offset '+key)
        need(named['maximum-width-scalars']['report']['receive_diagnostics']['udp_malformed']==1000000,'maximum receive counter')
        for label in ['source-layout-initial-observed','source-layout-maximum-receive']:
            row=named[label];legacy=dict(row['report'])
            for key in [*NAMES[:8],'owner_present','owner_terminal','initial_observation_known','initial_observed','groups_present_files','groups_roots','report_limit_bytes','report_truncated','report_omitted_mask','report_invalid_mask','report_omitted_fields']:legacy.pop(key,None)
            row['original_0110_required_bytes']=len(json.dumps(legacy,separators=(',',':')).encode())+row['unbounded_detail_bytes']+1 # retained receive trailing newline
            if label=='source-layout-maximum-receive':need(row['original_0110_required_bytes']>=7168,'0.1.10 overflow not reproduced')
        need(rows[-2]['report']['report_omitted_mask']==511 and len(rows[-2]['report']['report_omitted_fields'])==9,'all optional invalid metadata')
        modes[mode]={'receipt':rows[-1],'binary_sha256':sha(binary),'reports':rows[:-1]}
    need(all(modes[m]['reports']==modes['release']['reports'] for m in modes),'deterministic cross-mode JSON')
    need(pins=={k:sha(ROOT/k) for k in pins} and system=={k:sha(pathlib.Path(k)) for k in system},'source/compiler pin changed')
    frames=[]
    for f in out.glob('*.su'):
        for line in f.read_text().splitlines():
            where,size,kind=line.split('\t');need('unbounded' not in kind,'unbounded stack');frames.append({'function':where.rsplit(':',1)[-1],'bytes':int(size),'kind':kind})
    receipt={'schema':'coh-bounded-world-handoff-report-regression-v1','passed':True,'source_sha256':pins,'compiler_headers_sha256':system,'modes':modes,'commands':commands,'stack_frames':frames,'report_limit_bytes':7168,'new_report_heap_allocations':0,'LeakSanitizer_enabled':False,'owned_allocation_zero_wipe_controls':True,'source_layout_fixture_and_production_probes':True,'core_JNI_provider_and_socket_doubles':True,'old_qualifier_entrypoint_executed':False,'Android_Thor_or_original_server_execution':False,'world_authority':False}
    (out/'qualification.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':True,'modes':list(modes),'source_pins':len(pins),'checks_each':modes['release']['receipt']['checks'],'max_report_bytes':modes['release']['receipt']['max_report_bytes']}))
if __name__=='__main__':main()
