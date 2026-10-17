/* NONSHIPPING observer: include after source_snapshot.inc, anim.h, tricks.h.
 * Stable exclusive owner-thread group_info AND model/library/trick state required.
 * Never loads resources, invokes modelFind/groupModelFind, or mutates source.
 * Output goes to an unpublished temporary file; any failure discards all bytes.
 * SERVER-only observations do not establish CLIENT material/LOD completeness.
 */
#ifndef COH_SOURCE_RESOURCES_INCLUDED
#define COH_SOURCE_RESOURCES_INCLUDED
#define COH_RESOURCE_HEADER 192u
#define COH_RESOURCE_RECORD_MAX (128u*1024u)
#define COH_RESOURCE_TOTAL_MAX (64u*1024u*1024u)
#define COH_RESOURCE_TEXTURE_MAX 256u
#define COH_RESOURCE_MODEL_MAX 65536u
#define COH_RESOURCE_ROW_WORK_MAX (64u*1024u*1024u)

typedef struct CohSourceResourceReport {
    unsigned status,total_bytes,emitted_bytes,records,models,missing_models,textures,model_row_comparisons;
    unsigned client_materials_available,client_lods_available,actual_runtime_executed;
} CohSourceResourceReport;

static int coh_resource_string(unsigned char*out,unsigned*at,const char*name,
    unsigned bound,unsigned*length,int optional)
{
    unsigned n=0,i;
    *length=0;
    if(!name)return optional?COH_SOURCE_CATALOG_OK:COH_SOURCE_CATALOG_SOURCE;
    while(n<bound&&name[n])++n;
    if(!n||n==bound)return COH_SOURCE_CATALOG_SOURCE;
    ++n;if(n>COH_RESOURCE_RECORD_MAX-*at)return COH_SOURCE_CATALOG_LIMIT;
    for(i=0;i+1<n;i++)if((unsigned char)name[i]<32||(unsigned char)name[i]>126)return COH_SOURCE_CATALOG_SOURCE;
    memcpy(out+*at,name,n);*at+=n;*length=n;return COH_SOURCE_CATALOG_OK;
}
static int coh_resource_record(CohSnapshotState*s,GroupDef*d,unsigned generation,
    unsigned char*out,unsigned*size,unsigned*texture_count,unsigned*remaining_rows)
{
    unsigned at=COH_RESOURCE_HEADER,kind,file,slot,n,row=0xffffffffu,i,found=0;
    const char*names[6];Model*m;GeoLoadData*g=NULL;TrickInfo*info=NULL;int status;
    if(!generation||!out||!size||!texture_count||!remaining_rows)return COH_SOURCE_CATALOG_ARGUMENT;
    status=coh_snapshot_identity(s,d,&kind,&file,&slot);if(status)return status;
    memset(out,0,COH_RESOURCE_HEADER);memcpy(out,"COHRES01",8);
    coh_source_catalog_put_u32(out+8,1);coh_source_catalog_put_u32(out+12,COH_RESOURCE_HEADER);
    coh_source_catalog_put_u32(out+20,generation);coh_source_catalog_put_u32(out+24,kind);
    coh_source_catalog_put_u32(out+28,file);coh_source_catalog_put_u32(out+32,slot);
    coh_source_catalog_put_u32(out+36,(unsigned)d->id);coh_source_catalog_put_u32(out+44,1);
    m=d->model;names[0]=d->name;names[1]=names[2]=names[3]=names[4]=NULL;
    names[5]=objectLibraryPathFromObj(d->name);
    if(m){
        g=m->gld;
        if(!g||!m->name||g->modelheader.model_count<0||(unsigned)g->modelheader.model_count>COH_RESOURCE_MODEL_MAX||!g->modelheader.models||m->vert_count<0||m->tri_count<0||m->tex_count<0||(unsigned)m->tex_count>COH_RESOURCE_TEXTURE_MAX||(m->tex_count&&!m->tex_idx)||g->texnames.count<0||(g->texnames.count&&!g->texnames.strings)||g->file_format_version<0||g->loadstate<0||g->loadstate==2||m->loadstate==2)return COH_SOURCE_CATALOG_SOURCE;
        if((unsigned)g->modelheader.model_count>*remaining_rows)return COH_SOURCE_CATALOG_LIMIT;
        *remaining_rows-=(unsigned)g->modelheader.model_count;
        for(i=0;i<(unsigned)g->modelheader.model_count;i++)if(g->modelheader.models[i]==m){row=i;found++;}
        if(found!=1)return COH_SOURCE_CATALOG_SOURCE;
        names[1]=m->name;names[2]=g->name;
        coh_source_catalog_put_u32(out+40,1);coh_source_catalog_put_u32(out+68,row);
        coh_source_catalog_put_u32(out+72,(unsigned)g->file_format_version);
        coh_source_catalog_put_u32(out+76,(unsigned)g->loadstate);coh_source_catalog_put_u32(out+80,(unsigned)m->loadstate);
        coh_source_catalog_put_u32(out+84,m->flags);coh_source_catalog_put_u32(out+88,(unsigned)m->vert_count);
        coh_source_catalog_put_u32(out+92,(unsigned)m->tri_count);coh_source_catalog_put_u32(out+96,(unsigned)m->tex_count);
        if(m->trick){
            coh_source_catalog_put_u32(out+100,1);coh_source_catalog_put_u32(out+108,(unsigned)m->trick->flags1);coh_source_catalog_put_u32(out+112,(unsigned)m->trick->flags2);
            info=m->trick->info;
            if(info){
                names[3]=info->name;names[4]=info->file_name;
                if(!names[3]||!names[4])return COH_SOURCE_CATALOG_SOURCE;
                coh_source_catalog_put_u32(out+104,1);coh_source_catalog_put_u32(out+116,(unsigned)info->model_flags);coh_source_catalog_put_u32(out+120,info->group_flags);
                coh_snapshot_float(out+168,&info->lod_near);coh_snapshot_float(out+172,&info->lod_far);
                coh_snapshot_float(out+176,&info->lod_nearfade);coh_snapshot_float(out+180,&info->lod_farfade);
                coh_snapshot_float(out+184,&info->lod_scale);coh_snapshot_float(out+188,&info->shadow_dist);
            }
        }
        for(i=0;i<3;i++){coh_snapshot_float(out+128+i*4,&m->min[i]);coh_snapshot_float(out+140+i*4,&m->max[i]);coh_snapshot_float(out+152+i*4,&m->scale[i]);}
        coh_snapshot_float(out+164,&m->radius);
        if(!coh_snapshot_finite(out+128,16))return COH_SOURCE_CATALOG_SOURCE;
    }else coh_source_catalog_put_u32(out+68,0xffffffffu);
    for(i=0;i<6;i++){
        status=coh_resource_string(out,&at,names[i],i==2?sizeof(g->name):256u,&n,i!=0&&(!m||i>2));if(status)return status;
        coh_source_catalog_put_u32(out+(i<5?48+i*4:124),n);
    }
    *texture_count=0;
    if(m)for(i=0;i<(unsigned)m->tex_count;i++){
        unsigned id=m->tex_idx[i].id;
        if(id>=(unsigned)g->texnames.count||at>COH_RESOURCE_RECORD_MAX-12)return COH_SOURCE_CATALOG_SOURCE;
        coh_source_catalog_put_u32(out+at,id);coh_source_catalog_put_u32(out+at+4,m->tex_idx[i].count);at+=12;
        status=coh_resource_string(out,&at,g->texnames.strings[id],256,&n,0);if(status)return status;
        coh_source_catalog_put_u32(out+at-n-4,n);(*texture_count)++;
    }
    coh_source_catalog_put_u32(out+16,at);*size=at;return COH_SOURCE_CATALOG_OK;
}
/* The observer reuses exact source snapshot pointer-incidence discovery. Catalog
 * export and runtime sidecar must already be retained at this SAME boundary.
 * Scratch is caller-owned >=128KiB; writes never escape on a failed caller
 * transaction. No implicit original catalog/snapshot recapture occurs here. */
