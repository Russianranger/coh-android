#!/usr/bin/env python3
"""Build the opt-in mixer + AAudio library with Android NDK, without APK/JNI edits."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ndk', type=Path, required=True)
    p.add_argument('--build-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    tools = a.ndk / 'toolchains/llvm/prebuilt/linux-x86_64/bin'
    cc = tools / 'aarch64-linux-android26-clang'
    a.build_dir.mkdir(parents=True, exist_ok=True)
    sources = [HERE / 'coh_mixer.c', HERE / 'coh_mixer_aaudio.c', HERE / 'coh_audio_session.c', NATIVE / 'audio/coh_audio.c']
    commands = []
    objects = []
    for source in sources:
        obj = a.build_dir / (source.stem + '.o')
        command = [str(cc), '-std=c11', '-O2', '-fPIC', '-Wall', '-Wextra', '-Werror', '-ffp-contract=off', '-c', str(source), '-o', str(obj)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        commands.append(command)
        objects.append(obj)
    library = a.build_dir / 'libcoh_game_audio.so'
    link = [str(cc), '-shared', '-Wl,--no-undefined', *map(str, objects), '-laaudio', '-lm', '-o', str(library)]
    subprocess.run(link, check=True, capture_output=True, text=True)
    commands.append(link)
    elf = subprocess.check_output([str(tools / 'llvm-readelf'), '-h', '-d', str(library)], text=True)
    if 'AArch64' not in elf or 'libaaudio.so' not in elf:
        raise ValueError('Unexpected architecture or Android audio linkage')
    receipt = {'schema': 'coh-native-gate43-android-library-v1', 'passed': True, 'abi': 'arm64-v8a', 'api': 26,
               'compiler': subprocess.check_output([str(cc), '--version'], text=True).splitlines()[0],
               'ndk_revision': (a.ndk / 'source.properties').read_text().strip(),
               'sources': {str(s.relative_to(NATIVE.parent)): sha(s) for s in sources},
               'commands': commands, 'library_sha256': sha(library), 'library_bytes': library.stat().st_size,
               'elf': elf, 'android_emulator': 'not run', 'physical_thor': 'not run',
               'scope': 'Linked opt-in native library including AAudio sink and application lifecycle controller; no APK or existing Session Client changes'}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'passed': True, 'output': str(a.output), 'sha256': sha(library), 'bytes': library.stat().st_size}))


if __name__ == '__main__':
    main()
