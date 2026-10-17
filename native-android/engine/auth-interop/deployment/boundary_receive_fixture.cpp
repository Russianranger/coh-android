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
static unsigned expected_length=168,key_calls=0;
static unsigned char expected_body[BUFFER_SIZE];static unsigned decoded_calls;static bool decoder_matches;
static bool exact_body_decoder(unsigned char*data,int64_t&key,int length){
    ++decoded_calls;decoder_matches=length==(int)expected_length&&!std::memcmp(data,expected_body,expected_length)&&key==(int64_t)key_calls;
    if(decoder_matches){++key;++key_calls;}
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
static void reset(){allocated=0;dispatched=0;decoded_calls=0;decoder_matches=false;invalid_opcode=false;key_calls=0;}
static unsigned variable_checks;
static void make_frame(unsigned char*frame,unsigned length){
    expected_length=length;frame[0]=(unsigned char)(length+2);frame[1]=(unsigned char)((length+2)>>8);
    for(unsigned i=0;i<length;++i)expected_body[i]=(unsigned char)(17+i*37);
    std::memcpy(frame+2,expected_body,length);
}
static void deliver(CSocketServerEx&s,const unsigned char*data,unsigned length,unsigned cap){
    for(unsigned at=0;at<length&&!s.closed;){
        unsigned available=BUFFER_SIZE-(unsigned)s.m_pReadBuf->m_size;
        unsigned count=length-at;if(count>cap)count=cap;if(count>available)count=available;
        if(!count)std::abort();feed(s,data+at,count);at+=count;
    }
}
int main(){
    unsigned char frame[BUFFER_SIZE+2],stream[(BUFFER_SIZE+2)*3];
    for(unsigned length: {1u,2u,167u,168u,169u,4094u,4095u,4096u}){
        make_frame(frame,length);unsigned total=length+2;
        for(unsigned i=0;i<3;++i)std::memcpy(stream+i*total,frame,total);
        for(unsigned cap: {1u,2u,3u,7u,11u,169u,4094u,4095u,4096u}){
            reset();CSocketServerEx s;deliver(s,stream,total*3,cap);
            CHECK(!s.closed&&decoder_matches&&dispatched==3&&decoded_calls==3&&key_calls==3&&s.DecOneTimeKey==3);++variable_checks;
        }
        for(unsigned split: {1u,2u,3u,4u,167u,168u,169u,2048u,4094u,4095u,4096u}){
            if(split>=total||split>BUFFER_SIZE)continue;
            reset();CSocketServerEx s;feed(s,frame,split);
            CHECK(!s.closed&&dispatched==0&&decoded_calls==0&&key_calls==0);
            deliver(s,frame+split,total-split,BUFFER_SIZE);
            CHECK(!s.closed&&decoder_matches&&dispatched==1&&decoded_calls==1&&key_calls==1&&s.DecOneTimeKey==1);++variable_checks;
        }
    }
    // Distinct lengths in the same socket exercise state and retained buffers.
    for(unsigned cap: {1u,2u,3u,7u,4096u}){
        reset();CSocketServerEx s;
        for(unsigned length: {1u,4096u,1u}){make_frame(frame,length);deliver(s,frame,length+2,cap);CHECK(!s.closed&&decoder_matches);}
        CHECK(dispatched==3&&decoded_calls==3&&key_calls==3&&s.DecOneTimeKey==3);++variable_checks;
    }
    std::printf("{\"passed\":true,\"checks\":%u,\"boundary_schedules\":%u,\"minimum_body\":1,\"maximum_body\":4096,\"stateful_decoder_observer\":true,\"cryptography_executed\":false,\"live_service_executed\":false}\n",checks,variable_checks);
}
