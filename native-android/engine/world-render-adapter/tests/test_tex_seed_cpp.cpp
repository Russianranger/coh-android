#include "../coh_wr_tex_seed.h"
int main(){CohWrTexSeed out{};CohWrTexSeedLimits limits{};return coh_wr_tex_seed(nullptr,nullptr,&limits,CohCancel{},&out)==COH_INVALID?0:1;}
