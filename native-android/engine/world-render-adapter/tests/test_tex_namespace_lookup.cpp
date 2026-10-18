#include "../coh_wr_tex_namespace_lookup.h"
int main(){CohWrTexNamespaceLookup result{};CohWrTexNamespaceLookupLimits limits{};return coh_wr_tex_namespace_lookup(nullptr,nullptr,&limits,&result)==COH_INVALID?0:1;}
