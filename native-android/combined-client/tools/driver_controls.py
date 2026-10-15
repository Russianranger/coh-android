#!/usr/bin/env python3
"""Host regression for the observed Android document-drawer occlusion.

The captured Android 13 accessibility state exposed both the open drawer and a
filename behind it. These controls verify driver event selection only, never
reporting a host simulation as Android execution or a real import.
"""
from pathlib import Path
from types import SimpleNamespace
import json
import copy
import tempfile
import xml.etree.ElementTree as ET
from unittest.mock import patch
from emulator_check import (Check, PACKAGE, scene_pixels, settled_preview, viewport_contract,
                            map_report_contract, installed_apk_contract, guest_resources_contract,
                            activity_inventory, retained_launcher)

FILE = 'native-test-donor.apk'
BACKGROUND = f'<node package="com.google.android.documentsui" text="{FILE}" bounds="[189,899][583,956]"/>'
DRAWER = '<node package="com.google.android.documentsui" text="Open from"/><node package="com.google.android.documentsui" text="Downloads" resource-id="android:id/title" bounds="[168,552][714,603]"/>'
APP = f'<node package="{PACKAGE}" text="Import launcher APK"/>'


class Driver(Check):
    def __init__(self, path, frames):
        super().__init__(SimpleNamespace(output=path))
        self.frames = iter(ET.fromstring('<hierarchy>'+x+'</hierarchy>') for x in frames)
        self.commands = []
    def tap(self, label):
        self.control = label
    def dump(self):
        return next(self.frames)
    def adb(self, *args, check=True):
        self.commands.append(args)


class AnrDriver(Check):
    def record(self, name, **details):
        self.proofs.append({'host_fixture':True,'check':name,**details})
    def __init__(self, path, frames, lastanr='', events=''):
        super().__init__(SimpleNamespace(output=path))
        self.lastanr, self.events = lastanr, events
        self.frames = iter(x.encode() for x in frames)
        self.commands = []
    def text(self, *args, check=True):
        return self.lastanr if 'lastanr' in args else self.events
    def adb(self, *args, check=True):
        if args[:2] == ('exec-out', 'cat'):
            return SimpleNamespace(stdout=next(self.frames), stderr=b'', returncode=0)
        if args[:3] == ('shell', 'input', 'tap'):
            self.commands.append(args)
        return SimpleNamespace(stdout=b'', stderr=b'', returncode=0)


class CaptureDriver(Check):
    def __init__(self, path, captures, lastanr='', events='', crashes='', clear_code=0):
        super().__init__(SimpleNamespace(output=path))
        self.captures=iter(captures)
        self.lastanr,self.events,self.crashes=lastanr,events,crashes
        self.clear_code=clear_code
        self.remote=b'<hierarchy><node text="stale"/></hierarchy>'
        self.dump_count=self.read_count=self.clear_count=0
    def text(self, *args, check=True):
        if 'lastanr' in args:return self.lastanr
        if 'events' in args:return self.events
        return self.crashes() if callable(self.crashes) else self.crashes
    def record(self, name, **details):
        self.proofs.append({'host_fixture':True,'check':name,**details})
    def adb(self, *args, check=True):
        if args[:3]==('shell','rm','-f'):
            self.clear_count+=1
            if not self.clear_code:self.remote=None
            return SimpleNamespace(returncode=self.clear_code,stdout=b'',stderr=b'')
        if args[:3]==('shell','uiautomator','dump'):
            self.dump_count+=1
            code,stdout,stderr,payload=next(self.captures)
            if payload is not None:self.remote=payload
            return SimpleNamespace(returncode=code,stdout=stdout,stderr=stderr)
        if args[:2]==('exec-out','cat'):
            self.read_count+=1
            return SimpleNamespace(returncode=int(self.remote is None),stdout=self.remote or b'',stderr=b'')
        raise AssertionError('Unexpected fixture command: '+repr(args))


