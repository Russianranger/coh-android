#!/usr/bin/env python3
"""Untextured host image of genuine selected Huge meshes and source skinning.

No game texture is synthesized. This test shader displays normals on original
selected geometry. It does not publish a live actor or claim authored costume
materials/morphology. Input source conversion is prepare_received_costume.
"""
import ctypes as C
import hashlib
from pathlib import Path
import resource


def capture(packets, output, source_peak_bytes=0, texture_layers=None):
    texture_layers = texture_layers or {}
    if not packets:
        return {'captured': False, 'reason': 'No actual selected source meshes available'}
    import importlib.util
    path = Path(__file__).parent / 'tests/render_gpu.py'
    spec = importlib.util.spec_from_file_location('received_capture_gpu', path)
    bridge = importlib.util.module_from_spec(spec); spec.loader.exec_module(bridge)
    U, F = C.c_uint32, C.c_float
    width, height = 512, 640
    xyz = [[vertex.position[k] for _, vertices, _ in packets for vertex in vertices] for k in range(3)]
    minimum, maximum = list(map(min, xyz)), list(map(max, xyz))
    center = [(low + high) * .5 for low, high in zip(minimum, maximum)]
    extent = max(maximum[1] - minimum[1], (maximum[0] - minimum[0]) * 1.25)
    if not extent > 0: raise ValueError('Selected source bounds are degenerate')
    scale = 1.65 / extent
    matrix = bridge.renderer.identity()
    matrix[0], matrix[5], matrix[10] = scale * 1.25, scale, -.08
    matrix[12], matrix[13], matrix[14] = -center[0] * matrix[0], -center[1] * matrix[5], -center[2] * matrix[10]
    max_upload = max(C.sizeof(vertices) + C.sizeof(indices) for _, vertices, indices in packets)
    # Old+candidate buffer storage during glBufferData; target+depth+readback.
    gpu_payload = max_upload * 2 + width * height * (4 + 2 + 4) + sum(C.sizeof(value['pixels']) for value in texture_layers.values())
    if source_peak_bytes < 0 or source_peak_bytes + gpu_payload > 96 << 20: raise ValueError('Capture staging exceeds existing scene cap')
    contexts = []
    for context in range(2):
        egl = bridge.gpu.EGL(); gl = egl.g
        target, fbo, depth, vao, vertex_buffer, index_buffer = [U() for _ in range(6)]
        program = vertex_shader = fragment_shader = 0
        texture_handles = {}
        try:
            egl.gf('glGenRenderbuffers', None, [C.c_int, C.POINTER(U)])
            egl.gf('glBindRenderbuffer', None, [U, U])
            egl.gf('glRenderbufferStorage', None, [U, U, C.c_int, C.c_int])
            egl.gf('glFramebufferRenderbuffer', None, [U, U, U, U])
            egl.gf('glDeleteRenderbuffers', None, [C.c_int, C.POINTER(U)])
            egl.gf('glDrawElements', None, [U, C.c_int, U, C.c_void_p])
            egl.gf('glActiveTexture', None, [U])
            gl.glActiveTexture(0x84c0)
            target = egl.texture(width, height)
            gl.glGenFramebuffers(1, C.byref(fbo)); gl.glBindFramebuffer(0x8d40, fbo)
            gl.glFramebufferTexture2D(0x8d40, 0x8ce0, 0xde1, target, 0)
            gl.glGenRenderbuffers(1, C.byref(depth)); gl.glBindRenderbuffer(0x8d41, depth)
            gl.glRenderbufferStorage(0x8d41, 0x81a5, width, height)
            gl.glFramebufferRenderbuffer(0x8d40, 0x8d00, 0x8d41, depth)
            if gl.glCheckFramebufferStatus(0x8d40) != 0x8cd5: raise ValueError('Host capture framebuffer failed')
            vertex_shader = egl.shader(0x8b31, b'''#version 300 es
layout(location=0) in vec3 position;layout(location=1) in vec3 normal;
layout(location=2) in vec2 uv;uniform mat4 transform;out vec3 n;out vec2 source_uv;
void main(){gl_Position=transform*vec4(position,1.0);n=normal;source_uv=uv;}''')
            fragment_shader = egl.shader(0x8b30, b'''#version 300 es
precision highp float;in vec3 n;in vec2 source_uv;out vec4 color;uniform bool show_layer;uniform sampler2D original_layer;
void main(){float shade=.28+.72*abs(dot(normalize(n),normalize(vec3(.3,.6,.8))));vec3 base=show_layer?texture(original_layer,source_uv).rgb:vec3(.69,.77,.84);color=vec4(base*shade,1.0);}''')
            program = gl.glCreateProgram(); gl.glAttachShader(program, vertex_shader); gl.glAttachShader(program, fragment_shader); gl.glLinkProgram(program)
            ok = C.c_int(); gl.glGetProgramiv(program, 0x8b82, C.byref(ok))
            if not ok.value: raise ValueError('Host diagnostic shader failed')
            gl.glUseProgram(program); gl.glUniformMatrix4fv(gl.glGetUniformLocation(program, b'transform'), 1, 0, matrix)
            gl.glGenVertexArrays(1, C.byref(vao)); gl.glBindVertexArray(vao)
            gl.glGenBuffers(1, C.byref(vertex_buffer)); gl.glGenBuffers(1, C.byref(index_buffer))
            for key, layer in texture_layers.items():
                texture = U(); metadata = layer['metadata']
                gl.glGenTextures(1, C.byref(texture)); gl.glBindTexture(0xde1, texture)
                gl.glTexImage2D(0xde1, 0, 0x8058, metadata['width'], metadata['height'], 0, 0x1908, 0x1401, layer['pixels'])
                for parameter, value in ((0x2801, 0x2601), (0x2800, 0x2601), (0x2802, 0x2901), (0x2803, 0x2901)):
                    gl.glTexParameteri(0xde1, parameter, value)
                texture_handles[key] = texture
            gl.glUniform1i(gl.glGetUniformLocation(program, b'original_layer'), 0)
            for mode in ('untextured', 'known-layer') if texture_layers else ('untextured',):
                gl.glViewport(0, 0, width, height); gl.glDepthMask(1); gl.glEnable(0x0b71); gl.glDisable(0x0b44)
                gl.glClearColor(.035, .045, .065, 1); gl.glClear(0x4000 | 0x100)
                for packet, vertices, indices in packets:
                    texture = texture_handles.get(packet.geometry.identity) if mode == 'known-layer' else None
                    gl.glUniform1i(gl.glGetUniformLocation(program, b'show_layer'), int(texture is not None))
                    gl.glBindTexture(0xde1, texture or 0)
                    gl.glBindBuffer(0x8892, vertex_buffer); gl.glBufferData(0x8892, C.sizeof(vertices), vertices, 0x88e0)
                    gl.glBindBuffer(0x8893, index_buffer); gl.glBufferData(0x8893, C.sizeof(indices), indices, 0x88e0)
                    for location, count, offset in ((0, 3, 0), (1, 3, 12), (2, 2, 24)):
                        gl.glVertexAttribPointer(location, count, 0x1406, 0, C.sizeof(bridge.renderer.Vertex), C.c_void_p(offset)); gl.glEnableVertexAttribArray(location)
                    gl.glDrawElements(4, len(indices), 0x1405, None)
                pixels = C.create_string_buffer(width * height * 4)
                gl.glReadPixels(0, 0, width, height, 0x1908, 0x1401, pixels)
                if gl.glGetError(): raise ValueError('Host capture GL error')
                raw = memoryview(pixels).cast('B'); background = bytes(raw[:4])
                visible = sum(bytes(raw[i:i + 4]) != background for i in range(0, len(raw), 4))
                if visible < 100: raise ValueError('No meaningful selected mesh pixels')
                from PIL import Image
                image = Image.frombuffer('RGBA', (width, height), pixels, 'raw', 'RGBA', 0, 1).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                image.save(output / ('huge-' + mode + '-context' + str(context + 1) + '.png'))
                contexts.append({'context': context + 1, 'mode': mode, 'visible_pixels': visible, 'rgba_sha256': hashlib.sha256(raw).hexdigest(), 'driver': egl.identity})
                del image, raw, pixels

        finally:
            for texture in texture_handles.values(): gl.glDeleteTextures(1, C.byref(texture))
            if program: gl.glDeleteProgram(program)
            if vertex_shader: gl.glDeleteShader(vertex_shader)
            if fragment_shader: gl.glDeleteShader(fragment_shader)
            gl.glDeleteBuffers(1, C.byref(vertex_buffer)); gl.glDeleteBuffers(1, C.byref(index_buffer)); gl.glDeleteVertexArrays(1, C.byref(vao))
            gl.glDeleteFramebuffers(1, C.byref(fbo)); gl.glDeleteRenderbuffers(1, C.byref(depth)); gl.glDeleteTextures(1, C.byref(target))
            egl.close()
    for mode in ('untextured', 'known-layer') if texture_layers else ('untextured',):
        hashes = [value['rgba_sha256'] for value in contexts if value['mode'] == mode]
        if len(hashes) != 2 or hashes[0] != hashes[1]: raise ValueError('Source capture changed across context recreation')
    return {'captured': True, 'host_only': True, 'shader': 'normal-lit diagnostic with optional explicit original source-UV layer inspection; incomplete game material is not synthesized', 'original_texture_layers': [{**value['metadata'], 'slot': value['slot']} for value in texture_layers.values()], 'contexts': contexts, 'gpu_target_buffer_readback_bytes': gpu_payload, 'host_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, 'bounds': {'minimum': minimum, 'maximum': maximum}, 'authored_scales_applied': False}
