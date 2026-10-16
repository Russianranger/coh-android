void original_power_custom(int scenario,int aligned,U8 *out,U32 *length,U8 *expected,U32 *expected_size){
 U32 storage[32768]={0};Packet p={0};Entity send={0},received={0};Player sp={0},rp={0};PowerCustomizationList lists[10]={{0}},rlists[10]={{0}};CohEntPowerCustomEnvelope *result=calloc(1,sizeof(*result));assert(result);
 fixture_products=scenario==2?31:0;send.type=received.type=scenario==3?ENTTYPE_CRITTER:ENTTYPE_PLAYER;send.pl=scenario==3?NULL:&sp;received.pl=scenario==3?NULL:&rp;send.updated_powerCust=scenario!=5;send.send_all_powerCust=scenario==0||scenario==2;
 sp.current_powerCust=scenario==2?9:scenario==0?1:0;sp.num_costume_slots=scenario==2?4:scenario==0?1:0;
 for(unsigned n=0;n<10;n++){
  sp.powerCustomizationLists[n]=&lists[n];rp.powerCustomizationLists[n]=&rlists[n];
  for(unsigned j=0;j<(scenario==6?0:3);j++){
   PowerCustomization *v=calloc(1,sizeof(*v));assert(v);v->power=&fixture_powers[j==0?1:j==1?0:scenario==7?1:3];v->powerFullName=v->power->pchFullName;v->customTint.primary.integer=0x11223344u+n;v->customTint.secondary.integer=0xffffffffu-j;
   char token[64];snprintf(token,sizeof(token),"Token%u_%u",n,j);v->token=power_string(token);power_push(&lists[n].powerCustomizations,v);
  }
 }
 if(scenario==4){sp.powerCustomizationLists[0]=NULL;power_copy(&lists[0],&rlists[0]);}
 if(scenario==6){PowerCustomization *old=calloc(1,sizeof(*old));old->power=&fixture_powers[0];old->token=power_string("Previous");power_push(&rlists[0].powerCustomizations,old);}
 if(scenario==3)send.ownedPowerCustomizationList=&lists[0];
 int self=scenario!=1&&scenario!=3&&scenario!=5;
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);entSendPowerCust(&p,&send,self?&send:NULL);*length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=p.stream.cursor.bit=0;literal_count=query_count=power_receipt_count=0;fixture_player=self?&received:NULL;dummy_ent_powerCust=&rlists[9];assert(entReceivePowerCust(&p,&received,0));assert(bsGetCursorBitPosition(&p.stream)==*length);
 if(scenario==4)assert(eaSize(&rlists[0].powerCustomizations)==3);if(scenario==6)assert(eaSize(&rlists[0].powerCustomizations)==0);
 result->type=scenario==5?0:scenario==3?2:1;result->is_self=result->type==1?self:0;
 if(result->is_self){result->current_slot=rp.current_powerCust;result->additional_slots=rp.num_costume_slots;result->multiple=send.send_all_powerCust;}
 result->list_count=power_receipt_count;
 for(unsigned n=0;n<power_receipt_count;n++){
  CohEntPowerCustomRange *range=&result->lists[n];PowerCustomizationList *received_list=power_receipts[n].list;range->present=scenario!=4;range->first=result->item_count;range->count=power_receipts[n].query_count;range->end_bit=power_receipts[n].end;
  unsigned source_slot=result->type==2?0:result->multiple?n:result->current_slot;
  for(unsigned j=0;j<range->count;j++){
   char token[64];snprintf(token,sizeof(token),"Token%u_%u",source_slot,j);PowerCustomization *found=NULL;for(unsigned k=0;k<eaSize(&received_list->powerCustomizations);k++)if(!strcmp(token,received_list->powerCustomizations[k]->token))found=received_list->powerCustomizations[k];assert(found);
   CohEntPowerCustom *d=&result->items[result->item_count++];d->power_crc=queried_crcs[power_receipts[n].query_first+j];d->colors[0]=found->customTint.primary.integer;d->colors[1]=found->customTint.secondary.integer;strcpy(d->token,found->token);
  }
 }
 result->end_bit=*length;*expected_size=sizeof(*result);memcpy(expected,result,sizeof(*result));free(result);
 for(unsigned n=0;n<10;n++){power_clear(&lists[n]);power_clear(&rlists[n]);}if(received.ownedPowerCustomizationList){power_clear(received.ownedPowerCustomizationList);free(received.ownedPowerCustomizationList);}
}
