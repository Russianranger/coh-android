/* COH visible presentation fixture, contract 1. This is not a game client.
 * Screen coordinates are top-left, exact 800x600 client area, no window border.
 * Session: y=0..23, 128 bits MSB-first, 6 pixels/bit, black=0 white=1.
 * Frame: y=32..55, 16 bits MSB-first, 24 pixels/bit. Complement at x+384.
 * Bars: y=80..599, four 200-pixel columns; even=R,G,B,W, odd=W,B,G,R.
 * Everything else is black. Frames start at 1 and remain visible for 500 ms.
 * The session identifier prevents a previous run/framebuffer certifying a run.
 */
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0600
#endif
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

static int parse_arguments(int argc, char **argv, unsigned int *seconds) {
    size_t i;
    unsigned int value = 0;
    if (argc != 3 || strlen(argv[1]) != 32 || !*argv[2] || strlen(argv[2]) > 3) return 0;
    for (i = 0; i < 32; ++i)
        if (!((argv[1][i] >= '0' && argv[1][i] <= '9') ||
              (argv[1][i] >= 'a' && argv[1][i] <= 'f'))) return 0;
    for (i = 0; argv[2][i]; ++i) {
        if (argv[2][i] < '0' || argv[2][i] > '9') return 0;
        value = value * 10 + (unsigned int)(argv[2][i] - '0');
    }
    if (value < 30 || value > 120 || argv[2][0] == '0') return 0;
    *seconds = value;
    return 1;
}

static unsigned int session_bit(const char *session, unsigned int i) {
    unsigned int nibble = (unsigned int)(session[i / 4] <= '9' ?
        session[i / 4] - '0' : session[i / 4] - 'a' + 10);
    return (nibble >> (3 - i % 4)) & 1U;
}

static unsigned int frame_bit(unsigned int frame, unsigned int i) {
    return (frame >> (15 - i)) & 1U;
}

static void bar_rgb(unsigned int frame, unsigned int column, unsigned char rgb[3]) {
    static const unsigned char colors[4][3] = {{255,0,0},{0,255,0},{0,0,255},{255,255,255}};
    memcpy(rgb, colors[(frame & 1U) ? 3 - column : column], 3);
}

