"""Original dynamic power-defines/class CRC prototype. Never runtime admission."""
import ctypes as C,hashlib,re,subprocess,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXTRA=['libs/UtilitiesLib/src/utils/structDefines.c','libs/UtilitiesLib/include/utilitieslib/utils/structDefines.h','Common/entity/attrib_names.h','Common/entity/powers_load.c']
def sha(b):return hashlib.sha256(b).hexdigest()
def module(n,p):
 m=types.ModuleType(n);m.__file__=str(p);exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def build(root,work,seq_root,rows):
 classes=module('define_classes',HERE/'classes_oracle.py');classes.module=module;small=module('define_small',HERE/'../costume-inputs/oracle.py');stash=module('define_stash',HERE/'../stash32/oracle.py');cw=work/'classes';sw=work/'stash';cw.mkdir();sw.mkdir();_,cp=classes.build(root,cw);_,sp=stash.build(root,sw);code=(cw/'original-classes.c').read_text();st=(sw/'original.c').read_text().replace('allocations','stash_allocations');src={p:(root/'upstream/ouroboros'/p).read_text().replace('\r\n','\n')for p in EXTRA+['Common/entity/load_def.c','Common/entity/character_attribs.h','libs/UtilitiesLib/src/components/StashTable.c','libs/UtilitiesLib/include/utilitieslib/components/StashTable.h','libs/UtilitiesLib/src/utils/textparser.c']};functions={}
 def f(path,name):
  body=small.extract(src[path],name);functions[path+':'+name]=sha(body.encode());return body
 sh=src[EXTRA[1]];definitions=sh[sh.index('typedef struct DefineList'):sh.index('DefineContext* DefineCreate();')]+sh[sh.index('#define DM_END'):sh.index('// all lookups')]
 definitions=definitions.replace('U32_TO_PTR','U32_TO_PTR')
 code=code.replace('typedef void DefineContext;','typedef struct DefineContext DefineContext;\n#define U32_TO_PTR(v) ((void*)(uintptr_t)(U32)(v))\n#define PTR_TO_S32(v) ((int32_t)(intptr_t)(v))\n'+definitions)
 code=code.replace('static void UpdateCrcFromStaticDefines(void*p){(void)p;assert(0);}','static void UpdateCrcFromStaticDefines(StaticDefine*);').replace('static void UpdateCrcFromDefineList(void*p){(void)p;assert(0);}','void UpdateCrcFromDefineList(DefineContext*);')
 parser_header=(root/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/textparser.h').read_text()
 code=code.replace('size_t offDefiantHitPointsAttrib;','U32 offDefiantHitPointsAttrib;')
 code=code.replace('#define TOK_F32(s,m,d) TOK_F32_X,offsetof(s,m),((d)==1.0f?0x3f800000:0)','typedef uint64_t U64;\n#define SIZEOF2(s,m) sizeof(((s*)0)->m)\n'+next(line for line in parser_header.splitlines()if line.startswith('#define TOK_F32(')))
 code=code.replace('#define TOK_AUTOINT(s,m,d) TOK_INT(s,m,d)',next(line for line in parser_header.splitlines()if line.startswith('#define TOK_AUTOINT(')))
 code=code.replace('typedef void*cStashTable;','typedef const struct StashTableImp*cStashTable;')
 boolenum=re.search(r'StaticDefineInt BoolEnum\[\]\s*=.*?\n};',src[EXTRA[3]],re.S).group();code=code.replace('static ParseTable*ParsePowerDefines[1];static ParseTable*BoolEnum[1];','DefineContext*g_pParsePowerDefines=NULL;\nSTATIC_DEFINE_WRAPPER(ParsePowerDefines,g_pParsePowerDefines);\n'+boolenum)
 code=code.replace('case TOK_INT_X:case TOK_F32_X:case TOK_BOOLFLAG_X:return(CrcHandler)','case TOK_BOOL_X:case TOK_INT_X:case TOK_F32_X:case TOK_BOOLFLAG_X:return(CrcHandler)').replace('case TOK_START:case TOK_END:return(CrcHandler)','case TOK_POINTER_X:return(CrcHandler){pointer_interpretfield};case TOK_START:case TOK_END:return(CrcHandler)')
 at=code.index('typedef struct{ParseInfoFieldUsage(*interpretfield)');code=code[:at]+f('libs/UtilitiesLib/src/utils/textparser.c','pointer_interpretfield')+code[at:]
 # Original stash functions retain32-bit ub4 arithmetic. StringTable only stores
 # copies; fixture adapter does not choose hash slots or insertion order.
 st=st.replace('static void*strTableAddString(void*a,const void*b){(void)a;(void)b;assert(0);return NULL;}','static void*strTableAddString(void*a,const void*b){(void)a;char*s=strdup(b);assert(s);return s;}')
 code+='\n#undef bool\n'+st+'\n#undef calloc\n'
 stashh=src['libs/UtilitiesLib/include/utilitieslib/components/StashTable.h'];code+='\n'+re.search(r'#define STASH_DEEP_COPY_KEY_NAMES_BIT.*?} StashTableMode;',stashh,re.S).group()
 code+='''
typedef StashTableImp*StashTable;typedef StashElementImp*StashElement;typedef const StashElementImp*cStashElement;
#define onlyfulldebugdevassert(x) assert(x)
#define Indexable 0
#define WideString 1
static void*createStringTable(void){return(void*)1;}
static void initStringTable(void*p,int n){(void)p;(void)n;}
static void strTableSetMode(void*p,int n){(void)p;(void)n;}
static int isSharedMemory(const void*p){(void)p;assert(0);return 0;}
typedef struct{StashTable pTable;U32 uiIndex;}StashTableIterator;
typedef int(*StashElementProcessor)(StashElement);
'''
 sc='libs/UtilitiesLib/src/components/StashTable.c';code+='\n'+''.join(f(sc,n)for n in('stashSetMode','getKeyLength','stashTableCreateEx','stashTableCreateWithStringKeysEx','stashAddPointer','stashElementGetPointer','stashElementGetStringKey','stashGetIterator','stashNextElement','stashGetNextElement','stashForEachElement'))
 code+='\nstatic StashTable stashTableCreateWithStringKeys(unsigned n,StashTableMode mode){assert(n==100&&mode==StashDeepCopyKeys);return stashTableCreateWithStringKeysEx(n,mode,"define-fixture",0);}\n#define _strdup strdup\n#define SAFESTR(x) x,sizeof(x)\n#define sprintf_s snprintf\n'
 definec=src[EXTRA[0]];code+='\n'+re.search(r'typedef struct DefineContext\s*\{.*?} DefineContext;',definec,re.S).group()+'\nvoid DefineAdd(DefineContext*,const char*,const char*);\nvoid DefineAddIntList(DefineContext*,DefineIntList*);\n'
 code+='\n'+''.join(f(EXTRA[0],n)for n in('DefineCreate','DefineCreateFromIntList','DefineAddIntList'))
 code+='\n#define DefineAdd source_DefineAdd\n'+f(EXTRA[0],'DefineAdd')+'\n#undef DefineAdd\n'
 code+='''
static unsigned char define_trace[262144];static unsigned trace_bytes,trace_attempts;
static void emit_word(unsigned char*p,unsigned v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
void DefineAdd(DefineContext*c,const char*k,const char*v){unsigned kn=strlen(k),vn=strlen(v);assert(trace_bytes+8+kn+vn<=sizeof(define_trace));emit_word(define_trace+trace_bytes,kn);emit_word(define_trace+trace_bytes+4,vn);trace_bytes+=8;memcpy(define_trace+trace_bytes,k,kn);trace_bytes+=kn;memcpy(define_trace+trace_bytes,v,vn);trace_bytes+=vn;trace_attempts++;source_DefineAdd(c,k,v);}
unsigned original_define_trace(unsigned char*out,unsigned capacity){assert(capacity>=trace_bytes);memcpy(out,define_trace,trace_bytes);return trace_bytes;}
unsigned original_define_slots(unsigned char*out,unsigned capacity){assert(g_pParsePowerDefines);StashTable t=g_pParsePowerDefines->hash;unsigned at=0;assert(capacity>=8);emit_word(out,t->uiMaxSize);emit_word(out+4,t->uiValidValues);at=8;for(unsigned i=0;i<t->uiMaxSize;i++){StashElement e=&t->pStorage[i];unsigned present=!slotEmpty(e)&&!slotDeleted(e);assert(at+4<=capacity);emit_word(out+at,present);at+=4;if(present){const char*k=e->key.pKey,*v=e->value.pValue;unsigned kn=strlen(k),vn=strlen(v);assert(at+8+kn+vn<=capacity);emit_word(out+at,kn);emit_word(out+at+4,vn);at+=8;memcpy(out+at,k,kn);at+=kn;memcpy(out+at,v,vn);at+=vn;}}return at;}
void original_define_finish(void){if(g_pParsePowerDefines){StashTable t=g_pParsePowerDefines->hash;for(unsigned i=0;i<t->uiMaxSize;i++){StashElement e=&t->pStorage[i];if(!slotEmpty(e)&&!slotDeleted(e)){free(e->key.pKey);free(e->value.pValue);}}free(t->pStorage);free(t);free(g_pParsePowerDefines);g_pParsePowerDefines=NULL;}reset();}
'''
 code+='\n'+''.join(f(EXTRA[0],n)for n in('UpdateCrcFromDefineElement','UpdateCrcFromDefineList'))
 code+='\n'+f('libs/UtilitiesLib/src/utils/textparser.c','UpdateCrcFromStaticDefines')
 attrs=src['Common/entity/character_attribs.h'];code+='\n'+re.search(r'typedef enum ESpecialAttrib\s*\{.*?} ESpecialAttrib;',attrs,re.S).group();load=src['Common/entity/load_def.c'];code+='\n'+re.search(r'static DefineIntList s_PowerEnums\[\]\s*=.*?\n};',load,re.S).group()
 ah=src[EXTRA[2]]
 for name in('AttribName','AttribNames'):code+='\n'+re.search(r'typedef struct '+name+r'\b.*?} '+name+';',ah,re.S).group()
 for name in('ParseAttribName','ParseAttribNames'):code+='\n'+re.search(r'TokenizerParseInfo '+name+r'\[\]\s*=.*?\n};',ah,re.S).group()
 seqh=(seq_root/'upstream/ouroboros/Common/seq/seqstate.h').read_text();code+='\n'+seqh[seqh.index('typedef struct StateBit {'):seqh.index('} StateBit;')+11]+'\nextern StateBit stateBits[];\nunsigned original_state_count(void);int seqGetStateNumberFromName(char*);\n#define g_MaxUsedStates original_state_count()\n#define storeoffset offset\nstatic AttribNames g_AttribNames;static CharacterOrigins g_CharacterOrigins;\n'
 code+='\n'+''.join(f('Common/entity/load_def.c',n)for n in('AddSequencerDefines','AddAttributeDefines','AddAttribNames'))
 code+='''
unsigned original_names_roundtrip(const unsigned char*input,unsigned size,unsigned begin,unsigned char*out){SimpleBuffer*in=calloc(1,sizeof(*in)),*wr=calloc(1,sizeof(*wr));assert(in&&wr&&size<=65536);AttribNames data={0};int sum=0;reset();memcpy(in->data,input,size);in->filesize=size;in->curposition=begin;assert(ParserReadBinaryTable(in,ParseAttribNames,&data,&sum)&&in->curposition==(int)size);memcpy(wr->data,input,begin);wr->curposition=wr->filesize=begin;sum=0;assert(ParserWriteBinaryTable(wr,ParseAttribNames,&data,&sum,0,0));unsigned n=wr->filesize;memcpy(out,wr->data,n);free(in);free(wr);reset();return n;}
unsigned original_names_crc(void){return ParseTableCRC(ParseAttribNames,NULL);}
unsigned original_define_crc_only(void){cryptAdler32Init();UpdateCrcFromDefineList(g_pParsePowerDefines);return cryptAdler32Final();}
unsigned original_class_defines(const unsigned char*names,unsigned names_size,unsigned names_begin,const unsigned char*origins,unsigned origins_size,unsigned origins_begin,unsigned*stats,unsigned profile){
 SimpleBuffer*in=calloc(1,sizeof(*in));assert(in);AttribNames raw_names={0};CharacterOrigins raw_origins={0};int sum=0;trace_bytes=trace_attempts=0;stash_allocations=0;reset();memcpy(in->data,names,names_size);in->filesize=names_size;in->curposition=names_begin;assert(ParserReadBinaryTable(in,ParseAttribNames,&raw_names,&sum)&&in->curposition==(int)names_size);g_AttribNames=raw_names;for(unsigned i=0;i<7;i++){Vec*v=((Vec**)&raw_names)[i];((void***)&g_AttribNames)[i]=v?v->items:NULL;}
 memset(in,0,sizeof(*in));memcpy(in->data,origins,origins_size);in->filesize=origins_size;in->curposition=origins_begin;sum=0;assert(ParserReadBinaryTable(in,ParseCharacterOrigins,&raw_origins,&sum)&&in->curposition==(int)origins_size);Vec*v=(Vec*)raw_origins.ppOrigins;g_CharacterOrigins.ppOrigins=(const CharacterOrigin**)v->items;
 assert(profile<=7);g_pParsePowerDefines=DefineCreateFromIntList(s_PowerEnums);if(profile==6)DefineAdd(g_pParsePowerDefines,"kScience_Boost","999");if(profile==2){AddAttributeDefines(g_pParsePowerDefines);AddSequencerDefines(g_pParsePowerDefines);}else{if(profile!=1)AddSequencerDefines(g_pParsePowerDefines);AddAttributeDefines(g_pParsePowerDefines);}if(profile==3)((CharacterOrigin*)g_CharacterOrigins.ppOrigins[0])->pchName="Unknown_Origin";if(profile==4)((AttribName*)g_AttribNames.ppDamage[0])->pchName="Unknown_Damage";AddAttribNames(g_pParsePowerDefines);if(profile==5)DefineAdd(g_pParsePowerDefines,"kscience_boost","999");unsigned scale_index=0;while(strcmp(ParseCharacterClass[scale_index].name,"DefiantScale"))scale_index++;intptr_t original_scale=ParseCharacterClass[scale_index].param;if(profile==7)ParseCharacterClass[scale_index].param=0x3f800000;unsigned crc=ParseTableCRC(ParseCharacterClasses,g_pParsePowerDefines);stats[0]=g_pParsePowerDefines->hash->uiMaxSize;stats[1]=g_pParsePowerDefines->hash->uiValidValues;stats[2]=original_state_count();stats[3]=trace_attempts;stats[4]=stash_allocations;ParseCharacterClass[scale_index].param=original_scale;free(in);return crc;
}
'''
 for qualified,expected in functions.items():
  _,name=qualified.rsplit(':',1);assert sha(small.extract(code,name).encode())==expected,(name,'changed')
 for qualified,expected in cp['origin_provider']['small_original_provider']['function_sha256_lf'].items():
  _,name=qualified.rsplit(':',1);assert sha(small.extract(code,name).encode())==expected,(name,'changed')
 (work/'defines.c').write_text(code)
 supplier=module('define_seq',seq_root/'native-android/engine/world-render-adapter/check_surface_states.py');supplier.load=module
 seqcode=supplier.oracle(rows,lambda text,needle:small.extract(text,re.search(r'(\w+)\($',needle).group(1)));(work/'seq.c').write_text(seqcode)
 subprocess.run(['cc','-std=gnu99','-O0','-shared','-fPIC','-w','-I'+str(HERE/'../costume-inputs'),'-I'+str(seq_root/'native-android/engine/world-render-adapter'),work/'defines.c',work/'seq.c','-lz','-o',work/'defines.so'],check=True);lib=C.CDLL(str(work/'defines.so'));lib.original_class_defines.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_uint,C.c_uint,C.c_void_p,C.c_uint]
 lib.original_names_roundtrip.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_void_p]
 lib.original_define_trace.argtypes=[C.c_void_p,C.c_uint];lib.original_define_slots.argtypes=[C.c_void_p,C.c_uint]
 return lib,{'class_provider':cp,'stash_provider':sp,'functions_sha256_lf':functions,'source_sha256_lf':{p:sha(t.encode())for p,t in src.items()},'generated_define_c_sha256':sha(code.encode()),'generated_seq_c_sha256':sha(seqcode.encode()),'runtime_generation':False}
