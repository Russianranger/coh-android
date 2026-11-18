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
 * with ARMPORT_REALPATH_CACHE=1 it resolves a path the way glibc does, one
 * readlink() per component and following links, but takes every folder it
 * has resolved in the last TTL_SECONDS from a table. The last component is
 * always probed. The game's server folders are trees of links to the
 * installed data, so links are followed here too (CI run 44367156833: a
 * first version that left links to glibc answered 11,615 of 37,888 calls).
 * A missing file, a path with "." or ".." or an empty component, a link
 * with such a target, or any error goes to glibc's realpath() unchanged. In
 * any other process, or without the variable, every call goes straight to
 * glibc. wineserver has one thread, and the table is not locked.
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

#define SLOTS 16384             /* direct mapped; a collision replaces the entry */
#define TTL_SECONDS 60
#define REPORT_EVERY 1024
#define LINK_DEPTH 8

struct slot {
    char *asked;                /* a folder path as it was asked for */
    char *resolved;             /* its real path */
    size_t asked_length, resolved_length;
    time_t stamp;
};

static struct slot slots[SLOTS];
static int active = -1;
static char *(*next_realpath)(const char *, char *);
static const char *report_path;
static unsigned long calls, fast, folders, refreshed, passed, probes;
static time_t oldest;          /* the oldest table entry the current call has used */

static void report(void)
{
    char line[240];
    int length, fd;

    if (!report_path || !calls)     /* "wineserver -k" and "-w" resolve nothing: no file */
        return;
    length = snprintf(line, sizeof line,
                      "ARMPORT_REALPATH_CACHE_V2 calls=%lu fast=%lu folders=%lu refreshed=%lu passed=%lu probes=%lu\n",
                      calls, fast, folders, refreshed, passed, probes);
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

/* Absolute, no empty, "." or ".." component, no trailing slash: the only shape resolved here. */
static int plain(const char *path, size_t length)
{
    size_t index, begin;

    if (!length || length >= PATH_MAX || path[0] != '/')
        return 0;
    if (length == 1)
        return 1;
    for (begin = 1, index = 1; index <= length; index++) {
        if (index < length && path[index] != '/')
            continue;
        if (index == begin || (index - begin == 1 && path[begin] == '.')
            || (index - begin == 2 && path[begin] == '.' && path[begin + 1] == '.'))
            return 0;
        begin = index + 1;
    }
    return 1;
}

static void remember(const char *asked, size_t asked_length, const char *resolved, size_t resolved_length,
                     time_t moment)
{
    struct slot *slot = &slots[hash(asked, asked_length) % SLOTS];
    char *first = strndup(asked, asked_length), *second = strndup(resolved, resolved_length);

    if (!first || !second) {
        free(first);
        free(second);
        return;
    }
    if (slot->stamp) {
        free(slot->asked);
        free(slot->resolved);
    }
    slot->asked = first;
    slot->resolved = second;
    slot->asked_length = asked_length;
    slot->resolved_length = resolved_length;
    slot->stamp = moment;
    folders++;
}

/* The real path of the plain path[0..length) into out (PATH_MAX bytes); its length, or 0 to
 * let glibc answer the whole call. It does what glibc's realpath() does, one readlink() per
 * component, but a folder that was resolved in the last TTL_SECONDS is taken from the table.
 * `folder` is set for every component but the last one asked for; only those are remembered. */
static size_t resolve(const char *path, size_t length, char *out, int folder, int depth, time_t moment)
{
    char target[PATH_MAX];
    struct slot *slot;
    size_t parent, base, size;
    ssize_t linked;

    if (length == 1) {
        out[0] = '/';
        out[1] = 0;
        return 1;
    }
    if (folder) {
        slot = &slots[hash(path, length) % SLOTS];
        if (slot->stamp && slot->asked_length == length && !memcmp(slot->asked, path, length)) {
            if (moment - slot->stamp < TTL_SECONDS) {
                if (slot->stamp < oldest)
                    oldest = slot->stamp;
                memcpy(out, slot->resolved, slot->resolved_length + 1);
                return slot->resolved_length;
            }
            refreshed++;
        }
    }
    for (parent = length; path[parent - 1] != '/'; parent--)
        ;
    base = parent;                              /* path[base..length) is the last component */
    parent = parent > 1 ? parent - 1 : 1;       /* path[0..parent) is its folder */
    size = resolve(path, parent, out, 1, depth, moment);
    if (!size || size + 1 + (length - base) >= PATH_MAX)
        return 0;
    if (size > 1)
        out[size++] = '/';
    memcpy(out + size, path + base, length - base);
    size += length - base;
    out[size] = 0;
    probes++;
    linked = readlink(out, target, sizeof target - 1);
    if (linked < 0) {
        if (errno != EINVAL)
            return 0;                           /* missing, not a folder, no access: glibc reports it */
    } else {
        char joined[PATH_MAX];
        const char *next = target;
        size_t next_length = (size_t)linked;

        if (!linked || (size_t)linked >= sizeof target - 1 || depth >= LINK_DEPTH)
            return 0;
        target[linked] = 0;
        if (target[0] != '/') {                 /* relative to the folder the link is in */
            size_t folder_length = size - (length - base) - 1;
            const char *rest = target;
            size_t left = (size_t)linked;

            /* Leading "./" and "../": the folder is a real path already, so its parent is
             * the path without its last component ("/.." is "/"). */
            for (;;) {
                if (left >= 2 && rest[0] == '.' && rest[1] == '/') {
                    rest += 2;
                    left -= 2;
                } else if (left >= 3 && rest[0] == '.' && rest[1] == '.' && rest[2] == '/') {
                    while (folder_length && out[folder_length - 1] != '/')
                        folder_length--;
                    if (folder_length)
                        folder_length--;
                    rest += 3;
                    left -= 3;
                } else {
                    break;
                }
            }
            if (!left || folder_length + 1 + left >= PATH_MAX)
                return 0;
            memcpy(joined, out, folder_length);
            joined[folder_length] = '/';
            memcpy(joined + folder_length + 1, rest, left + 1);
            next = joined;
            next_length = folder_length + 1 + left;
        }
        if (!plain(next, next_length))
            return 0;
        size = resolve(next, next_length, out, folder, depth + 1, moment);
        if (!size)
            return 0;
    }
    /* An entry is as old as the oldest one it was built from, so nothing in the table
     * describes the file system as it was more than TTL_SECONDS ago. */
    if (folder)
        remember(path, length, out, size, oldest);
    return size;
}

static char *answer(const char *path, char *resolved)
{
    char found[PATH_MAX];
    size_t length, size;
    time_t moment;
    int saved = errno;
    char *result;

    if (!path)
        return NULL;
    length = strlen(path);
    moment = now();
    if (!moment || length < 2 || !plain(path, length))
        return NULL;
    oldest = moment;
    size = resolve(path, length, found, 0, 0, moment);
    errno = saved;
    if (!size)
        return NULL;
    if (resolved) {
        memcpy(resolved, found, size + 1);
        result = resolved;
    } else {
        result = strdup(found);
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
