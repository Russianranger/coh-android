/* Source-only lookup qualification. No catalog, runtime generation or packet API. */
#include <stdint.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern int sourcebone_lookup(const char *);
extern int sourcebone_is_valid(int);
extern unsigned sourcebone_row_count(void);
extern const char *sourcebone_row_name(unsigned);
extern int sourcebone_row_value(unsigned);

#define QUERY_MAX 259u
#define ROW_MAX 256u
#define QUERY_COUNT_MAX 4096u
#define FIXTURE_MAX (2u*1024u*1024u)
static unsigned long checks,lookups,mutations,invalid_profiles,alias_checks;
#define CHECK(x) do { checks++; if(!(x)) { fprintf(stderr,"check failed line %u: %s\n",__LINE__,#x); exit(1); } } while(0)

static uint32_t word(FILE *f) {
 unsigned char b[4]; CHECK(fread(b,1,4,f)==4);
 return (uint32_t)b[0]|(uint32_t)b[1]<<8|(uint32_t)b[2]<<16|(uint32_t)b[3]<<24;
}
static int overlap(const void *a,size_t an,const void *b,size_t bn) {
 uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
 if(!a||!b||an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
 return x<y+bn&&y<x+an;
}
/* An explicit qualification input profile, not a change to original lookup.
 * Caller supplies ASCII bytes without a terminator. This copies one bounded
 * query; invalid input or overlapping output leaves caller storage unchanged.
 * The result is the original raw integer, including unknown/sentinel values.
 * A successful query profile never admits runtime/body-catalog membership. */
static int profile_lookup(const unsigned char *query,size_t bytes,int *out) {
 char text[QUERY_MAX+1u];
 if(!query||!out||bytes>QUERY_MAX||overlap(query,bytes,out,sizeof(*out)))return 0;
 for(size_t i=0;i<bytes;i++)if(!query[i]||query[i]>127)return 0;
 memcpy(text,query,bytes);text[bytes]=0;
 int value=sourcebone_lookup(text);*out=value;return 1;
}
static void invalid(const unsigned char *query,size_t bytes,int *out) {
 int before=*out; CHECK(!profile_lookup(query,bytes,out));CHECK(*out==before);invalid_profiles++;
}

int main(int argc,char **argv) {
 if(argc!=2)return 2;
 FILE *f=fopen(argv[1],"rb");if(!f)return 2;
 CHECK(!fseek(f,0,SEEK_END));long extent=ftell(f);CHECK(extent>=0&&(unsigned long)extent<=FIXTURE_MAX);CHECK(!fseek(f,0,SEEK_SET));
 CHECK(word(f)==0x31454243u); /* CBE1 */
 unsigned bone_count=word(f),rows=word(f),queries=word(f);
 CHECK(bone_count>0&&bone_count<ROW_MAX&&rows>bone_count&&rows<=ROW_MAX&&queries>0&&queries<=QUERY_COUNT_MAX);
 CHECK(sourcebone_row_count()==rows);
 unsigned default_seen=0,count_seen=0,invalid_seen=0,aliases=0;
 for(unsigned i=0;i<rows;i++) {
  unsigned bytes=word(f);int value=(int32_t)word(f);char name[QUERY_MAX+1u];
  CHECK(bytes>0&&bytes<=QUERY_MAX&&fread(name,1,bytes,f)==bytes);name[bytes]=0;
  const char *actual=sourcebone_row_name(i);CHECK(actual&&strlen(actual)==bytes&&!memcmp(actual,name,bytes));
  CHECK(sourcebone_row_value(i)==value);CHECK(!!sourcebone_is_valid(value)==(value>=0&&(unsigned)value<bone_count));
  if(!strcmp(name,"DEFAULT")){CHECK(value==0);default_seen++;}
  if(!strcmp(name,"COUNT")){CHECK(value==(int)bone_count);count_seen++;}
  if(!strcmp(name,"INVALID")){CHECK(value==-1);invalid_seen++;}
  if(i&&value>=0&&value<(int)bone_count)for(unsigned j=0;j<i;j++)if(sourcebone_row_value(j)==value){aliases++;break;}
 }
 CHECK(default_seen==1&&count_seen==1&&invalid_seen==1&&aliases>0);
 CHECK(sourcebone_row_name(rows)==NULL&&sourcebone_row_name(UINT_MAX)==NULL);
 CHECK(sourcebone_row_value(rows)==INT_MIN&&sourcebone_row_value(UINT_MAX)==INT_MIN);
 CHECK(sourcebone_lookup(NULL)==-1);
 unsigned valid_ids=0,invalid_ids=0,case_queries=0,unknown_queries=0;
 for(unsigned i=0;i<queries;i++) {
  unsigned bytes=word(f);int expected=(int32_t)word(f);unsigned kind=word(f);unsigned char query[QUERY_MAX+1u],before[QUERY_MAX+1u];
  CHECK(bytes<=QUERY_MAX&&kind<=3&&fread(query,1,bytes,f)==bytes);query[bytes]=0;memcpy(before,query,bytes+1u);
  int value=INT_MIN;CHECK(profile_lookup(query,bytes,&value)&&value==expected);CHECK(!memcmp(before,query,bytes+1u));
  CHECK(sourcebone_lookup((const char*)query)==expected);lookups++;
  int numeric_id=value>=0&&(unsigned)value<bone_count;CHECK(!!sourcebone_is_valid(value)==numeric_id);valid_ids+=(unsigned)numeric_id;invalid_ids+=(unsigned)!numeric_id;
  if(!strcmp((const char*)query,"DEFAULT"))CHECK(numeric_id&&value==0);
  if(!strcmp((const char*)query,"COUNT")||!strcmp((const char*)query,"INVALID"))CHECK(!numeric_id);
  if(kind==1)case_queries++;
  if(kind==2)mutations++;
  if(kind==3)unknown_queries++;
 }
 CHECK(fgetc(f)==EOF);fclose(f);

 unsigned char edge[QUERY_MAX+2u];memset(edge,'!',sizeof(edge));int out=0x12345678;
 CHECK(profile_lookup(edge,QUERY_MAX,&out)&&out==-1);lookups++;
 invalid(edge,QUERY_MAX+1u,&out);invalid(NULL,0,&out);invalid(edge,SIZE_MAX,&out);
 edge[0]=0;invalid(edge,1,&out);edge[0]=128;invalid(edge,1,&out);edge[0]=255;invalid(edge,1,&out);
 edge[0]='H';edge[1]=0;edge[2]='I';invalid(edge,3,&out);
 CHECK(!profile_lookup(edge,0,NULL));invalid_profiles++;
 CHECK(profile_lookup(edge,0,&out)&&out==-1);lookups++;
 /* Aligned caller storage avoids undefined pointers in the alias controls. */
 union {int integer;unsigned char bytes[16];} alias;memset(&alias,'A',sizeof(alias));
 unsigned char saved[sizeof(alias)];memcpy(saved,&alias,sizeof(alias));
 CHECK(!profile_lookup(alias.bytes,8,&alias.integer)&&!memcmp(saved,&alias,sizeof(alias)));alias_checks++;
 CHECK(valid_ids&&invalid_ids&&case_queries&&unknown_queries&&mutations);
 printf("{\"checks\":%lu,\"generated_rows\":%u,\"source_bone_count\":%u,\"source_alias_rows\":%u,\"queries\":%lu,\"case_variant_queries\":%u,\"unknown_profile_queries\":%u,\"query_mutations\":%lu,\"numeric_in_range_results\":%u,\"numeric_out_of_range_results\":%u,\"invalid_profile_controls\":%lu,\"alias_controls\":%lu,\"maximum_query_bytes\":259,\"maximum_query_count\":4096,\"maximum_fixture_bytes\":2097152,\"maximum_result_json_bytes\":4096,\"original_parse_bone_names_executed\":false,\"current_map_runtime_executed\":false,\"body_catalog_admitted\":false,\"source_generation_admitted\":false,\"complete_initial_character\":false,\"actor_publication\":false,\"ack_permitted\":false,\"world_authority\":false}\n",checks,rows,bone_count,aliases,lookups,case_queries,unknown_queries,mutations,valid_ids,invalid_ids,invalid_profiles,alias_checks);
 return 0;
}
