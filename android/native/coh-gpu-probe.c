/* Isolated PE32 WGL prerequisite probe for the opt-in Zink route.
 * It does not load Game, Cg, assets, or Android presentation components.
 * Khronos ARB_vertex_program/ARB_fragment_program, EXT_framebuffer_object and
 * EXT_texture_compression_s3tc define the exercised calls and block formats.
 * No advertised GL version/extension override is used or accepted as proof.
 * The caller must bound process execution: a driver call itself can hang.
 */
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <stddef.h>

enum { STRING_LIMIT = 512, EXTENSION_LIMIT = 262144, SAMPLE_COUNT = 4,
       PRESENTATION_SIZE = 64, PRESENTATION_TIMEOUT_MS = 2000,
       PRESENTATION_MAX_ATTEMPTS = 100, PRESENTATION_WAIT_MS = 20 };
#ifdef COH_GPU_PROBE_TEST
#define BUILD_MARKER "COH_GPU_PROBE_BUILD:host_fixture"
#else
#define BUILD_MARKER "COH_GPU_PROBE_BUILD:production"
#endif

static const unsigned char pattern_rgba[4][4] = {
    {255, 0, 0, 255}, {0, 255, 0, 255},
    {0, 0, 255, 255}, {255, 255, 255, 255}
};
/* Deliberately different at every quadrant and channel. A stale first frame,
 * blank image, channel swap or vertical/horizontal reflection cannot match. */
static const unsigned char presentation_alternate_rgba[4][4] = {
    {41,93,173,255}, {211,57,99,255},
    {77,201,33,255}, {163,29,227,255}
};

/* GL samples are ordered bottom-left, bottom-right, top-left, top-right.
 * Win32 screen/client y increases downwards; convert the actual GL pixel,
 * including its one-pixel offset, rather than simply reversing quadrants. */
static int presentation_coordinates(int width, int height, unsigned int sample,
                                      int *x, int *y) {
    static const int quadrant[4][2] = {{1,1},{3,1},{1,3},{3,3}};
    if (!x || !y || width != PRESENTATION_SIZE || height != PRESENTATION_SIZE ||
        sample >= SAMPLE_COUNT) return 0;
    *x = width * quadrant[sample][0] / 4;
    *y = height - 1 - height * quadrant[sample][1] / 4;
    return *x >= 0 && *x < width && *y >= 0 && *y < height;
}

/* GDI screen readback proves RGB only. Alpha retains its independent GL/FBO
 * checks below and is never fabricated as screen-readback evidence. */
static int presentation_pixels_match(const unsigned char actual[SAMPLE_COUNT][3],
                                      const unsigned char expected[SAMPLE_COUNT][4]) {
    unsigned int i, j;
    for (i = 0; i < SAMPLE_COUNT; ++i) for (j = 0; j < 3; ++j) {
        int delta = (int)actual[i][j] - (int)expected[i][j];
        if (delta < -3 || delta > 3) return 0;
    }
    return 1;
}

/* Pure bounded polling guard is exercised by the actual-source host fixture.
 * The caller timestamps after reading: even a correct image returned beyond
 * the deadline must fail. Unsigned subtraction tolerates GetTickCount wrap. */
static int presentation_poll_step(unsigned int started, unsigned int now,
                                   unsigned int *attempts, unsigned int *elapsed,
                                   int owned_pixels,
                                   const unsigned char actual[SAMPLE_COUNT][3],
                                   const unsigned char expected[SAMPLE_COUNT][4]) {
    if (!attempts || !elapsed || *attempts >= PRESENTATION_MAX_ATTEMPTS) return -1;
    ++*attempts;
    *elapsed = now - started;
    if (*elapsed > PRESENTATION_TIMEOUT_MS) return -1;
    if (owned_pixels && presentation_pixels_match(actual,expected)) return 1;
    return *attempts >= PRESENTATION_MAX_ATTEMPTS || *elapsed >= PRESENTATION_TIMEOUT_MS ? -1 : 0;
}
/* Little-endian, all index zero: red opaque DXT1; green alpha136 DXT3;
 * blue alpha200 DXT5. Alternate blocks exercise the compressed subimage. */
static const unsigned char dxt_blocks[3][16] = {
    {0x00,0xf8,0,0,0,0,0,0},
    {0x88,0x88,0x88,0x88,0x88,0x88,0x88,0x88,0xe0,0x07,0,0,0,0,0,0},
    {200,0,0,0,0,0,0,0,0x1f,0,0,0,0,0,0,0}
};
static const unsigned char dxt_alternate_blocks[3][16] = {
    {0xff,0x07,0,0,0,0,0,0},
    {0x55,0x55,0x55,0x55,0x55,0x55,0x55,0x55,0x1f,0xf8,0,0,0,0,0,0},
    {120,0,0,0,0,0,0,0,0xe0,0xff,0,0,0,0,0,0}
};
static const unsigned char dxt_expected[3][4] = {
    {255,0,0,255}, {0,255,0,136}, {0,0,255,200}
};
static const unsigned char dxt_alternate_expected[3][4] = {
    {0,255,255,255}, {255,0,255,85}, {255,255,0,120}
};

static int pixels_match(const unsigned char actual[SAMPLE_COUNT][4],
                        const unsigned char expected[SAMPLE_COUNT][4]) {
    unsigned int i, j;
    for (i = 0; i < SAMPLE_COUNT; ++i) for (j = 0; j < 4; ++j) {
        int delta = (int)actual[i][j] - (int)expected[i][j];
        if (delta < -3 || delta > 3) return 0;
    }
    return 1;
}

static void solid_expected(unsigned char expected[SAMPLE_COUNT][4],
                           const unsigned char rgba[4]) {
    unsigned int i;
    for (i = 0; i < SAMPLE_COUNT; ++i) memcpy(expected[i], rgba, 4);
}

static void fill_bgra(unsigned char pixels[3 * 5 * 4], const unsigned char rgba[4]) {
    unsigned int i;
    for (i = 0; i < 3 * 5; ++i) {
        pixels[4*i] = rgba[2]; pixels[4*i+1] = rgba[1];
        pixels[4*i+2] = rgba[0]; pixels[4*i+3] = rgba[3];
    }
}

static void fill_compressed(unsigned char data[64], unsigned int kind,
                             unsigned int blocks) {
    unsigned int i, block_size = kind == 0 ? 8 : 16;
    memset(data, 0, 64);
    if (kind >= 3 || blocks > 4) return;
    for (i = 0; i < blocks; ++i)
        memcpy(data + i * block_size, dxt_blocks[kind], block_size);
}

