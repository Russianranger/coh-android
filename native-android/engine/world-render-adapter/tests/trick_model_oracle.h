#ifndef COH_WR_TRICK_MODEL_ORACLE_H
#define COH_WR_TRICK_MODEL_ORACLE_H
#include <stdint.h>
typedef struct {uint32_t ordinal,diagnostic,lookups;char key[260];} TrickModelOracleResult;
void original_trick_model_select(const char*,const char*,int,TrickModelOracleResult*);
#endif
