/* Native malformed-input reference writer, not an original-source oracle. */
typedef struct{uint8_t bytes[1048576];size_t bits;unsigned mode;}TailWriter;
static void put(TailWriter*w,unsigned n,uint32_t v){if(w->mode)n=(n+7u)&~7u;for(unsigned i=0;i<n;i++){CHECK(w->bits/8<sizeof(w->bytes));uint8_t mask=(uint8_t)(1u<<(w->bits%8));if((v>>i)&1u)w->bytes[w->bits/8]|=mask;else w->bytes[w->bits/8]&=(uint8_t)~mask;w->bits++;}}
static void packed(TailWriter*w,unsigned n,uint32_t value){if(w->mode){put(w,32,value);return;}for(;;){uint32_t mask=n==32?UINT32_MAX:((UINT32_C(1)<<n)-1u);if(value<mask||n==32){put(w,n,value);return;}put(w,n,mask);value-=mask;n=n>16?32:n*2;}}
static void automatic(TailWriter*w,uint32_t value){unsigned bin=value<4?0:value<1024?1:value<16777216?2:3;static const unsigned widths[]={2,10,24,32};put(w,2,bin);put(w,widths[bin],value);}
static void string(TailWriter*w,const char*s){while(*s)put(w,8,(uint8_t)*s++);put(w,8,0);}
static void zero_tail(TailWriter*w){
 automatic(w,0);automatic(w,0);put(w,10,0);put(w,10,0);for(unsigned i=0;i<4;i++)put(w,1,0);for(unsigned i=0;i<3;i++)put(w,32,0);
 put(w,1,0);for(unsigned i=0;i<4;i++)packed(w,1,0);for(unsigned i=0;i<5;i++){for(unsigned j=0;j<3;j++)packed(w,1,0);put(w,32,0);}
 for(unsigned i=0;i<20;i++){string(w,"");while(w->bits%8)put(w,1,0);put(w,32,0);put(w,32,0);for(unsigned j=0;j<4;j++)packed(w,1,0);}
 for(unsigned i=0;i<15;i++){string(w,"");packed(w,1,0);put(w,32,0);put(w,32,0);}
 packed(w,5,0);for(unsigned i=0;i<3;i++)string(w,"");automatic(w,0);automatic(w,0);put(w,32,0);for(unsigned i=0;i<5;i++)string(w,"");
 for(unsigned i=0;i<256;i++){string(w,"");put(w,32,0);put(w,32,0);}put(w,1,0);put(w,1,1);put(w,32,0x3f800000);put(w,32,0x40000000);
 for(unsigned i=0;i<8;i++){packed(w,9,0);}
 put(w,1,0);put(w,2,0);packed(w,1,1);packed(w,1,0);for(unsigned i=0;i<20;i++)put(w,1,0);put(w,1,0);
}
