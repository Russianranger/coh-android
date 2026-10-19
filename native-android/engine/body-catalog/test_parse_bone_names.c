/* Source callback fixture only: no runtime catalog, generation or packet API. */
#include "parse-bone-names-provider.h"
#include "../costume-inputs/coh_costume_inputs.h"
#include <limits.h>
#include <openssl/sha.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned long checks,successes,refusals,derived_mutations,case_controls,alias_controls;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"check failed line %u: %s\n",__LINE__,#x);exit(1);}}while(0)
static uint32_t word(FILE*f){unsigned char b[4];CHECK(fread(b,1,4,f)==4);return(uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;}
static void text(FILE*f,char*out){unsigned n=word(f);CHECK(n<260&&fread(out,1,n,f)==n);out[n]=0;}
static CohStatus digest(void*context,CohBytes b,uint8_t out[32]){(void)context;return SHA256(b.data,b.size,out)?COH_OK:COH_STATE;}
static void applied(const SourcePartInput*in,size_t count,SourcePartOutput*out,SourcePartsReceipt*r){
 SourcePartInput before[SOURCEPARTS_PART_MAX];CHECK(count<=SOURCEPARTS_PART_MAX);memcpy(before,in,count*sizeof(*in));
 CHECK(sourceparts_is_idle());CHECK(sourceparts_apply(in,count,1,out,r)==SOURCEPARTS_OK);CHECK(sourceparts_is_idle());
 CHECK(!memcmp(in,before,count*sizeof(*in)));unsigned calls=0;for(size_t i=0;i<count;i++)calls+=(unsigned)in[i].num_parts;
 CHECK(r->callback_executed==1&&r->callback_return==1&&r->count==count&&r->lookup_calls==calls&&r->source_count==count);successes++;
}
static void refused(const SourcePartInput*in,size_t count,unsigned association,SourcePartOutput*out,SourcePartsReceipt*r,int status){
 unsigned char oldout[sizeof(SourcePartOutput)*30],oldreceipt[sizeof(*r)];memcpy(oldout,out,sizeof(oldout));memcpy(oldreceipt,r,sizeof(oldreceipt));
 CHECK(sourceparts_is_idle());CHECK(sourceparts_apply(in,count,association,out,r)==status);CHECK(sourceparts_is_idle());
 CHECK(!memcmp(oldout,out,sizeof(oldout))&&!memcmp(oldreceipt,r,sizeof(oldreceipt)));refusals++;
}
static void baseline(SourcePartInput*in,SourcePartOutput*out,SourcePartsReceipt*r){
 memset(in,0,sizeof(*in)*30);memset(out,0xa5,sizeof(*out)*30);memset(r,0x5a,sizeof(*r));
 for(unsigned i=0;i<30;i++){in[i].name_geo=(const unsigned char*)"HIPS";in[i].name_bytes=4;in[i].num_parts=1;in[i].bone_num[0]=INT_MIN;in[i].bone_num[1]=(int32_t)(1000+i);in[i].part_index=INT_MAX;}
}
static void domains(void){
 SourcePartInput in[30];SourcePartOutput out[30];SourcePartsReceipt r;baseline(in,out,&r);
 /* Original accepts empty source lists; non-NULL profile arguments stay required. */
 applied(in,0,out,&r);CHECK(!r.lookup_calls&&!r.source_count);
 applied(in,29,out,&r);for(unsigned i=0;i<29;i++)CHECK(out[i].bone_num[0]==0&&out[i].bone_num[1]==(int32_t)(1000+i)&&out[i].part_index==(int32_t)i);
 baseline(in,out,&r);refused(in,30,1,out,&r,SOURCEPARTS_LIMIT);refused(in,SIZE_MAX,1,out,&r,SOURCEPARTS_LIMIT);
 refused(in,1,0,out,&r,SOURCEPARTS_STATE);refused(in,1,2,out,&r,SOURCEPARTS_STATE);
 for(unsigned n=0;n<4;n++){in[0].num_parts=n==0?0:n==1?3:n==2?-1:INT_MAX;refused(in,1,1,out,&r,SOURCEPARTS_INVALID);}baseline(in,out,&r);
 /* Late preflight failures must not publish an earlier valid row. */
 in[28].num_parts=0;refused(in,29,1,out,&r,SOURCEPARTS_INVALID);in[28].num_parts=1;
 in[28].name_geo=NULL;refused(in,29,1,out,&r,SOURCEPARTS_INVALID);baseline(in,out,&r);
 unsigned char name[261];memset(name,'!',sizeof(name));
 in[0].name_geo=name;in[0].name_bytes=259;applied(in,1,out,&r);CHECK(out[0].bone_num[0]==-1&&out[0].bone_num[1]==1000);
 in[0].name_bytes=260;refused(in,1,1,out,&r,SOURCEPARTS_LIMIT);in[0].name_bytes=SIZE_MAX;refused(in,1,1,out,&r,SOURCEPARTS_LIMIT);
 in[0].num_parts=2;in[0].name_bytes=126;applied(in,1,out,&r);CHECK(out[0].bone_num[0]==-1&&out[0].bone_num[1]==-1&&r.lookup_calls==2);
 in[0].name_bytes=127;refused(in,1,1,out,&r,SOURCEPARTS_LIMIT);
 in[0].name_bytes=126;name[125]=0;refused(in,1,1,out,&r,SOURCEPARTS_INVALID);name[125]=128;refused(in,1,1,out,&r,SOURCEPARTS_INVALID);name[125]=255;refused(in,1,1,out,&r,SOURCEPARTS_INVALID);name[125]='!';
 in[0].name_geo=(const unsigned char*)"";in[0].name_bytes=0;applied(in,1,out,&r);CHECK(out[0].bone_num[0]==-1&&out[0].bone_num[1]==-1);
 in[0].num_parts=1;in[0].bone_num[1]=-123;applied(in,1,out,&r);CHECK(out[0].bone_num[0]==-1&&out[0].bone_num[1]==-123);
 const char*names[]={"DEFAULT","INVALID","COUNT","not_a_bone","HIPS","LARM"};const int expected[]={0,-1,99,-1,0,9};
 for(unsigned i=0;i<6;i++){baseline(in,out,&r);in[0].name_geo=(const unsigned char*)names[i];in[0].name_bytes=strlen(names[i]);in[0].num_parts=i==5?2:1;applied(in,1,out,&r);CHECK(out[0].bone_num[0]==expected[i]);if(i==5)CHECK(out[0].bone_num[1]==10);}
 baseline(in,out,&r);refused(NULL,1,1,out,&r,SOURCEPARTS_INVALID);
 SourcePartsReceipt saved=r;CHECK(sourceparts_apply(in,1,1,NULL,&r)==SOURCEPARTS_INVALID&&!memcmp(&r,&saved,sizeof(r))&&sourceparts_is_idle());refusals++;
 SourcePartOutput savedout[30];memcpy(savedout,out,sizeof(out));CHECK(sourceparts_apply(in,1,1,out,NULL)==SOURCEPARTS_INVALID&&!memcmp(out,savedout,sizeof(out))&&sourceparts_is_idle());refusals++;
 /* Overlapping row/name/output/receipt storage refuses before original state. */
 baseline(in,out,&r);SourcePartInput savedin[30];memcpy(savedin,in,sizeof(in));saved=r;
 CHECK(sourceparts_apply(in,1,1,(SourcePartOutput*)(void*)in,&r)==SOURCEPARTS_INVALID&&!memcmp(in,savedin,sizeof(in))&&!memcmp(&r,&saved,sizeof(r))&&sourceparts_is_idle());alias_controls++;
 CHECK(sourceparts_apply(in,1,1,out,(SourcePartsReceipt*)(void*)in)==SOURCEPARTS_INVALID&&!memcmp(in,savedin,sizeof(in))&&!memcmp(out,savedout,sizeof(out))&&sourceparts_is_idle());alias_controls++;
 saved=r;memcpy(savedout,out,sizeof(out));CHECK(sourceparts_apply(in,2,1,out,(SourcePartsReceipt*)(void*)out)==SOURCEPARTS_INVALID&&!memcmp(out,savedout,sizeof(out))&&!memcmp(&r,&saved,sizeof(r))&&sourceparts_is_idle());alias_controls++;
 for(unsigned which=0;which<3;which++){baseline(in,out,&r);in[0].name_geo=which==0?(const unsigned char*)(const void*)in:which==1?(const unsigned char*)(const void*)out:(const unsigned char*)(const void*)&r;in[0].name_bytes=4;refused(in,1,1,out,&r,SOURCEPARTS_INVALID);alias_controls++;}
 baseline(in,out,&r);in[0].name_geo=(const unsigned char*)(uintptr_t)(UINTPTR_MAX-1u);in[0].name_bytes=4;refused(in,1,1,out,&r,SOURCEPARTS_INVALID);
}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*f=fopen(argv[1],"rb");if(!f)return 2;CHECK(word(f)==0x314e5043u);size_t bytes=word(f);unsigned count=word(f);uint8_t hash[32];CHECK(bytes==2584&&count==28&&fread(hash,1,32,f)==32);unsigned char*raw=malloc(bytes);CHECK(raw&&fread(raw,1,bytes,f)==bytes);
 CohCostumeInputWorkspace*w=calloc(1,sizeof(*w));CohCostumeInput*decoded=calloc(1,sizeof(*decoded));CHECK(w&&decoded);CohCostumeImportDigest d={digest,NULL,0,65536};
 CHECK(coh_costume_input_read((CohBytes){raw,bytes},COH_COSTUME_INPUT_BODY_PARTS,hash,&d,w,decoded,COH_COSTUME_INPUT_BUDGET_MAX,65536)==COH_OK);
 CHECK(decoded->part_count==count&&decoded->end_byte==bytes&&!memcmp(decoded->payload_sha256,hash,32));CHECK(!decoded->original_callbacks_applied&&!decoded->authentic_stash_slots&&!decoded->actor_authority);
 SourcePartInput input[30];SourcePartOutput output[30],expected[30];SourcePartsReceipt receipt;baseline(input,output,&receipt);unsigned genuine_unknown=0;
 for(unsigned i=0;i<count;i++){
  const CohCostumeInputPart*p=&decoded->parts[i];char fields[5][260];for(unsigned k=0;k<5;k++)text(f,fields[k]);
  CHECK(!strcmp(fields[0],p->name)&&!strcmp(fields[1],p->source_file)&&!strcmp(fields[2],p->geometry_name)&&!strcmp(fields[3],p->texture_name)&&!strcmp(fields[4],p->base_name));
  uint32_t words[7];for(unsigned k=0;k<7;k++)words[k]=word(f);CHECK(words[0]==p->bone_count_first&&words[1]==p->influence_cost&&words[2]==p->bone_count_last&&words[3]==p->dont_clear_word&&words[4]==p->bones[0]&&words[5]==p->bones[1]&&words[6]==p->part_index);
  expected[i].bone_num[0]=(int32_t)word(f);expected[i].bone_num[1]=(int32_t)word(f);expected[i].part_index=(int32_t)word(f);genuine_unknown+=expected[i].bone_num[0]==-1;
  input[i].name_geo=(const unsigned char*)p->geometry_name;input[i].name_bytes=strlen(p->geometry_name);input[i].num_parts=(int32_t)p->bone_count_last;input[i].bone_num[0]=(int32_t)p->bones[0];input[i].bone_num[1]=(int32_t)p->bones[1];input[i].part_index=(int32_t)p->part_index;
 }
 CHECK(fgetc(f)==EOF);fclose(f);applied(input,count,output,&receipt);CHECK(!memcmp(output,expected,count*sizeof(*output))&&receipt.lookup_calls==30&&receipt.source_count==28);
 /* Changing cached numbers proves source recomputation, including preservation
  * of the unused second number for single parts. */
 for(unsigned i=0;i<count;i++){
  SourcePartInput changed[30];memcpy(changed,input,sizeof(changed));changed[i].bone_num[0]=INT_MIN;changed[i].bone_num[1]=-10000-(int32_t)i;changed[i].part_index=INT_MAX;
  applied(changed,count,output,&receipt);for(unsigned j=0;j<count;j++){SourcePartOutput want=expected[j];if(i==j&&changed[j].num_parts==1)want.bone_num[1]=changed[j].bone_num[1];CHECK(!memcmp(output+j,&want,sizeof(want)));}derived_mutations++;
 }
 for(unsigned i=0;i<count;i++){
  SourcePartInput changed[30];unsigned char lower[260];memcpy(changed,input,sizeof(changed));memcpy(lower,changed[i].name_geo,changed[i].name_bytes);for(size_t j=0;j<changed[i].name_bytes;j++)if(lower[j]>='A'&&lower[j]<='Z')lower[j]=(unsigned char)(lower[j]+('a'-'A'));changed[i].name_geo=lower;
  applied(changed,count,output,&receipt);CHECK(!memcmp(output,expected,count*sizeof(*output)));case_controls++;
 }
 SourcePartInput reversed[30];for(unsigned i=0;i<count;i++)reversed[i]=input[count-1u-i];applied(reversed,count,output,&receipt);for(unsigned i=0;i<count;i++)CHECK(output[i].part_index==(int32_t)i&&output[i].bone_num[0]==expected[count-1u-i].bone_num[0]&&output[i].bone_num[1]==expected[count-1u-i].bone_num[1]);derived_mutations++;
 domains();CHECK(genuine_unknown==6&&sourceparts_is_idle());free(decoded);free(w);free(raw);
 printf("{\"checks\":%lu,\"authentic_CLIENT_rows\":28,\"authentic_lookup_calls\":30,\"authentic_unknown_first_bones\":%u,\"successful_callback_transactions\":%lu,\"bounded_profile_refusals\":%lu,\"derived_field_mutation_controls\":%lu,\"ASCII_case_controls\":%lu,\"alias_controls\":%lu,\"qualification_part_max\":29,\"original_source_count_max_exclusive\":60,\"paired_name_max\":126,\"single_name_max\":259,\"unknown_minus_one_preserved\":true,\"single_second_bone_preserved\":true,\"original_ParseBoneNames_executed\":true,\"original_GetBodyPartCount_executed\":true,\"original_full_Parse6_executed\":false,\"current_Map_runtime_executed\":false,\"runtime_body_catalog_admitted\":false,\"dictionary_imported\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}\n",checks,genuine_unknown,successes,refusals,derived_mutations,case_controls,alias_controls);return 0;
}
