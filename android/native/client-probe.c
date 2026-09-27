/* Narrow PE32 client prerequisite probe. No game assets, Cg, audio playback,
 * Android surface or physical input is exercised here.
 * CoH's Game/CMakeLists.txt links OpenGL, DirectInput and DirectSound;
 * rt_cgfx.c and rt_pbuffer.c require further shader/pbuffer qualification.
 */
#include <stdio.h>
#include <string.h>
#include <ctype.h>

static const unsigned char expected_rgb[4][3] = {
    {255, 0, 0}, {0, 255, 0}, {0, 0, 255}, {255, 255, 255}
};

static int samples_match(const unsigned char actual[4][3]) {
    unsigned int i, j;
    for (i = 0; i < 4; ++i) for (j = 0; j < 3; ++j) {
        int difference = (int)actual[i][j] - (int)expected_rgb[i][j];
        if (difference < -3 || difference > 3) return 0;
    }
    return 1;
}

static int contains_folded(const char *text, const char *needle) {
    size_t i, j;
    if (!text) return 0;
    for (i = 0; text[i]; ++i) {
        for (j = 0; needle[j] && text[i+j] &&
             tolower((unsigned char)text[i+j]) == tolower((unsigned char)needle[j]); ++j) {}
        if (!needle[j]) return 1;
    }
    return 0;
}

static int software_renderer(const char *renderer) {
    return contains_folded(renderer, "llvmpipe") || contains_folded(renderer, "softpipe") ||
           contains_folded(renderer, "swrast") || contains_folded(renderer, "software") ||
           contains_folded(renderer, "gdi generic") || contains_folded(renderer, "swiftshader") ||
           contains_folded(renderer, "lavapipe");
}

static int extension_present(const char *list, const char *name) {
    size_t size = strlen(name);
    const char *found = list;
    if (!list || !size || strchr(name, ' ')) return 0;
    while ((found = strstr(found, name)) != NULL) {
        if ((found == list || found[-1] == ' ') &&
            (found[size] == 0 || found[size] == ' ')) return 1;
        found += size;
    }
    return 0;
}

/* Emit bounded ASCII JSON even for arbitrary driver-provided strings. */
static void json_string(const char *text) {
    size_t i;
    putchar('"');
    for (i = 0; text && text[i] && i < 512; ++i) {
        unsigned char c = (unsigned char)text[i];
        if (c == '"' || c == '\\') { putchar('\\'); putchar(c); }
        else if (c < 32 || c >= 127) printf("\\u%04x", (unsigned int)c);
        else putchar(c);
    }
    putchar('"');
}

#ifndef COH_CLIENT_PROBE_TEST
#define COBJMACROS
#define DIRECTINPUT_VERSION 0x0800
#include <windows.h>
#include <windowsx.h>
#include <dinput.h>
#include <dsound.h>
#include <GL/gl.h>

static unsigned int keyboard_messages, mouse_messages;
static unsigned int audio_devices;
static int audio_default;
static HRESULT audio_enumeration = E_NOTIMPL;

static LRESULT CALLBACK window_proc(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    if (message == WM_KEYDOWN && wparam == VK_F6 && lparam == 1) keyboard_messages |= 1;
    if (message == WM_KEYUP && wparam == VK_F6 && lparam == (LPARAM)0xc0000001U) keyboard_messages |= 2;
    if (message == WM_MOUSEMOVE && GET_X_LPARAM(lparam) == 19 && GET_Y_LPARAM(lparam) == 23) mouse_messages |= 1;
    if (message == WM_LBUTTONDOWN && wparam == MK_LBUTTON && GET_X_LPARAM(lparam) == 19 && GET_Y_LPARAM(lparam) == 23) mouse_messages |= 2;
    if (message == WM_LBUTTONUP && wparam == 0 && GET_X_LPARAM(lparam) == 19 && GET_Y_LPARAM(lparam) == 23) mouse_messages |= 4;
    return DefWindowProcA(window, message, wparam, lparam);
}

