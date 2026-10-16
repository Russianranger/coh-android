/* Platform and decoder-boundary fixtures around two exact original functions.
 * No ciphertext, account, key or real service is used by this offset oracle. */
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
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
static unsigned char expected_body[168];static unsigned decoded_calls;static bool decoder_matches;
static bool exact_body_decoder(unsigned char*data,int64_t&,int length){
    ++decoded_calls;decoder_matches=length==168&&!std::memcmp(data,expected_body,168);
    if(decoder_matches)data[0]=0;
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
static void reset(){allocated=0;dispatched=0;decoded_calls=0;decoder_matches=false;}
int main(){
    unsigned char frame[170]={170,0};
    for(unsigned i=0;i<168;++i)expected_body[i]=(unsigned char)(17+i*37);
    std::memcpy(frame+2,expected_body,168);
    reset();{CSocketServerEx s;feed(s,frame,170);CHECK(!s.closed);CHECK(decoded_calls==1&&decoder_matches&&dispatched==1);}
    unsigned wrong=0;
    for(unsigned split=1;split<170;++split){
        reset();CSocketServerEx s;feed(s,frame,split);feed(s,frame+split,170-split);
        if(split<=2){CHECK(!s.closed);CHECK(decoded_calls==1&&decoder_matches&&dispatched==1);}
        else{CHECK(s.closed);CHECK(decoded_calls==1&&!decoder_matches&&dispatched==0);++wrong;}
    }
    reset();{CSocketServerEx s;for(unsigned at=0;at<170;){unsigned count=170-at<7?170-at:7;feed(s,frame+at,count);at+=count;}
        CHECK(s.closed);CHECK(decoded_calls==1&&!decoder_matches&&dispatched==0);}
    CHECK(wrong==167);CHECK(checks==344);
    std::printf("{\"passed\":true,\"checks\":%u,\"complete_body_matches\":true,\"one_and_two_byte_header_splits_match\":true,\"body_split_offsets_wrong\":%u,\"seven_byte_schedule_rejected\":true,\"cryptography_executed\":false,\"live_service_executed\":false}\n",checks,wrong);
}
