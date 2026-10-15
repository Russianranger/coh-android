#version 300 es
#define COH_PRECISE
/* vp_master_vp.cg: SKIN=0, LIGHT_SPACE=VIEW, TC_XFORM=NONE.
 * No inverse-transpose normal substitution: source uses upper-left model-view. */
precision highp float;
precision highp int;
layout(location=0) in vec3 aPosition;
layout(location=1) in vec3 aNormal;
layout(location=2) in vec2 aUV0;
layout(location=3) in vec2 aUV1;
layout(location=4) in vec4 aColor;
uniform mat4 uModelView, uProjection;
uniform int uLighting;
uniform vec3 uLight, uSpecular;
uniform vec4 uDiffuse, uAmbient;
uniform float uShininess;
out vec2 vUV0, vUV1;
out vec3 vViewPosition, vNormal;
out vec4 vLit;
out float vFog;
void main() {
    COH_PRECISE vec3 p;
    p.x=((aPosition.x*uModelView[0][0]+aPosition.y*uModelView[1][0])+aPosition.z*uModelView[2][0])+uModelView[3][0];
    p.y=((aPosition.x*uModelView[0][1]+aPosition.y*uModelView[1][1])+aPosition.z*uModelView[2][1])+uModelView[3][1];
    p.z=((aPosition.x*uModelView[0][2]+aPosition.y*uModelView[1][2])+aPosition.z*uModelView[2][2])+uModelView[3][2];
    vViewPosition=p;
    COH_PRECISE vec4 clip;
    clip.x=((p.x*uProjection[0][0]+p.y*uProjection[1][0])+p.z*uProjection[2][0])+uProjection[3][0];
    clip.y=((p.x*uProjection[0][1]+p.y*uProjection[1][1])+p.z*uProjection[2][1])+uProjection[3][1];
    clip.z=((p.x*uProjection[0][2]+p.y*uProjection[1][2])+p.z*uProjection[2][2])+uProjection[3][2];
    clip.w=((p.x*uProjection[0][3]+p.y*uProjection[1][3])+p.z*uProjection[2][3])+uProjection[3][3];
    gl_Position=clip;
    vFog = sqrt(dot(p,p)+1e-16);
    vec3 n = normalize(mat3(uModelView) * aNormal);
    vNormal=n;
    float ndl = dot(n,uLight);
    if (uLighting==0) vLit=aColor;
    else if (uLighting==1) vLit=clamp(ndl,0.0,1.0)*uDiffuse+uAmbient;
    else {
        vec3 halfVector=normalize(uLight+normalize(-p));
        vec3 diffuse=clamp(ndl*uDiffuse.rgb,0.0,1.0);
        float spec=pow(clamp(dot(n,halfVector),0.0,1.0),uShininess);
        vLit=vec4((diffuse+uAmbient.rgb)*aColor.rgb+spec*uSpecular,aColor.a);
    }
    vUV0=aUV0; vUV1=aUV1;
}
