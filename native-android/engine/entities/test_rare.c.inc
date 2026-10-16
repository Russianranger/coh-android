static void rare_bad(Fixture f,unsigned mode,CohStatus expected){
    CohRepReader r=reader(f,mode),oldr;CohEntRarePrefix value,old;CohEntFailure d;
    memset(&value,0xa5,sizeof(value));memcpy(&old,&value,sizeof(value));memcpy(&oldr,&r,sizeof(r));
    CohStatus status=coh_ent_rare_prefix(&r,&value,&d);
    if(status!=expected)fprintf(stderr,"rare bad bits=%zu mode=%u got=%d expected=%d bit=%zu\n",f.bits,mode,status,expected,d.bit);
    CHECK(status==expected);same_reader(&r,&oldr);CHECK(!memcmp(&value,&old,sizeof(value)));
    CHECK(d.stage==COH_ENT_STAGE_RARE_PREFIX&&d.bit<=f.bits);
}
static void rare_run_tests(void){
    for(unsigned i=0;i<sizeof(rare_fixtures)/sizeof(rare_fixtures[0]);i++){
        const RareFixture *f=&rare_fixtures[i];CohRepReader r=reader((Fixture){f->data,f->bits},f->mode);r.cursor=f->start;
        CohRepReader initial;memcpy(&initial,&r,sizeof(r));CohEntRarePrefix v,old,expected;CohEntFailure d;
        memcpy(&expected,f->expected,sizeof(expected));memset(&v,0xa5,sizeof(v));memcpy(&old,&v,sizeof(v));
        CHECK(coh_ent_rare_prefix(&r,&v,&d)==COH_OK);CHECK(r.cursor==f->bits&&v.end_bit==f->bits);
        CHECK(!memcmp(&v,&expected,offsetof(CohEntRarePrefix,afk_message)+sizeof(v.afk_message)));CHECK(v.end_bit==expected.end_bit);
        for(size_t n=f->start;n<f->bits;n++){
            r=initial;r.bits=n;CohRepReader prior;memcpy(&prior,&r,sizeof(r));memcpy(&v,&old,sizeof(v));truncations++;
            CHECK(coh_ent_rare_prefix(&r,&v,&d)!=COH_OK);same_reader(&r,&prior);CHECK(!memcmp(&v,&old,sizeof(v)));
            CHECK(d.stage==COH_ENT_STAGE_RARE_PREFIX&&d.bit<=n);
        }
        unsigned char bytes[4096];CHECK((f->bits+7)/8<sizeof(bytes));memset(bytes,0xa5,sizeof(bytes));memcpy(bytes,f->data,(f->bits+7)/8);
        CHECK(coh_rep_reader(&r,(CohBytes){bytes,sizeof(bytes)},f->bits+8,(int)f->mode)==COH_OK);r.cursor=f->start;
        CHECK(coh_ent_rare_prefix(&r,&v,NULL)==COH_OK);CHECK(r.cursor==f->bits); /* later supergroup bytes untouched */
        for(size_t j=f->start/8;j<(f->bits+7)/8;j++){
            memcpy(bytes,f->data,(f->bits+7)/8);bytes[j]^=0xff;
            CHECK(coh_rep_reader(&r,(CohBytes){bytes,sizeof(bytes)},f->bits,(int)f->mode)==COH_OK);r.cursor=f->start;
            CohRepReader prior;memcpy(&prior,&r,sizeof(r));memcpy(&v,&old,sizeof(v));CohStatus status=coh_ent_rare_prefix(&r,&v,&d);
            if(status!=COH_OK){same_reader(&r,&prior);CHECK(!memcmp(&v,&old,sizeof(v)));CHECK(d.bit<=f->bits);}else CHECK(r.cursor<=f->bits);
        }
    }
#define RARE_BAD_MODE(m) do{ \
    rare_bad(F(rare_bad_ignore##m),m,COH_INVALID); \
    rare_bad(F(rare_bad_owner_zero##m),m,COH_LIMIT);rare_bad(F(rare_bad_owner_limit##m),m,COH_LIMIT);rare_bad(F(rare_bad_creator_limit##m),m,COH_LIMIT); \
    rare_bad(F(rare_long_name##m),m,COH_LIMIT);rare_bad(F(rare_long_display##m),m,COH_LIMIT);rare_bad(F(rare_long_pet##m),m,COH_LIMIT);rare_bad(F(rare_long_afk##m),m,COH_LIMIT); \
}while(0)
    RARE_BAD_MODE(0);RARE_BAD_MODE(1);
    rare_bad(F(rare_bad_player_bits),1,COH_INVALID);rare_bad(F(rare_bad_presence),1,COH_INVALID);rare_bad(F(rare_bad_afk),1,COH_INVALID);rare_bad(F(rare_bad_auto),1,COH_INVALID);
    /* Raw CRC wire staging accepts no synthetic dictionary authority. */
    for(unsigned mode=0;mode<2;mode++){
        Fixture f=mode?F(rare_unknown_crc1):F(rare_unknown_crc0);CohRepReader r=reader(f,mode);CohEntRarePrefix v;
        CHECK(coh_ent_rare_prefix(&r,&v,NULL)==COH_OK);CHECK(r.cursor==f.bits&&v.power_present&&v.power_crc==0x12345678u);
    }
    for(unsigned i=0;i<5000;i++){
        unsigned char bytes[384];for(unsigned j=0;j<sizeof(bytes);j++)bytes[j]=(unsigned char)rand32();
        unsigned mode=rand32()&1;size_t bits=rand32()%(sizeof(bytes)*8+1);CohRepReader r;
        CHECK(coh_rep_reader(&r,(CohBytes){bytes,sizeof(bytes)},bits,(int)mode)==COH_OK);CohRepReader prior;memcpy(&prior,&r,sizeof(r));
        CohEntRarePrefix v,old;memset(&v,0x5a,sizeof(v));memcpy(&old,&v,sizeof(v));CohEntFailure d;randomized++;
        CohStatus status=coh_ent_rare_prefix(&r,&v,&d);
        if(status!=COH_OK){same_reader(&r,&prior);CHECK(!memcmp(&v,&old,sizeof(v)));CHECK(d.bit<=bits);}else CHECK(r.cursor<=bits);
    }
    CHECK(coh_ent_rare_prefix(NULL,NULL,NULL)==COH_INVALID);
    CohEntRarePrefix v;CohRepReader invalid={0};invalid.cursor=1;
    CHECK(coh_ent_rare_prefix(&invalid,&v,NULL)==COH_INVALID);
}
