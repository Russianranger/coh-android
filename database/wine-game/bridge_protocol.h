/* Pure bounded parsing shared by the Win32 bridge and its native contracts. */
#ifndef COH_BRIDGE_PROTOCOL_H
#define COH_BRIDGE_PROTOCOL_H
#include <stddef.h>
#include <string.h>
#include <stdint.h>

#define COH_BRIDGE_FRAME_LIMIT 100000
#define COH_BRIDGE_COMMAND_LIMIT 4096

static int coh_bridge_frame(const char *data, size_t bytes)
{
    return bytes > 1 && bytes <= COH_BRIDGE_FRAME_LIMIT &&
        data[bytes - 1] == '\0' && memchr(data, '\0', bytes - 1) == NULL;
}

static int coh_bridge_command(const char *data, size_t bytes)
{
    size_t i;
    if (!bytes || bytes >= COH_BRIDGE_COMMAND_LIMIT) return 0;
    for (i = 0; i < bytes; ++i)
        if ((unsigned char)data[i] < 32 || (unsigned char)data[i] > 126) return 0;
    return 1;
}

static int coh_bridge_pid(const char *text, uint32_t expected)
{
    uint64_t value = 0;
    size_t count = 0;
    if (*text < '1' || *text > '9') return 0;
    while (*text) {
        if (*text < '0' || *text > '9' || ++count > 10) return 0;
        value = value * 10 + (unsigned)(*text++ - '0');
        if (value > UINT32_MAX) return 0;
    }
    return value == expected;
}

/* Append one Windows command-line argument using the CommandLineToArgvW rules.
 * TestClient's own legacy parser is unchanged; callers use its accepted flags. */
static int coh_bridge_quote(char *output, size_t capacity, size_t *used, const char *argument)
{
    size_t slashes = 0;
    const char *p = argument;
#define COH_APPEND(c) do { if (*used + 1 >= capacity) return 0; output[(*used)++] = (c); } while (0)
    if (*used) COH_APPEND(' ');
    if (*argument && !strpbrk(argument, " \t\"")) {
        while (*p) COH_APPEND(*p++);
        output[*used] = 0;
        return 1;
    }
    COH_APPEND('"');
    for (;;) {
        if (*p == '\\') { ++slashes; ++p; continue; }
        if (*p == '"' || !*p) {
            size_t n;
            for (n = 0; n < slashes * 2; ++n) COH_APPEND('\\');
            if (*p == '"') COH_APPEND('\\');
        } else {
            size_t n;
            for (n = 0; n < slashes; ++n) COH_APPEND('\\');
        }
        slashes = 0;
        if (!*p) break;
        COH_APPEND(*p++);
    }
    COH_APPEND('"');
    output[*used] = 0;
    return 1;
#undef COH_APPEND
}
#endif
