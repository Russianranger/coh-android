/* M1 test: the original textparser, built for ARM64 Windows, reads body-part
 * data the same way the 32-bit client does.
 *
 *   armport_bodyparts <bodyparts.bp> [BodyParts.bin]
 *
 * 1. Text: ParserReadText with the original ParseBodyPartBegin table on
 *    defs/ui/bodyparts.bp must give 28 entries, first "Pants", last "Tail".
 * 2. Binary (optional): the shipped client BodyParts.bin must pass the
 *    original parse-table checksum and load to the same 28 entries. This
 *    checks that the 32-bit-built .bin files load in a 64-bit client.
 *
 * Prints one JSON line and exits 0 only if every check passes.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "utilitieslib/utils/textparser.h"
#include "utilitieslib/utils/file.h"
#include "utilitieslib/utils/serialize.h"
#include "utilitieslib/utils/textparserUtils.h"
#include "utilitieslib/components/earray.h"
#include "gameData/BodyPart.h"

extern ParseTable ParseBodyPartBegin[];

/* BodyPart.c's bone-name callback is only used by ParserLoadFiles, which this
 * test does not call; the animation system is not part of this test. */
BoneId bone_IdFromName(const char *name) { (void)name; return (BoneId)0; }

static char *read_all(const char *path, int *len)
{
	FILE *f = fopen(path, "rb");
	char *buf;
	long n;
	if (!f) return NULL;
	fseek(f, 0, SEEK_END);
	n = ftell(f);
	fseek(f, 0, SEEK_SET);
	buf = malloc(n + 1);
	if (!buf || fread(buf, 1, n, f) != (size_t)n) { fclose(f); free(buf); return NULL; }
	buf[n] = 0;
	fclose(f);
	*len = (int)n;
	return buf;
}

static int check_list(const char *label, BodyPartList *list, int ok_call)
{
	int n = eaSize(&list->bodyParts);
	const char *first = n ? list->bodyParts[0]->name : "";
	const char *last = n ? list->bodyParts[n - 1]->name : "";
	int ok = ok_call && n == 28 && first && last && !strcmp(first, "Pants") && !strcmp(last, "Tail");
	printf("\"%s\":{\"parsed\":%d,\"entries\":%d,\"first\":\"%s\",\"last\":\"%s\",\"pass\":%s}",
	       label, ok_call, n, first ? first : "", last ? last : "", ok ? "true" : "false");
	return ok;
}

int main(int argc, char **argv)
{
	int len = 0, ok = 1, r;
	char *text;
	BodyPartList text_list = {0};
	if (argc < 2) {
		fprintf(stderr, "usage: %s bodyparts.bp [BodyParts.bin]\n", argv[0]);
		return 2;
	}
	printf("{\"pointer_bytes\":%d,\"long_bytes\":%d,", (int)sizeof(void *), (int)sizeof(long));
	text = read_all(argv[1], &len);
	if (!text) {
		printf("\"text\":{\"error\":\"cannot read %s\"}}\n", argv[1]);
		return 1;
	}
	r = ParserReadText(text, len, ParseBodyPartBegin, &text_list);
	ok &= check_list("text", &text_list, r);
	if (argc >= 3) {
		BodyPartList bin_list = {0};
		int crc = ParseTableCRC(ParseBodyPartBegin, NULL);
		SimpleBufHandle file = SerializeReadOpen(argv[2], PARSE_SIG, crc, 0);
		printf(",\"table_crc\":\"%08x\",\"bin_header_accepted\":%s,", (unsigned)crc,
		       file ? "true" : "false");
		if (!file) {
			printf("\"bin\":{\"pass\":false}");
			ok = 0;
		} else {
			r = ParserReadBinaryFile(file, argv[2], ParseBodyPartBegin, &bin_list, NULL, NULL);
			ok &= check_list("bin", &bin_list, r);
		}
	}
	printf(",\"pass\":%s}\n", ok ? "true" : "false");
	return ok ? 0 : 1;
}
