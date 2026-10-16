/* Read-only independent sizing harness; uses existing committed record decoder.
 * No catalog/graph publication, payload mutation or complete scene claim. */
#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include "coh_scenecatalog.c"
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*f=fopen(argv[1],"rb");if(!f)return 3;
 if(fseek(f,0,SEEK_END)||ftell(f)<0)return 4;
 size_t bytes=(size_t)ftell(f);if(bytes>COH_CATALOG_INPUT_MAX||bytes<48)return 5;
 rewind(f);uint8_t*input=malloc(bytes);if(!input||fread(input,1,bytes,f)!=bytes)return 6;fclose(f);
 CohCatalogReport report;CohStatus status=coh_scenecatalog_preflight((CohBytes){input,bytes},le32(input+20),&report);
 if(status!=COH_OK){printf("{\"preflight_status\":%u}\n",status);free(input);return 7;}
 Scan s={0};s.input=(CohBytes){input,bytes};s.at=48;
 uint64_t defs=0,in_use=0,children=0,swaps=0,wire=0,record_bytes=0,child_bytes=0,swap_bytes=0;
 uint64_t def_strings=0,child_strings=0,swap_strings=0,file_strings=0;
 size_t max_record=0,max_owned=0,max_children=0,max_swaps=0,max_def_name=0,max_child_name=0;
 uint32_t max_file=0,max_slot=0;
 for(uint32_t fi=0;fi<report.files;fi++){
  uint32_t index,crc,slots,records,n; if(read32(&s,&index)||read32(&s,&crc)||read32(&s,&slots)||read32(&s,&records)||read32(&s,&n))return 8;
  file_strings+=n;s.at+=n;
  for(uint32_t di=0;di<records;di++){
   uint32_t id,bits,nbytes,aligned;if(read32(&s,&id)||read32(&s,&bits)||read32(&s,&nbytes)||read32(&s,&aligned))return 9;
   CohRepReader r;CohSgDefinition d={0};size_t owned=0;
   status=coh_rep_reader_bounded(&r,(CohBytes){input+s.at,nbytes},bits,(int)aligned,COH_REP_BOUNDED_MESSAGE_MAX);
   if(status==COH_OK)status=coh_scenegraph_definition_read(&d,&r,fi,COH_CATALOG_MEMORY_MAX,&owned);
   if(status!=COH_OK||r.cursor!=bits){printf("{\"record_status\":%u,\"file\":%u,\"slot\":%u,\"fully_decoded_before\":%"PRIu64"}\n",status,fi,id,defs);coh_scenegraph_definition_dispose(&d);free(input);return 10;}
   defs++;in_use+=d.in_use;children+=d.child_count;swaps+=d.swap_count;wire+=d.wire_bytes;record_bytes+=nbytes;
   child_bytes+=(uint64_t)d.child_count*sizeof(CohSgChild);swap_bytes+=(uint64_t)d.swap_count*sizeof(CohSgSwap);
   def_strings+=strlen(d.name)+strlen(d.geometry)+strlen(d.textures[0])+strlen(d.textures[1])+4;
   if(strlen(d.name)>max_def_name)max_def_name=strlen(d.name);
   for(uint32_t j=0;j<d.child_count;j++){size_t len=strlen(d.children[j].name);child_strings+=len+1;if(len>max_child_name)max_child_name=len;}
   for(uint32_t j=0;j<d.swap_count;j++)swap_strings+=strlen(d.swaps[j].original)+strlen(d.swaps[j].replacement)+2;
   if(nbytes>max_record)max_record=nbytes;
   if(owned>max_owned){max_owned=owned;max_file=fi;max_slot=id;}
   if(d.child_count>max_children)max_children=d.child_count;
   if(d.swap_count>max_swaps)max_swaps=d.swap_count;
   coh_scenegraph_definition_dispose(&d);s.at+=nbytes;
  }
 }
 printf("{\"scope\":\"read-only existing-record-decoder allocation payload ledger; no graph or source-generation admission\",\"input_bytes\":%zu,\"generation\":%u,\"files\":%u,\"definitions\":%"PRIu64",\"in_use\":%"PRIu64",\"children\":%"PRIu64",\"swaps\":%"PRIu64",\"definition_record_bytes\":%"PRIu64",\"definition_body_bytes\":%"PRIu64",\"child_array_bytes\":%"PRIu64",\"swap_array_bytes\":%"PRIu64",\"actual_definition_strings_bytes\":%"PRIu64",\"actual_child_strings_bytes\":%"PRIu64",\"actual_swap_strings_bytes\":%"PRIu64",\"actual_file_strings_bytes\":%"PRIu64",\"catalog_minimum_owned_bytes\":%zu,\"catalog_eager_total_payload_bytes\":%"PRIu64",\"max_record_bytes\":%zu,\"max_record_dynamic_payload_bytes\":%zu,\"max_record_file\":%u,\"max_record_slot\":%u,\"max_record_children\":%zu,\"max_record_swaps\":%zu,\"max_definition_name_bytes_without_nul\":%zu,\"max_child_name_bytes_without_nul\":%zu,\"sizeof\":{\"catalog\":%zu,\"catalog_file\":%zu,\"definition\":%zu,\"child\":%zu,\"swap\":%zu,\"graph\":%zu,\"file\":%zu,\"root\":%zu,\"index_entry\":%zu},\"complete_record_decode\":true,\"complete_scene_verified\":false,\"actual_android_rss_measured\":false}\n",bytes,report.generation,report.files,defs,in_use,children,swaps,record_bytes,wire,child_bytes,swap_bytes,def_strings,child_strings,swap_strings,file_strings,report.minimum_owned_bytes,(uint64_t)report.minimum_owned_bytes+wire+child_bytes+swap_bytes,max_record,max_owned,max_file,max_slot,max_children,max_swaps,max_def_name,max_child_name,sizeof(CohSceneCatalog),sizeof(CatalogFile),sizeof(CohSgDefinition),sizeof(CohSgChild),sizeof(CohSgSwap),sizeof(CohSceneGraph),sizeof(CohSgFile),sizeof(CohSgRoot),sizeof(CohSgIndexEntry));
 free(input);return s.at==bytes?0:11;
}
