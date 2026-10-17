#include "coh_wr_trick_model.h"
int main(){
 CohWrTrickModelQuery query={"model","data/example.geo",1};
 CohWrTrickModelLimits limits={4096,0};CohWrTrickModelSelection result={};
 return coh_wr_trick_model_select(nullptr,&query,&limits,&result)==COH_INVALID&&
  coh_wr_trick_detached_model_select(nullptr,&query,&limits,&result)==COH_INVALID?0:1;
}
