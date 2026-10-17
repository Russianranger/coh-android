/* Platform and decoder-boundary fixtures around two exact original functions.
 * No ciphertext, account, key or real service is used by this offset oracle. */
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
using DWORD=uint32_t;using SOCKET=int;
#define BUFFER_SIZE 4096
#define LOG_ERROR 1
#define LOG_DEBUG 2
#define WSAENOTSOCK 10038
#define WSAECONNRESET 10054
#define WSAECONNABORTED 10053
#define ERROR_IO_PENDING 997
#define AQ_MAX 6
struct {int PacketSizeType=3;} config;
struct {template<class...A>void AddLog(int,const char*,A...){}} logger;
struct WSABUF {unsigned long len;char*buf;};
static int WSARecv(SOCKET,WSABUF*,int,DWORD*,DWORD*,void*,void*){return 1;}
static int GetLastError(){return ERROR_IO_PENDING;}
static DWORD GetTickCount(){return 1000;}
static int InterlockedIncrement(int*p){return ++*p;}
static int g_hIOCompletionPort;
struct CIOBuffer {
    char m_buffer[BUFFER_SIZE]{};int m_size=0,m_ref=1;
    void AddRef(){++m_ref;}void Release(){--m_ref;}
    static CIOBuffer*Alloc();
};
static CIOBuffer buffers[8];static unsigned allocated;
CIOBuffer*CIOBuffer::Alloc(){if(allocated>=8)std::abort();auto*p=&buffers[allocated++];*p=CIOBuffer{};return p;}
class CIOSocket {
public:
    CIOBuffer*m_pReadBuf=CIOBuffer::Alloc();SOCKET m_hSocket=1;int m_overlappedRead=0;bool closed=false;
    void Read(DWORD);void AddRef(){}void ReleaseRef(){}void CloseSocket(){closed=true;}
};
class CSocketServerEx;
static unsigned dispatched;
struct CPacketServerEx {
    using ServerPacketFuncEx=bool(*)(CSocketServerEx*,const unsigned char*);
    CSocketServerEx*m_pSocket=nullptr;CIOBuffer*m_pBuf=nullptr;ServerPacketFuncEx m_pFunc=nullptr;
    static int g_nPendingPacket;static CPacketServerEx*Alloc(){static CPacketServerEx p;return &p;}
    void PostObject(int,int){++dispatched;}
};
int CPacketServerEx::g_nPendingPacket=0;
static CPacketServerEx::ServerPacketFuncEx ServerPacketEx[6]{};
static bool invalid_opcode=false;
static unsigned char expected_body[168];static unsigned decoded_calls;static bool decoder_matches;
static bool exact_body_decoder(unsigned char*data,int64_t&,int length){
    ++decoded_calls;decoder_matches=length==168&&!std::memcmp(data,expected_body,168);
    if(decoder_matches)data[0]=invalid_opcode?AQ_MAX:0;
    return decoder_matches;
}
class CSocketServerEx:public CIOSocket {
public:
    enum {SM_CLOSE,SM_READ_LEN,SM_READ_BODY};int mode=SM_READ_LEN,packetLen=0;int64_t DecOneTimeKey=0;DWORD m_lastIO=0;
    bool(*DecPacket)(unsigned char*,int64_t&,int)=exact_body_decoder;
    void OnRead();
};
/* EXACT_ORIGINAL_FUNCTIONS */
static unsigned checks;
#define CHECK(x) do{++checks;if(!(x)){std::fprintf(stderr,"check failed at %d\n",__LINE__);return 1;}}while(0)
static void feed(CSocketServerEx&s,const unsigned char*bytes,unsigned count){
    if(s.m_pReadBuf->m_size<0||count>BUFFER_SIZE-(unsigned)s.m_pReadBuf->m_size)std::abort();
    std::memcpy(s.m_pReadBuf->m_buffer+s.m_pReadBuf->m_size,bytes,count);
    s.m_pReadBuf->m_size+=(int)count;s.OnRead();
}
static void reset(){allocated=0;dispatched=0;decoded_calls=0;decoder_matches=false;invalid_opcode=false;}
int main(){
    unsigned char frame[170]={170,0}, stream[510];
    for(unsigned i=0;i<168;++i)expected_body[i]=(unsigned char)(17+i*37);
    std::memcpy(frame+2,expected_body,168);
    for(unsigned i=0;i<3;++i)std::memcpy(stream+i*170,frame,170);
    for(unsigned split=1;split<170;++split){
        reset();CSocketServerEx s;feed(s,frame,split);
        CHECK(!s.closed&&dispatched==0&&decoded_calls==0);
        feed(s,frame+split,170-split);
        CHECK(!s.closed&&decoder_matches&&decoded_calls==1&&dispatched==1);
    }
    for(unsigned cap=1;cap<=170;++cap){
        reset();CSocketServerEx s;
        for(unsigned at=0;at<510;){unsigned n=510-at<cap?510-at:cap;feed(s,stream+at,n);at+=n;CHECK(!s.closed);}
        CHECK(decoded_calls==3&&dispatched==3&&decoder_matches);
    }
    reset();{CSocketServerEx s;feed(s,stream,510);CHECK(!s.closed&&dispatched==3&&decoded_calls==3);}
    for(unsigned seed=1;seed<=100;++seed){
        reset();CSocketServerEx s;unsigned value=seed;
        for(unsigned at=0;at<510;){value=value*1664525u+1013904223u;unsigned n=1+(value%79);if(n>510-at)n=510-at;feed(s,stream+at,n);at+=n;CHECK(!s.closed);}
        CHECK(decoded_calls==3&&dispatched==3&&decoder_matches);
    }
    // Incomplete body never reaches decoder/dispatch, including zero payload.
    for(unsigned n=0;n<170;++n){reset();CSocketServerEx s;feed(s,frame,n);CHECK(!s.closed&&dispatched==0&&decoded_calls==0);}
    for(unsigned cap: {1u,7u,170u}){
        unsigned char bad[170];std::memcpy(bad,frame,170);bad[71]^=1;
        reset();CSocketServerEx s;for(unsigned at=0;at<170&&!s.closed;){unsigned n=170-at<cap?170-at:cap;feed(s,bad+at,n);at+=n;}
        CHECK(s.closed&&decoded_calls==1&&!decoder_matches&&dispatched==0);
    }
    reset();{CSocketServerEx s;invalid_opcode=true;feed(s,frame,170);CHECK(s.closed&&dispatched==0&&decoded_calls==1);}
    for(unsigned len: {0u,1u,2u,4099u,65535u}){reset();CSocketServerEx s;unsigned char bad[3]={(unsigned char)len,(unsigned char)(len>>8),0};feed(s,bad,3);CHECK(s.closed&&decoded_calls==0&&dispatched==0);}
    std::printf("{\"passed\":true,\"checks\":%u,\"all_body_splits\":169,\"send_caps\":170,\"random_schedules\":100,\"coalesced_frames\":3,\"cryptography_executed\":false,\"live_service_executed\":false}\n",checks);
}
