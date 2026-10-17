void record_clear_children(void){memset(children,0,sizeof(children));for(unsigned k=1;k<CH_COUNT;k++)children[k].required_mod8=255;}
/* required_mod8 is exact child producer start modulo8, or255 ONLY when the
 * independently qualified child provider explicitly allows bit relocation. */
void record_set_child(unsigned id,const U8*bytes,unsigned bits,unsigned required_mod8){assert(id>0&&id<CH_COUNT&&bits<=65536&&(required_mod8<=7||required_mod8==255));children[id]=(Child){bytes,bits,required_mod8};}
void record_outer(unsigned scenario,unsigned aligned,unsigned prefix,U8*out,unsigned*bits,unsigned*begin,unsigned*boundaries,unsigned*event_out,unsigned*events_count){
 assert(scenario<16&&aligned<=1&&prefix<=7&&(!aligned||!prefix));
 memset(storage,0,sizeof(storage));memset(&packet,0,sizeof(packet));initBitStream(&packet.stream,(U8*)storage,sizeof(storage),Write,0,0);
 for(unsigned k=0;k<prefix;k++)bsWriteBits(&packet.stream,1,k&1);packet.stream.byteAlignedMode=aligned;
 Entity e={0};Player pl={0};Character character={0};__typeof__(*e.motion)motion={0};
 e.info.net_prepared=1;e.pl=&pl;e.pchar=&character;e.motion=&motion;e.name="selected-source-fixture";e.xlucency=scenario&2?0.5f:1.0f;e.state.mode=scenario&1;e.bitfieldVisionPhases=1;e.exclusiveVisionPhase=scenario&3;e.shouldIConYellow=scenario&1;
 e.send_xlucency=1;e.status_effects_update=(scenario>>1)&1;e.name_update=(scenario>>2)&1;e.target_update=1;e.tf_params_update=1;e.taskforce=scenario&1?(void*)&e:NULL;
 e.info.send_on_odd_send=scenario&1;e.gender=1;e.name_gender=2;e.pvpZoneTimer=scenario;e.showOnMap=1;
 character.iAllyID=1;character.iGangID=scenario;character.bIgnoreCombatMods=(scenario>>2)&1;character.ignoreCombatModLevelShift=-3;character.iCombatModShiftToSendToClient=scenario;
 pl.titleThe=scenario;pl.titleTheText="The";pl.titleCommon="Fixture";pl.titleOrigin="Source";pl.titleSpecial="Bounded";pl.titleColors[0]=0x112233;pl.titleColors[1]=0x445566;pl.titleBadge=7;pl.glowieUnlocked=1;pl.attachArticle=1;pl.respecTokens=scenario;pl.lastTurnstileEventID=17;pl.lastTurnstileMissionID=23;pl.helperStatus=2;
 db_state.is_endgame_raid=(scenario>>3)&1;flashback=(scenario>>2)&1;send_ent.player_ent=&e;send_ent.destpak=&packet;send_ent.full_update=1;send_ent.last_idx_sent=16;send_ent.is_generic_pos_update=0;event_count=0;taskforce_started=0;taskforce_end=UINT_MAX;
 /* Delta index0 is original source output; record begins immediately after it.
  * Compute its exact size using the same original writer, then reset prefix. */
 unsigned saved=bsGetCursorBitPosition(&packet.stream);pktSendBitsPack(&packet,1,0);*begin=bsGetCursorBitPosition(&packet.stream);
 packet.stream.cursor.byte=saved/8;packet.stream.cursor.bit=saved&7;packet.stream.bitLength=saved;memset((U8*)storage+(saved+7)/8,0,sizeof(storage)-(saved+7)/8);
 sendEntity(17,&e,!(scenario&8));*bits=packet.stream.bitLength;memcpy(out,storage,(*bits+7)/8);*events_count=event_count;memcpy(event_out,events,event_count*3*sizeof(unsigned));
 assert(packet.stream.errorFlags==0);
 unsigned before[CH_COUNT],after[CH_COUNT];for(unsigned k=0;k<CH_COUNT;k++)before[k]=after[k]=UINT_MAX;
 for(unsigned k=0;k<event_count;k++){unsigned id=events[k*3];assert(before[id]==UINT_MAX);before[id]=events[k*3+1];after[id]=events[k*3+2];}
 unsigned pairs[26]={*begin,before[CH_MODES], before[CH_MODES],before[CH_TRIGGERS], before[CH_TRIGGERS],after[CH_AI], after[CH_AI],before[CH_COSTUME], before[CH_COSTUME],before[CH_POWER], before[CH_POWER],after[CH_POWER], after[CH_POWER],before[CH_RAGDOLL], before[CH_RAGDOLL],after[CH_RAGDOLL], after[CH_RAGDOLL],after[CH_INVENTORY], after[CH_INVENTORY],taskforce_end, taskforce_end,before[CH_SUPERGROUP], before[CH_SUPERGROUP],after[CH_LOGOUT], before[CH_TEAMMATE],after[CH_TEAMMATE]};
 memcpy(boundaries,pairs,sizeof(pairs));boundaries[26]=*begin;boundaries[27]=*bits;
 for(unsigned k=0;k<13;k++){assert(pairs[k*2]!=UINT_MAX&&pairs[k*2+1]>=pairs[k*2]);if(k)assert(pairs[k*2]==pairs[k*2-1]);}
}
