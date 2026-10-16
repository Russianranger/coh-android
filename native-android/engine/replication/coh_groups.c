#include "coh_groups.h"
#include <math.h>
#include <string.h>

typedef char coh_groups_float32_required[sizeof(float)==4?1:-1];
typedef struct {
    CohRepReader reader;
    CohGroupsInspection value;
    CohGroupsStage stage;
} Groups;
#define TRY(e) do { CohStatus status_=(e); if(status_!=COH_OK)return status_; } while(0)
static CohStatus work(Groups *g) {
    if(g->value.work_units==COH_GROUPS_WORK_MAX)return COH_LIMIT;
    g->value.work_units++;return COH_OK;
}
static CohStatus bits(Groups *g,unsigned width,uint32_t *out) {
    TRY(work(g));TRY(coh_rep_read(&g->reader,width,out));
    /* byteAlignedMode still rounds a scalar to bytes; unused high bits must
     * not turn source booleans/2-bit flags into unrecognized variants. */
    if(width<32 && *out>>width)return COH_INVALID;
    return COH_OK;
}
static CohStatus pack(Groups *g,unsigned width,uint32_t *out) {
    TRY(work(g));return coh_rep_pack(&g->reader,width,out);
}
static CohStatus flag(Groups *g,uint32_t *out){return bits(g,1,out);}
static CohStatus count(uint32_t *total,uint32_t add,uint32_t limit) {
    if(add>limit || *total>limit-add)return COH_LIMIT;
    *total+=add;return COH_OK;
}
static CohStatus string(Groups *g,uint32_t capacity,int *nonempty) {
    uint32_t c;int present=0;
    for(uint32_t i=0;i<capacity;i++) {
        TRY(bits(g,8,&c));
        TRY(count(&g->value.string_bytes,1,COH_GROUPS_STRING_BYTES_MAX));
        if(!c){g->value.strings++;if(nonempty)*nonempty=present;return COH_OK;}
        present=1;
    }
    return COH_LIMIT;
}
static CohStatus floats(Groups *g,unsigned count_) {
    for(unsigned i=0;i<count_;i++) {
        uint32_t u;float f;TRY(bits(g,32,&u));memcpy(&f,&u,4);
        if(!isfinite(f))return COH_INVALID;
    }
    return COH_OK;
}
static CohStatus optional_float(Groups *g) {
    uint32_t present;TRY(flag(g,&present));
    if(present)TRY(floats(g,1));
    return COH_OK;
}
static CohStatus color(Groups *g,unsigned count_) {
    for(unsigned i=0;i<count_;i++){uint32_t u;TRY(bits(g,8,&u));}
    return COH_OK;
}
static CohStatus matrix(Groups *g) {
    uint32_t packed;g->stage=COH_GROUPS_STAGE_MATRIX;TRY(flag(g,&packed));
    if(!packed){g->value.raw_matrices++;return floats(g,12);}
    g->value.packed_matrices++;
    uint32_t position,angles,scale;TRY(flag(g,&position));TRY(flag(g,&angles));TRY(flag(g,&scale));
    for(unsigned j=0;j<2;j++)if(j?angles:position)for(unsigned i=0;i<3;i++) {
        uint32_t half;TRY(flag(g,&half));
        if(half){uint32_t u;TRY(flag(g,&u));TRY(pack(g,5,&u));}
        else TRY(floats(g,1));
    }
    if(scale)TRY(floats(g,3));
    return COH_OK;
}
static CohStatus tricks(Groups *g) {
    uint32_t u,light,ambient;g->stage=COH_GROUPS_STAGE_TRICKS;
    TRY(string(g,COH_REP_NAME_MAX,NULL));TRY(flag(g,&u));
    TRY(flag(g,&light));TRY(flag(g,&ambient));
    if(light||ambient){if(light)TRY(optional_float(g));TRY(color(g,8));}
    TRY(flag(g,&u));if(u){TRY(bits(g,16,&u));TRY(bits(g,16,&u));TRY(floats(g,2));}
    TRY(flag(g,&u));if(u) {
        TRY(string(g,COH_REP_NAME_MAX,NULL));TRY(string(g,COH_REP_NAME_MAX,NULL));
        TRY(bits(g,8,&u));TRY(floats(g,1));TRY(flag(g,&u));
    }
    TRY(flag(g,&u));if(u){TRY(floats(g,4));TRY(color(g,8));}
    TRY(flag(g,&u));if(u)TRY(floats(g,3));
    TRY(flag(g,&u));if(u){TRY(string(g,COH_REP_NAME_MAX,NULL));TRY(floats(g,1));}
    TRY(flag(g,&u));if(u)TRY(color(g,6));
    TRY(pack(g,1,&u));if(u&~3u)return COH_UNSUPPORTED;
    if(u&1)TRY(string(g,COH_REP_NAME_MAX,NULL));
    if(u&2)TRY(string(g,COH_REP_NAME_MAX,NULL));
    TRY(flag(g,&u));if(u)TRY(floats(g,1));
    TRY(pack(g,1,&u));if(u>1)return COH_INVALID;
    if(u) {
        uint32_t n;g->stage=COH_GROUPS_STAGE_PROPERTY;TRY(bits(g,32,&n));
        TRY(count(&g->value.properties,n,COH_GROUPS_PROPERTY_MAX));
        for(uint32_t i=0;i<n;i++) {
            TRY(string(g,64,NULL));TRY(string(g,COH_GROUPS_VALUE_MAX,NULL));TRY(flag(g,&u));
        }
    }
    return COH_OK;
}
static CohStatus definition(Groups *g) {
    uint32_t u,n;g->stage=COH_GROUPS_STAGE_DEF;TRY(flag(g,&u));
    if(!u){g->value.removed_defs++;return COH_OK;}
    TRY(string(g,COH_REP_NAME_MAX,NULL));TRY(bits(g,32,&u));TRY(pack(g,1,&n));
    TRY(count(&g->value.children,n,COH_GROUPS_CHILD_MAX));
    for(uint32_t i=0;i<n;i++) {
        g->stage=COH_GROUPS_STAGE_CHILD;TRY(string(g,COH_REP_NAME_MAX,NULL));TRY(matrix(g));
    }
    g->stage=COH_GROUPS_STAGE_DEF;TRY(flag(g,&u));
    if(u) {
        for(unsigned i=0;i<5;i++)TRY(optional_float(g));
        TRY(bits(g,2,&u));for(unsigned i=0;i<4;i++)TRY(flag(g,&u));
    }
    TRY(flag(g,&u));if(u)for(unsigned i=0;i<6;i++)TRY(flag(g,&u));
    TRY(optional_float(g));TRY(optional_float(g));
    TRY(flag(g,&u));if(u)TRY(tricks(g));
    g->stage=COH_GROUPS_STAGE_SWAP;TRY(pack(g,1,&n));
    TRY(count(&g->value.swaps,n,COH_GROUPS_SWAP_MAX));
    for(uint32_t i=0;i<n;i++) {
        TRY(string(g,COH_REP_NAME_MAX,NULL));TRY(string(g,COH_REP_NAME_MAX,NULL));TRY(flag(g,&u));
    }
    g->stage=COH_GROUPS_STAGE_DEF;TRY(flag(g,&u));if(u)TRY(string(g,COH_REP_NAME_MAX,NULL));
    TRY(flag(g,&u));return COH_OK;
}
static CohStatus file(Groups *g) {
    uint32_t present,u,last=0;g->stage=COH_GROUPS_STAGE_FILE;TRY(flag(g,&present));
    if(!present)return COH_OK;
    g->value.present_files++;TRY(string(g,COH_REP_NAME_MAX,NULL));TRY(bits(g,32,&u));
    TRY(flag(g,&u));if(u)return COH_UNSUPPORTED;
    for(;;) {
        g->stage=COH_GROUPS_STAGE_DEF;TRY(pack(g,1,&u));if(!u)break;
        if(u>INT32_MAX)return COH_INVALID;
        if(u>COH_GROUPS_DEF_ID_MAX+1u)return COH_LIMIT;
        if(u<=last)return COH_INVALID;
        last=u;
        if(u-1>g->value.max_def_id)g->value.max_def_id=u-1;
        TRY(count(&g->value.defs,1,COH_GROUPS_DEF_MAX));TRY(definition(g));
    }
    return COH_OK;
}
static CohStatus inspect(Groups *g) {
    CohRepScenePrefix prefix;g->stage=COH_GROUPS_STAGE_PREFIX;
    TRY(coh_rep_scene_prefix(&g->reader,&prefix));
    if(prefix.no_auto_group>1 || prefix.team_area>7)return COH_INVALID;
    g->value.new_world=prefix.new_world;g->value.prefix_bits=g->reader.cursor;
    g->stage=COH_GROUPS_STAGE_FILES;TRY(pack(g,1,&g->value.files));
    if(g->value.files>COH_GROUPS_FILE_MAX)return COH_LIMIT;
    /* Wire order 1..N-1,0 is implicit, not a separate transmitted ID. */
    for(uint32_t i=0;i<g->value.files;i++)TRY(file(g));
    uint32_t previous=0;int have_previous=0;
    for(;;) {
        uint32_t index;int present;g->stage=COH_GROUPS_STAGE_ROOT;TRY(pack(g,1,&index));
        if(index==UINT32_MAX)break;
        if(index>INT32_MAX)return COH_INVALID;
        if(index>COH_GROUPS_ROOT_ID_MAX)return COH_LIMIT;
        if(have_previous && index<=previous)return COH_INVALID;
        previous=index;have_previous=1;g->value.max_root_id=index;
        TRY(count(&g->value.roots,1,COH_GROUPS_ROOT_MAX));
        TRY(string(g,COH_REP_NAME_MAX,&present));
        if(present)TRY(matrix(g));else g->value.removed_roots++;
    }
    g->stage=COH_GROUPS_STAGE_FOOTER;TRY(pack(g,1,&g->value.footer_file_count));
    if(g->value.footer_file_count!=g->value.files)return COH_INVALID;
    TRY(pack(g,1,&g->value.footer_active_roots));
    if(g->value.footer_active_roots>COH_GROUPS_ROOT_MAX)return COH_LIMIT;
    TRY(bits(g,32,&g->value.footer_defs_crc));TRY(bits(g,32,&g->value.footer_refs_crc));
    g->stage=COH_GROUPS_STAGE_END;
    if(g->reader.cursor!=g->reader.bits)return COH_UNSUPPORTED;
    g->value.consumed_bits=g->reader.cursor;return COH_OK;
}
CohStatus coh_rep_groups(CohRepReader *reader,CohGroupsInspection *out,CohGroupsFailure *failure) {
    CohStatus status=COH_INVALID;Groups g;memset(&g,0,sizeof(g));
    if(reader)g.reader=*reader;
    if(reader && out) {
        uint32_t ignored;status=coh_rep_read(&g.reader,0,&ignored);
        if(status==COH_OK)status=inspect(&g);
    }
    if(status!=COH_OK) {
        if(failure)*failure=(CohGroupsFailure){g.stage,g.reader.cursor,status};
        return status;
    }
    *reader=g.reader;*out=g.value;
    if(failure)*failure=(CohGroupsFailure){COH_GROUPS_STAGE_NONE,0,COH_OK};
    return COH_OK;
}
