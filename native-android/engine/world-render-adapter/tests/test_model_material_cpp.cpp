#include "../coh_wr_model_material.h"
int main(){
 CohWrModelMaterialPart part{};
 part.name="explicit_CPP_link_fixture";
 part.blend.shader=COH_WR_MODEL_MODULATE;
 part.layer_present_mask=1;
 CohWrModelMaterialInput input{};
 input.model_name="world_CPP_link_fixture";
 input.parts=&part;
 input.part_count=1;
 input.normals_present=1;
 CohWrModelMaterialProjection output{};
 if(coh_wr_model_material_project(&input,&output)!=COH_OK)return 1;
 if(output.parts[0].shader!=COH_WR_MODEL_MULTIPLY)return 2;
 if(output.unrepresented_shader_mask)return 3;
 return 0;
}
