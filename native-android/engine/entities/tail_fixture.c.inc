static void source_observe_mission(TailObservation *o,const TaskStatus *t) {
    const U32 words[]={t->ownerDbid,t->context,t->subhandle,t->level,t->alliance,
        t->difficulty.levelAdjust,t->difficulty.teamSize,t->difficulty.dontReduceBoss,t->difficulty.alwaysAV,
        t->timeout,t->timezero,t->timerType,t->failOnTimeout,t->isComplete,t->isMission,t->hasRunningMission,
        t->isSGMission,t->zoneTransfer,t->teleportOnComplete,t->enforceTimeLimit,t->isAbandonable,t->isZowie,t->hasLocation,t->detailInvalid};
    for(unsigned i=0;i<ARRAY_SIZE(words);i++)observe_word(o,words[i]);
    observe_text(o,t->filename,sizeof(t->filename));observe_text(o,t->description,sizeof(t->description));
    observe_text(o,t->owner,sizeof(t->owner));observe_text(o,t->state,sizeof(t->state));
    for(unsigned i=0;i<3;i++)observe_float(o,t->location.world_location[3][i]);
    observe_word(o,t->location.contactType);observe_text(o,t->location.mapName,sizeof(t->location.mapName));observe_text(o,t->location.name,sizeof(t->location.name));
    observe_word(o,t->zinfo);observe_word(o,t->zseed);observe_word(o,t->zmap_id);
    observe_text(o,t->ztype,sizeof(t->ztype));observe_text(o,t->zname,sizeof(t->zname));
    for(unsigned i=0;i<MAX_ZOWIE_TYPE;i++)observe_word(o,t->zpoolSize[i]);
}
static void source_observe(TailObservation *o,const Entity *e) {
    memset(o,0,sizeof(*o));observe_word(o,e->supergroup_id);observe_text(o,e->supergroup_name,sizeof(e->supergroup_name));
    observe_text(o,e->supergroup_emblem,sizeof(e->supergroup_emblem));observe_word(o,e->supergroup_color[0]);observe_word(o,e->supergroup_color[1]);
    observe_word(o,e->supergroup!=NULL);
    if(e->supergroup) {
        const Supergroup *s=e->supergroup;observe_word(o,s->spacesForItemsOfPower);observe_word(o,s->sgMission!=NULL);
        if(s->sgMission)source_observe_mission(o,s->sgMission);
        observe_word(o,eaSize(&s->rewardTokens));for(int i=0;i<eaSize(&s->rewardTokens);i++){observe_text(o,s->rewardTokens[i]->reward,2048);observe_word(o,s->rewardTokens[i]->val);observe_word(o,s->rewardTokens[i]->timer);}
        observe_word(o,eaSize(&s->invRecipes));for(int i=0;i<eaSize(&s->invRecipes);i++){observe_text(o,s->invRecipes[i]->recipe->pchName,2048);observe_word(o,s->invRecipes[i]->count);}
        observe_word(o,eaSize(&s->specialDetails));for(int i=0;i<eaSize(&s->specialDetails);i++){const SpecialDetail *d=s->specialDetails[i];observe_text(o,d->pDetail->pchName,2048);observe_word(o,d->creation_time);observe_word(o,d->expiration_time);observe_word(o,d->iFlags);observe_word(o,d->bValid);}
    }
    observe_word(o,e->levelingpact_id);observe_word(o,e->levelingpact!=NULL);
    if(e->levelingpact){const TeamMembers *m=&e->levelingpact->members;observe_word(o,m->count);for(int i=0;i<m->count;i++){observe_word(o,m->ids[i]);observe_text(o,m->names[i],64);observe_word(o,m->onMapserver[i]);}}
    observe_word(o,e->logout_bad_connection);observe_float(o,e->logout_timer);
}
static void receiver_free(Entity *e) {
    if(e->supergroup){Supergroup *s=e->supergroup;TaskStatusDestroy(s->sgMission);
        for(int i=0;i<eaSize(&s->rewardTokens);i++){free((void*)s->rewardTokens[i]->reward);free(s->rewardTokens[i]);}eaDestroy(&s->rewardTokens);
        eaClearEx(&s->invRecipes,DestroyRecipeInvItemAdapter);eaDestroy(&s->invRecipes);
        eaClearEx(&s->specialDetails,free);eaDestroy(&s->specialDetails);free(s);
    }
    if(e->levelingpact)destroyLevelingpact(e->levelingpact);
}
static void source_receive(const U8 *data,U32 bits,int aligned,U32 start,int stale,TailObservation *observation) {
    U32 storage[65536]={0};Packet p={0};Entity e={0};
    initBitStream(&p.stream,(U8*)storage,sizeof(storage),Read,aligned,0);memcpy(storage,data,(bits+7)/8);p.stream.bitLength=bits;p.stream.cursor.byte=start/8;p.stream.cursor.bit=start%8;
    e.type=ENTTYPE_PLAYER;e.db_id=4242;e.pchar=&e;e.supergroup_id=99;strcpy(e.supergroup_name,"PriorGroup");strcpy(e.supergroup_emblem,"PriorEmblem");e.supergroup_color[0]=0x11;e.supergroup_color[1]=0x22;e.levelingpact_id=88;e.logout_bad_connection=1;e.logout_timer=270;
    entReceiveOtherSupergroupInfo(&p,&e,stale);
    entReceiveLevelingpactInfo(&p,&e,false);
    entReceiveLogoutUpdate(&p,&e,stale);
    assert(!p.stream.errorFlags&&bsGetCursorBitPosition(&p.stream)==bits);source_observe(observation,&e);receiver_free(&e);
}
static unsigned stale_pact_differences;
unsigned tail_stale_pact_differences(void){return stale_pact_differences;}
unsigned tail_observation_size(void){return sizeof(TailObservation);}
void tail_original(unsigned scenario,unsigned aligned,unsigned offset,U8 *out,U32 *bits,U32 *begin,TailObservation *normal,TailObservation *stale) {
    U32 storage[65536]={0};Packet p={0};Entity e={0};Supergroup s={0};Levelingpact pact={0};int ids[2]={777,4242};MemberName names[2]={"First","Second"};
    StoryTaskInfo task={0};TaskDef def={0};char long_text[1100],name_storage[258][32];RewardToken token_storage[258];RecipeInvItem recipe_storage[258];SpecialDetail detail_storage[258];
    struct {int map_id;} team={1};int update=scenario!=0,sendself=1,pact_update=scenario!=0,logout_update=scenario!=0;
    memset(long_text,'x',sizeof(long_text));long_text[999]=0;memset(&server_state,0,sizeof(server_state));memset(&db_state,0,sizeof(db_state));
    fixture_location=(StoryLocation){{12.5f,-4.75f,100.0f},2,7};strcpy(fixture_local_member.name,"CachedMember");
    e.type=ENTTYPE_PLAYER;e.db_id=4242;strcpy(e.name,"SourcePlayer");e.pchar=&e;e.teamup=(void*)&team;e.supergroup_id=321;e.supergroup=&s;e.levelingpact_id=71;
    strcpy(s.name,"SourceGroup");strcpy(s.emblem,"KnownEmblem");s.colors[0]=0x12345678;s.colors[1]=0xa1b2c3d4;s.spacesForItemsOfPower=9;
    e.logout_bad_connection=1;e.logout_timer=91.5f;
    def=(TaskDef){"logical","Mission description","defs/fixture.task",NULL,"fixture.map","crystal","Fixture Zowie","2 3",1,1};
    task.def=&def;task.sahandle=(StoryHandle){123,4};task.difficulty=(StoryDifficulty){-1,8,1,1};task.level=49;task.alliance=3;
    task.timeout=123456;task.timezero=0xf1234567u;task.timerType=2;task.failOnTimeout=1;task.complete=1;task.mission=1;task.running=1;task.zone=1;task.teleport=1;task.abandon=1;task.status="Task status";task.completeSideObjectives=17;task.seed=0xaabbccdd;
    if(scenario>=3)s.activetask=&task;
    if(scenario>=3){
        token_storage[0]=(RewardToken){"TokenA",3,5};token_storage[1]=(RewardToken){"TokenB",7,9};token_storage[2]=(RewardToken){"TokenA",11,13};
        for(unsigned i=0;i<3;i++)eaPush(&s.rewardTokens,&token_storage[i]);eaPush(&s.rewardTokens,NULL);
        recipe_storage[0]=(RecipeInvItem){&fixture_recipes[0],-1};recipe_storage[1]=(RecipeInvItem){&fixture_recipes[1],0};recipe_storage[2]=(RecipeInvItem){&fixture_recipes[1],23};
        for(unsigned i=0;i<3;i++)eaPush(&s.invRecipes,&recipe_storage[i]);
        detail_storage[0]=(SpecialDetail){&fixture_details[0],1,2,3,0};detail_storage[1]=(SpecialDetail){NULL,4,5,6,0};
        for(unsigned i=0;i<2;i++)eaPush(&s.specialDetails,&detail_storage[i]);
        pact.members=(TeamMembers){2,ids,NULL,NULL,names};e.levelingpact=&pact;
    }
    if(scenario==1){e.supergroup=NULL;e.logout_timer=0;e.logout_bad_connection=0;}
    if(scenario==2){e.type=1;}
    if(scenario==4){task.location=1;server_state.clickToSource=1;}
    if(scenario==5){def.taskLocationMap="maps/explicit_fixture.txt";task.zowie=1;server_state.clickToSource=1;}
    if(scenario==6){task.location=1;task.zowie=1;db_state.local_server=1;server_state.clickToSource=1;}
    if(scenario==7){db_state.is_endgame_raid=1;}
    if(scenario==8){sendself=0;}
    if(scenario==9){strcpy(s.emblem,"UnknownEmblem");recipe_storage[2].recipe=&fixture_recipes[2];detail_storage[0].pDetail=&fixture_details[2];}
    if(scenario==10){token_storage[0].val=-1;token_storage[1].timer=(int)0x80000000u;task.difficulty.levelAdjust=(int)0x80000000u;task.timezero=0xffffffffu;task.timerType=0xffffffffu;detail_storage[0].iFlags=0xffffffffu;}
    if(scenario==11){def.inprogress_description=long_text;task.status=long_text;task.location=1;}
    if(scenario==12){memset(names[0],'p',63);names[0][63]=0;memset(names[1],'q',63);names[1][63]=0;}
    if(scenario==13){update=0;pact_update=0;e.logout_timer=30.0f*12345;}
    if(scenario==14){e.supergroup_id=0;}
    if(scenario==15){pact.members.count=0;}
    if(scenario==16){e.type=1;}
    if(scenario==17){s.name[0]=0;s.emblem[0]=0;names[0][0]=0;names[1][0]=0;def.inprogress_description="";task.status="";}
    if(scenario>=18&&scenario<=23){s.activetask=NULL;e.levelingpact=NULL;eaDestroy(&s.rewardTokens);eaDestroy(&s.invRecipes);eaDestroy(&s.specialDetails);
        if(scenario==18||scenario==21){unsigned n=scenario==18?256:257;for(unsigned i=0;i<n;i++){snprintf(name_storage[i],32,"Token%u",i);token_storage[i]=(RewardToken){name_storage[i],(int)i,(int)(i+1)};eaPush(&s.rewardTokens,&token_storage[i]);}}
        if(scenario==19){for(unsigned i=0;i<256;i++){recipe_storage[i]=(RecipeInvItem){&fixture_recipes[i%2],(int)i};eaPush(&s.invRecipes,&recipe_storage[i]);}}
        if(scenario==20){for(unsigned i=0;i<256;i++){detail_storage[i]=(SpecialDetail){&fixture_details[i%2],i,i+1,i+2,0};eaPush(&s.specialDetails,&detail_storage[i]);}}
        if(scenario==22||scenario==23){memset(long_text,'x',1024);long_text[scenario==22?1024:1023]=0;unsigned n=scenario==22?1:65;for(unsigned i=0;i<n;i++){token_storage[i]=(RewardToken){long_text,(int)i,(int)(i+1)};eaPush(&s.rewardTokens,&token_storage[i]);}}
    }
    if(scenario==26){eaDestroy(&s.rewardTokens);memset(long_text,'x',1023);long_text[1023]=0;token_storage[0]=(RewardToken){long_text,17,23};eaPush(&s.rewardTokens,&token_storage[0]);}
    if(scenario==27){task.difficulty=(StoryDifficulty){0};task.level=0;task.alliance=0;task.timeout=task.timezero=task.timerType=task.failOnTimeout=0;task.complete=task.mission=task.running=task.zone=task.teleport=task.abandon=0;def.sg=def.force=0;}
    if(scenario==24){s.activetask=NULL;e.levelingpact=NULL;eaDestroy(&s.rewardTokens);eaDestroy(&s.invRecipes);eaDestroy(&s.specialDetails);eaPush(&s.invRecipes,NULL);}
    fixture_mission=task.mission;
    initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);if(offset)pktSendBits(&p,offset,0);*begin=bsGetCursorBitPosition(&p.stream);
    entSendOtherSupergroupInfo(&p,&e,update,sendself);U32 pact_begin=bsGetCursorBitPosition(&p.stream);
    entSendLevelingpactInfo(&p,&e,pact_update);U32 pact_end=bsGetCursorBitPosition(&p.stream);
    entSendLogoutUpdate(&p,&e,logout_update);*bits=p.stream.bitLength;assert(!p.stream.errorFlags);memcpy(out,storage,(*bits+7)/8);
    memset(normal,0,sizeof(*normal));memset(stale,0,sizeof(*stale));
    if(scenario!=24){source_receive(out,*bits,aligned,*begin,0,normal);source_receive(out,*bits,aligned,*begin,1,stale);}
    if(pact_update&&e.levelingpact&&pact.members.count){
        Packet read={0};U32 copy[65536]={0};Entity receiver={0};receiver.pchar=&receiver;
        initBitStream(&read.stream,(U8*)copy,sizeof(copy),Read,aligned,0);memcpy(copy,out,(*bits+7)/8);read.stream.bitLength=*bits;read.stream.cursor.byte=pact_begin/8;read.stream.cursor.bit=pact_begin%8;
        assert(entReceiveLevelingpactInfo(&read,&receiver,true));assert(bsGetCursorBitPosition(&read.stream)<pact_end);stale_pact_differences++;receiver_free(&receiver);
    }
    eaDestroy(&s.rewardTokens);eaDestroy(&s.invRecipes);eaDestroy(&s.specialDetails);
}
/* Consumer-supported absent-name pact branch is not emitted by the current
 * original sender. Exercise it explicitly, preserving that distinction. */
