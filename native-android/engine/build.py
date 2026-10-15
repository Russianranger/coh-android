#!/usr/bin/env python3
"""Build opt-in engine modules together, outside every existing APK/JNI target."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, shutil, subprocess

ENGINE = Path(__file__).resolve().parent
NATIVE = ENGINE.parent
SOURCES = [
    'engine/assets/coh_asset_loader.c', 'engine/assets/coh_asset_geo.c',
    'engine/renderer/coh_renderer.c',
    'engine/network/coh_net.c', 'engine/network/coh_net_frame.c', 'engine/network/coh_net_zip.c',
    'engine/network/coh_net_udp.c', 'engine/auth/coh_auth.c',
    'engine/login/coh_login.c', 'engine/dbclient/coh_dbclient.c',
    'engine/dbclient/coh_db_session.c', 'engine/live/coh_live.c',
    'engine/mapclient/coh_mapclient.c',
    'engine/replication/coh_replication.c',
    'engine/session/coh_session_crypto.c',
    'engine/sequencer/coh_sequencer.c', 'engine/ui/coh_ui.c', 'engine/audio/coh_mixer.c',
    'src/coh_assets.c', 'src/coh_dds.c', 'src/coh_blowfish.c',
    'protocol/coh_protocol.c', 'animation/coh_animation.c', 'audio/coh_audio.c',
]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cc', default=os.environ.get('CC', 'gcc'))
    parser.add_argument('--ndk', type=Path)
    parser.add_argument('--codec-root', type=Path, help='Recovered pinned codec sources; copied and verified off-thread')
    parser.add_argument('--audio-fixture', type=Path, help='Original hash-pinned headset.ogg for asset/decoder/mixer ownership test')
    parser.add_argument('--crypto-root', type=Path, help='Verified single-ABI public Android crypto build output')
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    cc = args.cc
    flags = ['-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-ffp-contract=off',
             '-I'+str(NATIVE/'include'), '-I'+str(NATIVE/'src')]
    sources = [NATIVE/x for x in SOURCES]
    vendor_sources = []
    codec_receipt = None
    libraries = ['-lz', '-lm']
    readelf = 'readelf'
    crypto_receipt = None
    if args.crypto_root and not args.ndk:
        parser.error('--crypto-root requires an Android NDK build')
    if args.ndk:
        if args.sanitize:
            parser.error('Android sanitizer execution needs a device; this build is release-only')
        toolchain = args.ndk.resolve()/'toolchains/llvm/prebuilt/linux-x86_64/bin'
        cc = str(toolchain/'aarch64-linux-android26-clang')
        readelf = str(toolchain/'llvm-readelf')
        sources += [ENGINE/'renderer/coh_renderer_gles.c', ENGINE/'audio/coh_mixer_aaudio.c',
                    ENGINE/'audio/coh_audio_session.c']
        libraries += ['-lGLESv3', '-laaudio']
        if args.crypto_root:
            crypto = args.crypto_root.resolve()
            crypto_receipt = json.loads((crypto/'receipt.json').read_text())
            if crypto_receipt['status'] != 'PASS' or crypto_receipt['abi'] != 'arm64-v8a':
                raise RuntimeError('Android crypto receipt must qualify ARM64')
            pin = json.loads((ENGINE/'auth/android/openssl-source.json').read_text())
            if crypto_receipt['openssl_archive_sha256'] != pin['sha256'] or crypto_receipt['openssl_version'] != pin['version']:
                raise RuntimeError('Android crypto dependency pin differs')
            for path,sha in crypto_receipt['artifacts_sha256'].items():
                if hashlib.sha256((crypto/path).read_bytes()).hexdigest()!=sha:
                    raise RuntimeError('Android crypto artifact hash differs: '+path)
            flags += ['-I'+str(crypto/'include')]
            sources += [ENGINE/'auth/coh_auth_openssl.c']
            libraries += [str(crypto/'lib/libcrypto.a'), '-ldl']
    if args.sanitize:
        flags += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    if args.codec_root:
        codec_root = out/'pinned-codecs'
        shutil.copytree(args.codec_root, codec_root, dirs_exist_ok=True)
        spec = importlib.util.spec_from_file_location('coh_pinned_codec_acquire', NATIVE/'tools/decode_fixture/acquire.py')
        acquire = importlib.util.module_from_spec(spec); spec.loader.exec_module(acquire)
        codec_receipt = acquire.acquire(codec_root)
        flags += ['-DCOH_ENGINE_WITH_DECODER=1', '-DHAVE_ALLOCA_H=1',
                  '-I'+str(codec_root/'ogg/include'), '-I'+str(codec_root/'vorbis/include'),
                  '-I'+str(codec_root/'vorbis/lib')]
        sources += [ENGINE/'assets/coh_asset_audio.c', NATIVE/'decode/coh_decode.c']
        vendor_sources = [codec_root/'ogg/src/bitwise.c', codec_root/'ogg/src/framing.c']
        for name in 'mdct smallft block envelope window lsp lpc analysis synthesis psy info floor1 floor0 res0 mapping0 registry codebook sharedbook lookup bitrate vorbisfile'.split():
            vendor_sources.append(codec_root/'safe/sharedbook.c' if name=='sharedbook' else codec_root/'vorbis/lib'/f'{name}.c')
    if args.audio_fixture and not args.codec_root:
        parser.error('--audio-fixture requires --codec-root')
    if args.audio_fixture:
        pins=json.loads((NATIVE/'tools/audio_fixture/pins.json').read_text())['record']
        data=args.audio_fixture.read_bytes()
        if len(data)!=pins['size'] or hashlib.sha256(data).hexdigest()!=pins['sha256']:
            raise RuntimeError('Authentic audio fixture identity differs')
    vendor_objects=[]
    for index, source in enumerate(vendor_sources):
        obj=out/f'codec-{index}.o'
        vendor_flags=[f for f in flags if f not in ['-Wall','-Wextra','-Werror']]
        subprocess.run([cc,*vendor_flags,'-fPIC','-c',str(source),'-o',str(obj)],check=True)
        vendor_objects.append(str(obj))
    library = out/'libcoh_native_engine.so'
    command = [cc, *flags, '-shared', '-fPIC', *map(str, sources), *vendor_objects, *libraries,
               '-Wl,--no-undefined', '-o', str(library)]
    subprocess.run(command, check=True)
    elf = subprocess.check_output([readelf, '-h', '-d', str(library)], text=True)
    (out/'elf.txt').write_text(elf)
    if args.ndk and ('AArch64' not in elf or 'ELF64' not in elf):
        raise RuntimeError('Android library is not ELF64 AArch64')
    receipt = {
        'schema': 'coh-native-engine-build-v1', 'passed': True,
        'compiler': subprocess.check_output([cc, '--version'], text=True).splitlines()[0],
        'command': command, 'android_arm64_bionic_cross_compiled': bool(args.ndk),
        'android_executed': False, 'physical_thor_qualified': False,
        'sanitizers': ['address', 'undefined'] if args.sanitize else [],
        'library': {'name': library.name, 'bytes': library.stat().st_size,
                    'sha256': hashlib.sha256(library.read_bytes()).hexdigest()},
        'sources': [{'path': str(p.relative_to(NATIVE)),
                     'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources],
        'scope': 'Combined opt-in libraries only. No APK, JNI, server exchange or gameplay performance claim.',
        'public_android_crypto_provider_linked': bool(crypto_receipt),
    }
    if crypto_receipt:
        receipt['public_crypto_receipt_sha256']=hashlib.sha256((args.crypto_root/'receipt.json').read_bytes()).hexdigest()
        if 'libcrypto.so' in elf or 'libssl.so' in elf:
            raise RuntimeError('Private/dynamic platform crypto dependency is forbidden')
    if codec_receipt:
        receipt['pinned_codec_verification']=codec_receipt
        receipt['codec_sources']=[{'path':str(p.relative_to(out)), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in vendor_sources]
    if not args.ndk:
        exe = out/'engine-integration-test'
        command = [cc, *flags, str(ENGINE/'tests/integration.c'), *map(str, sources),
                   *vendor_objects, *libraries, '-o', str(exe)]
        if args.sanitize:
            command += ['-fno-pie', '-no-pie']
        subprocess.run(command, check=True)
        env = os.environ.copy()
        if args.sanitize:
            env.update(ASAN_OPTIONS='detect_leaks=0:abort_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        run=[str(exe)]
        if args.audio_fixture: run += [str(args.audio_fixture.resolve())]
        result = json.loads(subprocess.check_output(run, text=True, env=env, timeout=60))
        if not result['passed']:
            raise RuntimeError('Cross-module integration failed')
        receipt['host_integration'] = result
        receipt['leak_sanitizer_executed'] = False
        receipt['leak_sanitizer_limitation'] = 'LSan task enumeration is unavailable in this execution environment.'
    (out/'build-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k: receipt[k] for k in ['passed', 'android_arm64_bionic_cross_compiled', 'library']}))

if __name__ == '__main__':
    main()
