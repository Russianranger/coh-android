/* NONSHIPPING actual worldSendUpdate observation. Include after the complete
 * boundary and source_sink.inc (unchanged path validation only is reused).
 * No source hashes, account identities, generations or detached source blobs are
 * accepted from the environment. One actual eligible source transaction may be
 * copied. The caller owns the private stable output parent exclusively.
 *
 * COHGTX01 is a streamed envelope, not an authority certificate. All chunks are
 * provisional until the kind9 commit footer is flushed, closed and renamed.
 * External admission must hash exact output/source/run/PE bytes, normalize and
 * compare the actual native opaque-owner receive, and establish CLIENT state.
 */
#ifndef COH_SOURCE_GROUPS_CAPTURE_SINK_INCLUDED
#define COH_SOURCE_GROUPS_CAPTURE_SINK_INCLUDED
#if defined(SERVER) && defined(_WIN32)
#define COH_GROUPS_CAPTURE_BYTES_MAX (160u*1024u*1024u)
typedef struct CohGroupsCaptureFile {
 HANDLE handle;
 char path[COH_CATALOG_SINK_PATH_MAX+1u],partial[COH_CATALOG_SINK_PATH_MAX+9u];
 unsigned configured,attempted,opened,created,published,failed,id,thread;
 unsigned bytes,chunks,kind_bytes[9],kind_chunks[9],packet_written;
} CohGroupsCaptureFile;
static CohGroupsCaptureFile coh_groups_capture_file;
static void coh_groups_capture_u32(unsigned char*p,unsigned v)
{p[0]=(unsigned char)v;p[1]=(unsigned char)(v>>8);p[2]=(unsigned char)(v>>16);p[3]=(unsigned char)(v>>24);}
static int coh_groups_capture_output(CohGroupsCaptureFile*s,const unsigned char*p,unsigned n)
{
 DWORD written=0;
 if(!s->opened||s->failed||!p||!n||n>COH_GROUPS_CAPTURE_BYTES_MAX-s->bytes){s->failed=1;return 0;}
 if(!WriteFile(s->handle,p,n,&written,NULL)||written!=n){s->failed=1;return 0;}
 s->bytes+=n;return 1;
}
static int coh_groups_capture_chunk(CohGroupsCaptureFile*s,unsigned kind,const unsigned char*p,unsigned n)
{
 unsigned char head[16];
 if(kind<1u||kind>9u||!n||s->chunks==0xffffffffu||n>COH_GROUPS_CAPTURE_BYTES_MAX-16u||s->bytes>COH_GROUPS_CAPTURE_BYTES_MAX-16u-n)return 0;
 coh_groups_capture_u32(head,kind);coh_groups_capture_u32(head+4,s->id);coh_groups_capture_u32(head+8,n);coh_groups_capture_u32(head+12,s->chunks);
 if(!coh_groups_capture_output(s,head,sizeof(head))||!coh_groups_capture_output(s,p,n))return 0;
 s->kind_bytes[kind-1u]+=n;s->kind_chunks[kind-1u]++;s->chunks++;return 1;
}
static int coh_groups_capture_open(void*context,unsigned id)
{
 CohGroupsCaptureFile*s=&coh_groups_capture_file;unsigned char head[64];(void)context;
 if(!s->configured||s->attempted||s->opened||!id||GetCurrentThreadId()!=s->thread)return 0;
 s->attempted=1;s->id=id;
 /* Check immediately before CREATE_NEW. A race cannot replace an old final;
  * the stable private-parent prerequisite is additional to these checks. */
 if(!coh_catalog_sink_path(s->path,(unsigned)strlen(s->path))||GetFileAttributesA(s->path)!=INVALID_FILE_ATTRIBUTES||GetLastError()!=ERROR_FILE_NOT_FOUND)return 0;
 s->handle=CreateFileA(s->partial,GENERIC_WRITE,0,NULL,CREATE_NEW,FILE_ATTRIBUTE_NORMAL,NULL);
 if(s->handle==INVALID_HANDLE_VALUE)return 0;
 s->created=s->opened=1;
 memset(head,0,sizeof(head));memcpy(head,"COHGTX01",8);
 coh_groups_capture_u32(head+8,1);coh_groups_capture_u32(head+12,sizeof(head));coh_groups_capture_u32(head+16,id);coh_groups_capture_u32(head+20,s->thread);
 return coh_groups_capture_output(s,head,sizeof(head));
}
static int coh_groups_capture_write(void*context,unsigned id,unsigned kind,const unsigned char*p,unsigned n)
{
 CohGroupsCaptureFile*s=&coh_groups_capture_file;(void)context;
 if(id!=s->id||kind<1u||kind>6u||s->packet_written||GetCurrentThreadId()!=s->thread)return 0;
 return coh_groups_capture_chunk(s,kind,p,n);
}
static int coh_groups_capture_packet(void*context,unsigned id,const unsigned char*p,unsigned bits,unsigned aligned,unsigned compress,const CohGroupsEligibilityReport*r,const CohSourceCatalogExportReport*c,const CohSourceSnapshotReport*t,const CohSourceResourceReport*q,const CohSourcePublicBoundsReport*b)
{
 CohGroupsCaptureFile*s=&coh_groups_capture_file;unsigned char raw[192];unsigned i,words[38];(void)context;
 if(id!=s->id||s->packet_written||!bits||bits/8u+(bits%8u!=0)>COH_GROUPS_TRANSACTION_MAX_BYTES||aligned>1u||compress>1u||!r||!c||!t||!q||!b||GetCurrentThreadId()!=s->thread)return 0;
 if(s->kind_bytes[0]!=COH_SOURCE_GROUPS_OWNER_BYTES||s->kind_chunks[0]!=1u||s->kind_bytes[1]!=c->emitted_bytes||s->kind_bytes[2]!=t->emitted_bytes||s->kind_bytes[3]!=q->emitted_bytes||s->kind_bytes[4]!=r->records*64u||s->kind_bytes[5]!=b->emitted_bytes)return 0;
 words[0]=1;words[1]=sizeof(raw);words[2]=id;words[3]=bits;words[4]=aligned;words[5]=compress;
 words[6]=r->records;words[7]=r->files;words[8]=r->slots;words[9]=r->roots;words[10]=r->present_files;words[11]=r->emitted_defs;words[12]=r->emitted_roots;
 words[13]=c->files;words[14]=c->definitions;words[15]=c->slots;words[16]=c->children;words[17]=c->emitted_bytes;
 words[18]=t->root_slots;words[19]=t->active_roots;words[20]=t->external_count;words[21]=t->external_children;words[22]=t->defs_crc;words[23]=t->refs_crc;words[24]=t->emitted_bytes;
 words[25]=q->records;words[26]=q->models;words[27]=q->missing_models;words[28]=q->textures;words[29]=q->model_row_comparisons;words[30]=q->emitted_bytes;words[31]=q->client_materials_available;words[32]=q->client_lods_available;
 words[33]=b->files;words[34]=b->slots;words[35]=b->public_rows;words[36]=b->emitted_bytes;words[37]=s->thread;
 memset(raw,0,sizeof(raw));memcpy(raw,"COHGPAK1",8);for(i=0;i<38u;i++)coh_groups_capture_u32(raw+8u+i*4u,words[i]);
 if(!coh_groups_capture_chunk(s,7,raw,sizeof(raw))||!coh_groups_capture_chunk(s,8,p,bits/8u+(bits%8u!=0)))return 0;
 s->packet_written=1;return 1;
}
static int coh_groups_capture_commit(void*context,unsigned id)
{
 CohGroupsCaptureFile*s=&coh_groups_capture_file;unsigned char raw[128];unsigned i;(void)context;
 /* Boundary invokes commit only after successful actual quiet release. */
 if(id!=s->id||!s->packet_written||s->failed||GetCurrentThreadId()!=s->thread)return 0;
 memset(raw,0,sizeof(raw));memcpy(raw,"COHGEND1",8);coh_groups_capture_u32(raw+8,1);coh_groups_capture_u32(raw+12,sizeof(raw));coh_groups_capture_u32(raw+16,id);coh_groups_capture_u32(raw+20,s->bytes+16u+sizeof(raw));coh_groups_capture_u32(raw+24,s->chunks+1u);coh_groups_capture_u32(raw+28,s->thread);
 for(i=0;i<8u;i++){coh_groups_capture_u32(raw+32u+i*4u,s->kind_bytes[i]);coh_groups_capture_u32(raw+64u+i*4u,s->kind_chunks[i]);}
 if(!coh_groups_capture_chunk(s,9,raw,sizeof(raw))||!FlushFileBuffers(s->handle)||!CloseHandle(s->handle))return 0;
 s->opened=0;s->handle=INVALID_HANDLE_VALUE;
 if(!MoveFileExA(s->partial,s->path,MOVEFILE_WRITE_THROUGH))return 0;
 s->created=0;s->published=1;
 printf("COH_GROUPS_TRANSACTION_V1 status=1 observation=%u bytes=%u chunks=%u packet_bytes=%u source_quiet_released=1 partial_remaining=0\n",s->id,s->bytes,s->chunks,s->kind_bytes[7]);
 return 1;
}
static void coh_groups_capture_abort(void*context,unsigned id)
{
 CohGroupsCaptureFile*s=&coh_groups_capture_file;unsigned removed=0;(void)context;
 if(id!=s->id)return;
 if(s->opened&&CloseHandle(s->handle)){s->opened=0;s->handle=INVALID_HANDLE_VALUE;}
 if(s->created&&!s->opened&&DeleteFileA(s->partial)){s->created=0;removed=1;}
 printf("COH_GROUPS_TRANSACTION_V1 status=2 observation=%u bytes=%u chunks=%u packet_bytes=%u source_quiet_released=%u partial_remaining=%u\n",s->id,s->bytes,s->chunks,s->kind_bytes[7],coh_groups_boundary.quiet?0u:1u,s->created?1u:0u);
 (void)removed;
}
static unsigned coh_groups_capture_begin(void*context,const NetLink*link,int full)
{
 CohGroupsCaptureFile*s=&coh_groups_capture_file;(void)context;
 if(!s->configured||s->attempted||GetCurrentThreadId()!=s->thread)return 0;
 return coh_groups_boundary_begin(&coh_groups_boundary,link,full);
}
/* Explicit private normal-map-startup installation. Observations occur later
 * only on this actual thread through the original worldSendUpdate call. The
 * real guard checks initialized loader/empty queues and folder callback mode
 * on every observation. Merely installing never captures startup source blobs. */
