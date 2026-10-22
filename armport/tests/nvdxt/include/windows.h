/* Minimal host stand-in for building the nvDXT stand-in natively in tests. */
typedef unsigned int DWORD;
typedef long HRESULT;
typedef struct { long left, top, right, bottom; } RECT;
#define E_FAIL ((HRESULT)0x80004005L)
