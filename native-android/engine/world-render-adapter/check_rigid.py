#!/usr/bin/env python3
"""Rigid GEOv8 source-layout/delta/ownership qualification. No world admission."""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import zlib
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def run(command,**kwargs):
    p=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=180,**kwargs)
    if p.returncode:raise ValueError(p.stdout+p.stderr)
    return p.stdout

def producer_layout(temp):
    pins=json.loads((HERE/'rigid-source-pins.json').read_text())['source_sha256']
    for p,want in pins.items():
        if sha(ROOT/p)!=want:raise ValueError('Original producer source drift: '+p)
    source=(ROOT/'upstream/ouroboros/Utilities/GetVrml/src/output.c').read_text()
    a=source.index('typedef struct _ModelFormatOnDisk_v8');b=source.index('} ModelFormatOnDisk_v8;',a)+len('} ModelFormatOnDisk_v8;')
    original=source[a:b]
    anim=(ROOT/'upstream/ouroboros/Common/seq/anim.h').read_text();a=anim.index('typedef struct PackData');b=anim.index('} PackData;',a)+len('} PackData;');pack=anim[a:b]
    grid=(ROOT/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/components/gridpoly.h').read_text();a=grid.index('typedef struct\n{');b=grid.index('} PolyGrid;',a)+len('} PolyGrid;');grid=grid[a:b]
    prefix='typedef unsigned char U8;typedef unsigned int U32;typedef short S16;typedef float F32;typedef float Vec3[3];typedef struct BoneInfo BoneInfo;typedef struct TexID TexID;typedef struct AltPivotInfo AltPivotInfo;typedef struct PolyCell PolyCell;\n'
    names=['struct_size','radius','tex_count','boneinfo','vert_count','tri_count','reflection_quad_count','tex_idx','grid','name','api','scale','pack','lod_distances','id']
    code=prefix+pack+'\n'+grid+'\n'+original+'\nconst unsigned int offsets[]={sizeof(ModelFormatOnDisk_v8),'+','.join('__builtin_offsetof(ModelFormatOnDisk_v8,'+n+')' for n in names)+'};\n'
    path=temp/'producer.c';path.write_text(code)
    # Compile unchanged original producer structures using true32-bit pointer
    # layout. No multilib C runtime is needed; this object is never executed.
    run(['cc','-m32','-std=c11','-Wall','-Wextra','-Werror','-c',path,'-o',temp/'producer.o'])
    run(['objcopy','-O','binary','--only-section=.rodata',temp/'producer.o',temp/'producer.bin'])
    observed=list(struct.unpack('<16I',(temp/'producer.bin').read_bytes()))
    expected=[244,0,4,8,12,16,20,24,28,32,64,68,72,108,228,240]
    if observed!=expected:raise ValueError('Original32-bit GEOv8 producer layout differs')
    return {'source_sha256':pins,'original_structs_unchanged':True,'target_layout':'32-bit x86 object; no execution','fields':['sizeof',*names],'offsets':observed,'object_sha256':sha(temp/'producer.o')}

def delta_packet(temp,fixture):
    original=module('rigid_original_delta',ROOT/'native-android/tools/material_fixture/original_delta_check.py')
    code=original.original_c(ROOT/'upstream/ouroboros/Common/seq/anim.c');(temp/'original.c').write_bytes(code)
    run(['cc','-std=c11','-O0','-fno-strict-aliasing','-fPIC','-shared',temp/'original.c','-o',temp/'original.so'])
    lib=C.CDLL(str(temp/'original.so'));lib.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int]
    channels=[fixture.delta(fixture.INDICES,3,True),fixture.delta(fixture.POSITIONS,3),fixture.delta(fixture.NORMALS,3),fixture.delta(fixture.UV,2)]
    decoded=[]
    for index,stream in enumerate(channels):
        count=2 if index==0 else 4;stride=2 if index==3 else 3
        encoded=C.create_string_buffer(stream+b'\0'*16);out=C.create_string_buffer(count*stride*4)
        consumed=lib.uncompressDeltas(out,encoded,stride,count,int(index==0))
        if consumed!=len(stream):raise ValueError('Original delta byte consumption differs')
        decoded.append(struct.unpack('<'+('I' if index==0 else 'f')*(count*stride),out.raw))
    expected=bytearray()
    for part in range(2):
        for vertex in range(4):
            uv=decoded[3][vertex*2:vertex*2+2];scale=part+1
            values=[*decoded[1][vertex*3:vertex*3+3],*decoded[2][vertex*3:vertex*3+3],fixture.f32(uv[0]*scale),fixture.f32(fixture.f32(1-uv[1])*scale)]
            values += values[-2:]+[1.,1.,1.,1.]
            expected+=struct.pack('<14f',*values)
        expected+=struct.pack('<3I',*decoded[0][part*3:part*3+3])
    if (temp/'packet-release.bin').read_bytes()!=expected:raise ValueError('Rigid packet differs from original delta+independent UV/material partition oracle')
    for mode in ('address','undefined'):
        if (temp/('packet-'+mode+'.bin')).read_bytes()!=expected:raise ValueError('Sanitizer packet differs')
    return {'passed':True,'original_function_sha256_lf':original.FUNCTION_SHA,'encoded_channels':4,'source_decoded_elements':38,'partition_vertex_components':112,'partition_indices':6,'packet_sha256':hashlib.sha256(expected).hexdigest(),'source_geometry_fixture_only':True}

