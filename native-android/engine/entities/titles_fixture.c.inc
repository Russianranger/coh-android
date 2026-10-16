/* Calls the unchanged source title statement block and complete consumer.
 * This is not execution of complete sendEntity, a record, or an ALLENTS tail. */
unsigned original_titles_size(void){return sizeof(CohEntTitles);}
void original_titles_seed(CohEntTitles *out){TitleEntity e;TitlePlayer p;title_seed(&e,&p);title_export(&e,10,out);}
void original_titles(int scenario,int aligned,int offset,U8 *out,U32 *length,U32 *start){
    U32 storage[8192]={0};Packet p={0};TitleEntity e={0};TitlePlayer pl={0};e.pl=&pl;
    initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
    if(offset)pktSendBits(&p,offset,0);*start=bsGetCursorBitPosition(&p.stream);
    db_state.is_endgame_raid=scenario==4;
    if(scenario==0)e.pl=NULL;
    if(scenario==1||scenario==4||scenario==5){
        strcpy(e.name,"SourceTitlePlayer");strcpy(pl.titleTheText,"The");strcpy(pl.titleCommon,"Brave");
        strcpy(pl.titleOrigin,"Natural");strcpy(pl.titleSpecial,"SourceFixture");
        pl.titleThe=33;pl.titleColors[0]=0x12345678;pl.titleColors[1]=0xabcdef01;
        pl.titleBadge=0x98765432;pl.glowieUnlocked=1;e.gender=3;e.name_gender=2;pl.attachArticle=1;
        pl.respecTokens=0xdeadbeef;pl.lastTurnstileEventID=4242;pl.lastTurnstileMissionID=911;pl.helperStatus=1024;
    }
    if(scenario==3){
        memset(e.name,'n',sizeof(e.name)-1);memset(pl.titleTheText,'t',sizeof(pl.titleTheText)-1);
        memset(pl.titleCommon,'c',sizeof(pl.titleCommon)-1);memset(pl.titleOrigin,'o',sizeof(pl.titleOrigin)-1);
        memset(pl.titleSpecial,'s',sizeof(pl.titleSpecial)-1);
        pl.titleThe=-1;pl.titleColors[0]=3;pl.titleColors[1]=1023;pl.helperStatus=-1;
    }
    if(scenario==5){pl.titleTheText[0]=0;pl.titleOrigin[0]=0;pl.titleColors[0]=0xffffff;pl.helperStatus=3;}
    original_titles_statement(&p,&e);*length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_receive_titles(const U8 *data,U32 bits,int aligned,U32 start,U32 packet_id,CohEntTitles *out){
    U32 storage[8192]={0};Packet p={0};TitleEntity e;TitlePlayer pl;title_seed(&e,&pl);
    initBitStream(&p.stream,(U8*)storage,sizeof(storage),Read,aligned,0);memcpy(storage,data,(bits+7)/8);
    p.stream.bitLength=bits;p.stream.cursor.byte=start/8;p.stream.cursor.bit=start%8;p.id=packet_id;
    int received=entReceiveTitles(&p,&e,packet_id<10);
    assert(bsGetCursorBitPosition(&p.stream)==bits);assert(!p.stream.errorFlags);
    title_export(&e,received&&packet_id>=10?packet_id:10,out);
}