static int contains_folded(const char *text, const char *needle) {
    size_t i, j;
    if (!text || !needle || !*needle) return 0;
    for (i = 0; text[i] && i < STRING_LIMIT; ++i) {
        for (j = 0; needle[j] && i+j < STRING_LIMIT && text[i+j] &&
             tolower((unsigned char)text[i+j]) == tolower((unsigned char)needle[j]); ++j) {}
        if (!needle[j]) return 1;
    }
    return 0;
}

static int nonsoftware_zink(const char *renderer) {
    return contains_folded(renderer, "zink") &&
        !contains_folded(renderer, "llvmpipe") && !contains_folded(renderer, "softpipe") &&
        !contains_folded(renderer, "swrast") && !contains_folded(renderer, "software") &&
        !contains_folded(renderer, "gdi generic") && !contains_folded(renderer, "swiftshader") &&
        !contains_folded(renderer, "lavapipe");
}

static int extension_present(const char *list, const char *name) {
    size_t i = 0, length;
    if (!list || !name || !*name || strchr(name, ' ')) return 0;
    length = strlen(name);
    if (length > STRING_LIMIT) return 0;
    /* Scan complete bounded tokens; never accept a suffix or truncated token. */
    while (i < EXTENSION_LIMIT && list[i]) {
        size_t start, size;
        while (i < EXTENSION_LIMIT && list[i] == ' ') ++i;
        start = i;
        while (i < EXTENSION_LIMIT && list[i] && list[i] != ' ') ++i;
        if (i == EXTENSION_LIMIT) return 0;
        size = i - start;
        if (size == length && !memcmp(list + start, name, length)) return 1;
    }
    return 0;
}

static void copy_string(char destination[STRING_LIMIT+1], const char *source) {
    size_t i;
    for (i = 0; source && source[i] && i < STRING_LIMIT; ++i) destination[i] = source[i];
    destination[i] = 0;
}

static void json_string(const char *text) {
    size_t i;
    putchar('"');
    for (i = 0; text && text[i] && i < STRING_LIMIT; ++i) {
        unsigned char c = (unsigned char)text[i];
        if (c == '"' || c == '\\') { putchar('\\'); putchar(c); }
        else if (c < 32 || c >= 127) printf("\\u%04x", (unsigned int)c);
        else putchar(c);
    }
    putchar('"');
}

/* The same independently recomputed conjunction is used for exit status and
 * JSON. Renderer identity alone can never authorize this compatibility gate. */
struct probe_result {
    int pointer_bits, zink_nonsoftware;
    int multitexture, texture_compression, arb_vertex_program, arb_fragment_program;
    int framebuffer_extension, vertex_buffer_object, s3tc, npot, bgra_extension;
    int fp_max_local_parameters, fp_max_temporaries, fp_max_native_temporaries;
    int api_loaded, arb_programs, multitexture_render, vbo_render, npot_depth24_fbo;
    int dxt1_render, dxt3_render, dxt5_render;
    int dxt1_mipmaps, dxt3_mipmaps, dxt5_mipmaps;
    int dxt1_subimage, dxt3_subimage, dxt5_subimage;
    int bgra_render, bgra_subimage, backbuffer_render, swapped, frontbuffer_readback;
    int presented_pattern_first, presented_pattern_second, presented_readback;
    unsigned int presentation_attempts_first, presentation_attempts_second;
    unsigned int presentation_elapsed_ms_first, presentation_elapsed_ms_second;
    int presentation_client_width, presentation_client_height;
    unsigned char presented_pixels_first[SAMPLE_COUNT][3], presented_pixels_second[SAMPLE_COUNT][3];
    int cleanup_ok;
    unsigned long gl_error, win32_error, frontbuffer_gl_error;
};

static int result_passes(const struct probe_result *r) {
    return r && r->pointer_bits == 32 && r->zink_nonsoftware &&
        r->multitexture && r->texture_compression && r->arb_vertex_program &&
        r->arb_fragment_program && r->framebuffer_extension && r->vertex_buffer_object &&
        r->s3tc && r->npot && r->bgra_extension && r->fp_max_local_parameters >= 32 &&
        r->fp_max_temporaries >= 17 && r->fp_max_native_temporaries >= 17 &&
        r->api_loaded && r->arb_programs &&
        r->multitexture_render && r->vbo_render && r->npot_depth24_fbo &&
        r->dxt1_render && r->dxt3_render && r->dxt5_render &&
        r->dxt1_mipmaps && r->dxt3_mipmaps && r->dxt5_mipmaps &&
        r->dxt1_subimage && r->dxt3_subimage && r->dxt5_subimage &&
        r->bgra_render && r->bgra_subimage && r->backbuffer_render && r->swapped &&
        r->presented_pattern_first && r->presented_pattern_second && r->presented_readback &&
        r->presentation_client_width == PRESENTATION_SIZE &&
        r->presentation_client_height == PRESENTATION_SIZE &&
        r->presentation_attempts_first >= 1 && r->presentation_attempts_first <= PRESENTATION_MAX_ATTEMPTS &&
        r->presentation_attempts_second >= 1 && r->presentation_attempts_second <= PRESENTATION_MAX_ATTEMPTS &&
        r->presentation_elapsed_ms_first <= PRESENTATION_TIMEOUT_MS &&
        r->presentation_elapsed_ms_second <= PRESENTATION_TIMEOUT_MS &&
        presentation_pixels_match(r->presented_pixels_first,pattern_rgba) &&
        presentation_pixels_match(r->presented_pixels_second,presentation_alternate_rgba) &&
        r->cleanup_ok && !r->gl_error;
}

static void print_presented_pixels(const unsigned char pixels[SAMPLE_COUNT][3]) {
    unsigned int i;
    putchar('[');
    for (i = 0; i < SAMPLE_COUNT; ++i)
        printf("%s[%u,%u,%u]",i ? "," : "",(unsigned int)pixels[i][0],
               (unsigned int)pixels[i][1],(unsigned int)pixels[i][2]);
    putchar(']');
}

