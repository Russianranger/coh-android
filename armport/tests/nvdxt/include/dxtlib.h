/* Minimal host stand-in for 3rdparty/nvdxt/dxtlib.h (only what the stand-in uses). */
typedef struct CompressionOptions CompressionOptions;
typedef struct fpPixel fpPixel;
typedef HRESULT (*MIPcallback)(void *, int, DWORD, int, int, void *);
void ReadDTXnFile(DWORD count, void *buffer, void *userData);
