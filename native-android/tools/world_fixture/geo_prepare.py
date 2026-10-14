#!/usr/bin/env python3
"""Read the pinned v7 static bench and retain all original material partitions.

Disk offsets are integers; no x86 structs are cast to host pointers. Reviewed
Phase 6 stream bounds/delta arithmetic are reused, while v7's four-block header
and nine-pack model record are parsed explicitly. COHMESH1's one-bone identity
fields are a native static-geometry adapter, not a source character rig.
"""
from pathlib import Path
import ctypes as C, importlib.util, json, math, shlex, struct, subprocess, tempfile

ROOT=Path(__file__).resolve().parents[2]
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
accepted=module('world_accepted_material_prepare',ROOT/'tools/material_fixture/prepare.py')
require,span,u32,inflate,name_at=accepted.require,accepted.span,accepted.u32,accepted.inflate,accepted.name_at
f32,sha=accepted.f32,accepted.sha

def records(raw):
    require(16<=len(raw)<=2<<20,'world GEO size exceeds bound')
    biased,zero,version,unpacked=struct.unpack('<4I',span(raw,0,16))
    require(zero==0 and version==7 and 12<biased<len(raw)-4,'world GEO v7 envelope differs')
    header=inflate(span(raw,16,biased-12),unpacked)
    data=span(raw,biased+4,u32(header,0))
    require(biased+4+len(data)==len(raw),'world GEO trailing bytes differ')
    # anim.c geoLoad: v7+ removes the v2-v6 LOD block-size field.
    sizes=[u32(header,i*4) for i in range(4)];pos=16
    names=span(header,pos,sizes[1]);pos+=sizes[1]
    objects=span(header,pos,sizes[2]);pos+=sizes[2]
    texids=span(header,pos,sizes[3]);pos+=sizes[3]
    count=u32(header,pos+136);pos+=140
    require(0<count<=128,'world model count exceeds bound')
    texture_count=u32(names,0);require(0<texture_count<=128,'world texture count exceeds bound')
    namebase=4+texture_count*4
    textures=[name_at(names,namebase+u32(names,4+4*i)) for i in range(texture_count)]
    models=[]
    for index in range(count):
        size=u32(header,pos);require(size==232,'world v7 x86 model record size differs')
        record=span(header,pos,size);pos+=size
        require(u32(record,28)==0,'world disk PolyGrid cell is not null')
        name=name_at(objects,u32(record,60));vc,tc=struct.unpack_from('<2I',record,16)
        require(0<vc<=10000 and 0<tc<=10000,'world model cardinality exceeds bound')
        np=u32(record,8);require(0<np<=32,'world model partition count exceeds bound')
        materials=[];first=0
        for texid,triangles in struct.iter_unpack('<HH',span(texids,u32(record,24),np*4)):
            require(texid<len(textures) and triangles>0,'world material partition identity invalid')
            materials.append({'name':textures[texid],'texture_id':texid,
                'triangle_count':triangles,'first_triangle':first})
            first+=triangles
        require(first==tc,'world material partitions do not cover model')
        packs=[struct.unpack_from('<3I',record,104+i*12) for i in range(9)]
        for packed,decoded,offset in packs:
            require(decoded<=4<<20 and (not packed or decoded),'world stream size exceeds bound')
            span(data,offset,packed or decoded)
        scale=list(struct.unpack_from('<3f',record,68))
        require(all(math.isfinite(x) and 0<x<10 for x in scale),'world model scale invalid')
        models.append({'index':index,'name':name,'record_bytes':size,'vertex_count':vc,
            'triangle_count':tc,'materials':materials,'bone_info_offset':u32(record,12),
            'scale':scale,'packs':packs,'source_model_id':struct.unpack_from('<h',record,224)[0]})
    require(pos==len(header),'world GEO header suffix differs')
    return version,data,models,textures

def stream(data,model,index):
    packed,decoded,offset=model['packs'][index]
    raw=span(data,offset,packed or decoded)
    return inflate(raw,decoded) if packed else raw