static void print_result(const struct probe_result *r, const char *failure,
                          const char *vendor, const char *renderer, const char *version) {
    int passed = result_passes(r) && failure && !*failure;
    printf("COH_GPU_PROBE_V2 {\"format\":2,\"build_marker\":\"" BUILD_MARKER "\",\"status\":\"%s\",\"passed\":%s,\"failure\":",
           passed ? "passed" : "failed", passed ? "true" : "false");
    json_string(failure);
    printf(",\"scope\":\"bounded_wgl_gpu_prerequisites\",\"pointer_bits\":%d,\"win32_error\":%lu,\"gl_error\":%lu,\"gl_vendor\":",
           r->pointer_bits, r->win32_error, r->gl_error);
    json_string(vendor); fputs(",\"gl_renderer\":", stdout); json_string(renderer);
    fputs(",\"gl_version\":", stdout); json_string(version);
#define EMIT_BOOL(name) printf(",\"" #name "\":%s", r->name ? "true" : "false")
    EMIT_BOOL(zink_nonsoftware); EMIT_BOOL(multitexture); EMIT_BOOL(texture_compression);
    EMIT_BOOL(arb_vertex_program); EMIT_BOOL(arb_fragment_program);
    EMIT_BOOL(framebuffer_extension); EMIT_BOOL(vertex_buffer_object);
    EMIT_BOOL(s3tc); EMIT_BOOL(npot); EMIT_BOOL(bgra_extension);
    EMIT_BOOL(api_loaded); EMIT_BOOL(arb_programs); EMIT_BOOL(multitexture_render);
    EMIT_BOOL(vbo_render); EMIT_BOOL(npot_depth24_fbo);
    EMIT_BOOL(dxt1_render); EMIT_BOOL(dxt3_render); EMIT_BOOL(dxt5_render);
    EMIT_BOOL(dxt1_mipmaps); EMIT_BOOL(dxt3_mipmaps); EMIT_BOOL(dxt5_mipmaps);
    EMIT_BOOL(dxt1_subimage); EMIT_BOOL(dxt3_subimage); EMIT_BOOL(dxt5_subimage);
    EMIT_BOOL(bgra_render); EMIT_BOOL(bgra_subimage); EMIT_BOOL(backbuffer_render);
    EMIT_BOOL(swapped); EMIT_BOOL(frontbuffer_readback); EMIT_BOOL(cleanup_ok);
    EMIT_BOOL(presented_pattern_first); EMIT_BOOL(presented_pattern_second); EMIT_BOOL(presented_readback);
#undef EMIT_BOOL
    printf(",\"frontbuffer_gl_error\":%lu,\"presentation_method\":\"win32_screen_getpixel_two_patterns\","
           "\"presentation_sample_count\":%d,\"presentation_pattern_count\":2,"
           "\"presentation_client_width\":%d,\"presentation_client_height\":%d,"
           "\"presentation_attempts_first\":%u,\"presentation_attempts_second\":%u,"
           "\"presentation_elapsed_ms_first\":%u,\"presentation_elapsed_ms_second\":%u,"
           "\"presented_pixels_first\":",
           r->frontbuffer_gl_error,SAMPLE_COUNT,r->presentation_client_width,r->presentation_client_height,
           r->presentation_attempts_first,r->presentation_attempts_second,
           r->presentation_elapsed_ms_first,r->presentation_elapsed_ms_second);
    print_presented_pixels(r->presented_pixels_first);
    fputs(",\"presented_pixels_second\":",stdout); print_presented_pixels(r->presented_pixels_second);
    printf(",\"fp_max_local_parameters\":%d,\"fp_max_temporaries\":%d,\"fp_max_native_temporaries\":%d,",
           r->fp_max_local_parameters, r->fp_max_temporaries, r->fp_max_native_temporaries);
    puts("\"game_rendering_validated\":false,\"cg_shaders_validated\":false,\"android_surface_validated\":false,\"hardware_acceleration_validated\":false}");
}

#ifndef COH_GPU_PROBE_TEST
#include <windows.h>
#include <GL/gl.h>
#include <stdint.h>

/* Windows OpenGL headers expose 1.1 only. Explicit ARB/EXT signatures avoid
 * relying on a host extension-header revision, including with MSVC. */
#define C_TEXTURE0 0x84C0
#define C_TEXTURE1 0x84C1
#define C_BGRA 0x80E1
#define C_RGBA8 0x8058
#define C_VERTEX_PROGRAM 0x8620
#define C_FRAGMENT_PROGRAM 0x8804
#define C_PROGRAM_FORMAT_ASCII 0x8875
#define C_PROGRAM_ERROR_POSITION 0x864B
#define C_MAX_PROGRAM_LOCAL_PARAMETERS 0x88B4
#define C_MAX_PROGRAM_TEMPORARIES 0x88A5
#define C_MAX_PROGRAM_NATIVE_TEMPORARIES 0x88A7
#define C_ARRAY_BUFFER 0x8892
#define C_ELEMENT_ARRAY_BUFFER 0x8893
#define C_STATIC_DRAW 0x88E4
#define C_FRAMEBUFFER 0x8D40
#define C_RENDERBUFFER 0x8D41
#define C_COLOR_ATTACHMENT0 0x8CE0
#define C_DEPTH_ATTACHMENT 0x8D00
#define C_FRAMEBUFFER_COMPLETE 0x8CD5
#define C_DEPTH_COMPONENT24 0x81A6
#define C_RENDERBUFFER_DEPTH_SIZE 0x8D54
#define C_DXT1 0x83F1
#define C_DXT3 0x83F2
#define C_DXT5 0x83F3
#define C_TEXTURE_COMPRESSED 0x86A1
#define C_TEXTURE_BASE_LEVEL 0x813C
#define C_TEXTURE_MAX_LEVEL 0x813D

typedef void (APIENTRY *enum_call)(GLenum);
typedef void (APIENTRY *gen_call)(GLsizei, GLuint *);
typedef void (APIENTRY *delete_call)(GLsizei, const GLuint *);
typedef void (APIENTRY *bind_call)(GLenum, GLuint);
typedef void (APIENTRY *program_string_call)(GLenum, GLenum, GLsizei, const void *);
typedef void (APIENTRY *program_query_call)(GLenum, GLenum, GLint *);
typedef void (APIENTRY *local_parameter_call)(GLenum, GLuint, GLfloat, GLfloat, GLfloat, GLfloat);
typedef void (APIENTRY *buffer_data_call)(GLenum, ptrdiff_t, const void *, GLenum);
typedef void (APIENTRY *renderbuffer_storage_call)(GLenum, GLenum, GLsizei, GLsizei);
typedef void (APIENTRY *framebuffer_texture_call)(GLenum, GLenum, GLenum, GLuint, GLint);
typedef void (APIENTRY *framebuffer_renderbuffer_call)(GLenum, GLenum, GLenum, GLuint);
typedef GLenum (APIENTRY *framebuffer_status_call)(GLenum);
typedef void (APIENTRY *compressed_image_call)(GLenum, GLint, GLenum, GLsizei, GLsizei, GLint, GLsizei, const void *);
typedef void (APIENTRY *compressed_subimage_call)(GLenum, GLint, GLint, GLint, GLsizei, GLsizei, GLenum, GLsizei, const void *);

