#!/usr/bin/env python3
"""Recover exact character fixtures with bounded ZIP/HTTP range validation.

The reviewed Phase 6 range reader is reused without modifying its accepted tool.
Every source member has a pinned size, CRC and SHA-256. A full outer archive hash
is provenance only because this bounded reader deliberately acquires a subset.
"""
from pathlib import Path
import argparse, importlib.util, json, re, struct, zipfile, zlib, hashlib

RANGE_TOOL = Path(__file__).resolve().parents[1] / 'material_fixture/acquire.py'
spec = importlib.util.spec_from_file_location('accepted_material_ranges', RANGE_TOOL)
ranges = importlib.util.module_from_spec(spec); spec.loader.exec_module(ranges)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--use-verified-local',action='store_true',help='Reuse only exact size/CRC/SHA source matches')
    args=ap.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    pins=json.loads(Path(__file__).with_name('pins.json').read_text())
    readers={}; reused=[]
    for pin in pins['records']:
        existing=args.output/pin['file_name']
        if args.use_verified_local and existing.is_file():
            raw=existing.read_bytes()
            if len(raw)==pin['size'] and f'{zlib.crc32(raw):08x}'==pin['crc32'] and hashlib.sha256(raw).hexdigest()==pin['sha256']:
                reused.append(pin['id']); continue
        url=pin.get('outer_asset_url',pins['outer_asset_url'])
        member=pin.get('inner_member',pins['inner_member']); key=(url,member)
        if key not in readers:
            reader=ranges.HTTPRange(url,pin.get('outer_expected_bytes',pins['outer_expected_bytes']),8<<20)
            with zipfile.ZipFile(reader) as outer:
                stream=ranges.subzip(reader,outer.getinfo(member))
            if stream.size!=pin.get('inner_expected_bytes',pins['inner_expected_bytes']):
                raise ValueError('inner ZIP exact size differs')
            readers[key]=(reader,stream)
        reader,stream=readers[key]
        if not re.fullmatch(r'[a-z0-9]+\.(geo|texture|anim)',pin['file_name']):
            raise ValueError('unsafe fixture output name')
        if not 0<pin['size']<=2<<20 or pin['method'] not in (0,8):
            raise ValueError('oversized or unsupported fixture member')
        stream.seek(pin['offset']); header=stream.read(30)
        if header[:4]!=b'PK\x03\x04':raise ValueError('ZIP local signature differs')
        flags,method=struct.unpack_from('<HH',header,6)
        if flags&1 or method!=pin['method']:raise ValueError('ZIP encryption/method differs')
        nl,el=struct.unpack_from('<HH',header,26); name=stream.read(nl).decode('utf8')
        if name!=pin['name']:raise ValueError('ZIP local source identity differs')
        stream.seek(pin['offset']+30+nl+el); stored=stream.read(pin['compressed'])
        if len(stored)!=pin['compressed']:raise ValueError('truncated stored member')
        if pin['method']==8:
            dec=zlib.decompressobj(-15); raw=dec.decompress(stored,pin['size']+1)
            if not dec.eof or dec.unused_data or dec.unconsumed_tail:
                raise ValueError('compressed member envelope differs')
        else:raw=stored
        if len(raw)!=pin['size'] or f'{zlib.crc32(raw):08x}'!=pin['crc32'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:
            raise ValueError('fixture size, CRC32 or SHA256 differs')
        (args.output/pin['file_name']).write_bytes(raw)
        print(f'{pin["id"]}: {len(raw)} bytes SHA256 verified',flush=True)
    receipt=dict(pins); receipt.update(acquisition_passed=True,
        range_bytes_downloaded=sum(reader.total for reader,_ in readers.values()),
        range_count=sum(len(reader.requests) for reader,_ in readers.values()),
        etag_stable=True,exact_http_range_enforced=True,
        zip_member_crc32_verified=True,all_fixture_sha256_verified=True,
        locally_reused_after_size_crc_sha_verification=reused,
        ranges_by_archive={key[0]:reader.requests for key,(reader,_) in readers.items()})
    (args.output/'corpus.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':main()
