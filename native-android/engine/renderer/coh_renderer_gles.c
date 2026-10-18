#include "coh_renderer_gles.h"
#include <GLES3/gl3.h>
#include <limits.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* This adapter owns its GLES state; accepted renderer adapters use a separate
 * pass/context and restore their state explicitly. It never shadows their GL.
 */
enum {
  MODELVIEW,
  PROJECTION,
  LIGHTING,
  LIGHT,
  SPECULAR,
  DIFFUSE,
  AMBIENT,
  SHININESS,
  CONST0,
  CONST1,
  FOGPARAMS,
  FOGCOLOR,
  GLOWPARAMS,
  ALPHAREF,
  BASE,
  DUAL,
  MASK,
  UNIFORM_COUNT
};
static const char *uniform_names[UNIFORM_COUNT] = {
    "uModelView", "uProjection", "uLighting",   "uLight",    "uSpecular",
    "uDiffuse",   "uAmbient",    "uShininess",  "uConst0",   "uConst1",
    "uFogParams", "uFogColor",   "uGlowParams", "uAlphaRef", "uBase",
    "uDual",      "uMask"};
typedef struct {
  GLuint name;
  GLint loc[UNIFORM_COUNT];
} Program;
struct CohGlesRenderer {
  size_t max_vertices, max_indices, bytes;
  int precise;
  GLuint vao, vbo, ibo, samplers[3];
  Program programs[4];
  char log[1024];
};
static Program *find_program(CohGlesRenderer *g, GLuint id) {
  size_t i;
  for (i = 0; i < 4; ++i)
    if (g->programs[i].name == id)
      return g->programs + i;
  return NULL;
}
static GLuint compile_one(CohGlesRenderer *g, GLenum type, const char *s) {
  GLuint id = glCreateShader(type);
  GLint ok = 0;
  if (!id)
    return 0;
  glShaderSource(id, 1, &s, NULL);
  glCompileShader(id);
  glGetShaderiv(id, GL_COMPILE_STATUS, &ok);
  if (!ok) {
    glGetShaderInfoLog(id, sizeof g->log, NULL, g->log);
    glDeleteShader(id);
    return 0;
  }
  return id;
}
static CohStatus compile_program(void *ctx, CohMaterialFamily f, const char *v,
                                 const char *frag, uint32_t *out) {
  CohGlesRenderer *g = ctx;
  GLuint vs, fs, p;
  GLint ok = 0;
  size_t i, slot = 4;
  if (g->precise) {
    v = coh_renderer_vertex_shader_precise();
    frag = coh_renderer_fragment_shader_precise(f);
  }
  for (i = 0; i < 4; ++i) {
    if (!g->programs[i].name) {
      slot = i;
      break;
    }
  }
  if (slot == 4)
    return COH_LIMIT;
  vs = compile_one(g, GL_VERTEX_SHADER, v);
  if (!vs)
    return COH_UNSUPPORTED;
  fs = compile_one(g, GL_FRAGMENT_SHADER, frag);
  if (!fs) {
    glDeleteShader(vs);
    return COH_UNSUPPORTED;
  }
  p = glCreateProgram();
  if (!p) {
    glDeleteShader(vs);
    glDeleteShader(fs);
    return COH_LIMIT;
  }
  glAttachShader(p, vs);
  glAttachShader(p, fs);
  glLinkProgram(p);
  glDeleteShader(vs);
  glDeleteShader(fs);
  glGetProgramiv(p, GL_LINK_STATUS, &ok);
  if (!ok) {
    glGetProgramInfoLog(p, sizeof g->log, NULL, g->log);
    glDeleteProgram(p);
    return COH_UNSUPPORTED;
  }
  g->programs[slot].name = p;
  for (i = 0; i < UNIFORM_COUNT; ++i)
    g->programs[slot].loc[i] = glGetUniformLocation(p, uniform_names[i]);
  *out = p;
  return COH_OK;
}
static void delete_program(void *ctx, uint32_t id) {
  CohGlesRenderer *g = ctx;
  Program *p = find_program(g, id);
  if (p) {
    glDeleteProgram(id);
    memset(p, 0, sizeof *p);
  }
}
static GLenum wrap_value(CohWrap w) {
  return w == COH_WRAP_REPEAT
             ? GL_REPEAT
             : (w == COH_WRAP_CLAMP ? GL_CLAMP_TO_EDGE : GL_MIRRORED_REPEAT);
}
static GLenum filter_value(CohFilter f) {
  return f == COH_FILTER_NEAREST
             ? GL_NEAREST
             : (f == COH_FILTER_LINEAR ? GL_LINEAR : GL_LINEAR_MIPMAP_LINEAR);
}
static CohStatus bind_pipeline(void *ctx, uint32_t id,
                               const CohRenderMaterial *m) {
  CohGlesRenderer *g = ctx;
  size_t i;
  size_t count = m->family == COH_MAT_ADDGLOW ? 3 : 2;
  if (!find_program(g, id))
    return COH_STATE;
  for (i = 0; i < count; ++i)
    if (!m->textures[i].handle)
      return COH_NOT_FOUND;
  glUseProgram(id);
  if (m->blend == COH_BLEND_OPAQUE)
    glDisable(GL_BLEND);
  else {
    glEnable(GL_BLEND);
    glBlendEquation(GL_FUNC_ADD);
    glBlendFunc(GL_SRC_ALPHA,
                m->blend == COH_BLEND_ALPHA ? GL_ONE_MINUS_SRC_ALPHA : GL_ONE);
  }
  if (m->depth_test)
    glEnable(GL_DEPTH_TEST);
  else
    glDisable(GL_DEPTH_TEST);
  glDepthFunc(GL_LEQUAL);
  glDepthMask(m->depth_write ? GL_TRUE : GL_FALSE);
  if (m->cull_back)
    glEnable(GL_CULL_FACE);
  else
    glDisable(GL_CULL_FACE);
  glCullFace(GL_BACK);
  glFrontFace(m->front_cw ? GL_CW : GL_CCW);
  for (i = 0; i < count; ++i) {
    const CohRenderTexture *t = m->textures + i;
    glActiveTexture(GL_TEXTURE0 + (GLenum)i);
    glBindTexture(GL_TEXTURE_2D, t->handle);
    glBindSampler((GLuint)i, g->samplers[i]);
    glSamplerParameteri(g->samplers[i], GL_TEXTURE_WRAP_S,
                        (GLint)wrap_value(t->wrap_s));
    glSamplerParameteri(g->samplers[i], GL_TEXTURE_WRAP_T,
                        (GLint)wrap_value(t->wrap_t));
    glSamplerParameteri(g->samplers[i], GL_TEXTURE_MIN_FILTER,
                        (GLint)filter_value(t->min_filter));
    glSamplerParameteri(g->samplers[i], GL_TEXTURE_MAG_FILTER,
                        (GLint)filter_value(t->mag_filter));
  }
  return COH_OK;
}
static CohStatus draw_geometry(void *ctx, uint32_t id, const CohRenderDraw *d) {
  CohGlesRenderer *g = ctx;
  const CohRenderMaterial *m = &d->material;
  Program *p = find_program(g, id);
  if (!p || !g->vao)
    return COH_STATE;
  if (d->geometry.vertex_count > g->max_vertices ||
      d->geometry.index_count > g->max_indices)
    return COH_LIMIT;
#define LOC(x) p->loc[x]
  glUniformMatrix4fv(LOC(MODELVIEW), 1, GL_FALSE, d->model_view);
  glUniformMatrix4fv(LOC(PROJECTION), 1, GL_FALSE, d->projection);
  glUniform1i(LOC(LIGHTING), (GLint)m->lighting);
  glUniform3fv(LOC(LIGHT), 1, m->light);
  glUniform3fv(LOC(SPECULAR), 1, m->specular);
  glUniform4fv(LOC(DIFFUSE), 1, m->diffuse);
  glUniform4fv(LOC(AMBIENT), 1, m->ambient);
  glUniform1f(LOC(SHININESS), m->shininess);
  glUniform4fv(LOC(CONST0), 1, m->const0);
  glUniform4fv(LOC(CONST1), 1, m->const1);
  glUniform4fv(LOC(FOGPARAMS), 1, m->fog_params);
  glUniform4fv(LOC(FOGCOLOR), 1, m->fog_color);
  glUniform4fv(LOC(GLOWPARAMS), 1, m->glow_params);
  glUniform1f(LOC(ALPHAREF), m->alpha_ref);
  glUniform1i(LOC(BASE), 0);
  glUniform1i(LOC(DUAL), 1);
  glUniform1i(LOC(MASK), 2);
#undef LOC
  glBindVertexArray(g->vao);
  glBindBuffer(GL_ARRAY_BUFFER, g->vbo);
  glBufferSubData(
      GL_ARRAY_BUFFER, 0,
      (GLsizeiptr)(d->geometry.vertex_count * sizeof(CohRenderVertex)),
      d->geometry.vertices);
  glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, g->ibo);
  glBufferSubData(GL_ELEMENT_ARRAY_BUFFER, 0,
                  (GLsizeiptr)(d->geometry.index_count * sizeof(uint32_t)),
                  d->geometry.indices);
  glDrawElements(GL_TRIANGLES, (GLsizei)d->geometry.index_count,
                 GL_UNSIGNED_INT, 0);
  return COH_OK;
}
static void clear_objects(CohGlesRenderer *g, int alive) {
  size_t i;
  if (alive) {
    for (i = 0; i < 4; ++i)
      if (g->programs[i].name)
        glDeleteProgram(g->programs[i].name);
    glDeleteBuffers(1, &g->vbo);
    glDeleteBuffers(1, &g->ibo);
    glDeleteVertexArrays(1, &g->vao);
    glDeleteSamplers(3, g->samplers);
  }
  memset(g->programs, 0, sizeof g->programs);
  g->vao = g->vbo = g->ibo = 0;
  memset(g->samplers, 0, sizeof g->samplers);
}
CohStatus coh_renderer_gles_recreate(CohGlesRenderer *g, int alive) {
  if (!g)
    return COH_INVALID;
  {
    GLint major = 0, minor = 0;
    glGetIntegerv(GL_MAJOR_VERSION, &major);
    glGetIntegerv(GL_MINOR_VERSION, &minor);
    g->precise = major > 3 || (major == 3 && minor >= 2);
  }
  clear_objects(g, alive);
  glGenVertexArrays(1, &g->vao);
  glGenBuffers(1, &g->vbo);
  glGenBuffers(1, &g->ibo);
  glGenSamplers(3, g->samplers);
  glBindVertexArray(g->vao);
  glBindBuffer(GL_ARRAY_BUFFER, g->vbo);
  glBufferData(GL_ARRAY_BUFFER,
               (GLsizeiptr)(g->max_vertices * sizeof(CohRenderVertex)), NULL,
               GL_DYNAMIC_DRAW);
  glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, g->ibo);
  glBufferData(GL_ELEMENT_ARRAY_BUFFER,
               (GLsizeiptr)(g->max_indices * sizeof(uint32_t)), NULL,
               GL_DYNAMIC_DRAW);
