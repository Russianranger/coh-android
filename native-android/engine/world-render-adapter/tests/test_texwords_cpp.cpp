#include "../coh_wr_texwords.h"
int main(){CohWrTexWords*owner=nullptr;CohWrTexWordsReport report{};CohWrTexWordSelection selection{};return coh_wr_texwords_destroy(&owner)!=COH_OK||coh_wr_texwords_report(nullptr,&report)!=COH_INVALID||coh_wr_texwords_find(nullptr,nullptr,"name",0,nullptr,&selection)!=COH_INVALID||coh_wr_texwords_create(nullptr,nullptr,nullptr,CohCancel{},&owner)!=COH_INVALID;}
