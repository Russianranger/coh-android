#!/usr/bin/env python3
"""Build a read-only PE32 observer from exact unchanged sink path functions."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import delivery as d

HERE = Path(__file__).resolve().parent
SINK_SHA256 = '7bbaeaa669e652fea58e926250cff19a6c6eec5f234599842ffc9ae41c623f2d'


def original_path_functions(raw):
    d.require(d.digest(raw) == SINK_SHA256, 'SINK_SOURCE_IDENTITY')
    text = raw.decode('ascii')
    cap = '#define COH_CATALOG_SINK_PATH_MAX 240u\n'
    d.require(text.count(cap) == 1, 'SINK_PATH_CAP')
    begin = text.index('static int coh_catalog_sink_reserved(')
    end = text.index('/* Called only by the opt-in staged normal-map startup hook', begin)
    functions = text[begin:end]
    d.require(functions.count('static int ') == 2 and 'coh_catalog_sink_path(' in functions,
              'SINK_PATH_FUNCTIONS')
    return cap + functions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default='i686-w64-mingw32-gcc')
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    d.require(not args.binary.exists() and not args.output.exists(), 'EXISTING_OUTPUT')
    sink = (HERE/'source_sink.inc').read_bytes()
    functions = original_path_functions(sink)
    with tempfile.TemporaryDirectory(prefix='coh-path-probe-') as temporary:
        directory = Path(temporary)
        (directory/'sink-path-original.inc').write_text(functions)
        binary = directory/'catalog-path-probe.exe'
        command = [args.cc, '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                   '-I'+str(directory), str(HERE/'path_probe.c'), '-o', str(binary)]
        subprocess.run(command, check=True)
        raw = d.read(binary, 1024*1024)
        d.require(raw[:2] == b'MZ', 'PE_BINARY')
        pe = int.from_bytes(raw[60:64], 'little')
        d.require(raw[pe:pe+4] == b'PE\0\0' and raw[pe+4:pe+6] == b'\x4c\x01'
                  and raw[pe+24:pe+26] == b'\x0b\x01', 'PE32_I386')
        args.binary.parent.mkdir(parents=True, exist_ok=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.binary.open('xb') as stream: stream.write(raw)
        d.emit_json(args.output, {'schema':'coh-win32-catalog-path-build-v1', 'compiled':True,
            'runtime_executed':False, 'read_only':True, 'command':command,
            'source_sha256':{name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                             for name in ('build_path_probe.py','path_probe.c','source_sink.inc')},
            'original_path_functions_sha256':d.digest(functions.encode()),
            'binary':{'bytes':len(raw),'sha256':d.digest(raw),'machine':'I386','format':'PE32'}})
    print(json.dumps({'compiled':True,'runtime_executed':False,'binary_sha256':d.digest(raw)}))


if __name__ == '__main__': main()
