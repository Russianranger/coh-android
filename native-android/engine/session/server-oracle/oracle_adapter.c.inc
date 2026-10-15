/* Narrow host wrapper: bounded allocation/queue/checksum around unchanged
 * functions. No authentication, account, DB or world simulation. */
static NetLink link_state;
static SimpleSetElement received_set[16384];
static unsigned next_id,controls[8],game_received,output_count;
static U32 output_words[8][4096];
static unsigned output_sizes[8];
static Packet *pktCreateImp(const char *file,int line){
 (void)file;(void)line;Packet *p=calloc(1,sizeof(*p));assert(p);
 initBitStream(&p->stream,(U8*)p->storage,sizeof(p->storage),Write,0,NULL);return p;
}
static int pktSend(Packet **pp,NetLink *l){
 Packet *p=*pp;assert(output_count<8);assert(!p->compress);p->truncatedID=++next_id;
 BitStream output;initBitStream(&output,(U8*)output_words[output_count],sizeof(output_words[0]),Write,0,NULL);
 assert(pktWrap(p,l,&output));unsigned length=blowfishPad((output.bitLength+7)/8);
 assert(length<=sizeof(output_words[0]));U32 sum=(U32)adler32(1,(U8*)output_words[output_count]+8,length-8);
 U8 *wire=(U8*)output_words[output_count];wire[4]=sum>>24;wire[5]=sum>>16;wire[6]=sum>>8;wire[7]=sum;
 output_sizes[output_count++]=length;coh_auth_wipe(p,sizeof(*p));free(p);*pp=NULL;return 1;
}
void oracle_reset(int encrypted){
 coh_auth_wipe(&link_state,sizeof(link_state));memset(received_set,0,sizeof(received_set));memset(output_words,0,sizeof(output_words));memset(controls,0,sizeof(controls));
 next_id=game_received=output_count=ack_observed=discarded=0;link_state.receivedPacketID=received_set;link_state.encrypted=!!encrypted;link_state.parentNetLinkList=&link_state;link_state.recvBufferMaxSize=65536;
}
/* This test boundary deliberately permits only bounded trusted packets from the
 * separately sanitizer-qualified native writer. Never exposed as a service. */
int oracle_receive(const U8 *wire,unsigned bytes){
 if(!wire||bytes<12||bytes>1472||(bytes-4)%8)return -1;
 Packet packet={0};U32 plain[4096]={0};memcpy(plain,wire,bytes);
 if(link_state.decrypt_on&&coh_bf_crypt(&link_state.blowfish_ctx,(U8*)plain+4,bytes-4,1))return -2;
 U8 *b=(U8*)plain;U32 sum=(U32)adler32(1,b+8,bytes-8),given=((U32)b[4]<<24)|((U32)b[5]<<16)|((U32)b[6]<<8)|b[7];
 U32 bits=plain[0];if(sum!=given||bits<64||bits>bytes*8)return -3;
 initBitStream(&packet.stream,b,sizeof(plain),Read,0,NULL);packet.stream.size=bytes;packet.stream.bitLength=bits;bsSetCursorBitPosition(&packet.stream,64);
 int result=pktUnwrap(&packet,&link_state);if(result<0)return -4;
 assert(!packet.sib_count&&!packet.compress&&!packet.hasDebugInfo&&!packet.ordered);
 U32 cmd=pktGetBitsPack(&packet,1);
 if(link_state.controlCommandsSeparate&&cmd==0){cmd=pktEnd(&packet)?0:pktGetBitsPack(&packet,1);}
 else if(link_state.controlCommandsSeparate&&cmd!=1){
  assert(link_state.connected&&cmd==10);U32 token=pktGetBits(&packet,32);assert(token==0x12345678);game_received++;
  Packet *response=pktCreateImp("oracle",0);applyNetworkVersionToPacket(&link_state,response);pktSendBitsPack(response,1,11);pktSendBits(response,32,token);pktSend(&response,&link_state);return 1;
 }
 else if(!link_state.controlCommandsSeparate&&cmd>=8){
  assert(link_state.connected&&cmd==10);U32 token=pktGetBits(&packet,32);assert(token==0x12345678);game_received++;
  Packet *response=pktCreateImp("oracle",0);applyNetworkVersionToPacket(&link_state,response);pktSendBitsPack(response,1,11);pktSendBits(response,32,token);pktSend(&response,&link_state);return 1;
 }
 assert(cmd<8);controls[cmd]++;return handleControlCommand(&packet,(CommControlCommand)cmd,&link_state)+1;
}
unsigned oracle_output(U8 *wire,unsigned cap){
 if(!output_count)return 0;unsigned n=output_sizes[0];assert(cap>=n);memcpy(wire,output_words[0],n);if(link_state.encrypt_on)assert(!coh_bf_crypt(&link_state.blowfish_ctx,wire+4,n-4,0));
 for(unsigned i=1;i<output_count;i++){memcpy(output_words[i-1],output_words[i],sizeof(output_words[0]));output_sizes[i-1]=output_sizes[i];}output_count--;memset(output_words[output_count],0,sizeof(output_words[0]));return n;
}
unsigned oracle_stat(unsigned i){switch(i){case 0:return link_state.connected;case 1:return link_state.encrypt_on;case 2:return link_state.decrypt_on;case 3:return game_received;case 4:return ack_observed;case 5:return discarded;case 6:return controls[1];case 7:return controls[3];case 8:return controls[5];case 9:return link_state.duplicate_packet_recv_count;default:abort();}}