def capture_controls(path):
    fresh=b'<hierarchy><node text="fresh"/></hierarchy>'
    idle=(1,b'ERROR: could not get idle state.',b'',b'<hierarchy><node text="stale"/></hierarchy>')
    null=(0,b'',b'ERROR: null root node returned by UiTestAutomationBridge.',None)
    good=(0,b'UI hierchary dumped to: /data/local/tmp/combined-ui.xml',b'',fresh)
    count=0
    def driver(name, frames, **kwargs):
        return CaptureDriver(path/name,frames,**kwargs)
    def rejected(value, exception=RuntimeError):
        nonlocal count
        try:value.capture_ui()
        except exception:count+=1;return
        raise AssertionError('Failed capture was admitted')
    with patch('emulator_check.time.sleep'):
        for index,failure in enumerate((idle,null)):
            value=driver('retry-'+str(index),[failure,good]);raw,root=value.capture_ui()
            assert raw==fresh and root.find('node').get('text')=='fresh'
            assert (value.dump_count,value.clear_count,value.read_count)==(2,2,1)
            assert value.proofs[0]['stale_xml_used'] is False
            count+=1
        exhausted=driver('exhausted',[idle]*3);rejected(exhausted)
        assert exhausted.dump_count==3 and exhausted.clear_count==3 and exhausted.read_count==0
        assert len(list(exhausted.args.output.glob('*-dump.stdout')))==3
        for name,stdout,stderr in [('unknown',b'unknown failure',b''),('empty',b'',b''),('permission',b'',b'Permission denied')]:
            value=driver(name,[(1,stdout,stderr,fresh),good]);rejected(value)
            assert value.dump_count==1 and value.read_count==0
            assert (value.args.output/'ui-capture-1-attempt-1-dump.stdout').read_bytes()==stdout
            assert (value.args.output/'ui-capture-1-attempt-1-dump.stderr').read_bytes()==stderr
        for name,kwargs in [('native-anr',{'lastanr':'ANR in '+PACKAGE}),
                            ('native-event',{'events':'am_crash: [0,123,'+PACKAGE+',1]'}),
                            ('native-crash',{'crashes':'Process: '+PACKAGE})]:
            value=driver(name,[idle,good],**kwargs);rejected(value)
            assert value.dump_count==1 and value.read_count==0
        value=driver('late-crash',[idle,good]);value.crashes=lambda:'Process: '+PACKAGE if value.dump_count>1 else ''
        rejected(value);assert value.dump_count==2 and not value.proofs
        value=driver('clear-failure',[good],clear_code=1);rejected(value)
        assert value.dump_count==0 and value.read_count==0
        value=driver('missing-fresh-file',[(0,b'',b'',None)]);rejected(value)
        assert value.read_count==1
        value=driver('malformed-fresh-file',[(0,b'',b'',b'<broken')]);rejected(value,ET.ParseError)
        assert value.dump_count==1
    return count


