"""0.13.76: the app says which launch options are not at their recommended setting.

Thor 0.13.75 (exports 20261120-004204 .. -013715): all four launches ran with "Do not monitor
ordinary socket traffic" unticked, left so by launch C of the 0.13.73 test. The recommended set
is what a new install has, so the three places that state it must agree: each option's stored
default (ClientRuntime), the list the report field is built from (ClientRuntime), and the two
lists of tick boxes the options screen compares (ClientActivity).
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'

# Tick box field -> its ClientRuntime getter.
GETTERS = {
    'performanceGraphics': 'performanceGraphicsEnabled', 'prootFastMode': 'prootFastModeEnabled',
    'sharedServerData': 'sharedServerDataEnabled', 'clientSkipServerFolders': 'clientSkipServerFoldersEnabled',
    'clientFolderIndex': 'clientFolderIndexEnabled', 'clientAudio': 'clientAudioEnabled',
    'stockTravel': 'stockTravelEnabled', 'earlyZone': 'earlyZoneEnabled', 'trustedBins': 'trustedBinsEnabled',
    'gameplay60': 'gameplay60FpsEnabled', 'prootIoctlFilter': 'prootIoctlFilterEnabled',
    'prootSocketFilter': 'prootSocketFilterEnabled', 'prootCasefold': 'prootCasefoldEnabled',
    'serverQuickStart': 'serverQuickStartEnabled', 'wineserverPathCache': 'wineserverPathCacheEnabled',
    'physxCache': 'physxCacheEnabled', 'prestartNextZone': 'prestartNextZoneEnabled',
    'idleResidentMaps': 'idleResidentMapsEnabled', 'spareZone': 'spareZoneEnabled',
    'sharedHeap': 'sharedHeapEnabled', 'glDirect': 'glDirectEnabled', 'serverX87': 'serverX87Enabled',
    'deferZoneLoads': 'deferZoneLoadsEnabled'}


class RecommendedOptions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = (JAVA / 'ClientRuntime.java').read_text()
        cls.activity = (JAVA / 'ClientActivity.java').read_text()

    def stored_defaults(self):
        """getter name -> (preference key, default), read from each getter's own body."""
        found = {}
        for match in re.finditer(r'public static boolean (\w+Enabled)\(Context context\) \{\s*'
                                 r'return context\.getSharedPreferences\("client-launch-options", Context\.MODE_PRIVATE\)\s*'
                                 r'\.getBoolean\("([a-z0-9-]+)", (true|false)\);', self.runtime):
            found[match.group(1)] = (match.group(2), match.group(3) == 'true')
        return found

    def report_table(self):
        body = self.runtime[self.runtime.index('public static String optionsOffRecommended(Context context) {'):]
        body = body[:body.index('return off.toString();')]
        return {getter: (key, value == 'true') for key, getter, value in
                re.findall(r'\{"([a-z0-9-]+)",(\w+Enabled)\(context\),(true|false)\}', body)}

    def screen_lists(self):
        ticked = re.search(r'private CheckBox\[\] recommendedTicked\(\)\{return new CheckBox\[\]\{([\w,]+)\};\}', self.activity)
        unticked = re.search(r'private CheckBox\[\] recommendedUnticked\(\)\{return new CheckBox\[\]\{([\w,]+)\};\}', self.activity)
        return ticked.group(1).split(','), unticked.group(1).split(',')

    def test_every_option_box_is_in_exactly_one_list(self):
        boxes = re.findall(r'(\w+)\.setOnCheckedChangeListener\(\(button,checked\)->\{ClientRuntime\.set\w+Enabled\(this,checked\);'
                           r'recommendedChanged\(\);\}\);', self.activity)
        ticked, unticked = self.screen_lists()
        self.assertEqual(len(boxes), 23)
        self.assertEqual(sorted(boxes), sorted(ticked + unticked))
        self.assertEqual(sorted(boxes), sorted(GETTERS))
        self.assertEqual(len(set(ticked + unticked)), 23)
        # No option box changes without the line being read again.
        self.assertNotRegex(self.activity, r'->ClientRuntime\.set\w+Enabled\(this,checked\)\);')

    def test_the_lists_are_the_stored_defaults(self):
        stored, table = self.stored_defaults(), self.report_table()
        ticked, unticked = self.screen_lists()
        self.assertEqual(len(table), 23)
        for box, getter in GETTERS.items():
            with self.subTest(box):
                self.assertIn(getter, stored)
                self.assertEqual(table[getter], stored[getter])
                self.assertEqual(box in ticked, stored[getter][1])
                self.assertEqual(box in unticked, not stored[getter][1])
        self.assertEqual((len(ticked), len(unticked)), (18, 5))
        # 0.13.79: the spare zone server is recommended (owner's policy, the current zone and one
        # spare; Thor 0.13.78 launch B: trips 33.9 s and 27.7 s against 65.8 s, 60 FPS).
        self.assertIn('spareZone', ticked)
        self.assertEqual(stored['spareZoneEnabled'], ('spare-zone-server', True))
        # 0.13.79: 64-bit x87 arithmetic in the zone servers (CI 44882642501: group load 7.2 s for 8.3 s).
        self.assertIn('serverX87', ticked)
        self.assertEqual(stored['serverX87Enabled'], ('server-x87-64bit', True))
        runtime = (ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java').read_text()
        self.assertIn('"COH_SERVER_EMULATION="+(serverX87Requested?"x87":"")', runtime)
        self.assertNotIn('tso', re.findall(r'"COH_SERVER_EMULATION="[^,]*', runtime)[0])
        # 0.13.81: finishing a zone load after the server is ready is experimental: stored off, and
        # "Restore recommended options" unticks it. NPC and pet movement has no CI check.
        self.assertIn('deferZoneLoads', unticked)
        self.assertEqual(stored['deferZoneLoadsEnabled'], ('zone-load-after-ready', False))
        self.assertIn('"COH_DEFER_ZONE_LOADS="+(deferZoneLoadsRequested?"1":"0")', runtime)
        self.assertIn('.put("defer_zone_loads_requested", deferZoneLoadsRequested)', runtime)

    def test_the_report_carries_the_launch_time_reading(self):
        self.assertIn('optionsOffRecommended=optionsOffRecommended(context);', self.runtime)
        self.assertIn('.put("options_off_recommended", optionsOffRecommended)', self.runtime)
        # The socket option is among them: the one the Thor test ran without.
        self.assertEqual(self.report_table()['prootSocketFilterEnabled'], ('proot-socket-filter', True))

    def test_the_screen_shows_the_line_above_the_first_option_and_reads_it_after_the_last(self):
        activity = self.activity
        line = activity.index('recommendedStatus=text("Checking options…",12,true);controls.addView(recommendedStatus);')
        button = activity.index('controls.addView(button("Restore recommended options",this::restoreRecommendedOptions));')
        first = activity.index('performanceGraphics=new CheckBox(this);')
        last = activity.index('controls.addView(deferZoneLoads);\n        recommendedChanged();')
        self.assertLess(line, button)
        self.assertLess(button, first)
        self.assertLess(first, last)
        # Every box of both lists exists by then (physxCache is created last).
        ticked, unticked = self.screen_lists()
        for box in ticked + unticked:
            self.assertLess(activity.index(box + '=new CheckBox(this);'), last, box)
        # Restoring goes through each box's own listener (which stores it), and not during an operation.
        restore = activity[activity.index('private void restoreRecommendedOptions(){'):]
        restore = restore[:restore.index('\n    }\n')]
        self.assertIn('if(ClientRuntime.operationInProgress()){', restore)
        self.assertIn('box.setChecked(true);', restore)
        self.assertIn('box.setChecked(false);', restore)


if __name__ == '__main__':
    unittest.main()
