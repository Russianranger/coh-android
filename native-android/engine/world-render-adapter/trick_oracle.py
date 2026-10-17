"""Original persisted Trick tables/types and bounded numeric postprocess source projections."""
from pathlib import Path

def declarations(root):
 r=Path(root)/'upstream/ouroboros/Common/seq';h=(r/'tricks.h').read_text();a=(r/'AutoLOD.h').read_text();s=(r/'animtrackanimate.h').read_text()
 def decl(text,start,end):p=text.index(start);return text[p:text.index(end,p)+len(end)]
 flags=['TRICK2_TEXBIAS','TRICK2_ALPHAREF','TRICK2_CASTSHADOW','TRICK2_NIGHTGLOW','TRICK2_HAS_SWAY','TRICK2_STSCROLL0','TRICK2_STSCROLL1']
 constants=['#define '+name+' '+next(line.split('=',1)[1].split(',')[0].strip() for line in h.splitlines() if line.strip().startswith(name+' ')) for name in flags]
 constants.append('#define GROUP_VIS_TRAY '+next(line.split('=',1)[1].split(',')[0].strip() for line in h.splitlines() if line.strip().startswith('GROUP_VIS_TRAY ')))
 return '\n'.join(['typedef uint64_t U64;typedef struct BoneAnimTrack BoneAnimTrack;typedef struct TrickInfo TrickInfo;',decl(s,'typedef struct StAnim\n','} StAnim;'),decl(a,'typedef struct AutoLOD\n','} AutoLOD;'),decl(h,'typedef struct TrickNode\n','} TrickNode;'),decl(h,'typedef struct TrickInfo\n','} TrickInfo;'),*constants])
def tables(root):
 r=Path(root)/'upstream/ouroboros/Common/seq';tricks=(r/'tricks.c').read_text();auto=(r/'AutoLOD.c').read_text();result=[]
 for source,name in [(tricks,'parse_st_anim'),(auto,'parse_auto_lod'),(tricks,'parse_trick')]:
  p=source.index('TokenizerParseInfo '+name+'[]');result.append(source[p:source.index('\n};',p)+3])
 return '\n'.join(result)+'\n'
def projection(root,extract):
 source=(Path(root)/'upstream/ouroboros/Common/seq/tricks.c').read_text();body=extract(source,'static void setupTrick(');prefix=body[:body.index('#ifndef OFFLINE')]+'}\n';prefix=prefix.replace('setupTrick(', 'source_numeric_prefix(',1)
 p=body.index('    if (trick->group_flags & GROUP_VIS_TRAY)');group=body[p:body.index('\n\n',p)]
 return prefix+'static void source_group_projection(TrickInfo *trick) {\n'+group+'\n}\n'

