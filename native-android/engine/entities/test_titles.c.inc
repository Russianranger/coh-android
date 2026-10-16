static void titles_bad(Fixture f,unsigned mode,CohStatus expected){
    CohRepReader r=reader(f,mode),oldr;memcpy(&oldr,&r,sizeof(r));CohEntTitles value,old;CohEntFailure d;
    memcpy(&value,title_seed_bytes,sizeof(value));memcpy(&old,&value,sizeof(value));
    /* Both current and stale malformed packets must fail, never bypass data. */
    for(unsigned packet=9;packet<=11;packet++){
        CohStatus status=coh_ent_titles(&r,packet,&value,&d);
        if(status!=expected)fprintf(stderr,"titles bad fixture bits=%zu mode=%u packet=%u got=%d expected=%d failurebit=%zu\n",f.bits,mode,packet,status,expected,d.bit);
        CHECK(status==expected);
        same_reader(&r,&oldr);CHECK(!memcmp(&value,&old,sizeof(value)));
        CHECK(d.stage==COH_ENT_STAGE_TITLES&&d.bit<=f.bits);
    }
}
static void titles_run_tests(void){
    CHECK(sizeof(CohEntTitles)==sizeof(title_seed_bytes));
    for(unsigned i=0;i<sizeof(title_fixtures)/sizeof(title_fixtures[0]);i++){
        const TitleFixture *f=&title_fixtures[i];Fixture input={f->data,f->bits};
        CohRepReader r=reader(input,f->mode);r.cursor=f->start;CohRepReader start;memcpy(&start,&r,sizeof(r));
        CohEntTitles value,seed;CohEntFailure d;memcpy(&seed,title_seed_bytes,sizeof(seed));
        for(unsigned packet=9;packet<=11;packet++){
            r=start;memcpy(&value,&seed,sizeof(value));CHECK(coh_ent_titles(&r,packet,&value,&d)==COH_OK);
            CHECK(r.cursor==f->bits);CHECK(!memcmp(&value,f->expected[packet-9],offsetof(CohEntTitles,special)+sizeof(value.special)));
            for(size_t n=f->start;n<f->bits;n++){
                r=start;r.bits=n;CohRepReader before;memcpy(&before,&r,sizeof(r));memcpy(&value,&seed,sizeof(value));truncations++;
                CHECK(coh_ent_titles(&r,packet,&value,&d)!=COH_OK);same_reader(&r,&before);
                CHECK(!memcmp(&value,&seed,sizeof(value)));CHECK(d.stage==COH_ENT_STAGE_TITLES&&d.bit<=n);
            }
        }
        /* An explicitly reset entity-generation state ignores old packet IDs. */
        if(f->scenario){
            r=start;memset(&value,0,sizeof(value));value.packet_id=UINT32_MAX;
            CHECK(coh_ent_titles(&r,1,&value,NULL)==COH_OK);CHECK(value.valid&&value.packet_id==1);
        }
        /* The title boundary does not consume a later source transaction. */
        unsigned char bytes[4096];CHECK((f->bits+7)/8<sizeof(bytes));memset(bytes,0xa5,sizeof(bytes));
        memcpy(bytes,f->data,(f->bits+7)/8);
        CHECK(coh_rep_reader(&r,(CohBytes){bytes,sizeof(bytes)},f->bits+8,(int)f->mode)==COH_OK);
        r.cursor=f->start;memcpy(&value,&seed,sizeof(value));CHECK(coh_ent_titles(&r,11,&value,NULL)==COH_OK);CHECK(r.cursor==f->bits);
        /* Deterministic byte mutations complement every-bit truncations. */
        for(size_t j=f->start/8;j<(f->bits+7)/8;j++){
            memcpy(bytes,f->data,(f->bits+7)/8);bytes[j]^=0xff;
            CHECK(coh_rep_reader(&r,(CohBytes){bytes,sizeof(bytes)},f->bits,(int)f->mode)==COH_OK);
            r.cursor=f->start;CohRepReader before;memcpy(&before,&r,sizeof(r));memcpy(&value,&seed,sizeof(value));
            CohStatus status=coh_ent_titles(&r,11,&value,&d);
            if(status!=COH_OK){same_reader(&r,&before);CHECK(!memcmp(&value,&seed,sizeof(value)));CHECK(d.bit<=f->bits);}
            else CHECK(r.cursor<=f->bits);
        }
        r=start;CohRepReader rejected;memcpy(&rejected,&r,sizeof(r));memcpy(&value,&seed,sizeof(value));CHECK(coh_ent_titles(&r,0,&value,NULL)==COH_INVALID);same_reader(&r,&rejected);CHECK(!memcmp(&value,&seed,sizeof(value)));
    }
    /* Source presence clears optional fields, absence retains the complete
     * prior value; an equal-ID packet applies, an older packet does not. */
    for(unsigned mode=0;mode<2;mode++){
        const TitleFixture *full=&title_fixtures[mode?49:1],*empty=&title_fixtures[mode?50:2],*absent=&title_fixtures[mode?48:0];
        CHECK(full->mode==mode&&full->scenario==1&&empty->scenario==2&&absent->scenario==0);
        CohEntTitles value={0};CohRepReader r=reader((Fixture){full->data,full->bits},mode);
        CHECK(coh_ent_titles(&r,20,&value,NULL)==COH_OK);CHECK(value.special[0]&&value.the_text[0]);
        r=reader((Fixture){empty->data,empty->bits},mode);CHECK(coh_ent_titles(&r,20,&value,NULL)==COH_OK);
        CHECK(!value.name[0]&&!value.special[0]&&!value.the_text[0]&&!value.common[0]&&!value.origin[0]);
        CohEntTitles cleared;memcpy(&cleared,&value,sizeof(value));
        r=reader((Fixture){full->data,full->bits},mode);CHECK(coh_ent_titles(&r,19,&value,NULL)==COH_OK);CHECK(!memcmp(&value,&cleared,sizeof(value)));
        r=reader((Fixture){absent->data,absent->bits},mode);CHECK(coh_ent_titles(&r,21,&value,NULL)==COH_OK);CHECK(!memcmp(&value,&cleared,sizeof(value)));
    }
#define BAD_TITLE_MODE(m) do{ \
    titles_bad(F(titles_long_name##m),m,COH_LIMIT);titles_bad(F(titles_long_the##m),m,COH_LIMIT); \
    titles_bad(F(titles_long_common##m),m,COH_LIMIT);titles_bad(F(titles_long_origin##m),m,COH_LIMIT); \
    titles_bad(F(titles_long_special##m),m,COH_LIMIT); \
}while(0)
    BAD_TITLE_MODE(0);BAD_TITLE_MODE(1);
    titles_bad(F(titles_bad_presence),1,COH_INVALID);titles_bad(F(titles_bad_optional),1,COH_INVALID);
    titles_bad(F(titles_bad_auto),1,COH_INVALID);titles_bad(F(titles_bad_late_flag),1,COH_INVALID);titles_bad(F(titles_bad_gender),1,COH_INVALID);
    CHECK(coh_ent_titles(NULL,1,NULL,NULL)==COH_INVALID);
}
