/* NONSHIPPING. Include once after the accepted fresh GROUPS profile in
 * groupnetsend.c. Does not reuse its pre-ready initial-eligibility predicate. */
#include "coh_server_initial_ledger.c"
#include <errno.h>
static CohSIOLedger coh_sio_ledger;
static unsigned coh_sio_started,coh_sio_configured,coh_sio_write_failed,coh_sio_writes;
static DWORD coh_sio_thread;
static HANDLE coh_sio_handle=INVALID_HANDLE_VALUE;
static BY_HANDLE_FILE_INFORMATION coh_sio_file;
static CohSIOReport coh_sio_last_written;
static int coh_sio_registered(const NetLink*link){
 unsigned i,found=0;
 if(!link||!net_links.links||net_links.links->size<=0||(unsigned)net_links.links->size>65536u||!net_links.links->storage||net_links.links->maxSize<net_links.links->size)return 0;
 /* No dereference of a retained link key until current registered membership. */
 for(i=0;i<(unsigned)net_links.links->size;i++)if(net_links.links->storage[i]==link)found++;
 return found==1;
}
static int coh_sio_fresh_key(const NetLink*link,CohSIOKey*out){
 const ClientLink*client;const Entity*e;const Character*character;CohSIOKey key;
 if(!coh_sio_registered(link))return 0;
 client=(const ClientLink*)link->userData;
 if(!client||client->link!=link||!client->entity)return 0;
 e=client->entity;
 if(e->client!=client||e->owner<1||e->owner>=MAX_ENTITIES_PRIVATE||entities_max<1||entities_max>MAX_ENTITIES_PRIVATE||e->owner>=entities_max||entities[e->owner]!=e||!e->id||e->db_id<=0)return 0;
 if(entity_state[e->owner]!=ENTITY_IN_USE&&entity_state[e->owner]!=ENTITY_SLEEPING)return 0;
 if(ENTTYPE(e)!=ENTTYPE_PLAYER||!e->owned||!e->pl)return 0;
 character=e->pchar;if(!character||character->entParent!=e||!character_IsInitialized(e->pchar))return 0;
 if(link->type!=NLT_UDP||!link->connected||link->pending||link->connecting||link->disconnected||link->destroyed||link->removedFromMasterList||link->protocolVersion>5u)return 0;
 memset(&key,0,sizeof(key));key.link=link;key.client=client;key.entity=e;key.character=character;key.uid=link->UID;key.connection_id=link->connection_id;key.connect_id=link->connect_id;key.entity_id=e->id;key.dbid=(unsigned)e->db_id;key.server_index=(unsigned)e->owner;key.auth_id=e->auth_id;key.protocol=link->protocolVersion;*out=key;return 1;
}
static int coh_sio_file_valid(const BY_HANDLE_FILE_INFORMATION*info){return !(info->dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT))&&info->nNumberOfLinks==1u;}
static int coh_sio_same_file(void){BY_HANDLE_FILE_INFORMATION info;return coh_sio_handle!=INVALID_HANDLE_VALUE&&GetFileInformationByHandle(coh_sio_handle,&info)&&coh_sio_file_valid(&info)&&info.dwVolumeSerialNumber==coh_sio_file.dwVolumeSerialNumber&&info.nFileIndexHigh==coh_sio_file.nFileIndexHigh&&info.nFileIndexLow==coh_sio_file.nFileIndexLow;}
static int coh_sio_open(void){
 char path[COH_CATALOG_SINK_PATH_MAX+1u];DWORD n,attrs;BY_HANDLE_FILE_INFORMATION info;
 n=GetEnvironmentVariableA("COH_NATIVE_INITIAL_SEND_LEDGER_OUTPUT",path,sizeof(path));
 if(!n||n>=sizeof(path)||!coh_catalog_sink_path(path,n))return 0;
 attrs=GetFileAttributesA(path);if(attrs==INVALID_FILE_ATTRIBUTES||(attrs&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT)))return 0;
 coh_sio_handle=CreateFileA(path,GENERIC_WRITE,0,NULL,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,NULL);
 if(coh_sio_handle==INVALID_HANDLE_VALUE)return 0;
 if(!GetFileInformationByHandle(coh_sio_handle,&info)||!coh_sio_file_valid(&info)||info.nFileSizeHigh||info.nFileSizeLow){CloseHandle(coh_sio_handle);coh_sio_handle=INVALID_HANDLE_VALUE;return 0;}
 coh_sio_file=info;return 1;
}
static void coh_sio_flush(void){
 CohSIOReport view;char raw[COH_SIO_MAX_JSON];DWORD written=0;LARGE_INTEGER zero;int n,ok;
 if(!coh_sio_configured||coh_sio_write_failed||GetCurrentThreadId()!=coh_sio_thread)return;
 coh_sio_snapshot(&coh_sio_ledger,&view);
 /* Export only first-reached milestones, ready-state changes, and tick
  * powers of two at the TICK checkpoint. Repeated intermediate stages do
  * not cause I/O. A hard 128-write diagnostic limit bounds other changes. */
 if(view.stop==COH_SIO_ACTIVE&&view.reached_mask==coh_sio_last_written.reached_mask&&view.ready_seen_mask==coh_sio_last_written.ready_seen_mask&&view.last_sent_self==coh_sio_last_written.last_sent_self&&!(view.stage==COH_SIO_TICK&&view.tick_seen&&((view.tick_seen&(view.tick_seen-1u))==0)))return;
 if(coh_sio_writes==128u&&view.stop==COH_SIO_ACTIVE){coh_sio_refuse(&coh_sio_ledger,COH_SIO_LIMIT);coh_sio_snapshot(&coh_sio_ledger,&view);}
 coh_sio_writes++;n=coh_sio_json(&view,raw,sizeof(raw));zero.QuadPart=0;
 ok=n>0&&coh_sio_same_file()&&SetFilePointerEx(coh_sio_handle,zero,NULL,FILE_BEGIN)&&WriteFile(coh_sio_handle,raw,(DWORD)n,&written,NULL)&&written==(DWORD)n&&SetEndOfFile(coh_sio_handle)&&FlushFileBuffers(coh_sio_handle)&&coh_sio_same_file();
 if(!ok){coh_sio_write_failed=1;coh_sio_refuse(&coh_sio_ledger,COH_SIO_SINK);
  /* Best-effort invalidate an earlier checkpoint on the SAME held file.
   * A failed invalidation leaves only a historical checkpoint, never a
   * guarantee of later progress absence or of continued sink health. */
  if(coh_sio_same_file()&&SetFilePointerEx(coh_sio_handle,zero,NULL,FILE_BEGIN)){(void)SetEndOfFile(coh_sio_handle);(void)FlushFileBuffers(coh_sio_handle);}
 }
 else coh_sio_last_written=view;
 if(!ok||view.stop!=COH_SIO_ACTIVE){(void)CloseHandle(coh_sio_handle);coh_sio_handle=INVALID_HANDLE_VALUE;}
}
void coh_sio_source_bind_groups(const void*opaque){
 DWORD saved_error=GetLastError();int saved_errno=errno;CohSIOKey key;const NetLink*link=opaque;
 if(GetCurrentThreadId()!=coh_groups_capture_file.thread){SetLastError(saved_error);errno=saved_errno;return;}
 if(!coh_sio_started){coh_sio_started=1;coh_sio_init(&coh_sio_ledger);coh_sio_thread=GetCurrentThreadId();
  if(coh_sio_thread&&coh_sio_thread==coh_groups_capture_file.thread&&coh_groups_capture_file.configured&&coh_sio_open()){
   coh_sio_configured=1;if(coh_sio_fresh_key(link,&key))coh_sio_bind(&coh_sio_ledger,&key,coh_sio_thread);else coh_sio_refuse(&coh_sio_ledger,COH_SIO_OWNER);coh_sio_flush();
  }
 }SetLastError(saved_error);errno=saved_errno;
}
void coh_sio_source_event(unsigned event,const void*opaque,const void*entity,const void*packet,uint32_t a,uint32_t b,uint32_t c){
 DWORD saved_error=GetLastError();int saved_errno=errno;CohSIOKey key;const NetLink*link=opaque;
 if(GetCurrentThreadId()==coh_groups_capture_file.thread&&coh_sio_configured&&coh_sio_ledger.report.stop==COH_SIO_ACTIVE&&link==coh_sio_ledger.key.link){
  if(!coh_sio_fresh_key(link,&key))coh_sio_refuse(&coh_sio_ledger,COH_SIO_OWNER);
  else if(event!=COH_SIO_FULL_ENTER&&entity!=key.entity)coh_sio_refuse(&coh_sio_ledger,COH_SIO_OWNER);
  else coh_sio_record(&coh_sio_ledger,&key,coh_sio_thread,(CohSIOEvent)event,packet,a,b,c);
  coh_sio_flush();
 }SetLastError(saved_error);errno=saved_errno;
}
void coh_sio_source_character(unsigned event,const void*entity,const void*packet){
 DWORD saved_error=GetLastError();int saved_errno=errno;
 if(GetCurrentThreadId()==coh_groups_capture_file.thread&&coh_sio_configured&&coh_sio_ledger.report.stop==COH_SIO_ACTIVE&&entity==coh_sio_ledger.key.entity)coh_sio_source_event(event,coh_sio_ledger.key.link,entity,packet,0,0,0);
 SetLastError(saved_error);errno=saved_errno;
}
void coh_sio_source_finish_entity(const void*entity,const void*packet){
 DWORD saved_error=GetLastError();int saved_errno=errno;
 if(GetCurrentThreadId()==coh_groups_capture_file.thread&&coh_sio_configured&&coh_sio_ledger.report.stop==COH_SIO_ACTIVE&&entity==coh_sio_ledger.key.entity)coh_sio_source_event(COH_SIO_FINISH_ENTITY,coh_sio_ledger.key.link,entity,packet,0,0,0);
 SetLastError(saved_error);errno=saved_errno;
}
void coh_sio_source_retire_entity(const void*entity){
 DWORD saved_error=GetLastError();int saved_errno=errno;
 if(GetCurrentThreadId()==coh_groups_capture_file.thread&&coh_sio_configured&&coh_sio_ledger.report.stop==COH_SIO_ACTIVE&&entity==coh_sio_ledger.key.entity){coh_sio_refuse(&coh_sio_ledger,COH_SIO_OWNER);coh_sio_flush();}
 SetLastError(saved_error);errno=saved_errno;
}
void coh_sio_source_send_return(uintptr_t packet,int result){
 DWORD saved_error=GetLastError();int saved_errno=errno;
 if(GetCurrentThreadId()==coh_groups_capture_file.thread&&coh_sio_configured&&coh_sio_ledger.report.stop==COH_SIO_ACTIVE&&coh_sio_ledger.send_pending&&packet==coh_sio_ledger.packet){coh_sio_send_return(&coh_sio_ledger,coh_sio_thread,result);coh_sio_flush();}
 SetLastError(saved_error);errno=saved_errno;
}
