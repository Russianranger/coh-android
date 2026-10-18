"""Trusted complete command13 source fixtures; never an account service.

Whole direct DB sender, Queue relay and fresh-state Game consumer are extracted
without body edits. Bounded adapters provide objects/callback observations, not
catalog, entitlements, UI, original layouts or current runtime authority.
"""
from pathlib import Path
import ctypes as C
import hashlib
import importlib.util
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
FUNCTIONS = {
 'libs/UtilitiesLib/src/components/BitStream.c': [
  'initBitStream','bsWriteBits','bsReadBits','bsWriteBitsPack','bsReadBitsPack',
  'bsWriteString','bsReadStringAndLength','bsWriteBitsArray','bsReadBitsArray',
  'bsGetCursorBitPosition'],
 'libs/UtilitiesLib/src/network/net_packet.c': [
  'pktSendBits','pktGetBits','pktSendBitsPack','pktGetBitsPack','pktSendString',
  'pktGetStringAndLength','pktSendBitsArray','pktGetBitsArray','pktSetOrdered'],
 'libs/UtilitiesLib/src/network/net_packetutil.c': [
  'pktSendBitsAuto','pktGetBitsAuto','pktSendBitsAuto2','pktGetBitsAuto2'],
 'libs/UtilitiesLib/include/utilitieslib/network/net_packet_common.h': [
  'pktSendGetBits','pktSendGetBitsAuto','pktSendGetBitsAuto2',
  'pktSendGetStringNLength','pktSendGetBitsArray'],
 'Common/account/AccountTypes.cpp': ['skuIdIsNull'],
 'Common/account/AccountData.c': [
  'AccountInventorySendItem','AccountInventoryReceiveItem','AccountInventorySendReceive'],
 'DBServer/src/accountservercomm.c': ['accountInventoryRelayHelper','accountInventoryRelayToClient'],
 'QueueServer/src/QueueServer_Passthrough.c': ['passAccountServerInventoryDB'],
 'Game/src/clientcomm/dbclient.c': ['receiveAccountServerInventoryDB'],
}
AUDIT = [
 'Common/comm_backend.h','Common/account/AccountTypes.h','Common/account/AccountData.h',
 'Common/account/AccountCatalog.h','Common/account/AccountCatalog.c',
 'DBServer/src/container.h','AccountServer/src/AccountDb.cpp',
 'libs/UtilitiesLib/include/utilitieslib/stdtypes.h',
]


def digest(raw):
 return hashlib.sha256(raw).hexdigest()


def extract(source, name):
 match = re.search(r'^[\w \t*]+\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{', source, re.M)
 if not match:raise ValueError('missing inventory source function '+name)
 at=source.index('{',match.start());depth=0;mode='code'
 while at<len(source):
  c=source[at];pair=source[at:at+2]
  if mode=='code':
   if pair=='//':mode='line';at+=2;continue
   if pair=='/*':mode='comment';at+=2;continue
   if c in ('"',"'"):mode=c
   elif c=='{':depth+=1
   elif c=='}':
    depth-=1
    if not depth:return source[match.start():at+1]+'\n'
  elif mode=='line':
   if c=='\n':mode='code'
  elif mode=='comment':
   if pair=='*/':mode='code';at+=2;continue
  elif c=='\\':at+=2;continue
  elif c==mode:mode='code'
  at+=1
 raise ValueError('unclosed inventory source function')


def declaration(source, begin, end):
 at=source.index(begin)
 return source[at:source.index(end,at)+len(end)]+'\n'


