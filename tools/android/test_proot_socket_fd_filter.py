"""PRoot patch 0007: sendto, recvfrom and recvmsg are traced only from descriptor 960 (PROOT_NETLINK_HIGH_FDS=1).

PRoot asks for these calls only to serve rtnetlink sockets. Thor 0.13.72 (20261117-130723,
-131522, -132616): 38-49 % of all stops were these three calls on other sockets. The patch
moves each rtnetlink socket to a descriptor number from 960 and adds a self-contained header
with the seccomp statements. This test takes that header out of the patch, compiles a small
harness with the host compiler and runs the statements through a minimal BPF interpreter:
descriptors below 960 are allowed, 960 and above (and negative ones) reach the tracer, and a
call that is not one of the three continues to the statements after the block with its
number intact.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from test_proot_ioctl_filter import added_file

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'android/native/proot/0007-netlink-high-fds-socket-filter.patch'

HARNESS = r'''
#include "socket_fd_filter.h"
#include <stdio.h>
#include <string.h>
#include <linux/audit.h>

static long run(const struct sock_filter *program, size_t length, const struct seccomp_data *data)
{
	uint32_t accumulator = 0;
	size_t pc = 0, steps = 0;
	for (;;) {
		if (pc >= length || ++steps > 4096) return -1;          /* fell off the program */
		const struct sock_filter *s = &program[pc];
		switch (s->code) {
		case BPF_LD + BPF_W + BPF_ABS:
			if (s->k + 4 > sizeof(*data)) return -2;
			memcpy(&accumulator, (const char *) data + s->k, 4);
			pc++; break;
		case BPF_JMP + BPF_JEQ + BPF_K:
			pc += 1 + (accumulator == s->k ? s->jt : s->jf); break;
		case BPF_JMP + BPF_JGE + BPF_K:
			pc += 1 + (accumulator >= s->k ? s->jt : s->jf); break;
		case BPF_RET + BPF_K:
			return (long) s->k;
		default:
			return -3;
		}
	}
}

int main(void)
{
	/* arm64 numbers.  */
	enum { NR_SENDTO = 206, NR_RECVFROM = 207, NR_RECVMSG = 212, NR_SENDMSG = 211, NR_OPENAT = 56, NR_CLOSE = 57 };
	const int traced[] = { NR_SENDTO, NR_RECVFROM, NR_RECVMSG };
	struct sock_filter program[3 * LENGTH_TRACE_SOCKET_FD + 6];
	size_t length = 0, i, j;
	program[length++] = (struct sock_filter) BPF_STMT(BPF_LD + BPF_W + BPF_ABS, offsetof(struct seccomp_data, nr));
	for (i = 0; i < 3; i++)
		length += socket_fd_filter_statements(program + length, (uint32_t) traced[i], 0);
	program[length++] = (struct sock_filter) BPF_JUMP(BPF_JMP + BPF_JEQ + BPF_K, NR_SENDMSG, 0, 1);
	program[length++] = (struct sock_filter) BPF_STMT(BPF_RET + BPF_K, SECCOMP_RET_TRACE);
	program[length++] = (struct sock_filter) BPF_JUMP(BPF_JMP + BPF_JEQ + BPF_K, NR_OPENAT, 0, 1);
	program[length++] = (struct sock_filter) BPF_STMT(BPF_RET + BPF_K, SECCOMP_RET_TRACE);
	program[length++] = (struct sock_filter) BPF_STMT(BPF_RET + BPF_K, SECCOMP_RET_ALLOW);
	printf("floor %d length %d\n", SOCKET_FD_FLOOR, LENGTH_TRACE_SOCKET_FD);
	const uint64_t descriptors[] = { 0, 1, 3, 64, 959, 960, 961, 1023, 1024, 70000,
					 0xffffffffULL /* -1 */, 0xfffffff7ULL /* -9 */,
					 0x100000003ULL /* 3 with a stray high word */,
					 0x1000003c0ULL /* 960 with a stray high word */ };
	for (i = 0; i < 3; i++)
		for (j = 0; j < sizeof(descriptors) / sizeof(descriptors[0]); j++) {
			struct seccomp_data data = { .nr = traced[i], .arch = AUDIT_ARCH_AARCH64 };
			data.args[0] = descriptors[j];
			data.args[1] = 960; data.args[2] = 2000; data.args[4] = 960;    /* not the descriptor */
			printf("call %d 0x%llx %ld\n", traced[i], (unsigned long long) descriptors[j],
			       run(program, length, &data));
		}
	struct seccomp_data sendmsg = { .nr = NR_SENDMSG }, openat = { .nr = NR_OPENAT }, close_call = { .nr = NR_CLOSE };
	sendmsg.args[0] = 3; openat.args[0] = 3; close_call.args[0] = 2000;
	printf("sendmsg %ld\nopenat %ld\nclose %ld\n", run(program, length, &sendmsg), run(program, length, &openat),
	       run(program, length, &close_call));
	return 0;
}
'''


class ProotSocketFdFilterTest(unittest.TestCase):
    def test_patch_shape(self):
        patch = PATCH.read_text()
        self.assertEqual(sorted(re.findall(r'^diff --git a/(\S+) ', patch, re.M)), [
            'src/syscall/chain.c', 'src/syscall/chain.h', 'src/syscall/exit.c', 'src/syscall/seccomp.c',
            'src/syscall/seccomp.h', 'src/syscall/socket_fd_filter.h', 'src/syscall/stop_counts.h',
            'src/syscall/syscall.c', 'src/syscall/syscall.h', 'src/tracee/tracee.h'])
        self.assertIn('getenv("PROOT_NETLINK_HIGH_FDS")', patch)
        # The statements are longer than the plain ones, and only for the three calls of the default ABI.
        self.assertIn('+					nb_extra_statements += LENGTH_TRACE_SOCKET_FD - LENGTH_TRACE_SYSCALL;', patch)
        self.assertIn('+	return sysnum == PR_sendto || sysnum == PR_recvfrom || sysnum == PR_recvmsg;', patch)
        self.assertEqual(patch.count('seccomp_archs[i].abis[j] == ABI_DEFAULT'), 2)
        # The tracer moves descriptors under the same condition the filter is built with.
        self.assertIn('+	    || get_abi(tracee) != ABI_DEFAULT\n+	    || !netlink_high_fds(tracee))', patch)
        self.assertIn('+	status = set_seccomp_filters(filtered_sysnums, netlink_high_fds(tracee));', patch)
        # A failed move refuses the socket and still closes the low descriptor.
        self.assertIn('+		force_chain_final_result(tracee, (word_t) -EMFILE);', patch)
        self.assertIn('+	(void) register_chained_syscall(tracee, PR_close, fd, 0, 0, 0, 0, 0);', patch)
        header = added_file(patch, 'src/syscall/socket_fd_filter.h')
        self.assertIn('#define SOCKET_FD_FLOOR 960', header)

    @unittest.skipUnless(shutil.which('gcc') or shutil.which('cc'), 'no host C compiler')
    def test_statements_trace_high_descriptors_only(self):
        compiler = shutil.which('gcc') or shutil.which('cc')
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / 'socket_fd_filter.h').write_text(added_file(PATCH.read_text(), 'src/syscall/socket_fd_filter.h'))
            (work / 'harness.c').write_text(HARNESS)
            subprocess.run([compiler, '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-O1', '-o', str(work / 'harness'),
                            str(work / 'harness.c')], check=True, cwd=work, timeout=120)
            output = subprocess.run([str(work / 'harness')], check=True, capture_output=True, text=True,
                                    timeout=30).stdout.splitlines()
        trace, allow = 0x7ff00000, 0x7fff0000                   # SECCOMP_RET_TRACE, SECCOMP_RET_ALLOW
        self.assertEqual(output[0], 'floor 960 length 5')
        rows = [line.split() for line in output[1:]]
        calls = [row for row in rows if row[0] == 'call']
        self.assertEqual(len(calls), 3 * 14)
        for _, number, descriptor, verdict in calls:
            low_word = int(descriptor, 16) & 0xffffffff          # the kernel reads the low word
            with self.subTest(call=number, descriptor=descriptor):
                self.assertEqual(int(verdict), trace if low_word >= 960 else allow)
        self.assertEqual({row[1] for row in calls}, {'206', '207', '212'})
        self.assertEqual(rows[-3:], [['sendmsg', str(trace)], ['openat', str(trace)], ['close', str(allow)]])


if __name__ == '__main__':
    unittest.main()
