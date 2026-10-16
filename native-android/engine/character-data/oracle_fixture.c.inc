typedef struct{
 Character ch;Entity entity;Named class_name,origin_name;Boost boost;Power power;
 PowerSet sets[2];BasePowerSet base;const BasePower*roots[1];ConceptDef concept_defs[2];ConceptItem concepts[2];ConceptInventory concepts_inv[2];
 FixtureArray builds[8],powers,regular_boosts,global_boosts,concept_array;
}FixtureOwner;
static FixtureOwner owner;
static void setup(int scenario){
 memset(&owner,0,sizeof(owner));memset(&observed,0,sizeof(observed));
 for(unsigned i=0;i<8;i++)powers_by_crc[i].crcFullName=0x12340000u+i+1;
 Character*c=&owner.ch;owner.class_name.pchName="Fixture_Class";owner.origin_name.pchName="Fixture_Origin";
 c->pclass=&owner.class_name;c->porigin=&owner.origin_name;c->entParent=&owner.entity;owner.entity.pchar=c;owner.entity.type=scenario?2:1;
 c->iLevel=17;c->iCombatModShiftToSendToClient=0xffffffffu;c->iCurBuild=scenario?3:0;c->iActiveBuild=scenario?2:0;c->playerTypeByLocation=1;
 g_numSharedPowersets=scenario==5?3:(scenario==2?0:(scenario==3?2:1));
 owner.roots[0]=&powers_by_crc[0];owner.base.ppPowers=owner.roots;
 owner.boost.ppowBase=&powers_by_crc[1];owner.boost.iLevel=9;owner.boost.iNumCombines=3;
 for(unsigned i=0;i<4;i++)owner.boost.afVars[i]=(float)i*0.25f;
 for(unsigned i=0;i<(scenario==2?10u:2u);i++){owner.boost.aPowerupSlots[i].reward.type=(int)i;owner.boost.aPowerupSlots[i].reward.name="37";owner.boost.aPowerupSlots[i].filled=i&1;}
 owner.regular_boosts.count=2;owner.regular_boosts.items[0]=&owner.boost;owner.regular_boosts.items[1]=NULL;
 owner.global_boosts.count=1;owner.global_boosts.items[0]=&owner.boost;
 Power*p=&owner.power;p->ppowOriginal=&powers_by_crc[2];p->iLevelBought=7;p->iNumCharges=31;p->fRangeLast=13.5f;p->fUsageTime=0.5f;p->fAvailableTime=2.5f;
 p->ulCreationTime=0xfedcba98u;p->bEnabled=1;p->bDisabledManually=0;p->iUniqueID=70001;
 p->ppBoosts=(Boost**)owner.regular_boosts.items;p->ppGlobalBoosts=(Boost**)owner.global_boosts.items;
 owner.powers.count=scenario==3?0:2;owner.powers.items[0]=NULL;owner.powers.items[1]=p;
 for(unsigned i=0;i<2;i++){owner.sets[i].iLevelBought=5+(int)i;owner.sets[i].ppPowers=(Power**)owner.powers.items;owner.sets[i].psetBase=&owner.base;}
 for(unsigned i=0;i<8;i++){c->iBuildLevels[i]=(int)(i+10);owner.builds[i].count=2;owner.builds[i].items[0]=&owner.sets[0];owner.builds[i].items[1]=&owner.sets[1];c->ppBuildPowerSets[i]=(PowerSet**)owner.builds[i].items;}
 c->ppPowerSets=c->ppBuildPowerSets[c->iCurBuild];c->iNumInspirationCols=5;c->iNumInspirationRows=4;
 for(unsigned x=0;x<5;x++)for(unsigned y=0;y<4;y++)if((x+y)&1)c->aInspirations[x][y]=&powers_by_crc[3];
 c->aBoosts[0]=&owner.boost;c->aBoosts[69]=&owner.boost;
 c->auctionInvTotalSlots=73;
 for(unsigned t=0;t<5;t++){c->inventory_size[t]=2;c->inventory_total[t]=100+(int)t;for(unsigned i=0;i<2;i++){c->inventory[t][i].id=1+t*100+i;c->inventory[t][i].amount=i?3:0;}}
 owner.concept_array.count=2;
 for(unsigned i=0;i<2;i++){owner.concept_defs[i].id=(int)c->inventory[1][i].id;owner.concepts[i].def=&owner.concept_defs[i];for(unsigned k=0;k<4;k++)owner.concepts[i].afVars[k]=(float)(i+k)*0.5f;owner.concepts_inv[i].concept=&owner.concepts[i];owner.concept_array.items[i]=&owner.concepts_inv[i];}
 c->conceptInv=(ConceptInventory**)owner.concept_array.items;
 if(scenario==4){memset(c->aInspirations,0,sizeof(c->aInspirations));memset(c->aBoosts,0,sizeof(c->aBoosts));for(unsigned t=0;t<5;t++)c->inventory_size[t]=0;}
}
void original_send(int scenario,int mode,int prefix,U8*out,U32*bits){
 U32 storage[16384]={0};Packet p={0};setup(scenario);initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,mode,0);if(prefix)bsWriteBits(&p.stream,prefix,0);
 character_Send(&p,&owner.ch);*bits=p.stream.bitLength;memcpy(out,storage,(*bits+7)/8);
}
/* Independent original subconsumer execution; power dictionary resolution is
 * a synthetic fixture shell, never an imported or authenticated dictionary. */
typedef struct{U32 columns,rows,inspirations[5][4];CohCharacterBoost boosts[70];CohCharacterInventory inventories[5];CohCharacterInventoryItem items[10];U32 inventory_count,auction_slots;}SubExpected;
void original_subconsumers(int scenario,int mode,SubExpected*out){
 U32 storage[16384]={0};Packet p={0};setup(scenario);
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,mode,0);
 character_SendInspirations(&p,&owner.ch);character_SendBoosts(&p,&owner.ch);character_SendInventories(&owner.ch,&p);
 U32 bits=p.stream.bitLength,initial=storage[0];initBitStream(&p.stream,(U8*)storage,sizeof(storage),Read,mode,0);storage[0]=initial;p.stream.bitLength=bits;
 character_ReceiveInspirations(&p,&owner.ch);character_ReceiveBoosts(&p,&owner.ch);character_ReceiveInventories(&owner.ch,&p);
 assert(bsGetCursorBitPosition(&p.stream)==bits);observed.inspiration_columns=(U32)owner.ch.iNumInspirationCols;observed.inspiration_rows=(U32)owner.ch.iNumInspirationRows;
 observed.auction_slots=(U32)owner.ch.auctionInvTotalSlots;
 memset(out,0,sizeof(*out));out->columns=observed.inspiration_columns;out->rows=observed.inspiration_rows;
 memcpy(out->inspirations,observed.inspirations,sizeof(out->inspirations));memcpy(out->boosts,observed.boosts,sizeof(out->boosts));
 memcpy(out->inventories,observed.inventories,sizeof(out->inventories));memcpy(out->items,observed.items,sizeof(out->items));
 out->inventory_count=observed.inventory_count;out->auction_slots=observed.auction_slots;
}
unsigned original_data_size(void){return sizeof(CohCharacterData);}
unsigned original_subconsumer_size(void){return sizeof(SubExpected);}
