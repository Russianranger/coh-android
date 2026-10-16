#!/usr/bin/env python3
"""Run exact original component producers and consumer, then native tests.
The historical writer executes only trusted padded input at -O0; sanitizers
cover new code and test harness. No source fixture is evidence of live traffic.
List fixtures compose original component calls in a synthetic fixture shim;
they do not execute the original sendEntity or complete entSendUpdate path.
"""
from pathlib import Path
import argparse, ctypes as C, hashlib, importlib.util, json, os, re, shutil, struct, subprocess, tempfile
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
FILES=['MapServer/src/entity/entsend.c','Game/src/entity/entrecv.c',
       'Common/entity/entity_enum.h','Common/entity/entVarUpdate.h','Common/entity/entity.h','Common/entity/ragdoll.h',
       'libs/UtilitiesLib/src/components/BitStream.c','libs/UtilitiesLib/src/network/netcomp.c',
       'libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/utils/Quat.c',
       'libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h','Common/entity/gametypes.h','MapServer/src/entity/entserver.c','MapServer/src/entity/entsend.h','Common/entity/character_net.c','Common/entity/character_inventory.h','Common/comm_game.h','libs/UtilitiesLib/src/utils/structNet.c','Game/src/entity/character_net_client.c','Common/entity/attrib_net.c','libs/UtilitiesLib/src/utils/textparser.c','libs/UtilitiesLib/include/utilitieslib/utils/textparser.h','Common/entity/netfx.h','Common/entity/costume.c','Common/entity/costume.h','Common/entity/entPlayer.h','Common/gameData/costume_data.c','Common/gameData/BodyPart.c','libs/UtilitiesLib/src/utils/mathutil.c','Common/entity/power_customization.c','Common/entity/power_customization.h','Common/entity/teamCommon.h','Common/entity/TaskforceParams.c']
def run(cmd,**kw):
    p=subprocess.run([str(c) for c in cmd],text=True,capture_output=True,**kw)
    if p.returncode:raise RuntimeError(repr(cmd)+'\n'+p.stdout+p.stderr)
    return p

def source_text(repo,name):
    path=repo/'upstream/ouroboros'/name
    return (path.read_text() if path.exists() else run(['git','show','HEAD:upstream/ouroboros/'+name],cwd=repo).stdout).replace('\r\n','\n')

def extract(text,name):
    m=re.search(r'^(?:static\s+)?(?:unsigned\s+int|void|int|U32|F32|float|bool|const\s+BasePower\s*\*)\s*(?:INLINEDBG\s+)?'+name+r'\s*\([^;{}]*\)\s*\{',text,re.M)
    if not m:raise ValueError('Missing original function '+name)
    start=text.index('{',m.start());at=start+1;depth=1
    while depth:
        depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[m.start():at]+'\n'

