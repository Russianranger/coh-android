#!/usr/bin/env python3
"""Serialize the frozen bounded COHCHAR8 multi-part scene envelope."""
import struct
import geo

def make(meshes,parts,textures):
    geo.require(len(meshes)==len(parts)==11 and 0<len(textures)<=32,'scene fixture counts differ')
    po,ps,to,ts=128,128,128+11*128,32
    dataoff=to+len(textures)*ts; offset=dataoff; mesh_spans=[]; texture_spans=[]; body=[]
    for mesh in meshes:
        mesh_spans.append((offset,len(mesh))); offset+=len(mesh); body.append(mesh)
    for tex in textures:
        w,h,rgba=tex['width'],tex['height'],tex['rgba']
        geo.require(0<w<=4096 and 0<h<=4096 and len(rgba)==w*h*4,'scene texture footprint differs')
        texture_spans.append((offset,len(rgba))); offset+=len(rgba); body.append(rgba)
    header=bytearray(128)
    struct.pack_into('<8s14I',header,0,b'COHCHAR8',1,128,11,len(textures),po,ps,to,ts,dataoff,offset,2626,8958,620,0)
    part_records=[]
    for index,part in enumerate(parts):
        base,dual=part['base_texture'],part['dual_texture']
        geo.require(0<=base<len(textures) and 0<=dual<len(textures),'scene texture binding outside table')
        colors=[]
        for name in ('color1','color2'):
            rgb=part[name]; geo.require(len(rgb)==3 and all(isinstance(v,int) and 0<=v<=255 for v in rgb),'draw color bytes invalid')
            colors+= [geo.f32(v*geo.f32(1/255)) for v in rgb]+[1.0]
        flags=(1 if part['source_double_sided'] else 0)|(2 if index==7 else 0)
        geo.require(flags==(3 if index==7 else 1 if index==8 else 0),'original cull/alpha part rule differs')
        rec=bytearray(ps); struct.pack_into('<8I',rec,0,*mesh_spans[index],part['socket_global_id'],base,dual,flags,index,0)
        struct.pack_into('<11f',rec,32,*colors,1.0,1.0,0.0)
        part_records.append(bytes(rec))
    tex_records=[]
    for tex,(start,size) in zip(textures,texture_spans):
        tex_records.append(struct.pack('<8I',tex['width'],tex['height'],start,size,0,0,0,0))
    raw=bytes(header)+b''.join(part_records)+b''.join(tex_records)+b''.join(body)
    geo.require(len(raw)==offset,'scene output size differs')
    meta={'container':'COHCHAR8','header_bytes':128,'part_stride':128,'texture_stride':32,
        'part_count':11,'texture_count':len(textures),'vertex_count':2626,'index_count':8958,
        'triangle_count':2986,'genuinely_blended_vertices':620,
        'payload_rule':'contiguous canonical meshes then unique original mip0 RGBA pixels',
        'source_material_path':'automatic COLORBLEND_DUAL low quality fallback',
        'culling_rule':'CW front face, GL_BACK cull except Collar2x Hair/Neck double-sided',
        'alpha_rule':'Hair dual mask alpha retained and SRC_ALPHA/ONE_MINUS_SRC_ALPHA blend; other dual layers opaque',
        'native_runtime_skinning_required':True,'contains_baked_poses':False}
    return raw,meta
