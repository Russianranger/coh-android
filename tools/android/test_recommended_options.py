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
    'deferZoneLoads': 'deferZoneLoadsEnabled', 'clientGroupBins': 'clientGroupBinsEnabled',
    'keepPreviousZone': 'keepPreviousZoneEnabled', 'missionMaps': 'missionMapsEnabled',
    'unlockAll': 'unlockAllEnabled', 'primalist': 'primalistEnabled'}


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
        self.assertEqual(len(boxes), 28)
        self.assertEqual(sorted(boxes), sorted(ticked + unticked))
        self.assertEqual(sorted(boxes), sorted(GETTERS))
        self.assertEqual(len(set(ticked + unticked)), 28)
        # No option box changes without the line being read again.
        self.assertNotRegex(self.activity, r'->ClientRuntime\.set\w+Enabled\(this,checked\)\);')

    def test_the_lists_are_the_stored_defaults(self):
        stored, table = self.stored_defaults(), self.report_table()
        ticked, unticked = self.screen_lists()
        self.assertEqual(len(table), 28)
        for box, getter in GETTERS.items():
            with self.subTest(box):
                self.assertIn(getter, stored)
                self.assertEqual(table[getter], stored[getter])
                self.assertEqual(box in ticked, stored[getter][1])
                self.assertEqual(box in unticked, not stored[getter][1])
        self.assertEqual((len(ticked), len(unticked)), (19, 9))
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
        # Recommended from 0.13.82, after the Thor test of 0.13.81 (zone ready 10.9 s for 18.0 s).
        self.assertIn('deferZoneLoads', ticked)
        self.assertEqual(stored['deferZoneLoadsEnabled'], ('zone-load-after-ready', True))
        self.assertIn('"COH_DEFER_ZONE_LOADS="+(deferZoneLoadsRequested?"1":"0")', runtime)
        self.assertIn('.put("defer_zone_loads_requested", deferZoneLoadsRequested)', runtime)
        # 0.13.81: the game's own prepared group files (client patch 0133), experimental for the same
        # reason: no CI check looks at the drawn world.
        self.assertIn('clientGroupBins', unticked)
        self.assertEqual(stored['clientGroupBinsEnabled'], ('client-group-bins', False))
        self.assertIn('"COH_CLIENT_GROUP_BINS="+(clientGroupBinsRequested?"1":"0")', runtime)
        self.assertIn('.put("client_group_bins_requested", clientGroupBinsRequested)', runtime)
        # 0.13.82, the owner's option: the zone just left stays loaded; off by default, only with the spare.
        self.assertIn('keepPreviousZone', unticked)
        self.assertEqual(stored['keepPreviousZoneEnabled'], ('keep-previous-zone', False))
        self.assertIn('"COH_KEEP_PREVIOUS_ZONE="+(keepPreviousZoneRequested&&spareZoneRequested?"1":"0")', runtime)
        self.assertIn('.put("keep_previous_zone_requested", keepPreviousZoneRequested)', runtime)
        # 0.13.82: the ARM64 client starts the world at 60 (patch 0128); the app no longer types the cap.
        self.assertIn('if ("arm64".equals(clientArchitectureRequested)) recordLifecycle("gameplay_60fps_auto skipped=client_starts_at_60");', runtime)

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
        # 0.13.83: the boxes are grouped by category; an Experimental one is created last.
        last = activity.index('controls.addView(clientGroupBins);\n        recommendedChanged();')
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


