/* Integration-only worker. Include the qualified implementation unchanged so
 * its scene, shader-selection, uniforms, layout and comparison helpers remain
 * the exact accepted code. The retained JNI entry is private to this module's
 * unused historical package; no Java caller invokes it in the combined probe. */
#define Java_org_coh_worldprobe_ProbeNative_probe coh_interactive_retained_world_probe
#include "../world-probe/app/src/main/cpp/probe_renderer.c"
#undef Java_org_coh_worldprobe_ProbeNative_probe
#include "coh_interactive_world.h"

#define INTERACTIVE_FRAMES 450u
#define INPUT_SECONDS (1.0f / 30.0f)

static int control_cancelled(const CohInteractiveWorldControl *control) {
    return control->cancelled && control->cancelled(control->opaque);
}

/* Dynamic transform evidence uses CPU source arithmetic for each current
 * input camera; frozen independent source goldens are checked before this.
 * GPU feedback never supplies reference vertices or camera inputs. */
static int interactive_transform(Cycle *cycle, CohInteractiveWorldReport *out,
    Program *program, GLuint vao, GLuint vbo, GLuint ibo, GLuint tf,
    const Report *report, const Geometry *geometry, const GLuint *textures,
    const float eye[6][12], const float projection[16]) {
    for (unsigned part = 0; part < report->scene.part_count; part++) {
        const CohWorldPart *draw = &report->scene.parts[part];
        const Geometry *g = &geometry[part];
        world_uniforms(program, draw, textures, report->world[draw->node], eye[draw->node], projection);
        vertex_layout(vao, vbo, ibo);
        const GLsizeiptr count = (GLsizeiptr)((size_t)draw->mesh.vertex_count * TF_FLOATS * sizeof(float));
        glBufferData(GL_ARRAY_BUFFER, (GLsizeiptr)((size_t)draw->mesh.vertex_count * sizeof(Vertex)), g->vertices, GL_DYNAMIC_DRAW);
        glBindBuffer(GL_TRANSFORM_FEEDBACK_BUFFER, tf);
        glBufferData(GL_TRANSFORM_FEEDBACK_BUFFER, count, NULL, GL_DYNAMIC_READ);
        glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, tf);
        glEnable(GL_RASTERIZER_DISCARD);
        glBeginTransformFeedback(GL_POINTS);
        glDrawArrays(GL_POINTS, 0, (GLsizei)draw->mesh.vertex_count);
        glEndTransformFeedback();
        glDisable(GL_RASTERIZER_DISCARD);
        if (!glcheck(cycle, "interactive-transform-feedback")) return 0;
        const float *actual = glMapBufferRange(GL_TRANSFORM_FEEDBACK_BUFFER, 0, count, GL_MAP_READ_BIT);
        if (!actual) return fail(cycle, "interactive-transform-map", "Dynamic GPU feedback cannot be read");
        for (unsigned vertex = 0; vertex < draw->mesh.vertex_count; vertex++) {
            float expected[13];
            if (coh_world_vertex(report->world[draw->node], eye[draw->node], projection,
                    g->vertices[vertex].position, g->vertices[vertex].normal, expected)) {
                glUnmapBuffer(GL_TRANSFORM_FEEDBACK_BUFFER);
                return fail(cycle, "interactive-source-vertex", "Dynamic source vertex evaluation failed");
            }
            for (unsigned component = 0; component < TF_FLOATS; component++) {
                const float got = actual[vertex * TF_FLOATS + component];
                out->interactive_transform_components++;
                if (!isfinite(got) || fabsf(got - expected[component]) > FLOAT_TOLERANCE)
                    out->interactive_transform_mismatches++;
            }
        }
        if (!glUnmapBuffer(GL_TRANSFORM_FEEDBACK_BUFFER))
            return fail(cycle, "interactive-transform-unmap", "Dynamic GPU feedback became invalid");
        glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER, 0, 0);
        if (!glcheck(cycle, "interactive-transform-readback")) return 0;
    }
    return !out->interactive_transform_mismatches || fail(cycle, "interactive-transform-parity",
        "Current input-driven camera differs between source CPU arithmetic and actual GPU feedback");
}

