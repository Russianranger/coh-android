/* Shipping mmap/owner adapter, explicit Android asset/JNI/transport doubles.
 * No Android ABI or physical packet claim is made by this host test. */
#define COH_BODYPART_TEST_MAIN retained_bodypart_suite_not_executed
#include "test_bodypart_continuation.c"
struct AAssetManager {int value;};struct AAsset {int value;};
static struct AAssetManager manager;
static struct AAsset asset;
static const char *asset_file;
static unsigned asset_fault,asset_opens,asset_closes,maps,unmaps,map_live,map_peak,fail_map;
static size_t map_bytes_peak;
static off_t asset_prefix=37;
static unsigned char multi_packet[8192];static size_t multi_bits;
AAssetManager *AAssetManager_fromJava(JNIEnv *e,jobject value){(void)e;return value==&manager&&asset_fault!=1?&manager:NULL;}
AAsset *AAssetManager_open(AAssetManager *m,const char *name,int mode){CHECK(m==&manager&&!strcmp(name,"combined/client-slots.bin")&&mode==AASSET_MODE_RANDOM);if(asset_fault==2)return NULL;asset_opens++;return &asset;}
int AAsset_openFileDescriptor(AAsset *a,off_t *start,off_t *length){CHECK(a==&asset);if(asset_fault==3)return -1;*start=asset_prefix;*length=COH_CLIENT_COSTUME_RAW_BYTES-(asset_fault==4);return open(asset_file,O_RDONLY);}
void AAsset_close(AAsset *a){CHECK(a==&asset);asset_closes++;}
void *__real_mmap(void *,size_t,int,int,int,off_t);int __real_munmap(void *,size_t);
void *__wrap_mmap(void *at,size_t bytes,int protection,int flags,int fd,off_t offset){
 CHECK(!at&&protection==PROT_READ&&flags==MAP_PRIVATE&&offset%sysconf(_SC_PAGESIZE)==0);
 if(fail_map){errno=ENOMEM;return MAP_FAILED;}
 void *p=__real_mmap(at,bytes,protection,flags,fd,offset);if(p!=MAP_FAILED){maps++;map_live++;if(map_live>map_peak)map_peak=map_live;if(bytes*map_live>map_bytes_peak)map_bytes_peak=bytes*map_live;}return p;
}
int __wrap_munmap(void *p,size_t bytes){int status=__real_munmap(p,bytes);CHECK(!status&&map_live);unmaps++;map_live--;return status;}
static CohStatus slots_configure(const char *path){asset_file=path;return(CohStatus)JNI(configureClientSlots)(&env,NULL,&manager);}
static void slot_begin(void){current=JNI(begin)(&env,NULL,7000,&input,5,0,0,100);CHECK(current>0&&live==2&&map_live==1&&active->client_slots.view.raw.size==641477&&!configured_client_slots.mapping);}
static void first_index_capture(const char *path){
 fixture();CHECK(slots_configure(path)==COH_OK);partcount_fixture=1;
 unsigned index=0;while(index<32768&&!configured_client_slots.view.index[index])index++;
 CHECK(index<32767);unsigned at=COH_PARTCOUNT_JNI_FIXTURE_PARTCOUNT_BEGIN;partcount_scalar(at++,1,0);
 partcount_scalar(at,3,6);at+=3;partcount_scalar(at,15,index);at+=15;partcount_bits=at;
 slot_begin();CHECK(JNI(configureClientSlots)(&env,NULL,&manager)==COH_STATE);
 CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);
 CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);CHECK(JNI(service)(&env,NULL,current,104)==COH_UNSUPPORTED);
 CohRepReader legacy_reader={{partcount_packet,sizeof(partcount_packet)},partcount_bits,active->initial_costume_continuation.begin_bit,0,COH_REP_BOUNDED_MESSAGE_MAX};CohOriginalCostumeReport legacy;
 CHECK(coh_original_costume_receive(&legacy_reader,28,&active->costume_workspace,&legacy)==COH_UNSUPPORTED);
 CHECK(active->initial_costume_continuation.strings_read==legacy.strings_read+1&&active->initial_costume_continuation.field==COH_ORIGINAL_COSTUME_TEX1);
 CHECK(active->initial_costume_continuation.dictionary_required==0&&active->initial_costume_continuation.end_bit==at);
 CHECK(strstr(report(),"\"client_slots\":[0,641477,134144,")!=NULL);
 CHECK(strstr(report_text,"\"initial_observed\":true")&&!strstr(report_text,"REPORT_LIMIT"));
 JNI(suspend)(&env,NULL,current);CHECK(!map_live&&live==1&&!active->client_slots.view.raw.data);
 CHECK(strstr(report(),"\"client_slots\":[0,0,0,0]")!=NULL);finish();
}
static void set_bits(unsigned char *p,size_t at,unsigned n,uint32_t value){for(unsigned i=0;i<n;i++){size_t bit=at+i;p[bit/8]=(unsigned char)((p[bit/8]&~(1u<<(bit%8)))|(((value>>i)&1u)<<(bit%8)));}}
static CohStatus multi_observe(void *context,const CohInitialCapture *c,const CohInitialCaptureEvent *event){
 CHECK(event->kind==COH_INITIAL_CAPTURE_ALLENTS);loan.reader.bytes=(CohBytes){multi_packet,sizeof(multi_packet)};loan.reader.bits=multi_bits;
 return observe(context,c,event);
}
static void multiple_bodies(const char *path,unsigned count,unsigned truncate){
 fixture();CHECK(slots_configure(path)==COH_OK);partcount_fixture=1;
 const size_t begin=COH_COSTUME_SLOTS_JNI_FIXTURE_SLOTS_END,end=COH_PARTCOUNT_JNI_FIXTURE_PARTCOUNT_END;
 /* Retain the original sender's whole body header, with its explicit count
  * set to zero. The engine suite separately replays indexed original senders.
  * Repeat those exact header bits so this test isolates the JNI list loop. */
 partcount_scalar(COH_PARTCOUNT_JNI_FIXTURE_PARTCOUNT_BEGIN,1,1);
 partcount_scalar(COH_PARTCOUNT_JNI_FIXTURE_PARTCOUNT_COUNT_BEGIN,4,0);
 memset(multi_packet,0,sizeof(multi_packet));
 for(size_t b=0;b<begin;b++)set_bits(multi_packet,b,1,(partcount_packet[b/8]>>(b%8))&1u);
 set_bits(multi_packet,COH_COSTUME_SLOTS_JNI_FIXTURE_MULTIPLE_BEGIN,1,1);
 set_bits(multi_packet,COH_COSTUME_SLOTS_JNI_FIXTURE_COUNT_BEGIN,4,count);
 multi_bits=begin;
 for(unsigned body=0;body<count;body++)for(size_t b=begin;b<end;b++)set_bits(multi_packet,multi_bits++,1,(partcount_packet[b/8]>>(b%8))&1u);
 CHECK(multi_bits<sizeof(multi_packet)*8);if(truncate)multi_bits--;
 slot_begin();CHECK(JNI(service)(&env,NULL,current,101)==COH_OK);CHECK(JNI(choose)(&env,NULL,current,2,102)==COH_OK);CHECK(JNI(service)(&env,NULL,current,103)==COH_OK);
 active->busy=1;CHECK(coh_initial_capture_service(active->capture,104,(CohCancel){0},multi_observe,active,sizeof(*active))==COH_UNSUPPORTED);active->busy=0;
 CHECK(active->costume_bodies_expected==count&&active->costume_bodies_read==count-truncate);
 CHECK(active->initial_costume_continuation.costume_complete==!truncate);
 if(!truncate)CHECK(active->initial_costume_continuation.end_bit==multi_bits);
 CHECK(strstr(report(),"\"costume_bodies\":")!=NULL);finish();CHECK(!map_live&&!live);
}
int main(int argc,char **argv){
 CHECK(argc==3);fixture();CHECK(JNI(configureClientSlots)(&env,NULL,NULL)==COH_INVALID);
 CHECK(slots_configure(argv[1])==COH_OK&&map_live==1&&live==1);
 CHECK(configured_client_slots.view.present[0]==13209&&configured_client_slots.view.present[1]==156&&configured_client_slots.view.present[2]==224);
 CHECK(slots_configure(argv[1])==COH_OK&&map_live==1&&map_peak==2&&live==1);
 CHECK(slots_configure(argv[2])==COH_STATE&&!map_live&&!live);
 for(asset_fault=1;asset_fault<=4;asset_fault++){CHECK(slots_configure(argv[1])!=COH_OK);CHECK(!map_live&&!live);}asset_fault=0;
 fail_map=1;CHECK(slots_configure(argv[1])==COH_LIMIT&&!map_live&&!live);fail_map=0;
 fail_alloc=alloc_calls+1;CHECK(slots_configure(argv[1])==COH_LIMIT&&!map_live&&!live);fail_alloc=0;
 CHECK(slots_configure(argv[1])==COH_OK);CHECK(!JNI(begin)(&env,NULL,0,&input,5,0,0,100)&&!map_live&&!live);
 const int faults[]={1,2,6,7,8,9,10};
 for(unsigned i=0;i<sizeof(faults)/sizeof(faults[0]);i++){
  fixture();CHECK(slots_configure(argv[1])==COH_OK);fault=faults[i];
  CHECK(!JNI(begin)(&env,NULL,7000,&input,5,0,0,100));CHECK(!map_live&&!live);exception_pending=0;
 }
 fixture();CHECK(slots_configure(argv[1])==COH_OK);fail_alloc=alloc_calls+1;
 CHECK(!JNI(begin)(&env,NULL,7000,&input,5,0,0,100)&&!map_live&&!live);fail_alloc=0;
 for(unsigned path=0;path<3;path++){
  fixture();CHECK(slots_configure(argv[1])==COH_OK);slot_begin();
  if(path==0)JNI(suspend)(&env,NULL,current);else if(path==1)JNI(disconnect)(&env,NULL,current);
  if(path<2){CHECK(!map_live&&live==1);}
  finish();CHECK(!map_live&&!live);
 }
 first_index_capture(argv[1]);
 for(unsigned count=2;count<=10;count++){multiple_bodies(argv[1],count,0);multiple_bodies(argv[1],count,1);}
 CHECK(opens==closed_files&&asset_opens==asset_closes&&maps==unmaps&&!map_live&&!live);
 printf("{\"passed\":true,\"checks\":%u,\"mappings\":%u,\"unmappings\":%u,\"simultaneous_mapping_peak\":%u,\"mapping_bytes_peak\":%zu,\"interop_owner_bytes\":%zu,\"raw_bytes\":641477,\"index_bytes\":134144,\"report_peak_bytes\":%zu,\"physical_packet_replayed\":false}\n",checks,maps,unmaps,map_peak,map_bytes_peak,sizeof(Interop),max_report_bytes);return 0;
}
