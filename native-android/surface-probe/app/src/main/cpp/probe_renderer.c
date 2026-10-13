/* Bounded diagnostic renderer. Every JNI call owns and destroys all of its
 * windows, EGL objects, GPU objects and byte buffers. No game/runtime state. */
#include <jni.h>
#include <android/native_window.h>
#include <android/native_window_jni.h>
#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES3/gl3.h>
#include <inttypes.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "coh_native_core.h"

#define PROBE_CYCLES 2
#define MAX_DDS_BYTES (32u * 1024u * 1024u)
#define MAX_RGBA_BYTES (32u * 1024u * 1024u)
#define JSON_CAPACITY 16384u
#define TEXT_CAPACITY 512u

typedef struct {
    int completed, passed, context_created, fbo_complete, readback_passed;
    int swap_passed, window_pixel_match, released, width, height, viewport_x, viewport_y;
    int viewport_width, viewport_height, max_texture_size;
    int red_bits, green_bits, blue_bits, alpha_bits, egl_major, egl_minor;
    unsigned gl_errors, first_gl_error, egl_error;
    uint64_t compared_pixels, mismatched_pixels;
    uint32_t first_mismatch_x, first_mismatch_y;
    uint8_t expected[4], actual[4];
    unsigned window_samples, window_mismatches;
    int window_first_x, window_first_y;
    uint8_t window_expected[4], window_actual[4];
    char stage[TEXT_CAPACITY], failure[TEXT_CAPACITY];
    char gl_vendor[TEXT_CAPACITY], gl_renderer[TEXT_CAPACITY];
    char gl_version[TEXT_CAPACITY], glsl_version[TEXT_CAPACITY];
    char egl_vendor[TEXT_CAPACITY], egl_version[TEXT_CAPACITY];
} Cycle;

typedef struct {
    int passed, decoder_status, attempted_cycles, cpu_golden_match;
    uint32_t width, height, format, mip_count;
    size_t input_bytes, rgba_bytes;
    char failure[TEXT_CAPACITY];
    Cycle cycles[PROBE_CYCLES];
} Report;

typedef struct { char *bytes; size_t length, capacity; int ok; } Json;

static void copy_text(char *dst, const char *src) {
    (void)snprintf(dst, TEXT_CAPACITY, "%s", src ? src : "");
}

static void append(Json *j, const char *format, ...) __attribute__((format(printf, 2, 3)));
static void append(Json *j, const char *format, ...) {
    if (!j->ok) return;
    va_list args;
    va_start(args, format);
    int n = vsnprintf(j->bytes + j->length, j->capacity - j->length, format, args);
    va_end(args);
    if (n < 0 || (size_t)n >= j->capacity - j->length) { j->ok = 0; return; }
    j->length += (size_t)n;
}

static void json_string(Json *j, const char *s) {
    append(j, "\"");
    for (const unsigned char *p = (const unsigned char *)s; *p && j->ok; ++p) {
        if (*p == '"' || *p == '\\') append(j, "\\%c", *p);
        else if (*p < 32 || *p >= 127) append(j, "\\u%04x", *p);
        else append(j, "%c", *p);
    }
    append(j, "\"");
}

static const char *boolean(int v) { return v ? "true" : "false"; }