struct gl_api {
    enum_call active_texture, client_active_texture;
    gen_call gen_programs, gen_buffers, gen_framebuffers, gen_renderbuffers;
    delete_call delete_programs, delete_buffers, delete_framebuffers, delete_renderbuffers;
    bind_call bind_program, bind_buffer, bind_framebuffer, bind_renderbuffer;
    program_string_call program_string;
    program_query_call get_program, get_renderbuffer;
    local_parameter_call program_local_parameter;
    buffer_data_call buffer_data;
    renderbuffer_storage_call renderbuffer_storage;
    framebuffer_texture_call framebuffer_texture;
    framebuffer_renderbuffer_call framebuffer_renderbuffer;
    framebuffer_status_call framebuffer_status;
    compressed_image_call compressed_image;
    compressed_subimage_call compressed_subimage;
};

struct objects {
    GLuint textures[2], programs[2], vertices, indices, framebuffer, depth;
};

static int load_proc(void *destination, size_t size, const char *name) {
    PROC address = wglGetProcAddress(name);
    /* WGL implementations may return sentinel addresses for unsupported calls. */
    uintptr_t value = (uintptr_t)address;
    if (!address || value == 1 || value == 2 || value == 3 || value == (uintptr_t)-1 ||
        size != sizeof(address)) return 0;
    memcpy(destination, &address, size);
    return 1;
}

static int load_api(struct gl_api *a) {
#define LOAD(member, name) if (!load_proc(&a->member, sizeof(a->member), name)) return 0
    LOAD(active_texture, "glActiveTextureARB"); LOAD(client_active_texture, "glClientActiveTextureARB");
    LOAD(gen_programs, "glGenProgramsARB"); LOAD(delete_programs, "glDeleteProgramsARB");
    LOAD(bind_program, "glBindProgramARB"); LOAD(program_string, "glProgramStringARB");
    LOAD(get_program, "glGetProgramivARB"); LOAD(program_local_parameter, "glProgramLocalParameter4fARB");
    LOAD(gen_buffers, "glGenBuffersARB"); LOAD(delete_buffers, "glDeleteBuffersARB");
    LOAD(bind_buffer, "glBindBufferARB"); LOAD(buffer_data, "glBufferDataARB");
    LOAD(gen_framebuffers, "glGenFramebuffersEXT"); LOAD(delete_framebuffers, "glDeleteFramebuffersEXT");
    LOAD(bind_framebuffer, "glBindFramebufferEXT"); LOAD(framebuffer_texture, "glFramebufferTexture2DEXT");
    LOAD(framebuffer_renderbuffer, "glFramebufferRenderbufferEXT"); LOAD(framebuffer_status, "glCheckFramebufferStatusEXT");
    LOAD(gen_renderbuffers, "glGenRenderbuffersEXT"); LOAD(delete_renderbuffers, "glDeleteRenderbuffersEXT");
    LOAD(bind_renderbuffer, "glBindRenderbufferEXT"); LOAD(renderbuffer_storage, "glRenderbufferStorageEXT");
    LOAD(get_renderbuffer, "glGetRenderbufferParameterivEXT");
    LOAD(compressed_image, "glCompressedTexImage2DARB");
    LOAD(compressed_subimage, "glCompressedTexSubImage2DARB");
#undef LOAD
    return 1;
}

static int no_gl_error(struct probe_result *r) {
    unsigned int i;
    int clean = 1;
    for (i = 0; i < 32; ++i) {
        GLenum error = glGetError();
        if (error == GL_NO_ERROR) return clean;
        clean = 0;
        if (!r->gl_error) r->gl_error = error;
    }
    return 0;
}

static int compile_program(const struct gl_api *a, struct probe_result *r,
                             GLenum target, GLuint program, const char *source) {
    GLint error_position = 0;
    a->bind_program(target, program);
    a->program_string(target, C_PROGRAM_FORMAT_ASCII, (GLsizei)strlen(source), source);
    glGetIntegerv(C_PROGRAM_ERROR_POSITION, &error_position);
    return no_gl_error(r) && error_position == -1;
}

static int create_programs(const struct gl_api *a, struct objects *o, struct probe_result *r) {
    static const char vertex_source[] =
        "!!ARBvp1.0\nMOV result.position, vertex.position;\n"
        "MOV result.texcoord[0], vertex.texcoord[0];\n"
        "MOV result.texcoord[1], vertex.texcoord[1];\nEND\n";
    static const char fragment_source[] =
        "!!ARBfp1.0\nTEMP t0,t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12,t13,t14,t15,t16;\n"
        "PARAM tone = program.local[31];\n"
        "TEX t0, fragment.texcoord[0], texture[0], 2D;\n"
        "TEX t1, fragment.texcoord[1], texture[1], 2D;\n"
        "MUL t16, t0, t1;\nMUL result.color, t16, tone;\nEND\n";
    a->get_program(C_FRAGMENT_PROGRAM, C_MAX_PROGRAM_LOCAL_PARAMETERS, &r->fp_max_local_parameters);
    a->get_program(C_FRAGMENT_PROGRAM, C_MAX_PROGRAM_TEMPORARIES, &r->fp_max_temporaries);
    a->get_program(C_FRAGMENT_PROGRAM, C_MAX_PROGRAM_NATIVE_TEMPORARIES, &r->fp_max_native_temporaries);
    if (!no_gl_error(r) || r->fp_max_local_parameters < 32 || r->fp_max_temporaries < 17 ||
        r->fp_max_native_temporaries < 17) return 0;
    a->gen_programs(2, o->programs);
    if (!o->programs[0] || !o->programs[1] || !no_gl_error(r)) return 0;
    if (!compile_program(a, r, C_VERTEX_PROGRAM, o->programs[0], vertex_source) ||
        !compile_program(a, r, C_FRAGMENT_PROGRAM, o->programs[1], fragment_source)) return 0;
    a->program_local_parameter(C_FRAGMENT_PROGRAM, 31, 1.0f, 1.0f, 1.0f, 1.0f);
    glEnable(C_VERTEX_PROGRAM); glEnable(C_FRAGMENT_PROGRAM);
    return no_gl_error(r);
}

static void upload_vertices(const struct gl_api *a, const struct objects *o, GLfloat z) {
    GLfloat vertices[4][5] = {{-1,-1,0,0,0}, {1,-1,0,1,0}, {1,1,0,1,1}, {-1,1,0,0,1}};
    unsigned int i;
    for (i = 0; i < 4; ++i) vertices[i][2] = z;
    a->bind_buffer(C_ARRAY_BUFFER, o->vertices);
    a->buffer_data(C_ARRAY_BUFFER, sizeof(vertices), vertices, C_STATIC_DRAW);
}

