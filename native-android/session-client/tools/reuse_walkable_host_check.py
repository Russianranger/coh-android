#!/usr/bin/env python3
"""Check the real reuse guard with independent Git/ZIP mutation controls."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import warnings
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    path = Path(__file__).with_name('reuse_walkable_package.py')
    spec = importlib.util.spec_from_file_location('shipped_walkable_reuse', path)
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    checks = 0
    def check(value, label):
        nonlocal checks
        checks += 1
        if not value:
            raise AssertionError(label)
    with tempfile.TemporaryDirectory(prefix='coh-walkable-reuse-') as folder:
        root = Path(folder)
        def git(*arguments):
            return subprocess.run(['git', *arguments], cwd=root, capture_output=True,
                                  check=True, timeout=30).stdout.decode().strip()
        def write(name, content='independent text fixture\n'):
            file = root / name; file.parent.mkdir(parents=True, exist_ok=True); file.write_text(content)
        def commit():
            git('add', '-A'); git('-c', 'user.name=Guard fixture', '-c', 'user.email=guard@example.invalid',
                                 'commit', '--allow-empty', '-qm', 'Independent guard mutation')
            return git('rev-parse', 'HEAD')
        def reset():
            git('reset', '--hard', base); git('clean', '-fdq')
        git('init', '-q', '-b', 'native-android')
        runtime = 'native-android/session-client/app/src/main/cpp/session_renderer.c'
        write(runtime); write('README.md'); base = commit()
        check(helper.guard(root, base, base)['eligible'], 'Identical committed native branch is eligible')
        allow = list(helper.ALLOWED_FILES) + ['native-android/PHASES19-21.md',
                 'native-android/session-client/THOR-TEST.md', 'native-android/evidence/phases19-21/report.json']
        for name in allow:
            reset(); write(name); head = commit()
            check(helper.guard(root, base, head)['eligible'], 'Approved committed change: ' + name)
        reject = [runtime, 'native-android/session-client/app/build.gradle',
                  'native-android/session-client/app/src/main/AndroidManifest.xml',
                  'native-android/session-client/app/src/main/assets/note.md',
                  'native-android/session-client/app/test-signing/session-test.p12',
                  'native-android/systems-probe/app/src/main/java/org/coh/systemsprobe/InputAdapter.java',
                  'native-android/world-probe/shaders/world.vert', 'native-android/walk/source_world.c',
                  'native-android/tools/directional_fixture/prepare.py',
                  'native-android/session-client/tools/lifecycle_host_check.py',
                  'native-android/evidence/phases19-21-other/runtime.c']
        for name in reject:
            reset(); write(name, 'Actual runtime or unapproved dependency mutation\n'); head = commit()
            check(not helper.guard(root, base, head)['eligible'], 'Reject actual committed change: ' + name)
        reset(); write(runtime, 'Uncommitted runtime change\n')
        check(not helper.guard(root, base, base)['eligible'], 'Reject uncommitted tracked runtime change')
        reset(); write('native-android/session-client/app/src/main/java/NewActivity.java')
        check(not helper.guard(root, base, base)['eligible'], 'Reject untracked application source')
        reset(); (root / 'README.md').unlink(); (root / 'README.md').symlink_to(runtime); head = commit()
        check(not helper.guard(root, base, head)['eligible'], 'Reject allowed-path symlink mode')
        reset(); git('update-index', '--add', '--cacheinfo', '160000,' + base + ',native-android/evidence/phases19-21/submodule')
        git('-c', 'user.name=Guard fixture', '-c', 'user.email=guard@example.invalid', 'commit', '-qm', 'Gitlink mutation')
        head = git('rev-parse', 'HEAD')
        check(not helper.guard(root, base, head)['eligible'], 'Reject evidence gitlink')
        check(not helper.guard(root, head, base)['eligible'], 'Reject non-current/non-ancestor head')
        check(not helper.guard(root, base, 'HEAD')['eligible'], 'Reject symbolic head')
        check(not helper.guard(root, '0'*40, head)['eligible'], 'Reject unavailable base')
        reset(); git('checkout', '-qb', 'main')
        check(not helper.guard(root, base, base)['eligible'], 'Reject main branch')
        git('checkout', '-q', '--detach', base)
        check(not helper.guard(root, base, base)['eligible'], 'Detached checkout requires explicit CI branch provenance')
        check(helper.guard(root, base, base, 'refs/heads/native-android')['eligible'], 'Correct explicit native CI ref allowed')
        check(not helper.guard(root, base, base, 'refs/heads/main')['eligible'], 'Reject wrong explicit CI ref')
    def zip_case(entries, passed, label):
        stream = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(stream, 'w') as bundle:
                for name, mode in entries:
                    item = zipfile.ZipInfo(name); item.external_attr = mode << 16
                    bundle.writestr(item, b'independent archive fixture')
        try:
            with zipfile.ZipFile(io.BytesIO(stream.getvalue())) as bundle:
                helper.archive_entries(bundle)
            actual = True
        except ValueError:
            actual = False
        check(actual == passed, label)
    zip_case([('proof.json', stat.S_IFREG | 0o644)], True, 'Regular archive positive control')
    zip_case([('../proof.json', stat.S_IFREG | 0o644)], False, 'Reject parent traversal')
    zip_case([('/proof.json', stat.S_IFREG | 0o644)], False, 'Reject absolute path')
    zip_case([('C:/proof.json', stat.S_IFREG | 0o644)], False, 'Reject drive path')
    zip_case([('nested\\proof.json', stat.S_IFREG | 0o644)], False, 'Reject backslash path')
    zip_case([('proof.json', stat.S_IFLNK | 0o777)], False, 'Reject ZIP symlink')
    zip_case([('proof.json', stat.S_IFREG | 0o644)]*2, False, 'Reject duplicate ZIP member')
    receipt = {'schema': 1, 'passed': True, 'checks': checks,
               'guard_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
               'scope': 'Actual shipped guard over independent Git histories and unsafe ZIP mutation controls; no Android execution or device acceptance'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