static jstring json_report(JNIEnv *env, const Report *r) {
    char *buffer = (char *)malloc(JSON_CAPACITY);
    if (!buffer) return (*env)->NewStringUTF(env,
        "{\"schema\":1,\"passed\":false,\"failure\":\"report allocation failed\"}");
    Json j = {buffer, 0, JSON_CAPACITY, 1};
    append(&j, "{\"schema\":1,\"probe\":\"coh-surface-egl-gles3\","
               "\"passed\":%s,\"platform\":\"Android Bionic\","
               "\"pointer_bytes\":%zu,\"long_bytes\":%zu,"
               "\"dds_bytes\":%zu,\"rgba_bytes\":%zu,"
               "\"width\":%u,\"height\":%u,\"dxt_format\":%u,"
               "\"declared_mips\":%u,\"mip_level\":0,"
               "\"decoder\":\"coh_dds_rgba_legacy\",\"decoder_status\":%d,"
               "\"required_cycles\":%d,\"attempted_cycles\":%d,"
               "\"pixel_contract\":\"RGBA8 nearest; CPU row 0 equals FBO readback row 0\","
               "\"window_contract\":\"aspect fit; opaque RGB aspect fit; CPU row 0 displayed at top\","
               "\"cpu_golden_match\":%s,\"context_recreation_passed\":%s,"
               "\"fbo_pixel_match\":%s,\"window_pixel_match\":%s,"
               "\"surface_width\":%d,\"surface_height\":%d,\"failure\":",
               boolean(r->passed), sizeof(void *), sizeof(long),
               r->input_bytes, r->rgba_bytes, r->width, r->height, r->format,
               r->mip_count, r->decoder_status, PROBE_CYCLES, r->attempted_cycles,
               boolean(r->cpu_golden_match),
               boolean(r->attempted_cycles == PROBE_CYCLES && r->cycles[0].passed && r->cycles[1].passed),
               boolean(r->attempted_cycles == PROBE_CYCLES && r->cycles[0].readback_passed && r->cycles[1].readback_passed),
               boolean(r->attempted_cycles == PROBE_CYCLES && r->cycles[0].window_pixel_match && r->cycles[1].window_pixel_match),
               r->attempted_cycles ? r->cycles[r->attempted_cycles - 1].width : 0,
               r->attempted_cycles ? r->cycles[r->attempted_cycles - 1].height : 0);
    json_string(&j, r->failure);
    append(&j, ",\"cycles\":[");
    for (int i = 0; i < r->attempted_cycles; ++i) {
        const Cycle *c = &r->cycles[i];
        if (i) append(&j, ",");
        append(&j, "{\"index\":%d,\"completed\":%s,\"passed\":%s,"
                   "\"context_created\":%s,\"objects_released\":%s,"
                   "\"fbo_complete\":%s,\"readback_passed\":%s,"
                   "\"swap_passed\":%s,\"window_pixel_match\":%s,"
                   "\"surface_width\":%d,\"surface_height\":%d,"
                   "\"viewport\":[%d,%d,%d,%d],\"max_texture_size\":%d,"
                   "\"config_rgba_bits\":[%d,%d,%d,%d],\"egl_api_version\":[%d,%d],"
                   "\"compared_pixels\":%" PRIu64 ",\"mismatched_pixels\":%" PRIu64 ","
                   "\"first_mismatch\":{\"x\":%u,\"y\":%u,"
                   "\"expected_rgba\":[%u,%u,%u,%u],\"actual_rgba\":[%u,%u,%u,%u]},"
                   "\"window_samples\":%u,\"window_mismatches\":%u,"
                   "\"window_first_mismatch\":{\"x\":%d,\"y\":%d,"
                   "\"expected_rgba\":[%u,%u,%u,%u],\"actual_rgba\":[%u,%u,%u,%u]},"
                   "\"window_alpha_compared\":false,"
                   "\"gl_errors\":%u,\"first_gl_error\":%u,\"egl_error\":%u,"
                   "\"stage\":", i, boolean(c->completed), boolean(c->passed),
                   boolean(c->context_created), boolean(c->released),
                   boolean(c->fbo_complete), boolean(c->readback_passed),
                   boolean(c->swap_passed), boolean(c->window_pixel_match), c->width, c->height,
                   c->viewport_x, c->viewport_y, c->viewport_width, c->viewport_height,
                   c->max_texture_size, c->red_bits, c->green_bits, c->blue_bits,
                   c->alpha_bits, c->egl_major, c->egl_minor, c->compared_pixels,
                   c->mismatched_pixels, c->first_mismatch_x, c->first_mismatch_y,
                   c->expected[0], c->expected[1], c->expected[2], c->expected[3],
                   c->actual[0], c->actual[1], c->actual[2], c->actual[3],
                   c->window_samples, c->window_mismatches, c->window_first_x, c->window_first_y,
                   c->window_expected[0], c->window_expected[1], c->window_expected[2], c->window_expected[3],
                   c->window_actual[0], c->window_actual[1], c->window_actual[2], c->window_actual[3],
                   c->gl_errors, c->first_gl_error, c->egl_error);
        json_string(&j, c->stage);
        append(&j, ",\"failure\":"); json_string(&j, c->failure);
        append(&j, ",\"gl_vendor\":"); json_string(&j, c->gl_vendor);
        append(&j, ",\"gl_renderer\":"); json_string(&j, c->gl_renderer);
        append(&j, ",\"gl_version\":"); json_string(&j, c->gl_version);
        append(&j, ",\"glsl_version\":"); json_string(&j, c->glsl_version);
        append(&j, ",\"egl_vendor\":"); json_string(&j, c->egl_vendor);
        append(&j, ",\"egl_version\":"); json_string(&j, c->egl_version);
        append(&j, "}");
    }
    append(&j, "]}");
    jstring result = (*env)->NewStringUTF(env, j.ok ? buffer :
        "{\"schema\":1,\"passed\":false,\"failure\":\"report size exceeded\"}");
    free(buffer);
    return result;
}