static int allocate_geometry(Report *report, Geometry geometry[COH_WORLD_PARTS]) {
    unsigned first = 0;
    for (unsigned part = 0; part < report->scene.part_count; part++) {
        const CohMeshView *mesh = &report->scene.parts[part].mesh;
        Geometry *g = &geometry[part];
        g->first_vertex = first; first += mesh->vertex_count;
        g->vertices = calloc(mesh->vertex_count, sizeof(Vertex));
        g->reference = calloc(mesh->vertex_count, sizeof(Vertex));
        g->indices = malloc((size_t)mesh->index_count * sizeof(uint32_t));
        if (!g->vertices || !g->reference || !g->indices) return 0;
        for (unsigned i = 0; i < mesh->vertex_count; i++) {
            CohMeshVertex vertex;
            if (coh_mesh_vertex(mesh, i, &vertex)) return 0;
            memcpy(g->vertices[i].position, vertex.position, 12);
            memcpy(g->vertices[i].normal, vertex.normal, 12);
            memcpy(g->vertices[i].uv0, vertex.uv, 8);
            memcpy(g->vertices[i].uv1, vertex.uv, 8);
        }
        for (unsigned i = 0; i < mesh->index_count; i++)
            if (coh_mesh_index(mesh, i, &g->indices[i])) return 0;
    }
    return 1;
}

