void fixture(U32 scenario,U32 aligned,U32 prefix,U32 outer,U8*out,U32*bits,U32*end,U32*observed,U32*count) {
 U32 memory[65536]={0};Packet p={0};Character character={0};Entity entity={0};
 U32 crcs[]={0,1,3,4,1023,1024,0xffffff,0x1000000,0x80000000,0xffffffff};
 U32 floatwords[]={0,0x80000000,0x3f800000,0xc0200000,0x7f800000,0xff800000,0x7fc00000,0x7fa12345};
 memset(fixture_power_counts,0,sizeof(fixture_power_counts));
 fixture_set_count=scenario==0?0:scenario==9?4:1;
 for(int i=0;i<1026;i++)fixture_bases[i]=(BasePower){crcs[i%10],i%4,(i+1)%4};
 for(int i=0;i<4;i++) {
  fixture_sets[i].ppPowers=fixture_power_ptrs[i];fixture_set_ptrs[i]=&fixture_sets[i];
  fixture_power_counts[i]=scenario==10?1024:scenario==11?1025:scenario==1?1:6;
  for(int j=0;j<fixture_power_counts[i];j++) {
   Power*w=&fixture_powers[i][j];fixture_power_ptrs[i][j]=w;
   *w=(Power){&fixture_bases[j],&fixture_bases[j],-100.0f,(float)(i*10+j+1),(float)(i*10+j+101)};
   if(scenario==1){w->ppowBase=&fixture_bases[3];fixture_bases[3].eTargetType=fixture_bases[3].eTargetTypeSecondary=0;w->fRangeLast=0;}
   if(scenario==5&&j%2)fixture_power_ptrs[i][j]=NULL;
   if(scenario==7&&j%2)w->ppowOriginal=NULL;
   if(scenario==8){memcpy(&w->range1,&floatwords[j%8],4);memcpy(&w->range2,&floatwords[(j+2)%8],4);}
  }
 }
 character.ppPowerSets=fixture_set_ptrs;character.entParent=&entity;entity.pchar=&character;
 initBitStream(&p.stream,memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;
 if(prefix)bsWriteBits(&p.stream,prefix,0);
 if(outer)original_nochange_send(&entity,&p);else character_SendPowerRanges(&character,scenario==6,&p);
 *bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;
 fixture_observed=0;
 if(outer)original_nochange_receive(&entity,&p);else character_ReceivePowerRanges(&character,&p);
 *end=p.stream.cursor.byte*8+p.stream.cursor.bit;*count=fixture_observed/2;memcpy(observed,fixture_observation,fixture_observed*sizeof(U32));
}
