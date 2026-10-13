#include "coh_native_core.h"
#include "byte_reader.h"
/* Deliberately bounded legacy 2D DXT1/3/5 subset. No hidden allocations. */
int coh_dds_mip(const uint8_t *p,size_t n,uint32_t level,CohDdsMip *out){
    if(!p||!out||n<128||memcmp(p,"DDS ",4)||u32(p+4)!=124||u32(p+76)!=32)return 1;
    uint32_t w=u32(p+16),h=u32(p+12),m=u32(p+28),code=u32(p+84);
    if(!w||!h||w>16384||h>16384||u32(p+24)>1)return 1;
    if(u32(p+112)&0x20fe00u)return 2; /* cubemap/volume unsupported */
    if(!(u32(p+80)&4))return 2;
    uint32_t format=code==0x31545844u?1:code==0x33545844u?3:code==0x35545844u?5:0;
    if(!format)return 2;
    if(!m)m=1;
    uint32_t maxm=1,t=w>h?w:h;while(t>1){maxm++;t>>=1;}
    if(m>maxm||level>=m)return 1;
    size_t off=128;CohDdsMip result={0};
    for(uint32_t i=0;i<m;i++){
        size_t size=(size_t)((w+3)/4)*((h+3)/4)*(format==1?8:16);
        if(!span(n,off,size,1))return 1;
        if(i==level){result=(CohDdsMip){w,h,m,format,p+off,size,(size_t)w*h*4};}
        off+=size;w=w>1?w/2:1;h=h>1?h/2:1;
    }
    *out=result;return 0;
}
static void rgb565(uint16_t v,uint8_t *c){
    unsigned r=v>>11,g=(v>>5)&63,b=v&31;
    c[0]=(uint8_t)((r<<3)|(r>>2));c[1]=(uint8_t)((g<<2)|(g>>4));c[2]=(uint8_t)((b<<3)|(b>>2));c[3]=255;
}
static int decode_rgba(const uint8_t *p,size_t n,uint32_t level,uint8_t *out,size_t capacity,int legacy){
    CohDdsMip v;int status=coh_dds_mip(p,n,level,&v);if(status)return status;
    if(legacy && !(u32(p+8)&0x20000u))return 2; /* qualified producer mip-count contract */
    if(!out||capacity<v.rgba_bytes)return 1;
    /* Caller must supply a disjoint output buffer. No input/output overlap. */
    uintptr_t a=(uintptr_t)p,b=(uintptr_t)out;
    if(a<=b ? b-a<n : a-b<v.rgba_bytes)return 1;
    const uint8_t *block=v.blocks;
    for(uint32_t by=0;by<v.height;by+=4)for(uint32_t bx=0;bx<v.width;bx+=4){
        const uint8_t *color=block+(v.format==1?0:8);uint8_t c[4][4];
        uint16_t c0=u16(color),c1=u16(color+2);rgb565(c0,c[0]);rgb565(c1,c[1]);
        for(unsigned k=0;k<3;k++){
            if(c0>c1||(!legacy&&v.format!=1)){c[2][k]=(uint8_t)((2*c[0][k]+c[1][k]+(legacy?1:0))/3);c[3][k]=(uint8_t)((c[0][k]+2*c[1][k]+(legacy?1:0))/3);}
            else{c[2][k]=(uint8_t)((c[0][k]+c[1][k])/2);c[3][k]=0;}
        }
        c[2][3]=255;c[3][3]=(c0>c1||v.format!=1)?255:0;
        uint32_t selectors=u32(color+4);uint8_t alpha[8]={0};uint64_t abits=0;
        if(v.format==5){
            alpha[0]=block[0];alpha[1]=block[1];
            if(alpha[0]>alpha[1])for(unsigned k=2;k<8;k++)alpha[k]=(uint8_t)(((8-k)*alpha[0]+(k-1)*alpha[1]+(legacy?3:0))/7);
            else{for(unsigned k=2;k<6;k++)alpha[k]=(uint8_t)(((6-k)*alpha[0]+(k-1)*alpha[1]+(legacy?2:0))/5);alpha[6]=0;alpha[7]=255;}
            for(unsigned k=0;k<6;k++)abits|=(uint64_t)block[k+2]<<(k*8);
        }
        for(unsigned y=0;y<4;y++)for(unsigned x=0;x<4;x++){
            unsigned i=y*4+x,s=(selectors>>(i*2))&3;
            if(bx+x>=v.width||by+y>=v.height)continue;
            uint8_t *dst=out+((size_t)(by+y)*v.width+bx+x)*4;memcpy(dst,c[s],4);
            if(v.format==3)dst[3]=(uint8_t)(((block[i/2]>>((i%2)*4))&15)*17);
            if(v.format==5)dst[3]=alpha[(abits>>(i*3))&7];
        }
        block+=v.format==1?8:16;
    }
    if(legacy){
        /* The raw SDK consumer expands depth3 with opaque alpha. nvDXT always
         * strips DXT1 alpha, and strips DXT3/5 when visible alpha is all zero. */
        int has_alpha=0;
        if(v.format!=1)for(size_t i=3;i<v.rgba_bytes;i+=4)has_alpha|=out[i];
        if(!has_alpha)for(size_t i=3;i<v.rgba_bytes;i+=4)out[i]=255;
    }
    return 0;
}

/* Keep generic decode stable; use the qualified legacy path for CPU texWords
 * replacements. This intentionally preserves the vendor palette conventions. */
int coh_dds_rgba(const uint8_t *p,size_t n,uint32_t level,uint8_t *out,size_t cap){return decode_rgba(p,n,level,out,cap,0);}
int coh_dds_rgba_legacy(const uint8_t *p,size_t n,uint32_t level,uint8_t *out,size_t cap){return decode_rgba(p,n,level,out,cap,1);}
