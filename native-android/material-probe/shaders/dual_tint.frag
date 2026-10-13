#version 300 es
/* Scoped derivative of colorblenddualfp.cg, functions.cgh:calc_dual_tint
 * and calc_fogged_color. No BIT_HIGH_QUALITY/BIT_SHADOWMAP/BIT_DEBUG.
 * Alpha test is the explicit GLES equivalent of the original GL_GREATER test.
 * Fixed-function blending belongs to renderer state, not this shader. */
precision highp float;
uniform sampler2D uBase;
uniform sampler2D uDual;
uniform vec4 uConst0;
uniform vec4 uConst1;
uniform vec4 uFogParams;
uniform vec4 uFogColor;
uniform float uAlphaRef;
in vec4 vLitColor;
in float vFogCoord;
in vec2 vUV0;
in vec2 vUV1;
layout(location = 0) out vec4 outColor;
void main() {
    vec4 base = texture(uBase, vUV0);
    vec4 dual = texture(uDual, vUV1);
    vec3 tint = mix(uConst1.rgb, uConst0.rgb, dual.rgb);
    tint = mix(tint, vec3(1.0), base.a);
    vec3 rgb = tint * base.rgb;
    float alpha = dual.a * uConst0.a;
    rgb *= 4.0 * vLitColor.rgb;
    float fogAmount = clamp(uFogParams.w * (uFogParams.z - vFogCoord), 0.0, 1.0);
    rgb = mix(uFogColor.rgb, rgb, fogAmount);
    /* No texture-base-alpha multiplication: base.a is a tint mask. */
    if (!(alpha > uAlphaRef)) discard;
    outColor = vec4(rgb, alpha);
}