static int coh_source_resources_export(CohSourceCatalogOutputFn output,void*context,
    const unsigned char*catalog_header,const CohSourceCatalogExportReport*catalog,
    unsigned char*scratch,unsigned scratch_bytes,CohSourceResourceReport*report)
{
    CohSnapshotState s;unsigned pass,f,i,n,textures,records,models,total,defs_crc,refs_crc;
    int status=COH_SOURCE_CATALOG_ARGUMENT;GroupDef*d;
    if(!report)return status;
    memset(report,0,sizeof(*report));report->status=(unsigned)status;
    if(!output||!catalog_header||!catalog||catalog->status||!scratch||scratch_bytes<COH_RESOURCE_RECORD_MAX)return status;
    if(memcmp(catalog_header,"COHCAT01",8)||coh_snapshot_u32(catalog_header+8)!=1||coh_snapshot_u32(catalog_header+12)!=48||coh_snapshot_u32(catalog_header+20)==0||coh_snapshot_u32(catalog_header+16)!=catalog->total_bytes||catalog->emitted_bytes!=catalog->total_bytes||catalog->total_bytes<48||catalog->total_bytes>COH_SOURCE_CATALOG_MAX_BYTES||coh_snapshot_u32(catalog_header+24)!=catalog->files||coh_snapshot_u32(catalog_header+28)!=catalog->definitions||coh_snapshot_u32(catalog_header+44)||catalog->files>COH_SOURCE_CATALOG_MAX_FILES||catalog->slots>COH_SOURCE_CATALOG_MAX_SLOTS||catalog->definitions>COH_SOURCE_CATALOG_MAX_DEFINITIONS||catalog->children>COH_SOURCE_CATALOG_MAX_CHILDREN)return status;
    memset(&s,0,sizeof(s));s.files=catalog->files;s.slots=catalog->slots;s.definitions=catalog->definitions;s.children=catalog->children;s.roots=(unsigned)group_info.ref_count;
    status=coh_snapshot_inventory(&s);if(status){report->status=(unsigned)status;return status;}
    defs_crc=(unsigned)groupInfoCrcDefs();refs_crc=(unsigned)groupInfoCrcRefs();
    if(defs_crc!=coh_snapshot_u32(catalog_header+32)||refs_crc!=coh_snapshot_u32(catalog_header+36)||(unsigned)groupInfoRefCount()!=coh_snapshot_u32(catalog_header+40)){report->status=COH_SOURCE_CATALOG_CHANGED;return COH_SOURCE_CATALOG_CHANGED;}
    records=models=total=0;
    for(pass=0;pass<2;pass++){
        unsigned emitted=0,r=0,m=0,t=0,remaining_rows=COH_RESOURCE_ROW_WORK_MAX;s.pass=pass;
        status=coh_snapshot_inventory(&s);if(status)goto done;
        for(f=0;f<s.files+s.external_count;f++){
            unsigned count=f<s.files?(unsigned)group_info.files[f]->count:1;
            for(i=0;i<count;i++){
                d=f<s.files?group_info.files[f]->defs[i]:s.external[f-s.files];
                if(!d||!d->in_use)continue;
                status=coh_resource_record(&s,d,coh_snapshot_u32(catalog_header+20),scratch,&n,&textures,&remaining_rows);if(status)goto done;
                if(n>COH_RESOURCE_TOTAL_MAX-emitted){status=COH_SOURCE_CATALOG_LIMIT;goto done;}
                if(pass&&output(context,scratch,n)!=1){status=COH_SOURCE_CATALOG_OUTPUT;goto done;}
                emitted+=n;r++;m+=!!d->model;t+=textures;
                if(pass)report->emitted_bytes=emitted;
            }
        }
        if(!pass){records=r;models=m;total=emitted;report->textures=t;report->model_row_comparisons=COH_RESOURCE_ROW_WORK_MAX-remaining_rows;}
        else if(records!=r||models!=m||total!=emitted||report->textures!=t||report->model_row_comparisons!=COH_RESOURCE_ROW_WORK_MAX-remaining_rows){status=COH_SOURCE_CATALOG_CHANGED;goto done;}
    }
    status=coh_snapshot_inventory(&s);
    if(!status&&((unsigned)groupInfoCrcDefs()!=defs_crc||(unsigned)groupInfoCrcRefs()!=refs_crc))status=COH_SOURCE_CATALOG_CHANGED;
done:report->status=(unsigned)status;report->total_bytes=total;report->records=records;report->models=models;report->missing_models=records-models;return status;
}
#endif
