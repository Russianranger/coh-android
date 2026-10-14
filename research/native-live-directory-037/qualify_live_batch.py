#!/usr/bin/env python3
"""Actual portable C decoder and extracted stock constructor research.

Real source-projection packet is a controlled historical input, not current
runtime metadata authority. No native Game/Wine/PRoot/FEX/SDK build is invoked.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
TOOLS=Path('/workspace/scratch/5d16603ca7ff/client-census-wine-037/tools')
sys.path.insert(0,str(TOOLS))
import test_native_client_metadata_census_source as existing
import map_startup_namespace_certificate as namespace
import prepare_native_client_metadata_census_source as candidate
import native_client_census_observed_bridge as observed
PACKET=Path('/workspace/scratch/5d16603ca7ff/native037-recovery/client-capture-Wine-failure-11868411104/evidence/native-client-metadata-capture/source-projection/source-projection.bin')
PACKET_SHA='f9429ee6e2888eedcf44c69ebecca1751e8225b0fa18a2a28fd906df54fd2bca'

def generate():
    stock=candidate.source_bytes().decode()
    node_source=candidate.bytes_lf(candidate.ROOT/'upstream/ouroboros'/candidate.NODE_SOURCE).decode()
    base=existing.harness().split('static int fwFindFirstFile(',1)[0]
    base=base.replace('#include "coh_folder_census_adapter.h"','#include "coh_live_directory_batch.h"')
    base=base.replace('static FixtureDirectory fixture_dirs[8];','static FixtureDirectory fixture_dirs[16384];')
    base=base.replace('WIN32_FIND_DATAA *rows;unsigned int count;','const unsigned char *rows;unsigned int count;')
    # This portable fixture applies one identical conversion stub to both paths.
    # The actual native winfiletime implementation is retained, not qualified here.
    add=namespace.function(node_source,'FolderNode *FolderNodeAdd(')
    slash=namespace.function(node_source,'static char *firstSlash(')
    constructor=namespace.function(stock,candidate.SIGNATURE)
    compare=existing.harness().split('static void destroy_nodes(',1)[1].split('static WIN32_FIND_DATAA entry(',1)[0]
    compare='static void destroy_nodes('+compare
    wrappers=r'''
static int use_bridge=0,bridge_failed=0;
static uint32_t batch_sequence, batch_first, batch_cursor;
static unsigned char batch_data[COH_LIVE_MAX_BYTES], operation[16]={1},directory_token[16]={2};
static CohLiveBatch batch;static CohLiveCursor cursor;
static unsigned long long batches, rows_checked, max_batch;
static int current_directory=-1;
static void p32(unsigned char *p,uint32_t v) {p[0]=v;p[1]=v>>8;p[2]=v>>16;p[3]=v>>24;}
static void load_batch(FixtureHandle *h) {
 unsigned int first=h->index,n=0,nt=0,bytes;const unsigned char *at;
 memset(batch_data,0,sizeof(batch_data));memcpy(batch_data,"COHLIVE1",8);
 memcpy(batch_data+8,operation,16);memcpy(batch_data+24,directory_token,16);
 while(first+n<h->directory->count&&n<COH_LIVE_MAX_ROWS) {
  unsigned int length;at=h->directory->rows+(first+n)*328u+8;
  length=(unsigned int)strlen((const char*)at+44);
  unsigned int next=((nt+7u)&~7u)+94u+length*2u;
  if(next>8192)break;nt=next;
  p32(batch_data+64+n*328u,first+n);memcpy(batch_data+64+n*328u+8,at,320);n++;
 }
 assert(n||first==h->directory->count);bytes=64+n*328u;
 p32(batch_data+40,batch_sequence);p32(batch_data+44,first);p32(batch_data+48,n);
 p32(batch_data+52,first+n==h->directory->count);p32(batch_data+60,bytes);
 assert(cohLiveSubmit(&cursor,batch_data,bytes));batch=cursor.batch;
 batches++;rows_checked+=n;if(bytes>max_batch)max_batch=bytes;batch_cursor=0;batch_first=first;batch_sequence++;
}
static void row_for(FixtureHandle *h,WIN32_FIND_DATAA *row) {
 if(!use_bridge){memcpy(row,h->directory->rows+h->index*328u+8,320);return;}
 assert(!bridge_failed);
 if(h->index<batch_first||h->index>=batch_first+batch.count)load_batch(h);
 batch_cursor=h->index-batch_first;
 const unsigned char *projection=cohLiveTake(&cursor);assert(projection);memcpy(row,projection,320);
 assert(!memcmp(row,h->directory->rows+h->index*328u+8,320));
}
static int fwFindFirstFile(U32 *handle,const char *search,WIN32_FIND_DATAA *row) {
 int i,j;char path[1024];size_t n=strlen(search);++find_first_calls;
 assert(n>2&&!strcmp(search+n-2,"/*"));memcpy(path,search,n-2);path[n-2]=0;
 for(i=0;i<directory_count;i++)if(!strcmp(path,fixture_dirs[i].path)&&fixture_dirs[i].count) {
  for(j=0;j<8;j++)if(!fixture_handles[j].open) {
   FixtureHandle *h=&fixture_handles[j];h->directory=&fixture_dirs[i];h->index=0;h->open=1;
   *handle=(U32)(j+1);batch_sequence=0;batch_first=UINT32_MAX;memset(&batch,0,sizeof(batch));
   current_directory=i;cohLiveInit(&cursor,operation,directory_token);row_for(h,row);return 1;
  }assert(0);
 }return 0;
}
static int fwFindNextFile(U32 handle,WIN32_FIND_DATAA *row) {
 FixtureHandle *h;assert(handle>0&&handle<=8);h=&fixture_handles[handle-1];assert(h->open);++find_next_calls;
 if(++h->index>=h->directory->count)return 0;row_for(h,row);return 1;
}
static void fwFindClose(U32 handle) {assert(handle>0&&handle<=8&&fixture_handles[handle-1].open);fixture_handles[handle-1].open=0;++find_close_calls;}
static void decoder_refusals(void) {
 unsigned char bad[COH_LIVE_MAX_BYTES];CohLiveBatch out;unsigned int bytes;
 FixtureHandle h={&fixture_dirs[0],0,1};cohLiveInit(&cursor,operation,directory_token);load_batch(&h);bytes=p32,0; /* replaced below */
}
'''
    wrappers=wrappers.replace('bytes=p32,0; /* replaced below */','''bytes=cohLiveU32(batch_data+60);
 assert(cohLiveBatchDecode(batch_data,bytes,operation,directory_token,0,0,&out));
 #define REFUSE(expression) do {memcpy(bad,batch_data,bytes);expression;memset(&out,0xff,sizeof(out));assert(!cohLiveBatchDecode(bad,bytes,operation,directory_token,0,0,&out));assert(!out.rows&&!out.count);} while(0)
 REFUSE(bad[0]^=1);REFUSE(bad[8]^=1);REFUSE(bad[24]^=1);REFUSE(p32(bad+40,1));
 REFUSE(p32(bad+44,1));REFUSE(p32(bad+48,86));REFUSE(p32(bad+52,2));REFUSE(p32(bad+56,1));
 REFUSE(p32(bad+60,bytes+1));REFUSE(p32(bad+64,1));REFUSE(p32(bad+68,1));
 REFUSE(bad[64+8+36]=1);REFUSE(bad[64+8+44]=1);
 assert(!cohLiveBatchDecode(batch_data,bytes-1,operation,directory_token,0,0,&out));
 #undef REFUSE
 /* Fail before first returned row allows stock; after one row never restarts. */
 {CohLiveCursor early,late;unsigned char first_row[320];
  cohLiveInit(&early,operation,directory_token);bad[0]='?';
  assert(!cohLiveSubmit(&early,bad,bytes)&&early.terminal_failure&&early.fallback_allowed);
  assert(!cohLiveSubmit(&early,batch_data,bytes)&&!cohLiveTake(&early));
  cohLiveInit(&late,operation,directory_token);assert(cohLiveSubmit(&late,batch_data,bytes));
  memcpy(first_row,cohLiveTake(&late),320);memset(bad,0,bytes);
  assert(!memcmp(first_row,batch_data+72,320));
  assert(!cohLiveSubmit(&late,bad,bytes)&&late.terminal_failure&&!late.fallback_allowed);
  assert(late.rows_returned==1&&!cohLiveTake(&late));
  assert(!cohLiveSubmit(&late,batch_data,bytes)&&late.rows_returned==1);
  /* Mutating caller's transport buffer cannot alter the owned current batch. */
  cohLiveInit(&late,operation,directory_token);memcpy(bad,batch_data,bytes);
  assert(cohLiveSubmit(&late,bad,bytes));memset(bad,0,bytes);
  assert(!memcmp(cohLiveTake(&late),batch_data+72,320));
  while(cohLiveTake(&late)) {}
  assert(late.finished);assert(!cohLiveSubmit(&late,batch_data,bytes)&&late.terminal_failure&&!late.fallback_allowed);
 }''')
    main=r'''
int main(int argc,char **argv) {
 unsigned char *packet;FILE *f;long length;unsigned int offset,count,i,record;static const char *branches[]={"texture_library","object_library","fx","scripts","scripts.loc"};
 assert(argc==2);f=fopen(argv[1],"rb");assert(f);fseek(f,0,SEEK_END);length=ftell(f);rewind(f);assert(length>64&&length<=64*1024*1024);
 packet=(unsigned char*)malloc((size_t)length);assert(packet&&fread(packet,1,(size_t)length,f)==(size_t)length);fclose(f);
 count=cohLiveU32(packet+16);record=cohLiveU32(packet+24);assert(count<=16384);offset=64;
 for(i=0;i<count;i++) {
  unsigned int name_length=packet[offset]|((unsigned int)packet[offset+1]<<8),first=cohLiveU32(packet+offset+4),rows=cohLiveU32(packet+offset+8);
  assert(name_length<260&&offset+16+name_length<=record&&record+(size_t)(first+rows)*328u<=(size_t)length);
  memcpy(fixture_dirs[i].path,"fixture/",8);memcpy(fixture_dirs[i].path+8,packet+offset+16,name_length);fixture_dirs[i].path[8+name_length]=0;
  fixture_dirs[i].count=rows;fixture_dirs[i].rows=packet+record+(size_t)first*328u;offset=(offset+16+name_length+3)&~3;
 }directory_count=count;decoder_refusals();batches=rows_checked=max_batch=0;
 for(i=0;i<5;i++) {
  FolderCache baseline={0},changed={0};char path[1024];int files,folders;
  snprintf(path,sizeof(path),"fixture/%s",branches[i]);count_file=count_folder=0;use_bridge=0;
  stockConstructor(&baseline,&baseline.root,&baseline.root_tail,NULL,path,0);files=count_file;folders=count_folder;
  count_file=count_folder=0;use_bridge=1;
  stockConstructor(&changed,&changed.root,&changed.root_tail,NULL,path,0);
  assert(files==count_file&&folders==count_folder);
  assert_equal_nodes(baseline.root,changed.root,NULL,NULL,baseline.root_tail,changed.root_tail);
  assert(provider_digest(baseline.root,"")==provider_digest(changed.root,""));
  destroy_nodes(baseline.root);destroy_nodes(changed.root);
 }
 printf("COH_LIVE_SOURCE_PARITY_PASS branches=5 refusal_controls=14 terminal_custody_controls=4 rows=%llu buffers=%llu max_packet_bytes=%llu packet_limit=%u cursor_owned_bytes=%lu actual_native_API=0 provider_authority=0\n",rows_checked,batches,max_batch,(unsigned int)COH_LIVE_MAX_BYTES,(unsigned long)sizeof(CohLiveCursor));
 free(packet);return 0;
}
'''
    return base+wrappers+slash+'\n'+add+'\n'+constructor.replace('FolderCacheAddFolderToNode(','stockConstructor(')+'\n'+compare+main

def main():
    started=time.monotonic();packet=PACKET.read_bytes()
    assert hashlib.sha256(packet).hexdigest()==PACKET_SHA
    view=observed.decode(packet);del packet
    code=generate();c=ROOT/'portable-live-parity.c';c.write_text(code)
    compiler=shutil.which('cc');assert compiler,'Required portable C compiler missing'
    build=subprocess.run([compiler,'-std=c11','-O2','-Wall','-Wextra','-I',str(ROOT),str(c),'-o',str(ROOT/'portable-live-parity')],capture_output=True,text=True)
    assert build.returncode==0,build.stderr
    launch=time.monotonic()
    with (ROOT/'portable-live-parity.stdout').open('wb') as out,(ROOT/'portable-live-parity.stderr').open('wb') as err:
        process=subprocess.Popen([str(ROOT/'portable-live-parity'),str(PACKET)],stdout=out,stderr=err)
        _,status,usage=os.wait4(process.pid,0);process.returncode=os.waitstatus_to_exitcode(status)
    output=(ROOT/'portable-live-parity.stdout').read_text();errors=(ROOT/'portable-live-parity.stderr').read_text()
    assert process.returncode==0,output+errors
    result={'format':1,'role':'portable_extracted_stock_constructor_live_batch_parity',
      'status':'passed_portable_source_controls','stdout':output.strip(),'stderr':errors,
      'portable_C_process':{'wall_seconds':time.monotonic()-launch,'user_seconds':usage.ru_utime,
        'system_seconds':usage.ru_stime,'max_RSS_KiB':usage.ru_maxrss,'minor_page_faults':usage.ru_minflt,
        'major_page_faults':usage.ru_majflt,'input_blocks':usage.ru_inblock,'output_blocks':usage.ru_oublock},
      'packet':{'bytes':PACKET.stat().st_size,'sha256':PACKET_SHA,'directories':len(view.directories),'rows':view.row_count},
      'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'C_harness_sha256':hashlib.sha256(code.encode()).hexdigest(),
      'batch_header_sha256':hashlib.sha256((ROOT/'coh_live_directory_batch.h').read_bytes()).hexdigest(),
      'original_constructor_sha256':hashlib.sha256(candidate.source_bytes()).hexdigest(),
      'exact_FolderNodeAdd_source_sha256':hashlib.sha256(candidate.bytes_lf(candidate.ROOT/'upstream/ouroboros'/candidate.NODE_SOURCE)).hexdigest(),
      'compiler':subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],
      'elapsed_total_seconds':time.monotonic()-started,
      'whole_historical_packet_loaded_only_for_controlled_parity':True,
      'timestamp_conversion_identical_fixture_stub_not_native_qualification':True,
      'whole_census_proof_performed_by_live_decoder':False,
      'field_order_and_complete_stock_node_effects_equal_for_historical_source_projection':True,
      'actual_POSIX_server_or_Wine_API_or_PRooot_FEX_Game_executed':False,
      'provider_authority':False,'native_registration_allowed':False,'publication_allowed':False,'device_speedup_measured':False}
    (ROOT/'portable-live-parity-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
