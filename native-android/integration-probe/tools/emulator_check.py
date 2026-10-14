#!/usr/bin/env python3
"""Qualify installed integration bytes with real Android input, Surface and Home.

The UDP execution is restricted to native IPv4 loopback. Engine counters and
ADB framework input deliberately do not establish Thor audibility or sticks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import xml.etree.ElementTree as ET
import zipfile

PACKAGE = 'org.coh.integrationprobe'
ACTIVITY = PACKAGE + '/.MainActivity'
OUTPUT = None
ADB = 'adb'
TAPS = []


def adb(*args, check=True):
    return subprocess.run([ADB,*args],check=check,capture_output=True,timeout=30)


def read_report():
    result = adb('exec-out','run-as',PACKAGE,'cat','files/integration-probe-report.json',check=False)
    if result.returncode:
        return None
    assert len(result.stdout) <= 4 << 20, 'Evidence exceeds bound'
    try:
        report = json.loads(result.stdout)
    except (UnicodeDecodeError,json.JSONDecodeError):
        return None
    (OUTPUT/'emulator-integration-report.json').write_bytes(result.stdout)
    if report.get('session_failures',0):
        raise RuntimeError('Sticky native/Java failure: '+json.dumps(report.get('events',[])[-4:]))
    return report


def wait_report(predicate,label,seconds=60,interval=.1):
    deadline = time.monotonic()+seconds
    while time.monotonic()<deadline:
        report = read_report()
        if report is not None and predicate(report):
            return report
        time.sleep(interval)
    raise RuntimeError(label+' did not pass; latest report retained')


def save(name,report):
    (OUTPUT/name).write_text(json.dumps(report,indent=2)+'\n')


def tap(action):
    before = read_report()
    assert before is not None
    event_name = {'run':'checks_requested','play':'audio_play_requested','resize':'resize_requested',
                  'recreate':'view_recreation_requested','home':'home_check_requested',
                  'reset':'view_reset_requested','export':'export_snapshot_created'}[action]
    row = before['control_row']
    for direction in (-1,1):
        for _ in range(5):
            report = read_report()
            target = report['controls'][action]
            if target['visible'] and target['fully_visible'] and target['width']>=20 and target['height']>=20:
                sequence = max(e['sequence'] for e in report['events'])
                x,y = int(target['left']+target['width']//2),int(target['top']+target['height']//2)
                adb('shell','input','touchscreen','tap',str(x),str(y))
                after = wait_report(lambda r:any(e['sequence']>sequence and e['type']==event_name for e in r['events']),
                                    'Actual Button '+action,seconds=15,interval=.05)
                matched = next(e for e in after['events'] if e['sequence']>sequence and e['type']==event_name)
                TAPS.append({'action':action,'tap_x':x,'tap_y':y,'bounds':target,'event':matched})
                save('emulator-ui-tap-proof.json',{'schema':2,'passed':True,'scope':'Measured real Android Button taps; no foreground lifecycle Intents','button_taps':TAPS})
                return after
            xc,yc = int(row['left']+row['width']//2),int(row['top']+row['height']//2)
            distance = int(row['width']//3)
            adb('shell','input','touchscreen','swipe',str(xc-direction*distance),str(yc),str(xc+direction*distance),str(yc),'180')
            time.sleep(.2)
    raise RuntimeError('Button not visible: '+action)


def world_passes(report):
    return [r for r in report.get('world_runs',[]) if r.get('engine_passed') is True and r.get('java_obsolete') is False and r.get('cancelled') is False]


def inject_input(report):
    # All four gestures reach the Android framework and accepted InputAdapter.
    area = report['input_area']
    left,top,width,height = (int(area[k]) for k in ('left','top','width','height'))
    assert width>=64 and height>=64 and area['surface_ready'] is True
    xc,yc = left+width//2,top+height//2
    dx,dy = max(12,width//12),max(12,height//12)
    old_frames = report['input_snapshot']['frames']
    witnesses=[]
    for index,(x0,y0,x1,y1) in enumerate(((xc-dx,yc,xc+dx,yc),(xc+dx,yc,xc-dx,yc),(xc,yc-dy,xc,yc+dy),(xc,yc+dy,xc,yc-dy))):
        initial = read_report()
        adb('shell','input','touchscreen','swipe',str(x0),str(y0),str(x1),str(y1),'450')
        observed = wait_report(lambda r:r['input_adapter']['external_android']['touch_end']>initial['input_adapter']['external_android']['touch_end'] and not r['input_adapter']['touch_active'],
                               'Real touch release '+str(index+1),seconds=10)
        witnesses.append({'gesture':index+1,'bounds':area,'from':[x0,y0],'to':[x1,y1],
                          'frames_before':initial['input_snapshot']['frames'],'frames_after':observed['input_snapshot']['frames'],
                          'pyr_before':initial['input_snapshot']['pyr'],'pyr_after':observed['input_snapshot']['pyr']})
    adb('shell','input','keyboard','keyevent','KEYCODE_SPACE','KEYCODE_W','KEYCODE_S','KEYCODE_A','KEYCODE_D')
    result = wait_report(lambda r:r.get('interactive_direction_mask')==15 and r.get('input_linked_changed_pixels',0)>0 and r.get('interactive_settled_frames',0)>0,
                         'Actual source scene responds in four directions and settles',seconds=45)
    external = result['input_adapter']['external_android']
    assert external['touch_motion_directions']==15 and external['key_down']==external['key_up']>=5
    assert result['input_snapshot']['frames']>old_frames
    assert result['input_snapshot']['held']==0 and result['input_snapshot']['axes']==[0,0,0,0]
    assert any(r.get('external_revision_changes',0)>0 and r.get('input_linked_changed_pixels',0)>0 for r in world_passes(result))
    save('emulator-input-motion-proof.json',{'schema':2,'passed':True,'scope':'Real Android touches reach source camera and authored Atlas bench; physical joystick and gameplay excluded','gestures':witnesses,'direction_mask':result['interactive_direction_mask'],'input_linked_changed_pixels':result['input_linked_changed_pixels'],'settled_frames':result['interactive_settled_frames']})
    return result


def validate(report,full=False):
    assert report['schema']=='coh-native-integration-probe-v2' and report['phases']==[13,14,15]
    assert report['app']['package']==PACKAGE and report['app']['version_name']=='0.1.0-phases13-15'
    assert report['app']['version_code']==1 and report['device']['sdk']==33 and report['device']['emulator_detected'] is True
    assert report['assets_verified'] is True and report['session_failures']==0
    assert report['controller_axis_coverage_passed'] is False and report['device_audible_confirmation_passed'] is False
    assert report['android_input_transport_passed'] is True
    external=report['input_adapter']['external_android']
    assert external['controller_events']==external['motion']==0
    assert external['left_axis_directions']==external['right_axis_directions']==0
    assert report['interactive_direction_mask']==15 and report['input_linked_changed_pixels']>=64
    for run in report['native_runs']:
        assert run['passed'] is True and run['decode']['passed'] is True and run['input_source']['passed'] is True
        decode=run['decode']
        assert decode['maximum_sample_error']<=1 and decode['failed']==0 and decode['reference_compared'] is True and decode['reference_passed'] is True
        assert decode['frames']==18168 and decode['pcm_bytes']==72672 and decode['ov_read_calls']>0
        assert decode['compared_samples']==36336 and decode['maximum_allowed_sample_error']==1
        assert decode['sample_rate']==44100 and decode['channels']==2 and decode['streams']==1 and decode['eos'] is decode['opened'] is decode['cleared'] is True
        udp=run['transport']
        assert udp['passed'] is True and udp['backend_errors']==0 and udp['session_failure'] is udp['expected_cancel'] is udp['cancelled'] is False
        assert udp['sockets_opened']==udp['sockets_closed']==4 and udp['checks']==330
        assert udp['datagrams_sent']==udp['datagrams_received']==84 and udp['byte_parity_checks']==udp['decoded_payloads']==66 and udp['expected_rejects']==18
    cpu=gpu=image=actual=0
    for run in report['world_runs']:
        if run.get('engine_passed') is True and not run.get('java_obsolete'):
            assert run['objects_released'] is True and run['baseline_cpu_passed'] is True and run['baseline_gpu_passed'] is True
            assert run['source_frames_consumed']==run['frames']==180 and run['gl_errors']==0
            assert run['stationary_mismatches']==run['camera_determinism_mismatches']==run['same_camera_image_mismatches']==0
            assert run['interactive_transform_mismatches']==0 and run['session_failure'] is False
            assert run['direction_mask']==(run['cpu_direction_mask']&run['gpu_direction_mask']&run['image_direction_mask'])
            if run['external_revision_changes']>0 and run['input_linked_changed_pixels']>0:
                cpu|=run['cpu_direction_mask'];gpu|=run['gpu_direction_mask'];image|=run['image_direction_mask'];actual|=run['direction_mask']
    assert cpu==gpu==image==actual==15
    for run in report['audio_runs']:
        assert run['decode']['passed'] is True and run['backend_errors']==0
        if run['passed'] is True:
            assert run['decoded_audio_played'] is True and run['completed_clips']==3 and run['closed'] is True
            assert run['result']==0 and run['cancelled'] is False and run['opened'] is run['started'] is run['stopped'] is True
            assert run['requested_rate']==run['actual_rate']==44100 and run['actual_channels']==2 and run['actual_format']==1
            assert run['requested_clips']==3 and run['submitted_frames']==67734 and run['read_frames']>=67734 and run['write_calls']>0
    if full:
        assert report['pre_background_checks_passed'] is report['background_return_gate_passed'] is report['qualification_passed'] is True
        receipt=report['background_return'];pause,stop,resume=(receipt[k] for k in ('pause_sequence','stop_sequence','resume_sequence'))
        assert 0<pause<stop<resume and receipt['input_cleared'] is True
        assert receipt['audio_started_before_pause'] is receipt['transport_started_before_pause'] is True
        audio=next(r for r in report['audio_runs'] if r['run_id']==receipt['interrupted_audio_run_id'])
        assert audio['result']==1 and audio['cancelled'] is audio['opened'] is audio['started'] is audio['stopped'] is audio['closed'] is True
        assert audio['submitted_frames']>0 and audio['decoded_audio_played'] is True
        udp=next(r for r in report['transport_runs'] if r['run_id']==receipt['interrupted_transport_run_id'])
        assert udp['cancelled'] is True and udp['interrupted_blocked_poll']==1 and udp['blocked_polls']>0
        assert udp['sockets_opened']==udp['sockets_closed']==2 and udp['backend_errors']==0
        assert udp['passed'] is True and udp['result']==0 and udp['session_failure'] is False and udp['expected_cancel'] is True and udp['timeouts']==0


def inspect_apk(apk):
    names={'headset.ogg','audio.bin','audio-fixture.json','world.bin','world-reference.bin','material-reference.bin','world-fixture.json','codec-licenses.txt'}
    with zipfile.ZipFile(apk) as z:
        actual={p.removeprefix('assets/') for p in z.namelist() if p.startswith('assets/') and not p.endswith('/')}
        assert actual==names
        licenses=z.read('assets/codec-licenses.txt');assert 0<len(licenses)<=256*1024 and b'Xiph' in licenses and b'BSD' in licenses
        ogg=z.read('assets/headset.ogg');audio=json.loads(z.read('assets/audio-fixture.json'));world=json.loads(z.read('assets/world-fixture.json'))
        assert len(ogg)==12930 and hashlib.sha256(ogg).hexdigest()=='82bec697f9e824d192cac90f32a01421e4a3875aada64fc709862bc4d3ae9198'
        for name,pin in {'audio.bin':audio['audio'],**world['assets']}.items():
            data=z.read('assets/'+name);assert len(data)==pin['bytes'] and hashlib.sha256(data).hexdigest()==pin['sha256']
    return {'apk_sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'apk_bytes':apk.stat().st_size,'compressed_ogg_sha256':hashlib.sha256(ogg).hexdigest(),'compressed_ogg_bytes':len(ogg)}


def export_document(report):
    """Save through the real Android picker and verify the frozen pre-picker bytes."""
    original_home=dict(report['background_return'])
    tapped=tap('export')
    snapshot=next(e for e in reversed(tapped['events']) if e['type']=='export_snapshot_created')['detail']
    deadline=time.monotonic()+20
    saved=False
    while time.monotonic()<deadline and not saved:
        adb('shell','uiautomator','dump','/sdcard/integration-picker.xml',check=False)
        raw=adb('exec-out','cat','/sdcard/integration-picker.xml',check=False).stdout
        try:
            tree=ET.fromstring(raw)
        except ET.ParseError:
            time.sleep(.3);continue
        nodes=list(tree.iter('node'))
        # A Downloads location may need to be selected before Save is enabled.
        save_nodes=[n for n in nodes if n.get('text','').upper()=='SAVE' and n.get('enabled')=='true']
        candidates=save_nodes or [n for n in nodes if n.get('text')=='Downloads' and n.get('enabled')=='true']
        if not candidates:
            candidates=[n for n in nodes if n.get('content-desc') in ('Show roots','Open navigation drawer')]
        if candidates:
            import re
            values=[int(x) for x in re.findall(r'\d+',candidates[0].get('bounds',''))]
            if len(values)==4:
                adb('shell','input','tap',str((values[0]+values[2])//2),str((values[1]+values[3])//2))
                saved=bool(save_nodes)
        time.sleep(.3)
    if not saved:
        raise RuntimeError('Real Android document Save did not become available')
    returned=wait_report(lambda r:any(e['type']=='export_complete' for e in r['events']), 'Actual document export',seconds=15)
    assert returned['background_return']==original_home, 'Picker replaced the genuine Home evidence'
    paths=adb('shell','find','/sdcard/Download','-maxdepth','1','-name','COH-NativeIntegration-*.json',check=False).stdout.decode().splitlines()
    assert paths, 'Exported document missing from Downloads'
    exported=adb('exec-out','cat',paths[-1]).stdout
    assert len(exported)==snapshot['bytes'] and hashlib.sha256(exported).hexdigest()==snapshot['sha256']
    frozen=json.loads(exported);assert frozen['qualification_passed'] is True and frozen['background_return']==original_home
    (OUTPUT/'emulator-exported-report.json').write_bytes(exported)
    save('emulator-export-proof.json',{'schema':2,'passed':True,'scope':'Actual CREATE_DOCUMENT Save and immutable pre-picker qualification bytes','snapshot':snapshot,'document_path':paths[-1],'background_receipt_preserved':True})
    return returned


def main():
    global OUTPUT,ADB
    parser=argparse.ArgumentParser();parser.add_argument('--apk',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--adb',default='adb');args=parser.parse_args()
    OUTPUT=args.output;ADB=args.adb;OUTPUT.mkdir(parents=True,exist_ok=True)
    identity=inspect_apk(args.apk)
    adb('install','-r',str(args.apk));adb('shell','am','force-stop',PACKAGE);adb('shell','pm','clear',PACKAGE);adb('logcat','-c')
    try:
        adb('shell','am','start','-W','-n',ACTIVITY)
        initial=wait_report(lambda r:r.get('assets_verified') is True and not r.get('checks_busy') and r.get('backend_world_active') is True,'Verified assets, native checks, authored scene',seconds=60)
        assert initial['app']['installed_apk']['sha256']==identity['apk_sha256'] and initial['app']['installed_apk']['bytes']==identity['apk_bytes']
        initial=inject_input(initial)
        tap('play');wait_report(lambda r:any(a.get('passed') is True for a in r['audio_runs']) and not r['audio_busy'],'Complete decoded AAudio sequence',seconds=20)
        before=read_report();tap('resize')
        resized=wait_report(lambda r:any(p['width']!=before['input_area']['width'] and p['height']!=before['input_area']['height'] for p in world_passes(r)) and r.get('current_world_gate_passed') is True,'Actual new Surface dimensions',seconds=50)
        gen=resized['generation'];tap('recreate')
        ready=wait_report(lambda r:r['generation']>gen and r['pre_background_checks_passed'] is True,'Actual Surface recreation',seconds=50)
        validate(ready);save('emulator-initial-report.json',ready)
        tap('home');wait_report(lambda r:r.get('home_check_ready') is True,'Active native audio and blocked UDP wait',seconds=15,interval=.02)
        adb('shell','input','keyevent','KEYCODE_HOME')
        paused=wait_report(lambda r:r.get('background_return',{}).get('stop_sequence',0)>0 and not r['audio_busy'] and not r['transport_busy'],'Home owns cancellation and closes workers',seconds=15)
        save('emulator-background-report.json',paused)
        adb('shell','am','start','-W','-n',ACTIVITY)
        wait_report(lambda r:not r['audio_busy'] and not r['checks_busy'] and any(n['reason']=='foreground_return' for n in r['native_runs']),'Fresh foreground native checks',seconds=30)
        tap('play')
        qualified=wait_report(lambda r:r.get('qualification_passed') is True,'Foreground audio/network/scene reopen qualification',seconds=60)
        validate(qualified,full=True);save('emulator-foreground-report.json',qualified)
        # Reset invalidates same-size proof until a new actual graphics epoch completes.
        tap('reset');invalid=read_report();assert invalid['current_world_gate_passed'] is False
        qualified=wait_report(lambda r:r.get('qualification_passed') is True,'Same-size Reset requires new native renderer proof',seconds=50)
        validate(qualified,full=True)
        final=export_document(qualified)
        final=wait_report(lambda r:r.get('qualification_passed') is True,'Picker return completes current renderer',seconds=50)
        validate(final,full=True);save('emulator-final-report.json',final)
        summary={'schema':2,'phases':[13,14,15],'passed':True,**identity,'scope':'Installed Android 13 x86_64; authentic on-device compressed decode, real IPv4 loopback UDP, actual source camera/Atlas scene under real Android framework touch, Surface resize/recreate/Reset and Home cancellation/reopen',
                 'native_runs':len(final['native_runs']),'world_runs':len(world_passes(final)),'audio_runs':len([r for r in final['audio_runs'] if r['passed']]),'interactive_direction_mask':final['interactive_direction_mask'],'input_linked_changed_pixels':final['input_linked_changed_pixels'],'settled_frames':final['interactive_settled_frames'],'actual_home_cycle_passed':True,'actual_document_export_passed':True,'surface_resize_recreation_passed':True,'physical_controller_verified':False,'physical_audibility_verified':False,'thor_device_execution_verified':False,'external_network_execution':False,'server_interoperability_verified':False,'original_game_execution':False}
        save('emulator-smoke-summary.json',summary);print(json.dumps(summary))
    finally:
        (OUTPUT/'emulator-logcat.txt').write_bytes(adb('logcat','-d',check=False).stdout)
        screenshot=adb('exec-out','screencap','-p',check=False)
        if screenshot.returncode==0 and screenshot.stdout.startswith(b'\x89PNG\r\n\x1a\n'):(OUTPUT/'emulator-screenshot.png').write_bytes(screenshot.stdout)


if __name__=='__main__':
    main()
