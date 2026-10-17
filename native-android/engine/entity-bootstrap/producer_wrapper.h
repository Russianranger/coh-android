/* route0direct,1queue relay,2advertised IP,3queue+advertised; both alignments,
 * old/current command profiles. Export full command packet and original7words. */
int original_db_handoff(unsigned dbid,unsigned cookie,unsigned profile,unsigned route,unsigned char*out,unsigned*bits,unsigned*observed){
 assert(profile<4&&route<4);old_profile=profile;source_sends=0;NetLink link={0};link.addr.sin_addr.S_un.S_addr=0x0100007fu;EntCon ent={&link,1,1,1,(int)dbid,"fixture",0x0100007fu,1,0};map_fixture=(MapCon){1,{0x0100007fu,0},7002,7003};game_fixture.nonQueueIP=0x0100007fu;server_cfg.queue_server=route&1;server_cfg.advertisedIp=route&2?0x0100000au:0;
 sendLoginInfoToGameClient(&ent,(int)cookie);assert(source_sends==1&&ent.active&&!ent.is_gameclient&&!ent.callback_link&&!ent.logging_in&&!ent.handed_to_mapserver);
 unsigned length=packet.stream.bitLength;unsigned char saved[65536];memcpy(saved,storage,(length+7)/8);Packet input={0};static U32 read_storage[16384];initBitStream(&input.stream,(U8*)read_storage,sizeof(read_storage),Read,profile&1,0);memcpy(read_storage,saved,(length+7)/8);input.stream.bitLength=length;
 assert(pktGetBitsPack(&input,1)==4+((profile&2)?5:0));
 if(route&1){Packet*relay=pktCreateEx(&link,4);passdbOrMapConnect(&input,relay);assert(bsGetCursorBitPosition(&input.stream)==length);assert(packet.stream.bitLength==length&&!memcmp(storage,saved,(length+7)/8));}
 memcpy(out,saved,(length+7)/8);*bits=length;
 /* Independent source-reader projection, preserving first field despite the
  * original Game dbOrMapConnect consumer's misleading local link_id label. */
 initBitStream(&input.stream,(U8*)read_storage,sizeof(read_storage),Read,profile&1,0);memcpy(read_storage,saved,(length+7)/8);input.stream.bitLength=length;pktGetBitsPack(&input,1);for(unsigned i=0;i<7;i++)observed[i]=pktGetBitsPack(&input,1);assert(bsGetCursorBitPosition(&input.stream)==length);return 1;
}
