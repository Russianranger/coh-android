/* Fixture shell executes unchanged append/finish and receiver alignment helper.
 * Decoder below is an explicitly RESTRICTED projection of handleGameCmd;
 * whole client dispatcher, transport, ACK and unrelated handlers never run. */
void original_tail(unsigned profile,unsigned aligned,unsigned prefix,unsigned markers,U8*out,unsigned*bits,unsigned*begin,unsigned*end){
 assert(profile<3&&aligned<=1&&prefix<8&&(!aligned||!prefix)&&markers<=256);
 U32 mem[2048]={0},other[2048]={0};Packet p={0},inner={0};
 initBitStream(&p.stream,(U8*)mem,sizeof(mem),Write,0,0);
 initBitStream(&inner.stream,(U8*)other,sizeof(other),Write,0,0);
 for(unsigned i=0;i<prefix;i++)bsWriteBits(&p.stream,1,i&1);
 p.stream.byteAlignedMode=inner.stream.byteAlignedMode=aligned;
 *begin=bsGetCursorBitPosition(&p.stream);
 for(unsigned i=0;i<markers;i++)pktSendBitsPack(profile?&inner:&p,1,SERVER_GAME_CMDS);
 if(profile==2){pktSendBitsPack(&inner,1,SERVER_BEGIN_BYTE_ALIGNED_DATA);bsAlignByte(&inner.stream);}
 if(profile){TailEntity source={&inner};append_source(&p,&source);}
 TailEntity e={&p};finish_source(&e);*end=*bits=p.stream.bitLength;
 assert(!p.stream.errorFlags);memcpy(out,mem,(*bits+7)/8);
}
int restricted_tail_observe(const U8*data,unsigned bits,unsigned begin,unsigned aligned,unsigned*out_end,unsigned*out_markers,unsigned*out_meta){
 assert(bits<=65536&&begin<=bits&&aligned<=1);U32 mem[2048]={0};Packet p={0};
 initBitStream(&p.stream,(U8*)mem,sizeof(mem),Read,0,0);memcpy(mem,data,(bits+7)/8);
 p.stream.bitLength=bits;p.stream.size=(bits+7)/8;p.stream.byteAlignedMode=aligned;p.stream.cursor.byte=begin>>3;p.stream.cursor.bit=begin&7;
 unsigned markers=0,meta=0;
 for(unsigned k=0;k<258;k++){
  unsigned cmd=pktGetBitsPack(&p,1);if(p.stream.errorFlags)return 0;
  if(!cmd){if(bsGetCursorBitPosition(&p.stream)!=bits)return 0;*out_end=bits;*out_markers=markers;*out_meta=meta;return 1;}
  if(cmd==SERVER_GAME_CMDS)markers++;
  else if(cmd==SERVER_BEGIN_BYTE_ALIGNED_DATA){receiveByteAlignmentTag(&p);meta++;}
  else return 0;
 }
 return 0;
}
