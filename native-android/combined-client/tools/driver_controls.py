#!/usr/bin/env python3
"""Host regression for the observed Android document-drawer occlusion.

The captured Android 13 accessibility state exposed both the open drawer and a
filename behind it. These controls verify driver event selection only, never
reporting a host simulation as Android execution or a real import.
"""
from pathlib import Path
from types import SimpleNamespace
import json
import tempfile
import xml.etree.ElementTree as ET
from unittest.mock import patch
from emulator_check import Check, PACKAGE, scene_pixels, settled_preview

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
    print(json.dumps({'passed':True,'checks':17+capture_checks,'capture_controls':capture_checks,'scope':'Host regressions for foreground document selection, strict fresh UI capture and bounded known-transient retries, unconditional native fault rejection, and scene admission; no Android execution claim.'}))


if __name__ == '__main__':
    main()
