/* Scenarios are explicit synthetic source entities, never live captures. */
void buffs_original(unsigned scenario,unsigned aligned,unsigned prefix,void *bytes,U32 *bits,U32 *begin,U32 *normal,U32 *normal_count,U32 *stale,U32 *stale_count) {
    U32 memory[262144]={0};Packet pak={0},read={0};
    static Entity source,receiver,outsider;static Character p,recvchar;static Player player;static int diffs[300];
    memset(&source,0,sizeof(source));memset(&receiver,0,sizeof(receiver));memset(&outsider,0,sizeof(outsider));
    memset(&p,0,sizeof(p));memset(&recvchar,0,sizeof(recvchar));memset(&player,0,sizeof(player));
    memset(&fixture_new_stash,0,sizeof(fixture_new_stash));memset(&fixture_sent_stash,0,sizeof(fixture_sent_stash));
    receiver.pl=&player;receiver.pchar=&recvchar;recvchar.entParent=&receiver;
    recvchar.stSentBuffs=&fixture_sent_stash;recvchar.stNewBuffs=&fixture_new_stash;
    source.pchar=&p;source.pl=&player;p.entParent=&source;p.stSentBuffs=&fixture_sent_stash;p.stNewBuffs=&fixture_new_stash;
    source.team_buff_full_update=1;source.iCntBuffs=3;source.teamup_id=receiver.teamup_id=7;
    fixture_diff_count=0;source.diffBuffs=diffs;
    for(int i=0;i<300;i++){UniqueBuff *b=&source.aBuffs[i];b->ppow=&fixture_powers[i%5];b->uiID=(U32)(i+1);b->time_remaining=(float)(i%3?9:11);b->mod_cnt=3;b->addedOrChangedThisTick=i%3?-1:1;diffs[i]=i;
        for(int j=0;j<65;j++){b->mod[j].fMag=(float)(i+j-2)/4.0f;b->mod[j].iHash=(j==1)?-1:(100+j);}}
    if(scenario==0)source.teamup_id=0;
    if(scenario==1)source.team_buff_full_update=0;
    if(scenario==2)source.pchar=NULL;
    if(scenario==3)player.buffSettings=1u<<(kBuff_NoSend+8);
    if(scenario==4)source.iCntBuffs=0;
    if(scenario==5)fixture_diff_count=3;
    if(scenario==6)player.buffSettings=1u<<(kBuff_NoNumbers+8);
    if(scenario==7)for(unsigned i=0;i<3;i++)stashIntAddInt(&fixture_sent_stash,i+1,i+1,1);
    if(scenario==8)for(unsigned i=0;i<3;i++)source.aBuffs[i].time_remaining=0;
    if(scenario==9)for(unsigned i=0;i<3;i++)source.aBuffs[i].mod_cnt=0;
    if(scenario==10)source.aBuffs[0].ppow=NULL;
    if(scenario==11){static BasePower unknown={0xdeadbeef};source.aBuffs[1].ppow=&unknown;}
    if(scenario==12){source.teamup_id=0;source.erOwner=&receiver;player.buffSettings=1u<<(kBuff_NoSend+16);}
    if(scenario==13){source.teamup_id=0;source.league_id=receiver.league_id=42;}
    if(scenario==14)source.iCntBuffs=256;
    if(scenario==15)source.iCntBuffs=257;
    if(scenario==16){source.iCntBuffs=1;source.aBuffs[0].mod_cnt=64;}
    if(scenario==17){source.iCntBuffs=1;source.aBuffs[0].mod_cnt=65;}
    if(scenario==18){source.iCntBuffs=33;for(unsigned i=0;i<33;i++)source.aBuffs[i].mod_cnt=64;}
    if(scenario==19){source.iCntBuffs=32;for(unsigned i=0;i<32;i++)source.aBuffs[i].mod_cnt=64;}
    if(scenario==20){source.iCntBuffs=1;source.aBuffs[0].uiID=0xffffffff;source.aBuffs[0].mod[0].fMag=-1.25f;}
    if(scenario==21){source.iCntBuffs=1;source.aBuffs[0].uiID=0;source.aBuffs[0].ppow=&fixture_powers[4];}
    if(scenario==22){fixture_diff_count=3;diffs[0]=2;diffs[1]=0;diffs[2]=1;}
    if(scenario==23){source.teamup_id=0;source.erOwner=&outsider;}
    if(scenario==24){source.teamup_id=0;source.erOwner=&receiver;player.buffSettings=1u<<(kBuff_NoNumbers+16);}
    if(scenario>=25){source.iCntBuffs=receiver.iCntBuffs=3;receiver.aBuffs[0]=source.aBuffs[0];receiver.aBuffs[1]=source.aBuffs[1];receiver.aBuffs[2]=source.aBuffs[2];receiver.team_buff_full_update=1;receiver.diffBuffs=diffs;recvchar.entParent=&receiver;if(scenario==26)player.buffSettings=1u<<kBuff_NoSend;if(scenario==27)player.buffSettings=1u<<kBuff_NoNumbers;}
    initBitStream(&pak.stream,(U8*)memory,sizeof(memory),Write,0,0);pak.stream.byteAlignedMode=aligned;
    if(prefix)bsWriteBits(&pak.stream,(int)prefix,0xa5);
    *begin=bsGetCursorBitPosition(&pak.stream);
    appendTeammatePacket(&pak,&receiver,scenario>=25?&receiver:&source);
    *bits=pak.stream.bitLength;memcpy(bytes,memory,(*bits+7)/8);
    for(unsigned is_stale=0;is_stale<2;is_stale++) {
        initBitStream(&read.stream,(U8*)memory,sizeof(memory),Read,0,0);read.stream.byteAlignedMode=aligned;read.stream.bitLength=*bits;memcpy(memory,bytes,(*bits+7)/8);
        if(prefix)bsReadBits(&read.stream,(int)prefix);
        observation_used=fixture_desc_count=fixture_mag_count=0;
        if(pktGetBits(&read,1))entReceiveBuffs(&read,&receiver,(bool)is_stale);
        assert(bsGetCursorBitPosition(&read.stream)==*bits);
        if(is_stale){*stale_count=observation_used;memcpy(stale,observation,4*observation_used);}else{*normal_count=observation_used;memcpy(normal,observation,4*observation_used);}
    }
}
