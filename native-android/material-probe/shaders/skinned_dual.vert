#version 300 es
/* Scoped derivative of CoH vp_master_vp.cg with SKIN=1, LIGHT_SPACE=VIEW,
 * VERTEX_LIT=DIFFUSE, TC_XFORM=NONE, PIXEL_LIT=NONE, REFLECT=NONE.
 * Exact original source hashes and exclusions are in contract/shader-contract.json.
 * Local row indices already encode palette slot * 3. The validated host must
 * reject negative/non-multiple-of-three/out-of-palette indices before drawing.
 */
precision highp float;
precision highp int;
layout(location = 0) in vec3 aPosition;
layout(location = 1) in vec3 aNormal;
layout(location = 2) in vec2 aUV0;
layout(location = 3) in vec2 aUV1;
layout(location = 4) in vec2 aWeights;
layout(location = 5) in ivec2 aRowIndices;
uniform vec4 uBoneRows[48];
uniform mat4 uProjection;
uniform vec3 uLightDir;
uniform vec4 uDiffuse;
uniform vec4 uAmbient;
out vec3 vViewPosition;
out vec3 vNormal;
/* Probe-only diagnostic; excluded from the six-component parity gate. */
out vec3 vUnrefinedNormal;
out vec4 vClipPosition;
out vec4 vLitColor;
out float vFogCoord;
out vec2 vUV0;
out vec2 vUV1;

vec3 affine_position(int row, vec4 p) {
    return vec3(dot(uBoneRows[row], p), dot(uBoneRows[row + 1], p),
                dot(uBoneRows[row + 2], p));
}
vec3 affine_normal(int row, vec3 n) {
    return vec3(dot(uBoneRows[row].xyz, n),
                dot(uBoneRows[row + 1].xyz, n),
                dot(uBoneRows[row + 2].xyz, n));
}
void main() {
    vec3 p0 = affine_position(aRowIndices.x, vec4(aPosition, 1.0));
    vec3 p1 = affine_position(aRowIndices.y, vec4(aPosition, 1.0));
    vec3 n0 = affine_normal(aRowIndices.x, aNormal);
    vec3 n1 = affine_normal(aRowIndices.y, aNormal);
    vViewPosition = mix(p0, p1, aWeights.y);
    /* The original GPU helper normalizes after blending. The old CPU
     * DeformObject path does not normalize and is a different contract. */
    vec3 blendedNormal = mix(n0, n1, aWeights.y);
    vUnrefinedNormal = normalize(blendedNormal);
    /* Explicitly refine reciprocal length once. This retains the original
     * normalize-after-blend mathematical contract while avoiding a driver's
     * coarse reciprocal-square-root approximation in the compared/shaded normal.
     * Zero/collapsed normals are rejected by the bounded fixture producer. */
    float lengthSquared = dot(blendedNormal, blendedNormal);
    float inverseLength = inversesqrt(lengthSquared);
    inverseLength *= 1.5 - 0.5 * lengthSquared * inverseLength * inverseLength;
    vNormal = blendedNormal * inverseLength;
    vClipPosition = uProjection * vec4(vViewPosition, 1.0);
    gl_Position = vClipPosition;
    vFogCoord = sqrt(dot(vViewPosition, vViewPosition) + 1e-16);
    vLitColor = clamp(dot(vNormal, uLightDir), 0.0, 1.0) * uDiffuse + uAmbient;
    vUV0 = aUV0;
    vUV1 = aUV1;
}