void tail_receiver_only(unsigned aligned,unsigned offset,U8 *out,U32 *bits,U32 *begin,TailObservation *normal,TailObservation *stale) {
    U32 storage[256]={0};Packet p={0};initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
    strcpy(fixture_local_member.name,"CachedMember");if(offset)pktSendBits(&p,offset,0);*begin=bsGetCursorBitPosition(&p.stream);
    pktSendBits(&p,1,0);pktSendBits(&p,1,1);pktSendBitsAuto(&p,71);pktSendBitsAuto(&p,2);
    pktSendBitsAuto(&p,777);pktSendBits(&p,1,0);pktSendBitsAuto(&p,778);pktSendBits(&p,1,0);pktSendBits(&p,1,0);
    *bits=p.stream.bitLength;memcpy(out,storage,(*bits+7)/8);source_receive(out,*bits,aligned,*begin,0,normal);source_receive(out,*bits,aligned,*begin,1,stale);
}
/* Independent source prior-state controls document why the production module
 * emits raw events rather than applying assumed stale/clear behavior. */
unsigned tail_prior_controls(void) {
    unsigned checks=0;U32 storage[2048]={0};Packet p={0};Entity send={0},recv={0};Supergroup source_group={0};
#define SOURCE_CHECK(x) do{assert(x);checks++;}while(0)
    recv.pchar=&recv;recv.supergroup_id=99;recv.levelingpact_id=88;recv.logout_timer=270;recv.logout_bad_connection=1;
    strcpy(recv.supergroup_name,"PriorGroup");strcpy(recv.supergroup_emblem,"PriorEmblem");recv.supergroup_color[0]=17;
    recv.supergroup=createSupergroup();Supergroup *prior_group=recv.supergroup;recv.supergroup->sgMission=TaskStatusCreate();TaskStatus *prior_mission=recv.supergroup->sgMission;
    recv.levelingpact=createLevelingpact();
    initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,0,0);entSendOtherSupergroupInfo(&p,&send,1,1);entSendLevelingpactInfo(&p,&send,1);entSendLogoutUpdate(&p,&send,0);
    U32 bits=p.stream.bitLength;p.stream.mode=Read;p.stream.cursor.byte=p.stream.cursor.bit=0;
    SOURCE_CHECK(entReceiveOtherSupergroupInfo(&p,&recv,true));SOURCE_CHECK(recv.supergroup_id==0&&!recv.supergroup_name[0]&&!recv.supergroup_emblem[0]);
    SOURCE_CHECK(recv.supergroup==prior_group&&recv.supergroup->sgMission==prior_mission&&recv.supergroup_color[0]==17);
    SOURCE_CHECK(entReceiveLevelingpactInfo(&p,&recv,true));SOURCE_CHECK(!recv.levelingpact&&recv.levelingpact_id==88);
    SOURCE_CHECK(!entReceiveLogoutUpdate(&p,&recv,true)&&recv.logout_timer==270&&recv.logout_bad_connection==1);
    SOURCE_CHECK(bsGetCursorBitPosition(&p.stream)==bits&&!p.stream.errorFlags);
    int idx=rewardtoken_Award(&recv.supergroup->rewardTokens,"PriorToken",4242);recv.supergroup->rewardTokens[idx]->val=91;
    sgrp_SetRecipeNoLock(recv.supergroup,&fixture_recipes[0],5,0);
    SpecialDetail *old_detail=calloc(1,sizeof(*old_detail));assert(old_detail);old_detail->pDetail=&fixture_details[0];eaPush(&recv.supergroup->specialDetails,old_detail);
    send.supergroup_id=321;send.supergroup=&source_group;strcpy(source_group.name,"SourceGroup");strcpy(source_group.emblem,"KnownEmblem");source_group.colors[0]=23;
    memset(storage,0,sizeof(storage));initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,0,0);entSendOtherSupergroupInfo(&p,&send,1,1);bits=p.stream.bitLength;p.stream.mode=Read;p.stream.cursor.byte=p.stream.cursor.bit=0;
    SOURCE_CHECK(entReceiveOtherSupergroupInfo(&p,&recv,false));SOURCE_CHECK(recv.supergroup==prior_group&&!recv.supergroup->sgMission);
    SOURCE_CHECK(eaSize(&recv.supergroup->rewardTokens)==1&&recv.supergroup->rewardTokens[0]->val==91);
    SOURCE_CHECK(eaSize(&recv.supergroup->invRecipes)==0&&eaSize(&recv.supergroup->specialDetails)==0);
    SOURCE_CHECK(recv.supergroup_id==321&&!strcmp(recv.supergroup_name,"SourceGroup")&&recv.supergroup_color[0]==23);
    SOURCE_CHECK(bsGetCursorBitPosition(&p.stream)==bits&&!p.stream.errorFlags);
    /* Original eaDestroy frees the old detail array, not each detail object.
     * This fixture retains and releases its prior object explicitly; no source
     * memory ownership or leak-freedom claim is made by the raw-wire module. */
    free(old_detail);receiver_free(&recv);
#undef SOURCE_CHECK
    return checks;
}
