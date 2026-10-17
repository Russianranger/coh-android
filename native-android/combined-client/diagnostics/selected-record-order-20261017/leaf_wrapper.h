/* kind1selfstats,2!RAGDOLL,3prepared-sequence(no stance),4status-effects.
 * Prefix remains in returned wire; begin/end delimit actual original leaf. */
void original_record_leaf(unsigned kind,unsigned scenario,unsigned aligned,unsigned prefix,U8*out,unsigned*bits,unsigned*begin,unsigned*end){
 assert(kind>=1&&kind<=4&&scenario<4&&aligned<=1&&prefix<8&&(!aligned||!prefix));U32 memory[16384]={0};Packet p={0};initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);for(unsigned k=0;k<prefix;k++)bsWriteBits(&p.stream,1,k&1);p.stream.byteAlignedMode=aligned;*begin=bsGetCursorBitPosition(&p.stream);
 if(kind==1){
  StatsCharacter c={0};c.attrCur=(CharacterAttributes){123.45f,45.5f,91.2f,.753f,300.f,8.75f,-3.3f,.656f};c.attrMax=(CharacterAttributes){200.25f,55.5f,100.f,.853f,400.f,9.75f,2.4f,.757f};c.iLevel=12;c.iCombatLevel=14;c.iExperiencePoints=123456;c.iExperienceDebt=-123;c.iExperienceRest=1000;c.iInfluencePoints=7654321;
  if(scenario==3)memset(&c,0,sizeof(c));stats_ops[1]=(StatsOps){fixture_compare,int_senddiff};stats_ops[2]=(StatsOps){fixture_compare,float_senddiff};stats_ops[3]=(StatsOps){fixture_compare,struct_senddiff};LeafStatsEntity e={scenario==2?NULL:&c,&c,0};entSendCharacterStats(&p,&e,&e,scenario!=1);
 }else if(kind==2){Entity e={0};entSendRagdollUpdate(&p,&e,scenario&1);}
 else if(kind==3){
  int sticky[]={STATE_AMMO,STATE_CHEMICALROUNDS};LeafSeqCharacter ch={0};LeafSequence seq={0};LeafSeqEntity e={&ch,&seq,scenario==3?INT32_MAX:33,scenario==3?65535:4};leaf_seq_count=scenario==2?2:0;ch.piStickyAnimBits=leaf_seq_count?sticky:NULL;
  if(scenario==2){e.move_idx=e.net_move_change_time=0;seq.sticky_state[STATE_SHIELD/32]|=1u<<(STATE_SHIELD%32);seq.sticky_state[STATE_HOVER/32]|=1u<<(STATE_HOVER%32);}entSendSeqMoveUpdate(&p,&e,scenario!=1);
 }else{
  LeafStatusCharacter c={0};LeafStatusParent parent={1,0};LeafStatusMod mod={1};char*names[]={"source-status",""};c.entParent=&parent;g_attrModBase.fPerceptionRadius=300;c.attrMod.fPerceptionRadius=300;leaf_designer_count=0;
  if(scenario==1){c.attrCur=(LeafStatusAttributes){1,1,1,1,1,1,1,1,0};c.attrMod.fPerceptionRadius=100;c.pmodTaunt=&mod;c.pclass=leaf_classes;parent.bitfieldVisionPhases=5;parent.exclusiveVisionPhase=1;c.designerStatuses=names;leaf_designer_count=2;}
  if(scenario==2){c.attrCur.fMeter=1;c.attrMod.fPerceptionRadius=400;mod.fMagnitude=-1;c.pmodTaunt=&mod;}
  if(scenario==3){c.attrCur.fSleep=1;c.attrCur.fMeter=2;c.pclass=leaf_classes+2;c.attrMod.fPerceptionRadius=299;c.designerStatuses=names;leaf_designer_count=1;}
  character_SendStatusEffects(&p,&c);
 }
 assert(!p.stream.errorFlags);*end=*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);
}
