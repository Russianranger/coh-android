/* Controlled IO-completion fixture, not a Winsock socket or account handler.
 * Exact source receiver/dispatch functions are inserted below. Crypto uses an
 * aligned scratch adapter around original packet functions and qualified BF. */
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <algorithm>
extern "C" {
#include "coh_native_core.h"
}
static_assert(sizeof(unsigned int)==4,"original checksum words");
using DWORD=uint32_t;using SOCKET=int;using BOOL=int;using LPOVERLAPPED=void*;
#define __int64 int64_t
#define BUFFER_SIZE 8192
#define AQ_MAX 6
#define LOG_ERROR 1
#define LOG_DEBUG 2
#define ERROR_IO_PENDING 997
#define WSAENOTSOCK 10038
#define WSAECONNRESET 10054
#define WSAECONNABORTED 10053
#define _ASSERTE(x) do{if(!(x))std::abort();}while(0)
static struct {int PacketSizeType=3;} config;
static struct {template<class...A>void AddLog(int,const char*,A...){}} logger;
static unsigned checks,completions,decodes,dispatches;
#define CHECK(x) do{++checks;if(!(x)){std::fprintf(stderr,"controlled completion check %d\n",__LINE__);return false;}}while(0)
struct WSABUF {DWORD len;char*buf;};
static WSABUF pending{};static bool pending_read,recv_failure;
static int WSARecv(SOCKET,WSABUF*b,int n,DWORD*,DWORD*,void*,void*){
    if(recv_failure)return 1;
    if(n!=1||pending_read||!b->len||b->len>BUFFER_SIZE)std::abort();pending=*b;pending_read=true;return 1;
}
static int GetLastError(){return recv_failure?WSAECONNRESET:ERROR_IO_PENDING;}
static DWORD GetTickCount(){return 1000;}
static int InterlockedIncrement(int*p){return ++*p;}
static int InterlockedDecrement(int*p){return --*p;}
static int g_hIOCompletionPort;
struct CIOBuffer {
    alignas(8) char m_buffer[BUFFER_SIZE]{};DWORD m_size=0;int m_ref=1;
    void AddRef(){if(m_ref<1)std::abort();++m_ref;}
    void Release(){if(m_ref<1)std::abort();--m_ref;}
    static CIOBuffer*Alloc();
};
static CIOBuffer buffers[16];static unsigned allocated;
CIOBuffer*CIOBuffer::Alloc(){if(allocated>=16)std::abort();auto*p=&buffers[allocated++];*p=CIOBuffer{};return p;}
class CIOSocket {
public:
    CIOBuffer*m_pReadBuf=CIOBuffer::Alloc();SOCKET m_hSocket=1;int m_overlappedRead=0,m_overlappedWrite=0;
    bool closed=false;int refs=1;
    virtual ~CIOSocket(){};virtual void OnRead()=0;void Read(DWORD);void OnReadCallback(DWORD);void OnIOCallback(BOOL,DWORD,LPOVERLAPPED);
    void OnWriteCallback(DWORD){std::abort();}int GetRef(){return refs;}
    void AddRef(){if(refs<1)std::abort();++refs;}void ReleaseRef(){if(refs<1)std::abort();--refs;}
    void CloseSocket(){if(!closed){closed=true;ReleaseRef();}}
};
class CSocketServerEx;
struct CPacketServerEx {
    using ServerPacketFuncEx=bool(*)(CSocketServerEx*,const unsigned char*);
    CSocketServerEx*m_pSocket=nullptr;CIOBuffer*m_pBuf=nullptr;ServerPacketFuncEx m_pFunc=nullptr;
    DWORD offset=0;bool freed=false;static int g_nPendingPacket;static CPacketServerEx*Alloc();
    void PostObject(DWORD,int);void OnIOCallback(BOOL,DWORD,LPOVERLAPPED);void Free(){if(freed)std::abort();freed=true;}
};
int CPacketServerEx::g_nPendingPacket=0;
static CPacketServerEx packets[16];static unsigned packet_count;static std::vector<CPacketServerEx*> queued;static bool immediate;
CPacketServerEx*CPacketServerEx::Alloc(){if(packet_count>=16)std::abort();auto*p=&packets[packet_count++];*p=CPacketServerEx{};return p;}
void CPacketServerEx::PostObject(DWORD at,int){offset=at;if(immediate)OnIOCallback(1,at,nullptr);else queued.push_back(this);}
static CohBlowfish bf;
static void BlowfishEncrypt(unsigned char*p,int n){if(coh_bf_crypt(&bf,p,(size_t)n,0))std::abort();}
static void BlowfishDecrypt(unsigned char*p,int n){if(coh_bf_crypt(&bf,p,(size_t)n,1))std::abort();}
/* EXACT_PACKET_CRYPTO */
static bool aligned_decoder(unsigned char*p,int64_t&key,int n){
    ++decodes;if(n<=0||n>BUFFER_SIZE)std::abort();alignas(8) uint32_t scratch[BUFFER_SIZE/4]{};
    std::memcpy(scratch,p,(size_t)n);bool accepted=BlowFishDecryptPacket((unsigned char*)scratch,key,n);
    if(accepted)std::memcpy(p,scratch,(size_t)n);return accepted;
}
class CSocketServerEx:public CIOSocket {
public:
    enum {SM_CLOSE,SM_READ_LEN,SM_READ_BODY};int mode=SM_READ_LEN,packetLen=0;int64_t DecOneTimeKey=0x12345678;DWORD m_lastIO=0;
    bool(*DecPacket)(unsigned char*,int64_t&,int)=aligned_decoder;void OnRead()override;
};
struct Expected {unsigned opcode;std::vector<unsigned char> payload;};
static std::vector<Expected> expected;static bool payloads_match;
static bool capture(unsigned opcode,const unsigned char*p){
    if(dispatches>=expected.size()||expected[dispatches].opcode!=opcode||(!expected[dispatches].payload.empty()&&std::memcmp(p,expected[dispatches].payload.data(),expected[dispatches].payload.size())))payloads_match=false;
    ++dispatches;return false;
}
#define CAPTURE(n) static bool capture##n(CSocketServerEx*,const unsigned char*p){return capture(n,p);}
CAPTURE(0) CAPTURE(1) CAPTURE(2) CAPTURE(3) CAPTURE(4) CAPTURE(5)
static CPacketServerEx::ServerPacketFuncEx ServerPacketEx[6]={capture0,capture1,capture2,capture3,capture4,capture5};
/* EXACT_RECEIVER_FUNCTIONS */
static void reset(bool inline_dispatch){
    allocated=packet_count=0;pending_read=false;recv_failure=false;pending={};decodes=dispatches=0;payloads_match=true;queued.clear();immediate=inline_dispatch;expected.clear();
    if(CPacketServerEx::g_nPendingPacket)std::abort();
}
static std::vector<unsigned char> frame(unsigned payload_size,unsigned opcode,unsigned tag,bool bad_checksum=false){
    // payload_size includes opcode. Dirty source-defined alignment padding and
    // reserved trailer bytes are intentionally retained by original encryptor.
    alignas(8) uint32_t scratch[BUFFER_SIZE/4];std::memset(scratch,0xa6,sizeof(scratch));auto*p=(unsigned char*)scratch;
    p[0]=(unsigned char)opcode;Expected e{opcode,{}};
    for(unsigned i=1;i<payload_size;++i){p[i]=(unsigned char)(tag*29+i*17);e.payload.push_back(p[i]);}
    expected.push_back(e);int length=(int)payload_size;int64_t key=0x12345678;
    BlowFishEncryptPacket(p,key,length);
    if(bad_checksum){BlowfishDecrypt(p,length);p[length-8]^=1;BlowfishEncrypt(p,length);}
    std::vector<unsigned char> wire((size_t)length+2);wire[0]=(unsigned char)(length+2);wire[1]=(unsigned char)((length+2)>>8);
    std::memcpy(wire.data()+2,p,(size_t)length);return wire;
}
static bool complete(CSocketServerEx&s,const unsigned char*p,unsigned n,bool success=true){
    CHECK(pending_read&&n<=pending.len);WSABUF posted=pending;pending_read=false;
    if(n)std::memcpy(posted.buf,p,n);++completions;s.OnIOCallback(success,n,&s.m_overlappedRead);
    CHECK(s.refs>=0&&s.DecOneTimeKey==0x12345678);return true;
}
static void drain(){for(auto*p:queued)p->OnIOCallback(1,p->offset,nullptr);queued.clear();}
static bool cleanup(CSocketServerEx&s){
    if(!s.closed){CHECK(pending_read);CHECK(complete(s,nullptr,0));}
    drain();CHECK(s.closed&&s.refs==0&&CPacketServerEx::g_nPendingPacket==0&&!pending_read);
    s.m_pReadBuf->Release();for(unsigned i=0;i<allocated;++i)CHECK(buffers[i].m_ref==0);
    for(unsigned i=0;i<packet_count;++i)CHECK(packets[i].freed);return true;
}
static bool deliver(CSocketServerEx&s,const std::vector<unsigned char>&wire,unsigned first,unsigned cap){
    unsigned at=0;bool initial=true;
    while(at<wire.size()&&!s.closed){
        unsigned n=(unsigned)wire.size()-at;n=std::min(n,(unsigned)pending.len);n=std::min(n,initial&&first?first:cap);
        CHECK(n>0);CHECK(complete(s,wire.data()+at,n));at+=n;initial=false;
    }
    CHECK(at==wire.size()||s.closed);return true;
}
static bool success_case(unsigned first,unsigned cap,bool inline_dispatch,bool mixed,unsigned initial_payload=153){
    reset(inline_dispatch);auto wire=frame(initial_payload,0,1);
    if(mixed){auto small=frame(1,5,2),large=frame(8184,2,3);wire.insert(wire.end(),small.begin(),small.end());wire.insert(wire.end(),large.begin(),large.end());}
    CSocketServerEx s;s.OnRead();CHECK(deliver(s,wire,first,cap));CHECK(!s.closed);CHECK(inline_dispatch?allocated==1:allocated>1);
    CHECK(cleanup(s));CHECK(payloads_match&&dispatches==(mixed?3u:1u)&&decodes==dispatches);return true;
}
static bool run(){
    static const uint8_t key[]={0xa4,0xde,0x6b,0x64,0xff,0x24,0xad,0x74,0x52,0xa0,0x6a,0x35,0xaf,0xf5,0x37,0x11,0xd3,0x5a,0xc8,0x42};
    CHECK(coh_bf_init(&bf,key,sizeof(key))==0);unsigned schedules=0,malformed=0,incomplete=0;
    for(bool inline_dispatch:{false,true}){
        for(unsigned cap:{1u,2u,3u,7u,11u,16u,17u,169u,170u,4094u,4095u,4096u,8190u,8191u,8192u}){CHECK(success_case(0,cap,inline_dispatch,true));++schedules;}
        for(unsigned cut=1;cut<170;++cut){CHECK(success_case(cut,8192,inline_dispatch,false));++schedules;}
        for(unsigned cut:{171u,172u,173u,187u,188u,189u,4094u,4095u,4096u,8190u,8191u,8192u}){CHECK(success_case(cut,8192,inline_dispatch,true));++schedules;}
        // Every physically possible first completion of the source8192-byte
        // maximum ciphertext (the 2-byte header shares the receive buffer).
        for(unsigned cut=1;cut<=8192;++cut){CHECK(success_case(cut,8192,inline_dispatch,false,8184));++schedules;}
        // Every proper prefix including both header bytes must remain unpublished.
        for(unsigned prefix=0;prefix<170;++prefix){
            reset(inline_dispatch);auto wire=frame(153,0,1);wire.resize(prefix);CSocketServerEx s;s.OnRead();CHECK(deliver(s,wire,0,7));
            CHECK(!s.closed&&decodes==0&&dispatches==0);CHECK(cleanup(s));CHECK(dispatches==0);++incomplete;
        }
        // Independently closed sessions for every proper maximum-frame prefix.
        // Reuse immutable encrypted bytes; no re-encryption or accepted suffix.
        reset(inline_dispatch);auto maximum=frame(8184,0,1);auto maximum_expected=expected;
        CHECK(maximum.size()==BUFFER_SIZE+2);
        for(unsigned prefix=0;prefix<maximum.size();++prefix){
            reset(inline_dispatch);expected=maximum_expected;auto wire=maximum;wire.resize(prefix);
            CSocketServerEx s;s.OnRead();CHECK(deliver(s,wire,0,BUFFER_SIZE));
            CHECK(!s.closed&&decodes==0&&dispatches==0);CHECK(cleanup(s));CHECK(dispatches==0);++incomplete;
        }
        for(unsigned kind=0;kind<11;++kind){
            reset(inline_dispatch);std::vector<unsigned char> wire;
            if(kind<5){unsigned length[]={0,1,2,8195,65535};wire={(unsigned char)length[kind],(unsigned char)(length[kind]>>8),0};}
            else if(kind==5)wire={3,0,0};
            else if(kind==6)wire=frame(153,AQ_MAX,1);
            else if(kind==7)wire=frame(153,255,1);
            else if(kind==8)wire=frame(153,0,1,true);
            else if(kind==9)wire=frame(8184,0,1,true);
            else {wire.assign(8193,0);wire[0]=1;wire[1]=32;}
            CSocketServerEx s;s.OnRead();CHECK(deliver(s,wire,0,7));CHECK(s.closed&&dispatches==0);CHECK(cleanup(s));++malformed;
        }
        reset(inline_dispatch);CSocketServerEx s;s.OnRead();CHECK(complete(s,nullptr,0,false));CHECK(s.closed&&decodes==0&&dispatches==0);CHECK(cleanup(s));++malformed;
        reset(inline_dispatch);CSocketServerEx closing;closing.OnRead();closing.mode=CSocketServerEx::SM_CLOSE;unsigned char byte=0;
        CHECK(complete(closing,&byte,1));CHECK(closing.closed&&decodes==0&&dispatches==0);CHECK(cleanup(closing));++malformed;
        reset(inline_dispatch);recv_failure=true;CSocketServerEx failed;failed.OnRead();CHECK(failed.closed&&decodes==0&&dispatches==0);CHECK(cleanup(failed));++malformed;
    }
    std::printf("{\"passed\":true,\"checks\":%u,\"controlled_completion_schedules\":%u,\"incomplete_prefix_cases\":%u,\"malformed_cases\":%u,\"completion_callbacks\":%u,\"maximum_ciphertext_bytes\":8192,\"real_cipher_checksum\":true,\"aligned_crypto_adapter\":true,\"original_packet_callback\":true,\"live_receiver_controlled\":false,\"general_tcp_segmentation_accepted\":false}\n",checks,schedules,incomplete,malformed,completions);
    return true;
}
int main(){return run()?0:1;}
