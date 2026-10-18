"""Whole original Details/InvBaseDetail readers and fresh inventory finalization.
Extends the frozen Salvage reader provider; no old qualifier entrypoint runs.
"""
import ctypes as C,hashlib,json,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['Common/entity/character_inventory.c','Common/entity/character_inventory.h','Common/entity/character_net.c','Common/bases/basedata.c','Common/bases/basedata.h']
def sha(b):return hashlib.sha256(b).hexdigest()
LOCKED={}
def module(n,p):
 p=p.resolve();b=p.read_bytes()
 if LOCKED.get(p)!=sha(b):raise ValueError('unadmitted BaseDetail source provider')
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(b,str(p),'exec'),m.__dict__);return m

def build(root,work):
 pins=json.loads((HERE/'basedetail-inventory-source-pins.json').read_bytes())
 if set(pins)!={'source_sha256_raw','helper_sha256_raw','scope'}:raise ValueError('BaseDetail manifest shape')
 for p,d in pins['source_sha256_raw'].items():
  if sha((root/'upstream/ouroboros'/p).read_bytes())!=d:raise ValueError('BaseDetail original source differs')
 for p,d in pins['helper_sha256_raw'].items():
  q=(root/p).resolve()
  if sha(q.read_bytes())!=d:raise ValueError('BaseDetail provider differs')
  LOCKED[q]=d
 prior=module('basedetail_salvage',HERE/'salvage_oracle.py');prior.module=module;tmp=work/'salvage';tmp.mkdir();_,base=prior.build(root,tmp);code=(tmp/'original-salvage.c').read_text()
 # The prior builder supplies compiled functions, not its prior wrapper's
 # execution. This new entrypoint reads Details/IDs and executes generic hashes;
 # it never calls original_salvage, its getters, link observer or chareval.
 inherited=('CLIENT_chareval_body_executed_as_noop','ordinary_source_getters_executed','serialized_workshop_text_observed_at_original_link_ReadPascalString_boundary')
 base['prior_wrapper_capabilities_not_executed_here']={k:base.pop(k) for k in inherited}
 base['prior_original_salvage_entrypoint_executed']=False
 # Explicit host layout adapters preserve the original generic prefix. Parser
 # table member offsets are computed after these declarations, never raw ABI.
 a='typedef struct Detail{const char *pchName';b='typedef struct Detail{int id;const char *pchName'
 if code.count(a)!=1:raise ValueError('Details prefix adapter')
 code=code.replace(a,b)
 a='typedef struct{const Detail**ppDetails;}DetailDict;';b='typedef struct{const Detail**ppDetails;cStashTable haItemNames;const Detail**itemsById;}DetailDict;'
 if code.count(a)!=1:raise ValueError('Details dictionary prefix adapter')
 code=code.replace(a,b).replace('assert(kind==0);return &original_attrs;','assert(kind==0||kind==3);return &original_attrs;')
 src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n') for p in EXTRA};functions={};witnesses={}
 def f(p,n):
  body=prior.extract(src[p],n);functions[p+':'+n]=sha(body.encode());return body
 code+='\n#include "coh_basedetail_inventory.h"\n'
 for name in ('GenericInventoryType','GenericInvDictionary'):
  code+=re.search(r'typedef struct '+name+r'\s*\{.*?}\s*'+name+';',src[EXTRA[1]],re.S).group()+'\n'
 code+='''
#define assertmsg(x,msg) assert(x)
#define cpp_reinterpret_cast(t) (t)
#define STATIC_INFUNC_ASSERT(x) _Static_assert(x,"source inventory count")
#define INRANGE(x,a,b) ((x)>=(a)&&(x)<(b))
typedef int InventoryType;
#define kInventoryType_Concept 1
#define kInventoryType_Recipe 2
#define kInventoryType_BaseDetail 3
#define kInventoryType_StoredSalvage 4
#define kInventoryType_Count 5
static GenericInvDictionary g_ConceptDict,g_DetailRecipeDict;
static void eaSetForced(void*out,const void*p,int i){Vec*v=(Vec*)((char*)*(void***)out - offsetof(Vec,items));assert(i>=0&&i<8192);if(i>=v->capacity){unsigned cap=(unsigned)i+1;Vec*n=vector(cap,(unsigned)v->size);memcpy(n->items,v->items,(size_t)v->size*sizeof(void*));v=n;*(void***)out=v->items;}if(i>=v->size)v->size=i+1;v->items[i]=(void*)p;}
'''
 for n in ('genericinvdict_CreateHashes','basedetail_CreateDetailInvHashes','inventorytype_Valid','GetItemsByIdArrayRef','detail_GetItem'):code+=f(EXTRA[0],n)
 for p,names in ((EXTRA[0],('character_SetInventory','s_GetInvAndItem','character_GetInvHandleByType','character_GetInvInfo','attribfiledict_FinalProcess')),(EXTRA[2],('character_inventory_Receive','character_ReceiveInventories'))):
  for n in names:witnesses[p+':'+n]=sha(prior.extract(src[p],n).encode())
 code+='''
static CohSalvageText bd_copy(CohBaseDetailInventory*out,const char*s){assert(s);unsigned n=strlen(s);assert(n+1<=COH_BASEDETAIL_TEXT_MAX-out->text_bytes);CohSalvageText t={out->text_bytes,n};memcpy(out->text+t.offset,s,n+1);out->text_bytes+=n+1;return t;}
int original_basedetail(const unsigned char*defs,unsigned dn,unsigned dbegin,const unsigned char*ids,unsigned in,unsigned ibegin,CohBaseDetailInventory*out,unsigned char*dr,unsigned char*ir){
 reset();memset(&original_attrs,0,sizeof(original_attrs));memset(&g_DetailDict,0,sizeof(g_DetailDict));memset(out,0,sizeof(*out));SimpleBuffer*d=alloc(sizeof(*d)),*a=alloc(sizeof(*a)),*dw=alloc(sizeof(*dw)),*iw=alloc(sizeof(*iw));assert(dn<=1048576&&in<=1048576);memcpy(d->data,defs,dn);d->filesize=dn;d->curposition=dbegin;memcpy(a->data,ids,in);a->filesize=in;a->curposition=ibegin;int sum=0;
 assert(ParserReadBinaryTable(d,ParseDetailDict,&g_DetailDict,&sum)&&d->curposition==(int)dn);assert(ParserReadBinaryTable(a,ParseAttributeItems,&original_attrs,&sum)&&a->curposition==(int)in);
 dw->curposition=dw->filesize=dbegin;memcpy(dw->data,defs,dbegin);iw->curposition=iw->filesize=ibegin;memcpy(iw->data,ids,ibegin);assert(ParserWriteBinaryTable(dw,ParseDetailDict,&g_DetailDict,&sum,0,0)&&dw->filesize==(int)dn);assert(ParserWriteBinaryTable(iw,ParseAttributeItems,&original_attrs,&sum,0,0)&&iw->filesize==(int)in);memcpy(dr,dw->data,dn);memcpy(ir,iw->data,in);
 Vec*dv=(Vec*)g_DetailDict.ppDetails,*av=(Vec*)original_attrs.ppAttribItems;if(!dv)dv=vector(0,0);if(!av)av=vector(0,0);g_DetailDict.ppDetails=(const Detail**)dv->items;original_attrs.ppAttribItems=(const AttribFileItem**)av->items;int ok=attribfiledict_FinalProcess(NULL,&original_attrs,0);basedetail_CreateDetailInvHashes(&g_DetailDict,0);out->count=dv->size;out->id_count=av->size;out->max_id=original_attrs.maxId;out->slot_count=eaSize(&g_DetailDict.itemsById);
 for(unsigned i=0;i<out->count;i++){const Detail*p=dv->items[i];CohBaseDetailIdentity*t=&out->entries[i];t->name=bd_copy(out,p->pchName);t->id=p->id;t->active=detail_GetItem(p->pchName)==p;out->active_count+=t->active;}
 for(unsigned i=0;i<out->id_count;i++){const AttribFileItem*p=av->items[i];out->id_rows[i].id=p->id;out->id_rows[i].name=bd_copy(out,p->name);}
 const GenericInventoryType*const**ref=GetItemsByIdArrayRef(kInventoryType_BaseDetail);assert((const void*)*ref==(const void*)g_DetailDict.itemsById);
 for(unsigned id=0;id<out->slot_count;id++){const Detail*p=(const Detail*)(*ref)[id];if(p){assert(p->id==(int)id);unsigned i;for(i=0;i<out->count;i++)if(dv->items[i]==p)break;assert(i<out->count);out->slots[id]=i+1;}}
 reset();memset(&g_DetailDict,0,sizeof(g_DetailDict));return ok;
}
size_t original_basedetail_sizeof(void){return sizeof(CohBaseDetailInventory);}
'''
 path=work/'original-basedetail.c';path.write_text(code)
 for p,d in pins['helper_sha256_raw'].items():
  if sha((root/p).read_bytes())!=d:raise ValueError('BaseDetail helper changed')
 subprocess.run(['cc','-std=gnu11','-O0','-w','-shared','-fPIC','-I'+str(HERE),'-I'+str(HERE/'../costume-inputs'),path,'-lz','-o',work/'original-basedetail.so'],check=True)
 lib=C.CDLL(str(work/'original-basedetail.so'));lib.original_basedetail.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_void_p,C.c_void_p];lib.original_basedetail.restype=C.c_int;lib.original_basedetail_sizeof.restype=C.c_size_t
 return lib,{'schema':'coh-basedetail-original-source-v1','source_admission_manifest':pins,'provider':base,'whole_function_sha256_lf':functions,'unexecuted_receive_source_witnesses_sha256_lf':witnesses,'generated_source_sha256':sha(code.encode()),'fresh_generic_prefix_host_layout_adapter':True,'original_stash_allocator':False,'original_shared_memory_branch':False,'original_oracle_sanitized':False,'Details_gameplay_finalizers':False,'source_packet_dispatcher_executed':False}