def create(root,extract):
 from texopt_setup_oracle import create as typed_create
 root=Path(root);code=typed_create(root,extract)
 code=code.replace('arrays[2];','arrays[3];').replace('#define TOKARRAY_INFO(t) arrays[!!((t)&TOK_FIXED_ARRAY)]','#define TOKARRAY_INFO(t) arrays[((t)&TOK_EARRAY)?2:!!((t)&TOK_FIXED_ARRAY)]')
 insert=declarations(root)+'\n#define TOK_EARRAY 2048\n#define TOK_FUNCTIONCALL_X 6\n#define TOK_STRUCT(s,m,t) TOK_STRUCT_X|TOK_EARRAY,offsetof(s,m),sizeof(**((s*)0)->m),t\nstatic int trick_flags[]={0},group_flags[]={0},stanim_flags[]={0},autolod_flags[]={0};\n'+tables(root)
 code=code.replace('typedef int(*ReadBin)',insert+'\ntypedef int(*ReadBin)')
 original='static void*TokenStoreAlloc(ParseTable*t,int c,void*s,int i,intptr_t p,void*a,void*b){(void)i;(void)p;(void)a;(void)b;return(char*)s+t[c].storeoffset;}'
 replacement=r'''static void TokenStoreSetCapacity(ParseTable*t,int c,void*s,int n){assert(n>0&&n<=256);void***slot=(void***)((char*)s+t[c].storeoffset);assert(!*slot);*slot=calloc((size_t)n+1,sizeof(void*));assert(*slot);}
static void*TokenStoreAlloc(ParseTable*t,int c,void*s,int i,intptr_t p,void*a,void*b){(void)a;(void)b;if(t[c].type&TOK_EARRAY){void***slot=(void***)((char*)s+t[c].storeoffset);assert(*slot&&!(*slot)[i]);(*slot)[i]=calloc(1,(size_t)p);assert((*slot)[i]);return(*slot)[i];}return(char*)s+t[c].storeoffset;}
'''
 if original not in code:raise ValueError('typed adapter source drift')
 code=code.replace(original,replacement)
 reader=(root/'upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c').read_text()
 code+='\n'+extract(reader,'int earray_readbin(')+'\n'+projection(root,extract)
 code+=r'''
int seqGetStateNumberFromName(const char*name){(void)name;abort();} /* unused old TexOpt entry must not execute */
static TrickInfo*trick_rows;
static unsigned children(void**a){unsigned n=0;if(a)while(a[n]){n++;assert(n<=256);}return n;}
void original_trick_initialize(const unsigned char*body,size_t n){arrays[0].readbin=nonarray_readbin;arrays[1].readbin=fixedarray_readbin;arrays[2].readbin=earray_readbin;types[1].readbin=u8_readbin;types[2].readbin=int_readbin;types[3].readbin=float_readbin;types[4].readbin=string_readbin;types[5].readbin=struct_readbin;Buffer b={(unsigned char*)body,n,28};U32 size,count;assert(SimpleBufReadU32(&size,&b));SimpleBufSeek(&b,size,SEEK_CUR);assert(SimpleBufReadU32(&size,&b)&&size==b.size-b.pos&&SimpleBufReadU32(&count,&b)&&count==14715);for(U32 i=0;i<count;i++){assert(SimpleBufReadU32(&size,&b));SimpleBufSeek(&b,size,SEEK_CUR);}assert(SimpleBufReadU32(&count,&b)&&count==3644);trick_rows=calloc(count,sizeof(*trick_rows));assert(trick_rows);for(U32 i=0;i<count;i++){int sum=0;assert(ParserReadBinaryTable(&b,parse_trick,trick_rows+i,&sum));}assert(b.pos==b.size);}
const TrickInfo*original_trick_row(unsigned i){assert(i<3644);return trick_rows+i;}
unsigned original_trick_children(unsigned i,int lod){assert(i<3644);return children(lod?(void**)trick_rows[i].auto_lod:(void**)trick_rows[i].stAnim);}
unsigned original_trick_owner(unsigned i){assert(i<3644);for(unsigned n=3644;n>0;n--)if(!stricmp(trick_rows[n-1].name,trick_rows[i].name))return n-1;abort();}
void original_trick_project(unsigned i,TrickInfo*out){assert(i<3644);*out=trick_rows[i];source_numeric_prefix(out,false);source_group_projection(out);}
static void clear_trick(ParseTable*t,void*object){for(unsigned i=0;t[i].type;i++){if(t[i].type&TOK_REDUNDANTNAME)continue;char*base=(char*)object+t[i].storeoffset;unsigned type=TOK_GET_TYPE(t[i].type);if(t[i].type&TOK_EARRAY){void**a;memcpy(&a,base,sizeof(a));if(a){for(unsigned j=0;a[j];j++){clear_trick(t[i].subtable,a[j]);free(a[j]);}free(a);}}else if(type==TOK_STRING_X){char*str;memcpy(&str,base,sizeof(str));free(str);}}}
int original_trick_parse_row(const unsigned char*data,size_t n,TrickInfo*out){memset(out,0,sizeof(*out));Buffer b={(unsigned char*)data,n,0};int sum=0;return ParserReadBinaryTable(&b,parse_trick,out,&sum)&&b.pos==n;}
void original_trick_clear_row(TrickInfo*out){clear_trick(parse_trick,out);}
void original_trick_destroy(void){for(unsigned i=0;i<3644;i++)clear_trick(parse_trick,trick_rows+i);free(trick_rows);}
'''
 return code
