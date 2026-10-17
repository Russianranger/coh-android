"""Execute unchanged original model-name selection with explicit stash/log observers."""
from pathlib import Path

def create(root,extract):
 source=(Path(root)/'upstream/ouroboros/Common/seq/tricks.c').read_text()
 function=extract(source,'TrickInfo *trickFromObjectName(')
 directory=extract((Path(root)/'upstream/ouroboros/libs/UtilitiesLib/src/utils/utils_opt.c').read_text(),'char *getDirectoryName(')
 prefix=r'''
#include <assert.h>
#include <string.h>
#include <stdint.h>
#include <stddef.h>
#include <stdarg.h>
#include "trick_model_oracle.h"
#define TRICK_MODEL_ORACLE_ONLY 1
#include "trick-model-fixtures.h"
#define MAX_PATH 260
typedef struct {uint32_t ordinal;} TrickInfo;
static struct {int trick_name_hashes;} trick_list={1};
static int trick_report_exist_errors;
static TrickModelOracleResult observed;
static TrickInfo selected;
static unsigned fold(unsigned c){return c>='A'&&c<='Z'?c+32:c;}
static int same(const char*a,const char*b){while(*a&&*b){if(fold((unsigned char)*a++)!=fold((unsigned char)*b++))return 0;}return *a==*b;}
/* Original setupTrick registers in reverse order with overwrite=false. This
 * observer searches independently decoded original row order, highest first. */
static void stashFindPointer(int table,const char*key,TrickInfo**out){
 assert(table==1&&strlen(key)<sizeof(observed.key));
 observed.lookups++;strcpy(observed.key,key);*out=NULL;
 for(size_t i=sizeof(trick_fixtures)/sizeof(*trick_fixtures);i>0;i--)
  if(same(key,trick_fixtures[i-1].name)){selected.ordinal=(uint32_t)(i-1);*out=&selected;return;}
}
/* The original logger calls are observed without logging or claiming original
 * formatting/runtime ABI. Original getDirectoryName executes unchanged below. */
static void ErrorFilenamef(const char*path,const char*format,...){assert(path&&*path&&format);observed.diagnostic=1;}
static void Errorf(const char*format,...){assert(format);observed.diagnostic=2;}
'''
 suffix=r'''
void original_trick_model_select(const char*name,const char*path,int reporting,TrickModelOracleResult*out){
 memset(&observed,0,sizeof(observed));observed.ordinal=UINT32_MAX;
 trick_report_exist_errors=reporting;
 TrickInfo*result=trickFromObjectName(name,path);
 if(result)observed.ordinal=result->ordinal;
 *out=observed;
}
'''
 return prefix+'\n'+directory+'\n'+function+'\n'+suffix,{'trickFromObjectName':function,'getDirectoryName':directory}
