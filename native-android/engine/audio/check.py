#!/usr/bin/env python3
"""Standalone Gate 43 host/source/decoder checks. Never changes accepted gates."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parents[1]
REPO = NATIVE.parent
RECOVERED = Path('/workspace/scratch/552733ac6bdc/coh-next/native-android')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def function(text, name):
    matches = list(re.finditer(r'(?m)^(?:static )?[^\n]+\b' + re.escape(name) + r'\([^\n]*\)\s*\{', text))
    require(len(matches) == 1, 'Function identity differs: ' + name)
    start = matches[0].start()
    at = text.find('{', start) + 1
    depth = 1
    while depth:
        require(at < len(text), 'Unbalanced source ' + name)
        depth += (text[at] == '{') - (text[at] == '}')
        at += 1
    return text[start:at]


def source_oracle(source_root, build):
    root = source_root / 'upstream/ouroboros/Game/src/sound'
    expected = {'sound.c': '8f114a02c47c25cba0c090e1fd6b8a164a8bd7086ba1590ef5ef236db77eab25',
                'sound_sys.c': '0a48bbdc5006c2e2876253412bd263b9f2640de3745c27a2616dab0c5f173f09'}
    texts = {}
    for name, sha in expected.items():
        path = root / name
        require(path.is_file() and digest(path) == sha, 'Source hash differs: ' + str(path))
        texts[name] = path.read_text(encoding='latin1').replace('\r\n', '\n')
    attenuation = function(texts['sound.c'], 'sndSphereVolume')
    gain = '\n'.join(function(texts['sound_sys.c'], n) for n in ['volumeDbToRatio', 'volumeRatioToDb'])
    group = function(texts['sound.c'], 'sphereGroupGetVolume')
    shim = '''#include <math.h>
typedef float F32; typedef int S32; typedef float Vec3[3];
static struct { int ignoreSoundRamp; } game_state;
static float head_mat[4][3];
static void subVec3(const float*a,const float*b,float*c){for(int i=0;i<3;i++)c[i]=a[i]-b[i];}
static float normalVec3(float*v){float n=sqrtf(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);if(n)for(int i=0;i<3;i++)v[i]/=n;return n;}
static float lengthVec3(const float*v){return sqrtf(v[0]*v[0]+v[1]*v[1]+v[2]*v[2]);}
static void zeroVec3(float*v){for(int i=0;i<3;i++)v[i]=0;}
static void scaleVec3(const float*v,float s,float*out){for(int i=0;i<3;i++)out[i]=v[i]*s;}
static float dotVec3(const float*a,const float*b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
typedef struct {float inner_radius,outer_radius,secTimeoutTotal,secTimeoutCurrent,volRatio,spatialVariance,max_volume;Vec3 pos;} SoundSphere;
static int gets3D(SoundSphere*s){(void)s;return 1;}
#define MIN(a,b) ((a)<(b)?(a):(b))
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN_VOLUME_DB (-10000)
#define MAX_VOLUME_DB 0
#define MINMAX(v,lo,hi) ((v)<(lo)?(lo):((v)>(hi)?(hi):(v)))
'''
    suffix = '''
float oracle_attenuation(float inner,float outer,float distance,int ignore) { game_state.ignoreSoundRamp=ignore;Vec3 pos={distance,0,0};return sndSphereVolume(inner,outer,pos); }
int oracle_db(float v){return volumeRatioToDb(v);}
float oracle_gain(int v){return volumeDbToRatio(v);}
float oracle_spatial(float inner,float outer,float x,float y,float z,float gain,int ignore,float*pan) {
    game_state.ignoreSoundRamp=ignore;head_mat[0][0]=1;
    SoundSphere s={0};s.inner_radius=inner;s.outer_radius=outer;s.max_volume=1;s.volRatio=gain;s.pos[0]=x;s.pos[1]=y;s.pos[2]=z;
    *pan=0;return sphereGroupGetVolume(&s,1,pan);
}
'''
    path = build / 'oracle.c'
    path.write_text(shim + attenuation + '\n#pragma GCC diagnostic push\n#pragma GCC diagnostic ignored "-Wunused-variable"\n' + group + '\n#pragma GCC diagnostic pop\n' + gain + suffix)
    return path, {'revision': '61bcde64ece0c45a1e3ba1c39f038b15dc6efd7d', 'files': expected,
                  'functions': {n: hashlib.sha256(function(texts[f], n).encode()).hexdigest()
                                for n, f in [('sndSphereVolume', 'sound.c'), ('sphereGroupGetVolume', 'sound.c'), ('volumeDbToRatio', 'sound_sys.c'), ('volumeRatioToDb', 'sound_sys.c')]},
                  'shim': 'F32, vector operations, zero listener, head-right X, ignoreSoundRamp flag, one 3D sphere without fade/variance; functions unchanged'}


def codec_sources(root):
    pins = json.loads((NATIVE / 'decode/dependency-pins.json').read_text())
    count = 0
    for name, pin in pins.items():
        for relative, sha in pin['files'].items():
            path = root / name / relative
            require(path.is_file() and digest(path) == sha, 'Codec source differs: ' + str(path))
            count += 1
    original = (root / 'vorbis/lib/sharedbook.c').read_text()
    overlay = root / 'safe/sharedbook.c'
    old = 'ogg_uint32_t word=i<<(32-c->dec_firsttablen);'
    new = 'ogg_uint32_t word=(ogg_uint32_t)i<<(32-c->dec_firsttablen);'
    require(original.count(old) == 1 and overlay.read_text() == original.replace(old, new), 'Qualified codec overlay differs')
    require('#include <stdint.h>' in (root / 'ogg/include/ogg/config_types.h').read_text(), 'Generated Ogg types unavailable')
    names = 'mdct smallft block envelope window lsp lpc analysis synthesis psy info floor1 floor0 res0 mapping0 registry codebook sharedbook lookup bitrate vorbisfile'.split()
    sources = [root / 'ogg/src/bitwise.c', root / 'ogg/src/framing.c']
    sources += [overlay if n == 'sharedbook' else root / ('vorbis/lib/' + n + '.c') for n in names]
    return sources, {'verified_files': count, 'revisions': {n: p['revision'] for n, p in pins.items()},
                     'safe_overlay_sha256': digest(overlay)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, default=REPO)
    parser.add_argument('--codec-root', type=Path, default=RECOVERED / 'decode/.deps')
    parser.add_argument('--asset-root', type=Path, default=RECOVERED / 'integration-probe/app/src/main/assets')
    parser.add_argument('--sanitize', action='store_true')
    parser.add_argument('--no-authentic', action='store_true', help='Explicit partial check only; never reports authentic qualification')
    parser.add_argument('--cc', default=os.environ.get('CC', 'gcc'))
    args = parser.parse_args()
    cc = shlex.split(args.cc)
    with tempfile.TemporaryDirectory(prefix='coh-mixer-') as temporary:
        build = Path(temporary)
        oracle, source_receipt = source_oracle(args.source_root, build)
        sources = [HERE / 'test_mixer.c', HERE / 'coh_mixer.c', NATIVE / 'audio/coh_audio.c', oracle]
        strict = ['-std=c11', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-ffp-contract=off']
        options = ['-pthread']
        if args.sanitize:
            strict += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie']
            options += ['-fsanitize=address,undefined', '-no-pie']
        codec_receipt = None
        asset_receipt = None
        objects = []
        run_args = []
        if not args.no_authentic:
            codec, codec_receipt = codec_sources(args.codec_root)
            include = ['-I' + str(args.codec_root / p) for p in ['ogg/include', 'vorbis/include', 'vorbis/lib']]
            codec_flags = [x for x in strict if x not in ['-Wall', '-Wextra', '-Werror']]
            for i, path in enumerate(codec):
                obj = build / ('codec-' + str(i) + '.o')
                subprocess.run([*cc, *codec_flags, '-DHAVE_ALLOCA_H=1', *include, '-c', str(path), '-o', str(obj)], check=True, capture_output=True, text=True)
                objects.append(obj)
            sources.append(NATIVE / 'decode/coh_decode.c')
            strict += ['-DWITH_DECODE=1', *include]
            pins = json.loads((NATIVE / 'tools/audio_fixture/pins.json').read_text())
            ogg = args.asset_root / 'headset.ogg'
            reference = args.asset_root / 'audio.bin'
            require(digest(ogg) == pins['record']['sha256'], 'Authentic Ogg identity differs')
            fixture = json.loads((NATIVE / 'evidence/phases10-12/audio-fixture.json').read_text())
            require(digest(reference) == fixture['audio']['sha256'], 'Qualified PCM identity differs')
            asset_receipt = {'path': pins['record']['name'], 'ogg_sha256': digest(ogg), 'reference_sha256': digest(reference)}
            run_args = [str(ogg), str(reference)]
        executable = build / 'test-mixer'
        command = [*cc, *strict, *map(str, sources), *map(str, objects), *options,
                   '-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free', '-lm', '-o', str(executable)]
        result = subprocess.run(command, capture_output=True, text=True)
        require(result.returncode == 0, result.stdout + result.stderr)
        environment = dict(os.environ)
        environment['ASAN_OPTIONS'] = 'detect_leaks=1:halt_on_error=1'
        environment['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
        result = subprocess.run([str(executable), *run_args], capture_output=True, text=True, env=environment, timeout=120)
        leak_sanitizer = 'enabled' if args.sanitize else 'not requested'
        if args.sanitize and result.returncode and 'LeakSanitizer has encountered a fatal error' in result.stderr and "Can't open /proc/" in result.stderr:
            leak_sanitizer = 'unavailable: runtime cannot read /proc/PID/task; allocation accounting still enforced'
            environment['ASAN_OPTIONS'] = 'detect_leaks=0:halt_on_error=1'
            result = subprocess.run([str(executable), *run_args], capture_output=True, text=True, env=environment, timeout=120)
        require(result.returncode == 0, result.stdout + result.stderr)
        rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
        backend = build / 'test-aaudio-owner'
        command = [*cc, *strict, '-I' + str(HERE / 'host-shim'), str(HERE / 'test_aaudio.c'),
                   str(HERE / 'coh_mixer_aaudio.c'), str(HERE / 'coh_mixer.c'), str(NATIVE / 'audio/coh_audio.c'),
                   *options, '-Wl,--wrap=clock_gettime', '-lm', '-o', str(backend)]
        result = subprocess.run(command, capture_output=True, text=True)
        require(result.returncode == 0, result.stdout + result.stderr)
        result = subprocess.run([str(backend)], capture_output=True, text=True, env=environment, timeout=15)
        if args.sanitize and result.returncode and 'LeakSanitizer has encountered a fatal error' in result.stderr and "Can't open /proc/" in result.stderr:
            leak_sanitizer = 'unavailable: runtime cannot read /proc/PID/task; allocation accounting still enforced'
            environment['ASAN_OPTIONS'] = 'detect_leaks=0:halt_on_error=1'
            result = subprocess.run([str(backend)], capture_output=True, text=True, env=environment, timeout=15)
        require(result.returncode == 0, result.stdout + result.stderr)
        rows += [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
        receipt = {'schema': 'coh-native-gate43-host-v1', 'passed': True, 'source_oracle': source_receipt,
                   'module_sources': {str(p.relative_to(REPO)): digest(p) for p in
                                      [HERE / 'coh_mixer.c', HERE / 'coh_mixer.h', HERE / 'coh_mixer_aaudio.c',
                                       HERE / 'coh_mixer_aaudio.h', HERE / 'test_mixer.c', HERE / 'test_aaudio.c', NATIVE / 'audio/coh_audio.c']},
                   'sanitizers': ['address', 'undefined'] if args.sanitize else [], 'leak_sanitizer': leak_sanitizer,
                   'codec': codec_receipt, 'authentic_asset': asset_receipt, 'results': rows,
                   'compiler': subprocess.check_output([*cc, '--version'], text=True).splitlines()[0],
                   'real_time_allocation_guard': 'linker-wrapped malloc/calloc/realloc/free assert callback never calls allocator',
                   'android_emulator': 'not run', 'physical_thor': 'not run',
                   'limitations': ['Software stereo approximation; no DirectSound/HRTF sample parity', 'No resampling, Doppler, reverb, sphere merging or original owner routing',
                                   'Streaming ring accepts off-thread decoded PCM; existing bounded Ogg decoder still decodes whole clips',
                                   'Host elapsed time is not a device benchmark or proof of audible output']}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'passed': True, 'output': str(args.output), 'sanitized': args.sanitize,
                          'authentic': asset_receipt is not None, 'results': rows}))


if __name__ == '__main__':
    main()
