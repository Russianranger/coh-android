/* Exact shipped ic_post function with explicit transport/header-prefix and
 * callback doubles. Proves raw retention precedes even a refused prefix or
 * unknown/truncated command, and uses current accepted-READY state. */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include "../app/src/main/cpp/post_ready_replay.h"
#define COH_POST_READY_REPLAY_DIAGNOSTIC 1
#define COH_BOUNDED_CONTINUATION_DIAGNOSTIC 1
#define COH_NET_DECODED_MAX 4194304u
#define COH_REP_UPDATE 2u
#define COH_REP_ALLENTS 3u
enum{COH_OK,COH_INVALID,COH_UNSUPPORTED,COH_INITIAL_CAPTURE_RAW_POST=4,COH_INITIAL_CAPTURE_UPDATE=3,COH_INITIAL_CAPTURE_COMMAND_UNKNOWN=999,COH_INITIAL_ABORT_OBSERVER=5};
typedef int CohStatus;
typedef struct{const uint8_t*data;size_t size;}CohBytes;
typedef struct{CohBytes bytes;uint64_t bits,cursor;uint32_t compressed,max_bytes;}CohRepReader;
typedef struct{const uint8_t*payload;size_t payload_bytes;uint64_t payload_bits;uint32_t compressed;}CohNetOwnedMessage;
typedef struct{CohRepReader reader;unsigned version,command_kind;struct{int schema;}*map;struct{uint32_t command;}update;struct{struct{unsigned client_ready_sent,post_unclassified,abort_reason;}continuation;unsigned last_command;}d;}CohInitialMap;
static CohPostReplay sink;static unsigned raw_callbacks,normal_callbacks,prefix_calls,counted;static CohStatus prefix_result=COH_OK;
static CohStatus coh_rep_reader_bounded(CohRepReader*r,CohBytes b,uint64_t bits,unsigned compressed,unsigned maximum){if(!b.data||!b.size||b.size>maximum||!bits||bits>b.size*8)return COH_INVALID;*r=(CohRepReader){b,bits,0,compressed,maximum};return COH_OK;}
static CohStatus coh_rep_pack(CohRepReader*r,unsigned pack,uint32_t*out){(void)pack;if(r->bits<8)return COH_INVALID;*out=r->bytes.data[0];r->cursor=8;return COH_OK;}
static void ic_command_decoded(CohInitialMap*x,uint32_t command){x->command_kind=command;}
static void ic_post_count(CohInitialMap*x,const CohNetOwnedMessage*n,uint64_t now){(void)x;(void)n;(void)now;counted++;}
static CohStatus coh_rep_update_prefix(CohRepReader*r,const void*schema,unsigned command,void*out){(void)r;(void)schema;(void)command;(void)out;prefix_calls++;return prefix_result;}
static CohStatus ic_observe(CohInitialMap*x,unsigned kind){
 if(kind==COH_INITIAL_CAPTURE_RAW_POST){raw_callbacks++;post_replay_record(&sink,x->reader.bytes.data,x->reader.bytes.size,x->reader.bits,x->reader.cursor,1000+raw_callbacks,raw_callbacks,raw_callbacks,x->update.command,x->reader.compressed,0,0,7000000);}
 else if(kind==COH_INITIAL_CAPTURE_UPDATE)normal_callbacks++;else assert(0);return COH_OK;
}
/* SHIPPED_POST */
int main(void){unsigned checks=0;
#define CHECK(v) do{checks++;assert(v);}while(0)
 char path[]="/tmp/coh-rawtap-XXXXXX";int fd=mkstemp(path);CHECK(fd>=0);post_replay_init(&sink);CHECK(post_replay_start(&sink,fd));CohInitialMap x={0};struct{int schema;}map={0};x.map=(void*)&map;x.version=4;
 uint8_t snapshot[]={3,0xfe,0xed,0,0,0,0,0,0,0};CohNetOwnedMessage n={snapshot,sizeof(snapshot),80,1};prefix_result=COH_UNSUPPORTED;
 CHECK(ic_post(&x,&n,1000)==COH_UNSUPPORTED);CHECK(!raw_callbacks&&!sink.records&&prefix_calls==1);
 /* READY is accepted in this same service before the incoming packet callback. */
 x.d.continuation.client_ready_sent=1;CHECK(ic_post(&x,&n,1001)==COH_UNSUPPORTED);CHECK(raw_callbacks==1&&sink.records==1&&!normal_callbacks&&prefix_calls==2);
 snapshot[0]=2;prefix_result=COH_OK;CHECK(ic_post(&x,&n,1002)==COH_OK);CHECK(raw_callbacks==2&&sink.records==2&&normal_callbacks==1&&prefix_calls==3);
 snapshot[0]=205;CHECK(ic_post(&x,&n,1003)==COH_OK);CHECK(raw_callbacks==3&&sink.records==3&&normal_callbacks==1&&prefix_calls==3);
 n.payload_bits=1;n.payload_bytes=1;CHECK(ic_post(&x,&n,1004)==COH_INVALID);CHECK(raw_callbacks==4&&sink.records==4&&x.d.continuation.post_unclassified==1);
 n.payload_bits=100;CHECK(ic_post(&x,&n,1005)==COH_INVALID);CHECK(raw_callbacks==4&&sink.records==4&&x.d.continuation.post_unclassified==2);CHECK(counted==6);
 post_replay_finish(&sink,0);CHECK(sink.reasons==COH_POST_REPLAY_WINDOW_INCOMPLETE&&sink.finalized);close(fd);unlink(path);
 printf("{\"passed\":true,\"checks\":%u,\"prefix_refusal_retained\":true,\"unknown_command_retained\":true,\"truncated_command_retained\":true,\"same_service_READY\":true,\"source_header_and_transport_doubles\":true}\n",checks);return 0;
}
