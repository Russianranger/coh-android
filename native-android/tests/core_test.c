#include "coh_native_core.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static unsigned checks;
#define CHECK(c) do {checks++;if(!(c)){fprintf(stderr,"Failure at line %d\n",__LINE__);return 1;}}while(0)
static void le32(unsigned char *p,unsigned v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
int main(void){
    CohBlowfish ctx;unsigned char key[8]={0};const unsigned char expected[8]={0x45,0x97,0xf9,0x4e,0x78,0xdd,0x98,0x61};
    CHECK(sizeof(ctx)==4168);CHECK(coh_bf_init(&ctx,key,8)==0);
    for(unsigned offset=0;offset<8;offset++){
        unsigned char b[32];memset(b,0xa5,32);memset(b+offset+8,0,8);
        CHECK(coh_bf_crypt(&ctx,b+offset+8,8,0)==0);CHECK(!memcmp(b+offset+8,expected,8));
        for(unsigned i=0;i<32;i++)if(i<offset+8||i>=offset+16)CHECK(b[i]==0xa5);
        CHECK(coh_bf_crypt(&ctx,b+offset+8,8,1)==0);
    }
    unsigned char anim[644]={0};le32(anim,616);le32(anim+524,596);le32(anim+528,1);
    le32(anim+596,616);le32(anim+600,632);anim[604]=anim[606]=anim[608]=anim[610]=1;anim[612]=2;anim[613]=9;
    CohAnimHeader h;CohBoneView bone;CHECK(coh_anim_header(anim,644,&h)==0);CHECK(coh_anim_bone(anim,644,0,&bone)==0);
    CHECK(bone.rotation==anim+616 && bone.position==anim+632);
    for(size_t n=0;n<sizeof(anim);n++)CHECK(coh_anim_bone(anim,n,0,&bone)!=0);
    le32(anim+596,0xffffffffu);CHECK(coh_anim_bone(anim,sizeof(anim),0,&bone)!=0);
    unsigned char payload[16]={0},disk[12]={0};le32(disk+4,8);le32(disk+8,8);CohPackView p;
    CHECK(coh_pack_view(disk,12,payload,16,8,&p)==0 && p.bytes==payload+8);
    le32(disk+8,0xffffffffu);CHECK(coh_pack_view(disk,12,payload,16,8,&p)!=0);
    /* Decoder checks execute on Android as well as under host sanitizers. */
    unsigned char dds[152]={0},rgba[72];memcpy(dds,"DDS ",4);
    le32(dds+4,124);le32(dds+12,4);le32(dds+16,4);le32(dds+28,3);
    le32(dds+76,32);le32(dds+80,4);memcpy(dds+84,"DXT1",4);
    for(unsigned k=128;k<152;k+=8){dds[k]=0x00;dds[k+1]=0xf8;}
    CohDdsMip mip;CHECK(coh_dds_mip(dds,sizeof(dds),2,&mip)==0 && mip.width==1 && mip.rgba_bytes==4);
    for(unsigned level=0;level<3;level++){
        size_t bytes=(size_t)(4u>>level)*(4u>>level)*4;
        memset(rgba,0xa5,sizeof(rgba));CHECK(coh_dds_rgba(dds,sizeof(dds),level,rgba+4,bytes)==0);
        for(size_t k=0;k<bytes;k+=4)CHECK(rgba[4+k]==255&&rgba[5+k]==0&&rgba[6+k]==0&&rgba[7+k]==255);
        CHECK(rgba[3]==0xa5 && rgba[4+bytes]==0xa5);
        CHECK(coh_dds_rgba(dds,sizeof(dds),level,rgba+4,bytes-1)==1);
    }
    for(size_t n=0;n<sizeof(dds);n++){
        memset(rgba,0xa5,sizeof(rgba));CHECK(coh_dds_rgba(dds,n,0,rgba+4,64)==1);
        for(size_t k=0;k<sizeof(rgba);k++)CHECK(rgba[k]==0xa5);
    }
    CHECK(coh_dds_rgba(dds,sizeof(dds),0,dds,64)==1);
    le32(dds+28,1);memcpy(dds+84,"DXT3",4);memset(dds+128,0xff,8);dds[136]=0;dds[137]=0xf8;
    CHECK(coh_dds_rgba(dds,144,0,rgba+4,64)==0 && rgba[7]==255);
    memcpy(dds+84,"DXT5",4);dds[128]=20;dds[129]=200;memset(dds+130,0,6);
    CHECK(coh_dds_rgba(dds,144,0,rgba+4,64)==0 && rgba[7]==20);
    printf("{\"passed\":true,\"checks\":%u,\"pointer_bytes\":%zu,\"long_bytes\":%zu,\"platform\":\"%s\"}\n",checks,sizeof(void*),sizeof(long),
#ifdef __ANDROID__
        "Android Bionic"
#else
        "host"
#endif
    );return 0;
}
