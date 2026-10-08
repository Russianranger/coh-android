#!/usr/bin/env python3
"""Build only the KGSL Vulkan ICD and finite native device probe in Bookworm."""
import argparse
import hashlib
import json
import pathlib
import platform
import subprocess
import tarfile
import urllib.request


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


def unpack(path, output):
    # Authenticated upstream archives may contain ordinary source symlinks.
    # Python's data filter confines those links, paths and metadata to this build.
    with tarfile.open(path) as archive:
        archive.extractall(output, filter='data')


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
        unpack(path, work)
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
    # Mesa's copyright notice is retained verbatim; the compiler stays in the image.
    notices = (work / 'mesa-26.0.0/COPYING').read_text()
    (args.output / 'THIRD_PARTY_NOTICES.md').write_text(
        '# Mesa Turnip 26.0.0\n\nSource: ' + lock['mesa']['url'] + '\n\n' + notices)
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