def source_pins(root):
 sources={p:(Path(root)/'upstream/ouroboros'/p).read_bytes().replace(b'\r\n',b'\n')
          for p in dict.fromkeys([*FUNCTIONS,*AUDIT])}
 spans={n:extract(sources[p].decode(),n) for p,names in FUNCTIONS.items() for n in names}
 declarations={
  'SkuId':declaration(sources['Common/account/AccountTypes.h'].decode(),'typedef union SkuId {','} SkuId;'),
  'AccountInventory':declaration(sources['Common/account/AccountData.h'].decode(),'typedef struct AccountInventory\n','} AccountInventory;'),
  'AccountInventorySet':declaration(sources['Common/account/AccountData.h'].decode(),'typedef struct AccountInventorySet {','} AccountInventorySet;'),
  'ShardAccountInventoryItem':declaration(sources['DBServer/src/container.h'].decode(),'typedef struct ShardAccountInventoryItem {','} ShardAccountInventoryItem;'),
 }
 loyalty=re.findall(rb'^#define LOYALTY_BITS (\d+)$',sources['Common/account/AccountTypes.h'],re.M)
 if loyalty!=[b'128']:raise ValueError('source loyalty width')
 pins={'sha256_lf':{p:digest(b) for p,b in sources.items()},
       'functions_sha256_lf':{n:digest(s.encode()) for n,s in spans.items()},
       'declarations_sha256_lf':{n:digest(s.encode()) for n,s in declarations.items()},
       'loyalty_bits':128}
 return sources,spans,declarations,pins


