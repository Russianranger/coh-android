/* Prints realpath() of each argument: "ok <path>" or "error <errno>". Built as
 * "wineserver" (the library answers only in a process of that name) and under
 * another name (where it must change nothing). With "--repeat N" first, the
 * whole list is resolved N times and only the last round is printed. */
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    int first = 1, rounds = 1, round, index;

    if (argc > 2 && !strcmp(argv[1], "--repeat")) {
        rounds = atoi(argv[2]);
        first = 3;
    }
    for (round = 0; round < rounds; round++) {
        for (index = first; index < argc; index++) {
            char buffer[PATH_MAX];
            char *allocated, *copied;

            errno = 0;
            allocated = realpath(argv[index], NULL);
            if (round == rounds - 1) {
                if (allocated) printf("ok %s\n", allocated); else printf("error %d\n", errno);
            }
            errno = 0;
            copied = realpath(argv[index], buffer);
            if (round == rounds - 1) {
                if (copied) printf("ok %s\n", buffer); else printf("error %d\n", errno);
            }
            if ((allocated == NULL) != (copied == NULL) || (allocated && strcmp(allocated, buffer))) {
                printf("mismatch %s\n", argv[index]);
                return 2;
            }
            free(allocated);
        }
    }
    return 0;
}
