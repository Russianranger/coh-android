#include "coh_catalog_seed.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"boundschecksum:%d %s\n",__LINE__,#x);abort();}}while(0)
static unsigned read32(FILE*f){unsigned char b[4];CHECK(fread(b,1,4,f)==4);return(unsigned)b[0]|(unsigned)b[1]<<8|(unsigned)b[2]<<16|(unsigned)b[3]<<24;}
int main(int argc,char**argv){CHECK(argc==2);FILE*f=fopen(argv[1],"rb");CHECK(f);unsigned cases=read32(f);CHECK(cases==256);
 for(unsigned c=0;c<cases;c++){
  char filename[256],names[8][256];unsigned char raw[8][60];CohSourceBoundsChecksumRow rows[8];unsigned n=read32(f);CHECK(n&&n<sizeof(filename)&&fread(filename,1,n,f)==n&&filename[n-1]==0);CHECK(read32(f)==8);unsigned expected=read32(f);
  for(unsigned i=0;i<8;i++){unsigned live=read32(f);n=read32(f);CHECK(n&&n<sizeof(names[i])&&fread(names[i],1,n,f)==n&&names[i][n-1]==0);CHECK(fread(raw[i],1,60,f)==60);rows[i]=(CohSourceBoundsChecksumRow){names[i],{raw[i],60},live};}
  CohSourceBoundsChecksumReport out,prior;memset(&out,0xa5,sizeof(out));prior=out;CHECK(coh_source_bounds_checksum(1,filename,rows,8,expected,&out)==COH_OK&&out.checksum==expected);CHECK(coh_source_bounds_checksum(0,filename,rows,8,expected,&prior)==COH_UNSUPPORTED);
  CohSourceBoundsChecksumReport guard=prior;CHECK(coh_source_bounds_checksum(1,filename,rows,8,expected^1,&prior)==COH_STATE&&!memcmp(&prior,&guard,sizeof(prior)));
  CHECK(coh_source_bounds_checksum(1,filename,rows,8,expected,(CohSourceBoundsChecksumReport*)rows)==COH_INVALID);
  {CohSourceBoundsChecksumRow saved=rows[6];rows[6].name=NULL;rows[6].in_use=1;CHECK(coh_source_bounds_checksum(1,filename,rows,8,expected,&prior)==COH_OK);rows[6]=saved;prior=guard;}
  /* Raw padding/high flag bits are hashed, never silently canonicalized. */
  if(out.public_records){unsigned i;for(i=0;i<8;i++)if(rows[i].in_use&&names[i][0]&&strncmp(names[i],"grp",3)&&strncmp(names[i],"GRP",3)&&names[i][strlen(names[i])-1]!='&')break;CHECK(i<8);raw[i][59]^=0x80;CHECK(coh_source_bounds_checksum(1,filename,rows,8,expected,&prior)==COH_STATE&&!memcmp(&prior,&guard,sizeof(prior)));raw[i][59]^=0x80;rows[i].raw_bounds.size=59;CHECK(coh_source_bounds_checksum(1,filename,rows,8,expected,&prior)==COH_STATE);}
 }
 CHECK(fgetc(f)==EOF);CHECK(!fclose(f));printf("{\"passed\":true,\"checks\":%u,\"original_checksum_cases\":%u,\"actual_bounds_available\":false}\n",checks,cases);return 0;
}
