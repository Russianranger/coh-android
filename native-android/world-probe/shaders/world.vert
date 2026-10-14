#version 300 es
/* Controlled source rigid draw path: source model/view/projection, source transformed
 * non-normalized normal. Camera matrices are rebuilt from original Pos/PYR inputs. */
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
void main(){
    vWorldPosition=(uModel*vec4(aPosition,1)).xyz;
    vEyePosition=(uModelView*vec4(aPosition,1)).xyz;
    vEyeNormal=mat3(uModelView)*aNormal;
    vClipPosition=uProjection*vec4(vEyePosition,1);
    gl_Position=vClipPosition;
    vFogCoord=sqrt(dot(vEyePosition,vEyePosition)+1e-16);
    vLitColor=clamp(dot(vEyeNormal,uLightDir),0.0,1.0)*uDiffuse+uAmbient;
    vUV0=aUV0;vUV1=aUV1;
}
