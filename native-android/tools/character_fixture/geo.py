#!/usr/bin/env python3
"""Bounded, bytewise x86 GEO v0/v2/v3 extraction for the character gate.

Disk pointer fields remain integer offsets. The original delta decoder and
modelFixup UV convention are inherited from the accepted Phase 6 converter.
The head's fixed x86 v2 record is parsed explicitly, without native struct casts.
"""
from pathlib import Path
import importlib.util, math, struct

spec=importlib.util.spec_from_file_location('accepted_material_prepare',Path(__file__).resolve().parents[1]/'material_fixture/prepare.py')
accepted=importlib.util.module_from_spec(spec); spec.loader.exec_module(accepted)
require,span,u32,inflate,name_at=accepted.require,accepted.span,accepted.u32,accepted.inflate,accepted.name_at
f32,sha=accepted.f32,accepted.sha

def records(raw):
    require(8<=len(raw)<=2<<20,'geometry file size exceeds bound')
    biased,unpacked=struct.unpack('<2I',span(raw,0,8))
    if unpacked:
        version,start,packed,dataoff=0,8,biased-4,biased+8
    else:
        version,unpacked=struct.unpack('<2I',span(raw,8,8))
        require(version in (2,3),'character geometry version unsupported')
        start,packed,dataoff=16,biased-12,biased+4
    header=inflate(span(raw,start,packed),unpacked)
    data=span(raw,dataoff,u32(header,0))
    require(dataoff+len(data)==len(raw),'geometry trailing bytes differ')
    blockcount=4 if version==0 else 5
    sizes=[u32(header,4*i) for i in range(blockcount)]; pos=4*blockcount
    names=span(header,pos,sizes[1]); pos+=sizes[1]
    objects=span(header,pos,sizes[2]); pos+=sizes[2]
    texids=span(header,pos,sizes[3]); pos+=sizes[3]
    if blockcount==5:span(header,pos,sizes[4]); pos+=sizes[4]
    count=u32(header,pos+136); require(0<count<=128,'model count exceeds bound'); pos+=140
    texture_count=u32(names,0); require(texture_count<=128,'texture table exceeds bound')
    namebase=4+texture_count*4
    textures=[name_at(names,namebase+u32(names,4+4*i)) for i in range(texture_count)]
    result=[]
    for index in range(count):
        size=216 if version<3 else u32(header,pos)
        require(204<=size<=4096,'model disk record size differs')
        rec=span(header,pos,size); pos+=size
        if version<3:
            nameoff,texcountoff,boneoff,vertoff,texidoff,scaleoff,packoff=80,12,20,28,36,92,132
        else:
            nameoff,texcountoff,boneoff,vertoff,texidoff,scaleoff,packoff=60,8,12,16,24,68,104
        model=name_at(objects,u32(rec,nameoff)); vc,tc=struct.unpack('<2I',span(rec,vertoff,8))
        texcount=u32(rec,texcountoff); require(texcount<=32,'material count exceeds bound')
        material=[]
        for texid,triangles in struct.iter_unpack('<HH',span(texids,u32(rec,texidoff),texcount*4)):
            require(texid<len(textures),'texture index outside names table')
            material.append({'name':textures[texid],'triangle_count':triangles})
        packs=[struct.unpack('<3I',span(rec,packoff+i*12,12)) for i in range(7 if version<3 else 8)]
        if version<3:packs.insert(4,(0,0,0)) # missing source sts3 channel
        for packedsize,unpackedsize,offset in packs:
            require(unpackedsize<=4<<20,'model decoded stream exceeds bound')
            span(data,offset,packedsize or unpackedsize)
        bone_info=u32(rec,boneoff); bones=[]
        if bone_info:
            info=span(data,bone_info,72); n=u32(info,0)
            require(1<=n<=15,'model palette exceeds source limit')
            bones=[u32(info,4+4*i) for i in range(n)]
            require(len(set(bones))==n and all(i<99 for i in bones),'invalid model palette')
            require(u32(info,64)==u32(info,68)==0,'disk bone pointer slots not zero')
        scale=list(struct.unpack('<3f',span(rec,scaleoff,12)))
        require(all(math.isfinite(v) and 0<v<10 for v in scale),'model scale invalid')
        result.append({'index':index,'name':model,'vertex_count':vc,'triangle_count':tc,
            'materials':material,'bones':bones,'scale':scale,'packs':packs})
    require(pos<=len(header),'model records outside header')
    return version,data,result

