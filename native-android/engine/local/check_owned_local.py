#!/usr/bin/env python3
"""Execute integrated local-owner checks from frozen project source, never PYC."""
import argparse
import hashlib
import importlib.abc
import importlib.util
import json
import os
from pathlib import Path
import py_compile
import subprocess
import sys
import tempfile
import types


def execute_frozen(name, path, frozen, verify):
    path = Path(path).resolve()
    if path.suffix != '.py' or path not in frozen:
        raise ValueError('Python project source not admitted: ' + str(path))
    verify()
    module = types.ModuleType(name)
    module.__file__ = str(path)
    module.__cached__ = None
    exec(compile(frozen[path], str(path), 'exec', dont_inherit=True), module.__dict__)
    verify()
    return module


def controls():
    checks = 0
    with tempfile.TemporaryDirectory(prefix='coh-local-source-controls-') as td:
        path = Path(td) / 'helper.py'
        path.write_text('value=9\n')
        py_compile.compile(str(path), doraise=True)
        stamp = path.stat()
        path.write_text('value=1\n')
        os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
        frozen = {path.resolve(): path.read_bytes()}
        def verify():
            if path.read_bytes() != frozen[path.resolve()]:
                raise ValueError('source changed')
        old = importlib.util.spec_from_file_location('old', path)
        module = importlib.util.module_from_spec(old)
        old.loader.exec_module(module)
        assert module.value == 9
        checks += 1
        assert execute_frozen('fresh', path, frozen, verify).value == 1
        checks += 1
        for refused in (path.with_suffix('.pyc'), path.parent / 'missing.py'):
            try:
                execute_frozen('refused', refused, frozen, verify)
            except ValueError:
                checks += 1
            else:
                raise AssertionError('unadmitted helper accepted')
        path.write_text('value=2\n')
        try:
            execute_frozen('changed', path, frozen, verify)
        except ValueError:
            checks += 1
        else:
            raise AssertionError('changed helper accepted')
    return checks


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--sanitize', action='store_true')
    ap.add_argument('--ndk', type=Path)
    ap.add_argument('--android-output', type=Path)
    ap.add_argument('--controls-only', action='store_true')
    a = ap.parse_args()
    if a.output.exists():
        ap.error('fresh output required')
    source_controls = controls()
    root = a.source_root.resolve()
    native = root / 'native-android'
    # No project code is imported until every tracked native helper and native
    # compilation input has been frozen, together with the original local pins.
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).split(b'\0')
    files = [root / os.fsdecode(p) for p in tracked if p and
             os.fsdecode(p).startswith('native-android/') and
             Path(os.fsdecode(p)).suffix in ('.py', '.c', '.h', '.inc')]
    files.extend([Path(__file__).resolve(), native / 'engine/local/check.py'])
    for relative in ('local/source-pins.json', 'dbclient/source-pins.json',
                     'mapclient/source-pins.json', 'replication/source-pins.json',
                     'replication/groups-source-pins.json'):
        manifest = native / 'engine' / relative
        files.append(manifest)
        for name in json.loads(manifest.read_bytes())['sha256_lf']:
            files.append(root / name if name.startswith(('upstream/', 'android/'))
                         else root / 'upstream/ouroboros' / name)

    frozen = {p.resolve(): p.read_bytes() for p in files}
    def verify():
        for path, raw in frozen.items():
            if path.read_bytes() != raw:
                raise ValueError('project input changed: ' + str(path))
    verify()
    identity_module = execute_frozen('checked_source_identity', native / 'engine/local/run_owned_android.py', frozen, verify)
    identity = identity_module.source_identity(root)
    if identity['source_sha256'] != {str(p.relative_to(root)): hashlib.sha256(b).hexdigest() for p, b in frozen.items()}:
        raise ValueError('frozen helper domain differs from current Git source domain')
    loaded = ['native-android/engine/local/run_owned_android.py']
    original = importlib.util.spec_from_file_location
    class FrozenLoader(importlib.abc.Loader):
        def __init__(self, path):
            self.path = Path(path).resolve()
        def create_module(self, spec):
            return None
        def exec_module(self, module):
            admitted = execute_frozen(module.__name__, self.path, frozen, verify)
            module.__dict__.update(admitted.__dict__)
            loaded.append(str(self.path.relative_to(root)))
    def spec(name, location, *args, **kwargs):
        path = Path(location).resolve()
        if path.is_relative_to(root):
            if path not in frozen or path.suffix != '.py':
                raise ValueError('unadmitted project import: ' + str(path))
            return original(name, str(path), loader=FrozenLoader(path))
        return original(name, location, *args, **kwargs)
    proof = {'passed': True, 'source_loader_controls': source_controls,
             'project_helpers_frozen_before_first_import': True,
             'cached_project_bytecode_used': False, 'controls_only': a.controls_only}
    if not a.controls_only:
        importlib.util.spec_from_file_location = spec
        try:
            module = execute_frozen('checked_local_qualification', native / 'engine/local/check.py', frozen, verify)
            with tempfile.TemporaryDirectory(prefix='coh-owned-local-proof-') as td:
                old_argv = sys.argv
                sys.argv = ['check.py', '--source-root', str(root), '--output', str(Path(td) / 'host.json')]
                if a.sanitize:
                    sys.argv.append('--sanitize')
                if a.ndk:
                    sys.argv.extend(['--ndk', str(a.ndk)])
                if a.android_output:
                    sys.argv.extend(['--android-output', str(a.android_output)])
                try:
                    module.main()
                finally:
                    sys.argv = old_argv
                proof['integrated'] = json.loads((Path(td) / 'host.json').read_bytes())
        finally:
            importlib.util.spec_from_file_location = original
    verify()
    if subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD']).decode().strip() != identity['source_revision']:
        raise ValueError('Git revision changed during qualification')
    proof.update(identity)
    proof['checked_helpers'] = loaded
    proof['source_sha256'] = {str(p.relative_to(root)): hashlib.sha256(b).hexdigest() for p, b in frozen.items()}
    proof.update(real_server=False, encrypted_authentication=False,
                 actor_identity=False, world_authority=False, android_executed=False)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'passed': True, 'source_loader_controls': source_controls,
                      'project_inputs': len(frozen), 'checked_helpers': len(loaded)}))


if __name__ == '__main__':
    main()
