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
            return SimpleNamespace(stdout=next(self.frames))
        if args[:3] == ('shell', 'input', 'tap'):
            self.commands.append(args)
        return SimpleNamespace(stdout=b'')


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
    print(json.dumps({'passed':True,'checks':17,'scope':'Host regression for Android 13 accessibility drawer occlusion and actual app-return admission; no Android execution claim.'}))


if __name__ == '__main__':
    main()