static int fail(Cycle *c, const char *stage, const char *message) {
    copy_text(c->stage, stage); copy_text(c->failure, message); return 0;
}

static int egl_failed(Cycle *c, const char *stage) {
    c->egl_error = (unsigned)eglGetError();
    return fail(c, stage, "EGL call failed; surface may have been destroyed");
}

static int check_gl(Cycle *c, const char *stage) {
    GLenum error;
    int ok = 1;
    /* Bound draining even after a lost context. */
    for (unsigned i = 0; i < 32 && (error = glGetError()) != GL_NO_ERROR; ++i) {
        ++c->gl_errors;
        if (!c->first_gl_error) c->first_gl_error = (unsigned)error;
        ok = 0;
    }
    return ok ? 1 : fail(c, stage, "GL error");
}

static GLuint compile_shader(Cycle *c, GLenum type, const char *source) {
    GLuint shader = glCreateShader(type);
    if (!shader) { fail(c, "shader-create", "glCreateShader returned zero"); return 0; }
    glShaderSource(shader, 1, &source, NULL);
    glCompileShader(shader);
    GLint ok = GL_FALSE;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[TEXT_CAPACITY] = {0};
        glGetShaderInfoLog(shader, sizeof(log), NULL, log);
        fail(c, "shader-compile", log[0] ? log : "shader compilation failed");
        glDeleteShader(shader); return 0;
    }
    return shader;
}

