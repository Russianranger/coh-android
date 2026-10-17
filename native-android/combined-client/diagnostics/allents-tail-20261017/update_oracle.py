"""Whole original generic inventory update, retaining opaque auction text."""
import ctypes as C,json,re,tempfile
from pathlib import Path
import inventory_oracle as inv
q=inv.q;HERE=Path(__file__).resolve().parent
EXTRA=['MapServer/src/player/inventory_server.c','Game/src/player/inventory_client.c','Common/auction/Auction.c','libs/UtilitiesLib/src/network/net_packetutil.c']
def texts():return {**inv.texts(),**{p:q.source(p) for p in EXTRA}}
def generate(src):
 code,functions=inv.generate(src);code=re.sub(r'\bEntity\b','OuterEntity',code);code=re.sub(r'static void pktSendBitsAuto\([^\n]+\n','',code)
 code=code.replace('typedef struct{ConceptInventoryItem**conceptInv;int id,amount;U32 observed[8];} Character;', '''
typedef struct{char*text;} AuctionInventory;
typedef struct{ConceptInventoryItem**conceptInv;int id,amount;U32 observed[8];struct{int*type,*idx;}invStatusChange;int auctionInvUpdated;AuctionInventory*auctionInv;U32 observations[16][8];unsigned observed_count;} Character;
''')
 code=code.replace('p->observed[0]=kInventoryType_Concept;','p->observed[0]=kInventoryType_Concept;').replace('memcpy(p->observed+4,vars,4*sizeof(F32));','memcpy(p->observed+4,vars,4*sizeof(F32));memcpy(p->observations[p->observed_count++],p->observed,sizeof(p->observed));').replace('p->observed[3]=id;}','p->observed[3]=id;memset(p->observed+4,0,4*sizeof(U32));memcpy(p->observations[p->observed_count++],p->observed,sizeof(p->observed));}')
 code+='''
typedef struct{Character*pchar;} Entity;
static int eaiSize(int**p){return *p?(*p)[-1]:0;}
static void eaiSetSize(int**p,int n){assert(n==0);if(*p)(*p)[-1]=n;}
static void character_SetStoredSalvageInvCurrentCount(Character*p){(void)p;}
static void character_SetSalvageInvCurrentCount(Character*p){(void)p;}
#define devassert(x) (!!(x))
#define AINRANGE(i,a) ((i)>=0&&(i)<(int)ARRAY_SIZE(a))
static int auto_bins[]={2,10,24,32},g_bAssertOnBitStreamError;
static void AuctionInventory_ToStr(AuctionInventory*inv,char**s){*s=malloc(strlen(inv->text)+1);strcpy(*s,inv->text);}
static void estrDestroy(char**s){free(*s);*s=NULL;}
static AuctionInventory*AuctionInventory_Create(void){static AuctionInventory a;return &a;}
static void AuctionInventory_FromStr(AuctionInventory**inv,char*s){static char storage[1024];assert(strlen(s)<sizeof(storage));strcpy(storage,s);(*inv)->text=storage;}
'''
 for path,names in [(EXTRA[3],['pktSendBitsAuto','pktGetBitsAuto']),(EXTRA[2],['AuctionInventory_Send','AuctionInventory_Recv']),(EXTRA[0],['entity_SendInvUpdate']),(EXTRA[1],['entity_ReceiveInvUpdate'])]:
  for name in names:
   body=q.extract(src[path],name);code+=body;functions[name]={'source':path,'sha256_lf':q.sha(body.encode())}
 code+='''
void update_fixture(U32 scenario,U32 aligned,U32 prefix,U8*out,U32*bits,U32*end,U32*observed,char*text){
 U32 memory[4096]={0};Packet p={0};Character source={0},dest={0};Entity s={&source},d={&dest};ConceptDef def={123};ConceptItem concept={&def,{0.25f,-0.5f,1.0f,2.0f}};ConceptInventoryItem item={&concept};ConceptInventoryItem*items[]={&item};
 int types[17]={0},indexes[17]={0};int count=scenario%9;types[0]=indexes[0]=count;for(int i=0;i<count;i++){types[i+1]=(scenario+i)%7;indexes[i+1]=types[i+1]==kInventoryType_Concept?0:i;}
 source.conceptInv=items;source.invStatusChange.type=types+1;source.invStatusChange.idx=indexes+1;source.id=scenario*65537;source.amount=scenario*129;
 AuctionInventory auction={scenario%3?"InventorySize 40\\nItems { Id 1 }\\n":""};source.auctionInv=&auction;source.auctionInvUpdated=scenario%2?(scenario%3?1:300):0;
 initBitStream(&p.stream,(U8*)memory,sizeof(memory),Write,0,0);p.stream.byteAlignedMode=aligned;if(prefix)bsWriteBits(&p.stream,prefix,0);
 entity_SendInvUpdate(&s,&p);*bits=p.stream.bitLength;memcpy(out,memory,(*bits+7)/8);p.stream.mode=Read;p.stream.cursor.byte=prefix/8;p.stream.cursor.bit=prefix%8;
 entity_ReceiveInvUpdate(&d,&p);*end=bsGetCursorBitPosition(&p.stream);observed[0]=dest.observed_count;observed[1]=dest.auctionInvUpdated;observed[2]=source.auctionInvUpdated;observed[3]=types[0];observed[4]=indexes[0];memcpy(observed+5,dest.observations,sizeof(dest.observations));strcpy(text,dest.auctionInv?dest.auctionInv->text:"");
}
'''
 return code,functions

