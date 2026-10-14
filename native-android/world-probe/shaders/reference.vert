#version 300 es
/* Diagnostic comparison driver: independent source oracle clip/eye/normal outputs.
 * These bytes never drive the native world/camera preview. */
precision highp float;
layout(location=1) in vec3 aNormal;
layout(location=2) in vec2 aUV0;
layout(location=3) in vec2 aUV1;
layout(location=4) in vec4 aClip;
layout(location=5) in vec3 aEye;
uniform vec3 uLightDir;
uniform vec4 uDiffuse,uAmbient;
out vec4 vLitColor;
out float vFogCoord;
out vec2 vUV0,vUV1;
void main(){gl_Position=aClip;vFogCoord=sqrt(dot(aEye,aEye)+1e-16);vLitColor=clamp(dot(aNormal,uLightDir),0.0,1.0)*uDiffuse+uAmbient;vUV0=aUV0;vUV1=aUV1;}
