/* decode <in.dds> <out.bgra>: runs the nvDXT stand-in's nvDXTdecompress on a
 * DDS file the way render/dxtlibwrapper.cpp feeds it (ReadDTXnFile). */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static unsigned char *data;
static size_t offs;

void ReadDTXnFile(DWORD count, void *buffer, void *)
{
	memcpy(buffer, data + offs, count);
	offs += count;
}

unsigned char *nvDXTdecompress(int &w, int &h, int &depth, int &total_width, int &rowBytes,
                               int &src_format, int SpecifiedMipMaps);

int main(int argc, char **argv)
{
	FILE *f = fopen(argv[1], "rb");
	if (!f)
		return 2;
	fseek(f, 0, SEEK_END);
	long n = ftell(f);
	fseek(f, 0, SEEK_SET);
	data = (unsigned char *)malloc((size_t)n);   /* exact size: ASan catches over-reads */
	if (fread(data, 1, (size_t)n, f) != (size_t)n)
		return 2;
	fclose(f);
	int w, h, depth, total_width, row_bytes, src_format;
	unsigned char *out = nvDXTdecompress(w, h, depth, total_width, row_bytes, src_format, 1);
	if (!out) {
		free(data);
		printf("NULL\n");
		return 1;
	}
	FILE *o = fopen(argv[2], "wb");
	fwrite(out, 1, (size_t)w * h * 4, o);
	fclose(o);
	printf("%d %d %d %x\n", w, h, depth, src_format);
	free(out);
	free(data);
	return 0;
}