def auto(r):
 tag=r.scalar(2)
 return r.scalar([2,10,24,32][tag])
def qualify():
 src=texts();pins={p:q.sha(s.encode()) for p,s in src.items()}
 if json.loads((HERE/'update-source-pins.json').read_text())!=pins:raise ValueError('source pin mismatch')
 code,functions=generate(src);cases=[]
 with tempfile.TemporaryDirectory(prefix='coh-inv-update-') as td:
  td=Path(td);(td/'original.c').write_text(code);q.run(['cc','-std=c99','-O0','-fno-strict-aliasing','-shared','-fPIC','-w','-I'+str(q.ROOT/'native-android/include'),td/'original.c','-o',td/'original.so']);lib=C.CDLL(str(td/'original.so'))
  for aligned in (0,1):
   for prefix in (range(8) if not aligned else (0,8)):
    for scenario in range(36):
     raw=(C.c_uint8*16384)();bits=C.c_uint32();end=C.c_uint32();obs=(C.c_uint32*133)();text=C.create_string_buffer(1024);lib.update_fixture(scenario,aligned,prefix,raw,C.byref(bits),C.byref(end),obs,text)
     data=bytes(raw[:(bits.value+7)//8]);r=inv.independent.Reader(data,bits.value,aligned,prefix);count=r.packed(1);items=[]
     for _ in range(count):
      fields=[r.packed(5) for _ in range(4)];fields += [r.scalar(32) for _ in range(4)] if fields[0]==1 else [0]*4;items.append(fields)
     auction=auto(r);auction_text=r.string(1024).decode() if auction else ''
     assert r.cursor==bits.value==end.value and obs[0]==count and obs[1]==auction and list(obs[2:5])==[0,0,0] and auction_text==text.value.decode()
     assert items==[list(obs[5+i*8:13+i*8]) for i in range(count)]
     cases.append(dict(scenario=scenario,aligned=aligned,begin_bit=prefix,end_bit=end.value,wire_hex=data.hex(),expected={'items':items,'auction_updated':auction,'auction_text':auction_text}))
 return dict(schema='coh-inventory-update-source-oracle-v1',passed=True,source_pin=q.PIN,original_source_sha256_lf=pins,original_functions=functions,generated_source_sha256=q.sha(code.encode()),cases=cases,cases_count=len(cases),scope='whole original sender/consumer and auction wire wrappers; explicit inventory/auction text serialization and setter callbacks, no dictionary/text-parser application',auction_parser_semantics=False,dictionary_authority=False,original_oracle_sanitized=False,actor_publication=False,acknowledgments_enabled=False,android_executed=False)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--initialize-pins',action='store_true');a=p.parse_args()
 if a.initialize_pins:(HERE/'update-source-pins.json').write_text(json.dumps({p:q.sha(s.encode()) for p,s in texts().items()},indent=2)+'\n')
 result=qualify();a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'cases':result['cases_count']}))
