"""Entity interpolation clock across zoning (patch 0123), extracted from the given source.

entrecv.c draws other entities at client_abs, auto_delay seconds behind the
newest server update, using local_time_bias (U32) to map the client's clock
onto the server's abs_time. doMapXfer resets the bias to 0. When the new zone
server is younger than the client's clock (King's Row started after the client
was in Atlas), the corrected bias is negative modulo 2**32. x86 converts the
negative float correction modulo 2**32; AArch64 FCVTZU saturates it to 0, the
bias stays 0, client_abs is clamped to the newest update and entities jump
from update to update (Thor 0.13.50/0.13.51: King's Row NPCs, cars and trains).

The fixture compiles the bias update, the client_abs computation and
calcAutoDelay from entrecv.c and simulates Atlas (server 140 s older than the
client's clock, 600 s), a monorail trip to King's Row (server uptime 40 s,
60 s) and the return to Atlas, at 60 client frames and 4 server updates per
second (the MapServer's net_send.update_period of 30/4 ticks). Each stay must keep a mean interpolation lag of at least 50 ms.
Run on an AArch64 host (the CI build runner): --original takes the code from
the unpatched upstream file and must fail there. On x86 hosts the original
conversion wraps and passes, which is why the x86 client never showed it.
"""
from pathlib import Path
import argparse
import platform
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--original', type=Path, help='unpatched upstream/ouroboros (negative control)')
args = parser.parse_args()
root = args.original or args.source
text = (root / 'Game/src/entity/entrecv.c').read_text()
init_client = (root / 'Game/src/gameComm/initClient.c').read_text()
xfer = init_client[init_client.index('int doMapXfer()'):]
xfer = xfer[:xfer.index('\n}\n')]
assert 'local_time_bias = 0;' in xfer, 'doMapXfer no longer resets local_time_bias'
header_path = root / 'Game/src/entity/armport_net_clock.h'
header = header_path.read_text() if header_path.exists() else ''


def between(start, end, *, after=0):
    begin = text.index(start, after)
    return text[begin:text.index(end, begin) + len(end)]


auto_delay = between('static void calcAutoDelay(U32 old_abs_time,U32 new_abs_time)', '\n}\n')
receive = between('            dt = (abs_time - local_time_bias) / (30.f * 100.f)',
                  'server_time = (abs_time - local_time_bias) / (30.f * 100.f);')
net_start = text.index('int entNetUpdate()')
net = between('    add_time = (TIMESTEP / 30.0);',
              '            global_state.client_abs_slow = global_state.abs_time;\n    }\n', after=net_start)
assert re.search(r'^U32\s+local_time_bias;', text, re.M) and re.search(r'^F32\s+auto_delay = 0\.4;', text, re.M)

fixture = r'''
#include <stdio.h>
typedef unsigned int U32; typedef int S32; typedef float F32;
#define ABS(a) (((a) < 0) ? (-(a)) : (a))
static F32 TIMESTEP = 0.5f;                       /* 60 client frames per second */
static struct { U32 abs_time, client_abs, client_abs_slow; } global_state;
static U32 last_packet_abs_time, local_time_bias;
static F32 auto_delay = 0.4f, server_time, test_timer_elapsed;
''' + header + '\n' + auto_delay + r'''
static void receive_update(U32 abs_time) {
    F32 dt, ticklen;
''' + receive + r'''
    (void)ticklen;
}
static void net_update(void) {
    F32 add_time; U32 new_client_abs, new_client_abs_slow; int diff_client_abs, diff_client_abs_slow;
''' + net + r'''
}
/* Runs one zone stay; returns the mean lag (ms) behind the newest update over its last 10 s. */
static double stay(U32 *server_abs, int seconds) {
    double lag = 0; int counted = 0, frame;
    for (frame = 0; frame < seconds * 60; frame++) {
        *server_abs += 50;                            /* 1/60 s in abs_time units (1/3000 s) */
        if (frame % 15 == 0) receive_update(*server_abs);   /* 4 updates per second */
        net_update();
        if (frame >= (seconds - 10) * 60) { lag += (S32)(global_state.abs_time - global_state.client_abs) / 3.0; counted++; }
    }
    return lag / counted;
}
int main(void) {
    U32 atlas = 140 * 3000, kings_row, kings_row_bias;
    double a, k, r;
    a = stay(&atlas, 600);
    local_time_bias = 0; kings_row = 40 * 3000;       /* doMapXfer; King's Row started 40 s ago */
    k = stay(&kings_row, 60);
    kings_row_bias = local_time_bias;
    local_time_bias = 0; atlas += 70 * 3000;          /* back to the resident Atlas server */
    r = stay(&atlas, 30);
    printf("atlas lag_ms=%.0f kings_row lag_ms=%.0f atlas_return lag_ms=%.0f kings_row_bias=%u\n", a, k, r, kings_row_bias);
    return (a >= 50 && k >= 50 && r >= 50) ? 0 : 1;
}
'''
with tempfile.TemporaryDirectory() as temporary:
    source = Path(temporary) / 'net_clock.c'
    source.write_text(fixture)
    # 1. The host's own conversion: on AArch64 the original loses the delay.
    exe = Path(temporary) / 'net_clock'
    subprocess.run(['cc', '-std=gnu11', '-O2', '-w', str(source), '-o', str(exe)], check=True)
    result = subprocess.run([str(exe)], capture_output=True, text=True)
    status = result.returncode
    line = f'{platform.machine()}: {result.stdout.strip()}' + ('' if status == 0 else ' FAIL: no interpolation delay')
    # 2. On any host: a float-to-integer conversion outside the target range is
    # undefined in C, which is what made x86 and AArch64 differ.
    checked = Path(temporary) / 'net_clock_checked'
    subprocess.run(['cc', '-std=gnu11', '-O0', '-w', '-fsanitize=float-cast-overflow',
                    str(source), '-o', str(checked)], check=True)
    sanitized = subprocess.run([str(checked)], capture_output=True, text=True)
    # Each conversion site reports its first out-of-range value once.
    errors = [part.split('runtime error: ', 1)[1] for part in sanitized.stderr.splitlines() if 'runtime error: ' in part]
    converted = sanitized.returncode == 0 and not errors
    line += ' | conversions: ' + ('in range' if converted else 'FAIL: ' + '; '.join(errors or ['exit %d' % sanitized.returncode]))
    print(line)
    raise SystemExit(status or (0 if converted else 1))
