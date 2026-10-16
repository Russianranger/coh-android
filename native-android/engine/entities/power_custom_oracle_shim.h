/* Synthetic power dictionary, earray and StructCopy adapters. Original wire
 * producer/consumer and sort comparator are extracted without rewriting. */
static int fixture_products,g_PowerDictionary;
#define AINRANGE(i,array) ((i)>=0&&(unsigned)(i)<ARRAY_SIZE(array))
#define SKU(s) s
#ifndef MIN
#define MIN(a,b) ((a)<(b)?(a):(b))
#endif
static void *ent_GetProductInventory(Entity *e){(void)e;return &fixture_products;}
static int AccountHasStoreProduct(void *p,const char *s){int bit=s[strlen(s)-1]-'6';if(s[strlen(s)-1]=='0')bit=4;assert(bit>=0&&bit<5);return (*(int*)p>>bit)&1;}
static PowerCustomizationList *dummy_ent_powerCust;
static BasePower fixture_powers[]={{1,"Fixture.First"},{0xa1b2c3d4,"Fixture.Second"},{0x00abcdef,"Fixture.Third"},{0xfefefefe,"Missing.Fixture"}};
static uint32_t queried_crcs[4096];static unsigned query_count;
static const BasePower *powerdict_GetBasePowerByCRC(int *d,uint32_t crc){(void)d;assert(query_count<4096);queried_crcs[query_count++]=crc;for(unsigned i=0;i<3;i++)if(fixture_powers[i].crcFullName==crc)return &fixture_powers[i];return NULL;}
static size_t power_array_size(void *const *array){return array?((size_t*)array)[-1]:0;}
static void power_push(PowerCustomization ***array,PowerCustomization *value){size_t count=power_array_size((void*const*)*array);size_t *base=*array?((size_t*)*array)-1:NULL;base=realloc(base,sizeof(size_t)+(count+1)*sizeof(void*));assert(base);base[0]=count+1;*array=(PowerCustomization**)(base+1);(*array)[count]=value;}
static char *power_string(const char *s){char *out=malloc(strlen(s)+1);assert(out);strcpy(out,s);return out;}
static void power_clear(PowerCustomizationList *list){for(size_t i=0;i<power_array_size((void*const*)list->powerCustomizations);i++){free((void*)list->powerCustomizations[i]->token);free(list->powerCustomizations[i]);}if(list->powerCustomizations)free(((size_t*)list->powerCustomizations)-1);list->powerCustomizations=NULL;}
static void power_copy(PowerCustomizationList *src,PowerCustomizationList *dst){power_clear(dst);for(size_t i=0;i<power_array_size((void*const*)src->powerCustomizations);i++){PowerCustomization *v=malloc(sizeof(*v));assert(v);*v=*src->powerCustomizations[i];v->token=power_string(v->token);power_push(&dst->powerCustomizations,v);}}
#undef eaSize
#undef eaPush
#undef StructDestroy
#define eaSize(p) power_array_size((void*const*)*(p))
#define eaPush(p,v) power_push(p,v)
#define eaQSort(p,cmp) qsort(p,power_array_size((void*const*)p),sizeof(void*),cmp)
#define StructAllocString(s) power_string(s)
#define StructInit(p,size,parse) memset(p,0,size)
#define StructCopy(parse,src,dst,a,b) power_copy(src,dst)
#define StructDestroy(parse,p) do{power_clear(p);free(p);}while(0)
#define ParsePowerCustomizationList 0