static int probe_cycle(ANativeWindow *window, const CohDdsMip *mip,
                       const uint8_t *rgba, uint8_t *readback, Cycle *c) {
    EGLDisplay display = EGL_NO_DISPLAY;
    EGLSurface surface = EGL_NO_SURFACE;
    EGLContext context = EGL_NO_CONTEXT;
    GLuint input = 0, output = 0, fbo = 0, vbo = 0, vao = 0;
    GLuint program = 0, vertex = 0, fragment = 0;
    int initialized = 0, current = 0, success = 0;
    EGLint major = 0, minor = 0, count = 0, visual = 0;
    EGLConfig config = NULL;
    const EGLint config_attributes[] = {
        EGL_SURFACE_TYPE, EGL_WINDOW_BIT,
        EGL_RENDERABLE_TYPE, EGL_OPENGL_ES3_BIT_KHR,
        EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8, EGL_ALPHA_SIZE, 8,
        EGL_DEPTH_SIZE, 0, EGL_STENCIL_SIZE, 0, EGL_NONE
    };
    const EGLint context_attributes[] = { EGL_CONTEXT_CLIENT_VERSION, 3, EGL_NONE };
    const char *vertex_source =
        "#version 300 es\n"
        "layout(location=0) in vec2 aPosition;\n"
        "layout(location=1) in vec2 aUV;\n"
        "uniform bool uFlip; out highp vec2 vUV;\n"
        "void main(){ gl_Position=vec4(aPosition,0.0,1.0);"
        "vUV=vec2(aUV.x,uFlip?1.0-aUV.y:aUV.y); }\n";
    const char *fragment_source =
        "#version 300 es\nprecision highp float;\n"
        "precision highp int;\n"
        "uniform highp sampler2D uTexture; in highp vec2 vUV;\n"
        "uniform bool uWindow; uniform ivec4 uViewport; uniform ivec2 uSize;\n"
        "layout(location=0) out vec4 color;\n"
        "void main(){ if(uWindow){ ivec2 p=ivec2(gl_FragCoord.xy)-uViewport.xy;"
        "ivec2 t=((2*p+ivec2(1))*uSize)/(2*uViewport.zw);"
        "t=clamp(t,ivec2(0),uSize-ivec2(1)); t.y=uSize.y-1-t.y;"
        "color=vec4(texelFetch(uTexture,t,0).rgb,1.0); } else { color=texture(uTexture,vUV); } }\n";
    const GLfloat vertices[] = {
        -1,-1,0,0, 1,-1,1,0, 1,1,1,1,
        -1,-1,0,0, 1,1,1,1, -1,1,0,1
    };

    display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (display == EGL_NO_DISPLAY) { egl_failed(c, "egl-display"); goto cleanup; }
    if (!eglInitialize(display, &major, &minor)) { egl_failed(c, "egl-initialize"); goto cleanup; }
    initialized = 1; c->egl_major = major; c->egl_minor = minor;
    copy_text(c->egl_vendor, eglQueryString(display, EGL_VENDOR));
    copy_text(c->egl_version, eglQueryString(display, EGL_VERSION));
    if (!eglBindAPI(EGL_OPENGL_ES_API)) { egl_failed(c, "egl-bind-api"); goto cleanup; }
    if (!eglChooseConfig(display, config_attributes, &config, 1, &count)) {
        egl_failed(c, "egl-config"); goto cleanup;
    }
    if (!count) { fail(c, "egl-config", "No RGBA8 GLES3 window config"); goto cleanup; }
    if (!eglGetConfigAttrib(display, config, EGL_NATIVE_VISUAL_ID, &visual)) {
        egl_failed(c, "egl-native-format"); goto cleanup;
    }
    if (ANativeWindow_setBuffersGeometry(window, 0, 0, visual) != 0) {
        fail(c, "native-window-format", "ANativeWindow_setBuffersGeometry failed"); goto cleanup;
    }
    EGLint bits = 0;
    if (!eglGetConfigAttrib(display, config, EGL_RED_SIZE, &bits)) { egl_failed(c, "egl-red-size"); goto cleanup; }
    c->red_bits = bits;
    if (!eglGetConfigAttrib(display, config, EGL_GREEN_SIZE, &bits)) { egl_failed(c, "egl-green-size"); goto cleanup; }
    c->green_bits = bits;
    if (!eglGetConfigAttrib(display, config, EGL_BLUE_SIZE, &bits)) { egl_failed(c, "egl-blue-size"); goto cleanup; }
    c->blue_bits = bits;
    if (!eglGetConfigAttrib(display, config, EGL_ALPHA_SIZE, &bits)) { egl_failed(c, "egl-alpha-size"); goto cleanup; }
    c->alpha_bits = bits;
    surface = eglCreateWindowSurface(display, config, window, NULL);
    if (surface == EGL_NO_SURFACE) { egl_failed(c, "egl-window-surface"); goto cleanup; }
    context = eglCreateContext(display, config, EGL_NO_CONTEXT, context_attributes);
    if (context == EGL_NO_CONTEXT) { egl_failed(c, "egl-context"); goto cleanup; }
    c->context_created = 1;
    if (!eglMakeCurrent(display, surface, surface, context)) { egl_failed(c, "egl-make-current"); goto cleanup; }
    current = 1;
    copy_text(c->gl_vendor, (const char *)glGetString(GL_VENDOR));
    copy_text(c->gl_renderer, (const char *)glGetString(GL_RENDERER));
    copy_text(c->gl_version, (const char *)glGetString(GL_VERSION));
    copy_text(c->glsl_version, (const char *)glGetString(GL_SHADING_LANGUAGE_VERSION));
    glGetIntegerv(GL_MAX_TEXTURE_SIZE, &c->max_texture_size);
    if (!check_gl(c, "gl-capabilities")) goto cleanup;
    if (c->max_texture_size <= 0 || mip->width > (uint32_t)c->max_texture_size ||
        mip->height > (uint32_t)c->max_texture_size) {
        fail(c, "texture-limit", "DDS exceeds this GL context's maximum texture size"); goto cleanup;
    }
    glDisable(GL_DITHER); glDisable(GL_BLEND); glDisable(GL_DEPTH_TEST);
    glDisable(GL_STENCIL_TEST); glDisable(GL_SCISSOR_TEST); glDisable(GL_CULL_FACE);
    glDisable(GL_SAMPLE_ALPHA_TO_COVERAGE); glDisable(GL_SAMPLE_COVERAGE);
    glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1); glPixelStorei(GL_PACK_ALIGNMENT, 1);
    vertex = compile_shader(c, GL_VERTEX_SHADER, vertex_source);
    if (!vertex) goto cleanup;
    fragment = compile_shader(c, GL_FRAGMENT_SHADER, fragment_source);
    if (!fragment) goto cleanup;
    program = glCreateProgram();
    if (!program) { fail(c, "program-create", "glCreateProgram returned zero"); goto cleanup; }
    glAttachShader(program, vertex); glAttachShader(program, fragment); glLinkProgram(program);
    GLint linked = GL_FALSE;
    glGetProgramiv(program, GL_LINK_STATUS, &linked);
    if (!linked) {
        char log[TEXT_CAPACITY] = {0};
        glGetProgramInfoLog(program, sizeof(log), NULL, log);
        fail(c, "program-link", log[0] ? log : "program linking failed"); goto cleanup;
    }
    GLint texture_uniform = glGetUniformLocation(program, "uTexture");
    GLint flip_uniform = glGetUniformLocation(program, "uFlip");
    GLint window_uniform = glGetUniformLocation(program, "uWindow");
    GLint viewport_uniform = glGetUniformLocation(program, "uViewport");
    GLint size_uniform = glGetUniformLocation(program, "uSize");
    if (texture_uniform < 0 || flip_uniform < 0 || window_uniform < 0 ||
        viewport_uniform < 0 || size_uniform < 0) {
        fail(c, "program-uniforms", "Expected shader uniform missing"); goto cleanup;
    }
    glUseProgram(program); glUniform1i(texture_uniform, 0); glUniform1i(flip_uniform, 0);
    glUniform1i(window_uniform, 0); glUniform2i(size_uniform, (GLint)mip->width, (GLint)mip->height);
    glUniform4i(viewport_uniform, 0, 0, (GLint)mip->width, (GLint)mip->height);
    glGenVertexArrays(1, &vao); glBindVertexArray(vao);
    glGenBuffers(1, &vbo); glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(GLfloat), (void *)0);
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(GLfloat), (void *)(2 * sizeof(GLfloat)));
    glEnableVertexAttribArray(0); glEnableVertexAttribArray(1);
    glActiveTexture(GL_TEXTURE0);
    glGenTextures(1, &input); glBindTexture(GL_TEXTURE_2D, input);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA8, (GLsizei)mip->width, (GLsizei)mip->height);
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, (GLsizei)mip->width, (GLsizei)mip->height,
                    GL_RGBA, GL_UNSIGNED_BYTE, rgba);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glGenTextures(1, &output); glBindTexture(GL_TEXTURE_2D, output);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA8, (GLsizei)mip->width, (GLsizei)mip->height);
    glGenFramebuffers(1, &fbo); glBindFramebuffer(GL_FRAMEBUFFER, fbo);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, output, 0);
    if (!check_gl(c, "gpu-upload")) goto cleanup;
    GLenum framebuffer_status = glCheckFramebufferStatus(GL_FRAMEBUFFER);
    if (framebuffer_status != GL_FRAMEBUFFER_COMPLETE) {
        char detail[TEXT_CAPACITY];
        (void)snprintf(detail, sizeof(detail), "Framebuffer incomplete: 0x%x", framebuffer_status);
        fail(c, "fbo-status", detail); goto cleanup;
    }
    c->fbo_complete = 1;
    glBindTexture(GL_TEXTURE_2D, input);
    glViewport(0, 0, (GLsizei)mip->width, (GLsizei)mip->height);
    glClearColor(0, 0, 0, 0); glClear(GL_COLOR_BUFFER_BIT);
    glDrawArrays(GL_TRIANGLES, 0, 6);
    glReadPixels(0, 0, (GLsizei)mip->width, (GLsizei)mip->height,
                 GL_RGBA, GL_UNSIGNED_BYTE, readback);
    if (!check_gl(c, "fbo-draw-readback")) goto cleanup;
    c->compared_pixels = (uint64_t)mip->width * mip->height;
    for (size_t offset = 0; offset < mip->rgba_bytes; offset += 4) {
        if (memcmp(rgba + offset, readback + offset, 4)) {
            if (!c->mismatched_pixels) {
                size_t pixel = offset / 4;
                c->first_mismatch_x = (uint32_t)(pixel % mip->width);
                c->first_mismatch_y = (uint32_t)(pixel / mip->width);
                memcpy(c->expected, rgba + offset, 4); memcpy(c->actual, readback + offset, 4);
            }
            ++c->mismatched_pixels;
        }
    }
    if (c->mismatched_pixels) { fail(c, "fbo-parity", "GPU readback differs from CPU RGBA"); goto cleanup; }
    c->readback_passed = 1;
    EGLint width = 0, height = 0;
    if (!eglQuerySurface(display, surface, EGL_WIDTH, &width) ||
        !eglQuerySurface(display, surface, EGL_HEIGHT, &height)) {
        egl_failed(c, "egl-query-surface"); goto cleanup;
    }
    if (width <= 0 || height <= 0) { fail(c, "window-size", "Non-positive EGL surface dimensions"); goto cleanup; }
    /* Bound the integer nearest-map shader's products, and reject implausible
     * platform surfaces instead of allowing signed integer overflow in GLSL. */
    if (width > 16384 || height > 16384) { fail(c, "window-size", "EGL surface exceeds 16384-pixel bound"); goto cleanup; }
    c->width = width; c->height = height;
    int fit_width = width, fit_height = height;
    if ((uint64_t)width * mip->height <= (uint64_t)height * mip->width)
        fit_height = (int)((uint64_t)width * mip->height / mip->width);
    else fit_width = (int)((uint64_t)height * mip->width / mip->height);
    if (fit_width < 1) fit_width = 1;
    if (fit_height < 1) fit_height = 1;
    c->viewport_width = fit_width; c->viewport_height = fit_height;
    c->viewport_x = (width - fit_width) / 2; c->viewport_y = (height - fit_height) / 2;
    glBindFramebuffer(GL_FRAMEBUFFER, 0);
    glViewport(0, 0, width, height);
    glClearColor(0.04f, 0.04f, 0.06f, 1.0f); glClear(GL_COLOR_BUFFER_BIT);
    glViewport(c->viewport_x, c->viewport_y, fit_width, fit_height);
    glUniform1i(window_uniform, 1);
    glUniform4i(viewport_uniform, c->viewport_x, c->viewport_y, fit_width, fit_height);
    glUniform1i(flip_uniform, 1); glDrawArrays(GL_TRIANGLES, 0, 6);
    if (!check_gl(c, "window-draw")) goto cleanup;
    /* The exact FBO check covers every RGBA pixel. Presentation additionally
     * checks 49 bounded interior samples on the actual default framebuffer.
     * RGB is required; Android's Surface alpha/compositor contract is separate.
     * Integer texelFetch gives deterministic nearest mapping at resize ties. */
    for (int gy = 1; gy <= 7; ++gy) for (int gx = 1; gx <= 7; ++gx) {
        int lx = (int)((int64_t)gx * fit_width / 8);
        int ly = (int)((int64_t)gy * fit_height / 8);
        if (lx >= fit_width) lx = fit_width - 1;
        if (ly >= fit_height) ly = fit_height - 1;
        uint32_t tx = (uint32_t)(((uint64_t)(2 * lx + 1) * mip->width) / (2u * (unsigned)fit_width));
        uint32_t ty = mip->height - 1u - (uint32_t)(((uint64_t)(2 * ly + 1) * mip->height) / (2u * (unsigned)fit_height));
        const uint8_t *expected = rgba + ((size_t)ty * mip->width + tx) * 4;
        uint8_t actual[4] = {0};
        glReadPixels(c->viewport_x + lx, c->viewport_y + ly, 1, 1, GL_RGBA, GL_UNSIGNED_BYTE, actual);
        if (!check_gl(c, "window-readback")) goto cleanup;
        ++c->window_samples;
        if (memcmp(expected, actual, 3)) {
            if (!c->window_mismatches) {
                c->window_first_x = c->viewport_x + lx; c->window_first_y = c->viewport_y + ly;
                memcpy(c->window_expected, expected, 4); memcpy(c->window_actual, actual, 4);
            }
            ++c->window_mismatches;
        }
    }
    if (c->window_mismatches) { fail(c, "window-parity", "Actual window RGB samples differ from CPU pixels"); goto cleanup; }
    c->window_pixel_match = 1;
    if (!eglSwapBuffers(display, surface)) { egl_failed(c, "egl-swap-buffers"); goto cleanup; }
    c->swap_passed = 1;
    if (!check_gl(c, "post-swap")) goto cleanup;
    c->completed = 1; copy_text(c->stage, "complete"); success = 1;

