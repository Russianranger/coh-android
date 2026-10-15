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
from emulator_check import Check, PACKAGE

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
    def __init__(self, path, frames):
        super().__init__(SimpleNamespace(output=path))
        self.frames = iter(x.encode() for x in frames)
        self.commands = []
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
    print(json.dumps({'passed':True,'checks':6,'scope':'Host regression for Android 13 accessibility drawer occlusion and actual app-return admission; no Android execution claim.'}))


if __name__ == '__main__':
    main()
