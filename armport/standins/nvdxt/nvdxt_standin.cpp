/* ArmPort nvDXT stand-in.
 *
 * The NVIDIA nvDXT library is an x86-only static library. The client calls
 * four of its functions through render/dxtlibwrapper.cpp. The compressors
 * report failure (E_FAIL) so callers take their error paths; nvDXTdecompress
 * decodes DDS (below).
 * Signatures follow 3rdparty/nvdxt/dxtlib.h exactly.
 */
#include <windows.h>
#include <stdlib.h>
#include <string.h>
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

/* nvDXTdecompress: the client decodes DDS UI sprites through this
 * (texWords.c uncompressRawTexInfo). It reads the DDS file through
 * ReadDTXnFile (render/dxtlibwrapper.cpp) and returns the top level as 8-bit
 * BGRA (depth 4), which the caller swaps to RGBA. Supports DXT1, DXT3, DXT5
 * and uncompressed 16/24/32-bit RGB(A) with bit masks. Returns NULL for
 * anything else, as before.
 */
static unsigned rd32(const unsigned char *p) { return p[0] | p[1] << 8 | p[2] << 16 | (unsigned)p[3] << 24; }

static void rgb565(unsigned c, unsigned char out[4])
{
	unsigned r = (c >> 11) & 31, g = (c >> 5) & 63, b = c & 31;
	out[0] = (unsigned char)((b << 3) | (b >> 2));
	out[1] = (unsigned char)((g << 2) | (g >> 4));
	out[2] = (unsigned char)((r << 3) | (r >> 2));
	out[3] = 255;
}

/* Colour block (8 bytes) into 16 BGRA texels; dxt1 enables the 3-colour mode. */
static void colour_block(const unsigned char *b, unsigned char texel[16][4], bool dxt1)
{
	unsigned c0 = b[0] | b[1] << 8, c1 = b[2] | b[3] << 8;
	unsigned char pal[4][4];
	rgb565(c0, pal[0]);
	rgb565(c1, pal[1]);
	for (int k = 0; k < 3; k++) {
		if (c0 > c1 || !dxt1) {
			pal[2][k] = (unsigned char)((2 * pal[0][k] + pal[1][k]) / 3);
			pal[3][k] = (unsigned char)((pal[0][k] + 2 * pal[1][k]) / 3);
		} else {
			pal[2][k] = (unsigned char)((pal[0][k] + pal[1][k]) / 2);
			pal[3][k] = 0;
		}
	}
	pal[2][3] = 255;
	pal[3][3] = (c0 > c1 || !dxt1) ? 255 : 0;
	unsigned bits = rd32(b + 4);
	for (int i = 0; i < 16; i++)
		memcpy(texel[i], pal[(bits >> (2 * i)) & 3], 4);
}

static void alpha_block_dxt5(const unsigned char *b, unsigned char texel[16][4])
{
	unsigned a[8];
	a[0] = b[0];
	a[1] = b[1];
	if (a[0] > a[1]) {
		for (int k = 1; k <= 6; k++)
			a[1 + k] = ((7 - k) * a[0] + k * a[1]) / 7;
	} else {
		for (int k = 1; k <= 4; k++)
			a[1 + k] = ((5 - k) * a[0] + k * a[1]) / 5;
		a[6] = 0;
		a[7] = 255;
	}
	unsigned long long bits = 0;
	for (int k = 0; k < 6; k++)
		bits |= (unsigned long long)b[2 + k] << (8 * k);
	for (int i = 0; i < 16; i++)
		texel[i][3] = (unsigned char)a[(bits >> (3 * i)) & 7];
}

static unsigned mask_channel(unsigned v, unsigned mask)
{
	if (!mask)
		return 255;
	int shift = 0, width = 0;
	while (!((mask >> shift) & 1)) shift++;
	while (shift + width < 32 && ((mask >> (shift + width)) & 1)) width++;
	unsigned x = (v & mask) >> shift, max = (width >= 32) ? 0xffffffffu : ((1u << width) - 1);
	return max ? (x * 255 + max / 2) / max : 0;
}