static int input_messages(HWND window) {
    MSG message;
    unsigned int count = 0;
    keyboard_messages = mouse_messages = 0;
    if (!PostMessageA(window, WM_KEYDOWN, VK_F6, 1) ||
        !PostMessageA(window, WM_KEYUP, VK_F6, (LPARAM)0xc0000001U) ||
        !PostMessageA(window, WM_MOUSEMOVE, 0, MAKELPARAM(19, 23)) ||
        !PostMessageA(window, WM_LBUTTONDOWN, MK_LBUTTON, MAKELPARAM(19, 23)) ||
        !PostMessageA(window, WM_LBUTTONUP, 0, MAKELPARAM(19, 23))) return 0;
    while (PeekMessageA(&message, window, 0, 0, PM_REMOVE)) {
        if (++count > 256) return 0;
        DispatchMessageA(&message);
    }
    return keyboard_messages == 3 && mouse_messages == 7;
}

static BOOL CALLBACK audio_callback(LPGUID guid, LPCSTR description, LPCSTR module, LPVOID context) {
    (void)description; (void)module; (void)context;
    if (guid) ++audio_devices; else audio_default = 1;
    return TRUE;
}

static void audio_observation(void) {
    typedef HRESULT (WINAPI *enumerate_fn)(LPDSENUMCALLBACKA, LPVOID);
    HMODULE library = LoadLibraryA("dsound.dll");
    FARPROC address;
    enumerate_fn enumerate;
    if (!library) return;
    address = GetProcAddress(library, "DirectSoundEnumerateA");
    if (address && sizeof(address) == sizeof(enumerate)) {
        memcpy(&enumerate, &address, sizeof(enumerate));
        audio_enumeration = enumerate(audio_callback, NULL);
    }
    FreeLibrary(library);
}

static int render_samples(unsigned char actual[4][3]) {
    GLuint texture = 0;
    unsigned int i;
    static const GLint coordinates[4][2] = {{16, 16}, {48, 16}, {16, 48}, {48, 48}};
    glViewport(0, 0, 64, 64);
    glDisable(GL_DITHER);
    glDisable(GL_BLEND);
    glDisable(GL_DEPTH_TEST);
    glDisable(GL_ALPHA_TEST);
    glDisable(GL_SCISSOR_TEST);
    glDisable(GL_STENCIL_TEST);
    glDrawBuffer(GL_BACK);
    glReadBuffer(GL_BACK);
    glClearColor(0, 0, 0, 1);
    glClear(GL_COLOR_BUFFER_BIT);
    glMatrixMode(GL_PROJECTION);
    glLoadIdentity();
    glMatrixMode(GL_MODELVIEW);
    glLoadIdentity();
    glPixelStorei(GL_UNPACK_ALIGNMENT, 1);
    glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glGenTextures(1, &texture);
    if (!texture) return 0;
    glBindTexture(GL_TEXTURE_2D, texture);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, 2, 2, 0, GL_RGB, GL_UNSIGNED_BYTE, expected_rgb);
    glTexEnvi(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE);
    glEnable(GL_TEXTURE_2D);
    glBegin(GL_QUADS);
    glTexCoord2f(0, 0); glVertex2f(-1, -1);
    glTexCoord2f(1, 0); glVertex2f(1, -1);
    glTexCoord2f(1, 1); glVertex2f(1, 1);
    glTexCoord2f(0, 1); glVertex2f(-1, 1);
    glEnd();
    glFinish();
    for (i = 0; i < 4; ++i)
        glReadPixels(coordinates[i][0], coordinates[i][1], 1, 1, GL_RGB, GL_UNSIGNED_BYTE, actual[i]);
    glDisable(GL_TEXTURE_2D);
    glDeleteTextures(1, &texture);
    return glGetError() == GL_NO_ERROR && samples_match(actual);
}

