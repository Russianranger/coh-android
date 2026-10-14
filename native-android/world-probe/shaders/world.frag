#version 300 es
/* Source slices multiplyregfp.cg and colorblenddualfp.cg plus functions.cgh fog.
 * Controlled no-specular vertex light profile; no original Atlas light-grid claim. */
precision highp float;
uniform sampler2D uBase,uDual;
uniform vec4 uConst0,uConst1,uFogParams,uFogColor;
uniform float uAlphaRef;
uniform int uMaterialMode;
in vec4 vLitColor;
in float vFogCoord;
in vec2 vUV0,vUV1;
layout(location=0) out vec4 outColor;
void main(){
    vec4 base=texture(uBase,vUV0),dual=texture(uDual,vUV1);vec4 result;
    if(uMaterialMode==0){result=base*dual;result.rgb*=8.0*vLitColor.rgb;result.a*=uConst0.a;}
    else{vec3 tint=mix(uConst1.rgb,uConst0.rgb,dual.rgb);tint=mix(tint,vec3(1.0),base.a);result=vec4(tint*base.rgb,dual.a*uConst0.a);result.rgb*=4.0*vLitColor.rgb;}
    float fogAmount=clamp(uFogParams.w*(uFogParams.z-vFogCoord),0.0,1.0);result.rgb=mix(uFogColor.rgb,result.rgb,fogAmount);
    if(!(result.a>uAlphaRef))discard;outColor=result;
}
