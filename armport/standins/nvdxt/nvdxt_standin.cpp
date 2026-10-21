/* ArmPort nvDXT stand-in.
 *
 * The NVIDIA nvDXT library is an x86-only static library. The client calls
 * four of its functions through render/dxtlibwrapper.cpp. Until a portable
 * replacement is needed, they report failure (E_FAIL / NULL) so callers take
 * their error paths. Signatures follow 3rdparty/nvdxt/dxtlib.h exactly.
 */
#include <windows.h>
#include <dxtlib.h>

HRESULT nvDXTcompress(unsigned char *raw_data, unsigned long w, unsigned long h,
                      DWORD byte_pitch, CompressionOptions *options, DWORD planes,
                      MIPcallback callback, RECT *rect)
{
	return E_FAIL;
}

HRESULT nvDXTcompressVolume(unsigned char *raw_data, unsigned long w, unsigned long h,
                            unsigned long depth, DWORD byte_pitch,
                            CompressionOptions *options, DWORD planes,
                            MIPcallback callback, RECT *rect)
{
	return E_FAIL;
}

HRESULT nvDXTcompress32F(fpPixel *raw_data, unsigned long w, unsigned long h, DWORD pitch,
                         CompressionOptions *options, DWORD planes, MIPcallback callback,
                         RECT *rect)
{
	return E_FAIL;
}

unsigned char *nvDXTdecompress(int &w, int &h, int &depth, int &total_width, int &rowBytes,
                               int &src_format, int SpecifiedMipMaps)
{
	w = h = depth = total_width = rowBytes = src_format = 0;
	return NULL;
}
