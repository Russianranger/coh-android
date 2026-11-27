"""The APK builder's reviewed runtime lists cover every helper staging adds or changes.

0.13.54's first APK run failed after a full CI chain because a new guest helper
(external_map_supervisor.py) and a changed one (native_training_save.py) were
missing from build_thor_apk's lists. This repeats that check against pinned
donor contents so the gap shows up before CI.
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'armport/app'))

import build_thor_apk  # noqa: E402
import stage_app_assets  # noqa: E402

FIXTURE = ROOT / 'armport/tests/fixtures/donor-0.13.36-runtime-pins.json'
# stage() binds this helper to the donor's own world inventory.
BOUND = frozenset({'atlas_world_assets.py'})
APP_HELPERS = ('armport_client_package.py', 'armport_interactive.py', 'client_stdio.py', 'server_metrics.py')


def staged_helpers(donor):
    """(added, changed) helper names, mirroring stage_app_assets.stage replacements."""
    sources = {name: ROOT / 'armport/app' / name for name in APP_HELPERS}
    sources['character_creation_diagnostic.py'] = ROOT / 'android/guest/character_creation_diagnostic.py'
    for name in set(donor['client_files']) | set(stage_app_assets.GUEST_DEPENDENCIES):
        path = ROOT / 'android/guest' / name
        if name.endswith('.py') and path.is_file():
            sources[name] = path
    added, changed = set(), set()
    packaged = donor['packaged_runtime_sha256']
    for name, path in sources.items():
        if name in BOUND:
            continue
        if name not in packaged:
            added.add(name)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != packaged[name]:
            changed.add(name)
    return added, changed


class ThorApkRuntimeReview(unittest.TestCase):
    def setUp(self):
        self.donor = json.loads(FIXTURE.read_text())
        self.assertEqual(self.donor['donor_apk_sha256'], build_thor_apk.DONOR_APK['sha256'])

    def test_added_helpers_are_reviewed(self):
        added, _ = staged_helpers(self.donor)
        self.assertEqual(sorted(added - build_thor_apk.ADDED_RUNTIME), [])

    def test_changed_helpers_are_reviewed(self):
        _, changed = staged_helpers(self.donor)
        self.assertEqual(sorted(changed - build_thor_apk.CHANGED_RUNTIME), [])

    def test_reviewed_additions_are_not_donor_payloads(self):
        packaged = set(self.donor['packaged_runtime_sha256'])
        self.assertEqual(sorted(build_thor_apk.ADDED_RUNTIME & packaged), [])
        self.assertEqual(sorted(build_thor_apk.SERVER_OPTION_ADDED_RUNTIME & packaged), [])


if __name__ == '__main__':
    unittest.main()
