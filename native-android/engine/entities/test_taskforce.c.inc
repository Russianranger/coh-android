static CohEntTaskforceWorkspace task_workspace;
static CohEntTaskforce task_output,task_previous,task_expected;
static void taskforce(Fixture f,unsigned mode,const CostumeExpectedByte *pairs,size_t count,size_t expected_size,CohEntCostumeDictionary *d){
    CohRepReader r=reader(f,mode),start;memcpy(&start,&r,sizeof(r));CohEntFailure failure;
    CHECK(expected_size==sizeof(task_expected));memset(&task_expected,0,sizeof(task_expected));
    for(size_t i=0;i<count;i++){CHECK(pairs[i].offset<sizeof(task_expected));((unsigned char*)&task_expected)[pairs[i].offset]=pairs[i].value;}
    memset(&task_output,0xa5,sizeof(task_output));memcpy(&task_previous,&task_output,sizeof(task_output));
    CHECK(coh_ent_taskforce(&r,d,9,&task_workspace,&task_output,&failure)==COH_OK);CHECK(r.cursor==f.bits);
    CHECK(!memcmp(&task_output,&task_expected,offsetof(CohEntTaskforce,costume)));
    CHECK(!memcmp(&task_output.costume,&task_expected.costume,offsetof(CohEntCostume,parts)+sizeof(task_output.costume.parts)));
    CHECK(task_output.costume.end_bit==task_expected.costume.end_bit);
    CHECK(!memcmp(&task_output.custom,&task_expected.custom,offsetof(CohEntCustomCostume,parts)+sizeof(task_output.custom.parts)));
    CHECK(task_output.custom.end_bit==task_expected.custom.end_bit&&task_output.end_bit==f.bits);
    for(size_t n=0;n<f.bits;n++){
        r=start;r.bits=n;CohRepReader before;memcpy(&before,&r,sizeof(r));memcpy(&task_output,&task_previous,sizeof(task_output));truncations++;
        CHECK(coh_ent_taskforce(&r,d,9,&task_workspace,&task_output,&failure)!=COH_OK);
        CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&task_output,&task_previous,sizeof(task_output)));CHECK(failure.bit<=n);
    }
    r=start;memcpy(&task_output,&task_previous,sizeof(task_output));
    if(task_expected.costume_body){
        CohRepReader before;memcpy(&before,&r,sizeof(r));
        CHECK(coh_ent_taskforce(&r,d,8,&task_workspace,&task_output,&failure)==COH_STATE);
        CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&task_output,&task_previous,sizeof(task_output)));
        CHECK(coh_ent_taskforce(&r,NULL,9,&task_workspace,&task_output,&failure)==COH_INVALID&&failure.status==COH_INVALID);
        CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&task_output,&task_previous,sizeof(task_output)));
    }else CHECK(coh_ent_taskforce(&r,NULL,9,&task_workspace,&task_output,&failure)==COH_OK);
    /* Successful substructure syntax leaves the rest of the transaction. */
    unsigned char bytes[16384];CHECK((f.bits+7)/8<sizeof(bytes));memset(bytes,0xa5,sizeof(bytes));memcpy(bytes,f.data,(f.bits+7)/8);
    CHECK(coh_rep_reader(&r,(CohBytes){bytes,sizeof(bytes)},f.bits+8,(int)mode)==COH_OK);
    CHECK(coh_ent_taskforce(&r,d,9,&task_workspace,&task_output,&failure)==COH_OK&&r.cursor==f.bits);
    for(size_t i=0;i<(f.bits+7)/8;i++){
        memcpy(bytes,f.data,(f.bits+7)/8);bytes[i]^=0xff;
        CHECK(coh_rep_reader(&r,(CohBytes){bytes,sizeof(bytes)},f.bits,(int)mode)==COH_OK);
        CohRepReader before;memcpy(&before,&r,sizeof(r));memcpy(&task_output,&task_previous,sizeof(task_output));
        CohStatus s=coh_ent_taskforce(&r,d,9,&task_workspace,&task_output,&failure);
        if(s!=COH_OK){CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&task_output,&task_previous,sizeof(task_output)));CHECK(failure.bit<=f.bits);}
        else CHECK(r.cursor<=f.bits);
    }
}
static void taskforce_bad(Fixture f,unsigned mode,CohStatus expected_status,CohEntCostumeDictionary *d){
    CohRepReader r=reader(f,mode),before;memcpy(&before,&r,sizeof(r));CohEntFailure failure;
    memset(&task_output,0xa5,sizeof(task_output));memcpy(&task_previous,&task_output,sizeof(task_output));
    CohStatus s=coh_ent_taskforce(&r,d,9,&task_workspace,&task_output,&failure);
    if(s!=expected_status)fprintf(stderr,"taskforce bad bits=%zu got=%d expected=%d\n",f.bits,s,expected_status);
    CHECK(s==expected_status);CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&task_output,&task_previous,sizeof(task_output)));CHECK(failure.bit<=f.bits);
}
#define TASK(s,m,d) taskforce(F(costume_##s##_##m),m,costume_##s##_##m##_expected,sizeof(costume_##s##_##m##_expected)/sizeof(CostumeExpectedByte),costume_##s##_##m##_size,d)
#define TASK_MODE(m,d) do{ \
    TASK(22,m,d);TASK(23,m,d);TASK(24,m,d);TASK(25,m,d);TASK(26,m,d);TASK(27,m,d); \
    TASK(28,m,d);TASK(29,m,d);TASK(30,m,d);TASK(31,m,d);TASK(32,m,d); \
    taskforce_bad(F(task_bad_contact##m),m,COH_LIMIT,d);taskforce_bad(F(task_bad_name##m),m,COH_LIMIT,d); \
    taskforce_bad(F(task_bad_author##m),m,COH_LIMIT,d);taskforce_bad(F(task_bad_description##m),m,COH_LIMIT,d); \
    taskforce_bad(F(task_bad_flashback##m),m,COH_INVALID,d);taskforce_bad(F(task_bad_hole##m),m,COH_NOT_FOUND,d); \
}while(0)
static void taskforce_run_tests(CohEntCostumeDictionary *d){
    TASK_MODE(0,d);TASK_MODE(1,d);taskforce_bad(F(task_bad_flag),1,COH_INVALID,d);
    uint32_t seed=0x73198461;unsigned char data[1024];
    for(unsigned i=0;i<5000;i++){
        for(unsigned j=0;j<sizeof(data);j++){seed=seed*1664525u+1013904223u;data[j]=(unsigned char)(seed>>24);}
        CohRepReader r;size_t bits=seed%(sizeof(data)*8+1);CHECK(coh_rep_reader(&r,(CohBytes){data,sizeof(data)},bits,(int)(i%2))==COH_OK);
        CohRepReader before;memcpy(&before,&r,sizeof(r));memset(&task_output,0xa5,sizeof(task_output));memcpy(&task_previous,&task_output,sizeof(task_output));CohEntFailure failure;
        CohStatus s=coh_ent_taskforce(&r,d,9,&task_workspace,&task_output,&failure);randomized++;
        if(s!=COH_OK){CHECK(!memcmp(&r,&before,sizeof(r))&&!memcmp(&task_output,&task_previous,sizeof(task_output)));CHECK(failure.bit<=bits);}
        else CHECK(r.cursor<=bits);
    }
    CHECK(coh_ent_taskforce(NULL,d,9,&task_workspace,&task_output,NULL)==COH_INVALID);
}
