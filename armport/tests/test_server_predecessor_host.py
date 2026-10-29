#!/usr/bin/env python3
"""Real donor admission in fresh host processes without POSIX guest imports."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[2]
RETAINED = 'docs/android-evidence/mapserver-progress-package-36630872719.json'
MODERN = 'docs/android-evidence/client-map-startup-0.13.32-publication.json'


def historical_bytes(relative):
    path = ROOT / relative
    return path.read_bytes() if path.is_file() else subprocess.run(
        ['git', 'show', 'HEAD:' + relative], cwd=ROOT, capture_output=True, check=True).stdout


HOST_CHECK = textwrap.dedent('''\
    import importlib.abc
    import json
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(sys.argv[1]) / 'armport/app'))

    # A clean interpreter prevents cached Linux modules from hiding a Windows
    # import failure. No guest module or dummy fcntl is supplied to this check.
    forbidden = {'fcntl', 'termios', 'resource', 'diagnostic',
        'dbserver_diagnostic', 'game_diagnostic', 'game_device_diagnostic',
        'game_map_progress'}
    for name in forbidden:
        sys.modules.pop(name, None)
    class HostOnlyImports(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split('.')[0] in forbidden:
                raise ModuleNotFoundError('POSIX guest import in host admission: ' + fullname)
    sys.meta_path.insert(0, HostOnlyImports())
    import server_package as package

    raw = Path(sys.argv[2]).read_bytes()
    variant = sys.argv[3]
    game, baseline = package.validate_predecessor(raw, variant)
    expected = game['inputs']['mapserver_progress']['manifest']['build_input'] if variant == 'retained_progress' else game['native_map_startup']['receipt']['build_input']
    assert baseline == expected
    assert not forbidden.intersection(sys.modules)
    # Raw-byte identity stays strict, and a changed executable cannot become a
    # valid historical donor simply by changing its outer JSON representation.
    changed = json.loads(raw)
    changed['files']['MapServer.exe']['sha256'] = '0' * 64
    mutations = [json.dumps(changed).encode()]
    if variant == 'retained_progress':
        mutations += [raw + b' ', json.dumps(game, sort_keys=True).encode()]
    for changed_raw in mutations:
        try:
            package.validate_predecessor(changed_raw, variant)
        except ValueError:
            pass
        else:
            raise AssertionError('Changed donor was admitted')
    print(json.dumps({'variant': variant, 'build_role': baseline['build_role'],
                      'guest_lifecycle_imported': False}))
''')


class HostPredecessorTests(unittest.TestCase):
    def test_real_donors_in_fresh_processes_without_posix_guest_modules(self):
        publication = json.loads(historical_bytes(MODERN))
        cases = {
            'retained_progress': historical_bytes(RETAINED),
            'thor_certified_startup': json.dumps(
                publication['complete_preparation']['native_admission']['game_package']).encode(),
        }
        with tempfile.TemporaryDirectory(prefix='armport-host-predecessor-') as temporary:
            for variant, raw in cases.items():
                with self.subTest(variant=variant):
                    donor = Path(temporary) / (variant + '.json')
                    donor.write_bytes(raw)
                    result = subprocess.run([sys.executable, '-I', '-c', HOST_CHECK,
                        str(ROOT), str(donor), variant], capture_output=True, text=True, timeout=60)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    proof = json.loads(result.stdout)
                    self.assertEqual(proof['variant'], variant)
                    self.assertFalse(proof['guest_lifecycle_imported'])


if __name__ == '__main__':
    unittest.main()