cleanup:
    if (current) {
        if (fbo) glDeleteFramebuffers(1, &fbo);
        if (input) glDeleteTextures(1, &input);
        if (output) glDeleteTextures(1, &output);
        if (vbo) glDeleteBuffers(1, &vbo);
        if (vao) glDeleteVertexArrays(1, &vao);
        if (program) glDeleteProgram(program);
        if (vertex) glDeleteShader(vertex);
        if (fragment) glDeleteShader(fragment);
        if (!check_gl(c, "gpu-cleanup")) success = 0;
    }
    int release_ok = 1;
    if (current && !eglMakeCurrent(display, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT)) {
        egl_failed(c, "egl-release-current"); release_ok = 0;
    }
    if (surface != EGL_NO_SURFACE && !eglDestroySurface(display, surface)) {
        egl_failed(c, "egl-destroy-surface"); release_ok = 0;
    }
    if (context != EGL_NO_CONTEXT && !eglDestroyContext(display, context)) {
        egl_failed(c, "egl-destroy-context"); release_ok = 0;
    }
    if (initialized && !eglTerminate(display)) { egl_failed(c, "egl-terminate"); release_ok = 0; }
    if (!eglReleaseThread()) { egl_failed(c, "egl-release-thread"); release_ok = 0; }
    c->released = release_ok;
    c->passed = success && release_ok;
    return c->passed;
}

