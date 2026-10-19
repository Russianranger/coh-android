/* Included after exact original BodyPart declarations/getter/staged bp entry. */
#include <assert.h>
#include <errno.h>
static unsigned checks,transactions,repeats;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL line %u: %s\n",(unsigned)__LINE__,#x);abort();}}while(0)
static BodyPart fixture_parts[30],saved_parts[30];
static const BodyPart*fixture_rows[30],*saved_rows[30];
static char fixture_strings[30][5][261];
static unsigned scenario,io_fault,opens,writes,closes,unlinks;
static int fixture_count;
static int diag_open(const char*p,int f,int m){opens++;if(io_fault&1)return-1;return open(p,f,m);}
static int diag_write(int fd,const void*p,unsigned n){writes++;if(io_fault&2)return 0;if(io_fault&16&&n>7)n=7;return(int)write(fd,p,n);}
static int diag_close(int fd){int rc=close(fd);closes++;return io_fault&4?-1:rc;}
static int diag_unlink(const char*p){unlinks++;if(io_fault&8){errno=EACCES;return-1;}return unlink(p);}
static void fixture_init(unsigned count,unsigned longstrings){
 unsigned i,j;memset(fixture_parts,0,sizeof(fixture_parts));memset(fixture_rows,0,sizeof(fixture_rows));memset(fixture_strings,0,sizeof(fixture_strings));
 fixture_count=(int)count;bodyPartList.bodyParts=fixture_rows;
 for(i=0;i<count;i++){
  BodyPart*p=fixture_parts+i;fixture_rows[i]=p;
  for(j=0;j<5;j++)if(longstrings){memset(fixture_strings[i][j],'a'+(int)((i+j)%26),259);fixture_strings[i][j][259]=0;}
   else snprintf(fixture_strings[i][j],261,"part%u-string%u",i,j);
  p->name=fixture_strings[i][0];p->name_geo=fixture_strings[i][1];p->name_tex=fixture_strings[i][2];p->base_var=fixture_strings[i][3];p->sourceFile=fixture_strings[i][4];
  p->bone_num[0]=(BoneId)(i?i:0xffffffffu);p->bone_num[1]=(BoneId)0x80000000u;p->bodyPartIndex=(int)i;p->num_parts=i%2?2:1;p->influenceCost=-((int)i+1);p->dont_clear=(U8)(i+226);
 }
 memcpy(saved_parts,fixture_parts,sizeof(saved_parts));memcpy(saved_rows,fixture_rows,sizeof(saved_rows));
}
static void unchanged(void){CHECK(!memcmp(saved_parts,fixture_parts,sizeof(saved_parts)));CHECK(!memcmp(saved_rows,fixture_rows,sizeof(saved_rows)));}
static int idle(void){const unsigned char*p=(const unsigned char*)&coh_body_witness;size_t i;for(i=0;i<sizeof(coh_body_witness);i++)if(p[i])return 0;return 1;}
static void filename(char out[241],const char*dir,const char*name){CHECK(snprintf(out,241,"%s/%s",dir,name)>0);CHECK(strlen(out)<240);}
static void setoutput(const char*p){CHECK(!setenv("COH_NATIVE_BODY_WITNESS_OUTPUT",p,1));}
/* Fixture loader shell dispatches the NORMALIZED source events in actual source
 * order. It is not original loader/shared/allocator execution or attestation. */
