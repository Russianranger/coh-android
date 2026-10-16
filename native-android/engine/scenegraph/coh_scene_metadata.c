#include "coh_scene_metadata.h"
#include <math.h>
#include <string.h>
#define TRY(x) do {CohStatus s_=(x);if(s_!=COH_OK)return s_;}while(0)
static CohStatus bits(CohRepReader *r,unsigned n,uint32_t *out){TRY(coh_rep_read(r,n,out));return n<32&&(*out>>n)?COH_INVALID:COH_OK;}
static CohStatus flag(CohRepReader *r,uint32_t *out){return bits(r,1,out);}
static CohStatus number(CohRepReader *r,float *out){uint32_t u;TRY(bits(r,32,&u));memcpy(out,&u,4);return isfinite(*out)?COH_OK:COH_INVALID;}
static CohStatus optional(CohRepReader *r,float *out){uint32_t present;*out=0;TRY(flag(r,&present));return present?number(r,out):COH_OK;}
static CohStatus string(CohRepReader *r,char *out){char ignored[COH_REP_NAME_MAX];return coh_rep_string(r,out?out:ignored,COH_REP_NAME_MAX);}
static CohStatus color(CohRepReader *r,uint8_t *out,uint32_t count){uint32_t u;for(uint32_t i=0;i<count;i++){TRY(bits(r,8,&u));out[i]=(uint8_t)u;}return COH_OK;}
static CohStatus skip_matrix(CohRepReader *r){
    uint32_t packed,pos,angles,scale,half,negative,u;float value;TRY(flag(r,&packed));
    if(!packed){for(unsigned i=0;i<12;i++)TRY(number(r,&value));return COH_OK;}
    TRY(flag(r,&pos));TRY(flag(r,&angles));TRY(flag(r,&scale));
    for(unsigned k=0;k<pos+angles;k++)for(unsigned i=0;i<3;i++){
        TRY(flag(r,&half));if(half){TRY(flag(r,&negative));TRY(coh_rep_pack(r,5,&u));}else TRY(number(r,&value));
    }
    if(scale)for(unsigned i=0;i<3;i++)TRY(number(r,&value));
    return COH_OK;
}
static CohStatus property(CohRepReader *r,CohSgProperty *out){
    TRY(coh_rep_string(r,out->name,sizeof(out->name)));
    uint32_t value;size_t i;
    for(i=0;i<sizeof(out->value);i++){TRY(bits(r,8,&value));out->value[i]=(char)value;if(!value)break;}
    if(i==sizeof(out->value))return COH_LIMIT;
    TRY(flag(r,&out->type));return COH_OK;
}
CohStatus coh_scenegraph_property_begin(const CohSgMetadata *metadata,CohSgPropertyCursor *out){
    if(!metadata||!out)return COH_INVALID;
    if(metadata->property_count>COH_GROUPS_PROPERTY_MAX||metadata->property_span.cursor>metadata->property_span.bits)return COH_INVALID;
    *out=(CohSgPropertyCursor){metadata->property_span,metadata->property_count};return COH_OK;
}
CohStatus coh_scenegraph_property_next(CohSgPropertyCursor *cursor,CohSgProperty *out){
    if(!cursor||!out)return COH_INVALID;
    if(!cursor->remaining)return cursor->reader.cursor==cursor->reader.bits?COH_NOT_FOUND:COH_INVALID;
    if(cursor->remaining>COH_GROUPS_PROPERTY_MAX)return COH_INVALID;
    CohSgPropertyCursor next=*cursor;CohSgProperty candidate={0};TRY(property(&next.reader,&candidate));
    next.remaining--;if(!next.remaining&&next.reader.cursor!=next.reader.bits)return COH_INVALID;
    *cursor=next;*out=candidate;return COH_OK;
}
static CohStatus decode(const CohSgDefinition *d,CohRepReader *r,CohSgMetadata *m){
    uint32_t children,u;char name[COH_REP_NAME_MAX];
    TRY(flag(r,&m->in_use));if(m->in_use!=d->in_use)return COH_STATE;
    if(!m->in_use)return COH_OK;
    TRY(string(r,name));if(strcmp(name,d->name))return COH_STATE;
    TRY(bits(r,32,&m->mod_time));if(m->mod_time!=d->mod_time)return COH_STATE;
    TRY(coh_rep_pack(r,1,&children));if(children!=d->child_count)return COH_STATE;
    for(uint32_t i=0;i<children;i++){TRY(string(r,NULL));TRY(skip_matrix(r));}
    TRY(flag(r,&m->lod_present));
    if(m->lod_present){
        TRY(optional(r,&m->lod_scale));TRY(optional(r,&m->lod_near));TRY(optional(r,&m->lod_far));
        TRY(optional(r,&m->lod_nearfade));TRY(optional(r,&m->lod_farfade));
        TRY(bits(r,2,&m->lod_fadenode));TRY(flag(r,&m->parent_fade));TRY(flag(r,&m->child_parent_fade));
        TRY(flag(r,&m->no_fog_clip));TRY(flag(r,&m->no_coll));
    }
    TRY(flag(r,&m->children_present));
    if(m->children_present){
        TRY(flag(r,&m->open_tracker));TRY(flag(r,&m->child_light));TRY(flag(r,&m->child_ambient));
        TRY(flag(r,&m->child_volume));TRY(flag(r,&m->child_beacon));TRY(flag(r,&m->child_no_fog_clip));
    }
    TRY(optional(r,&m->sound_radius));TRY(optional(r,&m->shadow_dist));TRY(flag(r,&m->tricks_present));
    if(m->tricks_present){
        TRY(string(r,m->type_name));TRY(flag(r,&m->lib_ungroupable));TRY(flag(r,&m->has_light));TRY(flag(r,&m->has_ambient));
        if(m->has_light||m->has_ambient){if(m->has_light)TRY(optional(r,&m->light_radius));TRY(color(r,(uint8_t *)m->color,8));}
        TRY(flag(r,&m->has_cubemap));
        if(m->has_cubemap){TRY(bits(r,16,&m->cubemap_generation_size));TRY(bits(r,16,&m->cubemap_capture_size));TRY(number(r,&m->cubemap_blur_angle));TRY(number(r,&m->cubemap_capture_time));}
        TRY(flag(r,&m->has_sound));
        if(m->has_sound){TRY(string(r,m->sound_name));TRY(string(r,m->sound_script));TRY(bits(r,8,&m->sound_volume));TRY(number(r,&m->sound_ramp));TRY(flag(r,&m->sound_exclude));}
        TRY(flag(r,&m->has_fog));
        if(m->has_fog){TRY(number(r,&m->fog_near));TRY(number(r,&m->fog_far));TRY(number(r,&m->fog_radius));TRY(number(r,&m->fog_speed));TRY(color(r,(uint8_t *)m->color,8));}
        TRY(flag(r,&m->has_volume));if(m->has_volume)for(unsigned i=0;i<3;i++)TRY(number(r,&m->box_scale[i]));
        TRY(flag(r,&m->has_beacon));if(m->has_beacon){TRY(string(r,m->beacon_name));TRY(number(r,&m->beacon_radius));}
        TRY(flag(r,&m->has_tint_color));if(m->has_tint_color){TRY(color(r,m->color[0],3));TRY(color(r,m->color[1],3));}
        TRY(coh_rep_pack(r,1,&m->has_tex));if(m->has_tex&~3u)return COH_UNSUPPORTED;
        for(unsigned i=0;i<2;i++)if(m->has_tex&(1u<<i))TRY(string(r,m->textures[i]));
        TRY(flag(r,&m->has_alpha));if(m->has_alpha)TRY(number(r,&m->alpha));
        TRY(coh_rep_pack(r,1,&m->has_properties));if(m->has_properties>1)return COH_INVALID;
        if(m->has_properties){
            TRY(bits(r,32,&m->property_count));if(m->property_count>COH_GROUPS_PROPERTY_MAX)return COH_LIMIT;
            m->property_span=*r;CohSgProperty ignored;
            for(uint32_t i=0;i<m->property_count;i++)TRY(property(r,&ignored));
            m->property_span.bits=r->cursor;
        }
    }
    TRY(coh_rep_pack(r,1,&m->swap_count));if(m->swap_count!=d->swap_count)return COH_STATE;
    for(uint32_t i=0;i<m->swap_count;i++){
        TRY(string(r,name));if(strcmp(name,d->swaps[i].original))return COH_STATE;
        TRY(string(r,name));if(strcmp(name,d->swaps[i].replacement))return COH_STATE;
        TRY(flag(r,&u));if(u!=d->swaps[i].composite)return COH_STATE;
        if(u)m->unresolved_requirements|=COH_SG_META_COMPOSITE;
    }
    TRY(flag(r,&m->has_geometry));if(m->has_geometry)TRY(string(r,m->geometry));TRY(flag(r,&m->hide_for_gameplay));
    if(strcmp(m->geometry,d->geometry)||strcmp(m->textures[0],d->textures[0])||strcmp(m->textures[1],d->textures[1]))return COH_STATE;
    m->unresolved_requirements|=COH_SG_META_BOUNDS_LOD;
    if(m->has_geometry)m->unresolved_requirements|=COH_SG_META_GEOMETRY|COH_SG_META_MODEL_TRICKS;
    if(m->has_tex||m->swap_count)m->unresolved_requirements|=COH_SG_META_TEXTURES;
    if(m->has_properties)m->unresolved_requirements|=COH_SG_META_PROPERTIES;
    if(m->type_name[0])m->unresolved_requirements|=COH_SG_META_TYPE;
    if(m->has_light||m->has_ambient||m->has_tint_color||m->child_light||m->child_ambient)m->unresolved_requirements|=COH_SG_META_LIGHTING;
    if(m->has_fog)m->unresolved_requirements|=COH_SG_META_FOG;
    if(m->has_cubemap)m->unresolved_requirements|=COH_SG_META_CUBEMAP;
    if(m->has_sound)m->unresolved_requirements|=COH_SG_META_SOUND;
    if(m->has_volume||m->child_volume)m->unresolved_requirements|=COH_SG_META_VOLUME;
    if(m->has_beacon||m->child_beacon)m->unresolved_requirements|=COH_SG_META_BEACON;
    if(m->hide_for_gameplay||m->no_coll||m->no_fog_clip||m->child_no_fog_clip||m->open_tracker||m->has_alpha)m->unresolved_requirements|=COH_SG_META_VISIBILITY;
    return COH_OK;
}
CohStatus coh_scenegraph_metadata(const CohSceneGraph *g,uint32_t index,CohSgMetadata *out){
    if(!g||!out||!g->definitions||index>=g->definition_count||!g->generation||!g->asset_generation)return COH_INVALID;
    const CohSgDefinition *d=&g->definitions[index];CohSgMetadata candidate={0};CohRepReader r;
    if(d->child_count>COH_SG_CHILDREN_MAX||d->swap_count>COH_GROUPS_SWAP_MAX||(d->swap_count&&!d->swaps))return COH_INVALID;
    if(!d->wire||!d->wire_bytes)return COH_NOT_FOUND;
    if(d->wire_start_bit>7||d->wire_bytes>COH_REP_BOUNDED_MESSAGE_MAX||d->wire_bits>d->wire_bytes*8||d->wire_start_bit>d->wire_bytes*8-d->wire_bits||d->aligned>1)return COH_INVALID;
    TRY(coh_rep_reader_bounded(&r,(CohBytes){d->wire,d->wire_bytes},d->wire_bits+d->wire_start_bit,(int)d->aligned,COH_REP_BOUNDED_MESSAGE_MAX));r.cursor=d->wire_start_bit;
    candidate.scene_generation=g->generation;candidate.asset_generation=g->asset_generation;candidate.file=d->file;candidate.slot=d->id;
    TRY(decode(d,&r,&candidate));if(r.cursor!=r.bits)return COH_INVALID;
    *out=candidate;return COH_OK;
}
