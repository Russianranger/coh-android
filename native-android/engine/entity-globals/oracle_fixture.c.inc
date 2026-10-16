static void prior_modes(OracleModes *m) {
    memset(m,0,sizeof(*m));m->size=3;
    m->values[0]=17;m->values[1]=17;m->values[2]=-1;
}
static void observe_modes(const OracleModes *from,CohPowerModes *out) {
    assert(from->size>=0 && from->size<=COH_GLOBAL_POWER_MODE_MAX);
    memset(out,0,sizeof(*out));out->count=(U32)from->size;
    for(int i=0;i<from->size;i++) memcpy(&out->modes[i],&from->values[i],4);
}
unsigned original_state_size(void) {
    U32 endian=1;assert(*(U8 *)&endian==1 && sizeof(int)==4);
    return sizeof(CohPowerModes);
}
void original_prior(CohPowerModes *out) {OracleModes modes;prior_modes(&modes);observe_modes(&modes,out);}
void original_send(int present,int count,int aligned,int prefix,U8 *out,U32 *bits,U32 *flag_after) {
    U32 storage[8192]={0};Packet p={0};OracleModes modes={0};Character character={modes.values};Entity entity={&character,present};
    static const U32 values[]={0,1,6,7,8,69,70,71,4164,4165,4166,16781379,16781380,16781381,0x7fffffffu,0x80000000u,0xffffffffu,17,17};
    assert(count>=0 && count<=COH_GLOBAL_POWER_MODE_MAX+1);modes.size=count;
    for(int i=0;i<count;i++) memcpy(&modes.values[i],&values[i%(sizeof(values)/sizeof(values[0]))],4);
    initBitStream(&p.stream,(U8 *)storage,sizeof(storage),Write,aligned,0);
    if(prefix)bsWriteBits(&p.stream,prefix,0);
    entity_SendPowerModeUpdate(&entity,&p);
    *bits=p.stream.bitLength;*flag_after=(U32)entity.power_modes_update;
    memcpy(out,storage,(*bits+7)/8);
}
void original_receive(const U8 *input,U32 bits,int aligned,int prefix,CohPowerModes *out,U32 *cursor) {
    U32 storage[8192]={0};Packet p={0};OracleModes modes;Character character={modes.values};Entity entity={&character,0};
    prior_modes(&modes);
    initBitStream(&p.stream,(U8 *)storage,sizeof(storage),Read,aligned,0);
    memcpy(storage,input,(bits+7)/8);p.stream.bitLength=bits;
    if(prefix)bsReadBits(&p.stream,prefix);
    entity_ReceivePowerModeUpdate(&entity,&p);
    observe_modes(&modes,out);*cursor=bsGetCursorBitPosition(&p.stream);
}
