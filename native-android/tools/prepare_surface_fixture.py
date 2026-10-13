#!/usr/bin/env python3
"""Package one real DDS and its original-SDK-qualified RGBA for the Android proof."""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
FIXTURE='01-chest_5c_night_chest_01'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--corpus',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--library',type=Path);a=p.parse_args()
    pins=json.loads((ROOT/'tools/corpus/pins.json').read_text());pin=next(r for r in pins['records'] if r['id']==FIXTURE)
    data=(a.corpus/(FIXTURE+'.dds')).read_bytes()
    if sha(data)!=pin['dds_sha256']:raise SystemExit('Fixture differs from qualified source pin')
    evidence=json.loads((ROOT/'evidence/phase4/comparison.json').read_text());cid=sha(data)[:20]+'-mip0';gold=next(r for r in evidence['real']['records'] if r['id']==cid)
    if not gold['passed'] or gold['native_sha256']!=gold['reference_sha256']:raise SystemExit('Original SDK qualification missing')
    library=a.library
    if library is None:
        build=ROOT/'results/surface-fixture-core'
        subprocess.run([sys.executable,str(ROOT/'tools/build.py'),'--output',str(build)],check=True,stdout=subprocess.DEVNULL)
        library=build/'libcoh_native_core.so'
    lib=C.CDLL(str(library.resolve()));fn=lib.coh_dds_rgba_legacy;fn.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.c_void_p,C.c_size_t]
    buf=C.create_string_buffer(data);rgba=C.create_string_buffer(gold['reference_bytes'])
    if fn(buf,len(data),0,rgba,len(rgba))!=0:raise SystemExit('CPU decode failed')
    raw=rgba.raw
    if sha(raw)!=gold['reference_sha256']:raise SystemExit('Decoded bytes differ from original Windows SDK golden hash')
    a.output.mkdir(parents=True,exist_ok=True)
    meta={'format':1,'name':'Night Chest real CoH texture','fixture_id':FIXTURE,'source_path':pin['source_path'],'release_tag':pins['release_tag'],'dds_sha256':sha(data),'dds_bytes':len(data),'expected_rgba_sha256':sha(raw),'expected_rgba_bytes':len(raw),'width':gold['width'],'height':gold['height'],'dds_format':'DXT5','mip':0,'decoder':'coh_dds_rgba_legacy','golden_origin':'Pinned original Win32 NVIDIA nvDXTlibMT_S plus raw CPU consumer channel conversion','qualification_commit':evidence['source_commit'],'qualification_run':evidence['original_run'],'sdk_library_sha256':evidence['sdk_library_sha256'],'native_generator_library_sha256':sha(library.read_bytes()),'whole_asset_archive_hash_verified':False,'wrapper_manifest_hash_verified':True}
    (a.output/'fixture.dds').write_bytes(data);(a.output/'fixture.rgba').write_bytes(raw);(a.output/'fixture.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
