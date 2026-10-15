#!/usr/bin/env python3
"""Qualify the Java importer with the exact APK data and reviewed asset ZIP.

This runs on a hosted JVM. It checks data assembly independently against the
previously accepted full game-data inventory; it is not Android UI/device proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/android/atlas'))
import package_game_import as package

game = package.game
ACCEPTED_DATA_MANIFEST_SHA256 = 'b367cc35d3f3826d9988ffa5dadb0a240ffc0967f0d248586e54d8ac545615f4'


def extract_apk_data(apk, output):
    output.mkdir()
    limits = {package.PROPERTIES: 65536, package.TEXT_ARCHIVE: game.MAX_BYTES,
              package.TEXT_INDEX: game.MAX_MANIFEST, package.ASSET_INDEX: game.MAX_MANIFEST}
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        game.require(len(names) == len(set(names)), 'Duplicate APK member')
        expected = {'assets/atlas/' + name for name in package.PACKAGE_FILES}
        game.require({name for name in names if name.startswith('assets/')} == expected,
                     'Unexpected APK asset set')
        for name in sorted(package.PACKAGE_FILES):
            entry = archive.getinfo('assets/atlas/' + name)
            game.require(0 < entry.file_size <= limits[name] and not entry.is_dir(),
                         'Oversized or non-file APK payload')
            count = 0
            with archive.open(entry) as source, (output / name).open('xb') as target:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    count += len(block)
                    game.require(count <= entry.file_size, 'APK payload exceeds declared size')
                    target.write(block)
            game.require(count == entry.file_size, 'Truncated APK payload')


def read_properties(path):
    values = {}
    for line in path.read_text(encoding='ascii').splitlines():
        if not line or line.startswith('#'):
            continue
        key, value = line.split('=', 1)
        game.require(key not in values, 'Duplicate host summary property')
        values[key] = value
    return values


def qualify(apk, archive, output, commit):
    apk, archive, output = Path(apk).resolve(), Path(archive).resolve(), Path(output).resolve()
    game.require(not output.exists(), 'Host proof destination must be new')
    output.mkdir(parents=True)
    started = time.monotonic()
    report = {'format': 1, 'status': 'running', 'repository_commit': commit,
              'scope': 'hosted_JVM_import_of_exact_APK_assets_and_reviewed_archive',
              'android_execution_validated': False, 'gameplay_validated': False}
    report_file = output / 'host-import-report.json'
    try:
        game.require(archive.is_file() and not archive.is_symlink()
                     and archive.stat().st_size == game.ASSET_ARCHIVE_BYTES
                     and package.digest(archive) == game.ASSET_ARCHIVE_SHA256,
                     'Selected archive differs from the reviewed input')
        report['apk'] = {'bytes': apk.stat().st_size, 'sha256': package.digest(apk)}
        assets = output / 'apk-assets'
        extract_apk_data(apk, assets)
        contract = package.verify_package(assets, commit, verify_archive=False)
        report['apk_payloads'] = {name: {'bytes': (assets / name).stat().st_size,
                                        'sha256': package.digest(assets / name)}
                                  for name in sorted(package.PACKAGE_FILES)}
        classes = output / 'classes'
        classes.mkdir()
        core = ROOT / 'android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java'
        host = ROOT / 'tools/android/atlas/java/io/github/russianranger/cohatlas/HostImport.java'
        report['java_source_sha256'] = {str(path.relative_to(ROOT)): package.digest(path)
                                        for path in (core, host)}
        with (output / 'host-import.log').open('w', encoding='utf-8') as log:
            subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                            '-d', str(classes), str(core), str(host)], cwd=ROOT, check=True,
                           stdout=log, stderr=subprocess.STDOUT, timeout=120)
            subprocess.run(['java', '-Xmx512m', '-cp', str(classes),
                            'io.github.russianranger.cohatlas.HostImport', str(assets), str(archive),
                            str(output / 'installed'), str(output / 'import-summary.properties')],
                           cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
        summary = read_properties(output / 'import-summary.properties')
        game.require(summary.get('status') == 'passed' and summary.get('repository.commit') == commit
                     and summary.get('source.commit') == game.SOURCE
                     and summary.get('data.commit') == game.DATA
                     and summary.get('count') == str(game.DATA_COUNT)
                     and summary.get('bytes') == str(game.DATA_BYTES), 'Java import summary differs')
        data = Path(summary['data.directory']).resolve()
        game.require(data.name == 'data' and (output / 'installed') in data.parents,
                     'Java data destination is outside the private installation')
        _, records = package.pinned_assets(ROOT)
        expected = game.expected_data(ROOT, records)
        files, total = game.checked_inventory(data.parent, expected)
        document = {'format': 1, 'scope': 'reviewed_game_data',
                    'source_commit': game.SOURCE, 'data_commit': game.DATA,
                    'files': files, 'file_count': len(files), 'total_bytes': total,
                    'asset_manifest_sha256': game.ASSET_MANIFEST_SHA256,
                    'asset_archive_sha256': game.ASSET_ARCHIVE_SHA256,
                    'android_execution_validated': False, 'gameplay_validated': False}
        inventory_hash = hashlib.sha256(game.assets.canonical(document)).hexdigest()
        game.require(inventory_hash == ACCEPTED_DATA_MANIFEST_SHA256,
                     'Imported full-data inventory differs from accepted Atlas input')
        report.update(status='passed', file_count=len(files), total_bytes=total,
                      accepted_game_data_manifest_sha256=inventory_hash,
                      imported_files_independently_rehashed=True,
                      exact_APK_payloads_verified=True,
                      recovery_and_previous_generation_preservation=summary.get('recovery') == 'passed',
                      interrupted_reimport_preserves_current=summary.get('cancel') == 'passed',
                      asset_archive={'bytes': game.ASSET_ARCHIVE_BYTES,
                                     'sha256': game.ASSET_ARCHIVE_SHA256},
                      text_archive={'bytes': contract['text.archive.bytes'],
                                    'sha256': contract['text.archive.sha256']})
        game.require(report['recovery_and_previous_generation_preservation']
                     and report['interrupted_reimport_preserves_current'],
                     'Host cancellation/recovery checks did not pass')
    except Exception as failure:
        report.update(status='failed', failure_type=type(failure).__name__,
                      failure=str(failure))
        raise
    finally:
        report['elapsed_seconds'] = round(time.monotonic() - started, 6)
        report_file.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apk', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--repository-commit', required=True)
    args = parser.parse_args()
    qualify(args.apk, args.archive, args.output, args.repository_commit)


if __name__ == '__main__':
    main()