void coh_source_groups_capture_install(void)
{
 CohGroupsCaptureFile*s=&coh_groups_capture_file;CohGroupsBoundarySink sink;CohGroupsTransactionHooks hooks;DWORD length;
 if(s->configured||s->attempted||coh_groups_transaction_hooks.begin||coh_groups_transaction_hooks.record||coh_groups_transaction_hooks.finish||coh_groups_transaction_hooks.abort||coh_groups_transaction_active)return;
 memset(s,0,sizeof(*s));s->handle=INVALID_HANDLE_VALUE;
 length=GetEnvironmentVariableA("COH_NATIVE_GROUPS_TRANSACTION_OUTPUT",s->path,sizeof(s->path));
 if(!length)return;
 if(length>=sizeof(s->path)||!coh_catalog_sink_path(s->path,length))return;
 memcpy(s->partial,s->path,length);memcpy(s->partial+length,".partial",9);s->thread=GetCurrentThreadId();
 memset(&sink,0,sizeof(sink));sink.open=coh_groups_capture_open;sink.write=coh_groups_capture_write;sink.packet=coh_groups_capture_packet;sink.commit=coh_groups_capture_commit;sink.abort=coh_groups_capture_abort;sink.context=s;
 if(!s->thread||!coh_groups_boundary_prepare(&sink,&hooks))return;
 hooks.begin=coh_groups_capture_begin;s->configured=1;coh_groups_transaction_hooks=hooks;
}
#else
void coh_source_groups_capture_install(void) { }
#endif
#endif
