"""Source costume producer+consumer qualification; adapters use synthetic data."""
from pathlib import Path
import ctypes as C,hashlib,re,json,os
HERE=Path(__file__).resolve().parent
FILES=['Common/entity/costume.c','Common/entity/costume.h','Common/entity/entPlayer.h','Common/gameData/costume_data.c','Common/gameData/BodyPart.c','libs/UtilitiesLib/src/utils/mathutil.c']
def extract(text,name):
    m=re.search(r'^[^\n{};]+?\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{',text,re.M)
    if not m:raise ValueError('Missing source function '+name)
    at=text.index('{',m.start())+1;depth=1
    while depth:depth+=(text[at]=='{')-(text[at]=='}');at+=1
    return text[m.start():at]+'\n'
def generate(repo,directory,helper,run):
    paths=FILES+['libs/UtilitiesLib/src/network/net_packetutil.c','libs/UtilitiesLib/src/components/BitStream.c','Common/comm_game.h','Common/entity/entity_enum.h','MapServer/src/entity/entsend.c','Game/src/entity/entrecv.c']
    source={f:(repo/'upstream/ouroboros'/f).read_text() for f in paths}
    pins=json.loads((HERE/'source-pins.json').read_text())['sha256_lf']
    for name,data in source.items():
        if pins[name]!=hashlib.sha256(data.encode()).hexdigest():raise ValueError('Costume pin mismatch '+name)
    header=source['Common/entity/costume.h']
    enum=header[header.index('kBodyScale_Global'):header.index('MAX_BODY_SCALES')]
    if len(re.findall(r'kBodyScale_\w+',enum))!=30:raise ValueError('Source body scale count changed')
    if not re.search(r'#define\s+NUM_SG_COLOR_SLOTS\s+\(6\)',header):raise ValueError('Source SG slots changed')
    if 'stringcache[30*4]' not in source[FILES[0]] or 'colorcache[30*4]' not in source[FILES[0]]:raise ValueError('Source cache budget changed')
    if not re.search(r'num_colors_lookup\[\]\s*=\s*\{2,4\}',source[FILES[0]]):raise ValueError('Source color count schema changed')
    functions=[]
    def get(src,name):functions.append(name);return extract(src,name)
    bit=source['libs/UtilitiesLib/src/components/BitStream.c'];util=source['libs/UtilitiesLib/src/network/net_packetutil.c'];costume=source[FILES[0]]
    code=helper.PREAMBLE+'\n'+''.join(get(bit,n) for n in ['initBitStream','bsWriteBits','bsWriteBitsPack','bsReadBits','bsReadBitsPack','bsAlignByte','bsGetCursorBitPosition','bsWriteString'])
    code+='''
static void pktSendBits(Packet *p,int n,U32 v){bsWriteBits(&p->stream,n,v);}
static void pktSendBitsPack(Packet *p,int n,U32 v){bsWriteBitsPack(&p->stream,n,v);}
static U32 pktGetBits(Packet *p,int n){return bsReadBits(&p->stream,n);}
static U32 pktGetBitsPack(Packet *p,int n){return bsReadBitsPack(&p->stream,n);}
static void pktSendString(Packet *p,const char *s){bsWriteString(&p->stream,s?s:"");}
static void pktSendF32(Packet *p,float f){U32 u;memcpy(&u,&f,4);pktSendBits(p,32,u);}
static float pktGetF32(Packet *p){U32 u=pktGetBits(p,32);float f;memcpy(&f,&u,4);return f;}
'''
    code+=(HERE/'costume_oracle_shim.h').read_text()
    code+=get(source[FILES[-1]],'log2i')
    code+=''.join(get(util,n) for n in ['pktSendF','pktGetF','defaultBitsPack','defaultBitsPackGeneric','pktSendIndexedString','pktGetIndexedString','pktSendIndexedGeneric','pktGetIndexedGeneric'])
    code+=''.join(get(costume,n) for n in ['sendCachedIndexedString','getCachedIndexedString','sendCachedIndexedColor','getCachedIndexedColor','costume_send','costume_receive','NPCcostume_send','NPCcostume_receive'])
    code+='''
static void expected_text(CohEntCostumeText *t,const char *s){t->present=s!=NULL;if(s){assert(strlen(s)<260);strcpy(t->value,s);}}
void original_costume(int scenario,int aligned,U8 *out,U32 *length,U8 *expected,U32 *expected_size){
 U32 storage[32768]={0};Packet p={0};Costume send={0},received={0};CostumePart parts[30]={{0}},rparts[30]={{0}};CohEntCostume result={0};
 for(unsigned i=0;i<30;i++){send.parts[i]=&parts[i];received.parts[i]=&rparts[i];}
 send.appearance.entTypeFile=scenario==1?NULL:"FixtureEntity";send.appearance.costumeFilePrefix="Male";
 send.appearance.bodytype=1;send.appearance.colorSkin.integer=0xffeeddcc;send.appearance.convertedScale=1;send.appearance.currentSuperColorSet=5;
 send.appearance.iNumParts=scenario==2?0:scenario==1?4:3;
 for(unsigned i=0;i<30;i++)send.appearance.fScales[i]=i==0?1.25f:((int)i-15)*.05f;
 for(unsigned i=0;i<6;i++){
  SGColorBits *groups[]={send.appearance.superColorsPrimaryU,send.appearance.superColorsSecondaryU,send.appearance.superColorsPrimary2U,send.appearance.superColorsSecondary2U,send.appearance.superColorsTertiaryU,send.appearance.superColorsQuaternaryU};
  for(unsigned j=0;j<6;j++){groups[j][i].SGBitSetLow=1000+i*20+j;groups[j][i].SGBitSetHigh=2000+i*20+j;}
 }
 for(int i=0;i<send.appearance.iNumParts;i++){
  parts[i].pchGeom=i==2?"InlineGeometry":"FixtureGeometry";parts[i].pchTex1="InlineTexture";parts[i].pchTex2="InlineTexture";parts[i].pchFxName=i==1?"GlowFX":NULL;
  parts[i].regionName=i==1?NULL:"Upper";parts[i].bodySetName=i==2?"InlineBodySet":"BodySet";
  parts[i].color[0].integer=0x11223344;parts[i].color[1].integer=0;parts[i].color[2].integer=0x55667788;parts[i].color[3].integer=0xaabbccdd;
 }
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);costume_send(&p,&send,scenario!=1);*length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=p.stream.cursor.bit=0;literal_count=0;assert(costume_receive(&p,&received));assert(bsGetCursorBitPosition(&p.stream)==*length);
 result.generation=9;memset(result.manifest_sha256,0x42,32);expected_text(&result.entity_type_file,received.appearance.entTypeFile);expected_text(&result.prefix,received.appearance.costumeFilePrefix);
 result.body_type=received.appearance.bodytype;result.skin_color=received.appearance.colorSkin.integer;result.converted_scale=received.appearance.convertedScale;result.super_color_set=received.appearance.currentSuperColorSet;result.extra_info=scenario!=1;
 for(unsigned i=0;i<6;i++){
  SGColorBits *groups[]={received.appearance.superColorsPrimaryU,received.appearance.superColorsSecondaryU,received.appearance.superColorsPrimary2U,received.appearance.superColorsSecondary2U,received.appearance.superColorsTertiaryU,received.appearance.superColorsQuaternaryU};
  for(unsigned j=0;j<6;j++){result.super_colors[i][j*2]=groups[j][i].SGBitSetLow;result.super_colors[i][j*2+1]=groups[j][i].SGBitSetHigh;}
 }
 memcpy(result.scales,received.appearance.fScales,sizeof(result.scales));result.part_count=received.appearance.iNumParts;
 for(unsigned i=0;i<result.part_count;i++){
  CohEntCostumePart *d=&result.parts[i];CostumePart *s=received.parts[i];
  expected_text(&d->geometry,s->pchGeom);expected_text(&d->texture1,s->pchTex1);expected_text(&d->texture2,s->pchTex2);expected_text(&d->fx,s->pchFxName);expected_text(&d->region,s->regionName);expected_text(&d->body_set,s->bodySetName);
  for(unsigned j=0;j<4;j++)d->colors[j]=s->color[j].integer;
 }
 result.end_bit=*length;*expected_size=sizeof(result);memcpy(expected,&result,sizeof(result));
}
void original_custom(int aligned,U8 *out,U32 *length,U8 *expected,U32 *expected_size){
 U32 storage[32768]={0};Packet p={0};CustomNPCCostume send={0},received={0};CustomNPCCostumePart parts[3]={{0}};CustomNPCCostumePart *ptrs[]={parts,parts+1,parts+2};CohEntCustomCostume result={0};
 custom_count=3;send.parts=ptrs;send.skinColor.integer=0xff123456;
 for(int i=0;i<3;i++){parts[i].color[0].integer=100+i;parts[i].color[1].integer=200+i;parts[i].regionName=i==0?"Upper":i==1?"Lower":"Head";}
 initBitStream(&p.stream,(U8*)storage,sizeof(storage),Write,aligned,0);NPCcostume_send(&p,&send);*length=p.stream.bitLength;memcpy(out,storage,(*length+7)/8);
 p.stream.mode=Read;p.stream.cursor.byte=p.stream.cursor.bit=0;literal_count=0;assert(NPCcostume_receive(&p,&received));assert(bsGetCursorBitPosition(&p.stream)==*length);
 result.skin_color=received.skinColor.integer;result.count=custom_count;
 for(unsigned i=0;i<result.count;i++){result.parts[i].colors[0]=received.parts[i]->color[0].integer;result.parts[i].colors[1]=received.parts[i]->color[1].integer;strcpy(result.parts[i].region,received.parts[i]->regionName);free(received.parts[i]);}
 result.end_bit=*length;*expected_size=sizeof(result);memcpy(expected,&result,sizeof(result));
}
'''
    code+=source['Common/entity/entity_enum.h']
    comm=source['Common/comm_game.h'];start=comm.index('typedef enum',comm.index('// Used by entsend and entrecv.'));code+=comm[start:comm.index('} AppearanceType;',start)+len('} AppearanceType;')]+'\n'
    if not re.search(r'#define\s+MAX_COSTUMES\s+10',source['Common/entity/entPlayer.h']):raise ValueError('Original stored costume count changed')
    code+=''.join(get(util,n) for n in ['pktSendIfSetBitsPack','pktSendIfSetString','pktGetIfSetBitsPack','pktGetIfSetString'])
    code+=(HERE/'costume_envelope_oracle_shim.h').read_text()
    code+=(HERE/'costume_envelope_oracle.c.inc').read_text()
    code+=''.join(get(costume,n) for n in ['ent_SendCostumeRewards','ent_ReceiveCostumeRewards'])
    code+=get(source['MapServer/src/entity/entsend.c'],'entSendCostume')
    code+=get(source['Game/src/entity/entrecv.c'],'entReceiveCostume')
    code+=(HERE/'costume_envelope_fixture.c.inc').read_text()
    cfile=directory/'costume-oracle.c';cfile.write_text(code);so=directory/'costume-oracle.so'
    run([os.environ.get('CC','cc'),'-std=c99','-O0','-shared','-fPIC','-w','-I'+str(repo/'native-android/include'),'-I'+str(HERE),cfile,'-lm','-o',so])
    lib=C.CDLL(str(so));lib.original_costume.argtypes=[C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32),C.c_void_p,C.POINTER(C.c_uint32)];lib.original_custom.argtypes=[C.c_int,C.c_void_p,C.POINTER(C.c_uint32),C.c_void_p,C.POINTER(C.c_uint32)]
    lib.original_envelope.argtypes=[C.c_int,C.c_int,C.c_void_p,C.POINTER(C.c_uint32),C.c_void_p,C.POINTER(C.c_uint32)]
    content=['typedef struct {unsigned offset;unsigned char value;} CostumeExpectedByte;\n']
    for mode in [0,1]:
        for scenario in range(14):
            data=(C.c_uint8*131072)();expected=(C.c_uint8*1048576)();bits=C.c_uint32();size=C.c_uint32()
            if scenario<3:lib.original_costume(scenario,mode,data,C.byref(bits),expected,C.byref(size))
            elif scenario==3:lib.original_custom(mode,data,C.byref(bits),expected,C.byref(size))
            else:lib.original_envelope(scenario-4,mode,data,C.byref(bits),expected,C.byref(size))
            label=f'costume_{scenario}_{mode}'
            content.append('static const unsigned char '+label+'[]={'+','.join(map(str,data[:(bits.value+7)//8]))+'};\n#define '+label+'_bits '+str(bits.value)+'u\n')
            content.append('static const CostumeExpectedByte '+label+'_expected[]={'+','.join('{'+str(i)+','+str(v)+'}' for i,v in enumerate(expected[:size.value]) if v)+'};\n#define '+label+'_size '+str(size.value)+'u\n')
    path=directory/'costume_fixtures.h';path.write_text(''.join(content))
    return {'original_functions':functions,'fixtures':28,'fixtures_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'scope':'original full/owned/custom costume bodies and outer appearance/reward producer and consumer functions with synthetic dictionary/storage/render adapters; no entity record integration or server dictionary capture'}