static int contains_folded(const char *value, const char *needle) {
    size_t i, j;
    for (i = 0; value && value[i]; ++i) {
        for (j = 0; needle[j] && value[i+j] &&
             tolower((unsigned char)value[i+j]) == tolower((unsigned char)needle[j]); ++j) {}
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

static void json_string(const char *value) {
    size_t i;
    putchar('"');
    for (i = 0; value && value[i] && i < 512; ++i) {
        unsigned char c = (unsigned char)value[i];
        if (c == '"' || c == '\\') { putchar('\\'); putchar(c); }
        else if (c < 32 || c >= 127) printf("\\u%04x", (unsigned int)c);
        else putchar(c);
    }
    putchar('"');
}

#ifndef COH_PRESENTATION_PROBE_TEST
#include <windows.h>
#include <GL/gl.h>

static LRESULT CALLBACK window_proc(HWND window, UINT message, WPARAM wparam, LPARAM lparam) {
    if (message == WM_CLOSE) { PostQuitMessage(1); return 0; }
    return DefWindowProcA(window, message, wparam, lparam);
}

static void rectangle(int x, int y, int width, int height, unsigned char r, unsigned char g, unsigned char b) {
    glScissor(x, 600 - y - height, width, height);
    glClearColor(r / 255.0f, g / 255.0f, b / 255.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
}

static int render_frame(const char *session, unsigned int frame) {
    unsigned int i, j;
    unsigned char session_row[768*3], frame_row[768*3], actual[3], expected[3];
    glViewport(0, 0, 800, 600);
    glDisable(GL_DITHER); glDisable(GL_BLEND); glDisable(GL_DEPTH_TEST);
    glDisable(GL_ALPHA_TEST); glDisable(GL_STENCIL_TEST);
    glDrawBuffer(GL_BACK); glReadBuffer(GL_BACK); glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glEnable(GL_SCISSOR_TEST);
    rectangle(0, 0, 800, 600, 0, 0, 0);
    for (i = 0; i < 128; ++i) if (session_bit(session, i)) rectangle(6*i, 0, 6, 24, 255, 255, 255);
    for (i = 0; i < 16; ++i) {
        unsigned char value = frame_bit(frame, i) ? 255 : 0;
        rectangle(24*i, 32, 24, 24, value, value, value);
        rectangle(384+24*i, 32, 24, 24, 255-value, 255-value, 255-value);
    }
    for (i = 0; i < 4; ++i) { bar_rgb(frame, i, expected); rectangle(200*i, 80, 200, 520, expected[0], expected[1], expected[2]); }
    glDisable(GL_SCISSOR_TEST);
    glFinish();
    glReadPixels(0, 600-1-12, 768, 1, GL_RGB, GL_UNSIGNED_BYTE, session_row);
    glReadPixels(0, 600-1-44, 768, 1, GL_RGB, GL_UNSIGNED_BYTE, frame_row);
    for (i = 0; i < 128; ++i) for (j = 0; j < 3; ++j)
        if (session_row[(6*i+3)*3+j] != (session_bit(session, i) ? 255 : 0)) return 0;
    for (i = 0; i < 16; ++i) for (j = 0; j < 3; ++j) {
        unsigned char value = frame_bit(frame, i) ? 255 : 0;
        if (frame_row[(24*i+12)*3+j] != value || frame_row[(384+24*i+12)*3+j] != 255-value) return 0;
    }
    for (i = 0; i < 4; ++i) {
        bar_rgb(frame, i, expected);
        glReadPixels(100+200*i, 600-1-300, 1, 1, GL_RGB, GL_UNSIGNED_BYTE, actual);
        if (memcmp(actual, expected, 3)) return 0;
    }
    return glGetError() == GL_NO_ERROR;
}

int main(int argc, char **argv) {
    HINSTANCE instance = GetModuleHandleA(NULL);
    WNDCLASSA klass;
    PIXELFORMATDESCRIPTOR pixel;
    HWND window = NULL;
    HDC dc = NULL;
    HGLRC context = NULL;
    RECT client;
    MSG message;
    unsigned int seconds = 0, frame, frames = 0;
    char renderer[513] = "", vendor[513] = "", version[513] = "";
    const char *failure = "arguments", *session = "", *value;
    int passed = 0, format;
    ULONGLONG due;
    setvbuf(stdout, NULL, _IONBF, 0);
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
    if (!parse_arguments(argc, argv, &seconds)) goto done;
    session = argv[1];
    failure = "pointer_bits";
    if (sizeof(void *) != 4) goto done;
    memset(&klass, 0, sizeof(klass));
    klass.style = CS_OWNDC; klass.lpfnWndProc = window_proc;
    klass.hInstance = instance; klass.lpszClassName = "COHPresentationProbeV1";
    failure = "window_class";
    if (!RegisterClassA(&klass)) goto done;
    failure = "window_create";
    window = CreateWindowExA(WS_EX_TOPMOST, klass.lpszClassName, "COH visible presentation test",
        WS_POPUP, 0, 0, 800, 600, NULL, NULL, instance, NULL);
    if (!window) goto done;
    ShowWindow(window, SW_SHOW); UpdateWindow(window);
    SetWindowPos(window, HWND_TOPMOST, 0, 0, 800, 600, SWP_SHOWWINDOW);
    failure = "client_dimensions";
    if (!GetClientRect(window, &client) || client.right != 800 || client.bottom != 600) goto done;
    failure = "window_dc"; dc = GetDC(window); if (!dc) goto done;
    memset(&pixel, 0, sizeof(pixel)); pixel.nSize = sizeof(pixel); pixel.nVersion = 1;
    pixel.dwFlags = PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER;
    pixel.iPixelType = PFD_TYPE_RGBA; pixel.cColorBits = 24; pixel.iLayerType = PFD_MAIN_PLANE;
    failure = "pixel_format"; format = ChoosePixelFormat(dc, &pixel);
    if (!format || !SetPixelFormat(dc, format, &pixel)) goto done;
    failure = "wgl_context"; context = wglCreateContext(dc);
    if (!context || !wglMakeCurrent(dc, context)) goto done;
    failure = "renderer_identity";
    value = (const char *)glGetString(GL_RENDERER); if (!value || !*value) goto done;
    snprintf(renderer, sizeof(renderer), "%s", value);
    value = (const char *)glGetString(GL_VENDOR); if (!value || !*value) goto done;
    snprintf(vendor, sizeof(vendor), "%s", value);
    value = (const char *)glGetString(GL_VERSION); if (!value || !*value) goto done;
    snprintf(version, sizeof(version), "%s", value);
    for (frame = 1; frame <= seconds*2; ++frame) {
        failure = "frame_readback";
        if (!render_frame(session, frame)) goto done;
        failure = "swap_buffers"; if (!SwapBuffers(dc)) goto done;
        glFinish(); frames = frame;
        printf("COH_PRESENTATION_FRAME_V1 {\"session_id\":\"%s\",\"frame\":%u}\n", session, frame);
        due = GetTickCount64()+500;
        while (GetTickCount64() < due) {
            while (PeekMessageA(&message, NULL, 0, 0, PM_REMOVE)) {
                if (message.message == WM_QUIT) { failure = "window_closed"; goto done; }
                TranslateMessage(&message); DispatchMessageA(&message);
            }
            Sleep(10);
        }
    }
    passed = 1; failure = "";
done:
    if (context) {
        if (!wglMakeCurrent(NULL, NULL) || !wglDeleteContext(context)) { passed = 0; failure = "wgl_cleanup"; }
    }
    if (dc && !ReleaseDC(window, dc)) { passed = 0; failure = "dc_cleanup"; }
    if (window && !DestroyWindow(window)) { passed = 0; failure = "window_cleanup"; }
    printf("COH_PRESENTATION_PROBE_V1 {\"format\":1,\"status\":\"%s\",\"failure_stage\":", passed ? "passed" : "failed");
    json_string(failure);
    printf(",\"session_id\":\"%s\",\"width\":800,\"height\":600,\"frames\":%u,\"duration_seconds\":%u,\"pointer_bits\":%u,\"renderer\":", session, frames, seconds, (unsigned int)(sizeof(void *)*8));
    json_string(renderer); fputs(",\"vendor\":", stdout); json_string(vendor);
    fputs(",\"gl_version\":", stdout); json_string(version);
    printf(",\"software_rendering\":%s,\"frame_contract\":1,\"readback_verified\":%s,\"android_surface_validated\":false,\"game_validated\":false}\n",
        software_renderer(renderer) ? "true" : "false", passed ? "true" : "false");
    return passed ? 0 : 10;
}
#endif