def actual_delta_packet(temp,path):
    pin=json.loads((HERE/'rigid-authentic-pins.json').read_text())
    if sha(path)!=pin['payload']['sha256'] or path.stat().st_size!=pin['payload']['bytes']:
        raise ValueError('Authenticv8 payload pin mismatch')
    raw=path.read_bytes();bias,zero,version,size=struct.unpack_from('<4I',raw)
    if zero or version!=8:raise ValueError('Authentic fixture version differs')
    header=zlib.decompress(raw[16:bias+4]);data=raw[bias+4:]
    if len(header)!=size:raise ValueError('Authentic fixture header size differs')
    payload,textures,names,materials=struct.unpack_from('<4I',header)
    if payload!=len(data):raise ValueError('Authentic fixture payload size differs')
    start=16+textures+names+materials+140
    record=header[start:];parts,bone,vertices,triangles=struct.unpack_from('<4I',record,8)
    if bone or vertices!=56 or triangles!=28 or parts!=1:raise ValueError('Authentic fixture model changed')
    decoded=[];lib=C.CDLL(str(temp/'original.so'));lib.uncompressDeltas.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int]
    for index in range(4):
        packed,unpacked,offset=struct.unpack_from('<3I',record,108+index*12)
        stream=data[offset:offset+(packed or unpacked)]
        if packed:stream=zlib.decompress(stream)
        if len(stream)!=unpacked:raise ValueError('Authentic stream size differs')
        stride=2 if index==3 else 3;count=triangles if index==0 else vertices
        encoded=C.create_string_buffer(stream+b'\0'*16);out=C.create_string_buffer(count*stride*4)
        if lib.uncompressDeltas(out,encoded,stride,count,int(index==0))!=len(stream):raise ValueError('Authentic original delta consumption differs')
        decoded.append(struct.unpack('<'+('I' if index==0 else 'f')*(count*stride),out.raw))
    expected=bytearray()
    for vertex in range(vertices):
        uv=decoded[3][vertex*2:vertex*2+2];v=struct.unpack('<f',struct.pack('<f',1-uv[1]))[0]
        expected+=struct.pack('<14f',*decoded[1][vertex*3:vertex*3+3],*decoded[2][vertex*3:vertex*3+3],uv[0],v,uv[0],v,1,1,1,1)
    expected+=struct.pack('<'+'I'*len(decoded[0]),*decoded[0])
    for mode in ('release','address','undefined'):
        if (temp/('actual-packet-'+mode+'.bin')).read_bytes()!=expected:raise ValueError('Authentic packet differs from original delta oracle')
    return {'passed':True,'payload_sha256':sha(path),'model':pin['model'],'vertices':vertices,'triangles':triangles,'channels':4,'scalar_components':vertices*8+triangles*3,'packet_sha256':hashlib.sha256(expected).hexdigest(),'material_fixture_only':True,'loaded_generation_fixture_only':True,'world_authority':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--actual-geo',type=Path);p.add_argument('--ndk',type=Path);p.add_argument('--android-output',type=Path);a=p.parse_args()
    sources=[HERE/'tests/test_rigid.c',HERE/'coh_wr_rigid.c',HERE.parent/'assets/coh_asset_loader.c',HERE.parent/'assets/coh_asset_geo.c',HERE.parent/'renderer/coh_renderer.c',ROOT/'native-android/src/coh_assets.c',ROOT/'native-android/src/coh_dds.c']
    pins=[*sources,HERE/'coh_wr_rigid.h',HERE/'check_rigid.py',HERE/'acquire_rigid.py',HERE/'tests/rigid_fixture.py',HERE/'rigid-source-pins.json',HERE/'rigid-authentic-pins.json',HERE/'tests/test_rigid_actual.c',HERE/'rigid_android_contract.py',HERE/'run_rigid_android.py',HERE/'tests/test_rigid_android.py',HERE.parent/'continuation/run_adapter_android.py',HERE.parent/'scenecatalog-qualification/common.py',HERE.parent/'assets/coh_asset_geo.h',HERE.parent/'assets/coh_asset_loader.h',HERE.parent/'renderer/coh_renderer.h',ROOT/'native-android/include/coh_native_core.h',ROOT/'native-android/src/byte_reader.h',HERE/'coh_world_render.h',HERE.parent/'coh_contracts.h',HERE.parent/'renderer/coh_renderer_shaders.h',ROOT/'native-android/tools/material_fixture/original_delta_check.py']
    pins.extend(ROOT/name for name in json.loads((HERE/'rigid-source-pins.json').read_text())['source_sha256'])
    revision=run(['git','-C',ROOT,'rev-parse','HEAD']).strip()
    tree=run(['git','-C',ROOT,'rev-parse','HEAD^{tree}']).strip()
    dirty=run(['git','-C',ROOT,'status','--porcelain','--untracked-files=no']).strip()
    untracked=run(['git','-C',ROOT,'ls-files','--others','--exclude-standard','--',*pins]).strip().splitlines()
    identities={str(f.relative_to(ROOT)):sha(f) for f in pins}
    fixture=module('rigid_fixtures',HERE/'tests/rigid_fixture.py')
    contract=module('rigid_android_contract',HERE/'rigid_android_contract.py')
    results={};android_builds={};replay_results={}
    with tempfile.TemporaryDirectory(prefix='coh-rigid-v8-') as work:
        temp=Path(work)
        for kind in ('valid','bone','scale','lightmap','weights','matidx','reflection','missing_uv','reflection_count','pivot','bad_index','duplicate_model'):(temp/(kind+'.geo')).write_bytes(fixture.geo(kind))
        fixture_bytes={kind+'.geo':fixture.geo(kind) for kind in contract.KINDS}
        if a.actual_geo:
            if sha(a.actual_geo)!=contract.ACTUAL_SHA:raise ValueError('Actual fixture hash mismatch')
            fixture_bytes['authentic.geo']=a.actual_geo.read_bytes()
        fixtures_sha={name:hashlib.sha256(raw).hexdigest() for name,raw in fixture_bytes.items()}
        generated=contract.digest_header(fixture_bytes);(temp/'rigid_fixture_digests.h').write_bytes(generated)
        flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-I',ROOT/'native-android/include']
        for mode,extra in [('release',['-O2']),('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
            binary=temp/mode
            run(['cc',*flags,*extra,*sources,'-Wl,--wrap=calloc,--wrap=malloc,--wrap=realloc,--wrap=free','-lz','-lm','-lcrypto','-pthread','-o',binary])
            result=json.loads(run([binary,temp,temp/('packet-'+mode+'.bin')],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
            if results and result!=results['release']['result']:raise ValueError('Mode result mismatch')
            results[mode]={'result':result,'binary_sha256':sha(binary)}
            if a.actual_geo:
                actual=temp/('actual-'+mode)
                run(['cc',*flags,*extra,HERE/'tests/test_rigid_actual.c',*sources[1:],'-lz','-lm','-lcrypto','-pthread','-o',actual])
                observed=json.loads(run([actual,a.actual_geo.resolve(),temp/('actual-packet-'+mode+'.bin')],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
                results[mode]['actual']={'result':observed,'binary_sha256':sha(actual)}
        producer=producer_layout(temp);delta=delta_packet(temp,fixture)
        authentic=actual_delta_packet(temp,a.actual_geo) if a.actual_geo else None
        specs={'authored':{'source':sources[0],'result':results['release']['result'],
                          'packet_sha256':delta['packet_sha256']}}
        if authentic:specs['authentic']={'source':HERE/'tests/test_rigid_actual.c',
                                        'result':results['release']['actual']['result'],
                                        'packet_sha256':authentic['packet_sha256']}
        for name,spec in specs.items():
            binary=temp/('replay-'+name)
            run(['cc',*flags,'-I',temp,'-DCOH_RIGID_FIXTURE_DIGEST','-O2',spec['source'],*sources[1:],
                 *(['-Wl,--wrap=calloc,--wrap=malloc,--wrap=realloc,--wrap=free'] if name=='authored' else []),
                 '-lz','-lm','-pthread','-o',binary])
            arguments=[temp,temp/('replay-'+name+'.packet')] if name=='authored' else [a.actual_geo.resolve(),temp/('replay-'+name+'.packet')]
            observed=json.loads(run([binary,*arguments]));contract.result(observed,name=='authentic')
            if observed!=spec['result'] or sha(arguments[-1])!=spec['packet_sha256']:raise ValueError('Digest replay differs from source-qualified host result')
            replay_results[name]={'binary_sha256':sha(binary),'result':observed,'packet_sha256':sha(arguments[-1])}
        if a.ndk:
            root=a.output.parent.resolve();output=(a.android_output or root/'android').resolve()
            if output!=root/'android':raise ValueError('Android artifact directory must be qualification parent/android')
            fixture_dir=root/'fixtures';fixture_dir.mkdir(parents=True,exist_ok=True)
            for name,raw in fixture_bytes.items():(fixture_dir/name).write_bytes(raw)
            (root/'rigid_fixture_digests.h').write_bytes(generated)
            fixtures_sha={name:hashlib.sha256(raw).hexdigest() for name,raw in fixture_bytes.items()}
            for abi,(triple,_) in contract.ABIS.items():
                directory=output/abi;directory.mkdir(parents=True,exist_ok=True);binaries={}
                for name,spec in specs.items():
                    binary=directory/('rigid-'+name+'-test')
                    run([a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/(triple+'-clang'),*flags,
                         '-I',temp,'-DCOH_RIGID_FIXTURE_DIGEST','-O2','-fPIE','-pie',spec['source'],*sources[1:],
                         *(['-Wl,--wrap=calloc,--wrap=malloc,--wrap=realloc,--wrap=free'] if name=='authored' else []),
                         '-lz','-lm','-pthread','-o',binary])
                    raw=binary.read_bytes()
                    if len(raw)<64 or raw[:7]!=b'\x7fELF\x02\x01\x01' or struct.unpack_from('<H',raw,18)[0]!=contract.ABIS[abi][1] or struct.unpack_from('<H',raw,16)[0]!=3:raise ValueError('Crosscompiler did not produce exact ABI PIE')
                    binaries[name]={'binary':binary.name,'binary_sha256':sha(binary),'executed':False,
                                    'expected_result':spec['result'],'expected_packet_sha256':spec['packet_sha256']}
                build={'schema':'coh-rigid-android-build-v1','passed':True,'abi':abi,'api':26,'executed':False,
                       'source_revision':revision,'source_tree':tree,'source_sha256':identities,
                       'fixtures_sha256':fixtures_sha,'fixture_digest_header_sha256':hashlib.sha256(generated).hexdigest(),
                       'digest_mode':'exact-fixture-byte-equality replay; not cryptographic execution',
                       'binaries':binaries,'world_authority':False}
                (directory/'build.json').write_text(json.dumps(build,indent=2)+'\n');android_builds[abi]=build
    if identities!={str(f.relative_to(ROOT)):sha(f) for f in pins}:raise ValueError('Source changed during qualification')
    receipt={'schema':'coh-rigid-v8-qualification-v1','passed':True,'source_revision':revision,'source_tree':tree,'clean_source_inputs':not bool(dirty or untracked),'source_inputs_unchanged':True,'source_sha256':identities,'modes':results,'producer_layout':producer,'delta_packet_oracle':delta,'host_fixture_digest_replay_qualified':True,'host_fixture_digest_replay':replay_results,'fixtures_sha256':fixtures_sha,'fixture_digest_header_sha256':hashlib.sha256(generated).hexdigest(),'leak_sanitizer':False,'android_built':bool(android_builds),'android_builds':android_builds,'android_executed':False,'authentic_geo_v8_fixture_available':bool(authentic),'authentic_geometry_oracle':authentic,'world_authority':False,'scope':'Additive source-pinned rigid-v8 CPU conversion and lifetime only; authored malformed controls and optional authentic geometry with fixture material/generation bindings. No texture upload or graph/actor/world admission.'}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'checks_per_mode':results['release']['result']['checks'],'world_authority':False}))
if __name__=='__main__':main()