int main(int argc, char **argv) {
    HINSTANCE instance = GetModuleHandleA(NULL);
    WNDCLASSA klass;
    PIXELFORMATDESCRIPTOR requested, chosen;
    HWND window = NULL;
    HDC dc = NULL;
    HGLRC context = NULL;
    LPDIRECTINPUT8A direct_input = NULL;
    LPDIRECTINPUTDEVICE8A keyboard = NULL, mouse = NULL;
    const char *failure = "pointer_bits", *vendor = "", *renderer = "", *version = "", *extensions = "";
    char saved_vendor[513] = "", saved_renderer[513] = "", saved_version[513] = "";
    unsigned char samples[4][3] = {{0}};
    int format = 0, rendered = 0, swapped = 0, messages = 0, input_ready = 0, passed = 0;
    int arb_vertex = 0, arb_fragment = 0, shader_objects = 0, framebuffer = 0;
    int wgl_pbuffer = 0, wgl_pixel_format = 0;
    DWORD error = 0;
    HRESULT input_error = E_NOTIMPL;
    unsigned int i;
    (void)argv;
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
    setvbuf(stdout, NULL, _IONBF, 0);
    if (argc != 1) { failure = "arguments"; goto done; }
    if (sizeof(void *) != 4) goto done;
    memset(&klass, 0, sizeof(klass));
    klass.style = CS_OWNDC;
    klass.lpfnWndProc = window_proc;
    klass.hInstance = instance;
    klass.lpszClassName = "COHClientProbeV1";
    failure = "window_class";
    if (!RegisterClassA(&klass)) goto done;
    failure = "window_create";
    window = CreateWindowA(klass.lpszClassName, "COH client prerequisite probe", WS_OVERLAPPEDWINDOW,
                           0, 0, 128, 128, NULL, NULL, instance, NULL);
    if (!window) goto done;
    /* Visible only on the private diagnostic X server; no user desktop injection. */
    ShowWindow(window, SW_SHOW);
    UpdateWindow(window);
    failure = "window_dc";
    dc = GetDC(window);
    if (!dc) goto done;
    memset(&requested, 0, sizeof(requested));
    requested.nSize = sizeof(requested);
    requested.nVersion = 1;
    requested.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
    requested.iPixelType = PFD_TYPE_RGBA;
    requested.cColorBits = 24;
    requested.cDepthBits = 16;
    requested.iLayerType = PFD_MAIN_PLANE;
    failure = "pixel_format";
    format = ChoosePixelFormat(dc, &requested);
    if (!format || !DescribePixelFormat(dc, format, sizeof(chosen), &chosen) ||
        (chosen.dwFlags & requested.dwFlags) != requested.dwFlags ||
        chosen.iPixelType != PFD_TYPE_RGBA || chosen.cColorBits < 24 ||
        !SetPixelFormat(dc, format, &requested)) goto done;
    failure = "wgl_context";
    context = wglCreateContext(dc);
    if (!context || !wglMakeCurrent(dc, context)) goto done;
    failure = "gl_identity";
    vendor = (const char *)glGetString(GL_VENDOR);
    renderer = (const char *)glGetString(GL_RENDERER);
    version = (const char *)glGetString(GL_VERSION);
    extensions = (const char *)glGetString(GL_EXTENSIONS);
    if (!vendor || !*vendor || !renderer || !*renderer || !version || !*version || !extensions) goto done;
    snprintf(saved_vendor, sizeof(saved_vendor), "%s", vendor);
    snprintf(saved_renderer, sizeof(saved_renderer), "%s", renderer);
    snprintf(saved_version, sizeof(saved_version), "%s", version);
    arb_vertex = extension_present(extensions, "GL_ARB_vertex_program");
    arb_fragment = extension_present(extensions, "GL_ARB_fragment_program");
    shader_objects = extension_present(extensions, "GL_ARB_shader_objects");
    framebuffer = extension_present(extensions, "GL_EXT_framebuffer_object") ||
                  extension_present(extensions, "GL_ARB_framebuffer_object");
    /* These only report entry-point availability, not successful pbuffer use. */
    wgl_pbuffer = wglGetProcAddress("wglCreatePbufferARB") != NULL;
    wgl_pixel_format = wglGetProcAddress("wglChoosePixelFormatARB") != NULL;
    failure = "textured_render_readback";
    rendered = render_samples(samples);
    if (!rendered) goto done;
    failure = "swap_buffers";
    swapped = SwapBuffers(dc) != 0;
    if (!swapped) goto done;
    failure = "window_input_messages";
    messages = input_messages(window);
    if (!messages) goto done;
    failure = "directinput_create";
    input_error = DirectInput8Create(instance, DIRECTINPUT_VERSION, &IID_IDirectInput8A, (void **)&direct_input, NULL);
    if (FAILED(input_error) || !direct_input) goto done;
    failure = "directinput_keyboard";
    input_error = IDirectInput8_CreateDevice(direct_input, &GUID_SysKeyboard, &keyboard, NULL);
    if (FAILED(input_error) || !keyboard) goto done;
    failure = "directinput_mouse";
    input_error = IDirectInput8_CreateDevice(direct_input, &GUID_SysMouse, &mouse, NULL);
    if (FAILED(input_error) || !mouse) goto done;
    input_ready = 1;
    audio_observation();
    passed = 1;
    failure = "";

done:
    error = passed ? 0 : GetLastError();
    if (mouse) IDirectInputDevice8_Release(mouse);
    if (keyboard) IDirectInputDevice8_Release(keyboard);
    if (direct_input) IDirectInput8_Release(direct_input);
    if (context) {
        if (!wglMakeCurrent(NULL, NULL)) { passed = 0; failure = "wgl_cleanup"; error = GetLastError(); }
        if (!wglDeleteContext(context)) { passed = 0; failure = "wgl_cleanup"; error = GetLastError(); }
    }
    if (dc && !ReleaseDC(window, dc)) { passed = 0; failure = "dc_cleanup"; error = GetLastError(); }
    if (window && !DestroyWindow(window)) { passed = 0; failure = "window_cleanup"; error = GetLastError(); }
    printf("COH_CLIENT_PROBE_V1 {\"format\":1,\"status\":\"%s\",\"failure_stage\":", passed ? "passed" : "failed");
    json_string(failure);
    printf(",\"pointer_bits\":%u,\"win32_error\":%lu,\"scope\":\"headless_wgl_client_capabilities\",\"gl\":{\"vendor\":",
           (unsigned int)(sizeof(void *) * 8), (unsigned long)error);
    json_string(saved_vendor);
    fputs(",\"renderer\":", stdout); json_string(saved_renderer);
    fputs(",\"version\":", stdout); json_string(saved_version);
    printf(",\"renderer_class\":\"%s\",\"arb_vertex_program\":%s,\"arb_fragment_program\":%s,\"arb_shader_objects\":%s,\"framebuffer_extension\":%s,\"wgl_pbuffer_entrypoint\":%s,\"wgl_pixel_format_entrypoint\":%s,\"pbuffer_exercised\":false},",
           software_renderer(saved_renderer) ? "software" : "unclassified",
           arb_vertex ? "true" : "false", arb_fragment ? "true" : "false", shader_objects ? "true" : "false",
           framebuffer ? "true" : "false", wgl_pbuffer ? "true" : "false", wgl_pixel_format ? "true" : "false");
    printf("\"render\":{\"textured_quad_verified\":%s,\"samples_verified\":%u,\"swap_buffers\":%s,\"rgb_samples\":[",
           rendered ? "true" : "false", rendered ? 4U : 0U, swapped ? "true" : "false");
    for (i = 0; i < 4; ++i) printf("%s[%u,%u,%u]", i ? "," : "", samples[i][0], samples[i][1], samples[i][2]);
    printf("]},\"input\":{\"scope\":\"synthetic_own_window_and_device_creation_only\",\"window_messages_verified\":%s,\"keyboard_message_mask\":%u,\"mouse_message_mask\":%u,\"directinput_devices_created\":%s,\"directinput_hresult\":%lu,\"physical_input_validated\":false},",
           messages ? "true" : "false", keyboard_messages, mouse_messages, input_ready ? "true" : "false", (unsigned long)input_error);
    printf("\"audio\":{\"scope\":\"device_enumeration_only\",\"enumeration_hresult\":%lu,\"devices\":%u,\"default_reported\":%s,\"playback_validated\":false},",
           (unsigned long)audio_enumeration, audio_devices, audio_default ? "true" : "false");
    puts("\"cg_shaders_validated\":false,\"game_rendering_validated\":false,\"android_surface_validated\":false,\"hardware_acceleration_validated\":false}");
    return passed ? 0 : 10;
}
#endif
