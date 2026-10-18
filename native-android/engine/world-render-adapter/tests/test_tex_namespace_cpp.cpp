#include "../coh_wr_tex_namespace.h"
int main(){
 CohWrTexNamespace*owner=nullptr;
 if(coh_wr_tex_namespace_build(nullptr,nullptr,CohCancel{},&owner)!=COH_INVALID)return 1;
 if(coh_wr_tex_namespace_destroy(&owner)!=COH_OK||owner)return 2;
 return coh_wr_tex_namespace_find(nullptr,"white",nullptr)==COH_INVALID?0:3;
}