def mesh(raw,requested_name,socket):
    version,data,models=records(raw)
    found=[x for x in models if x['name'].split('__',1)[0].casefold()==requested_name.casefold()]
    require(len(found)==1,'requested exact geometry absent or ambiguous')
    model=found[0]; vc,tc=model['vertex_count'],model['triangle_count']
    require(0<vc<=10000 and 0<tc<=10000,'character mesh cardinality exceeds bound')
    require(len(model['materials'])==1 and model['materials'][0]['triangle_count']==tc,'one complete material required')
    def stream(index):
        packed,unpacked,offset=model['packs'][index]
        b=span(data,offset,packed or unpacked)
        return inflate(b,unpacked) if packed else b
    indices=accepted.decode_delta(stream(0),tc,3,False)
    positions=accepted.decode_delta(stream(1),vc,3,True)
    normals=accepted.decode_delta(stream(2),vc,3,True)
    uv=accepted.decode_delta(stream(3),vc,2,True)
    for i in range(vc):uv[2*i+1]=f32(1-uv[2*i+1])
    require(all(index<vc for index in indices),'triangle references absent vertex')
    bones=model['bones']; weights,matidx=stream(5),stream(6)
    dummy=not bones
    if dummy:
        require(not weights and not matidx,'unboned geometry has stray skin bytes')
        require(0<=socket<99,'dummy bone socket invalid'); bones=[socket]
        weights=bytes([255])*vc; matidx=bytes(vc*2)
    require(len(weights)==vc and len(matidx)==vc*2,'skin channels differ from vertex count')
    vertices=[]; blended=0; useful=set()
    for i in range(vc):
        slots=[x//3 for x in matidx[2*i:2*i+2]]
        require(all(x%3==0 and x//3<len(bones) for x in matidx[2*i:2*i+2]),'encoded palette row invalid')
        w0=f32(f32(weights[i])/255.0); w1=f32(1-w0)
        normal=normals[3*i:3*i+3]; require(sum(v*v for v in normal)>1e-12,'zero mesh normal')
        if 0<weights[i]<255 and slots[0]!=slots[1]:blended+=1
        if weights[i]>0:useful.add(slots[0])
        if weights[i]<255:useful.add(slots[1])
        vertices.append(positions[3*i:3*i+3]+normal+uv[2*i:2*i+2]+[w0,w1]+slots)
    vo=64; io=vo+vc*48; bo=io+len(indices)*4; total=bo+len(bones)*4
    header=struct.pack('<8s14I',b'COHMESH1',1,64,vc,len(indices),len(bones),48,vo,io,bo,total,0,0,0,0)
    body=b''.join(struct.pack('<10f2I',*v) for v in vertices)
    body+=struct.pack('<'+'I'*len(indices),*indices)+struct.pack('<'+'I'*len(bones),*bones)
    canonical=header+body; require(len(canonical)==total,'canonical mesh envelope differs')
    meta={k:model[k] for k in ('index','name','vertex_count','triangle_count','materials','scale')}
    meta.update(source_geo_version=version,bone_global_ids=bones,source_dummy_bone_applied=dummy,
        genuinely_blended_vertices=blended,nonzero_influence_slots=sorted(useful),
        source_weight_byte_values=sorted(set(weights)),socket_id=socket,
        bounds={'minimum':[min(positions[c::3]) for c in range(3)],'maximum':[max(positions[c::3]) for c in range(3)]},
        canonical_sha256=sha(canonical),canonical_bytes=len(canonical),
        gpu_uv_transform='V=float32(1-V), original modelFixup before GPU upload')
    return canonical,vertices,bones,meta
