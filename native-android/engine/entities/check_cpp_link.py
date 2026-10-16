#!/usr/bin/env python3
"""Check real C++ linkage and unchanged C preprocessing against qualified base."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
BASE = '35870d6f14fe388b8d51b3fcb496cfad77676bbd'

def run(command):
    return subprocess.run([str(x) for x in command], check=True, capture_output=True, text=True).stdout

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    cc, cxx = os.environ.get('CC', 'cc'), os.environ.get('CXX', 'c++')
    with tempfile.TemporaryDirectory(prefix='coh-costume-cpp-') as name:
        directory = Path(name)
        evidence = HERE/'qualification/power-custom-20261016'
        native_receipt = json.loads((evidence/'host.json').read_text())
        previous = (evidence/'coh_costume-base.h').read_text()
        old_source = (HERE/'coh_costume.c').read_text()
        for relative, contents in [('coh_costume.h', previous), ('coh_costume.c', old_source)]:
            assert sha(contents.encode()) == native_receipt['source_sha256']['native-android/engine/entities/'+relative], 'Qualified base identity mismatch: '+relative
        preprocessed = []
        for variant, header in [('old', previous), ('current', (HERE/'coh_costume.h').read_text())]:
            folder = directory/variant
            folder.mkdir()
            (folder/'coh_costume.h').write_text(header)
            (folder/'coh_costume.c').write_text(old_source)
            preprocessed.append(run([cc, '-std=c99', '-E', '-P', '-I'+str(HERE), folder/'coh_costume.c']))
        assert preprocessed[0] == preprocessed[1], 'C preprocessing differs from qualified base'
        objects = []
        for source in [HERE/'coh_costume.c', HERE/'../replication/coh_replication.c']:
            obj = directory/(source.stem+'.o')
            run([cc, '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror', '-pedantic', '-c', source, '-o', obj])
            objects.append(obj)
        binary = directory/'cpp-link'
        run([cxx, '-std=c++11', '-Wall', '-Wextra', '-Werror', '-pedantic', HERE/'test_costume_cpp.cpp', *objects, '-lm', '-o', binary])
        run([binary])
        files = ['coh_costume.h', 'coh_costume.c', 'test_costume_cpp.cpp', 'check_cpp_link.py', '../replication/coh_replication.c', '../replication/coh_replication.h', 'coh_entities.h', '../coh_contracts.h', 'qualification/power-custom-20261016/coh_costume-base.h', 'qualification/power-custom-20261016/host.json']
        receipt = dict(passed=True, base=BASE, unchanged_c_preprocessing=True,
                       c_preprocessed_sha256=sha(preprocessed[0].encode()),
                       binary_sha256=sha(binary.read_bytes()),
                       cc=run([cc, '--version']).splitlines()[0], cxx=run([cxx, '--version']).splitlines()[0],
                       sources={str((HERE/f).resolve().relative_to(REPO)): sha((HERE/f).read_bytes()) for f in files},
                       scope='C++ linkage to separately C-compiled public APIs; no parser behavior change, Android execution or server acceptance')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2)+'\n')
        print(json.dumps(receipt, indent=2))

if __name__ == '__main__':
    main()