def produce(root, work):
 root=Path(root);work=Path(work)
 sources,spans,declarations,pins=source_pins(root)
 if json.loads((HERE/'inventory-source-pins.json').read_bytes())!=pins:
  raise ValueError('original inventory source mismatch')
 # The caller admits this helper and prepare.py before this project execution.
 spec=importlib.util.spec_from_file_location('inventory_bits_fixture',root/'native-android/tools/protocol_fixture/prepare.py')
 helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
 pre=helper.PREAMBLE
 anchor='static void pktSendBitsAuto(Packet *p,unsigned int v){(void)p;(void)v;assert(0);}'
 if pre.count(anchor)!=1:raise ValueError('original preamble Auto anchor')
 pre=pre.replace(anchor,'')
 anchor='compress,ordered,ordered_id;} Packet;'
 if pre.count(anchor)!=1:raise ValueError('original preamble Packet anchor')
 pre=pre.replace(anchor,'compress,ordered,ordered_id,reliable;} Packet;')
 code=pre+r'''
typedef uint64_t U64;typedef int8_t bool;
_Static_assert(sizeof(U32)==4&&sizeof(U64)==8,"source wire widths");
_Static_assert(__BYTE_ORDER__==__ORDER_LITTLE_ENDIAN__,"original x86 Auto2 memory order");
#define THREADSAFE_STATIC static
#define THREADSAFE_STATIC_MARK(x)
#define AINRANGE(v,a) ((unsigned)(v)<sizeof(a)/sizeof(*(a)))
#define INLINEDBG inline
#define LOYALTY_BITS 128
static int g_bAssertOnBitStreamError;
static U32 bsTypedReadBits(BitStream*b,int n){(void)b;(void)n;assert(0);return 0;}
static void bsTypedWriteString(BitStream*b,const char*s){(void)b;(void)s;assert(0);}
static char *bsTypedReadStringAndLength(BitStream*b,int*n){(void)b;(void)n;assert(0);return NULL;}
static int bsTypedReadBitsArray(BitStream*b,int n,void*p){(void)b;(void)n;(void)p;assert(0);return 0;}
int auto_bins[]={2,10,24,32};
'''
 for path in list(FUNCTIONS)[:3]:
  for name in FUNCTIONS[path]:code+=spans[name]
 code+='\nvoid pktSendBitsArray(Packet*,int,const void*);\n#define pktGetString(p) pktGetStringAndLength((p),&(int){0})\n'
 for name in FUNCTIONS['libs/UtilitiesLib/include/utilitieslib/network/net_packet_common.h']:
  code+=spans[name]
 backend=sources['Common/comm_backend.h'].decode();at=backend.index('enum\n{\n    DBGAMESERVER_SEND_PLAYERS')
 code+='\nenum {COMM_MAX_CMD=2};\n'+backend[at:backend.index('\n};',at)+3]+'\n'
 for name,body in declarations.items():
  # Windows source long fields are 32 bits. Keep the original declaration
  # tokens, with a narrow wire-storage type adaptation on this host only.
  code+=('#define long int32_t\n'+body+'#undef long\n') if name=='AccountInventory' else body
 code+='\n_Static_assert(sizeof(((AccountInventory*)0)->granted_total)==4&&sizeof(((AccountInventory*)0)->claimed_total)==4,"Win32 source scalar storage only");\n'
 code+=r'''
/* Only explicitly accessed DB container members. Not original object ABI. */
typedef struct {
 ShardAccountInventoryItem **inventory;U8 loyaltyStatus[LOYALTY_BITS/8];
 int loyaltyPointsUnspent,loyaltyPointsEarned,slot_count;U32 accountStatusFlags;
} ShardAccountCon;
typedef struct {int unused;} GameClientLink;
typedef struct {int unused;} Entity;
static struct {char *shard_name;} server_cfg;
static struct {
 bool accountInformationAuthoritative;U32 shardXferFreeOnly,shardXferTokens;
 char shardname[101];U32 accountInformationCacheTime;
 AccountInventorySet account_inventory;U8 loyaltyStatus[LOYALTY_BITS/8];
 U32 loyaltyPointsUnspent,loyaltyPointsEarned,virtualCurrencyBal,lastEmailTime,lastNumEmailsSent,bonus_slots;
} db_info;
static U32 storage[32770];static Packet packet;static NetLink link;
static GameClientLink game_client;static ShardAccountCon container;
static ShardAccountInventoryItem source_items[1027],*source_rows[1027];
static AccountInventory *client_rows[1027];
static unsigned source_count,client_count,removed,sends,ordered_calls,release_calls,sort_calls;
static unsigned aligned,legacy,nonzero_padding,padding_start,padding_bits;
static unsigned client_player_queries,item_sends;
static char shard[16385];static U32 tail_values[7];static void *shardaccounts_list=&container;
static void *containerPtr(void *list,U32 id){assert(list==shardaccounts_list&&id==42);return &container;}
static NetLink *findLinkToClient(U32 id,bool *direct,int *dbid){assert(id==42);*direct=1;*dbid=77;return &link;}
static GameClientLink *dbClient_getGameClient(U32 id,NetLink*l){assert(id==42&&l==&link);return &game_client;}
static Packet *dbClient_createPacket(U32 command,GameClientLink*c){
 assert(c==&game_client);memset(storage,0,sizeof(storage));memset(&packet,0,sizeof(packet));
 initBitStream(&packet.stream,(U8*)storage,sizeof(storage)-16,Write,aligned,0);
 pktSendBitsPack(&packet,1,command+(legacy?5:0));return &packet;
}
static Packet *accountInventoryStartRelayThroughMapserver(NetLink*l,bool check,int id,int auth){
 (void)l;(void)check;(void)id;(void)auth;assert(0);return NULL;
}
static void pktSend(Packet **p,NetLink*l){assert(*p==&packet&&l==&link);sends++;*p=NULL;}
static int eaSize(ShardAccountInventoryItem ***p){assert(p==&container.inventory);return (int)source_count;}
static void eaRemoveAndDestroy(ShardAccountInventoryItem ***p,int index,void *destroy){
 assert(p==&container.inventory&&index>=0&&(unsigned)index<source_count&&!destroy);
 memmove(source_rows+index,source_rows+index+1,(source_count-(unsigned)index-1)*sizeof(*source_rows));source_count--;removed++;
}
static void eaPush(AccountInventory ***p,AccountInventory *item){
 assert(p==&db_info.account_inventory.invArr&&client_count<1027&&item);
 client_rows[client_count++]=item;*p=client_rows;
}
static void AccountInventorySet_Release(AccountInventorySet *set){
 assert(set==&db_info.account_inventory);for(unsigned i=0;i<client_count;i++)free(client_rows[i]);
 client_count=0;set->invArr=NULL;release_calls++;
}
static void AccountInventorySet_Sort(AccountInventorySet *set){assert(set==&db_info.account_inventory);sort_calls++;}
#define accountCatalogValidateSkuId(sku_id) do {} while(0,0)
static Entity *playerPtr(void){client_player_queries++;return NULL;}
static U32 timerSecondsSince2000(void){return 1234;}
static void costumereward_clear(int x){(void)x;assert(0);}
static void costumeAwardAuthParts(Entity*e){(void)e;assert(0);}
static void costumeAwardPowersetParts(Entity*e,int x,int y){(void)e;(void)x;(void)y;assert(0);}
static int getPCCEditingMode(void){assert(0);return 0;}
'''
 # Record source alignment without editing its function body; the controlled
 # nonzero-pad variant changes only bits the original array reader discards.
 # The already extracted packet-array function is renamed by the preprocessor
 # in the completed source below, then this wrapper observes its call sites.
 array_body=spans['pktSendBitsArray']
 if code.count(array_body)!=1:raise ValueError('array wrapper source anchor')
 code=code.replace(array_body,'#define pktSendBitsArray original_inventory_pktSendBitsArray\n'+array_body+'#undef pktSendBitsArray\n',1)
 code+=r'''
void pktSendBitsArray(Packet*p,int bits,const void*data){
 assert(bits==128);padding_start=bsGetCursorBitPosition(&p->stream);padding_bits=(8-(padding_start&7))&7;
 original_inventory_pktSendBitsArray(p,bits,data);
 if(nonzero_padding)for(unsigned i=0;i<padding_bits;i++)p->stream.data[(padding_start+i)>>3]|=(U8)(1u<<((padding_start+i)&7));
}
'''
 code+=spans['skuIdIsNull']
 for name in FUNCTIONS['Common/account/AccountData.c']:code+=spans[name]
 for name in FUNCTIONS['DBServer/src/accountservercomm.c']:code+=spans[name]
 code+=spans['passAccountServerInventoryDB']+spans['receiveAccountServerInventoryDB']
 code+=r'''
void original_inventory(unsigned profile,unsigned old,unsigned count,unsigned authoritative,
 unsigned free_only,unsigned shard_length,unsigned pad_variant,unsigned cleanup_variant,
 U8*out,U32*bits,U32*pad_start,U32*pad_count){
 assert(profile<=1&&old<=1&&count<=1025&&authoritative<=1&&free_only<=1&&shard_length<=16384);
 assert(client_count==0);aligned=profile;legacy=old;nonzero_padding=pad_variant;
 source_count=count;removed=sends=release_calls=sort_calls=client_player_queries=0;
 memset(&container,0,sizeof(container));memset(source_items,0,sizeof(source_items));
 memset(source_rows,0,sizeof(source_rows));memset(&db_info,0,sizeof(db_info));
 U32 values[]={0,3,1023,16777215,0xffffffff};
 for(unsigned i=0;i<count;i++){
  char sku[9];int size=snprintf(sku,sizeof(sku),"F%07u",i+1);assert(size==8);
  memcpy(source_items[i].sku_id.c,sku,8);source_items[i].granted_total=(int)values[i%5];
  source_items[i].claimed_total=(int)values[(i+1)%5];source_items[i].expires=values[(i+2)%5];
  source_rows[i]=source_items+i;
 }
 if(cleanup_variant){assert(count==3);source_rows[source_count++]=NULL;source_rows[source_count++]=source_items+1026;}
 container.inventory=source_rows;
 for(unsigned i=0;i<16;i++)container.loyaltyStatus[i]=(U8)(0x81u+i*13u);
 container.loyaltyPointsUnspent=(int)values[0];container.loyaltyPointsEarned=(int)values[1];
 container.accountStatusFlags=values[2];container.slot_count=(int)values[3];
 tail_values[0]=values[0];tail_values[1]=values[1];tail_values[2]=values[2];tail_values[3]=values[3];
 tail_values[4]=values[4];tail_values[5]=container.accountStatusFlags;tail_values[6]=(U32)container.slot_count;
 for(unsigned i=0;i<shard_length;i++)shard[i]='s';shard[shard_length]=0;server_cfg.shard_name=shard;
 /* Whole actual direct dispatch and helper, with unchanged field order. */
 accountInventoryRelayToClient(42,1023,free_only,(int)tail_values[2],tail_values[3],tail_values[4],authoritative);
 assert(sends==1&&packet.ordered==1&&packet.reliable==1&&source_count==count&&removed==(cleanup_variant?2u:0u));
 assert(!packet.stream.errorFlags);*bits=packet.stream.bitLength;assert(*bits<=131072u*8u);
 *pad_start=padding_start;*pad_count=padding_bits;memcpy(out,storage,(*bits+7)/8);
 Packet input=packet;input.stream.mode=Read;input.stream.cursor.byte=input.stream.cursor.bit=0;
 U32 command=pktGetBitsPack(&input,1)-(old?5:0);assert(command==DBGAMESERVER_ACCOUNTSERVER_INVENTORY);
 receiveAccountServerInventoryDB(&input);
 assert(!input.stream.errorFlags&&bsGetCursorBitPosition(&input.stream)==*bits);
 assert(client_player_queries==1&&release_calls==1&&sort_calls==1&&client_count==count);
 assert(db_info.accountInformationAuthoritative==(bool)authoritative&&db_info.shardXferFreeOnly==free_only&&db_info.shardXferTokens==1023);
 assert(db_info.accountInformationCacheTime==(authoritative?0u:1234u));
 assert(!memcmp(db_info.loyaltyStatus,container.loyaltyStatus,16));
 assert(db_info.loyaltyPointsUnspent==tail_values[0]&&db_info.loyaltyPointsEarned==tail_values[1]&&
  db_info.virtualCurrencyBal==tail_values[2]&&db_info.lastEmailTime==tail_values[3]&&
  db_info.lastNumEmailsSent==tail_values[4]&&db_info.account_inventory.accountStatusFlags==tail_values[5]&&db_info.bonus_slots==tail_values[6]);
 for(unsigned i=0;i<count;i++){
  assert(client_rows[i]->sku_id.u64==source_items[i].sku_id.u64);
  assert((U32)client_rows[i]->granted_total==(U32)source_items[i].granted_total);
  assert((U32)client_rows[i]->claimed_total==(U32)source_items[i].claimed_total&&client_rows[i]->expires==source_items[i].expires);
 }
 AccountInventorySet_Release(&db_info.account_inventory);assert(client_count==0);
 /* Whole Queue relay roundtrip. Canonical sender padding is zero; the
  * deliberately altered ignored padding is allowed to be canonicalized. */
 input=packet;input.stream.mode=Read;input.stream.cursor.byte=input.stream.cursor.bit=0;pktGetBitsPack(&input,1);
 U32 relay_storage[32770]={0};Packet relay={0};initBitStream(&relay.stream,(U8*)relay_storage,sizeof(relay_storage)-16,Write,profile,0);
 pktSendBitsPack(&relay,1,command+(old?5:0));nonzero_padding=0;passAccountServerInventoryDB(&input,&relay);
 assert(!input.stream.errorFlags&&!relay.stream.errorFlags&&bsGetCursorBitPosition(&input.stream)==*bits&&relay.stream.bitLength==*bits);
 assert(padding_start==*pad_start&&padding_bits==*pad_count);
 for(unsigned i=0;i<(*bits+7)/8;i++){
  U8 expected=out[i];for(unsigned j=0;j<*pad_count;j++)if(((*pad_start+j)>>3)==i)expected&=(U8)~(1u<<((*pad_start+j)&7));
  assert(((U8*)relay_storage)[i]==expected);
 }
 /* Item send and receive are independently exact original functions too. */
 if(count){
  U32 memory[64]={0};Packet item={0};initBitStream(&item.stream,(U8*)memory,sizeof(memory)-16,Write,profile,0);
  AccountInventory value={0};value.sku_id=source_items[0].sku_id;value.granted_total=source_items[0].granted_total;
  value.claimed_total=source_items[0].claimed_total;value.expires=source_items[0].expires;AccountInventorySendItem(&item,&value);
  item.stream.mode=Read;item.stream.cursor.byte=item.stream.cursor.bit=0;AccountInventory decoded={0};AccountInventoryReceiveItem(&item,&decoded);
  assert(!item.stream.errorFlags&&bsGetCursorBitPosition(&item.stream)==item.stream.bitLength&&decoded.sku_id.u64==value.sku_id.u64);
  assert((U32)decoded.granted_total==(U32)value.granted_total&&(U32)decoded.claimed_total==(U32)value.claimed_total&&decoded.expires==value.expires);
 }
}
'''
 source=work/'inventory-original.c';library=work/'inventory-original.so';source.write_text(code)
 built=subprocess.run(['cc','-std=c11','-O0','-shared','-fPIC','-w','-I'+str(root/'native-android/include'),str(source),'-o',str(library)],capture_output=True,text=True,timeout=120)
 if built.returncode:raise ValueError(built.stderr)
 lib=C.CDLL(str(library));lib.original_inventory.argtypes=[C.c_uint]*8+[C.c_void_p]+[C.POINTER(C.c_uint32)]*3
 configs=[]
 for items in (0,1,3):
  for authoritative in (0,1):
   for free_only in (0,1):configs.append((items,authoritative,free_only,7,0,0))
 configs += [(1024,0,0,0,0,0),(1025,0,1,0,0,0),(0,0,0,16383,0,0),
             (1,1,1,16384,0,0),(3,0,1,7,1,0),(3,1,0,7,0,1)]
 cases=[];header='/* Complete source-written command13; only labeled ignored padding is controlled. */\n'
 pad_variants=0;cleanup_controls=0
 for aligned in (0,1):
  for legacy in (0,1):
   for items,authoritative,free_only,length,pad,cleanup in configs:
    data=(C.c_uint8*131072)();bits=C.c_uint32();start=C.c_uint32();count=C.c_uint32()
    lib.original_inventory(aligned,legacy,items,authoritative,free_only,length,pad,cleanup,data,C.byref(bits),C.byref(start),C.byref(count))
    raw=bytes(data[:(bits.value+7)//8]);name='inventory_'+str(len(cases))
    header+='static const uint8_t '+name+'[]={'+','.join(map(str,raw))+'};\n'
    cases.append((name,bits.value,aligned,legacy,items,authoritative,free_only,length+1,start.value,count.value))
    pad_variants+=bool(pad and count.value);cleanup_controls+=bool(cleanup)
 header+='static const struct {const uint8_t*data;size_t bits;unsigned aligned,legacy,items,authoritative,free_only,shard_bytes,padding_start,padding_bits;} inventory_fixtures[]={\n'
 header+=''.join('{'+name+','+','.join(map(str,fields))+'},\n' for name,*fields in cases)+'};\n'
 (work/'inventory-fixtures.h').write_text(header)
 return {'whole_source_sha256_lf':pins['sha256_lf'],'whole_function_sha256_lf':pins['functions_sha256_lf'],
  'original_declarations_sha256_lf':pins['declarations_sha256_lf'],'fixtures':len(cases),
  'complete_original_direct_db_sender_executed':True,'complete_original_item_send_receive_executed':True,
  'complete_original_queue_and_fresh_state_game_consumer_executed':True,
  'original_loyalty_array_alignment_executed':True,'controlled_nonzero_ignored_padding_fixtures':pad_variants,
  'original_null_and_null_sku_filter_controls':cleanup_controls,
  'previous_authoritative_game_state_assumed_false':True,'map_route_executed':False,
  'catalog_validation_release_noop':True,'host_member_subset_storage_only':True,
  'source_win32_long_fields_adapted_to_explicit_int32_storage':True,
  'original_win32_layout_qualified':False,'client_earray_sort_and_ui_operations_stubbed':True,
  'original_unsafe_code_trusted_padded_complete_fixtures_only':True,
  'generated_source_sha256':digest(code.encode()),'generated_header_sha256':digest(header.encode()),
  'oracle_elf_sha256':digest(library.read_bytes()),'actual_packet_body_values_inferred':False,
  'real_account_db_ui_services':False,'source_generation_admitted':False,'world_authority':False}
