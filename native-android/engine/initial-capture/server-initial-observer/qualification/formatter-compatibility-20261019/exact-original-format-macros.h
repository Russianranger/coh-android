#include <stdio.h>
#define FORMAT const char *
int quick_snprintf(char *buffer, size_t buf_size, size_t maxlen, FORMAT format, ...);
#define ARRAY_SIZE_CHECKED(n)                    (sizeof(n) / ((sizeof(n)==sizeof(void*) || sizeof(n)==0)?0:sizeof((n)[0])))
#define snprintf_s        quick_snprintf
#define snprintf(buffer, maxlen, ...) \
	snprintf_s(buffer, ARRAY_SIZE_CHECKED(buffer), maxlen, __VA_ARGS__)
