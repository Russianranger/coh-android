#!/usr/bin/env python3
"""Streaming/resampling qualification; never changes accepted source or APKs."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
AUDIO = HERE.parent
NATIVE = AUDIO.parents[1]
REPO = NATIVE.parent
RECOVERED = Path('/workspace/scratch/cd30b2fc1c9e/recovery-corpus/coh-next/native-android')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, **kwargs)
    require(result.returncode == 0, result.stdout + result.stderr)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--source-root', default=REPO, type=Path)
    p.add_argument('--codec-root', default=RECOVERED / 'decode/.deps', type=Path)
    p.add_argument('--asset-root', default=RECOVERED / 'integration-probe/app/src/main/assets', type=Path)
    p.add_argument('--stream-corpus', type=Path, help='Verified corpus from android-integration/acquire.py; enables authentic long music/ambient and independent FFmpeg checks')
    p.add_argument('--sanitize', action='store_true')
    p.add_argument('--ndk', type=Path)
    p.add_argument('--build-dir', type=Path)
    a = p.parse_args()
    spec = importlib.util.spec_from_file_location('qualified_audio_check', AUDIO / 'check.py')
    accepted = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(accepted)
    codec, codec_receipt = accepted.codec_sources(a.codec_root)
    ogg = a.asset_root / 'headset.ogg'
    reference = a.asset_root / 'audio.bin'
    pins = json.loads((NATIVE / 'tools/audio_fixture/pins.json').read_text())
    fixture = json.loads((NATIVE / 'evidence/phases10-12/audio-fixture.json').read_text())
    require(sha(ogg) == pins['record']['sha256'], 'Authentic compressed asset changed')
    require(sha(reference) == fixture['audio']['sha256'], 'Qualified decoded reference changed')
    audit = json.loads((NATIVE / 'decode/source-audit.json').read_text())
    source = a.source_root / audit['source']
    require(sha(source) == audit['source_sha256'], 'Original Ogg source changed')
    require('ov_read(&ogg->vf,decode->decode_buffer + decode->decode_count,decode->decode_len - decode->decode_count,0,2,1,&ogg->current_section)' in source.read_text(), 'Original signed16 LE conversion contract changed')
    module = [AUDIO / 'coh_music.c', AUDIO / 'coh_resample.c', AUDIO / 'coh_mixer.c', NATIVE / 'audio/coh_audio.c']
    include = ['-I' + str(a.codec_root / part) for part in ['ogg/include', 'vorbis/include', 'vorbis/lib']]
    strict = ['-std=c11', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-ffp-contract=off']
    sanitized = ['-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie'] if a.sanitize else []
    with tempfile.TemporaryDirectory(prefix='coh-stream-audio-') as temporary:
        build = Path(temporary)
        oracle, source_receipt = accepted.source_oracle(a.source_root, build)
        objects = []
        for i, path in enumerate(codec):
            obj = build / ('codec-' + str(i) + '.o')
            run(['gcc', '-std=c11', '-O2', '-g', *sanitized, '-DHAVE_ALLOCA_H=1', *include, '-c', path, '-o', obj])
            objects.append(obj)
        executable = build / 'test-stream'
        command = ['gcc', *strict, *sanitized, *include, HERE / 'test_music.c', *module, oracle, *objects,
                   '-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free', '-lm', '-o', executable]
        if a.sanitize:
            command += ['-fsanitize=address,undefined', '-no-pie']
        run(command)
        env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        run_args = [str(ogg), str(reference)]
        corpus_receipt = None
        if a.stream_corpus:
            corpus_receipt = json.loads((a.stream_corpus / 'corpus.json').read_text())
            require(corpus_receipt['manifest_sha256'] == pins['manifest_sha256'], 'Long asset manifest identity differs')
            expected_long = {'atlasplaza.ogg': ('data/sound/ogg/music/atlasplaza.ogg', '1a9f7ee21bc425508eb2e4a17c6ac66c04059ee6f0b0e4d0517ba3e1095c7bf7'),
                             'steam1.ogg': ('data/sound/ogg/city/steam1_loop.ogg', '176bfd08df6a17af558157ad1934d23c92aaaa81d7428e2e04d1250cfa0c6821')}
            for name, (original_path, expected_sha) in expected_long.items():
                asset = a.stream_corpus / name
                record = next(r for r in corpus_receipt['records'] if r['file_name'] == name)
                require(record['path'] == original_path and record['sha256'] == expected_sha and sha(asset) == expected_sha, 'Authentic long sound identity differs')
                pcm = build / (name + '.pcm')
                run(['ffmpeg', '-v', 'error', '-i', asset, '-map', '0:a:0', '-f', 's16le', '-acodec', 'pcm_s16le', pcm])
                run_args.extend([str(asset), str(pcm)])
            corpus_receipt['independent_reference'] = run(['ffmpeg', '-version']).stdout.splitlines()[0]
        result = subprocess.run([str(executable), *run_args], capture_output=True, text=True, timeout=180, env=env)
        leaks = 'enabled' if a.sanitize else 'not requested'
        if a.sanitize and result.returncode and 'LeakSanitizer has encountered a fatal error' in result.stderr and "Can't open /proc/" in result.stderr:
            leaks = 'unavailable: sandbox /proc task access denied; explicit linked allocation accounting enforced'
            env['ASAN_OPTIONS'] = 'detect_leaks=0:halt_on_error=1'
            result = subprocess.run([str(executable), *run_args], capture_output=True, text=True, timeout=180, env=env)
        require(result.returncode == 0, result.stdout + result.stderr)
        rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    android = None
    if a.ndk:
        build = a.build_dir or (a.output.parent / 'android-build')
        build.mkdir(parents=True, exist_ok=True)
        tools = a.ndk / 'toolchains/llvm/prebuilt/linux-x86_64/bin'
        cc = tools / 'aarch64-linux-android26-clang'
        commands = []
        objects = []
        arm_sources = module + [AUDIO / 'coh_mixer_aaudio.c'] + codec
        for i, path in enumerate(arm_sources):
            obj = build / ('object-' + str(i) + '.o')
            flags = strict if path not in codec else ['-std=c11', '-O2']
            command = [cc, *flags, '-fPIC', '-DHAVE_ALLOCA_H=1', *include, '-c', path, '-o', obj]
            run(command)
            commands.append(list(map(str, command)))
            objects.append(obj)
        library = build / 'libcoh_stream_audio.so'
        command = [cc, '-shared', '-Wl,--no-undefined', *objects, '-laaudio', '-lm', '-o', library]
        run(command)
        commands.append(list(map(str, command)))
        elf = run([tools / 'llvm-readelf', '-h', '-d', library]).stdout
        require('AArch64' in elf and 'libaaudio.so' in elf, 'ARM64 AAudio linkage absent')
        android = {'built': True, 'abi': 'arm64-v8a', 'api': 26, 'library': str(library), 'sha256': sha(library),
                   'bytes': library.stat().st_size, 'commands': commands, 'elf': elf,
                   'compiler': run([cc, '--version']).stdout.splitlines()[0], 'emulator': 'not run', 'physical_thor': 'not run'}
    receipt = {'schema': 'coh-native-gate43-streaming-v1', 'passed': True,
               'source_provenance': {'decode_source': str(source), 'decode_source_sha256': sha(source),
                                     'source_revision': audit['source_revision'], 'existing_source_oracles': source_receipt},
               'codec': codec_receipt, 'authentic_asset': {'virtual_path': pins['record']['name'], 'ogg_sha256': sha(ogg), 'reference_sha256': sha(reference)},
               'authentic_stream_corpus': corpus_receipt,
               'sources': {str(s.relative_to(REPO)): sha(s) for s in [*module, AUDIO / 'coh_music.h', AUDIO / 'coh_resample.h', HERE / 'test_music.c']},
               'results': rows, 'sanitizers': ['address', 'undefined'] if a.sanitize else [], 'leak_sanitizer': leaks, 'android': android,
               'limitations': [('Authentic Atlas Plaza music and city steam qualify two files, not all original music/ambient routing' if corpus_receipt else 'One authentic short headset clip looped; long music/ambient corpus check not requested'),
                               'Linear resampler has no bandlimited antialias filter and is not source DirectSound sample parity',
                               'Open scans compressed pages off callback; codec heap allocations occur on decoder owner and are separate from fixed adapter storage',
                               'Simulated host playback does not establish Android timing, audible output or physical Thor acceptance',
                               'Use primary audio lifecycle controller unchanged; this extension does not request OS audio focus']}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'passed': True, 'output': str(a.output), 'results': rows, 'android_built': android is not None}))


if __name__ == '__main__':
    main()
