#define _POSIX_C_SOURCE 200809L
#include "armport_library_bounds.h"
#include <assert.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); return 1; } } while (0)
#define B 40u
static char seen[4096]; static unsigned seen_count; static unsigned char seen_first[B];
static void set(const char *name, const void *bounds) { if (!seen_count) memcpy(seen_first, bounds, B); strcat(seen, name); strcat(seen, ";"); seen_count++; }
static void reset_seen(void) { seen[0] = 0; seen_count = 0; }
static void restart(void) { free(armport_lb.data); free(armport_lb.entries); memset(&armport_lb, 0, sizeof(armport_lb)); }
static void keep(const char *file, unsigned stamp, const char **names, unsigned char fill) {
    unsigned char bounds[B]; unsigned i; memset(bounds, fill, B);
    armportLibraryBoundsBegin(file, stamp);
    for (i = 0; names[i]; i++) { bounds[0] = (unsigned char)i; armportLibraryBoundsAdd(names[i], bounds); }
    armportLibraryBoundsEnd(); }
static long size_of(const char *p) { struct stat s; return stat(p, &s) ? -1 : (long)s.st_size; }
int main(int argc, char **argv) {
    const char *path = argv[1]; char tmp[300];
    const char *a[] = {"road_a", "road_b", "road_c", 0}, *b[] = {"lamp", 0}, *none[] = {0}, *a2[] = {"road_new", 0};
    char longname[400]; const char *bad[] = {"ok", longname, "after", 0};
    FILE *f; long size; unsigned i;
    (void)argc; memset(longname, 'x', 399); longname[399] = 0; snprintf(tmp, sizeof tmp, "%s.tmp", path);
    unsetenv("ARMPORT_LIBRARY_BOUNDS_CACHE");
    CHECK(!armportLibraryBoundsEnabled(B));                       /* off by default, and stays off */
    keep("x/y.txt", 1, a, 7); CHECK(!armportLibraryBoundsApply("x/y.txt", 1, set) && !armportLibraryBoundsFlush());
    setenv("ARMPORT_LIBRARY_BOUNDS_CACHE", path, 1);
    CHECK(!armportLibraryBoundsEnabled(B)); restart();
    CHECK(!armportLibraryBoundsEnabled(0) ); restart();
    CHECK(!armportLibraryBoundsEnabled(257)); restart();
    CHECK(armportLibraryBoundsEnabled(B) && !armportLibraryBoundsEnabled(B + 4));   /* no file yet: empty */
    CHECK(!armportLibraryBoundsApply("object_library/Streets/Roads.txt", 5, set));
    CHECK(!armportLibraryBoundsFlush() && size_of(path) == -1);   /* nothing kept, nothing written */
    keep("object_library/Streets/Roads.txt", 5, a, 7);
    keep("Object_Library\\Omni\\Lamp.txt", 0, b, 9);
    keep("object_library/empty.txt", 3, none, 1);
    keep("object_library/bad.txt", 3, bad, 1);                    /* a name that does not fit: not kept */
    CHECK(armport_lb.count == 3 && armport_lb.kept == 3);
    reset_seen(); CHECK(armportLibraryBoundsApply("OBJECT_LIBRARY\\streets\\roads.TXT", 5, set));
    CHECK(!strcmp(seen, "road_a;road_b;road_c;") && seen_first[0] == 0 && seen_first[1] == 7 && seen_first[B - 1] == 7);
    reset_seen(); CHECK(!armportLibraryBoundsApply("object_library/Streets/Roads.txt", 6, set) && !seen_count);   /* stamp */
    CHECK(!armportLibraryBoundsApply("object_library/bad.txt", 3, set));
    reset_seen(); CHECK(armportLibraryBoundsApply("object_library/empty.txt", 3, set) && !seen_count);
    shim_fail_write = 1; CHECK(!armportLibraryBoundsFlush() && armport_lb.dirty && size_of(path) == -1 && size_of(tmp) == -1);
    shim_fail_write = 0; shim_fail_move = 1; CHECK(!armportLibraryBoundsFlush() && armport_lb.dirty && size_of(tmp) == -1);
    shim_fail_move = 0; CHECK(armportLibraryBoundsFlush() == 3 && !armport_lb.dirty && size_of(tmp) == -1);
    CHECK(!armportLibraryBoundsFlush());
    size = size_of(path); CHECK(size > 28);
    restart(); CHECK(armportLibraryBoundsEnabled(B) && armport_lb.count == 3 && !armport_lb.dirty);   /* a new process */
    reset_seen(); CHECK(armportLibraryBoundsApply("object_library/omni/lamp.txt", 0, set) && !strcmp(seen, "lamp;") && seen_first[1] == 9);
    keep("object_library/streets/roads.txt", 6, a2, 3);            /* the source changed: replaced */
    CHECK(armport_lb.count == 3);
    reset_seen(); CHECK(armportLibraryBoundsApply("object_library/Streets/Roads.txt", 6, set) && !strcmp(seen, "road_new;"));
    CHECK(armportLibraryBoundsFlush() == 1 && size_of(path) < size);
    restart(); CHECK(armportLibraryBoundsEnabled(B) && armport_lb.count == 3);
    reset_seen(); CHECK(armportLibraryBoundsApply("object_library/Streets/Roads.txt", 6, set) && !strcmp(seen, "road_new;"));
    restart();
    CHECK(armportLibraryBoundsEnabled(B + 8) && armport_lb.count == 0); restart();    /* another bounds size: ignored */
    size = size_of(path);
    for (i = 0; i < 3; i++) {                                      /* cut short, a changed byte, a longer file */
        char copy[300]; unsigned char buffer[8192]; long n; FILE *g;
        snprintf(copy, sizeof copy, "%s.case%u", path, i);
        f = fopen(path, "rb"); n = (long)fread(buffer, 1, sizeof buffer, f); fclose(f); CHECK(n == size);
        if (i == 0) n -= 5; else if (i == 1) buffer[n - 3] ^= 1; else buffer[n++] = 0;
        g = fopen(copy, "wb"); fwrite(buffer, 1, (size_t)n, g); fclose(g);
        setenv("ARMPORT_LIBRARY_BOUNDS_CACHE", copy, 1);
        CHECK(armportLibraryBoundsEnabled(B) && armport_lb.count == 0 && armport_lb.used == 0);
        keep("a/b.txt", 1, b, 2); CHECK(armportLibraryBoundsFlush() == 1);   /* and rewritten */
        restart(); CHECK(armportLibraryBoundsEnabled(B) && armport_lb.count == 1); restart();
    }
    return 0; }
