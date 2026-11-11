"""apt_install.sh: the runner's archive first, a signed mirror when it cannot be reached.

Builds 43038600688 to 43054851770 (2026-11-11) all stopped because ports.ubuntu.com did
not resolve on GitHub's ARM64 runners. The script is run here against a private copy of
an apt configuration with stand-ins for apt-get, getent and timeout.
"""
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'apt_install.sh'
ARM_SOURCES = ('Types: deb\nURIs: http://ports.ubuntu.com/ubuntu-ports/\nSuites: noble noble-updates\n'
               'Components: main universe\nSigned-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\n')
X86_MIRRORS = ('http://azure.archive.ubuntu.com/ubuntu/\tpriority:1\nhttps://archive.ubuntu.com/ubuntu/\tpriority:2\n'
               'https://security.ubuntu.com/ubuntu/\tpriority:3\n')


class AptInstall(unittest.TestCase):
    def run_script(self, sources, *, dead=(), failing=(), other=None):
        """Run the script; `dead` hosts do not resolve, `failing` hosts fail in apt-get."""
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root, tools = base / 'apt', base / 'bin'
            (root / 'sources.list.d').mkdir(parents=True)
            tools.mkdir()
            for name, text in sources.items():
                (root / name).write_text(text)
            if other:
                (root / 'sources.list.d' / 'other.list').write_text(other)
            log = base / 'log'
            # apt-get: record the call and the sources it saw; fail when they name a failing host.
            (tools / 'apt-get').write_text(
                '#!/bin/bash\n'
                'echo "apt-get $*" >> "$LOG"\n'
                'cat "$APT_INSTALL_ROOT"/sources.list.d/* "$APT_INSTALL_ROOT"/apt-mirrors.txt 2>/dev/null > "$LOG.seen"\n'
                'for host in $FAILING; do grep -q "//$host/" "$LOG.seen" && exit 100; done\n'
                'exit 0\n')
            (tools / 'getent').write_text(
                '#!/bin/bash\nfor host in $DEAD; do [ "$2" = "$host" ] && exit 2; done\nexit 0\n')
            (tools / 'timeout').write_text('#!/bin/bash\nshift\nexec "$@"\n')
            for tool in tools.iterdir():
                tool.chmod(tool.stat().st_mode | stat.S_IXUSR)
            environment = dict(os.environ, PATH=str(tools) + os.pathsep + os.environ['PATH'], LOG=str(log),
                               APT_INSTALL_ROOT=str(root), APT_INSTALL_SUDO='', DEAD=' '.join(dead),
                               FAILING=' '.join(failing))
            done = subprocess.run(['bash', str(SCRIPT), 'imagemagick'], env=environment, capture_output=True,
                                  text=True, timeout=60)
            calls = log.read_text().splitlines() if log.exists() else []
            seen = Path(str(log) + '.seen').read_text() if calls else ''
            after = {name: (root / name).read_text() for name in sources}
            return done, calls, seen, after

    def test_reachable_archive_is_used_unchanged(self):
        done, calls, seen, after = self.run_script({'sources.list.d/ubuntu.sources': ARM_SOURCES})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(calls), 2)
        self.assertIn('install -y --no-install-recommends', calls[1])
        self.assertTrue(calls[1].endswith(' imagemagick'))
        self.assertIn('ports.ubuntu.com', seen)
        self.assertNotIn('::notice', done.stdout)

    def test_unresolvable_ports_host_goes_straight_to_a_mirror(self):
        done, calls, seen, after = self.run_script({'sources.list.d/ubuntu.sources': ARM_SOURCES},
                                                    dead=('ports.ubuntu.com',))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len(calls), 2)                     # no eight minutes against the dead host
        self.assertIn('URIs: https://mirrors.mit.edu/ubuntu-ports/', seen)
        self.assertNotIn('ports.ubuntu.com', seen)
        self.assertIn('Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg', seen)
        self.assertIn('::notice title=apt mirror::Packages came from mirrors.mit.edu', done.stdout)
        self.assertEqual(after['sources.list.d/ubuntu.sources'], ARM_SOURCES)      # put back

    def test_next_mirror_when_one_is_down_or_fails(self):
        done, calls, seen, after = self.run_script(
            {'sources.list.d/ubuntu.sources': ARM_SOURCES}, dead=('ports.ubuntu.com', 'mirrors.mit.edu'),
            failing=('mirrors.ocf.berkeley.edu',))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('https://ftp.tu-chemnitz.de/pub/linux/ubuntu-ports/', seen)
        self.assertIn('mirror mirrors.mit.edu does not resolve', done.stderr)
        self.assertIn('mirror mirrors.ocf.berkeley.edu failed with 100', done.stderr)

    def test_install_error_on_a_reachable_archive_also_tries_mirrors(self):
        done, calls, seen, after = self.run_script({'sources.list.d/ubuntu.sources': ARM_SOURCES},
                                                    failing=('ports.ubuntu.com',))
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('mirrors.mit.edu', seen)

    def test_every_route_failing_reports_failure_and_restores(self):
        done, calls, seen, after = self.run_script(
            {'sources.list.d/ubuntu.sources': ARM_SOURCES},
            failing=('ports.ubuntu.com', 'mirrors.mit.edu', 'mirrors.ocf.berkeley.edu', 'ftp.tu-chemnitz.de'))
        self.assertEqual(done.returncode, 100)
        self.assertEqual(after['sources.list.d/ubuntu.sources'], ARM_SOURCES)

    def test_x86_mirror_list_and_other_vendors(self):
        other = 'deb [arch=amd64] https://packages.microsoft.com/ubuntu/24.04/prod noble main\n'
        done, calls, seen, after = self.run_script(
            {'apt-mirrors.txt': X86_MIRRORS}, dead=('azure.archive.ubuntu.com',), other=other)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(seen.count('https://mirrors.mit.edu/ubuntu/'), 3)
        self.assertIn('packages.microsoft.com/ubuntu/24.04/prod', seen)             # not an archive host
        self.assertEqual(after['apt-mirrors.txt'], X86_MIRRORS)

    def test_no_package_is_a_usage_error(self):
        done = subprocess.run(['bash', str(SCRIPT)], capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 2)


if __name__ == '__main__':
    unittest.main()
