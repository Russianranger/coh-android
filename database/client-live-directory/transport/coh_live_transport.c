#include "coh_live_transport.h"
#include "coh_live_directory_batch.h"
#include <string.h>
#include <limits.h>

struct CohLiveTransportCursor {
 CohLiveCursor live;
 uint32_t handle;
 uint64_t device,inode;
};
static void put32(unsigned char *p,uint32_t v) {
 p[0]=(unsigned char)v;p[1]=(unsigned char)(v>>8);
 p[2]=(unsigned char)(v>>16);p[3]=(unsigned char)(v>>24);
}
static uint64_t get64(const unsigned char *p) {
 return (uint64_t)cohLiveU32(p)|((uint64_t)cohLiveU32(p+4)<<32);
}
static void closePeer(CohLiveTransport *t) {
 if(!t->peer_closed) {t->peer_closed=1;if(t->io.close)t->io.close(t->io.context);}
}
static int fail(CohLiveTransport *t,CohLiveTransportCursor *c,CohLiveTransportReason why) {
 if(!t->dead) {
  t->dead=1;t->result=(t->rows_returned||why==COH_TRANSPORT_REASON_PEER_TERMINAL)?
   COH_TRANSPORT_TERMINAL:COH_TRANSPORT_INITIAL_DECLINE;
  t->reason=why;t->failure_handle=c?c->handle:0;
  t->failure_cursor_rows=c?c->live.rows_returned:0;
  t->failure_request_sequence=t->request_sequence;
 }
 closePeer(t);return t->result;
}
static CohLiveTransportCursor *find(CohLiveTransport *t,uint32_t handle,uint32_t *slot) {
 uint32_t i;
 if(handle)for(i=0;i<COH_TRANSPORT_MAX_CURSORS;i++)
  if(t->cursors[i]&&t->cursors[i]->handle==handle) {if(slot)*slot=i;return t->cursors[i];}
 return NULL;
}
static int exactWrite(CohLiveTransport *t,CohLiveTransportCursor *c,const unsigned char *p,uint32_t bytes) {
 while(bytes) {
  int32_t got=t->io.write(t->io.context,p,bytes);
  if(got<=0||(uint32_t)got>bytes)return fail(t,c,COH_TRANSPORT_REASON_WRITE);
  p+=got;bytes-=(uint32_t)got;
 }
 return COH_TRANSPORT_OK;
}
static int exactRead(CohLiveTransport *t,CohLiveTransportCursor *c,unsigned char *p,uint32_t bytes) {
 while(bytes) {
  int32_t got=t->io.read(t->io.context,p,bytes);
  if(got<=0||(uint32_t)got>bytes)return fail(t,c,COH_TRANSPORT_REASON_READ);
  p+=got;bytes-=(uint32_t)got;
 }
 return COH_TRANSPORT_OK;
}
/* Canonical absolute POSIX paths only: no empty component, dot traversal,
 * drive syntax, backslash, trailing slash (except /), control/non-ASCII byte.
 * Actual registered guest-root containment remains the native wrapper's job. */
