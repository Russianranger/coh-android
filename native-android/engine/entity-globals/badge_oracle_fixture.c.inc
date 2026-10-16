static BadgeDef player_defs[COH_BADGE_PLAYER_MAX],sg_defs[COH_BADGE_SUPERGROUP_MAX];
static BadgeDef *player_ptrs[COH_BADGE_PLAYER_MAX],*sg_ptrs[COH_BADGE_SUPERGROUP_MAX];
static char long_name[COH_BADGE_FILENAME_MAX+1];
static void badge_setup(unsigned scenario,Entity *e,EntPlayer *pl,Supergroup *sg,U32 *sg_states) {
    memset(pl,0,sizeof(*pl));memset(sg_states,0,4*BADGE_SG_MAX_STATS);
    memset(server_sg,0,sizeof(server_sg));*sg=(Supergroup){{sg_states}};*e=(Entity){pl,sg,0,721};
    player_def_count=scenario==0?0:6;sg_def_count=0;server_state.clickToSource=0;
    pl->debugBadgeLevel=scenario==8?1:scenario==9?2:scenario==10?-1:0;
    if(scenario==5){player_def_count=0;sg_def_count=1050;e->supergroup_id=1;}
    if(scenario==6||scenario==7)player_def_count=4096;
    if(scenario==7){sg_def_count=1050;e->supergroup_id=1;}
    if(scenario==3||scenario==8||scenario==9||scenario>=11)server_state.clickToSource=1;
    if(scenario==11||scenario==12)player_def_count=1;
    if(scenario==13||scenario==14)player_def_count=scenario==13?64:65;
    if(scenario==15){player_def_count=0;e->supergroup_id=1;}
    if(scenario==16){player_def_count=0;sg_def_count=6;e->supergroup_id=1;}
    memset(long_name,'x',sizeof(long_name));long_name[scenario==12?1024:1023]=0;
    static const unsigned ids[]={1,63,64,4095,2,1};
    for(int i=0;i<player_def_count;i++) {
        unsigned id=player_def_count==6?ids[i]:(unsigned)i%(COH_BADGE_PLAYER_MAX-1)+1;
        player_defs[i]=(BadgeDef){(int)id,scenario>=11?long_name:i==1?"":"defs/fixtures/badge.def",NULL,{NULL,NULL},{NULL,NULL}};
        player_ptrs[i]=player_defs+i;
        U32 value=(i%5==0?BADGE_FULL_OWNERSHIP:i%5==1?0:i%5==2?BADGE_VISIBLE_MASK|1u:i%5==3?BADGE_KNOWN_MASK|0xfffffu:BADGE_VISIBLE_MASK|BADGE_KNOWN_MASK|19u);
        pl->aiBadges[id]=value|((scenario!=1||i%2)?BADGE_CHANGED_MASK:0);
    }
    for(int i=0;i<sg_def_count;i++) {
        unsigned id=(unsigned)i%(COH_BADGE_SUPERGROUP_MAX-1)+1;
        sg_defs[i]=(BadgeDef){(int)id,"defs/fixtures/sg-badge.def",NULL,{NULL,NULL},{NULL,NULL}};sg_ptrs[i]=sg_defs+i;
        server_sg[id]=(i%2?BADGE_VISIBLE_MASK|BADGE_KNOWN_MASK|77u:BADGE_FULL_OWNERSHIP)|BADGE_CHANGED_MASK;
    }
    g_BadgeDefs.ppBadges=player_ptrs;g_SgroupBadges.ppBadges=sg_ptrs;
    unsigned history=scenario==4||scenario==6||scenario==7?50:scenario==2?0:3;
    for(unsigned i=0;i<history;i++){pl->recentBadges[i].idx=i==2?65535:i+1;pl->recentBadges[i].timeAwarded=i==1?0xffffffffu:500+i;}
    static const U32 monitor[]={0,1,255,256,65790,65791,0x7fffffffu,0x80000000u,0xffffffffu,1};
    for(unsigned i=0;i<10;i++)memcpy(&pl->badgeMonitorInfo[i].iIdx,&monitor[(i+scenario)%10],4);
}
static void badge_cleanup(void) {
    for(unsigned i=0;i<BADGE_ENT_MAX_BADGES;i++){free(g_pchBadgeText[i]);g_pchBadgeText[i]=NULL;free(g_pchBadgeFilename[i]);g_pchBadgeFilename[i]=NULL;free(g_pchBadgeButton[i]);g_pchBadgeButton[i]=NULL;}
    for(unsigned i=0;i<BADGE_SG_MAX_BADGES;i++){free(g_pchSgBadgeText[i]);g_pchSgBadgeText[i]=NULL;free(g_pchSgBadgeFilename[i]);g_pchSgBadgeFilename[i]=NULL;free(g_pchSgBadgeButton[i]);g_pchSgBadgeButton[i]=NULL;}
}
unsigned badge_observation_size(void){return sizeof(BadgeObservation);}
void badge_original(unsigned scenario,unsigned aligned,unsigned prefix,U8 *out,U32 *bits,U32 *badge_bits,BadgeObservation *observed) {
    U32 storage[65536]={0},sg_states[BADGE_SG_MAX_STATS]={0};Packet p={0};Entity e;EntPlayer pl;Supergroup sg;
    badge_setup(scenario,&e,&pl,&sg,sg_states);
    initBitStream(&p.stream,(U8 *)storage,sizeof(storage),Write,aligned,0);
    if(prefix)bsWriteBits(&p.stream,prefix,0);
    entity_SendBadgeUpdate(&e,&p,scenario!=1);
    *badge_bits=p.stream.bitLength;
    badgeMonitor_SendInfo(&e,&p);*bits=p.stream.bitLength;memcpy(out,storage,(*bits+7)/8);
    badge_prior(observed);g_DebugBadgeDisplayMode=99;
    memcpy(pl.aiBadges,observed->player,sizeof(pl.aiBadges));memcpy(sg_states,observed->supergroup,sizeof(observed->supergroup));
    for(unsigned i=0;i<50;i++){pl.recentBadges[i].idx=observed->recent[i].index;pl.recentBadges[i].timeAwarded=observed->recent[i].time_awarded;}
    for(unsigned i=0;i<4096;i++)g_pchBadgeFilename[i]=strdup("prior-player");
    for(unsigned i=0;i<1050;i++)g_pchSgBadgeFilename[i]=strdup("prior-supergroup");
    p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;
    entity_ReceiveBadgeUpdate(&e,&p);assert(bsGetCursorBitPosition(&p.stream)==*badge_bits);
    monitor_sort_calls=0;badgeMonitor_ReceiveInfo(&e,&p);assert(monitor_sort_calls==1);
    assert(bsGetCursorBitPosition(&p.stream)==*bits);
    observed->debug_mode=(U32)g_DebugBadgeDisplayMode;
    memcpy(observed->player,pl.aiBadges,sizeof(pl.aiBadges));memcpy(observed->supergroup,sg_states,sizeof(observed->supergroup));
    for(unsigned i=0;i<50;i++)observed->recent[i]=(CohBadgeRecent){pl.recentBadges[i].idx,pl.recentBadges[i].timeAwarded};
    for(unsigned i=0;i<4096;i++)observed->player_filename[i]=badge_text_hash(g_pchBadgeFilename[i]);
    for(unsigned i=0;i<1050;i++)observed->supergroup_filename[i]=badge_text_hash(g_pchSgBadgeFilename[i]);
    for(unsigned i=0;i<10;i++)memcpy(&observed->monitor.indices[i],&pl.badgeMonitorInfo[i].iIdx,4);
    badge_cleanup();
}
