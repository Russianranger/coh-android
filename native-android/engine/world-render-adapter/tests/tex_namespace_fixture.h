#ifndef TEX_NAMESPACE_FIXTURE_H
#define TEX_NAMESPACE_FIXTURE_H
#include "../coh_wr_tex_namespace.h"
typedef struct {
 const char *path;
 CohBytes body;
 int32_t timestamp,location,file_index;
 uint32_t directory;
} NamespaceOracleFile;
typedef struct {
 char key[128],directory[1000],original[1024];
 uint8_t mips[1024];
 uint32_t first,width,height,flags,mip_bytes,offset,bytes;
 int32_t location,timestamp,file_index;
} NamespaceOracleBasic;
void original_namespace(const NamespaceOracleFile*,uint32_t,uint32_t,uint32_t,
 const char*const*,uint32_t,uint32_t,uint32_t,
 const NamespaceOracleBasic*,uint32_t,NamespaceOracleBasic*,uint32_t*);
#endif