#define ATTR(i, field, n)                                                      \
  glVertexAttribPointer(i, n, GL_FLOAT, GL_FALSE, sizeof(CohRenderVertex),     \
                        (const void *)offsetof(CohRenderVertex, field));       \
  glEnableVertexAttribArray(i)
  ATTR(0, position, 3);
  ATTR(1, normal, 3);
  ATTR(2, uv0, 2);
  ATTR(3, uv1, 2);
  ATTR(4, color, 4);
#undef ATTR
  if (glGetError() != GL_NO_ERROR || !g->vao || !g->vbo || !g->ibo ||
      !g->samplers[0] || !g->samplers[1] || !g->samplers[2]) {
    clear_objects(g, 1);
    return COH_LIMIT;
  }
  return COH_OK;
}
CohStatus coh_renderer_gles_create(size_t v, size_t i, CohGlesRenderer **out,
                                   CohRenderBackend *backend) {
  CohGlesRenderer *g;
  CohStatus s;
  if (!out || !backend || !v || !i || v > INT_MAX / sizeof(CohRenderVertex) ||
      i > INT_MAX / sizeof(uint32_t))
    return COH_INVALID;
  if (*out)
    return COH_STATE;
  g = calloc(1, sizeof *g);
  if (!g)
    return COH_LIMIT;
  g->max_vertices = v;
  g->max_indices = i;
  g->bytes = v * sizeof(CohRenderVertex) + i * sizeof(uint32_t);
  s = coh_renderer_gles_recreate(g, 0);
  if (s != COH_OK) {
    free(g);
    return s;
  }
  *backend = (CohRenderBackend){compile_program, delete_program, bind_pipeline,
                                draw_geometry, g};
  *out = g;
  return COH_OK;
}
void coh_renderer_gles_destroy(CohGlesRenderer *g, int alive) {
  if (!g)
    return;
  clear_objects(g, alive);
  free(g);
}
const char *coh_renderer_gles_shader_log(const CohGlesRenderer *g) {
  return g ? g->log : "invalid renderer";
}
size_t coh_renderer_gles_buffer_bytes(const CohGlesRenderer *g) {
  return g ? g->bytes : 0;
}
