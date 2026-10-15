#!/usr/bin/env python3
"""Build only the KGSL Vulkan ICD and finite native device probe in Bookworm."""
import argparse
import hashlib
import json
import pathlib
import platform
import posixpath
import shutil
import subprocess
import tarfile
import urllib.request

MESA_LICENSE_FILES = ('docs/license.rst', 'licenses/Apache-2.0', 'licenses/BSL-1.0',
    'licenses/GPL-1.0-or-later', 'licenses/GPL-2.0-only', 'licenses/MIT',
    'licenses/SGI-B-2.0', 'licenses/exceptions/Linux-Syscall-Note')


def run(argv, cwd=None):
    subprocess.run(argv, cwd=cwd, check=True)


def download(pin, destination):
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(pin['url'], timeout=90) as response, destination.open('wb') as output:
        while data := response.read(1024 * 1024):
            total += len(data)
            if total > 96 * 1024 * 1024:
                raise ValueError('Oversized source archive')
            digest.update(data)
            output.write(data)
    if digest.hexdigest() != pin['sha256'] or ('bytes' in pin and total != pin['bytes']):
        raise ValueError('Pinned source archive differs')
    return dict(bytes=total, sha256=digest.hexdigest(), url=pin['url'])


def unpack(path, output, source_root):
    # Bookworm's Python lacks extractall(filter=...). Extract authenticated
    # source data explicitly, with links staged after all regular files.
    output = output.resolve()
    root = output / source_root
    if root.exists() or root.is_symlink():
        raise ValueError('Fresh source directory required')
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        if not 0 < len(members) <= 25000 or sum(m.size for m in members) > 512 * 1024 * 1024:
            raise ValueError('Excessive source archive expansion')
        names = {}
        for member in members:
            name = member.name.rstrip('/')
            parts = pathlib.PurePosixPath(name).parts
            if (not parts or parts[0] != source_root or name.startswith('/') or
                    '\\' in name or '\x00' in name or posixpath.normpath(name) != name or
                    any(part in ('.', '..') for part in name.split('/')) or
                    name in names or not (member.isreg() or member.isdir() or member.issym()) or
                    member.size < 0 or member.size > 64 * 1024 * 1024):
                raise ValueError('Unsafe source archive member')
            names[name] = member
        for name, member in names.items():
            for parent in pathlib.PurePosixPath(name).parents:
                if str(parent) in names and not names[str(parent)].isdir():
                    raise ValueError('Source archive descends through a file or link')
            if member.issym():
                target = member.linkname
                resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
                if (not target or target.startswith('/') or '\\' in target or '\x00' in target or
                        resolved.split('/')[0] != source_root or resolved not in names):
                    raise ValueError('Escaping or missing source archive link')
        for name, member in names.items():
            destination = output / name
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            elif member.isreg():
                destination.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, destination.open('xb') as target:
                    shutil.copyfileobj(source, target, length=1024 * 1024)
                if destination.stat().st_size != member.size:
                    raise ValueError('Truncated source archive member')
                destination.chmod(0o755 if member.mode & 0o111 else 0o644)
        for name, member in names.items():
            if member.issym():
                destination = output / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.symlink_to(member.linkname)


def mesa_notices(source, source_url):
    # Mesa 26 provides docs/license.rst and a finite licenses/ catalog instead
    # of a root COPYING file. Retain these upstream texts without modification.
    discovered = {path.relative_to(source).as_posix() for path in (source / 'licenses').rglob('*')
        if path.is_file() or path.is_symlink()}
    if discovered != set(MESA_LICENSE_FILES[1:]):
        raise ValueError('Pinned Mesa license catalog differs')
    parts = [('# Mesa Turnip 26.0.0\n\nSource: ' + source_url + '\n\n').encode()]
    total = 0
    for name in MESA_LICENSE_FILES:
        path = source / name
        if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= 64 * 1024:
            raise ValueError('Missing or unsafe pinned Mesa license text')
        data = path.read_bytes()
        data.decode('utf-8')
        total += len(data)
        if total > 128 * 1024:
            raise ValueError('Excessive Mesa license text')
        parts.extend([('## Upstream ' + name + '\n\n').encode(), data, b'\n\n'])
    return b''.join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    if platform.machine() != 'aarch64':
        raise ValueError('Actual ARM64/glibc build required')
    lock = json.loads(pathlib.Path('/src/lock.json').read_text())
    work = pathlib.Path('/build'); work.mkdir()
    args.output.mkdir()
    sources = {}
    for name in ('glslang', 'mesa'):
        path = work / (name + ('.tar.gz' if name == 'glslang' else '.tar.xz'))
        sources[name] = download(lock[name], path)
        unpack(path, work, name + '-' + lock[name]['version'])
    glslang = work / 'glslang-15.1.0'
    run(['cmake', '-S', str(glslang), '-B', '/build/glslang-build', '-G', 'Ninja',
         '-DCMAKE_BUILD_TYPE=Release', '-DENABLE_OPT=OFF', '-DBUILD_TESTING=OFF', '-DGLSLANG_TESTS=OFF'])
    run(['cmake', '--build', '/build/glslang-build', '--parallel', '2'])
    run(['cmake', '--install', '/build/glslang-build'])
    run(['meson', 'setup', '/build/mesa-build', '/build/mesa-26.0.0', *lock['mesa_options']])
    run(['ninja', '-C', '/build/mesa-build', '-j2'])
    driver = args.output / 'libvulkan_freedreno.so'
    driver.write_bytes((work / 'mesa-build/src/freedreno/vulkan/libvulkan_freedreno.so').read_bytes())
    probe = args.output / 'coh-vulkan-gpu-probe'
    run(['cc', *lock['probe_compile_args'], '/src/coh-vulkan-gpu-probe.c', '-o', str(probe), '-lvulkan'])
    run(['strip', str(driver), str(probe)])
    # The entire upstream license catalog is retained; the compiler stays in the image.
    (args.output / 'THIRD_PARTY_NOTICES.md').write_bytes(
        mesa_notices(work / 'mesa-26.0.0', lock['mesa']['url']))
    receipt = dict(format=1, architecture='aarch64', platform='linux',
        debian_image=lock['debian_image'], source_archives=sources,
        mesa_options=lock['mesa_options'], probe_compile_args=lock['probe_compile_args'],
        native_probe_source_sha256=hashlib.sha256(pathlib.Path('/src/coh-vulkan-gpu-probe.c').read_bytes()).hexdigest(),
        compiler=subprocess.check_output(['cc', '--version'], text=True).splitlines()[0],
        dpkg_packages=subprocess.check_output(['dpkg-query', '-W', '-f=${Package}:${Architecture}=${Version}\n'], text=True).splitlines(),
        build_tools=dict(meson=subprocess.check_output(['meson', '--version'], text=True).strip(),
            cmake=subprocess.check_output(['cmake', '--version'], text=True).splitlines()[0]),
        hardware_execution_validated=False, performance_validated=False)
    (args.output / 'container-build.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
