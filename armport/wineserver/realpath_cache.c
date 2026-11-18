/* Remember where folders really are, for wineserver (ArmPort, 0.13.74).
 *
 * Wine's server stores the real Unix path of every file it opens:
 * open_fd() and set_fd_name() in server/fd.c call realpath(path, NULL).
 * glibc resolves a path with one readlink() per component, and under PRoot
 * every readlink() is two tracing stops plus a path translation. Thor
 * 0.13.73, launch B: wineserver made 505,539 readlinkat calls for 27,423
 * opens, a quarter of everything PRoot served in that launch.
 *
 * This library is loaded with LD_PRELOAD. In a process named "wineserver"
 * with ARMPORT_REALPATH_CACHE=1 it answers realpath() from a small table of
 * folders it has already resolved: the folder part comes from the table, and
 * one readlink() of the last component shows whether that is a link. A link,
 * a missing file, an unusual path or any doubt goes to glibc's realpath()
 * unchanged. An entry is used for at most TTL_SECONDS. In any other process,
 * or without the variable, every call goes straight to glibc. wineserver has
 * one thread, and the table is not locked.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define SLOTS 2048              /* direct mapped; a collision replaces the entry */
#define TTL_SECONDS 60
#define REPORT_EVERY 1024

struct slot {
    char *folder;               /* as asked: everything before the last '/' */
    char *resolved;             /* glibc's realpath() of it */
    size_t folder_length, resolved_length;
    time_t stamp;
};

static struct slot slots[SLOTS];
static int active = -1;
static char *(*next_realpath)(const char *, char *);
static const char *report_path;
static unsigned long calls, fast, folders, refreshed, passed;

static void report(void)
{
    char line[200];
    int length, fd;

    if (!report_path || !calls)     /* "wineserver -k" and "-w" resolve nothing: no file */
        return;
    length = snprintf(line, sizeof line,
                      "ARMPORT_REALPATH_CACHE_V1 calls=%lu fast=%lu folders=%lu refreshed=%lu passed=%lu\n",
                      calls, fast, folders, refreshed, passed);
    if (length <= 0 || (size_t)length >= sizeof line)
        return;
    fd = open(report_path, O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (fd < 0)
        return;
    if (write(fd, line, (size_t)length) != length) { /* evidence only */ }
    close(fd);
}

static void leave(void)
{
    if (active == 1)
        report();
}

static void enter(void)
{
    const char *wanted = getenv("ARMPORT_REALPATH_CACHE");
    const char *name = program_invocation_short_name;

    next_realpath = (char *(*)(const char *, char *))dlsym(RTLD_NEXT, "realpath");
    active = next_realpath && wanted && !strcmp(wanted, "1") && name && !strcmp(name, "wineserver");
    if (active) {
        /* One file per server process: "<ARMPORT_REALPATH_CACHE_REPORT>.<pid>". */
        const char *path = getenv("ARMPORT_REALPATH_CACHE_REPORT");
        char *own;
        if (path && path[0] == '/' && strlen(path) < PATH_MAX - 16 && (own = malloc(strlen(path) + 16))) {
            sprintf(own, "%s.%ld", path, (long)getpid());
            report_path = own;
        }
        atexit(leave);
    }
}

static unsigned long hash(const char *text, size_t length)
{
    unsigned long value = 1469598103934665603UL;
    size_t index;

    for (index = 0; index < length; index++)
        value = (value ^ (unsigned char)text[index]) * 1099511628211UL;
    return value;
}

static time_t now(void)
{
    struct timespec value;

    if (clock_gettime(CLOCK_MONOTONIC_COARSE, &value))
        return 0;
    return value.tv_sec + 1;    /* never 0: 0 marks an empty slot */
}

/* The resolved folder for path[0..length), or NULL to let glibc answer. */
static const struct slot *folder_for(const char *path, size_t length)
{
    struct slot *slot = &slots[hash(path, length) % SLOTS];
    time_t moment = now();
    char *folder, *resolved;

    if (!moment)
        return NULL;
    if (slot->stamp && slot->folder_length == length && !memcmp(slot->folder, path, length)) {
        if (moment - slot->stamp < TTL_SECONDS)
            return slot;
        refreshed++;
    }
    folder = strndup(path, length);
    if (!folder)
        return NULL;
    resolved = next_realpath(folder, NULL);
    if (!resolved) {
        free(folder);
        return NULL;
    }
    if (slot->stamp) {
        free(slot->folder);
        free(slot->resolved);
    }
    slot->folder = folder;
    slot->resolved = resolved;
    slot->folder_length = length;
    slot->resolved_length = strlen(resolved);
    slot->stamp = moment;
    folders++;
    return slot;
}

static char *answer(const char *path, char *resolved)
{
    const char *slash, *last;
    size_t folder_length, last_length, total;
    const struct slot *slot;
    char candidate[PATH_MAX], probe;
    int saved = errno;
    char *result;

    if (!path || path[0] != '/')
        return NULL;
    slash = strrchr(path, '/');
    last = slash + 1;
    folder_length = (size_t)(slash - path);
    last_length = strlen(last);
    if (!folder_length || !last_length || folder_length + 1 + last_length >= PATH_MAX
        || !strcmp(last, ".") || !strcmp(last, ".."))
        return NULL;
    slot = folder_for(path, folder_length);
    if (!slot)
        return NULL;
    total = slot->resolved_length + 1 + last_length;
    if (slot->resolved[0] != '/' || total >= PATH_MAX)
        return NULL;
    if (slot->resolved_length == 1) {               /* the folder is "/" */
        candidate[0] = '/';
        memcpy(candidate + 1, last, last_length + 1);
    } else {
        memcpy(candidate, slot->resolved, slot->resolved_length);
        candidate[slot->resolved_length] = '/';
        memcpy(candidate + slot->resolved_length + 1, last, last_length + 1);
    }
    /* EINVAL: it exists and is not a link, so the candidate is the real path. */
    if (readlink(candidate, &probe, 1) != -1 || errno != EINVAL) {
        errno = saved;
        return NULL;
    }
    errno = saved;
    if (resolved) {
        strcpy(resolved, candidate);
        result = resolved;
    } else {
        result = strdup(candidate);
        if (!result)
            return NULL;
    }
    fast++;
    return result;
}

char *realpath(const char *path, char *resolved)
{
    char *result;

    if (active < 0)
        enter();
    if (!next_realpath) {
        errno = ENOSYS;
        return NULL;
    }
    if (active != 1)
        return next_realpath(path, resolved);
    calls++;
    result = answer(path, resolved);
    if (!result) {
        passed++;
        result = next_realpath(path, resolved);
    }
    if (calls % REPORT_EVERY == 0)
        report();
    return result;
}

/* The fortified entry point, should a caller have been compiled to use it. */
char *__realpath_chk(const char *path, char *resolved, size_t resolved_size)
{
    if (resolved && resolved_size < PATH_MAX) {     /* glibc's own check and abort */
        char *(*checked)(const char *, char *, size_t) =
            (char *(*)(const char *, char *, size_t))dlsym(RTLD_NEXT, "__realpath_chk");
        if (checked)
            return checked(path, resolved, resolved_size);
        errno = ERANGE;
        return NULL;
    }
    return realpath(path, resolved);
}
