/* Test-only platform and ownership shims. Not linked into an APK or server.
 * Original bodies are generated separately, pinned and never instrumented.
 * Only trusted, native-produced loopback datagrams may reach these bodies. */
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <zlib.h>
#include "coh_auth.h"
typedef uint32_t U32; typedef uint8_t U8; typedef int bool;
typedef enum {Read,Write} BitStreamMode;
typedef enum {BSE_NOERROR,BSE_OVERFLOW,BSE_OVERRUN,BSE_TYPEMISMATCH,BSE_COMPRESSION} BitStreamError;
typedef struct {unsigned int byte,bit;} BitStreamCursor;
typedef struct BitStream BitStream; typedef int (*MemoryAllocator)(BitStream*);
struct BitStream {BitStreamMode mode;BitStreamCursor cursor;unsigned char *data;unsigned int size,maxSize,bitLength;MemoryAllocator memAllocator;void *userData;unsigned int byteAlignedMode;BitStreamError errorFlags;};
typedef enum {COMMCONTROL_IDLE,COMMCONTROL_CONNECT,COMMCONTROL_CONNECT_SERVER_ACK,COMMCONTROL_CONNECT_CLIENT_ACK,COMMCONTROL_CONNECT_SERVER_ACK_ACK,COMMCONTROL_DISCONNECT,COMMCONTROL_DISCONNECT_ACK,COMMCONTROL_BUFFER_RESIZE} CommControlCommand;
typedef struct {void *value;} SimpleSetElement;
typedef struct NetLink NetLink;
typedef struct {BitStream stream;U32 checksum,truncatedID,sib_count,sib_partnum,sib_id,hasDebugInfo,compress,ordered,ordered_id,id,UID,reliable;NetLink *link;U32 storage[4096];} Packet;
struct NetLink {int ack_count;U32 ids_toack[32];int compressionAllowed,orderedAllowed,orderedDefault,compressionDefault,controlCommandsSeparate;unsigned protocolVersion;U32 connect_id;int connected,encrypted,decrypt_on,encrypt_on;U32 private_key[16],public_key[16],shared_secret[16];CohBlowfish blowfish_ctx;void *parentNetLinkList;U32 recvBufferMaxSize,recvBufferSize,idlePacketsReceived;struct {struct{struct{U32 S_addr;}S_un;}sin_addr;int sin_port;}addr;int simulateNetworkCondition,simulatedPacketLostRate;int pingHistory,recvHistory,reliablePacketsArray;U32 idAck,recv_ack_count,recv_acks[32],duplicate_packet_recv_count;SimpleSetElement *receivedPacketID;};
#define false 0
#define true 1
#define xcase break; case
#define BSASSERT(x) assert(x)
#define devassert(x) assert(x), (x)
#define MAX(a,b) ((a)>(b)?(a):(b))
#define MIN(a,b) ((a)<(b)?(a):(b))
#define ROUND_BITS_UP(x) (((x)+7)&~7)
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define AINRANGE(x,a) ((unsigned)(x)<ARRAY_SIZE(a))
#define PACKET_MISCINFO_SIZE_WITH_DEBUG 200
#define PACKET_MISCINFO_SIZE_WITHOUT_DEBUG 36
#define PACKET_HEADER_SIZE 8
#define COMM_CONNECT 1
#define COMM_CONTROLCOMMAND 0
#define COMM_OLDMAX_CMD 8
#define MAX_PKTACKS 32
#define S32_TO_PTR(x) ((void*)(uintptr_t)(x))
#define LOG(...) ((void)0)
#define netLog(...) ((void)0)
#define ReceiveBuffer 2
#define RETURN_ON_BAD_STREAM if (pak->stream.errorFlags) return -1;
static unsigned int g_packetsizes_one[33],g_packetsizes_success[33],g_packetsizes_failed[33];
static int printPacketSendData,printPacketGetData,g_bAssertOnBitStreamError;
static int auto_bins[]={2,10,24,32};
static int count_bits(unsigned int val){int n=0;do{val>>=1;n++;}while(val);return n;}
void bsAlignByte(BitStream*);unsigned int bsGetCursorBitPosition(BitStream*);unsigned int bsGetBitLength(BitStream*);
void bsWriteBits(BitStream*,int,unsigned int);void bsWriteBitsPack(BitStream*,int,unsigned int);unsigned int bsReadBitsPack(BitStream*,int);int bsGetLengthWriteBitsPack(BitStream*,int,U32);
void pktSendBitsAuto(Packet*,U32);U32 pktGetBitsAuto(Packet*);Packet *pktCreateControlCmd(NetLink*,CommControlCommand);void applyNetworkVersionToLink(NetLink*,unsigned);void applyNetworkVersionToPacket(NetLink*,Packet*);
static void bsTypedWriteBits(BitStream *b,int n,U32 v){abort();}
static void bsTypedWriteBitsPack(BitStream *b,int n,U32 v){abort();}
static U32 bsTypedReadBitsPack(BitStream *b,int n){abort();}
static U32 bsTypedReadBits(BitStream *b,int n){abort();}
static void bsTypedWriteBitsArray(BitStream *b,int n,const void *v){abort();}
static void bsTypedReadBitsArray(BitStream *b,int n,void *v){abort();}
static void bsTypedAlignBitsArray(BitStream *b){abort();}
static int pktGetLengthBitsPack(Packet *p,int n,U32 v){return bsGetLengthWriteBitsPack(&p->stream,n,v);}
static int cmpU32(const void *a,const void *b){U32 x=*(const U32*)a,y=*(const U32*)b;return (x>y)-(x<y);}
static void lnkFlush(NetLink *l){(void)l;}
static int packetCanUseEncryption(void){return 1;}
static void cryptMakeKeyPair(U32 *a,U32 *b){assert(coh_auth_dh_keypair(coh_auth_openssl_provider(),(U8*)a,(U8*)b)==COH_OK);}
static void cryptMakeSharedSecret(U32 *out,U32 *a,U32 *b){const CohAuthCrypto *p=coh_auth_openssl_provider();assert(p->shared(p->context,(U8*)a,(U8*)b,(U8*)out)==COH_OK);}
static U8 md5_input[64];
static void cryptMD5Update(U8 *v,int n){assert(n==64);memcpy(md5_input,v,64);}
static void cryptMD5Final(U32 *out){const CohAuthCrypto *p=coh_auth_openssl_provider();assert(p->md5(p->context,(CohBytes){md5_input,64},(U8*)out)==COH_OK);coh_auth_wipe(md5_input,64);}
static void cryptBlowfishInitU32(CohBlowfish *key,U32 *words,unsigned n){assert(n==4);assert(coh_bf_init(key,(U8*)words,16)==0);}

