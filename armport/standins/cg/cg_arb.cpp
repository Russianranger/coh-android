/* ArmPort Cg stand-in, program part: Cg programs as precompiled ARB assembly.
 *
 * The x86-only Cg runtime compiled the client's .cg shaders to ARB assembly
 * (arbvp1/arbfp1) at run time. On ARM64 the same assembly comes from the
 * original cgc.exe ahead of time (armport/shaders), and these functions load it
 * through GL_ARB_vertex_program / GL_ARB_fragment_program, which is what the Cg
 * runtime itself did for these profiles.
 *
 * cgCreateProgram(CG_SOURCE, ...) looks the request up by a key over
 * (profile, entry, compiler args, source text) in the directory named by
 * ARMPORT_CG_DIR (default "armport_cg" in the working directory): <key>.arb.
 * On a miss it writes the request to <dir>/requests/<key>.req so the
 * precompile step can compile exactly what the client asked for, and reports a
 * compiler error, which the client already handles (it loads its error shader).
 * CG_OBJECT programs (the client's own prebaked cache) are ARB text already.
 *
 * Only the vertex/fragment program path is implemented here. CgFX effects
 * (SSAO, post-processing filters) stay unimplemented in cg_standin.cpp.
 */
#include <windows.h>
#include <GL/gl.h>
#include <Cg/cg.h>
#include <Cg/cgGL.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <vector>

#define ARMPORT_GL_VERTEX_PROGRAM_ARB 0x8620
#define ARMPORT_GL_FRAGMENT_PROGRAM_ARB 0x8804
#define ARMPORT_GL_PROGRAM_FORMAT_ASCII_ARB 0x8875
#define ARMPORT_GL_PROGRAM_ERROR_POSITION_ARB 0x864B
#define ARMPORT_GL_PROGRAM_ERROR_STRING_ARB 0x8874

typedef void (APIENTRY *PFN_GenPrograms)(GLsizei, GLuint *);
typedef void (APIENTRY *PFN_DeletePrograms)(GLsizei, const GLuint *);
typedef void (APIENTRY *PFN_BindProgram)(GLenum, GLuint);
typedef void (APIENTRY *PFN_ProgramString)(GLenum, GLenum, GLsizei, const void *);

namespace {

struct Context { int unused; };

struct Program {
    CGprofile profile;
    std::string entry;
    std::string text;              /* ARB assembly, empty if not compiled */
    std::vector<std::string> args;
    std::vector<const char *> argv; /* NULL-terminated view of args */
    GLuint id;
};

Context g_context;
CGerror g_error = CG_NO_ERROR;
CGerrorCallbackFunc g_callback = NULL;
std::string g_listing;
PFN_GenPrograms pGenPrograms;
PFN_DeletePrograms pDeletePrograms;
PFN_BindProgram pBindProgram;
PFN_ProgramString pProgramString;

void set_error(CGerror e, const std::string &listing)
{
    g_error = e;
    g_listing = listing;
    if (e != CG_NO_ERROR && g_callback)
        g_callback();
}

bool gl_entry_points()
{
    if (!pGenPrograms) {
        pGenPrograms = (PFN_GenPrograms)(void *)wglGetProcAddress("glGenProgramsARB");
        pDeletePrograms = (PFN_DeletePrograms)(void *)wglGetProcAddress("glDeleteProgramsARB");
        pBindProgram = (PFN_BindProgram)(void *)wglGetProcAddress("glBindProgramARB");
        pProgramString = (PFN_ProgramString)(void *)wglGetProcAddress("glProgramStringARB");
    }
    return pGenPrograms && pDeletePrograms && pBindProgram && pProgramString;
}

GLenum gl_target(CGprofile p)
{
    return p == CG_PROFILE_ARBFP1 ? ARMPORT_GL_FRAGMENT_PROGRAM_ARB : ARMPORT_GL_VERTEX_PROGRAM_ARB;
}

const char *profile_name(CGprofile p)
{
    switch (p) {
    case CG_PROFILE_ARBVP1: return "arbvp1";
    case CG_PROFILE_ARBFP1: return "arbfp1";
    default: return "unsupported";
    }
}

std::string cache_dir()
{
    const char *d = getenv("ARMPORT_CG_DIR");
    return (d && *d) ? d : "armport_cg";
}

/* FNV-1a 64 over NUL-separated fields; the precompile step computes the same. */
std::string request_key(const char *profile, const char *entry,
                        const std::vector<std::string> &args, const char *source)
{
    unsigned long long h = 1469598103934665603ULL;
    auto add = [&](const char *s, size_t n) {
        for (size_t i = 0; i < n; i++) { h ^= (unsigned char)s[i]; h *= 1099511628211ULL; }
        h ^= 0; h *= 1099511628211ULL; /* field separator */
    };
    add(profile, strlen(profile));
    add(entry, strlen(entry));
    for (const std::string &a : args) add(a.data(), a.size());
    add("", 0);
    add(source, strlen(source));
    char buf[17];
    snprintf(buf, sizeof buf, "%016llx", h);
    return buf;
}

bool read_file(const std::string &path, std::string &out)
{
    FILE *f = fopen(path.c_str(), "rb");
    if (!f) return false;
    char buf[16384];
    size_t n;
    out.clear();
    while ((n = fread(buf, 1, sizeof buf, f)) > 0) out.append(buf, n);
    fclose(f);
    return true;
}

void write_request(const std::string &key, const char *profile, const char *entry,
                   const std::vector<std::string> &args, const char *source)
{
    std::string dir = cache_dir();
    CreateDirectoryA(dir.c_str(), NULL);
    std::string req = dir + "\\requests";
    CreateDirectoryA(req.c_str(), NULL);
    std::string path = req + "\\" + key + ".req";
    FILE *f = fopen(path.c_str(), "wb");
    if (!f) return;
    fprintf(f, "profile %s\nentry %s\n", profile, entry);
    for (const std::string &a : args) fprintf(f, "arg %s\n", a.c_str());
    fprintf(f, "source\n%s", source);
    fclose(f);
}

Program *as_program(CGprogram p) { return reinterpret_cast<Program *>(p); }

} // namespace

