#include "coh_native_core.h"
#include "byte_reader.h"
#include <math.h>

int coh_anim_header(const uint8_t *p,size_t n,CohAnimHeader *out){
    if(!p || !out || n<596)return 1;
    CohAnimHeader h={u32(p),u32(p+524),u32(p+528),u32(p+540),f32(p+516),f32(p+520)};
    if(h.header_bytes<596 || h.header_bytes>n || h.bone_count>100 || h.bone_offset<596 ||
       !span(h.header_bytes,h.bone_offset,h.bone_count,20) || !isfinite(h.hip) || !isfinite(h.length))return 1;
    if(h.hierarchy_offset){
        if(h.hierarchy_offset<596 || !span(h.header_bytes,h.hierarchy_offset,1,1204))return 1;
        if(h.bone_count && (size_t)h.bone_offset<(size_t)h.hierarchy_offset+1204 &&
           (size_t)h.hierarchy_offset<(size_t)h.bone_offset+(size_t)h.bone_count*20)return 1;
    }
    *out=h;return 0;
}
int coh_anim_bone(const uint8_t *p,size_t n,uint32_t index,CohBoneView *out){
    CohAnimHeader h;if(!out || coh_anim_header(p,n,&h) || index>=h.bone_count)return 1;
    const uint8_t *b=p+h.bone_offset+(size_t)index*20;
    unsigned flags=b[17],rot=flags&(1u|2u|4u|128u),pos=flags&(8u|16u);
    if(flags&(32u|64u))return 2; /* Delta modes are not admitted by this slice. */
    unsigned rs=rot==1?16:rot==4?8:(rot==2||rot==128)?5:0;
    unsigned ps=pos==8?12:pos==16?6:0;
    uint32_t ro=u32(b),po=u32(b+4);
    CohBoneView v={u16(b+8),u16(b+10),u16(b+12),u16(b+14),b[16],b[17],(uint8_t)rs,(uint8_t)ps,NULL,NULL,0,0};
    if(!rs || !ps || v.id>=100 || !v.rotation_frames || !v.position_frames ||
       v.rotation_frames>v.rotation_keys || v.position_frames>v.position_keys || ro<h.header_bytes || po<h.header_bytes ||
       !span(n,ro,v.rotation_keys,rs) || !span(n,po,v.position_keys,ps))return 1;
    v.rotation=p+ro;v.position=p+po;v.rotation_bytes=(size_t)v.rotation_keys*rs;v.position_bytes=(size_t)v.position_keys*ps;
    *out=v;return 0;
}
int coh_pack_view(const uint8_t *record,size_t rn,const uint8_t *payload,size_t n,size_t limit,CohPackView *out){
    if(!record || rn<12 || !out || (!payload && n))return 1;
    uint32_t compressed=u32(record),decoded=u32(record+4),offset=u32(record+8);
    size_t stored=compressed?compressed:decoded;
    if(compressed>INT32_MAX || decoded>limit || (compressed&&!decoded) ||
       (stored && (!payload || !span(n,offset,1,stored))))return 1;
    CohPackView v={stored?payload+offset:NULL,stored,decoded,compressed!=0};*out=v;return 0;
}
int coh_geo_model(const uint8_t *p,size_t n,uint32_t version,CohGeoModel *out){
    if(version<3 || version>8)return 2;
    if(!p || !out || n<4)return 1;
    uint32_t size=u32(p);if(size>n || size<4)return 1;
    size_t prefix=4+24+(version>=8?4:0),pack=prefix+32+8+36;
    unsigned count=8+(version>=7?1:0)+(version>=8?1:0);
    size_t id_offset=pack+(size_t)count*12+(version==4?24:0)+(version>=7?12:0);
    if(!span(size,id_offset,1,2))return 1;
    CohGeoModel m={0};m.version=version;m.record_bytes=size;m.radius=f32(p+4);
    m.texture_count=u32(p+8);m.bone_info_offset=u32(p+12);m.vertex_count=u32(p+16);m.triangle_count=u32(p+20);
    m.reflection_count=version>=8?u32(p+24):0;
    m.texture_index_offset=u32(p+prefix-4);
    if(!isfinite(m.radius) || m.texture_count>INT32_MAX || m.vertex_count>INT32_MAX || m.triangle_count>INT32_MAX ||
       m.reflection_count>INT32_MAX || u32(p+prefix))return 1; /* Disk PolyGrid.cell must be null. */
    m.name_offset=u32(p+prefix+32);m.alternate_pivot_offset=u32(p+prefix+36);m.pack_count=count;
    for(unsigned i=0;i<count;i++){
        const uint8_t *d=p+pack+(size_t)i*12;
        m.packs[i]=(CohPack32){u32(d),u32(d+4),u32(d+8)};
        if(m.packs[i].packed_bytes>INT32_MAX || (m.packs[i].packed_bytes&&!m.packs[i].unpacked_bytes))return 1;
    }
    uint16_t id=u16(p+id_offset);m.id=(int16_t)(id<=INT16_MAX?(int32_t)id:(int32_t)id-65536);
    *out=m;return 0;
}
