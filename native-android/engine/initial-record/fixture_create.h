/* Synthetic fixture objects/identities, whole original entSendCreate executes.
 * Type/generation/DBID changes are explicit fixture setup, never wire patches. */
void initial_create_fixture(unsigned type,unsigned self,unsigned pet,unsigned entity_id,unsigned dbid,unsigned aligned,unsigned prefix,U8*out,U32*length,U32*begin){
 U32 storage[8192]={0};Packet p={0};Entity e={0},owner={0},creator={0};BasePower power={0xa1b2c3d4};Character ch={3,1,1,NULL};Player pl={0};
 Villain v={"fixture.def","FixtureCritter","FixtureOverride"};
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);if(prefix)pktSendBits(&p,prefix,0);*begin=bsGetCursorBitPosition(&p.stream);
 e.type=type;e.id=entity_id;e.db_id=dbid;e.name="FixtureName";e.randSeed=0x12345678;e.fade=1;e.pchar=&ch;e.pl=type==2?&pl:NULL;
 pl.titleThe=3;pl.titleTheText="The";pl.titleCommon="Brave";pl.titleOrigin="Natural";pl.titleColors[0]=0x10203040;pl.titleColors[1]=0x50607080;pl.titleBadge=77;pl.titleSpecial="Synthetic";pl.chat_handle="Fixture";pl.playerSubType=2;pl.praetorianProgress=3;
 if(type==4){e.villainDef=&v;e.villainRank=3;e.idDetail=7;e.favoriteWeaponAnimList="FixtureAnim";server_state.clickToSource=1;}
 if(pet){owner.owner=12;creator.owner=13;e.erOwner=&owner;e.erCreator=&creator;e.commandablePet=1;e.petDismissable=1;e.petName="FixturePet";e.specialPowerDisplayName="FixturePower";e.specialPowerState=4;ch.ppowCreatedMe=&power;}
 entSendCreate(&p,&e,self?&e:NULL,1);*length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
