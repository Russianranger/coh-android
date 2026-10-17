/* Exact original writers. Emitted bodies contain only public synthetic data. */
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cwchar>
#include <cstdarg>
using U8=unsigned char;using U32=uint32_t;using U16=uint16_t;
struct AuthPacket{U16 length=0;U8 data[1000]{};int bytesRead=0;};
/* EXACT_FUNCTIONS */
static int build(char*body,int size,const char*format,...){va_list args;va_start(args,format);int n=Assemble(body,size,format,args);va_end(args);return n;}
static void hex(const unsigned char*data,int n){for(int i=0;i<n;++i)std::printf("%02x",data[i]);}
int main(){char body[256];unsigned char data[128];for(int i=0;i<128;++i)data[i]=(unsigned char)i;
 const char*names[]={"x","sourcefixture","abcdefghijklmn"};
 std::printf("{\"about\":[");for(int i=0;i<3;++i){char name[15];std::strcpy(name,names[i]);int n=build(body,sizeof(body),"cdsdddbddd",0,900001,name,0,2,3,128,(char*)data,1,123,456);if(n!=158+(int)std::strlen(name))return 1;if(i)std::printf(",");std::printf("{\"name\":\"%s\",\"body\":\"",name);hex((unsigned char*)body,n);std::printf("\"}");}
 char name[]="sourcefixture";int n=build(body,sizeof(body),"cdsdddd",0,900001,name,0,2,3,1,0);
 std::printf("],\"short_userdata_disabled\":\"");hex((unsigned char*)body,n);
 AuthPacket packet;authPutU08(&packet,0);authPutU32(&packet,900001);authPutU32(&packet,0x76543210);
 std::printf("\",\"db_play_ok\":\"");hex(packet.data,packet.length);
 n=build(body,sizeof(body),"cddc",7,0x76543210,900001,3);
 std::printf("\",\"client_play_ok\":\"");hex((unsigned char*)body,n);std::printf("\"}\n");return 0;}
