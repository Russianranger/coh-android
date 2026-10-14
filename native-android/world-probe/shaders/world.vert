#version 300 es
/* Original source point3/vec3 operation order. Shader variants enable precise
 * for ESSL 3.20 core or an advertised ESSL 3.10 gpu_shader5 extension. Plain
 * ESSL 3.00 retains explicit source order and still must pass actual GPU TF;
 * it cannot claim the precise qualifier's optimization guarantees.
 * Matrix multiplication hides its dot-product evaluation order and is omitted.
 */
#ifndef COH_SOURCE_PRECISE
#define COH_SOURCE_PRECISE
#endif
precision highp float;
layout(location=0) in vec3 aPosition;
layout(location=1) in vec3 aNormal;
layout(location=2) in vec2 aUV0;
layout(location=3) in vec2 aUV1;
uniform mat4 uModel,uModelView,uProjection;
uniform vec3 uLightDir;
uniform vec4 uDiffuse,uAmbient;
out vec3 vWorldPosition;
out vec3 vEyeNormal;
out vec3 vEyePosition;
out vec4 vClipPosition;
out vec4 vLitColor;
out float vFogCoord;
out vec2 vUV0,vUV1;
vec3 source_point(mat4 matrix,vec3 point){
    COH_SOURCE_PRECISE vec3 x=point.x*matrix[0].xyz;
    COH_SOURCE_PRECISE vec3 y=point.y*matrix[1].xyz;
    COH_SOURCE_PRECISE vec3 z=point.z*matrix[2].xyz;
    COH_SOURCE_PRECISE vec3 xy=x+y;
    COH_SOURCE_PRECISE vec3 xyz=xy+z;
    COH_SOURCE_PRECISE vec3 result=xyz+matrix[3].xyz;
    return result;
}
vec3 source_normal(mat4 matrix,vec3 normal){
    COH_SOURCE_PRECISE vec3 x=normal.x*matrix[0].xyz;
    COH_SOURCE_PRECISE vec3 y=normal.y*matrix[1].xyz;
    COH_SOURCE_PRECISE vec3 z=normal.z*matrix[2].xyz;
    COH_SOURCE_PRECISE vec3 xy=x+y;
    COH_SOURCE_PRECISE vec3 result=xy+z;
    return result;
}
vec4 source_clip(mat4 matrix,vec3 eye){
    COH_SOURCE_PRECISE vec4 x=eye.x*matrix[0];
    COH_SOURCE_PRECISE vec4 y=eye.y*matrix[1];
    COH_SOURCE_PRECISE vec4 z=eye.z*matrix[2];
    COH_SOURCE_PRECISE vec4 xy=x+y;
    COH_SOURCE_PRECISE vec4 xyz=xy+z;
    COH_SOURCE_PRECISE vec4 result=xyz+matrix[3];
    return result;
}
void main(){
    vWorldPosition=source_point(uModel,aPosition);
    vEyePosition=source_point(uModelView,aPosition);
    vEyeNormal=source_normal(uModelView,aNormal);
    vClipPosition=source_clip(uProjection,vEyePosition);
    gl_Position=vClipPosition;
    vFogCoord=sqrt(dot(vEyePosition,vEyePosition)+1e-16);
    vLitColor=clamp(dot(vEyeNormal,uLightDir),0.0,1.0)*uDiffuse+uAmbient;
    vUV0=aUV0;vUV1=aUV1;
}
