#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define SERVER 1
#define _WIN32 1
typedef unsigned DWORD;
static int initedBackgroundLoader,number_of_glds_in_background_loader,number_of_lods_in_background_loader;
static void*glds_ready_for_final_processing;
static DWORD background_loader_threadID,current_thread;
static unsigned geo_locked,lod_locked,geo_blocked,lod_blocked,attempts,releases,checks;
static unsigned heyThreadLoadAGeo_CriticalSection,heyThreadLODAModel_CriticalSection;
static DWORD GetCurrentThreadId(void){return current_thread;}
static int TryEnterCriticalSection(unsigned*lock){unsigned*held;attempts++;held=lock==&heyThreadLoadAGeo_CriticalSection?&geo_locked:&lod_locked;if((lock==&heyThreadLoadAGeo_CriticalSection?geo_blocked:lod_blocked)||*held)return 0;*held=1;return 1;}
static void LeaveCriticalSection(unsigned*lock){unsigned*held=lock==&heyThreadLoadAGeo_CriticalSection?&geo_locked:&lod_locked;if(!*held)abort();*held=0;releases++;}
#include "source_resource_quiescence.inc"
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"quiescence failure line%u\n",__LINE__);abort();}}while(0)
static void reset(void){CHECK(!coh_resource_quiet_active&&!geo_locked&&!lod_locked);initedBackgroundLoader=1;number_of_glds_in_background_loader=number_of_lods_in_background_loader=0;glds_ready_for_final_processing=NULL;background_loader_threadID=2;current_thread=1;geo_blocked=lod_blocked=attempts=releases=0;}
int main(void){unsigned i;
 reset();initedBackgroundLoader=0;CHECK(coh_resource_quiescence_begin()==2&&!attempts);
 reset();current_thread=2;CHECK(coh_resource_quiescence_begin()==4&&!attempts);
 reset();geo_blocked=1;CHECK(coh_resource_quiescence_begin()==5&&attempts==1&&!geo_locked&&!lod_locked&&!releases);
 reset();lod_blocked=1;CHECK(coh_resource_quiescence_begin()==6&&attempts==2&&!geo_locked&&!lod_locked&&releases==1);
 for(i=0;i<3;i++){
  reset();if(i==0)number_of_glds_in_background_loader=1;if(i==1)number_of_lods_in_background_loader=1;if(i==2)glds_ready_for_final_processing=&checks;
  CHECK(coh_resource_quiescence_begin()==7&&!geo_locked&&!lod_locked&&releases==2);
  CHECK(number_of_glds_in_background_loader==(i==0)&&number_of_lods_in_background_loader==(i==1)&&!!glds_ready_for_final_processing==(i==2));
 }
 reset();CHECK(coh_resource_quiescence_begin()==1&&geo_locked&&lod_locked&&coh_resource_quiet_active);
 CHECK(!number_of_glds_in_background_loader&&!number_of_lods_in_background_loader&&!glds_ready_for_final_processing);
 CHECK(coh_resource_quiescence_begin()==3&&geo_locked&&lod_locked&&attempts==2);
 current_thread=3;CHECK(coh_resource_quiescence_end()==0&&geo_locked&&lod_locked);
 current_thread=1;CHECK(coh_resource_quiescence_end()==1&&!geo_locked&&!lod_locked&&releases==2&&!coh_resource_quiet_active);
 CHECK(coh_resource_quiescence_end()==0&&!geo_locked&&!lod_locked);
 printf("{\"passed\":true,\"checks\":%u,\"actual_guard_source\":true,\"winapi_fixture_only\":true,\"runtime_executed\":false}\n",checks);return 0;
}