int coh_interactive_world_run(ANativeWindow *window,
    const uint8_t *world_bytes, size_t world_length,
    const uint8_t *reference_bytes, size_t reference_length,
    const uint8_t *material_bytes, size_t material_length,
    const CohInteractiveWorldControl *control, CohInteractiveWorldReport *out) {
    if (!out) return 0;
    memset(out, 0, sizeof *out);
    if (!window || !control || !control->sample || !control->cancelled ||
        !world_bytes || !reference_bytes || !material_bytes ||
        world_length > MAX_ASSET || reference_length > MAX_ASSET || material_length > MAX_ASSET ||
        world_length + reference_length + material_length > 32u * 1024u * 1024u) {
        textcopy(out->failure, "Live retained Surface, callbacks and bounded immutable fixture bytes are required");
        textcopy(out->stage, "invalid-input"); out->session_failure = 1; return 0;
    }
    Report report = {0}; Cycle cycle = {0}; Geometry geometry[COH_WORLD_PARTS] = {{0}};
    EGLDisplay display = EGL_NO_DISPLAY; EGLSurface surface = EGL_NO_SURFACE;
    EGLContext context = EGL_NO_CONTEXT; EGLConfig config = NULL;
    int initialized = 0, current = 0, success = 0, released = 1;
    GLuint textures[COH_WORLD_TEXTURES] = {0}, vao = 0, vbo = 0, ibo = 0, tf = 0, qvao = 0, qvbo = 0;
    Program program = {0}, present = {0}; Target target = {0};
    uint8_t *image = NULL, *previous_image = NULL;
    struct timespec start = {0}, end = {0};
    EGLint major = 0, minor = 0, count = 0, visual = 0;
    const EGLint attributes[] = {EGL_SURFACE_TYPE,EGL_WINDOW_BIT,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES3_BIT_KHR,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_DEPTH_SIZE,0,EGL_STENCIL_SIZE,0,EGL_NONE};
    const EGLint context_attributes[] = {EGL_CONTEXT_CLIENT_VERSION,3,EGL_NONE};
    const char *present_vertex = "#version 300 es\nlayout(location=0) in vec2 aPosition;void main(){gl_Position=vec4(aPosition,0,1);}\n";
    const char *present_fragment = "#version 300 es\nprecision highp float;precision highp int;uniform highp sampler2D uImage;uniform ivec4 uViewport;layout(location=0)out vec4 color;void main(){ivec2 p=ivec2(gl_FragCoord.xy)-uViewport.xy;ivec2 t=((2*p+ivec2(1))*ivec2(512))/(2*uViewport.zw);t=clamp(t,ivec2(0),ivec2(511));color=vec4(texelFetch(uImage,t,0).rgb,1.0);}\n";
#define REQUIRE_GL(expression) do { if (!(expression)) goto cleanup; } while (0)
#define REQUIRE_EGL(expression, stage) do { if (!(expression)) { egfail(&cycle, stage); goto cleanup; } } while (0)
#define CHECK_CANCEL() do { if (control_cancelled(control)) { out->cancelled = 1; out->obsolete = 1; out->expected_cancel = 1; goto cleanup; } } while (0)
    if (coh_world_scene_parse(world_bytes, world_length, &report.scene) ||
        !world_reference_parse((Bytes){(uint8_t *)reference_bytes,reference_length}, &report.scene, &report.reference) ||
        !material_parse((Bytes){(uint8_t *)material_bytes,material_length}, &report.scene, &report.materials) ||
        coh_world_group_matrices(&report.scene.inputs, report.local, report.world)) {
        fail(&cycle, "fixture-validation", "Accepted authentic world/source-reference/material fixtures failed validation"); goto cleanup;
    }
    out->fixtures_valid = 1;
    REQUIRE_GL(math_check(&cycle, &report)); out->baseline_cpu_passed = 1;
    if (!allocate_geometry(&report, geometry)) { fail(&cycle,"geometry-allocation","Bounded authentic geometry allocation failed"); goto cleanup; }
    image = malloc(WORLD_SIZE * WORLD_SIZE * 4); previous_image = malloc(WORLD_SIZE * WORLD_SIZE * 4);
    if (!image || !previous_image) { fail(&cycle,"image-allocation","Bounded interactive image allocation failed"); goto cleanup; }
    CHECK_CANCEL();
    display = eglGetDisplay(EGL_DEFAULT_DISPLAY);
    if (display == EGL_NO_DISPLAY) { egfail(&cycle,"egl-display"); goto cleanup; }
    REQUIRE_EGL(eglInitialize(display,&major,&minor),"egl-initialize"); initialized = 1;
    REQUIRE_EGL(eglBindAPI(EGL_OPENGL_ES_API),"egl-bind-api");
    REQUIRE_EGL(eglChooseConfig(display,attributes,&config,1,&count),"egl-config");
    if (!count) { fail(&cycle,"egl-config","No RGBA8 GLES3 configuration"); goto cleanup; }
    REQUIRE_EGL(eglGetConfigAttrib(display,config,EGL_NATIVE_VISUAL_ID,&visual),"egl-native-format");
    if (ANativeWindow_setBuffersGeometry(window,0,0,visual)) { fail(&cycle,"window-format","Surface buffer format failed"); goto cleanup; }
    surface = eglCreateWindowSurface(display,config,window,NULL);
    if (surface == EGL_NO_SURFACE) { egfail(&cycle,"egl-window-surface"); goto cleanup; }
    context = eglCreateContext(display,config,EGL_NO_CONTEXT,context_attributes);
    if (context == EGL_NO_CONTEXT) { egfail(&cycle,"egl-context"); goto cleanup; }
    out->context_created = 1;
    REQUIRE_EGL(eglMakeCurrent(display,surface,surface,context),"egl-current"); current = 1;
    textcopy(cycle.gl_vendor,(const char *)glGetString(GL_VENDOR));
    textcopy(cycle.gl_renderer,(const char *)glGetString(GL_RENDERER));
    GLint max_texture = 0; glGetIntegerv(GL_MAX_TEXTURE_SIZE,&max_texture);
    REQUIRE_GL(glcheck(&cycle,"gl-capabilities"));
    if (max_texture < WORLD_SIZE) { fail(&cycle,"texture-limit","Interactive target exceeds GL capability"); goto cleanup; }
    for (unsigned i = 0; i < report.scene.texture_count; i++)
        if (report.scene.textures[i].width > (unsigned)max_texture || report.scene.textures[i].height > (unsigned)max_texture) {
            fail(&cycle,"texture-limit","Authentic texture exceeds GL capability"); goto cleanup;
        }
    glDisable(GL_DITHER); glDisable(GL_BLEND); glDisable(GL_SCISSOR_TEST); glDisable(GL_CULL_FACE);
    glDisable(GL_STENCIL_TEST); glDisable(GL_SAMPLE_COVERAGE); glDisable(GL_SAMPLE_ALPHA_TO_COVERAGE);
    glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE); glPixelStorei(GL_PACK_ALIGNMENT,1); glPixelStorei(GL_UNPACK_ALIGNMENT,1);
    WorldShader selected; REQUIRE_GL(world_shader_select(&cycle,&selected));
    REQUIRE_GL(program_create(&cycle,&program,selected.vertex,selected.fragment,1));
    REQUIRE_GL(program_create(&cycle,&present,present_vertex,present_fragment,0));
    if (program.model < 0 || program.modelview < 0 || program.projection < 0 || program.base < 0 || program.dual < 0 || program.mode < 0) {
        fail(&cycle,"uniform-contract","Required accepted shader uniform missing"); goto cleanup;
    }
    for (unsigned i = 0; i < report.scene.texture_count; i++) {
        const CohWorldTexture *texture = &report.scene.textures[i];
        REQUIRE_GL(texture_create(&cycle,&textures[i],texture->width,texture->height,texture->rgba));
    }
    REQUIRE_GL(target_create(&cycle,&target,WORLD_SIZE,1));
    REQUIRE_GL(scene_texture_filter(&cycle,textures,report.scene.texture_count,GL_LINEAR));
    glGenVertexArrays(1,&vao); glGenBuffers(1,&vbo); glGenBuffers(1,&ibo); glGenBuffers(1,&tf);
    glGenVertexArrays(1,&qvao); glGenBuffers(1,&qvbo); REQUIRE_GL(glcheck(&cycle,"geometry-create"));
    for (unsigned camera = 0; camera < COH_WORLD_CAMERAS; camera++) {
        CHECK_CANCEL();
        float view[12], projection[16], eye[6][12];
        if (coh_world_camera(&report.scene.inputs,camera,0,view,projection) || coh_world_group_eye_matrices(&report.scene.inputs,view,eye)) {
            fail(&cycle,"baseline-source-camera","Accepted source camera evaluation failed"); goto cleanup;
        }
        for (unsigned part = 0; part < report.scene.part_count; part++)
            REQUIRE_GL(transform_check(&cycle,&program,vao,vbo,ibo,tf,&report,&geometry[part],textures,part,camera,eye[report.scene.parts[part].node],projection));
    }
    out->baseline_gpu_passed = 1;
    if (clock_gettime(CLOCK_MONOTONIC,&start)) { fail(&cycle,"interactive-clock","Monotonic clock unavailable"); goto cleanup; }
    CohInteractiveCamera adapter = {0};
    CohInputFrame input = {0};
    uint32_t last_source_frame = 0;
    uint64_t revision = 0, previous_revision = 0;
    float prior_camera[3] = {0}, previous_image_camera[3] = {0};
    int previous_image_valid = 0, image_has_input_link = 0;
    unsigned quiet_run = 0;
    for (unsigned tick = 0; tick < INTERACTIVE_FRAMES; tick++) {
        CHECK_CANCEL();
        const int sample = control->sample(control->opaque,INPUT_SECONDS,&input,&revision);
        if (!sample) { out->cancelled = 1; out->obsolete = 1; out->expected_cancel = 1; goto cleanup; }
        if (sample < 0 || !input.frames || (tick && input.frames <= last_source_frame) || (tick && revision < previous_revision)) {
            fail(&cycle,"interactive-input-frame","Input frame/revision must advance without duplicate consumption or regression"); goto cleanup;
        }
        last_source_frame = input.frames; out->source_frames_consumed++;
        if (!tick) { out->first_revision = revision; previous_revision = revision; }
        if (revision != previous_revision) out->external_revision_changes++;
        out->last_revision = revision;
        const int external_input = revision != out->first_revision;
        previous_revision = revision;
        CohWorldInputs live; float pitch_change = 0, yaw_change = 0;
        if (!coh_interactive_camera_apply(&adapter,&input,&report.scene.inputs,&live,&pitch_change,&yaw_change)) {
            fail(&cycle,"interactive-camera-adapter","Native editor-look to source camera adapter failed"); goto cleanup;
        }
        const float *camera = live.cameras[0].pyr_degrees;
        if (!tick) { memcpy(out->first_camera_degrees,camera,12); memcpy(prior_camera,camera,12); }
        memcpy(out->last_camera_degrees,camera,12);
        const int changed = memcmp(prior_camera,camera,12) != 0;
        unsigned motion_direction = 0;
        if (external_input && changed) {
            out->input_motion_frames++; image_has_input_link = 1;
            if (yaw_change > 0) motion_direction |= 1u;
            if (yaw_change < 0) motion_direction |= 2u;
            if (pitch_change > 0) motion_direction |= 4u;
            if (pitch_change < 0) motion_direction |= 8u;
            out->cpu_direction_mask |= motion_direction;
        }
        const int quiet = !input.delta_x && !input.delta_y && fabsf(input.axes[2]) <= .15f && fabsf(input.axes[3]) <= .15f;
        if (quiet) {
            quiet_run++;
            if (tick && changed) out->stationary_mismatches++;
            if (quiet_run >= 2 && out->input_motion_frames) out->settled_frames++;
        } else quiet_run = 0;
        memcpy(prior_camera,camera,12);
        float view[12], projection[16], eye[6][12], repeat_view[12], repeat_projection[16];
        if (coh_world_camera(&live,0,0,view,projection) || coh_world_group_eye_matrices(&live,view,eye) ||
            coh_world_camera(&live,0,0,repeat_view,repeat_projection)) {
            fail(&cycle,"interactive-source-camera","Current input-driven source camera evaluation failed"); goto cleanup;
        }
        out->camera_determinism_checks++;
        if (memcmp(view,repeat_view,sizeof view) || memcmp(projection,repeat_projection,sizeof projection))
            out->camera_determinism_mismatches++;
        const unsigned new_gpu_direction = motion_direction & ~out->gpu_direction_mask;
        if (!tick || tick % 30u == 0 || new_gpu_direction) {
            REQUIRE_GL(interactive_transform(&cycle,out,&program,vao,vbo,ibo,tf,&report,geometry,textures,eye,projection));
            out->gpu_direction_mask |= motion_direction;
        }
        const unsigned new_image_direction = motion_direction & ~out->image_direction_mask;
        const int capture = !tick || new_image_direction || (tick % 3u == 0 && (changed || image_has_input_link)) || (quiet && quiet_run == 2);
        REQUIRE_GL(world_draw(&cycle,&target,&program,vao,vbo,ibo,&report,geometry,textures,eye,projection,0,-1,capture ? image : NULL));
        if (capture) {
            out->image_samples++;
            if (previous_image_valid) {
                uint64_t pixels = 0;
                for (unsigned pixel = 0; pixel < WORLD_SIZE * WORLD_SIZE; pixel++)
                    if (pixel_error(image + pixel * 4,previous_image + pixel * 4,4) > BYTE_TOLERANCE) pixels++;
                const int camera_changed = memcmp(camera,previous_image_camera,12) != 0;
                if (!camera_changed && pixels) out->same_camera_image_mismatches++;
                if (camera_changed && pixels && image_has_input_link) {
                    out->changed_image_samples++; out->input_linked_changed_pixels += pixels;
                    out->image_direction_mask |= motion_direction;
                }
            }
            memcpy(previous_image,image,WORLD_SIZE * WORLD_SIZE * 4);
            memcpy(previous_image_camera,camera,12); previous_image_valid = 1; image_has_input_link = 0;
        }
        CHECK_CANCEL();
        REQUIRE_GL(display_window(&cycle,display,surface,&target,present.id,qvao,qvbo,NULL,0));
        out->frames++;
        /* Each fixed-rate input step is consumed once. Slow rendering carries
         * no elapsed-time input backlog; a run is capped at450 frames/25s. */
        if (clock_gettime(CLOCK_MONOTONIC,&end)) { fail(&cycle,"interactive-clock","Monotonic clock failed"); goto cleanup; }
        if (monotonic_ms(&end) - monotonic_ms(&start) > 25000u) {
            fail(&cycle,"interactive-deadline","450-frame diagnostic exceeded25-second bound"); goto cleanup;
        }
        const uint64_t ns = (uint64_t)start.tv_nsec + (uint64_t)(tick + 1) * (1000000000u / 30u);
        struct timespec deadline = {start.tv_sec + (time_t)(ns / 1000000000u),(long)(ns % 1000000000u)};
        int status; do { status = clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&deadline,NULL); } while (status == EINTR);
        if (status) { fail(&cycle,"interactive-pacing","Bounded native render pacing failed"); goto cleanup; }
    }
    success = !out->stationary_mismatches && !out->camera_determinism_mismatches &&
        !out->same_camera_image_mismatches && !out->interactive_transform_mismatches;
    if (!success) fail(&cycle,"interactive-determinism","Camera or image changed without corresponding current input");
    else textcopy(cycle.stage,"complete");
