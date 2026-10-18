#include "../coh_wr_tex_rgba32.h"
int main(){CohWrTexRgba32*owner=nullptr;CohWrTexRgba32View view{};return coh_wr_tex_rgba32_view(nullptr,&view)!=COH_INVALID||coh_wr_tex_rgba32_destroy(&owner)!=COH_INVALID||coh_wr_tex_rgba32_build(nullptr,0,0,nullptr,CohCancel{},&owner)!=COH_INVALID;}