static int create_vbo(const struct gl_api *a, struct objects *o, struct probe_result *r) {
    static const GLushort indices[6] = {0,1,2,0,2,3};
    a->gen_buffers(1, &o->vertices); a->gen_buffers(1, &o->indices);
    if (!o->vertices || !o->indices || !no_gl_error(r)) return 0;
    upload_vertices(a, o, 0.0f);
    a->bind_buffer(C_ELEMENT_ARRAY_BUFFER, o->indices);
    a->buffer_data(C_ELEMENT_ARRAY_BUFFER, sizeof(indices), indices, C_STATIC_DRAW);
    glVertexPointer(3, GL_FLOAT, 5 * sizeof(GLfloat), (const void *)(uintptr_t)0);
    glEnableClientState(GL_VERTEX_ARRAY);
    a->client_active_texture(C_TEXTURE0);
    glTexCoordPointer(2, GL_FLOAT, 5 * sizeof(GLfloat), (const void *)(uintptr_t)(3 * sizeof(GLfloat)));
    glEnableClientState(GL_TEXTURE_COORD_ARRAY);
    a->client_active_texture(C_TEXTURE1);
    glTexCoordPointer(2, GL_FLOAT, 5 * sizeof(GLfloat), (const void *)(uintptr_t)(3 * sizeof(GLfloat)));
    glEnableClientState(GL_TEXTURE_COORD_ARRAY);
    a->client_active_texture(C_TEXTURE0);
    return no_gl_error(r);
}

static void texture_parameters(void) {
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP);
    glTexParameteri(GL_TEXTURE_2D, C_TEXTURE_BASE_LEVEL, 0);
    glTexParameteri(GL_TEXTURE_2D, C_TEXTURE_MAX_LEVEL, 0);
}

static int create_fbo(const struct gl_api *a, struct objects *o, struct probe_result *r,
                        GLuint *target_texture) {
    GLint depth_size = 0;
    glGenTextures(1, target_texture);
    a->gen_framebuffers(1, &o->framebuffer); a->gen_renderbuffers(1, &o->depth);
    if (!*target_texture || !o->framebuffer || !o->depth || !no_gl_error(r)) return 0;
    glBindTexture(GL_TEXTURE_2D, *target_texture); texture_parameters();
    glTexImage2D(GL_TEXTURE_2D, 0, C_RGBA8, 600, 450, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
    a->bind_renderbuffer(C_RENDERBUFFER, o->depth);
    a->renderbuffer_storage(C_RENDERBUFFER, C_DEPTH_COMPONENT24, 600, 450);
    a->get_renderbuffer(C_RENDERBUFFER, C_RENDERBUFFER_DEPTH_SIZE, &depth_size);
    a->bind_framebuffer(C_FRAMEBUFFER, o->framebuffer);
    a->framebuffer_texture(C_FRAMEBUFFER, C_COLOR_ATTACHMENT0, GL_TEXTURE_2D, *target_texture, 0);
    a->framebuffer_renderbuffer(C_FRAMEBUFFER, C_DEPTH_ATTACHMENT, C_RENDERBUFFER, o->depth);
    if (!no_gl_error(r) || depth_size < 24 ||
        a->framebuffer_status(C_FRAMEBUFFER) != C_FRAMEBUFFER_COMPLETE || !no_gl_error(r)) return 0;
    glDrawBuffer(C_COLOR_ATTACHMENT0); glReadBuffer(C_COLOR_ATTACHMENT0);
    glViewport(0, 0, 600, 450);
    return no_gl_error(r);
}

static int read_samples(struct probe_result *r, unsigned char actual[SAMPLE_COUNT][4],
                          const unsigned char expected[SAMPLE_COUNT][4], GLint width, GLint height) {
    unsigned int i;
    static const GLint quadrant[4][2] = {{1,1},{3,1},{1,3},{3,3}};
    glFinish();
    for (i = 0; i < SAMPLE_COUNT; ++i)
        glReadPixels(width * quadrant[i][0] / 4, height * quadrant[i][1] / 4,
                     1, 1, GL_RGBA, GL_UNSIGNED_BYTE, actual[i]);
    return no_gl_error(r) && pixels_match(actual, expected);
}

static int draw_readback(struct probe_result *r, const unsigned char expected[SAMPLE_COUNT][4],
                           GLint width, GLint height) {
    unsigned char actual[SAMPLE_COUNT][4] = {{0}};
    glClearColor(0,0,0,0); glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_SHORT, (const void *)(uintptr_t)0);
    return read_samples(r, actual, expected, width, height);
}

static int pump_probe_messages(HWND window) {
    MSG message;
    unsigned int i;
    /* A continuously refilled message queue cannot turn this into an unbounded
     * wait. The outer screen polling and caller's process timeout remain bound. */
    for (i = 0; i < 64 && PeekMessageA(&message,NULL,0,0,PM_REMOVE); ++i) {
        if (message.message == WM_QUIT) return 0;
        TranslateMessage(&message); DispatchMessageA(&message);
    }
    return IsWindow(window) && IsWindowVisible(window) && !IsIconic(window);
}

static int read_presented_pattern(HWND window, HDC screen_dc, struct probe_result *r,
                                    const unsigned char expected[SAMPLE_COUNT][4],
                                    unsigned char actual[SAMPLE_COUNT][3],
                                    unsigned int *attempts, unsigned int *elapsed) {
    unsigned int started = (unsigned int)GetTickCount();
    for (;;) {
        RECT client;
        unsigned int i;
        int owned = pump_probe_messages(window) && GetClientRect(window,&client);
        int verdict;
        if (owned) {
            r->presentation_client_width = (int)(client.right - client.left);
            r->presentation_client_height = (int)(client.bottom - client.top);
            owned = client.left == 0 && client.top == 0 &&
                r->presentation_client_width == PRESENTATION_SIZE &&
                r->presentation_client_height == PRESENTATION_SIZE;
        }
        memset(actual,0,SAMPLE_COUNT * 3);
        for (i = 0; owned && i < SAMPLE_COUNT; ++i) {
            int x, y;
            POINT point;
            COLORREF color;
            if (!presentation_coordinates(r->presentation_client_width,r->presentation_client_height,
                                          i,&x,&y)) { owned = 0; break; }
            point.x = x; point.y = y;
            /* Read the visible screen, never this OpenGL DC or an FBO/back
             * image. ClientToScreen uses device coordinates. WindowFromPoint
             * prevents an occluding/stale foreign window from supplying proof.
             * GetDC/GetPixel/ClientToScreen/WindowFromPoint contracts:
             * learn.microsoft.com/en-us/windows/win32/api/{winuser,wingdi}/
             * nf-winuser-getdc, nf-wingdi-getpixel, nf-winuser-clienttoscreen,
             * nf-winuser-windowfrompoint. This validates private X presentation,
             * not the subsequent Android Surface or Game/Cg execution. */
            if (!ClientToScreen(window,&point) || WindowFromPoint(point) != window) {
                owned = 0; break;
            }
            color = GetPixel(screen_dc,(int)point.x,(int)point.y);
            if (color == CLR_INVALID || WindowFromPoint(point) != window) { owned = 0; break; }
            actual[i][0] = GetRValue(color); actual[i][1] = GetGValue(color); actual[i][2] = GetBValue(color);
        }
        verdict = presentation_poll_step(started,(unsigned int)GetTickCount(),attempts,elapsed,
                                         owned,actual,expected);
        if (verdict) return verdict > 0;
        /* Gives Wine/X11 presentation messages time to arrive without an
         * indefinite GetMessage wait or a render-loop retry hiding bad pixels. */
        MsgWaitForMultipleObjects(0,NULL,FALSE,PRESENTATION_WAIT_MS,QS_ALLINPUT);
    }
}

