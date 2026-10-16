#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#define __cdecl
#define CLIENT 0
#define MAX_PATH 260
#define LOAD_HEADER 1
#define GEO_DONT_INIT_FOR_DRAWING 2
#define GEO_USED_BY_WORLD 4
#define GEO_USE_MASK 4
#define OUTPUT_VERBOSE 0
#define PERFINFO_AUTO_START(...) ((void)0)
#define PERFINFO_AUTO_STOP(...) ((void)0)
#define PERFINFO_AUTO_STOP_CHECKED(...) ((void)0)
#define writeConsole(...) ((void)0)
#define min(a,b) ((a)<(b)?(a):(b))
#define strnicmp strncasecmp
#define stricmp strcasecmp
#define strstriConst strstr
#define strncpyt(dst,src,n) do {snprintf((dst),(n),"%s",(src));} while(0)
#define strcpy_s(dst,n,src) do {assert(strlen(src)<(n));strcpy((dst),(src));} while(0)
#define strcat_s(dst,n,src) do {assert(strlen(dst)+strlen(src)<(n));strcat((dst),(src));} while(0)
#define changeFileExt(src,ext,out) changeFileExt_s((src),(ext),(out),sizeof(out))
typedef struct {char *name;int namelen_notrick;unsigned slot,file;}Model;
typedef struct {Model**models;int model_count;}ModelHeader;
typedef struct {unsigned geo_use_type;ModelHeader modelheader;}GeoLoadData;
typedef struct {const char*name;unsigned slot;}GroupFileEntry;
typedef struct {const char*name;int dir_idx;}GroupLibNameEntry;
typedef struct {const char*name;int namelen;}ModelSearchData;
static GroupFileEntry*file_rows[16];
static GroupLibNameEntry*library_rows[32];
static struct {GroupFileEntry**group_files;GroupLibNameEntry**group_libnames;}group_names={file_rows,library_rows};
static void*group_name_hashes;
static GeoLoadData*useThisGeoLoadData;
static GeoLoadData geos[16];
static char geo_paths[16][260];
#define eaSize(x) 16
/* The original StashDefault ASCII comparison is represented by this explicit
 * fixture table. Full StashTable and geoLoad/archive I/O are not executed. */
static bool stashFindInt(void*table,const char*key,int*out){
    (void)table;
    for(unsigned i=0;i<32;i++)if(library_rows[i]&&!strcasecmp(key,library_rows[i]->name)){*out=(int)i;return true;}
    return false;
}
static GeoLoadData*geoLoad(const char*filename,int load_type,int use_type){
    (void)load_type;(void)use_type;
    for(unsigned i=0;i<16;i++)if(file_rows[i]&&!strcmp(geo_paths[i],filename))return &geos[i];
    return NULL;
}
