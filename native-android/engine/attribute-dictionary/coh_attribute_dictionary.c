#include "coh_attribute_dictionary.h"
#include <string.h>
typedef struct{const void*p;size_t n;}Span;
typedef struct{CohBytes input;size_t at;CohStatus status;}Parse;
static int valid(Span a){return a.p?(uintptr_t)a.p<=UINTPTR_MAX-a.n:!a.n;}
static int overlap(Span a,Span b){return a.n&&b.n&&(uintptr_t)a.p<(uintptr_t)b.p+b.n&&(uintptr_t)b.p<(uintptr_t)a.p+a.n;}
static void need(Parse*p,int yes,CohStatus status){if(p->status==COH_OK&&!yes)p->status=status;}
static const uint8_t*bytes(Parse*p,size_t n){if(p->status!=COH_OK)return NULL;if(n>p->input.size-p->at){p->status=COH_INVALID;return NULL;}const uint8_t*b=p->input.data+p->at;p->at+=n;return b;}
static uint32_t word(Parse*p){const uint8_t*b=bytes(p,4);return b?((uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24):0;}
static size_t segment(Parse*p){uint32_t n=word(p);need(p,n<=p->input.size-p->at,COH_INVALID);return p->status==COH_OK?p->at+n:p->at;}
static CohBytes text(Parse*p){CohBytes out={0};const uint8_t*b=bytes(p,2);if(!b)return out;size_t n=(size_t)b[0]|(size_t)b[1]<<8;need(p,n<260,COH_LIMIT);if(p->status!=COH_OK)return out;b=bytes(p,n);if(!b)return out;need(p,memchr(b,0,n)==NULL,COH_INVALID);out=(CohBytes){b,n};(void)bytes(p,(4-(n+2)%4)%4);return out;}
static int equal(CohBytes a,const char*b){size_t n=strlen(b);return a.size==n&&!memcmp(a.data,b,n);}
CohStatus coh_attribute_dictionary_read(CohBytes input,uint64_t lease,const uint8_t expected[32],
 const CohCostumeImportDigest*d,CohAttributeDictionary*out,CohAttributeDictionaryWorkspace*w,size_t budget,size_t retained){
 if(!input.data||!input.size||input.size>COH_ATTRIBUTE_DICTIONARY_INPUT_MAX||!lease||!expected||!d||!d->sha256||!out||!w||(!d->context&&d->context_bytes)||(d->context&&!d->context_bytes)||!budget||budget>COH_ATTRIBUTE_DICTIONARY_RAM_MAX)return COH_INVALID;
 Span spans[]={{input.data,input.size},{expected,32},{d,sizeof(*d)},{out,sizeof(*out)},{w,sizeof(*w)},{d->context,d->context_bytes}};
 size_t charge=COH_ATTRIBUTE_DICTIONARY_STACK_RESERVE;
 for(unsigned i=0;i<6;i++){if(!valid(spans[i]))return COH_INVALID;for(unsigned j=0;j<i;j++)if(overlap(spans[i],spans[j]))return COH_INVALID;if(spans[i].n>budget||charge>budget-spans[i].n)return COH_LIMIT;charge+=spans[i].n;}
 if(d->scratch_reserve>budget-charge)return COH_LIMIT;
 charge+=d->scratch_reserve;if(retained>budget-charge)return COH_LIMIT;
 uint8_t any=0,hash[32];for(unsigned i=0;i<32;i++)any|=expected[i];if(!any)return COH_STATE;
 CohAttributeDictionary*c=&w->candidate;memset(c,0,sizeof(*c));c->input=input;c->input_lease_token=lease;Parse p={input,0,COH_OK};const uint8_t*magic=bytes(&p,8);need(&p,magic&&!memcmp(magic,"CrypticS",8),COH_INVALID);c->schema_crc=word(&p);need(&p,c->schema_crc==UINT32_C(0x315acdb1),COH_STATE);
 CohBytes signature=text(&p),files=text(&p);need(&p,equal(signature,"Parse6")&&equal(files,"Files1"),COH_UNSUPPORTED);size_t files_end=segment(&p);c->dependency_count=word(&p);need(&p,c->dependency_count<=64,COH_LIMIT);
 for(unsigned i=0;i<c->dependency_count&&p.status==COH_OK;i++){(void)text(&p);(void)word(&p);need(&p,p.at<=files_end,COH_INVALID);}need(&p,p.at==files_end,COH_INVALID);
 size_t root_end=segment(&p);need(&p,root_end==input.size,COH_INVALID);c->category_count=word(&p);need(&p,c->category_count<=COH_ATTRIBUTE_DICTIONARY_CATEGORIES_MAX,COH_LIMIT);
 for(unsigned category=0;category<c->category_count&&p.status==COH_OK;category++){
  size_t category_end=segment(&p);CohBytes category_name=text(&p);uint32_t count=word(&p);need(&p,count<=COH_ATTRIBUTE_DICTIONARY_ROWS_MAX-c->row_count,COH_LIMIT);
  for(unsigned row=0;row<count&&p.status==COH_OK;row++){
   size_t row_end=segment(&p);CohAttributeDescription*a=&c->ordered[c->row_count];a->category=category;a->row=row;a->category_rows=count;a->category_name=category_name;a->name=text(&p);a->display_name=text(&p);a->tooltip=text(&p);a->type=word(&p);a->style=word(&p);a->key=word(&p);a->offset=word(&p);a->show_base_word=word(&p);a->lookup_key=UINT32_C(460)*a->type+a->offset;need(&p,p.at==row_end&&p.at<=category_end,COH_INVALID);c->row_count++;
  }
  need(&p,p.at==category_end&&p.at<=root_end,COH_INVALID);
 }
 need(&p,p.at==root_end&&p.at==input.size,COH_INVALID);if(p.status!=COH_OK)return p.status;
 /* Whole original producer/consumer iterate reversed categories and reversed
  * rows; reversing the complete forward flatten preserves both exactly. */
 for(unsigned i=0;i<c->row_count/2;i++){CohAttributeDescription tmp=c->ordered[i];c->ordered[i]=c->ordered[c->row_count-1-i];c->ordered[c->row_count-1-i]=tmp;}
 CohStatus status=d->sha256(d->context,input,hash);if(status!=COH_OK)return status;if(memcmp(hash,expected,32))return COH_STATE;memcpy(c->input_sha256,hash,32);c->raw_schema_validated=1;c->schema_crc_matched=1;*out=*c;return COH_OK;
}