def viewport_protocol_controls(path):
    """Replay Thor dimensions and reject stale/secret-bearing public reports."""
    count = 0
    preview = {'viewport_policy': {'schema':'coh-native-viewport-v1', 'maximum_controls_percent':60,
        'minimum_aspect':.25, 'maximum_aspect':8, 'maximum_dimension':16384,
        'host_width':1920, 'host_height':469},
        'input_area':{'left':0,'top':611,'width':1920,'height':469,'shown':True,'surface_ready':True},
        'native':{'width':1920,'height':469}, 'preview_is_server_world':False}
    viewport_contract(preview);count+=1
    # The actual failed EGL height must fail even if its outer host is larger.
    def reject(function, value):
        nonlocal count
        try:function(value)
        except AssertionError:count+=1;return
        raise AssertionError('Invalid public report was admitted')
    for mutate in (
        lambda v:v['input_area'].update(height=137),
        lambda v:v['native'].update(height=137),
        lambda v:v['input_area'].update(width=16385),
        lambda v:v['input_area'].update(width=True),
        lambda v:v['input_area'].update(surface_ready=False),
        lambda v:v['viewport_policy'].update(host_height=100),
        lambda v:v.update(preview_is_server_world=True),
    ):
        value=copy.deepcopy(preview);mutate(value);reject(viewport_contract,value)
    fitted=copy.deepcopy(preview);fitted['input_area'].update(width=1096,height=137)
    fitted['native'].update(width=1096,height=137);viewport_contract(fitted);count+=1
    mapping_fields = ('phase stage last_status last_command_valid last_command last_payload_bits last_byte_aligned '
        'accepted_messages rejected_messages malformed unsupported scene_prefixes entity_prefixes disconnects suspends timeouts').split()
    udp_fields = ('state link_state sockets_opened sockets_closed datagrams_sent datagrams_received peer_rejects '
        'truncated empty malformed unsupported send_would_block interrupted io_errors receive_budget_exhausted '
        'suspends resumes cancellations timeouts last_system_error').split()
    link_fields = ('sent received retransmits acknowledged duplicates malformed queue_limits fragment_expirations '
        'timeouts unsupported tx_pending rx_pending fragment_groups storage_bytes codec_bytes high_water_retained_bytes').split()
    top_fields = ('local_development_auth server_identity_bound generation selection_generation db_phase map_phase '
        'last_status attempts character_lists character_choices map_handoffs policy_rejections failures suspends '
        'cancellations opened_sockets closed_sockets terminal_failure terminal_db_phase terminal_map_phase').split()
    protocol = dict.fromkeys(top_fields,0)
    protocol.update(schema='coh-native-local-numeric-v1',phase='SCENE_INCOMPLETE',authserver_authenticated=False,
        live_world_rendered=False,map_protocol=dict.fromkeys(mapping_fields,0))
    protocol['map_protocol']['udp']=dict.fromkeys(udp_fields,0)
    protocol['map_protocol']['udp']['link']=dict.fromkeys(link_fields,0)
    map_report_contract(protocol);count+=1
    for mutate in (
        lambda v:v.update(password='must never appear'),
        lambda v:v['map_protocol'].update(packet_body='must never appear'),
        lambda v:v['map_protocol']['udp']['link'].update(cookie=42),
        lambda v:v.update(terminal_map_phase=-1),
        lambda v:v['map_protocol'].update(last_status=True),
        lambda v:v['map_protocol']['udp'].update(datagrams_received=-1),
        lambda v:v.update(authserver_authenticated=True),
        lambda v:v.update(live_world_rendered=True),
    ):
        value=copy.deepcopy(protocol);mutate(value);reject(map_report_contract,value)
    protocol['map_protocol']['udp']['last_system_error']=-11
    map_report_contract(protocol);count+=1
    class ScrollDriver(Check):
        def __init__(self):
            super().__init__(SimpleNamespace(output=path/'scroll'))
            self.commands=[]
            self.frames=iter([
                '<node text="Native Fixture • level 1" enabled="true" bounds="[0,430][800,510]"/>',
                '<node text="Native Fixture • level 1" enabled="true" bounds="[0,180][800,260]"/>'])
        def dump(self):
            return ET.fromstring('<hierarchy><node package="'+PACKAGE+'" content-desc="Native client controls" bounds="[0,30][1920,400]">'+next(self.frames)+'</node></hierarchy>')
        def adb(self,*args,**kwargs):self.commands.append(args)
    scroll=ScrollDriver()
    with patch('emulator_check.time.sleep'):scroll.tap('Native Fixture',prefix=True)
    assert scroll.commands==[('shell','input','swipe',960,326,960,104,'250'),('shell','input','tap',400,220)]
    count+=1
    return count


def identity_resource_controls():
    count = 0
    identity = {'installed_apk_status':'ready','installed_apk':{'bytes':1000,'sha256':'a'*64}}
    def accepted(v):return installed_apk_contract(v,'a'*64,1000)
    def reject(function, value):
        nonlocal count
        try:function(value)
        except AssertionError:count+=1;return
        raise AssertionError('Invalid APK/resource report was admitted')
    accepted(identity);count+=1
    for state in ('pending','unavailable'):
        value={'installed_apk_status':state,'installed_apk':None}
        installed_apk_contract(value,'a'*64,1000,require_ready=False);count+=1
        reject(accepted,value)
    for change in (
        {'bytes':True,'sha256':'a'*64}, {'bytes':0,'sha256':'a'*64},
        {'bytes':(25<<20)+1,'sha256':'a'*64}, {'bytes':1000,'sha256':'A'*64},
        {'bytes':1000,'sha256':'b'*64}, {'bytes':1000,'sha256':'a'*63},
        {'bytes':1000,'sha256':'a'*64,'path':'must stay private'},
    ):
        reject(accepted,{'installed_apk_status':'ready','installed_apk':change})
    reject(accepted,{'installed_apk_status':'ready','installed_apk':None})
    reject(accepted,{'installed_apk_status':'unknown','installed_apk':None})
    metrics=('rss_kib','peak_rss_kib','children_peak_rss_kib','cgroup_current_bytes','cgroup_max_bytes','cgroup_oom_kill_count')
    row=dict.fromkeys(metrics,None);row.update(stage='server_only_input_admission',boundary='entered',elapsed_ms=0)
    guest_resources_contract({'guest_resources':[]});count+=1
    guest_resources_contract({'guest_resources':[row]*32});count+=1
    populated=copy.deepcopy(row);populated.update(dict.fromkeys(metrics,1<<50))
    guest_resources_contract({'guest_resources':[populated]});count+=1
    reject(guest_resources_contract,{'guest_resources':[row]*33})
    for change in ({'pid':123},{'stage':'/private/path'},{'stage':'x'*121},{'boundary':'unknown'},
                   {'elapsed_ms':-1},{'elapsed_ms':True},{'rss_kib':-1},{'peak_rss_kib':True},
                   {'children_peak_rss_kib':.5},{'cgroup_current_bytes':(1<<50)+1}):
        value=copy.deepcopy(row);value.update(change);reject(guest_resources_contract,{'guest_resources':[value]})
    return count


