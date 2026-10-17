#!/usr/bin/env python3
"""Independent read-only byte inspection of the exact retained runtime capture.

This intentionally does not import the snapshot-admission or C decoder modules.
No graph publication is authorized. Reachability/CRCs are replayed by the pinned
native original-source checker, not inferred from this binary envelope parser.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import zipfile

PINS = {
 'capture/catalog.cohcat': (12179670, '61c9408b02e366fa487acc857ffb89cde5d431e7dfcc2b2e01ecd0446bea3763'),
 'capture/runtime.cohrts': (6585, 'c262be9797ad03ce0dfe02ec5afd7d44bae8144d19f2a25dacdc310ada33bb02'),
 'capture/source-identity.json': (5032, 'a5517f1ca0c5f1ce8aa2c39bfa70f76d0c913ef9a27634c16ad361b3770ff3f0'),
 'capture/run-identity.json': (535, '2e3b459686f769ac18519e7ec93cecff691854411c8c5dd7db70a62182868588'),
}

def inspect(archive):
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        payloads = {name: z.read(name) for name in PINS}
    for name, (size, sha) in PINS.items():
        assert len(payloads[name]) == size
        assert hashlib.sha256(payloads[name]).hexdigest() == sha
    data = payloads['capture/runtime.cohrts']
    at = 0
    def take(n):
        nonlocal at
        assert n >= 0 and n <= len(data) - at
        result = data[at:at+n]; at += n
        return result
    def ints(n):
        return struct.unpack('<' + 'I'*n, take(n*4))
    def string(n):
        value = take(n)
        assert n >= 2 and value[-1] == 0 and 0 not in value[:-1]
        return value[:-1].decode('ascii')
    assert take(8) == b'COHRTS01'
    h = ints(18)
    assert h == (1,80,6585,20261016,12179670,508,40225,40225,130314,33,33,7,3173822562,3649375123,0,0,0,0)
    roots = []
    for i in range(h[9]):
        index,present,kind,file,slot,n,bits,count = ints(8)
        assert index == i and present == 1 and kind == 1
        name = string(n)
        matrix = struct.unpack('<12f',take(48))
        assert all(math.isfinite(f) for f in matrix)
        wire = take(count)
        assert bits == count*8 and count <= 256
        roots.append(dict(index=index,name=name,file=file,slot=slot,
                          matrix_columns=[matrix[j:j+3] for j in range(0,12,3)],
                          encoded_matrix_sha256=hashlib.sha256(wire).hexdigest()))
    external = []
    for i in range(h[11]):
        index,source_id,flags,model,n,bits,count,lookup,path_n = ints(9)
        assert index == i and source_id == 0 and flags == 15 and model == lookup == path_n == 0
        live = take(60); cached = take(60)
        assert all(v == 0 for v in cached)
        name = string(n)
        wire = take(count)
        assert bits == count*8 and wire
        external.append(dict(index=index,name=name,source_id=source_id,flags=flags,
                             live_bounds_hex=live.hex(),cached_bounds_lookup=False,
                             model_present=False,library_path='',
                             wire_bytes=count,wire_sha256=hashlib.sha256(wire).hexdigest()))
    assert at == len(data)
    assert len({row['name'] for row in external}) == 7
    return dict(schema='coh-independent-retained-envelope-review-v1',passed=True,
                byte_pins={name:dict(bytes=size,sha256=sha) for name,(size,sha) in PINS.items()},
                root_records=roots,external_records=external,
                scope='byte envelope, raw finite matrices, exact names, captured ownership fields; native decoder replay separately verifies packed matrices, graph reachability and both CRCs',
                live_groups_transaction=False,graph_publication_authorized=False,world_authority=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    result=inspect(args.archive)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,roots=len(result['root_records']),external=len(result['external_records']))))