JNIEXPORT jstring JNICALL
Java_org_coh_nativeprobe_ProbeNative_probe(JNIEnv *env, jclass clazz,
                                        jobject java_surface, jbyteArray java_dds,
                                        jbyteArray java_expected) {
    (void)clazz;
    Report report = {0};
    report.decoder_status = -1;
    ANativeWindow *window = NULL;
    uint8_t *dds = NULL, *rgba = NULL, *readback = NULL;
    if (!java_surface || !java_dds || !java_expected) {
        copy_text(report.failure, "Surface, DDS bytes and original decoded RGBA bytes are required"); goto cleanup;
    }
    jsize input_bytes = (*env)->GetArrayLength(env, java_dds);
    if (input_bytes < 128 || (size_t)input_bytes > MAX_DDS_BYTES) {
        copy_text(report.failure, "DDS input outside bounded 128-byte to 32-MiB range"); goto cleanup;
    }
    report.input_bytes = (size_t)input_bytes;
    dds = (uint8_t *)malloc(report.input_bytes);
    if (!dds) { copy_text(report.failure, "DDS allocation failed"); goto cleanup; }
    (*env)->GetByteArrayRegion(env, java_dds, 0, input_bytes, (jbyte *)dds);
    if ((*env)->ExceptionCheck(env)) {
        (*env)->ExceptionClear(env);
        copy_text(report.failure, "JNI DDS copy failed"); goto cleanup;
    }
    CohDdsMip mip = {0};
    report.decoder_status = coh_dds_mip(dds, report.input_bytes, 0, &mip);
    if (report.decoder_status) { copy_text(report.failure, "DDS header/mip validation failed"); goto cleanup; }
    report.width = mip.width; report.height = mip.height;
    report.format = mip.format; report.mip_count = mip.mip_count;
    report.rgba_bytes = mip.rgba_bytes;
    if (mip.rgba_bytes > MAX_RGBA_BYTES) {
        copy_text(report.failure, "Decoded RGBA exceeds 32-MiB probe allocation limit"); goto cleanup;
    }
    rgba = (uint8_t *)malloc(mip.rgba_bytes); readback = (uint8_t *)malloc(mip.rgba_bytes);
    if (!rgba || !readback) { copy_text(report.failure, "RGBA/readback allocation failed"); goto cleanup; }
    report.decoder_status = coh_dds_rgba_legacy(dds, report.input_bytes, 0, rgba, mip.rgba_bytes);
    if (report.decoder_status) { copy_text(report.failure, "Qualified legacy DDS decode failed"); goto cleanup; }
    jsize expected_bytes = (*env)->GetArrayLength(env, java_expected);
    if ((size_t)expected_bytes != mip.rgba_bytes) {
        copy_text(report.failure, "Original oracle RGBA length differs from decoded image"); goto cleanup;
    }
    /* Reuse the readback allocation; JNI never pins the Java heap across EGL. */
    (*env)->GetByteArrayRegion(env, java_expected, 0, expected_bytes, (jbyte *)readback);
    if ((*env)->ExceptionCheck(env)) {
        (*env)->ExceptionClear(env);
        copy_text(report.failure, "JNI original RGBA copy failed"); goto cleanup;
    }
    if (memcmp(rgba, readback, mip.rgba_bytes)) {
        copy_text(report.failure, "Android CPU decode differs from original Win32 oracle RGBA"); goto cleanup;
    }
    report.cpu_golden_match = 1;
    window = ANativeWindow_fromSurface(env, java_surface);
    if ((*env)->ExceptionCheck(env)) (*env)->ExceptionClear(env);
    if (!window) { copy_text(report.failure, "Android Surface is unavailable"); goto cleanup; }
    report.passed = 1;
    for (int i = 0; i < PROBE_CYCLES; ++i) {
        ++report.attempted_cycles;
        if (!probe_cycle(window, &mip, rgba, readback, &report.cycles[i])) {
            report.passed = 0;
            copy_text(report.failure, report.cycles[i].failure);
            break;
        }
    }
cleanup:
    if (window) ANativeWindow_release(window);
    free(readback); free(rgba); free(dds);
    return json_report(env, &report);
}
