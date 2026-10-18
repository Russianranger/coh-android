#ifndef TEX_DEFAULTS_FIXTURE_H
#define TEX_DEFAULTS_FIXTURE_H
#include "../coh_wr_tex_defaults.h"
enum { DEFAULTS_ORACLE_ROWS=32 };
typedef struct {
 uint32_t required_present,selected_mask,lookup_count;
 uint32_t rows[7],flags[DEFAULTS_ORACLE_ROWS];
} DefaultsOracle;
void original_defaults(const char*const*,const uint32_t*,uint32_t,DefaultsOracle*);
#endif
