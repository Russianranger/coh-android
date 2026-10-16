void original_envelope(int scenario,int aligned,U8 *out,U32 *length,U8 *expected,U32 *expected_size){
 U32 storage[32768]={0};Packet p={0};Entity send={0},received={0};Player sp={0},rp={0};
 Costume send_bodies[12]={{0}},receive_bodies[12]={{0}};CostumePart send_parts[12][30]={0},receive_parts[12][30]={0};
 CustomNPCCostume custom={0};CustomNPCCostumePart custom_values[2]={0};CustomNPCCostumePart *custom_ptrs[]={custom_values,custom_values+1};
 RewardToken rewards[]={{"Male"},{"NotAReward"},{"LiteralReward"},{"NotAReward"},{"FixtureGeometry"}};
 struct {const char *name;} seqtype={"FixtureSequence"};SeqInst seq={(void*)&seqtype};CohEntCostumeEnvelope *result=calloc(1,sizeof(*result));assert(result);
 for(unsigned n=0;n<12;n++){
  for(unsigned j=0;j<30;j++){send_bodies[n].parts[j]=&send_parts[n][j];receive_bodies[n].parts[j]=&receive_parts[n][j];}
  send_bodies[n].appearance.bodytype=1;send_bodies[n].appearance.iNumParts=1;send_bodies[n].appearance.colorSkin.integer=1000+n;send_bodies[n].appearance.fScales[0]=1.25f;
  send_parts[n][0].pchGeom="FixtureGeometry";send_parts[n][0].pchTex1="InlineTexture";send_parts[n][0].pchTex2="InlineTexture";send_parts[n][0].regionName="Upper";send_parts[n][0].bodySetName="BodySet";send_parts[n][0].color[0].integer=0x11223344;
 }
 for(unsigned n=0;n<10;n++){sp.costume[n]=&send_bodies[n];rp.costume[n]=&receive_bodies[n];}
 sp.superCostume=&send_bodies[10];rp.superCostume=&receive_bodies[10];dummy_ent_costume=&receive_bodies[11];fixture_npc_costume=&receive_bodies[11];
 reward_ptrs[0]=&rewards[0];reward_ptrs[1]=&rewards[1];reward_ptrs[2]=&rewards[2];architect_ptrs[0]=&rewards[3];architect_ptrs[1]=&rewards[4];sp.rewardTokens=reward_ptrs;sp.ArchitectRewardTokens=architect_ptrs;
 send.type=scenario==3?ENTTYPE_CRITTER:scenario==4?ENTTYPE_NPC:scenario==5?ENTTYPE_MISSION_ITEM:ENTTYPE_PLAYER;received.type=send.type;
 send.pl=scenario<3||scenario>=7?&sp:NULL;received.pl=send.pl?&rp:NULL;send.seq=received.seq=&seq;send.npcIndex=123;send.costumeIndex=2;send.costumeWorldGroup="FixtureWorld";send.name=received.name="Fixture";
 send.ownedCostume=scenario==3?&send_bodies[0]:NULL;send.send_all_costume=scenario==0||scenario==7||scenario==8;sp.current_costume=1;sp.num_costume_slots=3;sp.num_costumes_stored=2;rp.num_costume_slots=3;
 if(scenario==8){sp.current_costume=9;sp.num_costumes_stored=10;sp.num_costume_slots=2;}
 if(scenario==9){sp.current_costume=0;sp.num_costumes_stored=1;sp.num_costume_slots=0;}
 if(scenario==2||scenario==7)sp.pendingCostumeForceTime=20;
 if(scenario==0){send.supergroup_id=42;sp.supergroup_mode=1;sp.hide_supergroup_emblem=1;strcpy(sp.costumeFxSpecial,"FIXTUREFX");sp.npc_costume=1;}
 if(scenario==0||scenario==4){custom_count=2;custom.parts=custom_ptrs;custom.skinColor.integer=0x22334455;for(unsigned n=0;n<2;n++){custom_values[n].color[0].integer=600+n;custom_values[n].color[1].integer=700+n;custom_values[n].regionName=n?"Head":"Upper";}send.customNPC_costume=&custom;}
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);entSendCostume(&p,&send,(scenario==0||scenario==1||scenario>=7)?&send:NULL,scenario!=6);*length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=p.stream.cursor.bit=0;literal_count=world_count=allocated_count=body_receipt_count=0;fixture_player=(scenario==0||scenario==1||scenario>=7)?&received:NULL;
 int applied=entReceiveCostume(&p,&received,0);assert(applied==(scenario!=6));assert(bsGetCursorBitPosition(&p.stream)==*length);
 result->generation=9;memset(result->manifest_sha256,0x42,32);result->type=scenario==6?0:scenario==3?2:scenario==4?3:scenario==5?4:1;
 if(result->type==1){
  result->is_self=fixture_player==&received;result->deferred=rp.pendingCostumeNumber!=0;result->multiple=send.send_all_costume;
  if(result->is_self){
   result->current_slot=result->deferred?(rp.pendingCostumeNumber&255)-1:rp.current_costume;result->additional_slots=rp.num_costume_slots;
   result->reward_count[0]=3;result->reward_count[1]=2;assert(received_reward_count[0]==2&&received_reward_count[1]==1);
   expected_text(&result->rewards[0][0],received_rewards[0][0]);expected_text(&result->rewards[0][2],received_rewards[0][1]);expected_text(&result->rewards[1][1],received_rewards[1][0]);
  }
  result->super_present=scenario==0;result->super_mode=rp.supergroup_mode;result->hide_emblem=rp.hide_supergroup_emblem;
  if(rp.costumeFxSpecial[0])expected_text(&result->special_fx,rp.costumeFxSpecial);
 }
 result->body_count=body_receipt_count-result->super_present;
 for(unsigned n=0;n<result->body_count;n++)expected_costume(&result->bodies[n],body_receipts[n].body,result->is_self,body_receipts[n].end);
 if(result->super_present)expected_costume(&result->super_body,body_receipts[result->body_count].body,1,body_receipts[result->body_count].end);
 result->npc_present=scenario==0||scenario==4;
 if(result->npc_present){
  result->npc_index=received.npcIndex;result->npc_costume_index=received.costumeIndex;expected_text(&result->world_group,received.costumeWorldGroup);
  result->custom_present=received.customNPC_costume!=NULL;
  if(result->custom_present){result->custom.skin_color=received.customNPC_costume->skinColor.integer;result->custom.count=custom_count;for(unsigned n=0;n<custom_count;n++){result->custom.parts[n].colors[0]=received.customNPC_costume->parts[n]->color[0].integer;result->custom.parts[n].colors[1]=received.customNPC_costume->parts[n]->color[1].integer;strcpy(result->custom.parts[n].region,received.customNPC_costume->parts[n]->regionName);}result->custom.end_bit=*length;fixture_custom_free(received.customNPC_costume);}
 }else if(scenario==5){strcpy(result->sequence,received.seq->type->name);expected_text(&result->world_group,received.costumeWorldGroup);}
 result->end_bit=*length;*expected_size=sizeof(*result);memcpy(expected,result,sizeof(*result));free(result);
}
