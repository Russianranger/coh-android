#include <assert.h>
#include <stdio.h>
#include "bridge_protocol.h"

int main(void)
{
    char output[256] = "";
    size_t used = 0;
    char maximum[COH_BRIDGE_FRAME_LIMIT];
    assert(coh_bridge_frame("PID: 72", 8));
    assert(!coh_bridge_frame("PID: 72", 7));
    assert(!coh_bridge_frame("", 1));
    assert(!coh_bridge_frame("PID\0: 72", 9));
    memset(maximum, 'A', sizeof(maximum));
    maximum[sizeof(maximum) - 1] = 0;
    assert(coh_bridge_frame(maximum, sizeof(maximum)));
    maximum[sizeof(maximum) - 1] = 'A';
    assert(!coh_bridge_frame(maximum, sizeof(maximum)));
    assert(!coh_bridge_frame(maximum, sizeof(maximum) + 1));
    assert(coh_bridge_command("CMD influence 12345", 19));
    assert(!coh_bridge_command("CMD quit\n", 9));
    assert(!coh_bridge_command("CMD\0quit", 8));
    assert(!coh_bridge_command("CMD \x80", 5));
    assert(!coh_bridge_command("", 0));
    assert(!coh_bridge_command(maximum, COH_BRIDGE_COMMAND_LIMIT));
    assert(coh_bridge_pid("72", 72));
    assert(coh_bridge_pid("4294967295", UINT32_MAX));
    assert(!coh_bridge_pid("4294967296", 0));
    assert(!coh_bridge_pid("72junk", 72));
    assert(!coh_bridge_pid("072", 72));
    assert(!coh_bridge_pid("-72", 72));
    assert(!coh_bridge_pid("73", 72));
    assert(coh_bridge_quote(output, sizeof(output), &used, "C:\\game path\\TestClient.exe"));
    assert(coh_bridge_quote(output, sizeof(output), &used, "-db"));
    assert(coh_bridge_quote(output, sizeof(output), &used, "127.0.0.1"));
    assert(!strcmp(output, "\"C:\\game path\\TestClient.exe\" -db 127.0.0.1"));
    used = 0;
    assert(coh_bridge_quote(output, sizeof(output), &used, "a b\\"));
    assert(!strcmp(output, "\"a b\\\\\""));
    used = 0;
    assert(coh_bridge_quote(output, sizeof(output), &used, "say\"hello"));
    assert(!strcmp(output, "\"say\\\"hello\""));
    used = 0;
    assert(coh_bridge_quote(output, sizeof(output), &used, ""));
    assert(!strcmp(output, "\"\""));
    used = 0;
    assert(!coh_bridge_quote(output, 4, &used, "long"));
    puts("PASS bounded bridge frame, PID, command and child-argument contracts");
    return 0;
}
