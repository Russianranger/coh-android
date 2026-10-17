#include "coh_classes.h"
#include <string.h>
typedef struct{const void*p;size_t n;}Span;
typedef struct{uint8_t kind,sub;}Field;
typedef struct{const Field*fields;size_t count;}Schema;
#include "class_schema.inc"
typedef struct{CohBytes input;size_t at;CohStatus status;CohClassDictionary*d;}Parse;
static int valid(Span a){return a.p?(uintptr_t)a.p<=UINTPTR_MAX-a.n:!a.n;}
static int overlap(Span a,Span b){return a.n&&b.n&&(uintptr_t)a.p<(uintptr_t)b.p+b.n&&(uintptr_t)b.p<(uintptr_t)a.p+a.n;}
static void need(Parse*p,int yes,CohStatus s){if(p->status==COH_OK&&!yes)p->status=s;}
static const uint8_t*bytes(Parse*p,size_t n){if(p->status!=COH_OK)return NULL;if(n>p->input.size-p->at){p->status=COH_INVALID;return NULL;}const uint8_t*b=p->input.data+p->at;p->at+=n;return b;}
static uint32_t word(Parse*p){const uint8_t*b=bytes(p,4);return b?((uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24):0;}
static size_t segment(Parse*p){uint32_t n=word(p);need(p,n<=p->input.size-p->at,COH_INVALID);return p->status==COH_OK?p->at+n:p->at;}
static CohBytes text(Parse*p){CohBytes out={0};const uint8_t*b=bytes(p,2);if(!b)return out;size_t n=(size_t)b[0]|(size_t)b[1]<<8;need(p,n<260,COH_LIMIT);if(p->status!=COH_OK)return out;b=bytes(p,n);if(!b)return out;need(p,memchr(b,0,n)==NULL,COH_INVALID);out=(CohBytes){b,n};(void)bytes(p,(4-(n+2)%4)%4);return out;}
static int equal(CohBytes a,const char*b){size_t n=strlen(b);return a.size==n&&!memcmp(a.data,b,n);}
static uint32_t own(Parse*p,unsigned owner,unsigned table,unsigned row,unsigned field,unsigned element){CohBytes s=text(p);CohClassDictionary*d=p->d;if(p->status!=COH_OK)return 0;if(d->text_count==COH_CLASS_TEXTS_MAX||s.size+1>COH_CLASS_TEXT_BYTES_MAX-d->text_bytes){p->status=COH_LIMIT;return 0;}uint32_t index=d->text_count++;CohClassText*t=&d->texts[index];*t=(CohClassText){owner,table,row,field,element,d->text_bytes,(uint32_t)s.size};memcpy(d->text+d->text_bytes,s.data,s.size);d->text_bytes+=(uint32_t)s.size+1;return index;}
static void record(Parse*p,unsigned table,unsigned owner,unsigned row,unsigned depth){
 need(p,table<5&&depth<=3,COH_INVALID);if(p->status!=COH_OK)return;size_t begin=p->at,end=segment(p);CohClassModTable*mod=NULL;
 if(table==1){need(p,owner<COH_CLASS_MAX,COH_LIMIT);if(p->status!=COH_OK)return;p->d->entries[owner].record=(CohClassSpan){(uint32_t)begin,(uint32_t)end};}
 if(table==4){need(p,p->d->modtable_count<COH_CLASS_TABLES_MAX,COH_LIMIT);if(p->status!=COH_OK)return;mod=&p->d->modtables[p->d->modtable_count++];*mod=(CohClassModTable){{(uint32_t)begin,(uint32_t)end},owner,row,0};}
 for(unsigned f=0;f<schemas[table].count&&p->status==COH_OK;f++){
  Field field=schemas[table].fields[f];size_t field_begin=p->at;uint32_t n;
  switch(field.kind){
  case 1:{uint32_t text_index=own(p,owner,table,row,f,0);if(table==1&&f==0)p->d->entries[owner].name_text=text_index;if(mod&&f==0)mod->name_text=text_index;break;}
  case 2:n=word(p);need(p,n<=128,COH_LIMIT);for(unsigned i=0;i<n&&p->status==COH_OK;i++)(void)own(p,owner,table,row,f,i);break;
  case 3:n=word(p);need(p,n<=4096,COH_LIMIT);for(unsigned i=0;i<n&&p->status==COH_OK;i++){(void)word(p);p->d->array_words++;}break;
  case 4:(void)word(p);p->d->scalar_words++;break;
  case 5:n=word(p);need(p,n<=(field.sub==1?COH_CLASS_MAX:field.sub==4?COH_CLASS_TABLES_MAX:128),COH_LIMIT);if(table==0)p->d->count=n;for(unsigned i=0;i<n&&p->status==COH_OK;i++)record(p,field.sub,field.sub==1?i:owner,i,depth+1);break;
  case 6:n=word(p);(void)bytes(p,n);break;
  default:p->status=COH_INVALID;break;
  }
  if(table==1)p->d->entries[owner].fields[f]=(CohClassSpan){(uint32_t)field_begin,(uint32_t)p->at};
  need(p,p->at<=end,COH_INVALID);
 }
 need(p,p->at==end,COH_INVALID);
}
CohStatus coh_classes_read(CohBytes input,uint64_t lease,const uint8_t expected[32],const CohCostumeImportDigest*d,CohClassDictionary*out,CohClassWorkspace*w,size_t budget,size_t retained){
 if(!input.data||!input.size||input.size>COH_CLASS_INPUT_MAX||!lease||!expected||!d||!d->sha256||!out||!w||(!d->context&&d->context_bytes)||(d->context&&!d->context_bytes)||!budget||budget>COH_CLASS_RAM_MAX)return COH_INVALID;
 Span spans[]={{input.data,input.size},{expected,32},{d,sizeof(*d)},{out,sizeof(*out)},{w,sizeof(*w)},{d->context,d->context_bytes}};size_t charge=COH_CLASS_STACK_RESERVE;
 for(unsigned i=0;i<6;i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(spans[i],spans[j]))return COH_INVALID;if(spans[i].n>budget||charge>budget-spans[i].n)return COH_LIMIT;charge+=spans[i].n;}
 if(d->scratch_reserve>budget-charge)return COH_LIMIT;
 charge+=d->scratch_reserve;if(retained>budget-charge)return COH_LIMIT;uint8_t any=0,hash[32];for(unsigned i=0;i<32;i++)any|=expected[i];if(!any)return COH_STATE;
 CohClassDictionary*c=&w->candidate;memset(c,0,sizeof(*c));c->input=input;c->input_lease=lease;Parse p={input,0,COH_OK,c};const uint8_t*magic=bytes(&p,8);need(&p,magic&&!memcmp(magic,"CrypticS",8),COH_INVALID);c->header_crc=word(&p);need(&p,c->header_crc==UINT32_C(0x7ff68aaf),COH_STATE);
 CohBytes signature=text(&p),files=text(&p);need(&p,equal(signature,"Parse6")&&equal(files,"Files1"),COH_UNSUPPORTED);size_t files_end=segment(&p);c->dependency_count=word(&p);need(&p,c->dependency_count<=128,COH_LIMIT);for(unsigned i=0;i<c->dependency_count&&p.status==COH_OK;i++){(void)text(&p);(void)word(&p);need(&p,p.at<=files_end,COH_INVALID);}need(&p,p.at==files_end,COH_INVALID);
 /* Check exact envelope before any potentially long nested traversal. */
 if(p.status==COH_OK){size_t begin=p.at;size_t end=segment(&p);need(&p,end==input.size,COH_INVALID);p.at=begin;}record(&p,0,0,0,0);need(&p,p.at==input.size,COH_INVALID);if(p.status!=COH_OK)return p.status;
 CohStatus status=d->sha256(d->context,input,hash);if(status!=COH_OK)return status;if(memcmp(hash,expected,32))return COH_STATE;memcpy(c->input_sha256,hash,32);c->raw_schema_validated=1;*out=*c;return COH_OK;
}
CohStatus coh_classes_find(const CohClassDictionary*d,CohBytes name,uint32_t*index){
 if(!d||!index||!name.data||name.size>=260)return COH_INVALID;
 Span a={d,sizeof(*d)},b={name.data,name.size},c={index,sizeof(*index)};if(!valid(a)||!valid(b)||!valid(c)||overlap(a,c)||overlap(b,c))return COH_INVALID;
 if(!d->raw_schema_validated||d->count>COH_CLASS_MAX||d->text_count>COH_CLASS_TEXTS_MAX||d->text_bytes>COH_CLASS_TEXT_BYTES_MAX)return COH_STATE;
 for(size_t i=0;i<name.size;i++)if(!name.data[i]||name.data[i]>127)return COH_UNSUPPORTED;
 for(unsigned i=d->count;i>0;i--){uint32_t ti=d->entries[i-1].name_text;if(ti>=d->text_count)return COH_STATE;CohClassText t=d->texts[ti];if(t.offset>=d->text_bytes||t.size>=d->text_bytes-t.offset||d->text[t.offset+t.size])return COH_STATE;const uint8_t*s=(const uint8_t*)d->text+t.offset;int match=t.size==name.size;for(unsigned j=0;j<t.size;j++){if(!s[j]||s[j]>127)return COH_UNSUPPORTED;if(match){unsigned x=s[j],y=name.data[j];if(x>='A'&&x<='Z')x+=32;if(y>='A'&&y<='Z')y+=32;if(x!=y)match=0;}}if(match){*index=i-1;return COH_OK;}}
 return COH_NOT_FOUND;
}
