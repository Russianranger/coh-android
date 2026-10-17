/* NONSHIPPING caller preparation only; no hook installation or sink.
 * Include after real owner, exporters, eligibility and transaction helpers.
 * Original exclusive link/client/entity/group/model owner thread, completed
 * loader init, disabled folder callbacks, no engine callbacks/lazy loads/yield
 * throughout begin -> original worldSendUpdate -> finish/abort are prerequisites.
 * The real quiet functions must be linked from guarded original anim.c.
 */
#ifndef COH_SOURCE_GROUPS_BOUNDARY_INCLUDED
#define COH_SOURCE_GROUPS_BOUNDARY_INCLUDED
#define COH_GROUPS_BOUNDARY_MAX_BYTES (128u*1024u*1024u)
int coh_resource_quiescence_begin(void);
int coh_resource_quiescence_end(void);
extern int folder_cache_update_enable,folder_cache_manual_callback_check;
typedef struct CohGroupsBoundarySink {
 /* Local monotonic id only: sink must bind actual fresh run/source receipt and
  * use private provisional outputs. It is NOT a runtime generation token. */
 int (*open)(void*,unsigned);
 /* kind 1 owner,2 catalog,3 runtime,4 resources,5 eligibility,6 raw public bounds; copy synchronously. */
 int (*write)(void*,unsigned,unsigned,const unsigned char*,unsigned);
 int (*packet)(void*,unsigned,const unsigned char*,unsigned,unsigned,unsigned,
               const CohGroupsEligibilityReport*,const CohSourceCatalogExportReport*,
               const CohSourceSnapshotReport*,const CohSourceResourceReport*,const CohSourcePublicBoundsReport*);
 /* Commit only after all data and actual quiet-release success. */
 int (*commit)(void*,unsigned);
 void (*abort)(void*,unsigned);
 void *context;
} CohGroupsBoundarySink;
typedef struct CohGroupsBoundaryState {
 CohGroupsBoundarySink sink;
 unsigned phase,blocked,quiet,opened,id,next,bytes,kind,kind_bytes,header_present,raw_expected;
 const NetLink*link;CohSourceGroupsOwner owner;
 unsigned char header[48],scratch[COH_RESOURCE_RECORD_MAX];
 CohSourceCatalogExportReport catalog;CohSourceSnapshotReport snapshot;CohSourceResourceReport resources;CohSourcePublicBoundsReport raw_bounds;
} CohGroupsBoundaryState;
static CohGroupsBoundaryState coh_groups_boundary;
static void coh_groups_boundary_abort(void*context,unsigned id)
{
 CohGroupsBoundaryState*s=&coh_groups_boundary;(void)context;
 if(!s->phase||s->id!=id)return;
 /* Retain phase during external callbacks to prevent recursive begin/config. */
 s->phase=3;
 if(s->quiet){if(coh_resource_quiescence_end()==1)s->quiet=0;else s->blocked=1;}
 if(s->opened)s->sink.abort(s->sink.context,id);
 s->opened=0;s->link=NULL;s->phase=0;
}
static int coh_groups_boundary_write(void*context,const unsigned char*raw,unsigned n)
{
 CohGroupsBoundaryState*s=&coh_groups_boundary;unsigned cap;(void)context;
 cap=s->kind==1?COH_SOURCE_GROUPS_OWNER_BYTES:s->kind==2?COH_SOURCE_CATALOG_MAX_BYTES:s->kind==3?COH_SNAPSHOT_MAX_BYTES:s->kind==4?COH_RESOURCE_TOTAL_MAX:s->kind==6?COH_RAW_BOUNDS_MAX_BYTES:64u*(COH_GROUPS_ELIGIBILITY_MAX_FILES+COH_GROUPS_ELIGIBILITY_MAX_DEFS+COH_GROUPS_ELIGIBILITY_MAX_REFS+2u);
 if(!s->phase||!s->opened||!s->quiet||!raw||!n||n>cap-s->kind_bytes||n>COH_GROUPS_BOUNDARY_MAX_BYTES-s->bytes)return 0;
 if(s->kind==2&&!s->kind_bytes){if(n!=sizeof(s->header))return 0;memcpy(s->header,raw,n);s->header_present=1;}
 /* Raw supplier preflights its complete ledger before this first header.
  * Charge the entire candidate output against remaining transaction capacity
  * BEFORE invoking any raw sink callback; no post-hoc admission. */
 if(s->kind==6&&!s->kind_bytes){
  unsigned bytes;
  if(n!=96u||memcmp(raw,"COHRBW01",8)||coh_raw_bounds_u32(raw+8)!=1u||coh_raw_bounds_u32(raw+12)!=96u||memcmp(raw+32,s->header,48))return 0;
  bytes=coh_raw_bounds_u32(raw+16);
  if(bytes<96u||bytes>COH_RAW_BOUNDS_MAX_BYTES||bytes>COH_GROUPS_BOUNDARY_MAX_BYTES-s->bytes)return 0;
  s->raw_expected=bytes;
 }
 if(s->kind==6&&(!s->raw_expected||s->kind_bytes>s->raw_expected||n>s->raw_expected-s->kind_bytes))return 0;
 if(s->sink.write(s->sink.context,s->id,s->kind,raw,n)!=1)return 0;
 s->kind_bytes+=n;s->bytes+=n;return 1;
}
static unsigned coh_groups_boundary_begin(void*context,const NetLink*link,int full)
{
 CohGroupsBoundaryState*s=&coh_groups_boundary;int status;(void)context;
 if(s->phase||s->blocked||full!=1||s->next==0xffffffffu||folder_cache_update_enable||!folder_cache_manual_callback_check)return 0;
 s->phase=1;s->id=++s->next;s->link=link;s->opened=s->quiet=s->bytes=s->kind_bytes=s->header_present=s->raw_expected=0;
 memset(&s->catalog,0,sizeof(s->catalog));memset(&s->snapshot,0,sizeof(s->snapshot));memset(&s->resources,0,sizeof(s->resources));memset(&s->raw_bounds,0,sizeof(s->raw_bounds));
 status=coh_resource_quiescence_begin();if(status!=1)goto fail;s->quiet=1;
 if(!coh_source_groups_prepare_owner(link,&s->owner))goto fail;
 s->opened=1;if(s->sink.open(s->sink.context,s->id)!=1)goto fail;
 s->kind=1;if(!coh_groups_boundary_write(s,s->owner.wire,sizeof(s->owner.wire)))goto fail;
 s->kind=2;s->kind_bytes=0;
 status=coh_source_catalog_export(coh_groups_boundary_write,s,s->id,&s->catalog);
 if(status||s->catalog.status||!s->header_present||s->catalog.total_bytes!=s->kind_bytes||s->catalog.emitted_bytes!=s->kind_bytes)goto fail;
 s->kind=3;s->kind_bytes=0;
 status=coh_source_runtime_snapshot_export(coh_groups_boundary_write,s,s->header,&s->catalog,&s->snapshot);
 if(status||s->snapshot.status||s->snapshot.total_bytes!=s->kind_bytes||s->snapshot.emitted_bytes!=s->kind_bytes)goto fail;
 s->kind=4;s->kind_bytes=0;
 status=coh_source_resources_export(coh_groups_boundary_write,s,s->header,&s->catalog,s->scratch,sizeof(s->scratch),&s->resources);
 if(status||s->resources.status||s->resources.total_bytes!=s->kind_bytes||s->resources.emitted_bytes!=s->kind_bytes||s->resources.client_materials_available||s->resources.client_lods_available)goto fail;
 s->kind=6;s->kind_bytes=0;
 status=coh_source_public_bounds_export(coh_groups_boundary_write,s,s->header,&s->catalog,&s->raw_bounds);
 if(status||s->raw_bounds.status||!s->raw_expected||s->raw_bounds.total_bytes!=s->raw_expected||s->raw_bounds.emitted_bytes!=s->kind_bytes||s->kind_bytes!=s->raw_expected||s->raw_bounds.files!=s->catalog.files||s->raw_bounds.slots!=s->catalog.slots)goto fail;
 s->kind=5;s->kind_bytes=0;s->phase=2;return s->id;
fail:coh_groups_boundary_abort(s,s->id);return 0;
}
static int coh_groups_boundary_record(void*context,const unsigned char*raw,unsigned n)
{(void)context;return coh_groups_boundary.phase==2&&coh_groups_boundary.kind==5&&n==64u?coh_groups_boundary_write(&coh_groups_boundary,raw,n):0;}
static int coh_groups_boundary_finish(void*context,unsigned id,const unsigned char*raw,unsigned bits,unsigned aligned,unsigned compress,const CohGroupsEligibilityReport*r)
{
 CohGroupsBoundaryState*s=&coh_groups_boundary;CohSourceGroupsOwner current;unsigned n=bits/8u+(bits%8u!=0);(void)context;
 if(s->phase!=2||s->id!=id||!s->quiet||!raw||!bits||n>COH_GROUPS_TRANSACTION_MAX_BYTES||n>COH_GROUPS_BOUNDARY_MAX_BYTES-s->bytes||!r||r->records>0xffffffffu/64u||r->records*64u!=s->kind_bytes||!coh_source_groups_prepare_owner(s->link,&current))return 0;
 /* Original worldSendUpdate changes link timestamps/world id and force_reload.
  * Compare exact owner wire except those two documented timestamp/world words. */
 memcpy(current.wire+8u+28u*4u,s->owner.wire+8u+28u*4u,8u);
 if(memcmp(current.wire,s->owner.wire,sizeof(current.wire)))return 0;
 s->phase=3;
 if(s->sink.packet(s->sink.context,id,raw,bits,aligned,compress,r,&s->catalog,&s->snapshot,&s->resources,&s->raw_bounds)!=1)return 0;
 if(coh_resource_quiescence_end()!=1){s->blocked=1;return 0;}s->quiet=0;
 if(s->sink.commit(s->sink.context,id)!=1)return 0;
 s->opened=0;s->link=NULL;s->phase=0;return 1;
}
/* Only prepares a hook value. Caller installation remains absent. Config/sink,
 * outputs and all engine storage must be disjoint; callbacks cannot reenter.
 * No callbacks or observation occur here. Existing installed hooks are untouched. */
static int coh_groups_boundary_prepare(const CohGroupsBoundarySink*sink,CohGroupsTransactionHooks*out)
{
 CohGroupsTransactionHooks h;
 if(!sink||!out||coh_groups_boundary.phase||coh_groups_boundary.blocked||!sink->open||!sink->write||!sink->packet||!sink->commit||!sink->abort)return 0;
 memset(&h,0,sizeof(h));h.begin=coh_groups_boundary_begin;h.record=coh_groups_boundary_record;h.finish=coh_groups_boundary_finish;h.abort=coh_groups_boundary_abort;h.context=&coh_groups_boundary;
 coh_groups_boundary.sink=*sink;*out=h;return 1;
}
#endif