static Packet *pktCreateImp(const char*,int);
static int pktSend(Packet **,NetLink*);
static void lnkBatchSend(NetLink *l){(void)l;}
static int discarded;
static void netDiscardDeadLink(NetLink *l){discarded=1;}
static unsigned int getDefaultNetworkVersion(void){return 5;}
static void applyDefaultNetworkVersionToLink(NetLink *l){abort();}
static NetLink *createNetLink(void){abort();}
static int randInt(int n){abort();}
static U32 timerCpuTicks(void){return 1;}
static void pingBatchBegin(void *p){(void)p;}
static void pingBatchEnd(void *p){(void)p;}
static unsigned ack_observed;
static int pktProcessAck(U32 id,NetLink *l,U32 ticks){(void)l;(void)ticks;ack_observed++;return 0;}
static void arrayCompactStable(void *p){(void)p;}
static SimpleSetElement *sSetFindElement(SimpleSetElement *s,void *v){SimpleSetElement *e=&s[(uintptr_t)v%16384];return e->value?e:NULL;}
static void sSetAddElement(SimpleSetElement *s,void *v){s[(uintptr_t)v%16384].value=v;}
static void pktAddHist(void *h,int a,int b){(void)h;(void)a;(void)b;}
static void netIdleEx(NetLink *l,int a,int b,int c){abort();}
static void netLinkSetBufferSize(NetLink *l,int t,U32 size){l->recvBufferSize=size;}
