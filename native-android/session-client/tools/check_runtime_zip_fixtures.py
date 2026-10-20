#!/usr/bin/env python3
"""Python-only checks for reproducible, honestly labeled runtime ZIP fixtures."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
import prepare_runtime_zip_fixtures as fixture


def check(cache):
    controls = 0
    with tempfile.TemporaryDirectory(prefix='coh-zip-format-check-') as temporary:
        root = Path(temporary)
        first = fixture.prepare(cache, root / 'first')
        second = fixture.prepare(cache, root / 'second')
        assert first == second
        assert not first['original_archive_sha256_verified'] and first['network_requests'] == 0
        controls += 3
        for entry in first['archives']:
            assert entry['origin'].startswith('generated_zip_format_fixture_')
            one, two = root / 'first' / entry['file'], root / 'second' / entry['file']
            assert one.read_bytes() == two.read_bytes()
            assert hashlib.sha256(one.read_bytes()).hexdigest() == entry['ranges'][0]['sha256']
            controls += 3
            with zipfile.ZipFile(one) as archive:
                assert archive.testzip() is None and set(archive.namelist()) == set(entry['members'])
                controls += 1
                for name, pin in entry['members'].items():
                    raw = archive.read(name)
                    assert len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256']
                    controls += 1
        bad = root / 'bad'
        bad.mkdir()
        for _, alias, _, _, _ in fixture.source_inputs():
            shutil.copyfile(Path(cache) / alias, bad / alias)
        for mode in ('corrupt', 'missing', 'symlink'):
            selected = bad / fixture.source_inputs()[0][1]
            if selected.exists() or selected.is_symlink():
                selected.unlink()
            if mode == 'corrupt':
                raw = bytearray((Path(cache) / selected.name).read_bytes())
                raw[-1] ^= 1
                selected.write_bytes(raw)
            elif mode == 'symlink':
                selected.symlink_to((Path(cache) / selected.name).resolve())
            output = root / mode
            try:
                fixture.prepare(bad, output)
                raise AssertionError('Invalid input accepted: ' + mode)
            except ValueError:
                assert not output.exists()
                controls += 1
        try:
            fixture.prepare(cache, root / 'first')
            raise AssertionError('Existing output overwritten')
        except ValueError:
            assert fixture.prepare(cache, root / 'third') == first
            controls += 1
    return {'passed': True, 'controls': controls, 'scope': fixture.SCOPE, 'network_requests': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(check(args.cache)))


if __name__ == '__main__':
    main()
