#ifndef TEXWORDS_FIXTURE_H
#define TEXWORDS_FIXTURE_H
#include "../coh_wr_texwords.h"
typedef struct {uint32_t records,nodes,fields;} TexWordsOracleStats;
typedef struct {CohBytes source_name;uint32_t offset,bytes;} TexWordOracleRecord;
void original_texwords_initialize(CohBytes);
void original_texwords_configure(const char*,uint32_t,uint32_t,uint32_t,uint32_t);
uint32_t original_texwords_find(const CohWrTexNamespace*,const char*,int,uint32_t*);
void original_texwords_record(uint32_t,TexWordOracleRecord*);
void original_texwords_configuration(char[32],char[32],char[80]);
TexWordsOracleStats original_texwords_stats(void);
size_t original_texwords_workspace(void);
void original_texwords_destroy(void);
#endif
