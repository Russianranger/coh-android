"""PRoot patch 0004: ioctl(2) is traced only for the commands PRoot acts on (PROOT_IOCTL_COMMANDS_ONLY=1).

The patch adds a self-contained header with the seccomp statements. This test takes that header out
of the patch, compiles a small harness with the host compiler and runs the statements through a
minimal BPF interpreter: the handled commands reach the tracer, every other ioctl is allowed, and a
call that is not ioctl continues to the statements after the block with its number intact.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'android/native/proot/0004-ioctl-command-filter.patch'
HANDLED = (0x8933, 0x5404, 0x802C542A, 0x402C542B, 0x402C542C, 0x402C542D, 0x40049409)

HARNESS = r'''
#include "ioctl_filter.h"
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
		case BPF_JMP + BPF_JA + BPF_K:
			pc += 1 + s->k; break;
		case BPF_RET + BPF_K:
			return (long) s->k;
		default:
			return -3;
		}
	}
}

int main(void)
{
	enum { NR_IOCTL = 29, NR_OPENAT = 56, NR_CLOSE = 57, FLAG = 1 };
	struct sock_filter program[LENGTH_TRACE_IOCTL + 4];
	size_t length = 0, i;
	program[length++] = (struct sock_filter) BPF_STMT(BPF_LD + BPF_W + BPF_ABS, offsetof(struct seccomp_data, nr));
	length += ioctl_filter_statements(program + length, NR_IOCTL, FLAG);
	program[length++] = (struct sock_filter) BPF_JUMP(BPF_JMP + BPF_JEQ + BPF_K, NR_OPENAT, 0, 1);
	program[length++] = (struct sock_filter) BPF_STMT(BPF_RET + BPF_K, SECCOMP_RET_TRACE);
	program[length++] = (struct sock_filter) BPF_STMT(BPF_RET + BPF_K, SECCOMP_RET_ALLOW);
	printf("count %zu length %zu\n", (size_t) IOCTL_FILTER_COMMAND_COUNT, (size_t) LENGTH_TRACE_IOCTL);
	for (i = 0; i < IOCTL_FILTER_COMMAND_COUNT; i++) {
		struct seccomp_data data = { .nr = NR_IOCTL, .arch = AUDIT_ARCH_AARCH64 };
		data.args[0] = 3; data.args[1] = ioctl_filter_commands[i];
		printf("handled 0x%08x %ld\n", ioctl_filter_commands[i], run(program, length, &data));
		data.args[1] |= 0xffffffff00000000ULL;                  /* the kernel reads the low word */
		printf("handled-high 0x%08x %ld\n", ioctl_filter_commands[i], run(program, length, &data));
	}
	/* GPU (KGSL type 0x09, DRM 'd'), FIONREAD, TCGETS, TIOCGWINSZ, TCSETS, neighbours of handled ones.  */
	const uint64_t others[] = { 0xC0400945, 0xC0200907, 0x40086409, 0xC0106443, 0x541B, 0x5401, 0x5413, 0x5402,
				    0x5403, 0x8932, 0x8934, 0x802C542B, 0x402C542A, 0x40049408, 0, 0xFFFFFFFF,
				    0x893300000000ULL };
	for (i = 0; i < sizeof(others) / sizeof(others[0]); i++) {
		struct seccomp_data data = { .nr = NR_IOCTL, .arch = AUDIT_ARCH_AARCH64 };
		data.args[1] = others[i];
		printf("other 0x%llx %ld\n", (unsigned long long) others[i], run(program, length, &data));
	}
	struct seccomp_data openat = { .nr = NR_OPENAT }, close_call = { .nr = NR_CLOSE };
	openat.args[1] = 0x8933; close_call.args[1] = 0x8933;         /* not ioctl: the argument is not a command */
	printf("openat %ld\nclose %ld\n", run(program, length, &openat), run(program, length, &close_call));
	return 0;
}
'''


def added_file(patch, name):
    """The text of a file the patch creates."""
    block = re.search(r'^diff --git a/%s b/%s\n.*?(?=^diff --git |\Z)' % (re.escape(name), re.escape(name)),
                      patch, re.M | re.S)
    assert block is not None and '\n--- /dev/null\n' in block.group(0)
    lines = block.group(0).split('\n@@', 1)[1].split('\n')[1:]
    assert all(line.startswith('+') for line in lines if line)
    return '\n'.join(line[1:] for line in lines)


class ProotIoctlFilterTest(unittest.TestCase):
    def test_patch_shape(self):
        patch = PATCH.read_text()
        self.assertEqual(sorted(re.findall(r'^diff --git a/(\S+) ', patch, re.M)),
                         ['src/syscall/ioctl_filter.h', 'src/syscall/seccomp.c'])
        self.assertIn('getenv("PROOT_IOCTL_COMMANDS_ONLY")', patch)
        self.assertIn('+	       + nb_extra_statements)', patch)
        self.assertIn('+					nb_extra_statements += LENGTH_TRACE_IOCTL - LENGTH_TRACE_SYSCALL;', patch)
        header = added_file(patch, 'src/syscall/ioctl_filter.h')
        self.assertEqual(tuple(int(value, 16) for value in re.findall(r'^\t(0x[0-9A-Fa-f]+),', header, re.M)), HANDLED)

    @unittest.skipUnless(shutil.which('gcc') or shutil.which('cc'), 'no host C compiler')
    def test_statements_trace_handled_commands_only(self):
        compiler = shutil.which('gcc') or shutil.which('cc')
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / 'ioctl_filter.h').write_text(added_file(PATCH.read_text(), 'src/syscall/ioctl_filter.h'))
            (work / 'harness.c').write_text(HARNESS)
            subprocess.run([compiler, '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-O1', '-o', str(work / 'harness'),
                            str(work / 'harness.c')], check=True, cwd=work, timeout=120)
            output = subprocess.run([str(work / 'harness')], check=True, capture_output=True, text=True,
                                    timeout=30).stdout.splitlines()
        trace, allow = 0x7ff00000, 0x7fff0000                   # SECCOMP_RET_TRACE, SECCOMP_RET_ALLOW
        self.assertEqual(output[0], 'count %d length %d' % (len(HANDLED), len(HANDLED) + 4))
        rows = [line.split() for line in output[1:]]
        handled = [row for row in rows if row[0] in ('handled', 'handled-high')]
        self.assertEqual(len(handled), 2 * len(HANDLED))
        self.assertTrue(all(int(row[2]) == trace + 1 for row in handled), handled)
        others = [row for row in rows if row[0] == 'other']
        self.assertEqual(len(others), 17)
        self.assertTrue(all(int(row[2]) == allow for row in others), others)
        self.assertEqual(rows[-2:], [['openat', str(trace)], ['close', str(allow)]])


if __name__ == '__main__':
    unittest.main()
