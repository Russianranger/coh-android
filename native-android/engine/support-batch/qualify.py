#!/usr/bin/env python3
"""Opt-in, offline six-module qualification (at most two concurrent checkers).

No downloads, network/auth/session tests, existing workflow edits or APK writes.
Missing authentic inputs fail the relevant workstream; other work continues.
Pass --help for explicit corpus overrides. Android compilation is not execution.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NATIVE = ROOT / 'native-android'
ACCEPTED_APK_SHA = '75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639'
PROTECTED = ['native-android/session-client', 'native-android/walk', 'native-android/motion',
             'native-android/locomotion', 'native-android/character', 'native-android/animation',
             'native-android/engine/ui/coh_ui.c', 'native-android/engine/ui/coh_ui.h']
SCOPES = {'appearance': ['appearance'], 'physics': ['physics'],
          'sequencer': ['sequencer/coh_seq_playback.c', 'sequencer/coh_seq_playback.h', 'sequencer/continuation'],
          'ui': ['ui/coh_hud.c', 'ui/coh_hud.h', 'ui/gameplay'],
          'audio': ['audio/coh_music.c', 'audio/coh_music.h', 'audio/coh_resample.c', 'audio/coh_resample.h', 'audio/android-integration'],
          'perf': ['perf']}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):
    p = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True)
    if p.returncode:
        raise ValueError(p.stderr.decode(errors='replace'))
    return p.stdout


def protected_audit(ref):
    baseline = git('rev-parse', '--verify', ref + '^{commit}').decode().strip()
    paths = git('ls-tree', '-r', '--name-only', baseline, '--', *PROTECTED).decode().splitlines()
    if not paths:
        raise ValueError('Protected baseline has no accepted source files')
    files = {}
    for name in paths:
        wanted = hashlib.sha256(git('show', baseline + ':' + name)).hexdigest()
        actual = digest(ROOT / name) if (ROOT / name).is_file() else None
        files[name] = {'baseline_sha256': wanted, 'current_sha256': actual, 'identical': actual == wanted}
    return {'baseline_ref': ref, 'baseline_sha': baseline, 'passed': all(x['identical'] for x in files.values()),
            'files': files, 'session_renderer': files.get('native-android/session-client/app/src/main/cpp/session_renderer.c')}


def scope_hashes():
    scopes = {}
    for module, paths in SCOPES.items():
        files = {}
        for relative in paths:
            path = NATIVE / 'engine' / relative
            for p in ([path] if path.is_file() else sorted(path.rglob('*'))):
                if p.is_file() and p.suffix in ('.c', '.h', '.py', '.json') and not any(
                        x in p.parts for x in ('__pycache__', 'qualification', 'evidence', 'build')):
                    files[str(p.relative_to(ROOT))] = digest(p)
        scopes[module] = {'files': files, 'sha256': hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}
    return scopes


def resolve(explicit, common, alternatives, marker=None):
    choices = [explicit] if explicit else [common / x for x in alternatives]
    for p in choices:
        if p and (p / marker).is_file() if marker else p and p.is_file():
            return p.resolve()
    return explicit.resolve() if explicit else None


def check_receipt(name, r):
    if name == 'appearance':
        return r.get('host_qualified') is True and r.get('arm64_built') is True and r['sanitizers'].get('run') is True and len(r['adapters'].get('files', [])) >= 7
    if name == 'physics':
        return r.get('passed') is True and r.get('sanitizers_passed') is True and r['android'].get('built') is True
    if name == 'sequencer':
        return all(x.get('failed', 0) == 0 for x in r['host'].values()) and 'asan-ubsan' in r['host'] and r.get('original_source_oracle') is True and len(r['additional_authentic_families'].get('raw_assets', [])) > 0 and 'compiled' in r['android'].get('status', '')
    if name == 'ui':
        return 'qualified' in r.get('host', '') and 'ASan + UBSan passed' in r.get('sanitizers', '') and r['authentic_font'].get('status') != 'not run; pass --font' and r['android'].get('status') != 'not run; pass --ndk'
    if name == 'audio':
        return r.get('passed') is True and r.get('authentic_stream_corpus') is not None and r.get('sanitizers') == ['address', 'undefined'] and r['android'].get('built') is True
    return r.get('status') == 'host-qualified-and-arm64-built' and r['sanitizers'].get('status') == 'passed' and r['android_arm64'].get('status') == 'built'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root', required=True, type=Path, help='Full repository root containing upstream/ouroboros and upstream/i24')
    ap.add_argument('--corpus', required=True, type=Path, help='Common local corpus root; per-input options override bounded relative discovery')
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--android-clang', required=True, type=Path, help='NDK aarch64-linux-android26-clang; NDK root is derived from this path')
    ap.add_argument('--baseline-ref', default='origin/native-android')
    ap.add_argument('--jobs', type=int, choices=(1, 2), default=2)
    ap.add_argument('--timeout', type=int, default=600, help='Seconds per checker; timeout is a failure, not a pass')
    ap.add_argument('--cc', default=os.environ.get('CC', 'cc'))
    ap.add_argument('--disable-leak-sanitizer', action='store_true', help='Explicit physics checker option for executor /proc restriction; other checker restrictions remain in their receipts')
    for name in ('appearance-corpus', 'animation-corpus', 'extra-animation-corpus', 'landing-corpus', 'walk-fixture',
                 'audio-codec-root', 'audio-asset-root', 'audio-stream-corpus', 'font', 'apk'):
        ap.add_argument('--' + name, type=Path)
    a = ap.parse_args()
    output = a.output.resolve() if a.output.suffix == '.json' else a.output.resolve() / 'qualification.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    common, source, clang = a.corpus.resolve(), a.source_root.resolve(), a.android_clang.absolute()
    ndk = clang.parents[5] if len(clang.parents) > 5 else Path('/invalid-ndk')
    inputs = {
        'appearance': resolve(a.appearance_corpus, common, ['appearance', 'support-appearance-corpus', '.'], 'rig.bin'),
        'animation': resolve(a.animation_corpus, common, ['animation', 'directional', 'coh-next/native-android/tools/directional_fixture/corpus', '.'], 'ready.anim'),
        'extra': resolve(a.extra_animation_corpus, common, ['extra', 'support-corpus/extra'], 'acquisition.json'),
        'landing': resolve(a.landing_corpus, common, ['extra-landing', 'support-corpus/extra-landing'], 'acquisition.json'),
        'walk': resolve(a.walk_fixture, common, ['walkable.bin', 'map-prepared/walkable.bin', 'nextbatch-prepared-assets/walkable.bin']),
        'codec': resolve(a.audio_codec_root, common, ['codec', 'decode/.deps'], 'vorbis/include/vorbis/codec.h'),
        'audio': resolve(a.audio_asset_root, common, ['audio', 'integration-probe/app/src/main/assets'], 'headset.ogg'),
        'streams': resolve(a.audio_stream_corpus, common, ['streams', 'audio-stream-corpus'], 'corpus.json'),
        'font': resolve(a.font, common, ['mont_hvbold.ttf', 'extra/assets/fonts/mont_hvbold.ttf', 'support-corpus/extra/assets/fonts/mont_hvbold.ttf']),
        'apk': resolve(a.apk, common, ['CoH-Native-Session-Client-0.3.0-arm64.apk', 'recovered-world-qualified/CoH-Native-Session-Client-0.3.0-arm64.apk']),
    }
    global_errors = []
    if not (source / 'upstream/ouroboros/Common/entity/entworldcoll.c').is_file() or not (source / 'upstream/i24').is_dir():
        global_errors.append('Full original source root unavailable')
    if not clang.is_file() or not (ndk / 'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang').is_file():
        global_errors.append('Required Android NDK compiler unavailable or path layout differs')
    try:
        audit_before = protected_audit(a.baseline_ref)
    except Exception as e:
        audit_before = {'passed': False, 'error': str(e)}
    before = scope_hashes()
    specs = {
        'appearance': ('appearance/check.py', ['appearance'], ['--source-root', source, '--corpus-root', inputs['appearance'], '--sanitize', '--ndk', ndk]),
        'physics': ('physics/check.py', ['walk'], ['--source-root', source, '--fixture', inputs['walk'], '--ndk', ndk] + (['--disable-leak-sanitizer'] if a.disable_leak_sanitizer else [])),
        'sequencer': ('sequencer/continuation/check.py', ['animation', 'extra', 'landing'], ['--source-root', source, '--corpus', inputs['animation'], '--extra-corpus', inputs['extra'], '--landing-corpus', inputs['landing'], '--sanitize', '--android-clang', clang]),
        'ui': ('ui/gameplay/check.py', ['font'], ['--source-root', source, '--font', inputs['font'], '--sanitize', '--ndk', ndk, '--cc', a.cc]),
        'audio': ('audio/android-integration/check.py', ['codec', 'audio', 'streams'], ['--source-root', source, '--codec-root', inputs['codec'], '--asset-root', inputs['audio'], '--stream-corpus', inputs['streams'], '--sanitize', '--ndk', ndk]),
        'perf': ('perf/check.py', ['apk'], ['--source-root', source, '--apk', inputs['apk'], '--ndk', ndk, '--compiler', a.cc]),
    }
    def execute(name, spec):
        script, required, arguments = spec
        directory = output.parent / name
        directory.mkdir(parents=True, exist_ok=True)
        receipt = directory / 'qualification.json'
        command = [str(x) for x in [sys.executable, NATIVE / 'engine' / script, *arguments, '--output', receipt]]
        errors = list(global_errors)
        errors += ['Missing authentic input: ' + key for key in required if inputs[key] is None or not inputs[key].exists()]
        if name == 'appearance' and inputs['appearance'] and not list(inputs['appearance'].glob('*.geo')):
            errors.append('Appearance corpus contains no authentic GEO files')
        if name == 'audio' and inputs['audio'] and not (inputs['audio'] / 'audio.bin').is_file():
            errors.append('Audio decoded reference unavailable')
        if name == 'perf' and inputs['apk'] and inputs['apk'].is_file() and digest(inputs['apk']) != ACCEPTED_APK_SHA:
            errors.append('Accepted 0.3.0 APK SHA256 differs')
        result = {'command': command, 'returncode': None, 'passed': False, 'preflight_errors': errors,
                  'android_execution': False, 'emulator_qualified': False, 'physical_thor_accepted': False}
        if errors:
            return name, result
        start = time.monotonic()
        try:
            env = {**os.environ, 'CC': a.cc, 'ANDROID_NDK_HOME': str(ndk)}
            p = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=a.timeout, env=env)
            (directory / 'stdout.log').write_text(p.stdout)
            (directory / 'stderr.log').write_text(p.stderr)
            result.update(returncode=p.returncode, stdout=str(directory / 'stdout.log'), stderr=str(directory / 'stderr.log'))
            if p.returncode == 0 and receipt.is_file():
                r = json.loads(receipt.read_text())
                result.update(receipt=r, receipt_path=str(receipt), receipt_sha256=digest(receipt), passed=check_receipt(name, r))
                if not result['passed']:
                    result['validation_error'] = 'Checker exited zero but required host/sanitizer/source/corpus/ARM64 evidence is incomplete'
        except Exception as e:
            result['error'] = str(e)
        result['elapsed_seconds'] = time.monotonic() - start
        return name, result
    workers = {}
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        futures = [pool.submit(execute, name, spec) for name, spec in specs.items()]
        for future in as_completed(futures):
            name, result = future.result()
            workers[name] = result
            print(json.dumps({'worker': name, 'passed': result['passed'], 'returncode': result['returncode']}), flush=True)
    after = scope_hashes()
    try:
        audit_after = protected_audit(audit_before.get('baseline_sha', a.baseline_ref))
    except Exception as e:
        audit_after = {'passed': False, 'error': str(e)}
    report = {'schema': 'coh-native-second-batch-aggregate-v1', 'created_utc': datetime.now(timezone.utc).isoformat(),
              'source_head_at_finish': git('rev-parse', 'HEAD').decode().strip(), 'jobs': a.jobs,
              'passed': all(x['passed'] for x in workers.values()) and audit_before['passed'] and audit_after['passed'] and before == after,
              'commands_invoke_only': list(specs), 'network_auth_session_tests_run': False,
              'inputs': {k: str(v) if v else None for k, v in inputs.items()}, 'source_root': str(source),
              'android_clang': str(clang), 'host_compiler': a.cc, 'global_preflight_errors': global_errors,
              'accepted_apk_sha256': digest(inputs['apk']) if inputs['apk'] and inputs['apk'].is_file() else None,
              'protected_source_before': audit_before, 'protected_source_after': audit_after,
              'module_scope_before': before, 'module_scope_after': after, 'module_scopes_unchanged': before == after,
              'workers': workers, 'android_execution': False, 'emulator_qualified': False, 'physical_thor_accepted': False,
              'qualification_scope': 'Fresh offline host/source-oracle/sanitizer tests and ARM64 compilation only; no complete gate, full-game FPS or new device acceptance.'}
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'output': str(output), 'workers_passed': sum(x['passed'] for x in workers.values()), 'android_execution': False}), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
