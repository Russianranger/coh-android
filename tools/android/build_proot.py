#!/usr/bin/env python3
"""Build pinned PRoot/talloc for the APK and the Linux ARM64 guest smoke test.

No global installation or source checkout is modified. Every build uses a new
work directory and preserves original sources, patches and recipes with hashes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import tarfile
import urllib.request


ROOT = Path(__file__).resolve().parents[2]
PATCHES = ROOT / 'android/native/proot'
PROOT_URL = 'https://github.com/termux/proot.git'
PROOT_COMMIT = '7266fb3e8516535682f5a9c8f3a7e70f6506eddb'
PROOT_TREE = '8fcee3911b8e0848a1fc75c2e9827316ba658a5a'
SOURCE_DATE_EPOCH = '1787437959'
TALLOC_URL = 'https://www.samba.org/ftp/talloc/talloc-2.4.3.tar.gz'
TALLOC_SHA256 = 'dc46c40b9f46bb34dd97fe41f548b0e8b247b77a918576733c528e83abd854dd'
NDK_VERSION = '27.2.12479018'
PATCH_NAMES = ('0001-sysvipc-memfd.patch', '0002-android-string-header.patch',
               '0003-portable-loader-offset.patch')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def record(path):
    return {'bytes': path.stat().st_size, 'sha256': sha256(path)}


def run(command, cwd=None, env=None, capture=False):
    return subprocess.run([str(arg) for arg in command], cwd=cwd, env=env,
                          check=True, text=True, stdout=subprocess.PIPE if capture else None).stdout


def extract(archive, destination):
    """Only the verified upstream archives enter this new private build tree."""
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        require(len(members) < 100000 and sum(m.size for m in members) < 512 * 1024 * 1024,
                'Source archive exceeds the reviewed bound')
        for member in members:
            path = Path(member.name)
            require(not path.is_absolute() and '..' not in path.parts and
                    not member.isdev() and not member.isfifo(), 'Unsafe source archive entry')
        bundle.extractall(destination, filter='data')


def prepare(work, checkout=None, talloc_archive=None):
    sources = work / 'sources'
    sources.mkdir()
    if checkout is None:
        checkout = work / 'proot-git'
        run(['git', 'init', checkout])
        run(['git', '-C', checkout, 'remote', 'add', 'origin', PROOT_URL])
        run(['git', '-C', checkout, 'fetch', '--depth', '1', 'origin', PROOT_COMMIT])
    require(run(['git', '-C', checkout, 'rev-parse', PROOT_COMMIT + '^{tree}'], capture=True).strip() == PROOT_TREE,
            'PRoot source tree differs from the pinned commit')
    proot_archive = sources / ('proot-' + PROOT_COMMIT + '.tar.gz')
    run(['git', '-C', checkout, 'archive', '--format=tar.gz', '--prefix=proot/',
         '--output=' + str(proot_archive), PROOT_COMMIT])
    talloc = sources / 'talloc-2.4.3.tar.gz'
    if talloc_archive:
        shutil.copyfile(talloc_archive, talloc)
    else:
        # TLS verification remains enabled. Failed/partial downloads never pass
        # the mandatory complete-file hash check below.
        with urllib.request.urlopen(TALLOC_URL, timeout=60) as source, talloc.open('wb') as target:
            total = 0
            while chunk := source.read(1024 * 1024):
                total += len(chunk)
                require(total <= 16 * 1024 * 1024, 'talloc source exceeds the reviewed bound')
                target.write(chunk)
    require(sha256(talloc) == TALLOC_SHA256, 'talloc source SHA-256 mismatch')
    extract(proot_archive, work)
    extract(talloc, work)
    proot = work / 'proot'
    run(['git', 'init', proot])
    run(['git', '-C', proot, 'config', 'core.autocrlf', 'false'])
    run(['git', '-C', proot, 'add', '--all'])
    require(run(['git', '-C', proot, 'write-tree'], capture=True).strip() == PROOT_TREE,
            'Extracted PRoot tree differs from its pinned Git identity')
    # git apply accepts an exported source tree; no mutation of the input Git
    # repository occurs. Validate every exact patch before applying it.
    for name in PATCH_NAMES:
        run(['git', 'apply', '--check', PATCHES / name], cwd=proot)
        run(['git', 'apply', PATCHES / name], cwd=proot)
    require('--sysvipc' in (proot / 'src/cli/proot.h').read_text(),
            'Pinned PRoot lacks the required SysV IPC option')
    require('proot-sysvshm' in (proot / 'src/extension/sysvipc/sysvipc_shm.c').read_text(),
            'memfd SysV shared-memory patch missing')
    return proot, work / 'talloc-2.4.3', sources


def toolchain(target, ndk):
    require(sys.platform == 'linux', 'Build PRoot on a Linux host')
    tools = {}
    if target == 'android-arm64':
        if ndk is None:
            value = os.environ.get('ANDROID_NDK_HOME') or os.environ.get('ANDROID_NDK_ROOT')
            if value:
                ndk = Path(value)
            elif os.environ.get('ANDROID_HOME'):
                ndk = Path(os.environ['ANDROID_HOME']) / 'ndk' / NDK_VERSION
        require(ndk is not None, 'Supply --ndk or ANDROID_NDK_HOME for the pinned Android NDK')
        ndk = ndk.resolve()
        require(re.search(r'^Pkg\.Revision\s*=\s*' + re.escape(NDK_VERSION) + r'\s*$',
                          (ndk / 'source.properties').read_text(), re.M), 'Android NDK revision mismatch')
        require(platform.machine() in ('x86_64', 'AMD64'), 'This NDK package requires a Linux x86_64 build host')
        folder = ndk / 'toolchains/llvm/prebuilt/linux-x86_64/bin'
        names = {'CC': 'aarch64-linux-android26-clang', 'AR': 'llvm-ar', 'RANLIB': 'llvm-ranlib',
                 'STRIP': 'llvm-strip', 'OBJCOPY': 'llvm-objcopy', 'OBJDUMP': 'llvm-objdump', 'READELF': 'llvm-readelf'}
        tools = {key: str(folder / name) for key, name in names.items()}
    else:
        require(platform.machine().lower() in ('aarch64', 'arm64'), 'Linux guest smoke must build on native ARM64')
        for key, name in {'CC': 'cc', 'AR': 'ar', 'RANLIB': 'ranlib', 'STRIP': 'strip',
                          'OBJCOPY': 'objcopy', 'OBJDUMP': 'objdump', 'READELF': 'readelf'}.items():
            tools[key] = shutil.which(name)
    require(all(value and Path(value).is_file() for value in tools.values()), 'Required native build tool is missing')
    return tools


def compile_sources(proot, talloc, work, target, tools, jobs):
    prefix = work / 'talloc-prefix'
    env = dict(os.environ, **tools, SOURCE_DATE_EPOCH=SOURCE_DATE_EPOCH,
               CFLAGS='-O2 -fPIC', LDFLAGS='-Wl,-z,max-page-size=16384')
    configure = ['./configure', '--prefix=' + str(prefix), '--disable-rpath', '--disable-python']
    if target == 'android-arm64':
        answers = talloc / 'coh-cross-answers.txt'
        shutil.copy2(PATCHES / 'talloc-android-cross-answers.txt', answers)
        configure += ['--cross-compile', '--cross-answers=' + str(answers)]
    run(configure, cwd=talloc, env=env)
    if target == 'android-arm64':
        require(answers.read_bytes() == (PATCHES / 'talloc-android-cross-answers.txt').read_bytes(),
                'talloc requested cross answers outside the pinned configuration')
    run(['make', '-j' + str(jobs)], cwd=talloc, env=env)
    (prefix / 'include').mkdir(parents=True)
    (prefix / 'lib').mkdir()
    shutil.copy2(talloc / 'talloc.h', prefix / 'include/talloc.h')
    objects = sorted((talloc / 'bin/default').glob('talloc*.o'))
    require(objects, 'talloc build did not produce allocator objects')
    run([tools['AR'], 'rcs', prefix / 'lib/libtalloc.a', *objects], env=env)
    run(['make', '-C', proot / 'src', '-j' + str(jobs), 'CC=' + tools['CC'],
         'LD=' + tools['CC'] + ' -Wl,-z,max-page-size=16384',
         'STRIP=' + tools['STRIP'], 'OBJCOPY=' + tools['OBJCOPY'], 'OBJDUMP=' + tools['OBJDUMP'],
         'CPPFLAGS=-D_FILE_OFFSET_BITS=64 -D_GNU_SOURCE -I. -I' + str(proot / 'src') + ' -I' + str(prefix / 'include'),
         'LDFLAGS=-L' + str(prefix / 'lib') + ' -ltalloc -Wl,-z,noexecstack,-z,max-page-size=16384',
         'PROOT_UNBUNDLE_LOADER=/unused', 'HAS_LOADER_32BIT='], env=env)


def elf_record(path, tools, android):
    header = path.read_bytes()[:64]
    require(header[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<H', header, 18)[0] == 183,
            'Native launcher output is not little-endian ARM64 ELF64: ' + path.name)
    dynamic = run([tools['READELF'], '-dW', path], capture=True)
    needed = re.findall(r'\(NEEDED\).*?\[([^\]]+)\]', dynamic)
    require(not any('talloc' in item for item in needed), 'PRoot must statically link the pinned talloc library')
    program = run([tools['READELF'], '-lW', path], capture=True)
    interp = re.findall(r'Requesting program interpreter:\s*([^\]]+)', program)
    alignments = [int(line.split()[-1], 16) for line in program.splitlines() if line.lstrip().startswith('LOAD ')]
    require(alignments and all(value >= 16384 for value in alignments),
            'Native launcher LOAD segments must preserve the requested 16 KB alignment')
    if android and path.name == 'libproot.so':
        require(interp == ['/system/bin/linker64'], 'Android PRoot must use the system ARM64 interpreter')
        require(set(needed) <= {'libc.so', 'libdl.so', 'libm.so', 'liblog.so'}, 'Unexpected Android shared dependency')
    return dict(record(path), elf_machine='aarch64', needed=needed, interpreter=interp,
                load_segment_alignment=alignments)


def source_bundle(output, sources, proot, talloc, receipt):
    notices = output / 'licenses'
    notices.mkdir()
    shutil.copy2(proot / 'COPYING', notices / 'PRoot-COPYING')
    # talloc's full archive includes library and bundled configure-tool notices;
    # expose its root license files and library header separately as well.
    for path in sorted(talloc.iterdir()):
        if path.is_file() and (path.name.startswith(('COPYING', 'LICENSE')) or path.name == 'talloc.h'):
            shutil.copy2(path, notices / ('talloc-' + path.name))
    bundle = output / 'proot-corresponding-sources.tar.gz'
    with tarfile.open(bundle, 'w:gz') as archive:
        for path in sorted(sources.iterdir()):
            archive.add(path, arcname='sources/' + path.name)
        archive.add(Path(__file__), arcname='recipe/tools/android/build_proot.py')
        archive.add(PATCHES, arcname='recipe/android/native/proot')
    receipt['corresponding_sources'] = dict(record(bundle), file=bundle.name,
        scope='Original complete PRoot tree and talloc archive, exact build script, patches and attribution')
    receipt['license_files'] = {p.name: record(p) for p in sorted(notices.iterdir())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=('android-arm64', 'linux-arm64'), required=True)
    parser.add_argument('--ndk', type=Path)
    parser.add_argument('--work', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'out/android/native')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--proot-checkout', type=Path, help='Read-only existing Git repository containing the exact pin')
    parser.add_argument('--talloc-archive', type=Path, help='Use a local copy; mandatory pinned SHA-256 still applies')
    parser.add_argument('--prepare-only', action='store_true', help='Verify/export/patch source only; does not claim a native build')
    args = parser.parse_args()
    require(1 <= args.jobs <= 32, '--jobs must be between 1 and 32')
    work = (args.work or ROOT / ('out/android/proot-build-' + args.target)).resolve()
    require(not work.exists(), 'PRoot work directory must be new: ' + str(work))
    output = args.output.resolve() / ('arm64-v8a' if args.target == 'android-arm64' else 'linux-arm64')
    require(not output.exists(), 'PRoot output target directory must be new: ' + str(output))
    tools = None if args.prepare_only else toolchain(args.target, args.ndk)
    work.mkdir(parents=True)
    proot, talloc, sources = prepare(work, args.proot_checkout, args.talloc_archive)
    receipt = {'schema_version': 1, 'target': args.target, 'source_commit': PROOT_COMMIT,
        'source_tree': PROOT_TREE, 'source_url': PROOT_URL,
        'sources': {p.name: record(p) for p in sorted(sources.iterdir())},
        'talloc_version': '2.4.3', 'talloc_source_url': TALLOC_URL,
        'patches': {name: record(PATCHES / name) for name in PATCH_NAMES},
        'recipe_sha256': sha256(Path(__file__)),
        'android_cross_answers_sha256': sha256(PATCHES / 'talloc-android-cross-answers.txt'),
        'optional_acceleration_patch': False, 'sysvipc_memfd_patch': True,
        'runtime_validation': 'unverified', 'status': 'source_prepared_only', 'files': {}}
    if not args.prepare_only:
        compile_sources(proot, talloc, work, args.target, tools, args.jobs)
        output.mkdir(parents=True)
        pairs = {'libproot.so': proot / 'src/proot', 'libproot-loader.so': proot / 'src/loader/loader'} if args.target == 'android-arm64' else {
                 'proot': proot / 'src/proot', 'proot-loader': proot / 'src/loader/loader'}
        for name, source in pairs.items():
            target = output / name
            shutil.copy2(source, target)
            target.chmod(0o755)
            run([tools['STRIP'], target])
            receipt['files'][name] = elf_record(target, tools, args.target == 'android-arm64')
        receipt.update(status='native_built_runtime_unverified',
            compiler=run([tools['CC'], '--version'], capture=True).splitlines()[0],
            ndk_version=NDK_VERSION if args.target == 'android-arm64' else None,
            android_api=26 if args.target == 'android-arm64' else None,
            max_page_size=16384, talloc_linkage='static')
    else:
        output.mkdir(parents=True)
    source_bundle(output, sources, proot, talloc, receipt)
    (output / 'proot-build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'status': receipt['status'], 'target': args.target, 'output': str(output)}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError) as error:
        print('PRoot build failed: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
