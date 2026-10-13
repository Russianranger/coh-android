#version 300 es
/* Arithmetic fixture driver, not a replacement for CoH's game vertex shader.
 * Supplies controlled fragment inputs to the original dual-tint material slice. */
precision highp float;
layout(location = 0) in vec2 aPosition;
layout(location = 2) in vec2 aUV0;
uniform vec4 uReferenceColor;
uniform float uReferenceFogCoord;
out vec4 vLitColor;
out float vFogCoord;
out vec2 vUV0;
out vec2 vUV1;
void main() {
    gl_Position = vec4(aPosition, 0.0, 1.0);
    vLitColor = uReferenceColor;
    vFogCoord = uReferenceFogCoord;
    vUV0 = aUV0;
    vUV1 = aUV0;
}