static uint32_t pathBytes(const char *p) {
 uint32_t n=0,start=1,i;
 if(!p||p[0]!='/')return 0;
 while(n<=COH_TRANSPORT_MAX_PATH&&p[n]) {
  unsigned char c=(unsigned char)p[n];
  if(c<32||c>=127||c=='\\'||c==':')return 0;
  n++;
 }
 if(!n||n>COH_TRANSPORT_MAX_PATH)return 0;
 if(n==1)return 1;
 if(p[n-1]=='/')return 0;
 for(i=1;i<=n;i++)if(i==n||p[i]=='/') {
  uint32_t length=i-start;
  if(!length||(length==1&&p[start]=='.')||
     (length==2&&p[start]=='.'&&p[start+1]=='.'))return 0;
  start=i+1;
 }
 return n;
}
static int exchange(CohLiveTransport *t,CohLiveTransportCursor *c,uint32_t command,
 const char *path,uint32_t path_length,uint32_t *payload) {
 unsigned char request[COH_TRANSPORT_REQUEST_BYTES],reply[COH_TRANSPORT_REPLY_BYTES];
 uint32_t status,length;
 if(t->dead)return t->result;
 if(t->request_sequence==UINT32_MAX)return fail(t,c,COH_TRANSPORT_REASON_SEQUENCE);
 t->request_sequence++;
 memset(request,0,sizeof(request));memcpy(request,"COHLDIR1",8);
 put32(request+8,1);put32(request+12,command);memcpy(request+16,t->operation,16);
 memcpy(request+32,t->nonce,32);put32(request+64,t->request_sequence);
 memcpy(request+68,c->live.directory,16);put32(request+84,path_length);
 put32(request+88,COH_TRANSPORT_REQUEST_BYTES+path_length);
 if(exactWrite(t,c,request,sizeof(request))!=COH_TRANSPORT_OK)return t->result;
 if(path_length&&exactWrite(t,c,(const unsigned char *)path,path_length)!=COH_TRANSPORT_OK)return t->result;
 if(exactRead(t,c,reply,sizeof(reply))!=COH_TRANSPORT_OK)return t->result;
 t->backend_reply_observed=1;t->backend_status=cohLiveU32(reply+12);
 t->backend_error=cohLiveU32(reply+24);t->reply_sequence=cohLiveU32(reply+16);
 if(memcmp(reply,"COHRSP1\0",8))return fail(t,c,COH_TRANSPORT_REASON_REPLY_MAGIC);
 if(cohLiveU32(reply+8)!=1)return fail(t,c,COH_TRANSPORT_REASON_REPLY_VERSION);
 status=t->backend_status;length=cohLiveU32(reply+20);
 if(status>2)return fail(t,c,COH_TRANSPORT_REASON_REPLY_STATUS);
 if(t->reply_sequence!=t->request_sequence)return fail(t,c,COH_TRANSPORT_REASON_REPLY_SEQUENCE);
 if(cohLiveU32(reply+28)!=0)return fail(t,c,COH_TRANSPORT_REASON_REPLY_RESERVED);
 if(length>COH_LIVE_MAX_BYTES||(status&&length)||
    (!status&&command==1&&length!=32)||(!status&&command==3&&length)||
    (!status&&command==2&&length<COH_LIVE_HEADER_BYTES))
  return fail(t,c,COH_TRANSPORT_REASON_REPLY_PAYLOAD);
 if(status)return fail(t,c,status==1?COH_TRANSPORT_REASON_PEER_DECLINE:COH_TRANSPORT_REASON_PEER_TERMINAL);
 if(t->backend_error)return fail(t,c,COH_TRANSPORT_REASON_REPLY_ERROR);
 if(length&&exactRead(t,c,t->receive_frame,length)!=COH_TRANSPORT_OK)return t->result;
 *payload=length;return COH_TRANSPORT_OK;
}
int cohLiveTransportInit(CohLiveTransport *t,const CohLiveTransportIo *io,
 const unsigned char operation[16],const unsigned char nonce[32]) {
 if(!t)return COH_TRANSPORT_INITIAL_DECLINE;
 memset(t,0,sizeof(*t));t->result=COH_TRANSPORT_OK;
 if(io)t->io=*io;
 if(!io||!io->read||!io->write||!io->close||!io->allocate||!io->release||!operation||!nonce)
  return fail(t,NULL,COH_TRANSPORT_REASON_CONFIG);
 memcpy(t->operation,operation,16);memcpy(t->nonce,nonce,32);return COH_TRANSPORT_OK;
}
int cohLiveTransportOpen(CohLiveTransport *t,const char *path,
 const unsigned char directory[16],uint64_t expected_device,
 uint64_t expected_native_inode,uint32_t *handle) {
 CohLiveTransportCursor *c;uint32_t i,slot=COH_TRANSPORT_MAX_CURSORS,length,payload=0;
 if(handle)*handle=0;
 if(!t)return COH_TRANSPORT_INITIAL_DECLINE;
 if(t->shutdown_complete)return t->dead?t->result:COH_TRANSPORT_INITIAL_DECLINE;
 if(t->dead)return t->result;
 if(!handle||!directory)return fail(t,NULL,COH_TRANSPORT_REASON_CONFIG);
 length=pathBytes(path);if(!length)return fail(t,NULL,COH_TRANSPORT_REASON_PATH);
 for(i=0;i<COH_TRANSPORT_MAX_CURSORS;i++) {
  if(t->cursors[i]) {if(!memcmp(t->cursors[i]->live.directory,directory,16))
    return fail(t,t->cursors[i],COH_TRANSPORT_REASON_DUPLICATE_TOKEN);}
  else if(slot==COH_TRANSPORT_MAX_CURSORS)slot=i;
 }
 if(slot==COH_TRANSPORT_MAX_CURSORS)return fail(t,NULL,COH_TRANSPORT_REASON_LIMIT);
 if(t->handle_sequence==UINT32_MAX)return fail(t,NULL,COH_TRANSPORT_REASON_SEQUENCE);
 if(!t->receive_frame) {
  t->receive_frame=(unsigned char *)t->io.allocate(t->io.context,COH_LIVE_MAX_BYTES);
  if(!t->receive_frame)return fail(t,NULL,COH_TRANSPORT_REASON_ALLOCATION);
 }
 c=(CohLiveTransportCursor *)t->io.allocate(t->io.context,sizeof(*c));
 if(!c)return fail(t,NULL,COH_TRANSPORT_REASON_ALLOCATION);
 cohLiveInit(&c->live,t->operation,directory);c->handle=++t->handle_sequence;
 t->cursors[slot]=c;t->active_cursors++;
 if(exchange(t,c,1,path,length,&payload)!=COH_TRANSPORT_OK)return t->result;
 c->device=get64(t->receive_frame);c->inode=get64(t->receive_frame+8);
 t->observed_device=c->device;t->observed_inode=c->inode;
 if(cohLiveU32(t->receive_frame+16)!=1||cohLiveU32(t->receive_frame+20)!=1)
  return fail(t,c,COH_TRANSPORT_REASON_ACK_RECIPE);
 if(get64(t->receive_frame+24)!=0)return fail(t,c,COH_TRANSPORT_REASON_ACK_RESERVED);
 if(c->device!=expected_device||c->inode!=expected_native_inode)
  return fail(t,c,COH_TRANSPORT_REASON_ACK_IDENTITY);
 *handle=c->handle;return COH_TRANSPORT_OK;
}
int cohLiveTransportIdentity(const CohLiveTransport *t,uint32_t handle,
 uint64_t *device,uint64_t *inode) {
 uint32_t i;
 if(!t||!device||!inode||t->dead||t->shutdown_complete)return 0;
 for(i=0;i<COH_TRANSPORT_MAX_CURSORS;i++)if(t->cursors[i]&&t->cursors[i]->handle==handle) {
  *device=t->cursors[i]->device;*inode=t->cursors[i]->inode;return 1;
 }
 return 0;
}
int cohLiveTransportNext(CohLiveTransport *t,uint32_t handle,const unsigned char **wfd) {
 CohLiveTransportCursor *c;const unsigned char *row;uint32_t payload=0;
 if(wfd)*wfd=NULL;
 if(!t)return COH_TRANSPORT_INITIAL_DECLINE;
 if(t->shutdown_complete)return t->dead?t->result:COH_TRANSPORT_INITIAL_DECLINE;
 if(t->dead)return t->result;
 c=find(t,handle,NULL);if(!wfd||!c)return fail(t,c,COH_TRANSPORT_REASON_HANDLE);
 if(c->live.finished)return COH_TRANSPORT_END;
 row=cohLiveTake(&c->live);
 if(!row) {
  if(exchange(t,c,2,NULL,0,&payload)!=COH_TRANSPORT_OK)return t->result;
  if(!cohLiveSubmit(&c->live,t->receive_frame,payload))return fail(t,c,COH_TRANSPORT_REASON_BATCH);
  row=cohLiveTake(&c->live);
  if(!row) {if(c->live.finished)return COH_TRANSPORT_END;
   return fail(t,c,COH_TRANSPORT_REASON_BATCH);}
 }
 t->rows_returned++;*wfd=row;return COH_TRANSPORT_OK;
}
int cohLiveTransportClose(CohLiveTransport *t,uint32_t *handle) {
 CohLiveTransportCursor *c;uint32_t slot,payload=0;int result;
 if(!t)return COH_TRANSPORT_INITIAL_DECLINE;
 if(t->shutdown_complete)return t->dead?t->result:COH_TRANSPORT_INITIAL_DECLINE;
 if(!handle||!*handle)return t->dead?t->result:fail(t,NULL,COH_TRANSPORT_REASON_HANDLE);
 c=find(t,*handle,&slot);
 if(!c)return t->dead?t->result:fail(t,NULL,COH_TRANSPORT_REASON_HANDLE);
 result=t->dead?t->result:exchange(t,c,3,NULL,0,&payload);
 t->io.release(t->io.context,c);t->cursors[slot]=NULL;t->active_cursors--;*handle=0;
 return result;
}
void cohLiveTransportShutdown(CohLiveTransport *t) {
 uint32_t i;if(!t||t->shutdown_complete)return;
 closePeer(t);
 for(i=0;i<COH_TRANSPORT_MAX_CURSORS;i++)if(t->cursors[i]) {
  t->io.release(t->io.context,t->cursors[i]);t->cursors[i]=NULL;
 }
 t->active_cursors=0;
 if(t->receive_frame) {t->io.release(t->io.context,t->receive_frame);t->receive_frame=NULL;}
 t->shutdown_complete=1;
}