static int texture_properties(struct probe_result *r, GLint level, GLenum format, GLint width) {
    GLint compressed = 0, internal = 0, actual_width = 0, actual_height = 0;
    glGetTexLevelParameteriv(GL_TEXTURE_2D, level, C_TEXTURE_COMPRESSED, &compressed);
    glGetTexLevelParameteriv(GL_TEXTURE_2D, level, GL_TEXTURE_INTERNAL_FORMAT, &internal);
    glGetTexLevelParameteriv(GL_TEXTURE_2D, level, GL_TEXTURE_WIDTH, &actual_width);
    glGetTexLevelParameteriv(GL_TEXTURE_2D, level, GL_TEXTURE_HEIGHT, &actual_height);
    return no_gl_error(r) && compressed == GL_TRUE && internal == (GLint)format &&
        actual_width == width && actual_height == width;
}

static int compressed_test(const struct gl_api *a, struct objects *o, struct probe_result *r,
                             unsigned int kind, int *rendered, int *mipmaps, int *subimage) {
    static const GLenum formats[3] = {C_DXT1,C_DXT3,C_DXT5};
    unsigned char base[64], mip[64], expected[SAMPLE_COUNT][4];
    GLuint texture = 0;
    GLsizei block_size = kind == 0 ? 8 : 16;
    int success = 0;
    (void)o;
    glGenTextures(1, &texture);
    if (!texture || !no_gl_error(r)) goto done;
    glBindTexture(GL_TEXTURE_2D, texture); texture_parameters();
    fill_compressed(base, kind, 4);
    memset(mip,0,sizeof(mip));
    memcpy(mip,dxt_alternate_blocks[kind],(size_t)block_size);
    a->compressed_image(GL_TEXTURE_2D, 0, formats[kind], 8, 8, 0, 4*block_size, base);
    a->compressed_image(GL_TEXTURE_2D, 1, formats[kind], 4, 4, 0, block_size, mip);
    if (!texture_properties(r, 0, formats[kind], 8) ||
        !texture_properties(r, 1, formats[kind], 4)) goto done;
    solid_expected(expected, dxt_expected[kind]);
    *rendered = draw_readback(r, expected, 600, 450);
    if (!*rendered) goto done;
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST_MIPMAP_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, C_TEXTURE_BASE_LEVEL, 1);
    glTexParameteri(GL_TEXTURE_2D, C_TEXTURE_MAX_LEVEL, 1);
    solid_expected(expected,dxt_alternate_expected[kind]);
    *mipmaps = draw_readback(r, expected, 600, 450);
    if (!*mipmaps) goto done;
    texture_parameters();
    a->compressed_subimage(GL_TEXTURE_2D, 0, 0, 0, 4, 4, formats[kind], block_size,
                          dxt_alternate_blocks[kind]);
    solid_expected(expected,dxt_expected[kind]);
    memcpy(expected[0], dxt_alternate_expected[kind], 4);
    *subimage = draw_readback(r, expected, 600, 450);
    success = *subimage;
done:
    if (texture) glDeleteTextures(1, &texture);
    if (!no_gl_error(r)) success = 0;
    return success;
}

static int run_render_tests(const struct gl_api *a, struct objects *o, struct probe_result *r) {
    static const unsigned char modulation[4] = {255,128,255,255};
    static const unsigned char white[4] = {255,255,255,255};
    static const unsigned char bgra_color[4] = {173,93,41,255};
    static const unsigned char bgra_alternate[4] = {47,161,219,255};
    unsigned char expected[SAMPLE_COUNT][4], pixels[3*5*4], actual[SAMPLE_COUNT][4];
    GLuint target_texture = 0;
    int success = 0;
    glDisable(GL_DITHER); glDisable(GL_BLEND); glDisable(GL_ALPHA_TEST);
    glDisable(GL_SCISSOR_TEST); glDisable(GL_STENCIL_TEST); glDisable(GL_CULL_FACE);
    glDisable(GL_LIGHTING); glDisable(GL_FOG); glDisable(GL_DEPTH_TEST);
    glPixelStorei(GL_UNPACK_ALIGNMENT,1); glPixelStorei(GL_PACK_ALIGNMENT,1);
    glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE); glDepthMask(GL_TRUE);
    glClearDepth(1.0); glDepthFunc(GL_LESS);
    glGenTextures(2, o->textures);
    if (!o->textures[0] || !o->textures[1] || !no_gl_error(r)) goto done;
    a->active_texture(C_TEXTURE1);
    glBindTexture(GL_TEXTURE_2D,o->textures[1]); texture_parameters();
    glTexImage2D(GL_TEXTURE_2D,0,C_RGBA8,1,1,0,GL_RGBA,GL_UNSIGNED_BYTE,modulation);
    a->active_texture(C_TEXTURE0);
    if (!create_fbo(a,o,r,&target_texture) || !create_vbo(a,o,r)) goto done;
    glBindTexture(GL_TEXTURE_2D,o->textures[0]); texture_parameters();
    glTexImage2D(GL_TEXTURE_2D,0,C_RGBA8,2,2,0,GL_RGBA,GL_UNSIGNED_BYTE,pattern_rgba);
    memcpy(expected,pattern_rgba,sizeof(expected));
    expected[1][1] = expected[3][1] = 128;
    r->multitexture_render = draw_readback(r,expected,600,450);
    if (!r->multitexture_render) goto done;
    a->active_texture(C_TEXTURE1); glBindTexture(GL_TEXTURE_2D,o->textures[1]);
    glTexImage2D(GL_TEXTURE_2D,0,C_RGBA8,1,1,0,GL_RGBA,GL_UNSIGNED_BYTE,white);
    a->active_texture(C_TEXTURE0); glBindTexture(GL_TEXTURE_2D,o->textures[0]);
    r->vbo_render = draw_readback(r,pattern_rgba,600,450);
    if (!r->vbo_render) goto done;
    fill_bgra(pixels,bgra_color); solid_expected(expected,bgra_color);
    glTexImage2D(GL_TEXTURE_2D,0,C_RGBA8,3,5,0,C_BGRA,GL_UNSIGNED_BYTE,pixels);
    glEnable(GL_DEPTH_TEST);
    r->bgra_render = draw_readback(r,expected,600,450);
    if (!r->bgra_render) goto done;
    /* A farther red draw must leave the previously drawn NPOT image intact. */
    upload_vertices(a,o,0.5f);
    glTexImage2D(GL_TEXTURE_2D,0,C_RGBA8,1,1,0,GL_RGBA,GL_UNSIGNED_BYTE,pattern_rgba[0]);
    glDrawElements(GL_TRIANGLES,6,GL_UNSIGNED_SHORT,(const void *)(uintptr_t)0);
    r->npot_depth24_fbo = read_samples(r,actual,expected,600,450);
    upload_vertices(a,o,0.0f); glDisable(GL_DEPTH_TEST);
    if (!r->npot_depth24_fbo) goto done;
    fill_bgra(pixels,bgra_color);
    glTexImage2D(GL_TEXTURE_2D,0,C_RGBA8,3,5,0,C_BGRA,GL_UNSIGNED_BYTE,pixels);
    fill_bgra(pixels,bgra_alternate); solid_expected(expected,bgra_alternate);
    glTexSubImage2D(GL_TEXTURE_2D,0,0,0,3,5,C_BGRA,GL_UNSIGNED_BYTE,pixels);
    r->bgra_subimage = draw_readback(r,expected,600,450);
    if (!r->bgra_subimage) goto done;
    if (!compressed_test(a,o,r,0,&r->dxt1_render,&r->dxt1_mipmaps,&r->dxt1_subimage) ||
        !compressed_test(a,o,r,1,&r->dxt3_render,&r->dxt3_mipmaps,&r->dxt3_subimage) ||
        !compressed_test(a,o,r,2,&r->dxt5_render,&r->dxt5_mipmaps,&r->dxt5_subimage)) goto done;
    a->bind_framebuffer(C_FRAMEBUFFER,0);
    glDrawBuffer(GL_BACK); glReadBuffer(GL_BACK); glViewport(0,0,PRESENTATION_SIZE,PRESENTATION_SIZE);
    glBindTexture(GL_TEXTURE_2D,o->textures[0]); texture_parameters();
    glTexImage2D(GL_TEXTURE_2D,0,C_RGBA8,2,2,0,GL_RGBA,GL_UNSIGNED_BYTE,pattern_rgba);
    r->backbuffer_render = draw_readback(r,pattern_rgba,PRESENTATION_SIZE,PRESENTATION_SIZE);
    success = r->backbuffer_render;
