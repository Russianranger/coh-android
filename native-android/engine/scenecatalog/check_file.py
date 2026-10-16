#!/usr/bin/env python3
"""Qualify standalone capture decoder against unchanged original source records."""
from pathlib import Path
import argparse
import ctypes as C
import hashlib
import json
import os
import subprocess
import shutil
import tempfile
import check as catalog

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def qualify(root, output, retained_binary=None):
    if output.exists() or output.is_symlink():
        raise ValueError('Output receipt must be new')
    if retained_binary is not None:
        if retained_binary.exists() or retained_binary.is_symlink() or any(p.is_symlink() for p in retained_binary.parents):
            raise ValueError('Retained binary must be new without linked ancestors')
    with tempfile.TemporaryDirectory(prefix='coh-catalog-file-') as temporary:
        work = Path(temporary)
        source_receipt, _ = catalog.prepare(root, work)
        library = C.CDLL(str(work/'catalog-original.so'))
        library.catalog_original.argtypes = [C.c_uint32]*4 + [C.c_void_p, C.POINTER(C.c_uint32),
            C.c_void_p, C.POINTER(C.c_uint32), C.c_void_p]
        payload = (C.c_uint8*(32<<20))(); wire = (C.c_uint8*(1<<20))()
        size = C.c_uint32(); bits = C.c_uint32(); counts = (C.c_uint32*7)()
        if library.catalog_original(2,1,0,0,payload,C.byref(size),wire,C.byref(bits),counts) != 0:
            raise ValueError('Original catalog producer failed')
        raw = bytes(payload[:size.value])
        valid = work/'valid.cohcat'; valid.write_bytes(raw)
        truncated = work/'truncated.cohcat'; truncated.write_bytes(raw[:-1])
        extra = work/'extra.cohcat'; extra.write_bytes(raw+b'\0')
        empty = work/'empty.cohcat'; empty.write_bytes(b'')
        oversized = work/'oversized.cohcat'
        with oversized.open('wb') as stream: stream.truncate((32<<20)+1)
        sources = [HERE/'validate_file.c', HERE/'coh_scenecatalog.c',
                   HERE.parent/'scenegraph/coh_scenegraph.c',
                   HERE.parent/'replication/coh_replication.c', HERE.parent/'replication/coh_groups.c']
        included = sources + [HERE/'coh_scenecatalog.h', HERE/'check_file.py',
                              HERE.parent/'scenegraph/coh_scenegraph.h',
                              HERE.parent/'replication/coh_replication.h',
                              HERE.parent/'replication/coh_groups.h', HERE.parent/'coh_contracts.h']
        environment = {**os.environ, 'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1', 'UBSAN_OPTIONS':'halt_on_error=1'}
        outcomes = {}
        for mode, flags in (
            ('release',['-O2']),
            ('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),
            ('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])):
            binary = work/mode
            command = [os.environ.get('CC','cc'), '-std=c99','-Wall','-Wextra','-Werror','-pedantic',
                       *flags,*sources,'-lm','-o',binary]
            catalog.run(command)
            result = json.loads(catalog.run([binary,valid,'7'],env=environment).stdout)
            if not result['native_decode_completed'] or result['definitions'] != 5:
                raise ValueError('Original rich source catalog did not decode')
            rejected = 0
            for path, generation in ((valid,'8'), (valid,'0'), (valid,'4294967296'),
                                     (valid,'-1'), (valid,'+7'), (valid,' 7'), (valid,''), (valid,'7x'),
                                     (truncated,'7'), (extra,'7'), (empty,'7'), (oversized,'7')):
                failure = subprocess.run([str(binary),str(path),generation], capture_output=True,
                                         text=True,env=environment,timeout=30)
                if failure.returncode != 2 or json.loads(failure.stdout)['native_decode_completed']:
                    raise ValueError('Malformed capture admitted')
                rejected += 1
            outcomes[mode] = {'source_rich_catalog':result,'malformed_rejections':rejected,
                              'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
                              'compiler_command':list(map(str,command))}
        proof = {'schema':1, 'passed':True, 'source_oracle':source_receipt,
                 'fixture_sha256':hashlib.sha256(raw).hexdigest(), 'checks':outcomes,
                 'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in included},
                 'server_executed':False,'authentic_capture':False,'android_executed':False,
                 'graph_published':False,'renderer_authorized':False,'leak_sanitizer':False}
        if retained_binary is not None:
            retained_binary.parent.mkdir(parents=True,exist_ok=True)
            with (work/'release').open('rb') as source, retained_binary.open('xb') as target:
                shutil.copyfileobj(source,target,64*1024)
                target.flush();os.fsync(target.fileno())
            retained_binary.chmod(0o700)
            actual = hashlib.sha256(retained_binary.read_bytes()).hexdigest()
            if actual != outcomes['release']['binary_sha256']:
                raise ValueError('Retained qualified binary hash differs')
            proof['retained_release_binary']={'sha256':actual, 'bytes':retained_binary.stat().st_size,
                                             'same_exact_executed_binary':True}
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('x') as target: json.dump(proof,target,indent=2);target.write('\n')
        return proof


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,default=ROOT)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--binary',type=Path,help='Retain the exact successfully tested release executable')
    parser.add_argument('--sanitize',action='store_true',help='Accepted for CI compatibility; ASan/UBSan always run')
    args=parser.parse_args()
    result=qualify(args.source_root.resolve(),args.output,args.binary)
    print(json.dumps({'passed':result['passed'],'modes':list(result['checks']),
                      'original_record_comparisons':result['source_oracle']['exact_record_comparisons']}))


if __name__=='__main__':main()
