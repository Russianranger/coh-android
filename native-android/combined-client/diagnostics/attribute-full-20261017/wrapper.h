void attribute_full(unsigned sc,unsigned aligned,unsigned prefix,U8*out,unsigned*bits,unsigned*end,unsigned*observed,unsigned*modsout){
 assert(sc<16&&aligned<=1&&prefix<8&&(!aligned||!prefix));U32 memory[8192]={0};Packet p={0};scenario=sc;window_calls=0;allocation_count=0;interned_count=0;init_schema();
 WdwBase windows[MAX_WINDOW_COUNT]={0};windows[WDW_COMBATNUMBERS].mode=WINDOW_DISPLAYING;AttribPlayer pl={0};pl.winLocs=windows;
 AttribModTemplate templates[8]={0};AttribMod mods[8]={0};Character character={{mods,0}};
 Entity player={&pl,sc%2,sc%3?99:0,777,&character,ENTTYPE_PLAYER,22,0,"selected"};Entity target={&pl,0,0,888,&character,ENTTYPE_CRITTER,33,0,"target"};fixture_player=&player;fixture_target=&target;
 struct{const char*displayName;}npc={"source NPC display"};npcDefList.npcDefs[0]=(void*)&npc;
 sources[0]=player;sources[1]=(Entity){NULL,0,0,0,NULL,ENTTYPE_PLAYER,45,0,"source player"};sources[2]=(Entity){NULL,0,0,0,NULL,ENTTYPE_CRITTER,46,0,"source critter"};sources[3]=(Entity){NULL,0,0,0,NULL,ENTTYPE_CRITTER,47,0,""};
 for(unsigned i=0;i<4;i++)powers[i].crcFullName=(unsigned[]){0,3,1023,0xf1234567}[i];
 character.listMod.count=sc%9;
 for(unsigned i=0;i<character.listMod.count;i++){
  templates[i]=(AttribModTemplate){(sc%5==1&&i==1)?1.f:0.f,descriptions[i%69].key,powers+i%4};
  mods[i]=(AttribMod){templates+i,1.f,(sc%5==2&&i==2)?0.f:(float)(i+1)/8.f,-(float)(i+1)*2.5f,(sc%5==3&&i==3),i%5};
 }
 if(sc==15)character.listMod.count=0;
 server_state.enablePowerDiminishing=sc%2;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;for(unsigned i=0;i<prefix;i++)bsWriteBits(&p.stream,1,i&1);
 sendAttribDescription(&player,&p,1);*bits=p.stream.bitLength;assert(!p.stream.errorFlags);memcpy(out,memory,(*bits+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;receiveAttribDescription(&player,&p,1,0);assert(!p.stream.errorFlags);*end=bsGetCursorBitPosition(&p.stream);
 observed[0]=window_calls;observed[1]=player.newAttribTarget;observed[2]=g_pAttribTarget?g_pAttribTarget->owner:0;
 for(unsigned i=0;i<69;i++){observed[3+3*i]=descriptions[i].key;memcpy(observed+4+3*i,&descriptions[i].fVal,4);observed[5+3*i]=descriptions[i].buffOrDebuff;}
 modsout[0]=allocation_count;
 for(unsigned i=0;i<allocation_count;i++){
  AttribContributer*c=allocated[i];unsigned*j=modsout+1+i*8;j[0]=c->ppow->crcFullName;j[1]=c->eSrcType;j[2]=(c->eSrcType==kAttribSource_Critter||c->eSrcType==kAttribSource_Player)?c->svr_id:0;memcpy(j+3,&c->fChance,4);memcpy(j+4,&c->fMag,4);j[6]=0;for(unsigned d=0;d<69;d++)for(unsigned k=0;k<descriptions[d].contributors;k++)if(descriptions[d].ppContributers[k]==c)j[6]=descriptions[d].key;j[5]=0;if(c->eSrcType==kAttribSource_Critter||c->eSrcType==kAttribSource_Player)for(const unsigned char*s=(void*)c->pchSrcDisplayName;*s;s++)j[5]=j[5]*33+*s;free(c);
 }
}