done:
    if (a->bind_framebuffer) a->bind_framebuffer(C_FRAMEBUFFER,0);
    if (target_texture) glDeleteTextures(1,&target_texture);
    if (!no_gl_error(r)) success = 0;
    return success;
}

static int delete_objects(const struct gl_api *a, struct objects *o, struct probe_result *r) {
    /* API loading completes before any object is generated. */
    if (r->api_loaded) {
        glDisable(C_VERTEX_PROGRAM); glDisable(C_FRAGMENT_PROGRAM);
        a->bind_framebuffer(C_FRAMEBUFFER,0); a->bind_renderbuffer(C_RENDERBUFFER,0);
        a->bind_buffer(C_ARRAY_BUFFER,0); a->bind_buffer(C_ELEMENT_ARRAY_BUFFER,0);
        glDisableClientState(GL_VERTEX_ARRAY);
        a->client_active_texture(C_TEXTURE1); glDisableClientState(GL_TEXTURE_COORD_ARRAY);
        a->client_active_texture(C_TEXTURE0); glDisableClientState(GL_TEXTURE_COORD_ARRAY);
        a->active_texture(C_TEXTURE1); glBindTexture(GL_TEXTURE_2D,0);
        a->active_texture(C_TEXTURE0); glBindTexture(GL_TEXTURE_2D,0);
        a->bind_program(C_VERTEX_PROGRAM,0); a->bind_program(C_FRAGMENT_PROGRAM,0);
        if (o->framebuffer) a->delete_framebuffers(1,&o->framebuffer);
        if (o->depth) a->delete_renderbuffers(1,&o->depth);
        if (o->vertices) a->delete_buffers(1,&o->vertices);
        if (o->indices) a->delete_buffers(1,&o->indices);
        if (o->programs[0] || o->programs[1]) a->delete_programs(2,o->programs);
        if (o->textures[0] || o->textures[1]) glDeleteTextures(2,o->textures);
    }
    return no_gl_error(r);
}

static LRESULT CALLBACK window_proc(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    return DefWindowProcA(window,message,wparam,lparam);
}

