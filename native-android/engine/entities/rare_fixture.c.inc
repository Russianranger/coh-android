/* Only exact inline statement blocks and named component functions execute.
 * The Entity/Player shells, lookup entries and UI callbacks are synthetic. */
static void rare_export_raw(Entity *e,int send_afk_string,CohEntRarePrefix *v){
    memset(v,0,sizeof(*v));Character *c=e->pchar;Player *p=e->pl;
    v->send_on_odd=e->net_info.send_on_odd_send;v->ally_id=c?c->iAllyID:0;v->gang_id=c?c->iGangID:0;
    v->ignore_combat=c?c->bIgnoreCombatMods:0;if(v->ignore_combat){v->combat_shift=c->ignoreCombatModLevelShift;v->combat_shift_wire=(U32)v->combat_shift+8;}
    v->player_type=p?p->playerType:0;v->player_subtype=p?p->playerSubType:0;v->praetorian_progress=p?p->praetorianProgress:0;v->player_location=c?c->playerTypeByLocation:0;
    v->pvp_switch=p?p->pvpSwitch:0;v->pvp_active=c?c->bPvPActive:0;v->pvp_timer=(int)e->pvpZoneTimer;v->is_ganker=p?p->bIsGanker:0;
    v->no_collision=e->motion->input.no_ent_collision;v->not_selectable=e->notSelectable;v->no_draw=e->noDrawOnClient;v->show_on_map=e->showOnMap;
    v->contact_pnpc=e->contactOrPnpc;v->contact_architect=e->contactArchitect;v->always_con=e->alwaysCon;v->see_through_walls=e->seeThroughWalls;
    if(e->name_update&&e->name){v->name_present=1;strcpy(v->name,e->name);}
    if(e->erOwner){v->is_pet=1;v->owner_index=e->erOwner->owner;v->creator_index=e->erCreator?e->erCreator->owner:0;
        if(c&&c->ppowCreatedMe){v->power_present=1;v->power_crc=c->ppowCreatedMe->crcFullName;}
        v->commandable_pet=e->commandablePet;v->visible_pet=isPetDisplayed(e);v->dismissable_pet=e->petDismissable;
        if(e->specialPowerDisplayName&&e->specialPowerDisplayName[0]){v->power_display_present=1;strcpy(v->special_power_display,e->specialPowerDisplayName);}
        v->special_power_state=e->specialPowerState;
        if(e->petName&&e->petName[0]){v->pet_name_present=1;strcpy(v->pet_name,e->petName);}
    }
    v->afk=p?p->afk:0;if(v->afk&&send_afk_string){v->afk_message_present=1;strcpy(v->afk_message,p->afk_string);}
}
unsigned original_rare_size(void){return sizeof(CohEntRarePrefix);}
static void rare_receive_check(const U8 *data,U32 bits,int aligned,U32 start,int player,int isSelf,int stale,const CohEntRarePrefix *v){
    U32 storage[8192]={0};Packet pak={0};Entity e={0},owner={0},creator={0},other={0};Character c={0};Player pl={0};RareMotion motion={0};char name[128]="PriorName";
    e.type=player?ENTTYPE_PLAYER:ENTTYPE_CRITTER;e.pchar=&c;e.pl=player?&pl:NULL;e.motion=&motion;e.name=name;
    e.specialPowerDisplayName=rare_strdup("PriorDisplay");e.petName=rare_strdup("PriorPet");e.erOwner=&other;e.erCreator=&other;
    c.ppowCreatedMe=&rare_power;c.iAllyID=17;c.iGangID=19;c.ignoreCombatModLevelShift=99;c.bIgnoreCombatMods=1;
    pl.afk=1;strcpy(pl.afk_string,"PriorAFK");e.notSelectable=1;pl.playerType=1;pl.playerSubType=1;pl.praetorianProgress=1;
    rare_player=isSelf?&e:&other;owner.owner=12;creator.owner=13;entities[12]=&owner;entities[13]=&creator;
    initBitStream(&pak.stream,(U8*)storage,sizeof(storage),Read,aligned,0);memcpy(storage,data,(bits+7)/8);pak.stream.bitLength=bits;
    pak.stream.cursor.byte=start/8;pak.stream.cursor.bit=start%8;
    original_rare_receive_statement(&pak,&e,stale,isSelf);
    assert(!pak.stream.errorFlags&&bsGetCursorBitPosition(&pak.stream)==bits);
    assert(e.net_info.send_on_odd_send==(stale?0:(int)v->send_on_odd));
    assert(c.iAllyID==(stale?17:(int)v->ally_id)&&c.iGangID==(stale?19:(int)v->gang_id));
    assert(c.ignoreCombatModLevelShift==(stale?99:v->combat_shift));
    assert(c.bIgnoreCombatMods==(stale?1:(int)v->ignore_combat));
    if(!stale){assert(c.bPvPActive==(int)v->pvp_active);assert(e.pvpClientZoneTimer==(int)v->pvp_timer);assert(e.pvpUpdateTime==12345);}
    assert(e.motion->input.no_ent_collision==(!stale&&!isSelf?(int)v->no_collision:0));
    assert(e.notSelectable==(!stale&&!player?(int)v->not_selectable:0));
    assert(e.noDrawOnClient==(!stale&&!isSelf?(int)v->no_draw:0));
    assert(e.showOnMap==(!stale&&!isSelf?(int)v->show_on_map:0));
    assert(e.contactOrPnpc==(!stale&&!isSelf?(int)v->contact_pnpc:0));
    assert(e.contactArchitect==(!stale&&!isSelf?(int)v->contact_architect:0));
    assert(e.alwaysCon==(!stale?(int)v->always_con:0)&&e.seeThroughWalls==(!stale?(int)v->see_through_walls:0));
    assert(!strcmp(e.name,!stale&&!isSelf&&v->name_present&&v->name[0]?v->name:"PriorName"));
    if(player&&!stale){assert(pl.playerType==(int)v->player_type&&pl.playerSubType==(int)v->player_subtype&&pl.praetorianProgress==(int)v->praetorian_progress);assert(c.playerTypeByLocation==(int)v->player_location);assert(pl.pvpSwitch==(int)v->pvp_switch&&pl.bIsGanker==(int)v->is_ganker);assert(pl.afk==(int)v->afk);}
    if(player)assert(!strcmp(pl.afk_string,!stale&&v->afk_message_present?v->afk_message:"PriorAFK"));
    if(v->is_pet){
        assert(e.erOwner==(!stale?&owner:&other));assert(e.erCreator==(!stale&&v->creator_index?&creator:&other));
        assert(c.ppowCreatedMe==&rare_power);
        if(!stale){assert(e.commandablePet==(int)v->commandable_pet&&e.petVisibility==(int)v->visible_pet&&e.petDismissable==(int)v->dismissable_pet);assert(e.specialPowerState==(int)v->special_power_state);assert(v->power_display_present?!strcmp(e.specialPowerDisplayName,v->special_power_display):e.specialPowerDisplayName==NULL);}
        assert(!strcmp(e.petName,v->pet_name_present?v->pet_name:"PriorPet")); /* source updates even stale */
    }else{assert(!e.erOwner&&!e.erCreator&&!e.petName&&!e.specialPowerDisplayName);}
    SAFE_FREE(e.specialPowerDisplayName);SAFE_FREE(e.petName);entities[12]=NULL;entities[13]=NULL;rare_player=NULL;
}
void original_rare(int scenario,int aligned,int offset,U8 *out,U32 *length,U32 *start,CohEntRarePrefix *expected){
    U32 storage[8192]={0};Packet p={0};Entity e={0},owner={0},creator={0};Character ch={0};Player pl={0};RareMotion motion={0};
    char name[128]="SourceRare",pet[128]="SourcePet",display[1000]="SourcePower";int afk_string=1;
    e.pchar=&ch;e.pl=&pl;e.motion=&motion;e.name=name;e.type=ENTTYPE_PLAYER;
    if(scenario){
        e.net_info.send_on_odd_send=1;ch.iAllyID=5;ch.iGangID=1025;ch.bIgnoreCombatMods=1;ch.ignoreCombatModLevelShift=-8;
        pl.playerType=1;pl.playerSubType=3;pl.praetorianProgress=7;ch.playerTypeByLocation=1;pl.pvpSwitch=1;pl.bIsGanker=1;ch.bPvPActive=1;e.pvpZoneTimer=63.75f;
        motion.input.no_ent_collision=1;e.notSelectable=1;e.noDrawOnClient=1;e.showOnMap=1;e.contactOrPnpc=1;e.contactArchitect=1;e.alwaysCon=1;e.seeThroughWalls=1;e.name_update=1;
        owner.owner=12;creator.owner=13;e.erOwner=&owner;e.erCreator=&creator;ch.ppowCreatedMe=&rare_power;e.commandablePet=1;e.petDismissable=1;e.specialPowerState=17;
        e.specialPowerDisplayName=display;e.petName=pet;pl.afk=1;strcpy(pl.afk_string,"SourceAFK");
    }
    if(scenario==2){e.erCreator=NULL;ch.ppowCreatedMe=NULL;e.specialPowerDisplayName=NULL;e.petName=NULL;ch.ignoreCombatModLevelShift=-9;afk_string=0;}
    if(scenario==3){memset(name,'n',sizeof(name)-1);name[127]=0;memset(pet,'p',sizeof(pet)-1);pet[127]=0;memset(display,'d',sizeof(display)-1);display[999]=0;memset(pl.afk_string,'a',47);pl.afk_string[47]=0;ch.ignoreCombatModLevelShift=0;}
    if(scenario==4){e.pl=NULL;e.pchar=NULL;e.erOwner=NULL;e.type=ENTTYPE_CRITTER;e.name_update=1;}
    if(scenario==5){e.name[0]=0;e.petName[0]=0;e.specialPowerDisplayName[0]=0;pl.afk_string[0]=0;ch.ignoreCombatModLevelShift=INT32_MAX-8;}
    if(scenario==6){ch.ignoreCombatModLevelShift=INT32_MIN;e.specialPowerState=-1;ch.iAllyID=-1;ch.iGangID=-1;}
    if(scenario==7){ch.bIgnoreCombatMods=0;e.erOwner=NULL;e.name_update=0;pl.afk=0;}
    rare_export_raw(&e,afk_string,expected);
    initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);if(offset)pktSendBits(&p,offset,0);*start=bsGetCursorBitPosition(&p.stream);
    original_rare_send_statement(&p,&e,afk_string);*length=p.stream.bitLength;expected->end_bit=*length;memcpy(out,storage,(*length+7)/8);
    for(int self=0;self<2;self++)for(int stale=0;stale<2;stale++)rare_receive_check(out,*length,aligned,*start,e.pl!=NULL,self,stale,expected);
}
