/* Synthetic outer flags; unchanged original component producers execute. This
 * is NOT full sendEntity, live capture, dictionary or identity authority. */
void selected_record_front(unsigned rare,unsigned medium,unsigned very,unsigned pchar,unsigned aligned,unsigned prefix,U8*out,U32*bits,U32*begin){
 U32 storage[65536]={0};Packet p={0};Entity e={0};Character ch={3,1,1,NULL};Player pl={0};initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);if(prefix)pktSendBits(&p,prefix,0);*begin=bsGetCursorBitPosition(&p.stream);
 original_record_entity(&e,91);e.type=2;e.db_id=4242;e.pchar=&ch;e.pl=&pl;e.name="FixturePlayer";
 pktSendBits(&p,1,1);entSendCreate(&p,&e,&e,1);pktSendBits(&p,1,rare);if(rare){pktSendBits(&p,1,medium);pktSendBits(&p,1,very);}
 if(medium)entSendModes(&p,&e,1);entSendPosUpdate(&p,&e,7,1,0);entSendQrotUpdate(&p,&e,7);
 if(rare){pktSendBits(&p,1,1);pktSendIfSetBitsPack(&p,8,33);pktSendIfSetBitsPack(&p,4,4);pktSendIfSetBits(&p,11,3);}
 if(medium){entSendSeqTriggeredMoves(&p,&e);entSendAiAnimList(&p,&e,1);}
 pktSendBits(&p,1,pchar);pktSendBits(&p,1,pchar);if(pchar)original_netfx_fields(&p,0);
 *bits=p.stream.bitLength;memcpy(out,storage,(*bits+7)/8);
}
/* Individual whole component calls; the wrapper supplies explicit fixture
 * objects. Prefix is emitted by the original writer before each body. */
void selected_record_leaf(unsigned id,unsigned aligned,unsigned prefix,U8*out,U32*bits,U32*begin){
 U32 storage[65536]={0};Packet p={0};Entity e={0};Character ch={3,1,1,NULL};Player pl={0};initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);if(prefix)pktSendBits(&p,prefix,0);*begin=bsGetCursorBitPosition(&p.stream);
 original_record_entity(&e,91);e.type=2;e.db_id=4242;e.pchar=&ch;e.pl=&pl;e.name="FixturePlayer";
 switch(id){case 1:entSendCreate(&p,&e,&e,1);break;case 2:entSendModes(&p,&e,1);break;case 3:entSendPosUpdate(&p,&e,7,1,0);break;case 4:entSendQrotUpdate(&p,&e,7);break;case 6:entSendSeqTriggeredMoves(&p,&e);break;case 7:entSendAiAnimList(&p,&e,1);break;case 8:original_netfx_fields(&p,0);break;default:assert(0);}
 *bits=p.stream.bitLength;memcpy(out,storage,(*bits+7)/8);
}