int main(int argc, char **argv) {
    struct probe_result r;
    struct gl_api api;
    struct objects objects;
    WNDCLASSA klass;
    PIXELFORMATDESCRIPTOR requested, chosen;
    HINSTANCE instance = GetModuleHandleA(NULL);
    HWND window = NULL;
    HDC dc = NULL, screen_dc = NULL;
    HGLRC context = NULL;
    int registered = 0, current = 0, format, completed = 0, cleanup_ok = 1;
    const char *failure = "arguments", *extensions, *vendor, *renderer, *version;
    char saved_vendor[STRING_LIMIT+1] = "", saved_renderer[STRING_LIMIT+1] = "", saved_version[STRING_LIMIT+1] = "";
    unsigned char front[SAMPLE_COUNT][4] = {{0}};
    (void)argv;
    memset(&r,0,sizeof(r)); memset(&api,0,sizeof(api)); memset(&objects,0,sizeof(objects));
    memset(&klass,0,sizeof(klass)); memset(&requested,0,sizeof(requested)); memset(&chosen,0,sizeof(chosen));
    r.pointer_bits = (int)(sizeof(void *) * 8);
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
    setvbuf(stdout,NULL,_IONBF,0);
    if (argc != 1) goto done;
    failure = "pointer_bits";
    if (r.pointer_bits != 32) goto done;
    klass.style = CS_OWNDC; klass.lpfnWndProc = window_proc;
    klass.hInstance = instance; klass.lpszClassName = "COHGpuProbeV2";
    failure = "window_class";
    if (!RegisterClassA(&klass)) goto done;
    registered = 1;
    failure = "window_create";
    window = CreateWindowA(klass.lpszClassName,"COH GPU prerequisite probe",
                           WS_POPUP | WS_CLIPSIBLINGS | WS_CLIPCHILDREN,
                           16,16,PRESENTATION_SIZE,PRESENTATION_SIZE,NULL,NULL,instance,NULL);
    if (!window) goto done;
    /* Only the caller's private diagnostic X server receives this window. */
    ShowWindow(window,SW_SHOW); UpdateWindow(window);
    failure = "window_visible_client";
    if (!SetWindowPos(window,HWND_TOPMOST,16,16,PRESENTATION_SIZE,PRESENTATION_SIZE,SWP_SHOWWINDOW) ||
        !pump_probe_messages(window)) goto done;
    failure = "screen_dc";
    screen_dc = GetDC(NULL);
    if (!screen_dc) goto done;
    failure = "window_dc";
    dc = GetDC(window);
    if (!dc) goto done;
    requested.nSize = sizeof(requested); requested.nVersion = 1;
    requested.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
    requested.iPixelType = PFD_TYPE_RGBA; requested.cColorBits = 24;
    requested.cAlphaBits = 8; requested.cDepthBits = 24; requested.iLayerType = PFD_MAIN_PLANE;
    failure = "pixel_format";
    format = ChoosePixelFormat(dc,&requested);
    if (!format || !DescribePixelFormat(dc,format,sizeof(chosen),&chosen) ||
        (chosen.dwFlags & requested.dwFlags) != requested.dwFlags || chosen.iPixelType != PFD_TYPE_RGBA ||
        chosen.cColorBits < 24 || !SetPixelFormat(dc,format,&requested)) goto done;
    failure = "wgl_context";
    context = wglCreateContext(dc);
    if (!context || !wglMakeCurrent(dc,context)) goto done;
    current = 1;
    failure = "gl_identity";
    vendor = (const char *)glGetString(GL_VENDOR); renderer = (const char *)glGetString(GL_RENDERER);
    version = (const char *)glGetString(GL_VERSION); extensions = (const char *)glGetString(GL_EXTENSIONS);
    if (!vendor || !*vendor || !renderer || !*renderer || !version || !*version || !extensions || !no_gl_error(&r)) goto done;
    copy_string(saved_vendor,vendor); copy_string(saved_renderer,renderer); copy_string(saved_version,version);
    r.zink_nonsoftware = nonsoftware_zink(saved_renderer);
    r.multitexture = extension_present(extensions,"GL_ARB_multitexture");
    r.texture_compression = extension_present(extensions,"GL_ARB_texture_compression");
    r.arb_vertex_program = extension_present(extensions,"GL_ARB_vertex_program");
    r.arb_fragment_program = extension_present(extensions,"GL_ARB_fragment_program");
    r.framebuffer_extension = extension_present(extensions,"GL_EXT_framebuffer_object");
    r.vertex_buffer_object = extension_present(extensions,"GL_ARB_vertex_buffer_object");
    r.s3tc = extension_present(extensions,"GL_EXT_texture_compression_s3tc");
    r.npot = extension_present(extensions,"GL_ARB_texture_non_power_of_two");
    r.bgra_extension = extension_present(extensions,"GL_EXT_bgra");
    failure = "nonsoftware_zink_identity";
    if (!r.zink_nonsoftware) goto done;
    failure = "required_extensions";
    if (!r.multitexture || !r.texture_compression || !r.arb_vertex_program || !r.arb_fragment_program ||
        !r.framebuffer_extension || !r.vertex_buffer_object || !r.s3tc || !r.npot || !r.bgra_extension) goto done;
    failure = "required_entrypoints";
    r.api_loaded = load_api(&api);
    if (!r.api_loaded) goto done;
    failure = "arb_program_compile_and_limits";
    r.arb_programs = create_programs(&api,&objects,&r);
    if (!r.arb_programs) goto done;
    failure = "indexed_vbo_fbo_texture_readback";
    if (!run_render_tests(&api,&objects,&r)) goto done;
    failure = "swap_buffers";
    r.swapped = SwapBuffers(dc) != 0;
    if (!r.swapped || !no_gl_error(&r)) goto done;
    /* GLX/Kopper swap semantics need not retain a readable GL_FRONT image.
     * Keep that old check as a diagnostic, with its own error channel, then
     * independently require actual visible-screen pixels after TWO swaps. */
    {
        struct probe_result diagnostic;
        memset(&diagnostic,0,sizeof(diagnostic));
        glReadBuffer(GL_FRONT);
        r.frontbuffer_readback = read_samples(&diagnostic,front,pattern_rgba,
                                              PRESENTATION_SIZE,PRESENTATION_SIZE);
        r.frontbuffer_gl_error = diagnostic.gl_error;
    }
    glReadBuffer(GL_BACK); glFinish();
    if (!no_gl_error(&r)) goto done;
    failure = "post_swap_presented_pattern_first";
    r.presented_pattern_first = read_presented_pattern(window,screen_dc,&r,pattern_rgba,
        r.presented_pixels_first,&r.presentation_attempts_first,&r.presentation_elapsed_ms_first);
    if (!r.presented_pattern_first) goto done;
    /* Rendering a second distinct pattern and proving it on-screen rejects an
     * unchanged first frame even if SwapBuffers itself reports success. */
    failure = "second_backbuffer_readback";
    glBindTexture(GL_TEXTURE_2D,objects.textures[0]);
    glTexImage2D(GL_TEXTURE_2D,0,C_RGBA8,2,2,0,GL_RGBA,GL_UNSIGNED_BYTE,presentation_alternate_rgba);
    if (!draw_readback(&r,presentation_alternate_rgba,PRESENTATION_SIZE,PRESENTATION_SIZE)) goto done;
    failure = "second_swap_buffers";
    r.swapped = SwapBuffers(dc) != 0;
    glFinish();
    if (!r.swapped || !no_gl_error(&r)) goto done;
    failure = "post_swap_presented_pattern_second";
    r.presented_pattern_second = read_presented_pattern(window,screen_dc,&r,presentation_alternate_rgba,
        r.presented_pixels_second,&r.presentation_attempts_second,&r.presentation_elapsed_ms_second);
    r.presented_readback = r.presented_pattern_first && r.presented_pattern_second;
    if (!r.presented_readback) goto done;
    completed = 1;
done:
    if (!completed) r.win32_error = GetLastError();
    if (current && !delete_objects(&api,&objects,&r)) cleanup_ok = 0;
    if (context) {
        if (current && !wglMakeCurrent(NULL,NULL)) cleanup_ok = 0;
        if (!wglDeleteContext(context)) cleanup_ok = 0;
    }
    if (dc && !ReleaseDC(window,dc)) cleanup_ok = 0;
    if (screen_dc && !ReleaseDC(NULL,screen_dc)) cleanup_ok = 0;
    if (window && !DestroyWindow(window)) cleanup_ok = 0;
    if (registered && !UnregisterClassA(klass.lpszClassName,instance)) cleanup_ok = 0;
    r.cleanup_ok = cleanup_ok;
    if (!cleanup_ok && completed) { failure = "cleanup"; r.win32_error = GetLastError(); }
    else if (completed) failure = "";
    print_result(&r,failure,saved_vendor,saved_renderer,saved_version);
    return completed && !*failure && result_passes(&r) ? 0 : 10;
}
#endif