static int fixture_loader(const char*s,const char*d,const char*m,const char*n,int f,void*t,void*r,size_t z,void*a,void*b,int(*c)(void*,void*),void*e,void*g){
 (void)s;(void)d;(void)m;(void)n;(void)f;(void)t;(void)z;(void)a;(void)b;(void)c;(void)e;(void)g;
 CHECK(r==&bodyPartList);transactions++;
 coh_source_body_witness_route(r,1,scenario==1?1:scenario==2?3:scenario==7?4:2);
 if(scenario!=1){
  if(scenario!=5)coh_source_body_witness_located(r,"/owned/profile/data/bin/BodyParts.bin");
  if(scenario==3){CHECK(!coh_source_body_witness_binary(r,0));coh_source_body_witness_route(r,3,1);}
  else if(scenario==4)coh_source_body_witness_route(r,3,1);
  else CHECK(coh_source_body_witness_binary(r,scenario==6?0:1)==(scenario==6?0:1));
 }
 coh_source_body_witness_route(r,4,scenario==6?1:2);return scenario!=6;
}
static void observe(unsigned which){scenario=which;bpReadBodyPartFiles();}
static void startup_expect(unsigned expected){CHECK((unsigned)coh_source_body_witness_snapshot_startup()==expected);CHECK(coh_body_witness_last_status==expected);CHECK(idle());}
int main(int argc,char**argv){
 char path[241],other[241];unsigned i,j,copy[6];size_t written;unsigned char saved[65536];
 CHECK(argc==2);filename(path,argv[1],"min.bin");unsetenv("COH_NATIVE_BODY_WITNESS_OUTPUT");fixture_init(1,0);observe(0);CHECK(idle());startup_expect(0);CHECK(!opens);
 setoutput(path);fixture_init(1,0);fixture_parts[0].name=NULL;fixture_parts[0].name_geo=(char*)"";memcpy(saved_parts,fixture_parts,sizeof(saved_parts));observe(0);CHECK(coh_body_witness.ready);CHECK(coh_body_witness.count==1);unchanged();startup_expect(0);CHECK(opens==1&&closes==1);unchanged();
 filename(path,argv[1],"max.bin");setoutput(path);fixture_init(29,1);observe(2);CHECK(coh_body_witness.ready);CHECK(coh_body_witness.used==170+37+29*(24+10+5*259));
 memcpy(saved,coh_body_witness.bytes,sizeof(saved));written=999;
 CHECK(coh_body_witness_serialize(0,coh_body_witness.used-1,&written)==2);CHECK(written==999);CHECK(!memcmp(saved,coh_body_witness.bytes,sizeof(saved)));
 CHECK(coh_body_witness_serialize(0,65537,&written)==1);CHECK(written==999);
 CHECK(coh_body_witness_serialize(0,SIZE_MAX,&written)==1);CHECK(written==999);
 CHECK(coh_body_witness_serialize(0,0,&written)==1);CHECK(written==999);
 CHECK(coh_body_witness_serialize(0,65536,(size_t*)&coh_body_witness)==1);CHECK(!memcmp(saved,coh_body_witness.bytes,sizeof(saved)));
 fixture_rows[0]=(const BodyPart*)&coh_body_witness;CHECK(coh_body_witness_serialize(0,65536,&written)==1);fixture_rows[0]=fixture_parts;
 bodyPartList.bodyParts=(const BodyPart**)(uintptr_t)(UINTPTR_MAX-2);CHECK(coh_body_witness_serialize(0,65536,&written)==1);bodyPartList.bodyParts=fixture_rows;
 fixture_parts[0].name=(char*)(uintptr_t)(UINTPTR_MAX-2);CHECK(coh_body_witness_serialize(0,65536,&written)==1);fixture_parts[0]=saved_parts[0];
 CHECK(!memcmp(saved,coh_body_witness.bytes,sizeof(saved)));startup_expect(0);unchanged();
 /* Source mutation/generation replacement refuses without touching live rows. */
 filename(path,argv[1],"rejected.bin");setoutput(path);
 for(i=0;i<9;i++){
  fixture_init(1,0);observe(0);CHECK(coh_body_witness.ready);
  if(i==0)fixture_parts[0].bodyPartIndex++;
  if(i==1)fixture_strings[0][0][0]='Z';
  if(i==2)fixture_count=2;
  if(i==3)bodyPartList.bodyParts=fixture_rows+1;
  if(i==4)coh_body_witness.root=fixture_rows;
  if(i==5){observe(0);CHECK(!coh_body_witness.ready);}
  if(i==6){coh_body_witness_begin(&bodyPartList);CHECK(!coh_body_witness.ready);}
  if(i==7)fixture_parts[0].name=NULL;
  if(i==8){memset(fixture_strings[0][0],'x',260);fixture_strings[0][0][260]=0;}
  startup_expect(i==0||i==1||i==7?3:i==8?1:4);CHECK(access(path,F_OK));
 }
 /* Refusals at rows and string bound, plus exact maximum present empty/null. */
 for(i=0;i<4;i++){
  fixture_init(i==0?0:i==1?30:1,0);if(i==2)fixture_rows[0]=NULL;if(i==3){memset(fixture_strings[0][0],'x',260);fixture_strings[0][0][260]=0;}
  observe(0);CHECK(!coh_body_witness.ready);startup_expect(4);CHECK(access(path,F_OK));
 }
 /* Every acquisition and cache/text branch remains source observation only. */
 for(i=0;i<8;i++){
  fixture_init(1,0);observe(i);
  if(i==5||i==6||i==7){CHECK(!coh_body_witness.ready);startup_expect(4);}
  else{CHECK(coh_body_witness.ready);startup_expect(0);CHECK(!unlink(path));}
 }
 /* Other-root callbacks never modify an active witness; malformed routes refuse. */
 for(i=0;i<7;i++){
  fixture_init(1,0);coh_body_witness_begin(&bodyPartList);memcpy(copy,&coh_body_witness.active,sizeof(copy));
  coh_source_body_witness_route(fixture_rows,1,3);CHECK(!memcmp(copy,&coh_body_witness.active,sizeof(copy)));
  if(i==0){coh_source_body_witness_route(&bodyPartList,1,2);coh_source_body_witness_route(&bodyPartList,1,2);}
  if(i==1)coh_source_body_witness_route(&bodyPartList,99,1);
  if(i==2)coh_source_body_witness_route(&bodyPartList,2,3);
  if(i==3)coh_source_body_witness_route(&bodyPartList,4,3);
  if(i==4){coh_source_body_witness_located(&bodyPartList,"bin/BodyParts.bin");coh_source_body_witness_located(&bodyPartList,"bin/BodyParts.bin");}
  if(i==5){coh_source_body_witness_route(&bodyPartList,2,2);coh_source_body_witness_route(&bodyPartList,3,1);}
  if(i==6)coh_source_body_witness_located(&bodyPartList,NULL);
  CHECK(coh_body_witness.error);coh_body_witness_end();startup_expect(4);
 }
 /* Supported fault points: exclusive open/write/close/unlink, no allocations. */
 for(i=1;i<=15;i++)if(i==1||i==2||i==4||i==10){
  unsigned previous_open=opens,previous_unlink=unlinks;fixture_init(1,0);observe(0);io_fault=i;startup_expect(i==10?5:i==4?6:1);io_fault=0;
  CHECK(opens==previous_open+1);if(i==1)CHECK(unlinks==previous_unlink);
  else CHECK(unlinks==previous_unlink+1);
  if(i==10){CHECK(!access(path,F_OK));CHECK(!unlink(path));}else CHECK(access(path,F_OK));unchanged();
 }
 fixture_init(1,0);observe(0);io_fault=16;startup_expect(0);io_fault=0;CHECK(!unlink(path));
 /* Exclusive-file refusal preserves existing contents. */
 {int fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0600);CHECK(fd>=0);CHECK(write(fd,"old",3)==3);CHECK(!close(fd));fixture_init(1,0);observe(0);startup_expect(1);fd=open(path,O_RDONLY);CHECK(fd>=0);CHECK(read(fd,copy,3)==3);CHECK(!memcmp(copy,"old",3));CHECK(!close(fd));CHECK(!unlink(path));}
 for(i=0;i<3;i++){setoutput(i==0?"relative.bin":i==1?"/tmp/../bad":"/");fixture_init(1,0);observe(0);startup_expect(1);}
 filename(other,argv[1],"repeat.bin");setoutput(other);
 for(i=0;i<256;i++){fixture_init(1+i%29,i%2);observe(i%3);CHECK(coh_body_witness.ready);startup_expect(0);CHECK(!unlink(other));unchanged();repeats++;}
 fixture_init(1,0);observe(0);CHECK(coh_body_witness.ready);unsetenv("COH_NATIVE_BODY_WITNESS_OUTPUT");startup_expect(0);CHECK(access(other,F_OK));
 for(j=0;j<1;j++)CHECK(idle());
 printf("{\"passed\":true,\"checks\":%u,\"source_load_transactions\":%u,\"repeated_create_destroy\":%u,\"owned_static_bytes\":%u,\"owned_heap_bytes\":0,\"stack_reserve_bytes\":%u,\"open_calls\":%u,\"write_calls\":%u,\"close_calls\":%u,\"unlink_calls\":%u,\"cleanup_complete\":true,\"current_map_observed\":false,\"generation_admitted\":false,\"actor_or_ack_authority\":false}\n",checks,transactions,repeats,(unsigned)(sizeof(coh_body_witness)+sizeof(coh_body_witness_last_status)),COH_BODY_WITNESS_STACK_RESERVE,opens,writes,closes,unlinks);
 return 0;
}