def make(raw):
    version,data,models,texture_names=records(raw)
    selected=[m for m in models if m['name'].split('__',1)[0].casefold()=='modern_bench_2wide']
    require(len(selected)==1,'exact world model is absent or ambiguous')
    model=selected[0]
    require(model['index']==10 and model['name']=='modern_bench_2wide__mbench'
        and model['vertex_count']==256 and model['triangle_count']==188,'selected world model differs')
    require(model['bone_info_offset']==0 and not stream(data,model,5)
        and not stream(data,model,6),'static world model unexpectedly has skin channels')
    require(not stream(data,model,4),'selected world model unexpected secondary UV channel')
    require(model['scale']==[1.,1.,1.],'selected world model scale differs')
    vc,tc=model['vertex_count'],model['triangle_count']
    indices=accepted.decode_delta(stream(data,model,0),tc,3,False)
    positions=accepted.decode_delta(stream(data,model,1),vc,3,True)
    normals=accepted.decode_delta(stream(data,model,2),vc,3,True)
    rawuv=accepted.decode_delta(stream(data,model,3),vc,2,True)
    require(all(i<vc for i in indices),'world triangle references absent vertex')
    uv=list(rawuv)
    for i in range(vc):uv[i*2+1]=f32(1-uv[i*2+1])
    vertices=[]
    for i in range(vc):
        n=normals[i*3:i*3+3]
        require(sum(x*x for x in n)>1e-12,'world model has zero normal')
        vertices.append(positions[i*3:i*3+3]+n+uv[i*2:i*2+2]+[1.,0.,0,0])
    meshes=[];partmeta=[]
    for i,part in enumerate(model['materials']):
        pi=indices[part['first_triangle']*3:(part['first_triangle']+part['triangle_count'])*3]
        vo=64;io=vo+vc*48;bo=io+len(pi)*4;total=bo+4
        header=struct.pack('<8s14I',b'COHMESH1',1,64,vc,len(pi),1,48,vo,io,bo,total,0,0,0,0)
        body=b''.join(struct.pack('<10f2I',*v) for v in vertices)
        body+=struct.pack('<'+'I'*len(pi),*pi)+struct.pack('<I',0)
        canonical=header+body;require(len(canonical)==total,'world canonical mesh envelope differs')
        meshes.append(canonical)
        partmeta.append(dict(part,index=i,vertex_count=vc,index_count=len(pi),
            original_vertex_indices_retained=True,canonical_bytes=total,
            canonical_sha256=sha(canonical),source_group_node=5,
            static_identity_adapter={'bone_ids':[0],'weights':[1,0],'slots':[0,0],
                'role':'native static COHMESH1 adapter; no source bone or authored skin invented'}))
    meta={k:model[k] for k in ('index','name','record_bytes','vertex_count','triangle_count','scale','materials','packs')}
    meta.update(source_geo_version=version,source_geo_sha256=sha(raw),
        source_model_count=len(models),source_texture_names=texture_names,parts=partmeta,
        canonical_vertex_count=vc*len(meshes),canonical_index_count=len(indices),
        source_secondary_uv_present=False,source_static_vertex_rgb_present=False,
        source_normals_present=True,source_skin_channels_present=False,
        source_reductions_present=bool(model['packs'][8][1]),
        source_grid_present=bool(model['packs'][7][1]),
        reductions_selected=False,source_grid_collision_reconstructed=False,
        gpu_uv_transform='U unchanged; V=float32(1-V), original modelFixup upload',
        bounds={'minimum':[min(positions[c::3]) for c in range(3)],
                'maximum':[max(positions[c::3]) for c in range(3)]})
    return meshes,[vertices for _ in meshes],meta,(data,model)

def original_delta_check(raw,source,compiler='cc'):
    meshes,vertices,meta,(data,model)=make(raw)
    original=module('world_original_scalar_decoder',ROOT/'tools/material_fixture/original_delta_check.py')
    code=original.original_c(source);checks=[];vc=meta['vertex_count'];tc=meta['triangle_count']
    with tempfile.TemporaryDirectory(prefix='coh-world-original-delta-') as temporary:
        t=Path(temporary);(t/'oracle.c').write_bytes(code)
        subprocess.run([*shlex.split(compiler),'-std=c11','-O0','-fno-strict-aliasing',
            '-fPIC','-shared','-o',str(t/'oracle.so'),str(t/'oracle.c')],check=True)
        lib=C.CDLL(str(t/'oracle.so'))
        lib.uncompressDeltas.argtypes=[C.c_void_p,C.POINTER(C.c_uint8),C.c_int,C.c_int,C.c_int]
        lib.uncompressDeltas.restype=C.c_int
        lib.original_gpu_uvs.argtypes=[C.POINTER(C.c_float),C.c_int,C.POINTER(C.c_float)]
        for channel,index,count,stride,kind in [('indices',0,tc,3,1),('positions',1,vc,3,0),
                ('normals',2,vc,3,0),('uvs',3,vc,2,0)]:
            src=stream(data,model,index);python=accepted.decode_delta(src,count,stride,kind==0)
            expected=struct.pack('<'+('f' if kind==0 else'I')*len(python),*python)
            mem=(C.c_uint8*(len(src)+16))();C.memmove(mem,src,len(src))
            output=(C.c_uint8*len(expected))()
            require(lib.uncompressDeltas(output,mem,stride,count,kind)==len(src)
                and bytes(output)==expected,'original world delta '+channel+' differs')
            checks.append({'channel':channel,'elements':count*stride,'byte_exact':True,
                'source_stream_sha256':sha(src),'decoded_sha256':sha(expected)})
            if channel=='indices':
                joined=b''.join(mesh[u32(mesh,36):u32(mesh,36)+u32(mesh,20)*4] for mesh in meshes)
                require(joined==expected,'canonical world material triangle partitions differ')
            elif channel in ('positions','normals'):
                offset=0 if channel=='positions' else 12
                for mesh in meshes:
                    target=b''.join(mesh[64+i*48+offset:64+i*48+offset+12] for i in range(vc))
                    require(target==expected,'canonical world '+channel+' differs')
            if channel=='uvs':
                inp=(C.c_float*(vc*2)).from_buffer_copy(bytes(output));gpu=(C.c_float*(vc*2))()
                lib.original_gpu_uvs(inp,vc,gpu)
                target=b''.join(meshes[0][64+i*48+24:64+i*48+32] for i in range(vc))
                require(target==bytes(gpu),'canonical world GPU UV flip differs')
                checks.append({'channel':'uvs_gpu_upload','elements':vc*2,'byte_exact':True,
                    'decoded_sha256':sha(bytes(gpu))})
    return {'format':1,'passed':True,'scope':'unchanged original uncompressDeltas and source GPU UV upload expression',
        'source_sha256_lf':original.SOURCE_SHA,'function_sha256_lf':original.FUNCTION_SHA,
        'source_geometry_sha256':sha(raw),'original_client_execution':False,
        'source_vertices':vc,'source_triangles':tc,'canonical_partition_vertices':vc*len(meshes),
        'channel_checks':len(checks),'scalar_elements':sum(c['elements'] for c in checks),'checks':checks}
