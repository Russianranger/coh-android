#include "session_stream_qualify.h"
#include <GLES3/gl3.h>
#include <float.h>
#include <math.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define STREAM_VERTEX_LIMIT 200000u
#define STREAM_DRAW_LIMIT 512u
#define STREAM_TARGET_SIZE 256
#define STREAM_COMPONENTS 12u
#define STREAM_TOLERANCE 0.0001f

typedef struct {
    GLuint program, vao, vertex, feedback, transform, fbo, color, depth;
    GLint draw_fbo, read_fbo, viewport[4], pack_buffer, pack_alignment;
    GLint pack_row_length, pack_skip_pixels, pack_skip_rows, renderbuffer;
    GLint transform_binding, feedback_binding, active_texture;
    GLboolean rasterizer_discard, scissor, color_mask[4];
} StreamGpu;

static int reject(char *error, size_t cap, const char *message) {
    if (error && cap) snprintf(error, cap, "%s", message);
    return 0;
}
static int clean_gl(char *error, size_t cap, const char *message) {
    GLenum first = glGetError();
    if (first == GL_NO_ERROR) return 1;
    for (unsigned i = 0; i < 31 && glGetError() != GL_NO_ERROR; ++i) {}
    if (error && cap) snprintf(error, cap, "%s (GL 0x%04x)", message, (unsigned)first);
    return 0;
}
static GLuint shader(GLenum type, const char *source, char *error, size_t cap) {
    GLuint name = glCreateShader(type);
    GLint ok = 0;
    if (!name) { reject(error, cap, "Stream diagnostic shader allocation failed"); return 0; }
    glShaderSource(name, 1, &source, NULL);
    glCompileShader(name);
    glGetShaderiv(name, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[768] = {0};
        glGetShaderInfoLog(name, sizeof log, NULL, log);
        if (error && cap) snprintf(error, cap, "Stream diagnostic shader compile: %.700s", log);
        glDeleteShader(name);
        return 0;
    }
    return name;
}
static int program(StreamGpu *g, char *error, size_t cap) {
    GLint major = 0, minor = 0, ok = 0;
    glGetIntegerv(GL_MAJOR_VERSION, &major);
    glGetIntegerv(GL_MINOR_VERSION, &minor);
    int precise = major > 3 || (major == 3 && minor >= 2);
    if (major < 3) return reject(error, cap, "Stream diagnostics require GLES3");
    const char *vertex = precise ? coh_renderer_vertex_shader_precise() : coh_renderer_vertex_shader();
    const char *fragment = precise ? coh_renderer_fragment_shader_precise(COH_MAT_MULTIPLY) : coh_renderer_fragment_shader(COH_MAT_MULTIPLY);
    GLuint vs = shader(GL_VERTEX_SHADER, vertex, error, cap);
    if (!vs) return 0;
    GLuint fs = shader(GL_FRAGMENT_SHADER, fragment, error, cap);
    if (!fs) { glDeleteShader(vs); return 0; }
    g->program = glCreateProgram();
    if (g->program) {
        const char *varyings[] = {"gl_Position", "vNormal", "vLit", "vFog"};
        glAttachShader(g->program, vs);
        glAttachShader(g->program, fs);
        glTransformFeedbackVaryings(g->program, 4, varyings, GL_INTERLEAVED_ATTRIBS);
        glLinkProgram(g->program);
        glGetProgramiv(g->program, GL_LINK_STATUS, &ok);
    }
    glDeleteShader(vs);
    glDeleteShader(fs);
    if (!ok) {
        char log[768] = {0};
        if (g->program) glGetProgramInfoLog(g->program, sizeof log, NULL, log);
        if (error && cap) snprintf(error, cap, "Stream diagnostic shader link: %.700s", log);
        return 0;
    }
    return clean_gl(error, cap, "Stream diagnostic program failed");
}
static void uniforms(GLuint p, const CohRenderDraw *d) {
    const CohRenderMaterial *m = &d->material;
#define LOCATION(name) glGetUniformLocation(p, name)
    glUseProgram(p);
    glUniformMatrix4fv(LOCATION("uModelView"), 1, GL_FALSE, d->model_view);
    glUniformMatrix4fv(LOCATION("uProjection"), 1, GL_FALSE, d->projection);
    glUniform1i(LOCATION("uLighting"), (GLint)m->lighting);
    glUniform3fv(LOCATION("uLight"), 1, m->light);
    glUniform3fv(LOCATION("uSpecular"), 1, m->specular);
    glUniform4fv(LOCATION("uDiffuse"), 1, m->diffuse);
    glUniform4fv(LOCATION("uAmbient"), 1, m->ambient);
    glUniform1f(LOCATION("uShininess"), m->shininess);
#undef LOCATION
}
static int feedback(StreamGpu *g, const CohRenderDraw *draws, size_t count,
                    size_t max_vertices, CohStreamQualification *stats,
                    char *error, size_t cap) {
    glGenVertexArrays(1, &g->vao);
    glGenBuffers(1, &g->vertex);
    glGenBuffers(1, &g->feedback);
    glGenTransformFeedbacks(1, &g->transform);
    if (!g->vao || !g->vertex || !g->feedback || !g->transform)
        return reject(error, cap, "Stream diagnostic GPU buffers unavailable");
    glBindVertexArray(g->vao);
    glBindBuffer(GL_ARRAY_BUFFER, g->vertex);
    glBufferData(GL_ARRAY_BUFFER, (GLsizeiptr)(max_vertices * sizeof(CohRenderVertex)), NULL, GL_STREAM_DRAW);
#define ATTRIBUTE(index, field, elements) \
    glVertexAttribPointer(index, elements, GL_FLOAT, GL_FALSE, sizeof(CohRenderVertex), (const void *)offsetof(CohRenderVertex, field)); \
    glEnableVertexAttribArray(index)
    ATTRIBUTE(0, position, 3);
    ATTRIBUTE(1, normal, 3);
    ATTRIBUTE(2, uv0, 2);
    ATTRIBUTE(3, uv1, 2);
    ATTRIBUTE(4, color, 4);
#undef ATTRIBUTE
    glBindTransformFeedback(GL_TRANSFORM_FEEDBACK, g->transform);
    glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER, g->feedback);
    glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER, (GLsizeiptr)(max_vertices * STREAM_COMPONENTS * sizeof(float)), NULL, GL_STREAM_READ);
    glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, g->feedback);
    if (!clean_gl(error, cap, "Stream transform-feedback buffers failed")) return 0;
    for (size_t i = 0; i < count; ++i) {
        const CohRenderDraw *d = draws + i;
        size_t bytes = d->geometry.vertex_count * STREAM_COMPONENTS * sizeof(float);
        uniforms(g->program, d);
        glBindVertexArray(g->vao);
        glBindBuffer(GL_ARRAY_BUFFER, g->vertex);
        glBufferSubData(GL_ARRAY_BUFFER, 0, (GLsizeiptr)(d->geometry.vertex_count * sizeof(CohRenderVertex)), d->geometry.vertices);
        glEnable(GL_RASTERIZER_DISCARD);
        glBeginTransformFeedback(GL_POINTS);
        glDrawArrays(GL_POINTS, 0, (GLsizei)d->geometry.vertex_count);
        glEndTransformFeedback();
        glDisable(GL_RASTERIZER_DISCARD);
        if (!clean_gl(error, cap, "Stream GPU transform feedback failed")) return 0;
        glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER, g->feedback);
        const float *actual = glMapBufferRange(GL_TRANSFORM_FEEDBACK_BUFFER, 0, (GLsizeiptr)bytes, GL_MAP_READ_BIT);
        if (!actual) return reject(error, cap, "Stream transform-feedback map failed");
        int source_valid = 1;
        for (size_t j = 0; j < d->geometry.vertex_count; ++j) {
            float expected[STREAM_COMPONENTS];
            if (coh_renderer_vertex(d, d->geometry.vertices + j, expected, expected + 4, expected + 7, expected + 11) != COH_OK) {
                source_valid = 0;
                break;
            }
            for (size_t k = 0; k < STREAM_COMPONENTS; ++k) {
                float difference = fabsf(actual[j * STREAM_COMPONENTS + k] - expected[k]);
                stats->tf_components++;
                if (!isfinite(difference)) { stats->tf_mismatches++; stats->max_error = FLT_MAX; }
                else {
                    if (difference > stats->max_error) stats->max_error = difference;
                    if (difference > STREAM_TOLERANCE) stats->tf_mismatches++;
                }
            }
        }
        GLboolean unmapped = glUnmapBuffer(GL_TRANSFORM_FEEDBACK_BUFFER);
        if (!source_valid) return reject(error, cap, "Stream source CPU vertex admission failed");
        if (!unmapped) return reject(error, cap, "Stream transform feedback became invalid");
        if (!clean_gl(error, cap, "Stream transform-feedback comparison failed")) return 0;
    }
    return stats->tf_mismatches ? reject(error, cap, "Stream source CPU/GPU transform mismatch") : 1;
}
static int target(StreamGpu *g, char *error, size_t cap) {
    glGenFramebuffers(1, &g->fbo);
    glGenTextures(1, &g->color);
    glGenRenderbuffers(1, &g->depth);
    if (!g->fbo || !g->color || !g->depth)
        return reject(error, cap, "Stream visibility target unavailable");
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, g->color);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA8, STREAM_TARGET_SIZE, STREAM_TARGET_SIZE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glBindRenderbuffer(GL_RENDERBUFFER, g->depth);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT24, STREAM_TARGET_SIZE, STREAM_TARGET_SIZE);
    glBindFramebuffer(GL_FRAMEBUFFER, g->fbo);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, g->color, 0);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, g->depth);
    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
        return reject(error, cap, "Stream visibility framebuffer incomplete");
    return clean_gl(error, cap, "Stream visibility target creation failed");
}
static int cancelled(void *context) { (void)context; return 1; }
static int visible(StreamGpu *g, CohRenderer *renderer, const CohRenderDraw *draws,
                   size_t count, CohStreamQualification *stats, char *error, size_t cap) {
    glBindFramebuffer(GL_FRAMEBUFFER, g->fbo);
    glViewport(0, 0, STREAM_TARGET_SIZE, STREAM_TARGET_SIZE);
    glDisable(GL_SCISSOR_TEST);
    glDisable(GL_RASTERIZER_DISCARD);
    glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    glDepthMask(GL_TRUE);
    glClearDepthf(1.f);
    glClearColor(17.f/255.f, 19.f/255.f, 23.f/255.f, 1.f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    uint8_t *pixels = malloc(STREAM_TARGET_SIZE * STREAM_TARGET_SIZE * 4u);
    if (!pixels) return reject(error, cap, "Stream visibility readback allocation failed");
    CohRendererStats before = coh_renderer_stats(renderer);
    CohStatus status = coh_renderer_begin(renderer, before.surface_generation);
    if (status == COH_OK) {
        for (size_t i = 0; i < count; ++i) {
            status = coh_renderer_submit(renderer, draws + i);
            if (status != COH_OK) break;
        }
        if (status == COH_OK) status = coh_renderer_flush(renderer, (CohCancel){0});
        else {
            /* Submit never executes GPU work. Drop the partially assembled
             * diagnostic pass without touching cached shader programs. */
            CohCancel cancel = {cancelled, NULL};
            (void)coh_renderer_flush(renderer, cancel);
        }
    }
    if (status != COH_OK) {
        free(pixels);
        if (error && cap) snprintf(error, cap, "Stream backend visibility draw failed (status %u)", (unsigned)status);
        return 0;
    }
    glBindBuffer(GL_PIXEL_PACK_BUFFER, 0);
    glPixelStorei(GL_PACK_ALIGNMENT, 4);
    glPixelStorei(GL_PACK_ROW_LENGTH, 0);
    glPixelStorei(GL_PACK_SKIP_PIXELS, 0);
    glPixelStorei(GL_PACK_SKIP_ROWS, 0);
    glReadPixels(0, 0, STREAM_TARGET_SIZE, STREAM_TARGET_SIZE, GL_RGBA, GL_UNSIGNED_BYTE, pixels);
    int ok = clean_gl(error, cap, "Stream actual geometry visibility readback failed");
    if (ok) {
        for (size_t i = 0; i < STREAM_TARGET_SIZE * STREAM_TARGET_SIZE; ++i) {
            const uint8_t *p = pixels + i * 4u;
            if (abs((int)p[0] - 17) > 2 || abs((int)p[1] - 19) > 2 || abs((int)p[2] - 23) > 2)
                stats->visible_pixels++;
        }
    }
    free(pixels);
    return ok && (stats->visible_pixels ? 1 : reject(error, cap, "Stream actual geometry produced no visible pixels"));
}
static void restore(StreamGpu *g) {
    glDisable(GL_RASTERIZER_DISCARD);
    glBindTransformFeedback(GL_TRANSFORM_FEEDBACK, (GLuint)g->transform_binding);
    glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER, (GLuint)g->feedback_binding);
    glBindBuffer(GL_PIXEL_PACK_BUFFER, (GLuint)g->pack_buffer);
    glPixelStorei(GL_PACK_ALIGNMENT, g->pack_alignment);
    glPixelStorei(GL_PACK_ROW_LENGTH, g->pack_row_length);
    glPixelStorei(GL_PACK_SKIP_PIXELS, g->pack_skip_pixels);
    glPixelStorei(GL_PACK_SKIP_ROWS, g->pack_skip_rows);
    glBindRenderbuffer(GL_RENDERBUFFER, (GLuint)g->renderbuffer);
    glBindFramebuffer(GL_DRAW_FRAMEBUFFER, (GLuint)g->draw_fbo);
    glBindFramebuffer(GL_READ_FRAMEBUFFER, (GLuint)g->read_fbo);
    glViewport(g->viewport[0], g->viewport[1], g->viewport[2], g->viewport[3]);
    for (GLuint i = 0; i < 3; ++i) glBindSampler(i, 0);
    glActiveTexture((GLenum)g->active_texture);
    glEnable(GL_DEPTH_TEST);
    glDepthMask(GL_TRUE);
    glDepthFunc(GL_LEQUAL);
    glEnable(GL_CULL_FACE);
    glFrontFace(GL_CW);
    glCullFace(GL_BACK);
    glDisable(GL_BLEND);
    if (g->scissor) glEnable(GL_SCISSOR_TEST); else glDisable(GL_SCISSOR_TEST);
    glColorMask(g->color_mask[0], g->color_mask[1], g->color_mask[2], g->color_mask[3]);
    if (g->rasterizer_discard) glEnable(GL_RASTERIZER_DISCARD);
    if (g->program) glDeleteProgram(g->program);
    glDeleteVertexArrays(1, &g->vao);
    glDeleteBuffers(1, &g->vertex);
    glDeleteBuffers(1, &g->feedback);
    glDeleteTransformFeedbacks(1, &g->transform);
    glDeleteFramebuffers(1, &g->fbo);
    glDeleteTextures(1, &g->color);
    glDeleteRenderbuffers(1, &g->depth);
}
int coh_stream_qualify(CohRenderer *renderer, const CohRenderDraw *draws,
                       size_t count, CohStreamQualification *stats,
                       char *error, size_t errorcap) {
    if (error && errorcap) error[0] = 0;
    if (stats) memset(stats, 0, sizeof *stats);
    if (!renderer || !draws || !stats || !count || count > STREAM_DRAW_LIMIT)
        return reject(error, errorcap, "Stream diagnostic arguments exceed bounds");
    size_t total = 0, maximum = 0;
    for (size_t i = 0; i < count; ++i) {
        size_t vertices = draws[i].geometry.vertex_count;
        if (!draws[i].geometry.vertices || !vertices || vertices > STREAM_VERTEX_LIMIT - total)
            return reject(error, errorcap, "Stream diagnostic vertex budget exceeded");
        total += vertices;
        if (vertices > maximum) maximum = vertices;
    }
    if (coh_renderer_stats(renderer).queued)
        return reject(error, errorcap, "Stream diagnostics require an idle renderer");
    GLboolean active = GL_FALSE;
    glGetBooleanv(GL_TRANSFORM_FEEDBACK_ACTIVE, &active);
    if (active) return reject(error, errorcap, "Stream diagnostics cannot interrupt active transform feedback");
    if (!clean_gl(error, errorcap, "Stream diagnostics entered with GL errors")) return 0;
    StreamGpu g;
    memset(&g, 0, sizeof g);
    glGetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &g.draw_fbo);
    glGetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &g.read_fbo);
    glGetIntegerv(GL_VIEWPORT, g.viewport);
    glGetIntegerv(GL_PIXEL_PACK_BUFFER_BINDING, &g.pack_buffer);
    glGetIntegerv(GL_PACK_ALIGNMENT, &g.pack_alignment);
    glGetIntegerv(GL_PACK_ROW_LENGTH, &g.pack_row_length);
    glGetIntegerv(GL_PACK_SKIP_PIXELS, &g.pack_skip_pixels);
    glGetIntegerv(GL_PACK_SKIP_ROWS, &g.pack_skip_rows);
    glGetIntegerv(GL_RENDERBUFFER_BINDING, &g.renderbuffer);
    glGetIntegerv(GL_TRANSFORM_FEEDBACK_BINDING, &g.transform_binding);
    glGetIntegerv(GL_TRANSFORM_FEEDBACK_BUFFER_BINDING, &g.feedback_binding);
    glGetIntegerv(GL_ACTIVE_TEXTURE, &g.active_texture);
    g.rasterizer_discard = glIsEnabled(GL_RASTERIZER_DISCARD);
    g.scissor = glIsEnabled(GL_SCISSOR_TEST);
    glGetBooleanv(GL_COLOR_WRITEMASK, g.color_mask);
    int ok = clean_gl(error, errorcap, "Stream diagnostic GL state capture failed") &&
        target(&g, error, errorcap) &&
        program(&g, error, errorcap) &&
        feedback(&g, draws, count, maximum, stats, error, errorcap) &&
        visible(&g, renderer, draws, count, stats, error, errorcap);
    restore(&g);
    int restored = clean_gl(error, errorcap, "Stream diagnostic GL state restoration failed");
    return ok && restored;
}
