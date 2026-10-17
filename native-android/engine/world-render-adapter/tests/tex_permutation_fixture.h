#ifndef TEX_PERMUTATION_FIXTURE_H
#define TEX_PERMUTATION_FIXTURE_H
#include "../coh_wr_tex_permutation.h"
typedef struct{char lookup_keys[2][128],locales[16][128];unsigned lookup_count,locale_count,fully_executed,candidate_ordinal;int scene_index;}PermutationOracle;
void original_permutation(const char*const*,unsigned,const CohWrTexPermutationInput*,PermutationOracle*);
#endif