extern "C" {

CGcontext CGENTRY cgCreateContext(void)
{
    return reinterpret_cast<CGcontext>(&g_context);
}

void CGENTRY cgDestroyContext(CGcontext) {}

CGerror CGENTRY cgGetError(void)
{
    CGerror e = g_error;
    g_error = CG_NO_ERROR;
    return e;
}

const char *CGENTRY cgGetErrorString(CGerror error)
{
    switch (error) {
    case CG_NO_ERROR: return "CG_NO_ERROR";
    case CG_COMPILER_ERROR: return "ArmPort: no precompiled ARB program for this request";
    case CG_PROGRAM_LOAD_ERROR: return "ArmPort: the driver rejected the ARB program";
    case CG_INVALID_PROFILE_ERROR: return "ArmPort: only arbvp1 and arbfp1 are supported";
    case CG_INVALID_PROGRAM_HANDLE_ERROR: return "ArmPort: invalid program handle";
    default: return "ArmPort: Cg function not implemented";
    }
}

void CGENTRY cgSetErrorCallback(CGerrorCallbackFunc func) { g_callback = func; }

const char *CGENTRY cgGetLastListing(CGcontext) { return g_listing.c_str(); }

void CGENTRY cgSetLastListing(CGhandle, const char *listing) { g_listing = listing ? listing : ""; }

CGprogram CGENTRY cgCreateProgram(CGcontext, CGenum program_type, const char *program,
                                  CGprofile profile, const char *entry, const char **args)
{
    if (profile != CG_PROFILE_ARBVP1 && profile != CG_PROFILE_ARBFP1) {
        set_error(CG_INVALID_PROFILE_ERROR, "");
        return NULL;
    }
    Program *p = new Program();
    p->profile = profile;
    p->entry = entry ? entry : "main";
    p->id = 0;
    for (const char **a = args; a && *a; a++) p->args.push_back(*a);
    for (const std::string &a : p->args) p->argv.push_back(a.c_str());
    p->argv.push_back(NULL);
    const char *source = program ? program : "";
    if (program_type == CG_OBJECT) {
        p->text = source;
        set_error(CG_NO_ERROR, "");
        return reinterpret_cast<CGprogram>(p);
    }
    std::string key = request_key(profile_name(profile), p->entry.c_str(), p->args, source);
    if (read_file(cache_dir() + "\\" + key + ".arb", p->text) && !p->text.empty()) {
        set_error(CG_NO_ERROR, "");
    } else {
        write_request(key, profile_name(profile), p->entry.c_str(), p->args, source);
        set_error(CG_COMPILER_ERROR, "ArmPort: request " + key + " recorded for precompilation\n");
    }
    return reinterpret_cast<CGprogram>(p);
}

void CGENTRY cgDestroyProgram(CGprogram program)
{
    Program *p = as_program(program);
    if (!p) return;
    if (p->id && gl_entry_points()) pDeletePrograms(1, &p->id);
    delete p;
}

CGbool CGENTRY cgIsProgramCompiled(CGprogram program)
{
    Program *p = as_program(program);
    return (p && !p->text.empty()) ? CG_TRUE : CG_FALSE;
}

const char *CGENTRY cgGetProgramString(CGprogram program, CGenum pname)
{
    Program *p = as_program(program);
    if (!p) return "";
    switch (pname) {
    case CG_COMPILED_PROGRAM: return p->text.c_str();
    case CG_PROGRAM_ENTRY: return p->entry.c_str();
    case CG_PROGRAM_PROFILE: return profile_name(p->profile);
    default: return "";
    }
}

CGprofile CGENTRY cgGetProgramProfile(CGprogram program)
{
    Program *p = as_program(program);
    return p ? p->profile : CG_PROFILE_UNKNOWN;
}

const char *const *CGENTRY cgGetProgramOptions(CGprogram program)
{
    Program *p = as_program(program);
    return p ? p->argv.data() : NULL;
}

void CGGLENTRY cgGLLoadProgram(CGprogram program)
{
    Program *p = as_program(program);
    if (!p || p->text.empty()) {
        set_error(CG_INVALID_PROGRAM_HANDLE_ERROR, "");
        return;
    }
    if (!gl_entry_points()) {
        set_error(CG_PROGRAM_LOAD_ERROR, "ArmPort: GL_ARB_vertex_program entry points missing\n");
        return;
    }
    GLenum target = gl_target(p->profile);
    if (!p->id) pGenPrograms(1, &p->id);
    pBindProgram(target, p->id);
    pProgramString(target, ARMPORT_GL_PROGRAM_FORMAT_ASCII_ARB, (GLsizei)p->text.size(), p->text.data());
    GLint pos = -1;
    glGetIntegerv(ARMPORT_GL_PROGRAM_ERROR_POSITION_ARB, &pos);
    if (pos != -1) {
        const char *msg = (const char *)glGetString(ARMPORT_GL_PROGRAM_ERROR_STRING_ARB);
        pDeletePrograms(1, &p->id);
        p->id = 0;
        set_error(CG_PROGRAM_LOAD_ERROR, std::string("ARB program error: ") + (msg ? msg : "") + "\n");
        return;
    }
    set_error(CG_NO_ERROR, "");
}

CGbool CGGLENTRY cgGLIsProgramLoaded(CGprogram program)
{
    Program *p = as_program(program);
    return (p && p->id) ? CG_TRUE : CG_FALSE;
}

void CGGLENTRY cgGLBindProgram(CGprogram program)
{
    Program *p = as_program(program);
    if (!p || !p->id || !gl_entry_points()) {
        set_error(CG_INVALID_PROGRAM_HANDLE_ERROR, "");
        return;
    }
    pBindProgram(gl_target(p->profile), p->id);
}

void CGGLENTRY cgGLEnableProfile(CGprofile profile)
{
    if (profile == CG_PROFILE_ARBVP1 || profile == CG_PROFILE_ARBFP1) glEnable(gl_target(profile));
}

void CGGLENTRY cgGLDisableProfile(CGprofile profile)
{
    if (profile == CG_PROFILE_ARBVP1 || profile == CG_PROFILE_ARBFP1) glDisable(gl_target(profile));
}

CGprofile CGGLENTRY cgGLGetLatestProfile(CGGLenum profile_type)
{
    const char *ext = (const char *)glGetString(GL_EXTENSIONS);
    if (profile_type == CG_GL_VERTEX)
        return (ext && strstr(ext, "GL_ARB_vertex_program")) ? CG_PROFILE_ARBVP1 : CG_PROFILE_UNKNOWN;
    if (profile_type == CG_GL_FRAGMENT)
        return (ext && strstr(ext, "GL_ARB_fragment_program")) ? CG_PROFILE_ARBFP1 : CG_PROFILE_UNKNOWN;
    return CG_PROFILE_UNKNOWN;
}

/* Settings the Cg runtime accepted; nothing to do for precompiled programs. */
void CGGLENTRY cgGLSetOptimalOptions(CGprofile) {}
void CGGLENTRY cgGLRegisterStates(CGcontext) {}
void CGGLENTRY cgGLSetDebugMode(CGbool) {}
void CGENTRY cgSetAutoCompile(CGcontext, CGenum) {}
void CGENTRY cgSetParameterSettingMode(CGcontext, CGenum) {}
void CGENTRY cgSetCompilerIncludeCallback(CGcontext, CGIncludeCallbackFunc) {}
void CGENTRY cgSetCompilerIncludeString(CGcontext, const char *, const char *) {}
void CGENTRY cgSetCompilerIncludeFile(CGcontext, const char *, const char *) {}

} // extern "C"