unsigned char *nvDXTdecompress(int &w, int &h, int &depth, int &total_width, int &rowBytes,
                               int &src_format, int SpecifiedMipMaps)
{
	w = h = depth = total_width = rowBytes = src_format = 0;
	unsigned char hdr[128];
	ReadDTXnFile(sizeof(hdr), hdr, NULL);
	if (memcmp(hdr, "DDS ", 4) || rd32(hdr + 4) != 124)
		return NULL;
	int height = (int)rd32(hdr + 12), width = (int)rd32(hdr + 16);
	const unsigned char *pf = hdr + 4 + 72;    /* DDPIXELFORMAT */
	unsigned pf_flags = rd32(pf + 4), fourcc = rd32(pf + 8), bpp = rd32(pf + 12);
	unsigned rmask = rd32(pf + 16), gmask = rd32(pf + 20), bmask = rd32(pf + 24), amask = rd32(pf + 28);
	if (width <= 0 || height <= 0 || width > 16384 || height > 16384)
		return NULL;
	unsigned char *out = (unsigned char *)malloc((size_t)width * height * 4);
	if (!out)
		return NULL;

	if (pf_flags & 0x4) {                      /* DDPF_FOURCC */
		int kind = fourcc == 0x31545844 ? 1 : fourcc == 0x33545844 ? 3 : fourcc == 0x35545844 ? 5 : 0;
		if (!kind) {
			free(out);
			return NULL;
		}
		int block_bytes = kind == 1 ? 8 : 16, bw = (width + 3) / 4, bh = (height + 3) / 4;
		unsigned char *blocks = (unsigned char *)malloc((size_t)bw * bh * block_bytes);
		if (!blocks) {
			free(out);
			return NULL;
		}
		ReadDTXnFile((DWORD)(bw * bh * block_bytes), blocks, NULL);
		for (int by = 0; by < bh; by++)
			for (int bx = 0; bx < bw; bx++) {
				const unsigned char *b = blocks + ((size_t)by * bw + bx) * block_bytes;
				unsigned char texel[16][4];
				colour_block(kind == 1 ? b : b + 8, texel, kind == 1);
				if (kind == 3)
					for (int i = 0; i < 16; i++) {
						unsigned a = (b[i / 2] >> (4 * (i & 1))) & 15;
						texel[i][3] = (unsigned char)(a * 17);
					}
				else if (kind == 5)
					alpha_block_dxt5(b, texel);
				for (int i = 0; i < 16; i++) {
					int x = bx * 4 + (i & 3), y = by * 4 + (i >> 2);
					if (x < width && y < height)
						memcpy(out + ((size_t)y * width + x) * 4, texel[i], 4);
				}
			}
		free(blocks);
		src_format = (int)fourcc;
	} else if ((pf_flags & 0x40) && (bpp == 16 || bpp == 24 || bpp == 32)) {  /* DDPF_RGB */
		int bytes = (int)bpp / 8;
		unsigned char *row = (unsigned char *)malloc((size_t)width * bytes);
		if (!row) {
			free(out);
			return NULL;
		}
		if (!(pf_flags & 0x1))                 /* no DDPF_ALPHAPIXELS */
			amask = 0;
		/* Row pitch: rows may be padded to a DWORD (DDSD_PITCH). The client
		 * (render/tex.c) rewrites width and height when it skips mip levels
		 * but keeps the top level's pitch, so the header pitch is used only
		 * when it is this width's unpadded or DWORD-aligned row. */
		unsigned row_bytes = (unsigned)width * bytes, pitch = row_bytes;
		unsigned hdr_flags = rd32(hdr + 8), hdr_pitch = rd32(hdr + 20);
		if ((hdr_flags & 0x8) && hdr_pitch == ((row_bytes + 3) & ~3u))
			pitch = hdr_pitch;
		unsigned char pad[4];
		for (int y = 0; y < height; y++) {
			ReadDTXnFile((DWORD)row_bytes, row, NULL);
			if (pitch > row_bytes && y + 1 < height)
				ReadDTXnFile((DWORD)(pitch - row_bytes), pad, NULL);
			for (int x = 0; x < width; x++) {
				unsigned v = 0;
				for (int k = 0; k < bytes; k++)
					v |= (unsigned)row[x * bytes + k] << (8 * k);
				unsigned char *o = out + ((size_t)y * width + x) * 4;
				o[0] = (unsigned char)mask_channel(v, bmask);
				o[1] = (unsigned char)mask_channel(v, gmask);
				o[2] = (unsigned char)mask_channel(v, rmask);
				o[3] = (unsigned char)mask_channel(v, amask);
			}
		}
		free(row);
		src_format = (int)bpp;
	} else {
		free(out);
		return NULL;
	}
	(void)SpecifiedMipMaps;                    /* top level only */
	w = width;
	h = height;
	depth = 4;
	total_width = width;
	rowBytes = width * 4;
	return out;
}