def activity_controls():
    header='ACTIVITY MANAGER ACTIVITIES (dumpsys activity activities)\n'
    main=PACKAGE+'/.MainActivity';native=PACKAGE+'/.NativeClientActivity'
    live='  * Hist  #0: ActivityRecord{abc123 u0 '+main+' t41}\n'
    resumed='  ResumedActivity: ActivityRecord{abc123 u0 '+main+'} t41}\n'
    historical='  mLastPausedActivity: ActivityRecord{def456 u0 '+native+' t41 f}}\n'
    def parsed(text):return {**activity_inventory(header+text),'pid':1000}
    baseline=parsed(live+resumed)
    assert retained_launcher(baseline,parsed(live+resumed+resumed+historical))
    count=1
    brief=parsed(live.replace('* Hist  ','Hist  ').replace(main,PACKAGE+'/'+PACKAGE+'.MainActivity')+resumed)
    assert retained_launcher(baseline,brief);count+=1
    for changed in (
        live+resumed+' * Hist #1: ActivityRecord{def456 u0 '+native+' t41}\n',
        live+resumed+live.replace('abc123','eeee'),
        (live+resumed).replace('abc123','eeee'),
        live+resumed+live.replace('abc123','eeee').replace('t41','t99'),
        live+resumed.replace('abc123','def456').replace(main,native),
        live,
        live+resumed+' * Fin #0: ActivityRecord{def456 u0 '+native+' t41 f}}\n',
        live+resumed+' Stop #0: ActivityRecord{def456 u0 '+native+' t41}\n',
    ):
        assert not retained_launcher(baseline,parsed(changed));count+=1
    changed=parsed(live+resumed);changed['pid']=1001
    assert not retained_launcher(baseline,changed);count+=1
    for raw in ('', 'Permission denied', live+resumed, header+' * Hist #0: broken '+main,
                header+' * Hist #0: ActivityRecord{abc123 u0 '+main+'}\n'):
        try:activity_inventory(raw)
        except AssertionError:count+=1;continue
        raise AssertionError('Malformed Activity inventory was admitted')
    return count