cleanup:
    /* A Surface may disappear immediately after a cancellation check. Only
     * those specific window-Surface errors may become obsolete cancellation.
     * Numeric parity, bad input, GL and deadline errors remain sticky even if
     * Home arrives later. Preserve every observed backend code in the report. */
    if (!success && !out->cancelled) {
        const int expected_surface_error =
            (cycle.egl_error == EGL_BAD_SURFACE || cycle.egl_error == EGL_BAD_NATIVE_WINDOW) &&
            (!strcmp(cycle.stage,"egl-window-surface") || !strcmp(cycle.stage,"surface-query") || !strcmp(cycle.stage,"swap-buffers"));
        if (expected_surface_error && control_cancelled(control)) { out->cancelled = 1; out->obsolete = 1; out->expected_cancel = 1; }
        else out->session_failure = 1;
    }
    if (current) {
        glDisable(GL_RASTERIZER_DISCARD); glBindBufferBase(GL_TRANSFORM_FEEDBACK_BUFFER,0,0);
        target_delete(&target);
        for (unsigned i = 0; i < report.scene.texture_count; i++) if (textures[i]) glDeleteTextures(1,&textures[i]);
        if (vao) glDeleteVertexArrays(1,&vao); if (qvao) glDeleteVertexArrays(1,&qvao);
        if (vbo) glDeleteBuffers(1,&vbo); if (ibo) glDeleteBuffers(1,&ibo);
        if (tf) glDeleteBuffers(1,&tf); if (qvbo) glDeleteBuffers(1,&qvbo);
        if (program.id) glDeleteProgram(program.id); if (present.id) glDeleteProgram(present.id);
        if (!glcheck(&cycle,"interactive-gpu-cleanup")) { success = 0; out->session_failure = 1; }
    }
    if (current && !eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT)) { egfail(&cycle,"egl-release-current"); released = 0; }
    if (surface != EGL_NO_SURFACE && !eglDestroySurface(display,surface)) { egfail(&cycle,"egl-destroy-surface"); released = 0; }
    if (context != EGL_NO_CONTEXT && !eglDestroyContext(display,context)) { egfail(&cycle,"egl-destroy-context"); released = 0; }
    if (initialized && !eglTerminate(display)) { egfail(&cycle,"egl-terminate"); released = 0; }
    if (!eglReleaseThread()) { egfail(&cycle,"egl-release-thread"); released = 0; }
    if (!released) out->session_failure = 1;
    /* Deferred comparison counters are already observed failures. A later
     * clean Home cancellation cannot erase a mismatch accumulated in an
     * earlier frame before the normal450-frame completion predicate runs. */
    if (out->stationary_mismatches || out->camera_determinism_mismatches ||
        out->same_camera_image_mismatches || out->interactive_transform_mismatches ||
        cycle.transform_mismatches || cycle.group_local_mismatches || cycle.group_world_mismatches ||
        cycle.camera_view_mismatches || cycle.projection_mismatches || cycle.modelview_mismatches)
        out->session_failure = 1;
    if (out->session_failure || cycle.gl_errors) out->expected_cancel = 0;
    for (unsigned i = 0; i < COH_WORLD_PARTS; i++) { free(geometry[i].vertices); free(geometry[i].reference); free(geometry[i].indices); }
    free(image); free(previous_image);
    out->objects_released = released;
    out->swapped = cycle.swap_passed; out->width = cycle.width; out->height = cycle.height;
    out->gl_errors = cycle.gl_errors; out->egl_error = cycle.egl_error;
    out->shader_language_version = cycle.shader_language_version; out->shader_precise_enabled = (unsigned)cycle.shader_precise_enabled;
    out->baseline_transform_components = cycle.transform_components; out->baseline_transform_mismatches = cycle.transform_mismatches;
    out->baseline_cpu_components = cycle.group_local_components + cycle.group_world_components + cycle.camera_view_components + cycle.projection_components + cycle.modelview_components;
    out->baseline_cpu_mismatches = cycle.group_local_mismatches + cycle.group_world_mismatches + cycle.camera_view_mismatches + cycle.projection_mismatches + cycle.modelview_mismatches;
    out->direction_mask = out->cpu_direction_mask & out->gpu_direction_mask & out->image_direction_mask;
    textcopy(out->stage,cycle.stage); textcopy(out->failure,cycle.failure);
    textcopy(out->gl_vendor,cycle.gl_vendor); textcopy(out->gl_renderer,cycle.gl_renderer);
    textcopy(out->shader_precision_mechanism,cycle.shader_precision_mechanism);
    if (start.tv_sec && !clock_gettime(CLOCK_MONOTONIC,&end)) out->duration_ms = monotonic_ms(&end) - monotonic_ms(&start);
    out->engine_passed = success && released && !out->session_failure && out->frames == INTERACTIVE_FRAMES && !out->gl_errors && !out->egl_error;
    out->interaction_passed = out->engine_passed && out->direction_mask == 15u && out->external_revision_changes &&
        out->input_motion_frames && out->settled_frames >= 2u && out->changed_image_samples && out->input_linked_changed_pixels >= 64u;
    out->passed = out->engine_passed && out->interaction_passed;
    return out->passed;