def oracle(repo,directory):
    spec=importlib.util.spec_from_file_location('source_bit_adapter',repo/'native-android/tools/protocol_fixture/prepare.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    source={f:source_text(repo,f) for f in FILES}
    pins={f:hashlib.sha256(s.encode()).hexdigest() for f,s in source.items()}
    if pins!=json.loads((HERE/'source-pins.json').read_text())['sha256_lf']:raise ValueError('Entity source pin mismatch')
    pre=helper.PREAMBLE.replace('hasDebugInfo,compress,ordered,ordered_id;', 'hasDebugInfo,compress,ordered,ordered_id,id;')
    pre=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',pre)
    bit=source[FILES[6]];util=source[FILES[8]];send=source[FILES[0]];recv=source[FILES[1]]
    names=[]
    def get(text,name):names.append(name);return extract(text,name)
    code=pre+'\n'+''.join(get(bit,n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString'])
    code+='''
static void pktSendBits(Packet *p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet *p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet *p,int n){return bsReadBits(&p->stream,n);}
static U32 pktGetBitsPack(Packet *p,int n){return bsReadBitsPack(&p->stream,n);}
static void pktSendF32(Packet *p,float f){U32 u;memcpy(&u,&f,4);pktSendBits(p,32,u);}
static float pktGetF32(Packet *p){U32 u=pktGetBits(p,32);float f;memcpy(&f,&u,4);return f;}
static void pktSendString(Packet *p,const char *s){bsWriteString(&p->stream,s?s:"");}
static int auto_bins[]={2,10,24,32};
'''
    code+=''.join(get(util,n) for n in ['pktSendIfSetBitsPack','pktSendIfSetBits','pktGetIfSetBits','pktSendIfSetString','pktSendBitsAuto'])
    code+='typedef float F32;typedef float Vec3[3];typedef struct {struct {U32 integer;} primary,secondary;} ColorPair;\n'
    fxheader=source['Common/entity/netfx.h'];code+=fxheader[fxheader.index('//2 bits'):fxheader.index('/*Header info')]
    code+=(HERE/'oracle_shim.h').read_text()
    code+=''.join(get(util,n) for n in ['pktSendIfSetF32','pktGetIfSetF32','pktGetIfSetBitsPack'])
    code+=get(source['Common/entity/character_net.c'],'basepower_Send')
    code+=get(source['Common/entity/character_net.c'],'character_SendInventorySizes')
    code+=''.join(get(send,n) for n in ['entSendPetInfo','entSendCreate','entSendPosUpdate','entSendQrotUpdate','entSendModes','entSendSeqTriggeredMoves','entSendAiAnimList','entSendDeletes','entSendCostume','entSendTargetUpdate','entSendNetFx'])
    code+=get(source[FILES[7]],'unpackQuatElem')
    code+=''.join(get(source[FILES[9]],n) for n in ['quatCalcWFromXYZ','quatNormalize'])
    code+=get(recv,'entGetOrientation')
    code+=get(recv,'entReceiveNetFx')
    code+=(HERE/'stats_oracle_shim.h').read_text()
    structnet=source['libs/UtilitiesLib/src/utils/structNet.c']
    code+=structnet[structnet.index('typedef struct FloatAccuracyTable'):structnet.index('float ParserUnpackFloat')]
    code+=''.join(get(structnet,n) for n in ['ParserUnpackFloat','ParserPackFloat','ParserFloatMinBits'])
    code+=''.join(get(source['libs/UtilitiesLib/src/utils/textparser.c'],n) for n in ['int_senddiff','float_senddiff','struct_senddiff','int_recvdiff','float_recvdiff','struct_recvdiff'])
    code+=''.join(get(structnet,n) for n in ['sdPackStruct','ParserSend','sdUnpackStruct','ParserRecv'])
    schema=source['Common/entity/attrib_net.c']
    code+='\n#define Character StatsCharacter\n'+schema[schema.index('TokenizerParseInfo ParseBasicCharacterAttributesLowRes'):schema.index('/* End of File */')]+'\n#undef Character\n'
    code+='''
void original_receive_stats(const U8 *data,U32 bits,int aligned,int self,float *values,int *integers){
 U32 storage[8192]={0};Packet p={0};StatsCharacter c={0};
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Read,aligned,0);memcpy(storage,data,(bits+7)/8);p.stream.bitLength=bits;p.id=10;
 stats_ops[1].recvdiff=int_recvdiff;stats_ops[2].recvdiff=float_recvdiff;stats_ops[3].recvdiff=struct_recvdiff;
 assert(ParserRecv(self?SendCharacterToSelf:SendBasicCharacter,&p,&c,NULL,true));assert(bsGetCursorBitPosition(&p.stream)==bits);
 memcpy(values,&c.attrCur,sizeof(c.attrCur));memcpy(values+8,&c.attrMax,sizeof(c.attrMax));memcpy(integers,&c.iLevel,6*sizeof(int));
}
void original_stats(int self,int aligned,U8 *out,U32 *length,float *expected){
 U32 storage[8192]={0};Packet p={0};StatsCharacter c={0};
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 stats_ops[1]=(StatsOps){fixture_compare,int_senddiff};stats_ops[2]=(StatsOps){fixture_compare,float_senddiff};stats_ops[3]=(StatsOps){fixture_compare,struct_senddiff};
 c.attrCur=(CharacterAttributes){123.45f,45.5f,91.2f,.753f,300.f,8.75f,-3.3f,.656f};
 c.attrMax=(CharacterAttributes){200.25f,55.5f,100.f,.853f,400.f,9.75f,2.4f,.757f};
 c.iLevel=12;c.iCombatLevel=14;c.iExperiencePoints=123456;c.iExperienceDebt=-123;c.iExperienceRest=1000;c.iInfluencePoints=7654321;
 ParserSend(self?SendCharacterToSelf:SendBasicCharacter,&p,&c,&c,true,false,true,0,0);
 expected[0]=ParserUnpackFloat(ParserPackFloat(c.attrCur.fHitPoints,self?FLOAT_TENTHS:FLOAT_ONES),self?FLOAT_TENTHS:FLOAT_ONES);
 expected[1]=ParserUnpackFloat(ParserPackFloat(c.attrCur.fEndurance,self?FLOAT_TENTHS:FLOAT_FIVES),self?FLOAT_TENTHS:FLOAT_FIVES);
 expected[2]=ParserUnpackFloat(ParserPackFloat(c.attrCur.fStealthRadiusPlayer,FLOAT_ONES),FLOAT_ONES);
 expected[3]=ParserUnpackFloat(ParserPackFloat(c.attrCur.fConfused,FLOAT_TENTHS),FLOAT_TENTHS);
 expected[4]=ParserUnpackFloat(ParserPackFloat(c.attrCur.fToHit,FLOAT_HUNDRETHS),FLOAT_HUNDRETHS);
 *length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
'''

    code+='''
void original_fields(const int *widths,const U32 *values,U32 count,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};BitStream s;initBitStream(&s,(U8*)storage,sizeof(storage),Write,aligned,0);
 for(U32 i=0;i<count;i++){if(widths[i]<0)bsWriteBitsPack(&s,-widths[i],values[i]);else bsWriteBits(&s,widths[i],values[i]);}
 *length=s.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_create(int scenario,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};Packet p={0};Entity e={0},owner={0},creator={0};
 BasePower power={0xa1b2c3d4};Character ch={3,1,1,NULL};Player pl={0};Villain v={"fixture.def","FixtureCritter","FixtureOverride"};
 PNPCDef pn={"FixturePNPC"};PNPCInfo pi={&pn,1025};
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 e.type=scenario==0||scenario==1||scenario>=6?2:(scenario==2||scenario==3||scenario==4?4:1);
 e.id=scenario==6?70001:91;e.db_id=scenario==6?4243:4242;e.access_level=0;e.name="FixtureName";e.randSeed=0x12345678;e.fade=1;
 e.pchar=&ch;e.pl=e.type==2?&pl:NULL;
 pl.titleThe=3;pl.titleTheText="The";pl.titleCommon="Brave";pl.titleOrigin="Natural";
 pl.titleColors[0]=0x10203040;pl.titleColors[1]=0x50607080;pl.titleBadge=77;
 pl.titleSpecial="Synthetic";pl.chat_handle="Fixture";pl.playerSubType=2;pl.praetorianProgress=3;
 if(scenario==1)pl.isBeingCritter=1;
 if(scenario==2||scenario==3||scenario==4){e.villainDef=&v;e.villainRank=3;e.idDetail=7;e.favoriteWeaponAnimList="FixtureAnim";server_state.clickToSource=1;}
 if(scenario==3||scenario==4){owner.owner=12;creator.owner=13;e.erOwner=&owner;e.erCreator=&creator;e.commandablePet=1;e.petDismissable=1;e.petName="FixturePet";e.specialPowerDisplayName="FixturePower";e.specialPowerState=4;}
 if(scenario==4)ch.ppowCreatedMe=&power;
 if(scenario==5){e.persistentNPCInfo=&pi;e.name=NULL;}
 pktSendBits(&p,1,1);entSendCreate(&p,&e,scenario==0||scenario==1?&e:NULL,1);
 *length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
/* Fixture composition only: component functions above remain unchanged. The
 * pchar/appearance body flags below are normally suppressed, including
 * for self fixtures; the dedicated NPC stat fixture enables only supported
 * pchar fields. These bytes are not a complete real-player update. */
static void original_netfx_fields(Packet *p,int scenario);
static int fixture_record_stats;
static void original_record_fields(Packet *p,Entity *e,Entity *self,int medium){
 pktSendBits(p,1,1);entSendCreate(p,e,self,1);
 pktSendBits(p,1,medium);if(medium){pktSendBits(p,1,1);pktSendBits(p,1,0);entSendModes(p,e,1);}
 entSendPosUpdate(p,e,7,1,0);entSendQrotUpdate(p,e,7);
 if(medium){
  pktSendBits(p,1,1);pktSendIfSetBitsPack(p,8,33);pktSendIfSetBitsPack(p,4,4);pktSendIfSetBits(p,11,3);
  entSendSeqTriggeredMoves(p,e);entSendAiAnimList(p,e,1);
 }
 pktSendBits(p,1,fixture_record_stats!=0);pktSendBits(p,1,fixture_record_stats==2);
 if(fixture_record_stats==2)original_netfx_fields(p,0);
 if(medium){pktSendIfSetBitsPack(p,2,0);pktSendIfSetBits(p,8,20);}
 pktSendIfSetBits(p,5,medium);if(medium)for(int i=0;i<3;i++)pktSendBits(p,10,256);
 if(fixture_record_stats){
  StatsCharacter c={0};c.attrCur.fHitPoints=123.45f;c.attrCur.fEndurance=91.2f;c.iLevel=12;c.iCombatLevel=14;
  pktSendBits(p,1,1);pktSendBits(p,1,1);ParserSend(SendBasicCharacter,p,&c,&c,true,false,true,0,0);
 }
 pktSendBitsAuto(p,1);pktSendBitsAuto(p,0);pktSendBitsAuto(p,0);
 if(fixture_record_stats){pktSendBitsAuto(p,8);pktSendBits(p,1,0);pktSendBits(p,1,0);}
 pktSendBits(p,1,0);
}
static void original_record_entity(Entity *e,U32 id){
 e->type=1;e->id=id;e->name="FixtureNPC";e->randSeed=123;
 e->net_ipos[0]=(1<<23)+800;e->net_ipos[1]=(1<<23)-400;e->net_ipos[2]=(1<<23)+8192;
 e->net_iqrot[0]=e->net_iqrot[2]=256;e->net_iqrot[1]=384;e->state.mode=1;
 e->triggered_move_count=1;e->triggered_moves[0]=(TriggeredMove){42,6,1000,0};e->aiAnimList="FixtureAnim";
}
void original_record(int medium,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};Packet p={0};Entity e={0};
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 original_record_entity(&e,91);fixture_record_stats=medium>=2?medium-1:0;original_record_fields(&p,&e,NULL,medium==1);fixture_record_stats=0;
 *length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_list(int scenario,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};Packet p={0};int indices[3]={4,7,0},count=2,last=-1;
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 if(scenario==1){indices[0]=7;indices[1]=4;indices[2]=9;count=3;}
 if(scenario==2){indices[0]=10239;count=1;}
 for(int i=0;i<count;i++){
  Entity e={0};Character ch={3,1,1,NULL};Player pl={0};
  original_record_entity(&e,91+i);e.owner=indices[i];
  int self=scenario==4||(scenario==3&&i==0);
  if(self){e.type=2;e.db_id=4242;e.pchar=&ch;e.pl=&pl;e.name="FixturePlayer";}
  /* Same signed expression and U32 writer conversion as sendEntity. The
   * descending scenario intentionally exercises its modular wire value. */
  pktSendBitsPack(&p,1,indices[i]-last-1);last=indices[i];
  original_record_fields(&p,&e,self?&e:NULL,0);
 }
 pktSendBitsPack(&p,1,0);pktSendBits(&p,1,1);pktSendBits(&p,1,1);
 *length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
static void original_netfx_fields(Packet *p,int scenario){
 NetFx fx[4]={{0}};Entity e={0};e.netfx_list=fx;e.netfx_count=scenario==2?0:4;e.netfx_effective=2;e.lastTimeEntSent=1;
 for(int i=0;i<4;i++){
  fx[i].command=(i%3)+1;fx[i].net_id=100+i;fx[i].commandStatus=i==3?NEW_FX_COMMAND:(i==0?OLD_FX_COMMAND:NEW_FX_COMMAND_TO_SEND);
  fx[i].originType=i%2;fx[i].targetType=1-i%2;fx[i].originEnt=4;fx[i].targetEnt=7;fx[i].bone_id=12;
  fx[i].originPos[0]=1.25f;fx[i].originPos[1]=-2.5f;fx[i].originPos[2]=3.75f;
  fx[i].targetPos[0]=4.25f;fx[i].targetPos[1]=-5.5f;fx[i].targetPos[2]=6.75f;
 }
 fx[0].pitchToTarget=1;fx[0].powerTypeflags=15;fx[0].handle=12345;fx[0].hasColorTint=1;
 fx[0].colorTint.primary.integer=0x11223344;fx[0].colorTint.secondary.integer=0x55667788;
 fx[0].clientTimer=2;fx[0].timeCalled=5;fx[0].duration=1.5f;fx[0].radius=12.25f;fx[0].power=9;fx[0].debris=0xdeadbeef;
 fx[1].clientTimer=2;fx[1].clientTriggerFx=123;fx[1].duration=-1;fx[1].radius=0;
 entSendNetFx(p,&e,scenario!=1,&e);
}
void original_netfx(int scenario,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};Packet p={0};initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 original_netfx_fields(&p,scenario);*length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_receive_netfx(const U8 *data,U32 bits,int aligned,U32 *values,float *positions){
 U32 storage[8192]={0};Packet p={0};NetFx fx[32]={{0}};Entity e={0};e.netfx_list=fx;
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Read,aligned,0);memcpy(storage,data,(bits+7)/8);p.stream.bitLength=bits;
 entReceiveNetFx(&p,&e);assert(bsGetCursorBitPosition(&p.stream)==bits);values[0]=e.netfx_count;
 for(int i=0;i<e.netfx_count;i++){
  U32 fields[]={fx[i].command,fx[i].net_id,fx[i].pitchToTarget,fx[i].powerTypeflags,fx[i].handle,fx[i].hasColorTint,fx[i].colorTint.primary.integer,fx[i].colorTint.secondary.integer,(U32)fx[i].clientTimer,fx[i].clientTriggerFx,fx[i].power,fx[i].debris,fx[i].originType,fx[i].originEnt,fx[i].bone_id,fx[i].targetType,fx[i].targetEnt};
  memcpy(values+1+i*17,fields,sizeof(fields));positions[i*8]=fx[i].duration;positions[i*8+1]=fx[i].radius;
  memcpy(positions+i*8+2,fx[i].originPos,12);memcpy(positions+i*8+5,fx[i].targetPos,12);
 }
}
void original_appearance(int scenario,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};Packet p={0};Entity e={0};
 struct {char *name;} seqtype={"FixtureSequence"};struct {void *type;} seq={&seqtype};
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 e.type=scenario==1?ENTTYPE_MISSION_ITEM:1;e.npcIndex=12345;e.costumeIndex=3;
 e.costumeWorldGroup="FixtureWorldGroup";e.seq=(void*)&seq;
 entSendCostume(&p,&e,NULL,scenario!=2);
 pktSendIfSetBits(&p,8,44);
 *length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
static void original_target_fields(Packet *p,int scenario){
 Entity e={0},target={0},assist={0},taunter={0};Character ch={0};
 AttribMod taunt={&taunter,1},placate1={&target,1},placate2={&assist,0};AttribMod *placates[]={&placate1,&placate2};
 e.pchar=&ch;target.owner=4;assist.owner=7;taunter.owner=9;
 ch.erAssist=&assist;ch.erTargetInstantaneous=&target;ch.pmodTaunt=&taunt;ch.ppmodPlacates=placates;
 e.clear_target=scenario==1;fixture_placates=2;entSendTargetUpdate(p,&e,scenario!=2);fixture_placates=0;
}
void original_target(int scenario,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};Packet p={0};initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 original_target_fields(&p,scenario);*length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
static void original_inventory_fields(Packet *p,int valid){
 Entity e={0};Player pl={0};Character ch={0};ch.entParent=&e;e.pl=valid?&pl:NULL;
 for(int i=0;i<5;i++){ch.inventory_total[i]=100+i;ch.inventory_used[i]=50+i;}
 ch.auction_total=999;ch.boost_total=70;character_SendInventorySizes(&ch,p);
}
void original_inventory(int valid,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};Packet p={0};initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 original_inventory_fields(&p,valid);*length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_deletes(int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0},visible[320]={0};Packet p={0};EntNetLink link={0};Entity e={0};
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);
 ent_delete_count=1;ent_deletes[0]=4;ent_delete_ids[0]=91;
 link.sent_ids[0]=(1u<<4)|(1u<<7);e.id=92;entities[7]=&e;entities_max=8;
 entSendDeletes(&p,&link,visible);
 *length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_orientation(const U32 *values,U32 mask,int aligned,U8 *out,U32 *length){
 U32 storage[8192]={0};Packet p={0};Entity e={0};memcpy(e.net_iqrot,values,12);
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);entSendQrotUpdate(&p,&e,mask);
 *length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
}
void original_receive_orientation(const U8 *data,U32 bits,int aligned,U32 id,U32 *ids,float *q){
 U32 storage[8192]={0};Packet p={0};Entity e={0};memcpy(e.pkt_id_qrot,ids,12);memcpy(e.net_qrot,q,16);
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Read,aligned,0);memcpy(storage,data,(bits+7)/8);p.stream.bitLength=bits;p.id=id;
 entGetOrientation(&p,&e);memcpy(ids,e.pkt_id_qrot,12);memcpy(q,e.net_qrot,16);
}
'''
    # The title producer is an inline statement block inside sendEntity. Keep
    # its exact bytes; explicitly do not claim complete sendEntity execution.
    sender=extract(send,'sendEntity')
    title_at=sender.index('        if(e->pl)',sender.index('entSendPowerCust(pak, e, send_ent.player_ent);'))
    title_end=sender.index('\n    }\n\n#ifdef RAGDOLL',title_at)
    title_block=sender[title_at:title_end]
    assert title_block.count('pktSendBitsAuto(pak, e->pl->helperStatus);')==1
    code+=(HERE/'titles_oracle_shim.h').read_text()
    code+=get(util,'pktGetBitsAuto')
    code+='\nstatic void original_titles_statement(Packet *pak,TitleEntity *e){\n'+title_block+'\n}\n'
    code+='\n#define Entity TitleEntity\n'+get(recv,'entReceiveTitles')+'\n#undef Entity\n'
    code+=(HERE/'titles_fixture.c.inc').read_text()
    title_proof={'producer_scope':'unchanged inline sendEntity title statement block; not full sendEntity',
                 'producer_statement_sha256_lf':hashlib.sha256(title_block.encode()).hexdigest(),
                 'consumer_function_sha256_lf':hashlib.sha256(extract(recv,'entReceiveTitles').encode()).hexdigest(),
                 'source_fields':{'name':128,'the_text':10,'common':32,'origin':32,'special':128}}
    # Consecutive very-rare prefix: exact inline blocks, not full entities.
    rare_at=sender.index('        pktSendBits(pak, 1, ENTINFO(e).send_on_odd_send);')
    rare_end=sender.index('        entSendOtherSupergroupInfo(',rare_at)
    rare_send=sender[rare_at:rare_end]
    receiver=extract(recv,'entReceive')
    rare_at=receiver.index('            // These are just part of the main stream, no separate packet ids are kept')
    rare_end=receiver.index('            START_BIT_COUNT(pak, "entReceiveOtherSupergroupInfo");',rare_at)
    rare_receive=receiver[rare_at:rare_end]
    code+=(HERE/'rare_oracle_shim.h').read_text()
    code+=get(source['Common/entity/character_net.c'],'basepower_Receive')
    code+=get(send,'entSendAfk')
    rare_consumers=['entReceiveSendOnOddSend','entReceiveAllyID','entReceivePvP','entReceiveEntCollision','entReceiveEntSelectable','entReceiveNoDrawOnClient','entReceiveShowOnMap','entReceiveContactOrPnpc','entReceiveNameUpdate','entReceivePetName','entReceivePetInfo','entReceiveAFK']
    code+=''.join(get(recv,n) for n in rare_consumers)
    code+='\nstatic void original_rare_send_statement(Packet *pak,Entity *e,int send_afk_string){\n'+rare_send+'\n}\n'
    code+='\nstatic void original_rare_receive_statement(Packet *pak,Entity *e,int stream_oo_packet,int isSelf){\n'+rare_receive+'\n}\n'
    code+=(HERE/'rare_fixture.c.inc').read_text()
    rare_proof={'scope':'unchanged inline rare prefix producer/consumer statements and complete named component functions; no complete sendEntity/entReceive execution; synthetic owner/power/UI adapters',
                'producer_statement_sha256_lf':hashlib.sha256(rare_send.encode()).hexdigest(),
                'consumer_statement_sha256_lf':hashlib.sha256(rare_receive.encode()).hexdigest(),
                'component_consumer_sha256_lf':{n:hashlib.sha256(extract(recv,n).encode()).hexdigest() for n in rare_consumers}}
    cfile=directory/'source-oracle.c';cfile.write_text(code);so=directory/'source-oracle.so'
    run([os.environ.get('CC','cc'),'-std=c99','-O0','-shared','-fPIC','-w','-I'+str(repo/'native-android/include'),'-I'+str(HERE),cfile,'-lm','-o',so])
    lib=C.CDLL(str(so))
    lib.original_fields.argtypes=[C.c_void_p,C.c_void_p,C.c_uint32,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_receive_stats.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_int,C.c_void_p,C.c_void_p]
    lib.original_stats.argtypes=[C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32),C.c_void_p]
    lib.original_create.argtypes=[C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_record.argtypes=[C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_list.argtypes=[C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_receive_netfx.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_void_p,C.c_void_p]
    for name in ['original_appearance','original_target','original_inventory','original_netfx']:
        getattr(lib,name).argtypes=[C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_deletes.argtypes=[C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_orientation.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_receive_orientation.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_uint32,C.c_void_p,C.c_void_p]
    lib.original_titles.argtypes=[C.c_int,C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]
    lib.original_titles_seed.argtypes=[C.c_void_p]
    lib.original_receive_titles.argtypes=[C.c_void_p,C.c_uint32,C.c_int,C.c_uint32,C.c_uint32,C.c_void_p]
    title_proof['state_bytes']=lib.original_titles_size()
    lib.original_rare.argtypes=[C.c_int,C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32),C.c_void_p]
    rare_proof['event_bytes']=lib.original_rare_size()
    return lib,pins,names,title_proof,rare_proof

def fixtures(lib,directory):
    content=[];count=0
    def emit(label,data,bits):
        nonlocal count
        content.append('static const unsigned char '+label+'[]={'+','.join(map(str,data))+'};\n#define '+label+'_bits '+str(bits)+'u\n');count+=1
    def fields(seq,mode):
        widths=(C.c_int*len(seq))(*(x[0] for x in seq));vals=(C.c_uint32*len(seq))(*(x[1] for x in seq));out=(C.c_uint8*32768)();bits=C.c_uint32()
        lib.original_fields(widths,vals,len(seq),mode,out,C.byref(bits));return bytes(out[:(bits.value+7)//8]),bits.value
    def u(w,v):return [(w,v)]
    def p(w,v):return [(-w,v)]
    def opt(w,v,packed=False):return u(1,1)+(p(w,v) if packed else u(w,v)) if v else u(1,0)
    def auto(v):
        widths=[2,10,24,32];i=next(i for i,w in enumerate(widths) if v<1<<w);return u(2,i)+u(widths[i],v)
    def string(s):return sum((u(8,v) for v in s.encode()+b'\0'),[])
    title_size=lib.original_titles_size();seed=(C.c_uint8*title_size)();lib.original_titles_seed(seed)
    content.append('static const unsigned char title_seed_bytes[]={'+','.join(map(str,seed))+'};\n')
    title_rows=[];rare_rows=[]
    for mode in [0,1]:
        for offset in (range(8) if mode==0 else [0]):
            for scenario in range(6):
                out=(C.c_uint8*32768)();bits=C.c_uint32();start=C.c_uint32()
                lib.original_titles(scenario,mode,offset,out,C.byref(bits),C.byref(start))
                label=f'titles_{mode}_{offset}_{scenario}';emit(label,bytes(out[:(bits.value+7)//8]),bits.value)
                expected=[]
                for packet in [9,10,11]:
                    value=(C.c_uint8*title_size)();lib.original_receive_titles(out,bits.value,mode,start.value,packet,value)
                    name=f'{label}_expected_{packet}';content.append('static const unsigned char '+name+'[]={'+','.join(map(str,value))+'};\n');expected.append(name)
                title_rows.append('{'+','.join([label,str(bits.value),str(start.value),str(mode),str(scenario),'{'+','.join(expected)+'}'])+'}')
        for offset in (range(8) if mode==0 else [0]):
            for scenario in range(8):
                out=(C.c_uint8*32768)();bits=C.c_uint32();start=C.c_uint32();expected=(C.c_uint8*lib.original_rare_size())()
                lib.original_rare(scenario,mode,offset,out,C.byref(bits),C.byref(start),expected)
                label=f'rare_{mode}_{offset}_{scenario}';emit(label,bytes(out[:(bits.value+7)//8]),bits.value)
                content.append('static const unsigned char '+label+'_expected[]={'+','.join(map(str,expected))+'};\n')
                rare_rows.append('{'+','.join([label,str(bits.value),str(start.value),str(mode),str(scenario),label+'_expected'])+'}')
        for self in [0,1]:
            out=(C.c_uint8*32768)();bits=C.c_uint32();expected=(C.c_float*5)();lib.original_stats(self,mode,out,C.byref(bits),expected)
            label=f'stats_{self}_{mode}';emit(label,bytes(out[:(bits.value+7)//8]),bits.value)
            content.append('static const float '+label+'_expected[]={'+','.join(float(v).hex()+'f' for v in expected)+'};\n')
            values=(C.c_float*16)();integers=(C.c_int*6)();lib.original_receive_stats(out,bits.value,mode,self,values,integers)
            content.append('static const float '+label+'_received[]={'+','.join(float(v).hex()+'f' for v in values)+'};\n')
            content.append('static const int '+label+'_integers[]={'+','.join(str(v) for v in integers)+'};\n')
        for scenario in range(3):
            out=(C.c_uint8*32768)();bits=C.c_uint32();lib.original_netfx(scenario,mode,out,C.byref(bits))
            label=f'netfx_{scenario}_{mode}';emit(label,bytes(out[:(bits.value+7)//8]),bits.value)
            vals=(C.c_uint32*(1+32*17))();positions=(C.c_float*(32*8))();lib.original_receive_netfx(out,bits.value,mode,vals,positions)
            content.append('static const unsigned int '+label+'_values[]={'+','.join(str(v)+'u' for v in vals[:1+vals[0]*17])+'};\n')
            content.append('static const float '+label+'_positions[]={'+','.join(float(v).hex()+'f' for v in positions[:max(1,vals[0]*8)])+'};\n')
        for prefix,scenarios in [('appearance',3),('target',3),('inventory',2)]:
            for scenario in range(scenarios):
                out=(C.c_uint8*32768)();bits=C.c_uint32();getattr(lib,'original_'+prefix)(scenario,mode,out,C.byref(bits))
                emit(f'{prefix}_{scenario}_{mode}',bytes(out[:(bits.value+7)//8]),bits.value)
        for scenario in range(8):
            out=(C.c_uint8*32768)();bits=C.c_uint32();lib.original_create(scenario,mode,out,C.byref(bits))
            emit('create_'+str(scenario)+'_'+str(mode),bytes(out[:(bits.value+7)//8]),bits.value)
        for medium in [0,1,2,3]:
            out=(C.c_uint8*32768)();bits=C.c_uint32();lib.original_record(medium,mode,out,C.byref(bits))
            emit(f'source_record_{medium}_{mode}',bytes(out[:(bits.value+7)//8]),bits.value)
        for scenario,label in enumerate(['source_list_0','source_list_1','source_list_2','source_list_self','source_list_duplicate_self']):
            out=(C.c_uint8*32768)();bits=C.c_uint32();lib.original_list(scenario,mode,out,C.byref(bits))
            emit(f'{label}_{mode}',bytes(out[:(bits.value+7)//8]),bits.value)
        out=(C.c_uint8*32768)();bits=C.c_uint32();lib.original_deletes(mode,out,C.byref(bits))
        emit(f'source_deletes{mode}',bytes(out[:(bits.value+7)//8]),bits.value)
        ids=(C.c_uint32*3)();q=(C.c_float*4)(0,0,0,1)
        for step,(mask,vals,ident) in enumerate([(7,[256,384,256],10),(3,[320,256,256],12),(7,[256,256,384],11),(1,[400,0,0],12),(0,[0,0,0],20)]):
            out=(C.c_uint8*32768)();bits=C.c_uint32();values=(C.c_uint32*3)(*vals)
            lib.original_orientation(values,mask,mode,out,C.byref(bits));data=bytes(out[:(bits.value+7)//8]);label=f'orientation_{step}_{mode}'
            emit(label,data,bits.value);lib.original_receive_orientation(data,bits.value,mode,ident,ids,q)
            content.append('static const float '+label+'_expected[]={'+','.join(float(v).hex()+'f' for v in q)+'};\n')
            content.append('static const unsigned int '+label+'_ids[]={'+','.join(map(str,ids))+'};\n')
        # Complete source-layout per-record fixtures. They intentionally suppress
        # pchar/appearance: do not describe a complete real player full update.
        pos=u(3,7)+u(24,(1<<23)+800)+u(24,(1<<23)-400)+u(24,(1<<23)+8192)
        qrot=opt(3,7)+u(9,256)+u(9,384)+u(9,256)
        vision=auto(1)+auto(0)+auto(0)
        npc=u(1,1)+u(1,0)+p(12,91)+p(2,1)+u(1,0)+u(1,1)+string('FixtureNPC')+u(1,0)+u(1,1)+u(32,123)+u(1,0)*4+auto(0)
        simple=npc+u(1,0)+pos+qrot+u(1,0)*3+vision+u(1,0)
        emit('record_simple'+str(mode),*fields(simple,mode))
        medium=npc+u(1,1)+u(1,1)+u(1,0)+u(1,1)+opt(3,1,True)+pos+qrot+u(1,1)+opt(8,33,True)+opt(4,4,True)+opt(11,3)+p(1,1)+p(10,42)+p(6,6)+opt(16,1000,True)+u(1,1)+u(1,1)+string('FixtureAnim')+u(1,0)*2+opt(2,0,True)+opt(8,20)+opt(5,1)+u(10,256)*3+vision+u(1,0)
        emit('record_medium'+str(mode),*fields(medium,mode))
        update=u(1,0)+u(1,0)+pos+u(1,1)+u(1,1)+qrot+u(1,0)*3+vision+u(1,0)
        emit('record_update'+str(mode),*fields(update,mode))
        unsupported_interp=u(1,0)+u(1,0)+pos+u(1,1)+u(1,0)
        emit('unsupported_interp'+str(mode),*fields(unsupported_interp,mode))
        unsupported_appearance=npc+u(1,1)+u(1,1)+u(1,0)+u(1,0)+pos+qrot+u(1,0)+p(1,0)+u(1,0)+u(1,0)*2+opt(2,1,True)
        emit('unsupported_appearance'+str(mode),*fields(unsupported_appearance,mode))
        unsupported_pchar=npc+u(1,0)+pos+qrot+u(1,1)+u(1,0)*2+u(1,1)*3+p(1,3)
        emit('unsupported_pchar'+str(mode),*fields(unsupported_pchar,mode))
        status=u(10,0x305)+auto(3)+auto(7)+auto(2)+string('Held')+string('SyntheticStatus')
        emit('status'+str(mode),*fields(status,mode))
        for name,seq in [('target_overflow',u(1,1)+opt(12,10240,True)+u(1,0)*3+p(2,0)),('target_limit',u(1,1)+u(1,0)*4+p(2,33)),('status_limit',u(10,0)+auto(1)+auto(0)+auto(17)),('status_long',u(10,0)+auto(1)+auto(0)+auto(1)+string('x'*128)),('inventory_unknown',p(1,1)+p(3,6)),('inventory_invalid',p(1,2)),('netfx_limit',p(1,33)),('netfx_zero_command',p(1,1)+u(2,0)+u(32,100)+u(1,0)),('netfx_zero_id',p(1,1)+u(2,1)+u(32,0)+u(1,0)),('netfx_nan',p(1,1)+u(2,1)+u(32,100)+u(1,0)*6+u(1,1)+u(32,0x7fc00000)),('stats_unknown',u(1,1)+p(1,7)),('stats_duplicate',u(1,1)+p(1,3)+p(16,100)+u(1,1)+p(1,3)),('stats_relative',u(1,1)+p(1,0)+u(1,1)+u(1,0)),('stats_nested_unknown',u(1,1)+p(1,0)+u(1,1)*3+p(1,8)),('appearance_absent_group',opt(2,3,True)+p(12,555)+p(1,2)+u(1,0)+p(1,0)+opt(8,9)),('appearance_empty_group',opt(2,4,True)+string('SecondSequence')+u(1,1)+string('')+opt(8,8))]:
            emit(name+str(mode),*fields(seq,mode))
        fxprefix=p(1,1)+u(2,1)+u(32,100)+u(1,0)*10
        for name,seq in [('netfx_origin_type',fxprefix+opt(2,3)),('netfx_bone_limit',fxprefix+u(1,0)*2+p(2,256)),('netfx_target_limit',fxprefix+u(1,0)*2+p(2,0)+u(1,0)+opt(12,10240,True)),('netfx_infinite_position',fxprefix+opt(2,1)+u(32,0x7f800000))]:
            emit(name+str(mode),*fields(seq,mode))
        # Adversarial rare-prefix cases use original scalar writers only.
        lead=u(1,0)+p(2,0)+p(4,0)+p(1,0)
        types=u(1,0)+u(2,0)+u(3,0)+u(1,0)
        flags=u(1,0)*2+p(5,0)+u(1,0)*9
        pre=lead+types+flags
        petpre=pre+u(1,0)+u(1,1)
        petbase=petpre+p(12,12)+p(12,0)+u(1,0)+u(1,0)*3
        emit('rare_bad_ignore'+str(mode),*fields(u(1,0)+p(2,0)+p(4,0)+p(1,2),mode))
        for name,owner,creator in [('owner_zero',0,0),('owner_limit',10240,0),('creator_limit',12,10240)]:
            emit('rare_bad_'+name+str(mode),*fields(petpre+p(12,owner)+p(12,creator),mode))
        for name,seq in [('name',pre+u(1,1)+string('n'*128)),('display',petbase+u(1,1)+string('d'*1000)),('pet',petbase+u(1,0)+p(1,0)+u(1,1)+string('p'*128)),('afk',pre+u(1,0)*2+u(1,1)*2+string('a'*48))]:
            emit('rare_long_'+name+str(mode),*fields(seq,mode))
        emit('rare_unknown_crc'+str(mode),*fields(petpre+p(12,12)+p(12,0)+u(1,1)+auto(0x12345678)+u(1,0)*4+p(1,0)+u(1,0)*2,mode))
        if mode:
            for name,seq in [('player_bits',lead+u(8,2)),('presence',pre+u(8,2)),('afk',pre+u(1,0)*2+u(8,2)),('auto',u(1,0)+p(2,0)+p(4,0)+p(1,1)+u(8,4))]:
                emit('rare_bad_'+name,*fields(seq,mode))
        # Adversarial title cases use original scalar writers only; they are
        # not claimed as unchanged original producer output.
        title_prefix=u(1,1)+string('')+p(5,0)
        for field,limit in [('name',128),('the',10),('common',32),('origin',32),('special',128)]:
            before={'name':u(1,1),'the':title_prefix+u(1,1),
                    'common':title_prefix+u(1,0)+u(1,1),
                    'origin':title_prefix+u(1,0)*2+u(1,1),
                    'special':title_prefix+u(1,0)*3+auto(0)*2+u(32,0)+u(1,1)}[field]
            emit('titles_long_'+field+str(mode),*fields(before+string('x'*limit),mode))
        if mode:
            for label,seq in [('presence',u(8,2)),('optional',title_prefix+u(8,2)),('auto',title_prefix+u(1,0)*3+u(8,4)),('late_flag',title_prefix+u(1,0)*3+auto(0)*2+u(32,0)+u(1,0)+u(8,2)),('gender',title_prefix+u(1,0)*3+auto(0)*2+u(32,0)+u(1,0)*2+u(8,4))]:
                emit('titles_bad_'+label,*fields(seq,mode))
        # Taskforce malformed fixtures are scalar constructions, separate from
        # the complete unchanged component-function oracle.
        task_head=u(1,1)*2+auto(0)*3
        task_contact=task_head+string('')
        task_review=task_contact+u(1,0)*2+u(1,1)
        for label,seq in [('contact',task_head+string('x'*32)),('name',task_review+string('x'*256)),('author',task_review+string('')+string('x'*128)),('description',task_review+string('')*2+string('x'*4096)),('flashback',u(1,0)+p(1,2)),('hole',task_contact+u(1,1)*2+u(1,1)+u(1,0)+u(1,1)*2+p(4,2))]:
            emit('task_bad_'+label+str(mode),*fields(seq,mode))
        if mode:emit('task_bad_flag',*fields(u(8,2),mode))
        # Costume failure fixtures use original scalar writers in source field order.
        costume_head=u(1,0)*2+p(6,1)+u(32,0)+u(1,0)+u(3,0)+u(1,1)+u(32,0)*72
        costume_body=costume_head+u(32,0)*30
        nullparts=u(1,0)*2+u(1,1)*3
        for name,seq in [('costume_bad_empty_cache',u(1,1)*2),('costume_bad_hole',u(1,1)+u(1,0)+u(1,1)*2+p(4,2)),('costume_bad_index',u(1,1)+u(1,0)+u(1,1)*2+p(4,16)),('costume_bad_long',u(1,1)+u(1,0)+u(1,1)+u(1,0)+string('x'*260)),('costume_bad_body',u(1,0)*2+p(6,6)+u(32,0)+u(1,0)+u(3,0)+u(1,0)),('costume_bad_nan',costume_head+u(32,0x7fc00000)),('costume_bad_parts',costume_body+u(1,1)+p(4,5)),('costume_bad_color_cache',costume_body+u(1,1)+p(4,1)+nullparts+u(1,0)+u(1,1)),('costume_bad_color_hole',costume_body+u(1,1)+p(4,1)+nullparts+u(1,0)*2+u(1,1)+p(3,1))]:
            emit(name+str(mode),*fields(seq,mode))
        self_envelope=opt(2,1,True)+u(1,1)
        own_empty_rewards=self_envelope+u(32,0)*2+u(1,0)
        for name,seq in [('envelope_unknown',opt(2,5,True)),('envelope_reward_limit',self_envelope+u(32,257)),('envelope_reward_hole',self_envelope+u(32,1)+u(1,1)*3+p(4,2)),('envelope_reward_null',self_envelope+u(32,1)+u(1,1)+u(1,0)),('envelope_slots',own_empty_rewards+u(8,10)+u(8,0)),('envelope_current',own_empty_rewards+u(8,255)+u(8,3)),('envelope_count_zero',own_empty_rewards+u(8,0)+u(8,3)+u(1,1)+u(4,0)),('envelope_count_limit',own_empty_rewards+u(8,0)+u(8,10)+u(1,1)+u(4,11)),('envelope_other_multiple',opt(2,1,True)+u(1,0)*2+u(1,1)+u(4,1)),('envelope_custom_flag',opt(2,3,True)+p(12,1)+p(1,0)+u(1,0)+p(1,2)),('envelope_sequence_long',opt(2,4,True)+string('x'*260)),('envelope_fx_long',opt(2,1,True)+u(1,0)*3+costume_body+u(1,1)+p(4,0)+u(1,0)+u(1,1)+string('x'*260))]:
            emit(name+str(mode),*fields(seq,mode))
        emit('envelope_rewards_max'+str(mode),*fields(self_envelope+u(32,256)+u(1,0)*256+u(32,256)+u(1,0)*256+u(1,0)+u(8,0)+u(8,255)+u(1,0)+costume_body+u(1,1)+p(4,0)+u(1,0)*3,mode))
        power_self=opt(2,1,True)+u(1,1)
        power_owned=opt(2,2,True)+u(1,1)
        for name,seq in [('power_unknown',opt(2,3,True)),('power_current',power_self+u(8,10)+u(8,0)),('power_slots_zero',power_self+u(8,0)*2+u(1,1)+u(4,0)),('power_slots_limit',power_self+u(8,0)*2+u(1,1)+u(4,11)),('power_current_unstored',power_self+u(8,2)+u(8,0)+u(1,1)+u(4,2)),('power_count_limit',power_owned+auto(513)),('power_long_token',power_owned+auto(1)+auto(1)+auto(0)*2+string('x'*260))]:
            emit(name+str(mode),*fields(seq,mode))
        power_items=(auto(1)+auto(0)*2+string(''))*512
        power_full_list=u(1,1)+auto(512)+power_items
        emit('power_aggregate_max'+str(mode),*fields(power_self+u(8,0)+u(8,7)+u(1,1)+u(4,8)+power_full_list*8,mode))
        emit('power_aggregate_limit'+str(mode),*fields(power_self+u(8,0)+u(8,8)+u(1,1)+u(4,9)+power_full_list*8+u(1,1)+auto(512),mode))
        # Manual zero-field fixture complements original nonempty stats.
        pchar=npc+u(1,0)+pos+qrot+u(1,1)+u(1,0)*2+u(1,1)*2+u(1,0)+vision+auto(8)+u(1,0)+u(1,1)+status+u(1,0)
        emit('record_pchar'+str(mode),*fields(pchar,mode))
        # NPC and sequence appearances in the audited outer record ordering.
        for typ,appearance in [(3,opt(2,3,True)+p(12,12345)+p(1,3)+u(1,1)+string('FixtureWorldGroup')+p(1,0)),(4,opt(2,4,True)+string('FixtureSequence')+u(1,1)+string('FixtureWorldGroup'))]:
            body=npc+u(1,1)+u(1,1)+u(1,0)+u(1,0)+pos+qrot+u(1,0)+p(1,0)+u(1,0)+u(1,0)*2+appearance+opt(8,44)+u(1,0)+vision+u(1,0)
            emit('record_appearance_'+str(typ)+'_'+str(mode),*fields(body,mode))
        # Independent grammar constructions complement the source-function
        # compositions. Each complete list ends at the canonical delta0/1/1.
        sentinel=p(1,0)+u(1,1)+u(1,1)
        npc_next=u(1,1)+u(1,0)+p(12,92)+npc[3:]
        simple_next=npc_next+simple[len(npc):]
        unsupported_next=npc_next+unsupported_appearance[len(npc):]
        for name,seq in [
            ('list_empty',sentinel),
            ('list_end_nonzero_delta',p(1,1)+u(1,1)+u(1,1)),
            ('list_duplicate_index',p(1,4)+simple+p(1,0xffffffff)+simple_next+sentinel),
            ('list_sentinel_collision',p(1,7)+simple+p(1,0xfffffffe)+simple_next+sentinel),
            ('list_zero_normal',p(1,0)+simple+sentinel),
            ('list_unknown_update',p(1,4)+update+sentinel),
            ('list_capacity_missing',p(1,4)+simple+p(1,2)+simple_next+sentinel),
            ('list_late_unsupported',p(1,4)+simple+p(1,2)+unsupported_next+sentinel),
        ]:
            emit(name+str(mode),*fields(seq,mode))
        for name,seq in [('delta_indices',p(1,4)+p(1,2)),('delta_descending',p(1,7)+p(1,0xfffffffc)+p(1,4)),('delta_overflow',p(1,10240)),('delta_zero',p(1,0)),('end',u(1,1)+u(1,1)),('update_flag',u(1,0)),('deletes',p(1,2)+p(12,4)+p(12,91)+p(12,7)+p(12,92)),('delete_large_generation',p(1,1)+p(12,4)+p(12,70001)),('delete_zero',p(1,1)+p(12,0)+p(12,91)),('delete_duplicate',p(1,2)+p(12,4)+p(12,91)+p(12,4)+p(12,92)),('delete_limit',p(1,257)),('bad_type',u(1,1)+u(1,0)+p(12,91)+p(2,99)),('bad_id',u(1,1)+u(1,0)+p(12,0)+p(2,1)),('long_name',u(1,1)+u(1,0)+p(12,91)+p(2,1)+u(1,0)+u(1,1)+string('x'*256))]:
            emit(name+str(mode),*fields(seq,mode))
    content.append('typedef struct {const unsigned char *data;unsigned bits,start,mode,scenario;const unsigned char *expected[3];} TitleFixture;\n')
    content.append('typedef struct {const unsigned char *data;unsigned bits,start,mode,scenario;const unsigned char *expected;} RareFixture;\nstatic const RareFixture rare_fixtures[]={'+','.join(rare_rows)+'};\n')
    content.append('static const TitleFixture title_fixtures[]={'+','.join(title_rows)+'};\n')
    (directory/'fixtures.h').write_text(''.join(content));return count

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=REPO);ap.add_argument('--output',type=Path);ap.add_argument('--fixtures-output',type=Path);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);args=ap.parse_args()
    if bool(args.ndk)!=bool(args.android_output):ap.error('--ndk and --android-output must be supplied together')
    with tempfile.TemporaryDirectory(prefix='coh-entities-') as d:
        directory=Path(d);lib,pins,names,title_proof,rare_proof=oracle(args.source_root.resolve(),directory);n=fixtures(lib,directory)
        spec=importlib.util.spec_from_file_location('costume_oracle',HERE/'costume_oracle.py');costume_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(costume_module)
        spec=importlib.util.spec_from_file_location('costume_bit_adapter',args.source_root.resolve()/'native-android/tools/protocol_fixture/prepare.py');costume_helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(costume_helper)
        costume_proof=costume_module.generate(args.source_root.resolve(),directory,costume_helper,run)
        if args.fixtures_output:
            args.fixtures_output.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(directory/'fixtures.h',args.fixtures_output)
            shutil.copyfile(directory/'costume_fixtures.h',args.fixtures_output.parent/'costume_fixtures.h')
        common=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(directory),'-I'+str(HERE)]
        sources=[HERE/'coh_entities.c',HERE/'coh_costume.c',HERE/'coh_taskforce.c',HERE/'../replication/coh_replication.c',HERE/'test_entities.c',HERE/'test_costume.c']
        checks={};modes=[('release',['-O2'])]
        if args.sanitize:modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
        for name,flags in modes:
            exe=directory/name;run([os.environ.get('CC','cc'),*common,*flags,*sources,'-lm','-o',exe])
            env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
            checks[name]=json.loads(run([exe],env=env).stdout)
        fixture_sha=hashlib.sha256((directory/'fixtures.h').read_bytes()).hexdigest()
        source_hashes={str(p.resolve().relative_to(REPO.resolve())):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*sources,HERE/'CMakeLists.txt',HERE/'coh_entities.h',HERE/'coh_costume.h',HERE/'costume_oracle.py',HERE/'costume_oracle_shim.h',HERE/'costume_envelope_oracle_shim.h',HERE/'costume_envelope_oracle.c.inc',HERE/'costume_envelope_fixture.c.inc',HERE/'power_custom_oracle_shim.h',HERE/'power_custom_observer.c.inc',HERE/'power_custom_fixture.c.inc',HERE/'check.py',HERE/'oracle_shim.h',HERE/'stats_oracle_shim.h',HERE/'titles_oracle_shim.h',HERE/'titles_fixture.c.inc',HERE/'test_titles.c.inc',HERE/'rare_oracle_shim.h',HERE/'rare_fixture.c.inc',HERE/'test_rare.c.inc',HERE/'coh_taskforce.h',HERE/'taskforce_oracle_shim.h',HERE/'taskforce_fixture.c.inc',HERE/'test_taskforce.c.inc',HERE/'source-pins.json',HERE/'../replication/coh_replication.h',HERE/'../coh_contracts.h',REPO/'native-android/tools/protocol_fixture/prepare.py']}
        android={}
        if args.ndk:
            args.android_output.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(directory/'fixtures.h',args.android_output/'fixtures.h')
            shutil.copyfile(directory/'costume_fixtures.h',args.android_output/'costume_fixtures.h')
            tc=args.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'
            for abi,target in [('arm64-v8a','aarch64-linux-android26-clang'),('x86_64','x86_64-linux-android26-clang')]:
                dest=args.android_output/abi;dest.mkdir(parents=True,exist_ok=True);exe=dest/'coh_entities_test'
                run([tc/target,*common,'-O2',*sources,'-lm','-o',exe]);sha=hashlib.sha256(exe.read_bytes()).hexdigest()
                receipt={'passed':True,'abi':abi,'binary':exe.name,'binary_sha256':sha,'executed':False,'fixtures_sha256':fixture_sha,'costume_fixtures_sha256':costume_proof['fixtures_sha256'],'source_sha256':source_hashes}
                (dest/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');android[abi]=receipt
        proof={'schema':1,'passed':True,'scope':'original create/pet CRC, NPC/sequence costume, target, inventory, pose/sequence/delete component producers; original NetFX and standalone complete appearance/costume/reward producer/consumer parity; exact original basic/self schema producer and consumer comparisons; unchanged inline title producer block and full title consumer; unchanged rare-prefix inline statements and component consumers; synthetic record/list compositions; no original complete sendEntity/entSendUpdate execution','source_files':len(pins),'original_functions':names,'fixtures':n,'fixtures_sha256':fixture_sha,'costume_fixtures_sha256':costume_proof['fixtures_sha256'],'source_sha256':source_hashes,'checks':checks,'costume_oracle':costume_proof,'titles_oracle':dict(title_proof,producer_fixtures=54,consumer_comparisons=162),'rare_oracle':dict(rare_proof,producer_fixtures=72,consumer_comparisons=288,consumer_scope='source component cursor and applied-field assertions in fresh/stale and self/nonself contexts; native publishes raw events only'),'android':android,'full_update_tail_supported':False,'real_server_interoperability':False,'renderable_authoritative_actor':False,'emulator_qualified':False,'thor_accepted':False}
        if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(proof,indent=2)+'\n')
        print(json.dumps(proof,indent=2))
if __name__=='__main__':main()
