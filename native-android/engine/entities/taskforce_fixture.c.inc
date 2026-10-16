/* Synthetic outer update/flashback flags compose both original component
 * producers in the actual source order. Not complete sendEntity execution. */
void original_taskforce(int scenario,int aligned,U8 *out,U32 *length,U8 *expected,U32 *expected_size){
    U32 storage[32768]={0};Packet p={0};TaskEntity send={0},receive={0};TaskForce st={0},rt={0};
    Costume body={0};CostumePart parts[30]={0};CustomNPCCostume custom={0};
    CustomNPCCostumePart custom_value={0};CustomNPCCostumePart *custom_ptrs[]={&custom_value};
    char review_name[256]="FixtureArc",review_author[128]="FixtureAuthor",review_description[4096]="FixtureDescription";
    PlayerCreatedStoryArc arc={review_name,review_author,review_description,1024,3};
    CohEntTaskforce *result=calloc(1,sizeof(*result));assert(result);
    send.taskforce=&st;receive.taskforce=&rt;send.onArchitect=scenario>=2&&scenario!=10;
    send.invincible=3;send.untargetable=17;st.architect_flags=0x42;st.architect_id=12345;st.architect_contact_override=1024;
    strcpy(st.architect_contact_name,"FixtureContact");
    for(unsigned i=0;i<30;i++)body.parts[i]=&parts[i];body.appearance.bodytype=1;body.appearance.iNumParts=1;body.appearance.colorSkin.integer=0x10203040;
    body.appearance.fScales[0]=1.25f;parts[0].pchGeom="FixtureGeometry";parts[0].pchTex1="InlineTexture";parts[0].pchTex2="InlineTexture";
    parts[0].color[0].integer=0x11223344;
    custom.skinColor.integer=0xabcdef01;custom.parts=custom_ptrs;custom_count=1;custom_value.regionName="Upper";custom_value.color[0].integer=11;custom_value.color[1].integer=22;
    if(scenario==4||scenario==6||scenario==7)st.architect_contact_costume=&body;
    if(scenario==5||scenario==6||scenario==7)st.architect_contact_npc_costume=&custom;
    if(scenario==7)st.architect_useCachedCostume=1;
    task_arc=(scenario==3||scenario>=8)&&scenario!=10?&arc:NULL;
    if(scenario==8){memset(st.architect_contact_name,'c',31);memset(review_name,'n',255);memset(review_author,'a',127);memset(review_description,'d',4095);}
    if(scenario==9){review_name[0]=review_author[0]=review_description[0]=0;arc.rating=-1;arc.european=0;}
    int architect_update=scenario!=0;
    int parameter_update=scenario==1||scenario>=3;
    int flashback=scenario%2;
    st.parametersSet=scenario==10?UINT32_MAX:scenario==1?0:(1u<<1)|(1u<<23)|(1u<<4);
    for(unsigned i=0;i<32;i++)st.parameters[i]=i==1?5:i==23?0:(i+1)*1023u;
    initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
    pktSendBits(&p,1,architect_update);if(architect_update)entSendTaskforceArchitectInfo(&send,&p);
    pktSendBitsPack(&p,1,flashback);pktSendBits(&p,1,parameter_update);if(parameter_update)entSendTaskforceParameters(&st,&p);
    *length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
    p.stream.mode=Read;p.stream.cursor.byte=p.stream.cursor.bit=0;literal_count=task_string_count=allocated_count=body_receipt_count=0;task_review_received=0;task_custom_end=0;
    rt.parametersSet=0x80000000u;for(unsigned i=0;i<32;i++)rt.parameters[i]=0x12345678u;
    rt.architect_contact_override=-1;strcpy(rt.architect_contact_name,"OldContact");rt.architect_useCachedCostume=1;
    entRecieveTaskforceArchitectInfo(&p,&receive);entReceiveTaskforceParameters(&p,&receive);
    assert(bsGetCursorBitPosition(&p.stream)==*length&&!p.stream.errorFlags);
    result->generation=9;result->architect_update=architect_update;result->on_architect=receive.onArchitect;
    if(receive.onArchitect){
        result->architect_flags=rt.architect_flags;result->architect_id=rt.architect_id;result->contact_override=rt.architect_contact_override;
        strcpy(result->contact_name,rt.architect_contact_name);
        result->costume_exists=st.architect_contact_costume!=NULL;result->costume_body=body_receipt_count!=0;
        result->custom_exists=st.architect_contact_npc_costume!=NULL;result->custom_body=task_custom_end!=0;
        if(result->costume_body){assert(body_receipt_count==1);expected_costume(&result->costume,rt.architect_contact_costume,0,body_receipts[0].end);}
        if(result->custom_body){
            CustomNPCCostume *c=rt.architect_contact_npc_costume;result->custom.skin_color=c->skinColor.integer;result->custom.count=custom_count;result->custom.end_bit=task_custom_end;
            for(unsigned i=0;i<custom_count;i++){result->custom.parts[i].colors[0]=c->parts[i]->color[0].integer;result->custom.parts[i].colors[1]=c->parts[i]->color[1].integer;strcpy(result->custom.parts[i].region,c->parts[i]->regionName);}
            fixture_custom_free(c);
        }
        result->review_present=task_review_received;
        if(task_review_received){strcpy(result->review_name,task_review_name);strcpy(result->review_author,task_review_author);strcpy(result->review_description,task_review_description);
            result->rating=task_rating;result->european=task_european;result->invincible=receive.architect_invincible;result->untargetable=receive.architect_untargetable;}
    }
    result->on_flashback=receive.onFlashback;result->parameter_update=parameter_update;
    if(parameter_update){
        result->parameter_mask=rt.parametersSet;
        for(unsigned i=0;i<32;i++)if(rt.parametersSet&(UINT32_C(1)<<i)){
            result->parameters[i]=rt.parameters[i];if(i==1||i==23)result->parameters[i]-=(U32)timerSecondsSince2000();
            assert(result->parameters[i]==(i==1||i==23?st.parameters[i]-(U32)timerSecondsSince2000():st.parameters[i]));
        }else assert(rt.parameters[i]==0x12345678u);
    }else assert(rt.parametersSet==0x80000000u);
    result->end_bit=*length;*expected_size=sizeof(*result);memcpy(expected,result,sizeof(*result));free(result);
}
#undef Entity
#undef pktGetString
#undef NPCcostume_receive