#undef REQUIRE_GL
#undef REQUIRE_EGL
#undef CHECK_CANCEL
}

char *coh_interactive_world_json(const CohInteractiveWorldReport *report) {
    if (!report) return NULL;
    char *buffer = malloc(JSON_CAP); if (!buffer) return NULL;
    Json json = {buffer,0,1};
    append(&json,"{\"schema\":1,\"probe\":\"coh-native-input-authentic-world\",\"passed\":%s,\"engine_passed\":%s,\"interaction_passed\":%s,\"cancelled\":%s,\"obsolete\":%s,\"expected_cancel\":%s,\"session_failure\":%s",
        boolstr(report->passed),boolstr(report->engine_passed),boolstr(report->interaction_passed),boolstr(report->cancelled),boolstr(report->obsolete),boolstr(report->expected_cancel),boolstr(report->session_failure));
#define B(name) append(&json,",\""#name"\":%s",boolstr(report->name))
#define U(name) append(&json,",\""#name"\":%u",report->name)
#define N(name) append(&json,",\""#name"\":%"PRIu64,report->name)
    B(fixtures_valid); B(baseline_cpu_passed); B(baseline_gpu_passed); B(context_created); B(objects_released); B(swapped);
    append(&json,",\"width\":%d,\"height\":%d,\"surface_width\":%d,\"surface_height\":%d",report->width,report->height,report->width,report->height);
    U(frames); U(source_frames_consumed); U(direction_mask); U(settled_frames); U(external_revision_changes);
    U(cpu_direction_mask); U(gpu_direction_mask); U(image_direction_mask);
    U(input_motion_frames); U(stationary_mismatches); U(camera_determinism_checks); U(camera_determinism_mismatches);
    U(image_samples); U(changed_image_samples); U(same_camera_image_mismatches); U(gl_errors); U(egl_error);
    U(shader_language_version); U(shader_precise_enabled);
    N(baseline_transform_components); N(baseline_transform_mismatches); N(interactive_transform_components); N(interactive_transform_mismatches);
    N(baseline_cpu_components); N(baseline_cpu_mismatches); N(input_linked_changed_pixels); N(duration_ms); N(first_revision); N(last_revision);
#undef B
#undef U
#undef N
    append(&json,",\"first_camera_degrees\":[%.9g,%.9g,%.9g],\"last_camera_degrees\":[%.9g,%.9g,%.9g]",
        report->first_camera_degrees[0],report->first_camera_degrees[1],report->first_camera_degrees[2],report->last_camera_degrees[0],report->last_camera_degrees[1],report->last_camera_degrees[2]);
    append(&json,",\"stage\":"); string(&json,report->stage); append(&json,",\"failure\":"); string(&json,report->failure);
    append(&json,",\"gl_vendor\":"); string(&json,report->gl_vendor); append(&json,",\"gl_renderer\":"); string(&json,report->gl_renderer);
    append(&json,",\"shader_precision_mechanism\":"); string(&json,report->shader_precision_mechanism);
    append(&json,",\"scope\":\"Authentic accepted Atlas bench geometry/materials under current native editor-look input and source camera arithmetic; bounded +/-12-degree view adapter\",\"original_lighting_qualified\":false,\"full_atlas_loading_qualified\":false,\"character_movement_qualified\":false,\"collision_qualified\":false,\"gameplay_qualified\":false,\"performance_qualified\":false}");
    if (!json.ok) { free(buffer); return NULL; } return buffer;
}