class OptionCategories(unittest.TestCase):
    """0.13.83 (owner, 2026-11-24): "recommended options in their own category, experimental in its own
    (for ones that had no apparent benefit), a test category for ones we are actively testing"; the third
    zone server "in its own category of optional"; "options in a separate tab"."""
    CATEGORIES = (
        ('Recommended', ['performanceGraphics', 'prootFastMode', 'sharedServerData', 'clientSkipServerFolders',
                         'clientFolderIndex', 'clientAudio', 'stockTravel', 'earlyZone', 'spareZone', 'trustedBins',
                         'gameplay60', 'prootIoctlFilter', 'prootSocketFilter', 'prootCasefold', 'serverQuickStart',
                         'wineserverPathCache', 'physxCache', 'serverX87', 'deferZoneLoads']),
        ('Optional', ['keepPreviousZone']),
        ('Test', ['missionMaps', 'unlockAll', 'primalist']),
        ('Experimental', ['prestartNextZone', 'idleResidentMaps', 'sharedHeap', 'glDirect', 'clientGroupBins']))

    @classmethod
    def setUpClass(cls):
        cls.activity = (JAVA / 'ClientActivity.java').read_text()
        start = cls.activity.index('    private void buildOptionsPage(LinearLayout controls){')
        cls.page = cls.activity[start:cls.activity.index('\n    }\n', start)]

    def test_each_box_sits_under_its_category_heading(self):
        marks = [self.page.index('category(controls,"%s",' % name) for name, _ in self.CATEGORIES]
        marks.append(self.page.index('category(controls,"Client and renderer",'))
        self.assertEqual(marks, sorted(marks))
        placed = []
        for index, (name, boxes) in enumerate(self.CATEGORIES):
            section = self.page[marks[index]:marks[index + 1]]
            found = re.findall(r'controls\.addView\((\w+)\);', section)
            self.assertEqual(found, boxes, name)
            placed += found
        self.assertEqual(sorted(placed), sorted(GETTERS))
        # No box is built on another page.
        self.assertNotIn('recommendedChanged();});', self.activity.replace(self.page, ''))

    def test_the_categories_agree_with_the_recommended_lists(self):
        ticked = re.search(r'recommendedTicked\(\)\{return new CheckBox\[\]\{([\w,]+)\};\}', self.activity).group(1).split(',')
        unticked = re.search(r'recommendedUnticked\(\)\{return new CheckBox\[\]\{([\w,]+)\};\}', self.activity).group(1).split(',')
        groups = dict(self.CATEGORIES)
        self.assertEqual(sorted(groups['Recommended']), sorted(ticked))
        self.assertEqual(sorted(groups['Optional'] + groups['Test'] + groups['Experimental']), sorted(unticked))
        # 0.13.84: mission maps are under test (off by default, restored to off like the experiments).
        self.assertEqual(groups['Test'], ['missionMaps', 'unlockAll', 'primalist'])
        self.assertNotIn('Nothing is under test in this version.', self.page)
        # The third zone server (Thor 0.13.82 launch B: lowest free memory 3.5 GB for 4.9 GB) is the owner's choice.
        self.assertEqual(groups['Optional'], ['keepPreviousZone'])
        self.assertIn('private CheckBox[] optionalOptions(){return new CheckBox[]{keepPreviousZone};}', self.activity)
        # Optional is the owner's choice either way: named on the line, never counted as a difference, and
        # left alone by "Restore recommended options".
        self.assertIn('if(optionalOption(box)){chosen.append(chosen.length()==0?" Optional, on: ":"; ").append(optionName(box));continue;}',
                      self.activity)
        self.assertIn('if(box!=null&&box.isChecked()&&!optionalOption(box))box.setChecked(false);', self.activity)
        # The options are on their own tab now, so a difference is also shown above the tabs.
        self.assertIn('optionsNotice.setVisibility(count==0?View.GONE:View.VISIBLE);', self.activity)
        self.assertLess(self.activity.index('optionsNotice=text("",12,true);'),
                        self.activity.index('LinearLayout tabRow=new LinearLayout(this);'))

    def test_three_tabs_with_the_commands_first(self):
        activity = self.activity
        self.assertIn('String[] tabNames={"Play","Options","Setup"};', activity)
        self.assertIn('buildPlayPage(menuPages[0]);buildOptionsPage(menuPages[1]);buildSetupPage(menuPages[2]);', activity)
        self.assertIn('selectTab(controlsPreferences.getInt(CONTROLS_PREFIX+"tab",0));', activity)
        # What is happening stays above the tabs.
        self.assertLess(activity.index('status=text("Connecting",17,true);controls.addView(status);'),
                        activity.index('LinearLayout tabRow=new LinearLayout(this);'))
        start = activity.index('    private void buildPlayPage(LinearLayout controls){')
        play = activity[start:activity.index('\n    }\n', start)]
        order = ['resumeGame=button(', 'run=button("Reopen saved character"', 'typeText=button(', 'enterKey=button(',
                 'showFps=button(', 'saveLogout=button(', 'finish=button(', 'export=button(', 'returnGround=button(',
                 'stop=button(']
        places = [play.index(item) for item in order]
        self.assertEqual(places, sorted(places))
        self.assertNotIn('CheckBox', play)
        start = activity.index('    private void buildSetupPage(LinearLayout controls){')
        setup = activity[start:activity.index('\n    }\n', start)]
        for item in ('setup=button(', 'importAssets=button(', 'button("Controller mappings"', 'recoverReports=button(',
                     'storage=button(', 'startTest=button(', 'captureContact=button(', 'logs=text('):
            self.assertEqual(setup.count(item), 1, item)
        # Only the chosen page is shown, and the choice is remembered.
        select = activity[activity.index('    private void selectTab(int index){'):]
        select = select[:select.index('\n    }\n')]
        self.assertIn('menuPages[i].setVisibility(i==index?View.VISIBLE:View.GONE);', select)
        self.assertIn('controlsPreferences.edit().putInt(CONTROLS_PREFIX+"tab",index).apply();', select)


if __name__ == '__main__':
    unittest.main()
