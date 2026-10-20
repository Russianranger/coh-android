#ifndef COH_SESSION_FRAME_CAPTURE_GL_H
#define COH_SESSION_FRAME_CAPTURE_GL_H
#include <stdint.h>
int coh_frame_capture_readback(uint32_t viewport_width,uint32_t viewport_height,uint32_t width,uint32_t height,uint8_t *rgba);
#endif