def main():
    with tempfile.TemporaryDirectory(prefix='coh-driver-controls-') as temp:
        driver = Driver(Path(temp), [BACKGROUND+DRAWER, BACKGROUND, APP])
        driver.select_document('Import launcher APK', FILE)
        assert driver.commands == [('shell','input','tap',441,577), ('shell','input','tap',386,927)], 'Obscured filename was clicked before the foreground drawer root'
        trace = json.loads((Path(temp)/'picker-selection-history.json').read_text())
        assert trace[0]['drawer_open'] is True and trace[0]['selected_file'] is False
        assert trace[1]['selected_file'] is True
        direct = Driver(Path(temp), [BACKGROUND, APP])
        direct.select_document('Import launcher APK', FILE)
        assert direct.commands == [('shell','input','tap',386,927)]
        anr = '<hierarchy><node resource-id="android:id/alertTitle" text="Pixel Launcher isn&amp;apos;t responding"/><node resource-id="android:id/aerr_wait" text="Wait" bounds="[70,1024][1010,1150]"/></hierarchy>'.replace('isn&amp;apos;t', "isn't")
        external = AnrDriver(Path(temp), [anr, '<hierarchy>'+APP+'</hierarchy>'])
        external.dump()
        assert external.commands == [('shell','input','tap',540,1087)] and external.launcher_anrs == 1
        own = AnrDriver(Path(temp), [anr.replace('Pixel Launcher', 'CoH Native Combined')])
        try:
            own.dump()
            raise AssertionError('Native app ANR was admitted')
        except RuntimeError as failure:
            assert 'without dismissal' in str(failure) and not own.commands
        files = AnrDriver(Path(temp), [anr.replace('Pixel Launcher','Files'), '<hierarchy>'+APP+'</hierarchy>'], 'ANR in com.google.android.documentsui (com.google.android.documentsui/.files.FilesActivity)')
        files.dump()
        assert files.commands == [('shell','input','tap',540,1087)] and files.proofs[0]['external_component'] == 'com.google.android.documentsui'
        cpu_only = AnrDriver(Path(temp), [anr.replace('Pixel Launcher','Files'), '<hierarchy>'+APP+'</hierarchy>'], 'ANR in com.android.documentsui\nCPU usage: 1% '+PACKAGE)
        cpu_only.dump()
        assert cpu_only.commands == [('shell','input','tap',540,1087)]
        unknown = AnrDriver(Path(temp), [anr.replace('Pixel Launcher','Files')])
        try:
            unknown.dump()
            raise AssertionError('Unidentified Files ANR was admitted')
        except RuntimeError as failure:
            assert 'not positively identified' in str(failure) and not unknown.commands
        native_trace = AnrDriver(Path(temp), [anr], 'ANR in '+PACKAGE)
        try:
            native_trace.dump()
            raise AssertionError('Native app ANR trace was admitted')
        except RuntimeError as failure:
            assert 'Native app ANR' in str(failure) and not native_trace.commands
        from PIL import Image
        from io import BytesIO
        def png(image):
            out=BytesIO();image.save(out,format='PNG');return out.getvalue()
        area={'left':0,'top':872,'width':1080,'height':985,'shown':True,'surface_ready':True}
        shot=Image.new('RGB',(1080,1920),(0,0,0));shot.paste((255,255,255),(0,0,1080,872))
        proof,_=scene_pixels(png(shot),area)
        assert proof['passed'] is False and proof['bright_pixels']==0, 'White app header admitted a black actual Surface'
        shot.paste((17,19,23),(0,872,1080,1857));proof,_=scene_pixels(png(shot),area)
        assert proof['passed'] is False, 'Uniform GLES clear admitted without scene'
        texture=Image.new('RGB',(128,128));texture.putdata([(40+x,40+y,80) for y in range(128) for x in range(128)]);shot.paste(texture,(100,1000))
        proof,_=scene_pixels(png(shot),area)
        assert proof['passed'] is True and proof['surface_bounds_ltrb']==[0,872,1080,1857]
        native=dict(valid=True,failed=False,running=True,foreground=True,objects_released=False,frames=300,contexts_started=6,contexts_completed=5,gl_errors=0,tf_mismatches=0,world_visible_pixels=1,actor_visible_pixels=1,world_occludes_actor_pixels=1,actor_occludes_world_pixels=1,actor_changed_pixels=1,static_renderer=dict(gpu_bytes=1,tf_mismatches=0,visible_pixels=1))
        ready=dict(assets_verified=True,resumed=True,failure=None,report_write_failed=False,native=native)
        assert settled_preview(ready,290) is True
        native['objects_released']=True;assert settled_preview(ready,290) is False
        native['objects_released']=False;native['static_renderer']['gpu_bytes']=0;assert settled_preview(ready,290) is False
        native['static_renderer']['gpu_bytes']=1;assert settled_preview(ready,310) is False
        capture_checks=capture_controls(Path(temp)/'captures')
        viewport_protocol_checks=viewport_protocol_controls(Path(temp)/'viewport-protocol')
        identity_resource_checks=identity_resource_controls()
        activity_checks=activity_controls()
    print(json.dumps({'passed':True,'checks':17+capture_checks+viewport_protocol_checks+identity_resource_checks+activity_checks,'capture_controls':capture_checks,
        'activity_inventory_controls':activity_checks,
        'identity_resource_controls':identity_resource_checks,
        'viewport_protocol_controls':viewport_protocol_checks,'scope':'Host regressions for document selection, strict fresh capture, native fault rejection, scene/viewport admission, bounded scrolling, exact APK identity and numeric protocol/resource privacy; no Android execution claim.'}))


if __name__ == '__main__':
    main()
