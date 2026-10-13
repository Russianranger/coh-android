#!/usr/bin/env python3
"""Qualify all real Wretch meshes against the retained original scalar decoder.

Only pinned, bounded, decoded source streams reach the original host function.
The unchanged Phase 6 host shim supplies delta, weight and GPU UV expressions.
This validates the legacy v2 head as well as the v3 parts, including rigid and
fully weighted endpoints. It does not execute the original complete client.
"""
from pathlib import Path
import argparse, ctypes as C, importlib.util, json, shlex, struct, subprocess, tempfile
import geo

PARTS=(('pants','GEO_Hips_Wretch',0),('shirt','GEO_Chest_Wretch',2),
    ('head','GEO_Head_Wretch',4),('glove','GEO_LarmL_Wretch',10),
    ('boot','GEO_LlegR_Wretch',25),('boot','GEO_LlegL_Wretch',26),
    ('belt','GEO_Belt_Wretch',34),('hair','GEO_Hair_Jack',43),
    ('neck','GEO_Neck_Wretch',3),('sleeves','GEO_Sleeves_Wretch',72),
    ('spadr','GEO_Spadr_Wretch',47))
spec=importlib.util.spec_from_file_location('accepted_original_delta',Path(__file__).resolve().parents[1]/'material_fixture/original_delta_check.py')
original=importlib.util.module_from_spec(spec); spec.loader.exec_module(original)

def check(corpus,source,compiler='cc'):
    pins=json.loads(Path(__file__).with_name('pins.json').read_text())
    byname={r['file_name']:r for r in pins['records']}
    code=original.original_c(source); results=[]
    with tempfile.TemporaryDirectory(prefix='coh-character-original-delta-') as temp:
        p=Path(temp); (p/'oracle.c').write_bytes(code)
        subprocess.run([*shlex.split(compiler),'-std=c11','-O0','-fno-strict-aliasing',
            '-fPIC','-shared','-o',str(p/'oracle.so'),str(p/'oracle.c')],check=True)
        lib=C.CDLL(str(p/'oracle.so'))
        lib.uncompressDeltas.argtypes=[C.c_void_p,C.POINTER(C.c_uint8),C.c_int,C.c_int,C.c_int]
        lib.uncompressDeltas.restype=C.c_int
        lib.original_gpu_uvs.argtypes=[C.POINTER(C.c_float),C.c_int,C.POINTER(C.c_float)]
        lib.original_weight_slots.argtypes=[C.POINTER(C.c_uint8),C.POINTER(C.c_uint8),C.c_int,C.c_int,C.POINTER(C.c_float),C.POINTER(C.c_uint32)]
        lib.original_weight_slots.restype=C.c_int
        for file,name,socket in PARTS:
            raw=(corpus/(file+'.geo')).read_bytes()
            geo.require(geo.sha(raw)==byname[file+'.geo']['sha256'],'source GEO identity differs')
            canonical,vertices,bones,meta=geo.mesh(raw,name,socket)
            version,data,models=geo.records(raw); rec=next(x for x in models if x['index']==meta['index'])
            def stream(index):
                packed,unpacked,offset=rec['packs'][index]; b=geo.span(data,offset,packed or unpacked)
                return geo.inflate(b,unpacked) if packed else b
            vc,tc=meta['vertex_count'],meta['triangle_count']; checks=[]
            for channel,index,count,stride,kind in [('indices',0,tc,3,1),('positions',1,vc,3,0),('normals',2,vc,3,0),('uvs',3,vc,2,0)]:
                src=stream(index); py=geo.accepted.decode_delta(src,count,stride,kind==0)
                expected=struct.pack('<'+('f' if kind==0 else 'I')*len(py),*py)
                mem=(C.c_uint8*(len(src)+16))(); C.memmove(mem,src,len(src))
                output=(C.c_uint8*len(expected))(); consumed=lib.uncompressDeltas(output,mem,stride,count,kind)
                geo.require(consumed==len(src) and bytes(output)==expected,'original '+channel+' byte parity differs')
                if channel=='indices':target=canonical[64+vc*48:64+vc*48+tc*12]
                elif channel=='uvs':
                    inp=(C.c_float*(vc*2)).from_buffer_copy(bytes(output)); gpu=(C.c_float*(vc*2))()
                    lib.original_gpu_uvs(inp,vc,gpu); expected=bytes(gpu)
                    target=b''.join(canonical[64+i*48+24:64+i*48+32] for i in range(vc))
                else:
                    offset=0 if channel=='positions' else 12
                    target=b''.join(canonical[64+i*48+offset:64+i*48+offset+12] for i in range(vc))
                geo.require(target==expected,'canonical '+channel+' byte parity differs')
                checks.append({'channel':channel,'elements':count*stride,'byte_exact':True})
            weights,mats=stream(5),stream(6)
            geo.require(len(weights)==vc and len(mats)==vc*2,'skin channel source lengths differ')
            w=(C.c_uint8*vc).from_buffer_copy(weights); m=(C.c_uint8*(vc*2)).from_buffer_copy(mats)
            wf=(C.c_float*(vc*2))(); slots=(C.c_uint32*(vc*2))()
            geo.require(lib.original_weight_slots(w,m,vc,len(bones),wf,slots)==0,'original skin slot semantics failed')
            geo.require(bytes(wf)==b''.join(canonical[64+i*48+32:64+i*48+40] for i in range(vc)),'original weights differ')
            geo.require(bytes(slots)==b''.join(canonical[64+i*48+40:64+i*48+48] for i in range(vc)),'original palette rows differ')
            checks.extend([{'channel':'weights','elements':vc*2,'byte_exact':True},
                {'channel':'palette_slots','elements':vc*2,'byte_exact':True}])
            results.append({'model':name,'source_geo_version':version,'vertices':vc,'triangles':tc,
                'source_geo_sha256':geo.sha(raw),'canonical_sha256':geo.sha(canonical),'checks':checks})
    return {'format':1,'passed':True,'oracle':'unchanged original uncompressDeltas with retained host shims',
        'source_sha256_lf':original.SOURCE_SHA,'function_sha256_lf':original.FUNCTION_SHA,
        'original_client_execution':False,'mesh_count':len(results),'meshes':results,
        'vertices':sum(x['vertices'] for x in results),'triangles':sum(x['triangles'] for x in results),
        'channel_checks':sum(len(x['checks']) for x in results),
        'scalar_elements':sum(c['elements'] for x in results for c in x['checks'])}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--corpus',type=Path,required=True)
    ap.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[3]/'upstream/ouroboros/Common/seq/anim.c')
    ap.add_argument('--compiler',default='cc'); ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args(); result=check(a.corpus,a.source,a.compiler)
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='meshes'},indent=2))

if __name__=='__main__':main()
