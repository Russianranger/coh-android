#include <strings.h>
#define strnicmp strncasecmp
static int objectLibraryLoadBoundsFile(const char*n,U32 c){(void)n;(void)c;return 1;}
static void objectLibraryWriteBoundsFile(GroupFile*f){(void)f;abort();}
/* ORIGINAL_FUNCTIONS_HERE */
/* Original groupInLib/groupIsPrivate/groupIsPublic and writer function inserted
 * unchanged immediately above this fixture by the hash-pinned qualifier. */
static void bounds_u32(FILE*f,unsigned v){unsigned char b[4]={(unsigned char)v,(unsigned char)(v>>8),(unsigned char)(v>>16),(unsigned char)(v>>24)};assert(fwrite(b,1,4,f)==4);}
int main(int argc,char**argv){FILE*out;unsigned mode,row,b;assert(argc==2);out=fopen(argv[1],"wb");assert(out);bounds_u32(out,256);
 for(mode=0;mode<256;mode++){
  GroupFile file;GroupDef defs[8];GroupDef*ptrs[8];const char*files[]={"object_library/test.txt","OBJECT_LIBRARY/test.txt","object_libraryX/test.txt","maps/no_public.txt"};const char*names[]={"PublicA","grpLocal","Private&","GRPUpper","public_a&","Other","","grp"};
  memset(&file,0,sizeof(file));memset(defs,0,sizeof(defs));file.idx=1;file.fullname=(char*)files[mode%4];file.count=8;file.defs=ptrs;
  for(row=0;row<8;row++){ptrs[row]=&defs[row];defs[row].file=&file;defs[row].name=(char*)names[row];defs[row].in_use=(mode>>(row%8))&1;if(row==6)defs[row].in_use=0;
   for(b=0;b<sizeof(GroupBounds);b++)((unsigned char*)defs[row].min)[b]=(unsigned char)(mode*13+row*17+b*19);
  }
  assert(sizeof(GroupBounds)==60);objectLibraryWriteBoundsFileIfDifferent(&file);
  bounds_u32(out,(unsigned)strlen(file.fullname)+1);assert(fwrite(file.fullname,1,strlen(file.fullname)+1,out)==strlen(file.fullname)+1);bounds_u32(out,8);bounds_u32(out,file.bounds_checksum);
  for(row=0;row<8;row++){bounds_u32(out,(unsigned)defs[row].in_use);bounds_u32(out,(unsigned)strlen(defs[row].name)+1);assert(fwrite(defs[row].name,1,strlen(defs[row].name)+1,out)==strlen(defs[row].name)+1);assert(fwrite(defs[row].min,1,60,out)==60);}
 }
 assert(!fclose(out));puts("{\"fixtures\":256,\"original_functions_unchanged\":true,\"source_runtime\":false}");return 0;
}
