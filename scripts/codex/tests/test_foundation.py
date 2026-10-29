"""Exercise host-wrapper boundaries with disposable Git repos; no external calls.

Tool shims make command routing deterministic. These tests do not qualify the
real COH suites, OS package installation, network access, or device behavior.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]


def run(*args, cwd=None, env=None):
    return subprocess.run(args, cwd=cwd, env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=45)


class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="coh foundation ")
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.repo = self.work / "source repo"
        self.repo.mkdir()
        self.env = os.environ.copy()
        for key in ("ARMPORT_SERVER_BASELINE_ROOT", "COH_CODEX_CACHE_DIR", "GIT_DIR",
                    "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CONFIG_COUNT", "PYTHONHOME"):
            self.env.pop(key, None)
        self.env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
                        GIT_AUTHOR_NAME="Foundation Test", GIT_COMMITTER_NAME="Foundation Test",
                        GIT_AUTHOR_EMAIL="foundation@example.invalid",
                        GIT_COMMITTER_EMAIL="foundation@example.invalid",
                        PYTHONDONTWRITEBYTECODE="1")
        self.git("init", "-q")
        self.write(".gitignore", "__pycache__/\n*.pyc\n")
        self.write("tools/fixture.txt", "historical source\n")
        self.write("android/guest/fixture.txt", "historical guest\n")
        self.git("add", ".")
        self.git("commit", "-q", "-m", "historical baseline")
        self.pin = self.git("rev-parse", "HEAD").stdout.strip()
        self.write("armport/app/server_package.py", f"BASELINE_COMMIT = {self.pin!r}\n")
        self.write(".github/workflows/armport-build.yml", 'run: pip install "pillow==12.0.0"\n')
        for source in SCRIPTS.glob("*.sh"):
            self.write("scripts/codex/" + source.name, source.read_text(), executable=True)
        self.git("add", ".")
        self.git("commit", "-q", "-m", "current source")
        self.cache = self.work / "external cache"
        self.env["COH_CODEX_CACHE_DIR"] = str(self.cache)
        self.venv = self.cache / "venv"
        (self.venv / "bin").mkdir(parents=True)
        (self.venv / "pyvenv.cfg").write_text("# disposable wrapper fixture\n")
        (self.venv / "bin/python").symlink_to(sys.executable)
        self.support = self.work / "python support"
        (self.support / "PIL").mkdir(parents=True)
        (self.support / "PIL/__init__.py").write_text('__version__ = "12.0.0"\nImage = object()\n')
        dist = self.support / "Pillow-12.0.0.dist-info"
        dist.mkdir()
        (dist / "METADATA").write_text("Metadata-Version: 2.1\nName: Pillow\nVersion: 12.0.0\n")
        self.env["PYTHONPATH"] = str(self.support)
        self.bin = self.work / "fixture bin"
        self.bin.mkdir()
        self.env["PATH"] = str(self.bin) + os.pathsep + self.env["PATH"]
        self.env["FOUNDATION_GH_LOG"] = str(self.work / "gh-requests.jsonl")
        for command in ("cmake", "ninja", "cc", "c++", "clang", "java", "javac", "convert",
                        "identify", "pkg-config", "unzip", "xz", "rg"):
            self.executable(command, '#!/bin/sh\nprintf "fixture tool 1\\n"\n')
        self.executable("curl", '#!/bin/sh\nprintf "%s" "${FOUNDATION_HTTP_STATUS:-200}"\n')
        self.executable("gh", """#!/usr/bin/env python3
import json, os, sys
with open(os.environ['FOUNDATION_GH_LOG'], 'a') as stream:
    stream.write(json.dumps({'args': sys.argv[1:], 'debug': os.environ.get('GH_DEBUG')}) + '\\n')
print('[]')
raise SystemExit(int(os.environ.get('FOUNDATION_GH_EXIT', '0')))
""")

    def write(self, relative, text, executable=False):
        path = self.repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        if executable:
            path.chmod(0o755)
        return path

    def executable(self, name, text):
        path = self.bin / name
        path.write_text(text)
        path.chmod(0o755)

    def git(self, *args):
        result = run("git", *args, cwd=self.repo, env=self.env)
        self.assertEqual(result.returncode, 0, result.stdout)
        return result

    def script(self, name, *args):
        return run("bash", str(self.repo / "scripts/codex" / name), *args,
                   cwd=self.work, env=self.env)

    def source_common(self, expression):
        return run("bash", "-c", 'source "$1"; ' + expression,
                   "fixture", str(self.repo / "scripts/codex/common.sh"),
                   cwd=self.work, env=self.env)

    def setup_ready(self):
        result = self.script("setup.sh")
        self.assertEqual(result.returncode, 0, result.stdout)
        return self.cache / "baselines" / self.pin

    def isolate_host_tools(self, *missing):
        # Keep missing tools absent even when the machine running these tests
        # happens to have them. System package commands are always intercepted.
        for name in ("bash", "python3", "git", "dirname", "mkdir", "mktemp",
                     "rm", "mv", "uname", "df", "timeout", "env", "cat"):
            path = self.bin / name
            if not path.exists():
                path.symlink_to(shutil.which(name))
        for name in missing:
            (self.bin / name).unlink(missing_ok=True)
        self.env["PATH"] = str(self.bin)
        self.env["FOUNDATION_PACKAGE_LOG"] = str(self.work / "package-requests.jsonl")
        package_stub = f"#!{sys.executable}\n" + """import json, os, sys
from pathlib import Path
name = Path(sys.argv[0]).name
with open(os.environ['FOUNDATION_PACKAGE_LOG'], 'a') as stream:
    stream.write(json.dumps([name, *sys.argv[1:]]) + '\\n')
if name == 'id':
    print(os.environ.get('FOUNDATION_UID', '1000'))
elif name == 'apt-cache':
    package = sys.argv[-1]
    candidate = '(none)' if package == os.environ.get('FOUNDATION_UNAVAILABLE_PACKAGE') else '1.0'
    print(f'{package}:\\n  Candidate: {candidate}')
elif name == 'apt-get' and os.environ.get('FOUNDATION_UID') == '0':
    if 'install' in sys.argv:
        for tool in os.environ.get('FOUNDATION_INSTALL_TOOLS', '').split():
            path = Path(os.environ['PATH']) / tool
            path.write_text('#!/bin/sh\\nprintf "fixture installed tool 1\\\\n"\\n')
            path.chmod(0o755)
else:
    raise SystemExit(99)
"""
        for name in ("id", "sudo", "apt-get", "apt-cache", "dpkg-query"):
            self.executable(name, package_stub)

    def package_calls(self):
        path = Path(self.env["FOUNDATION_PACKAGE_LOG"])
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def python_without_venv_support(self):
        (self.bin / "python3").unlink(missing_ok=True)
        self.env["FOUNDATION_VENV_PROBE_LOG"] = str(self.work / "venv-probe.txt")
        self.executable("python3", f"#!{sys.executable}\n" + """import os, sys
from pathlib import Path
if len(sys.argv) > 2 and sys.argv[1] == '-c' and 'ensurepip' in sys.argv[2]:
    Path(os.environ['FOUNDATION_VENV_PROBE_LOG']).write_text('base Python has no ensurepip')
    raise SystemExit(1)
os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
""")

    def test_install_system_reuses_existing_tools_without_admin_or_apt(self):
        self.isolate_host_tools()
        first = self.script("setup.sh", "--install-system")
        self.assertEqual(first.returncode, 0, first.stdout)
        second = self.script("setup.sh", "--install-system")
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertEqual(self.package_calls(), [])
        self.assertTrue((self.cache / "baselines" / self.pin / ".git").is_dir())

    def test_existing_venv_does_not_require_base_python_ensurepip(self):
        self.isolate_host_tools()
        self.python_without_venv_support()
        result = self.script("setup.sh", "--install-system")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertFalse(Path(self.env["FOUNDATION_VENV_PROBE_LOG"]).exists())
        self.assertEqual(self.package_calls(), [])

    def test_missing_tool_without_admin_is_actionable_and_preserves_venv(self):
        self.isolate_host_tools("clang")
        result = self.script("setup.sh", "--install-system")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Missing developer tools: clang", result.stdout)
        self.assertIn("root or passwordless sudo is unavailable", result.stdout)
        self.assertTrue((self.venv / "pyvenv.cfg").is_file())
        self.assertFalse(any(call[0] == "apt-get" for call in self.package_calls()))

    def test_default_setup_reports_missing_tool_without_package_operations(self):
        self.isolate_host_tools("clang")
        result = self.script("setup.sh")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Missing developer tools: clang", result.stdout)
        self.assertEqual(self.package_calls(), [])

    def test_optional_apt_installs_only_the_missing_tool(self):
        self.isolate_host_tools("clang")
        self.env.update(FOUNDATION_UID="0", FOUNDATION_INSTALL_TOOLS="clang")
        result = self.script("setup.sh", "--install-system")
        self.assertEqual(result.returncode, 0, result.stdout)
        installs = [call for call in self.package_calls() if call[:2] == ["apt-get", "install"]]
        self.assertEqual(installs, [["apt-get", "install", "-y", "--no-install-recommends", "clang"]])

    def test_unavailable_jdk17_does_not_select_another_java_or_repository(self):
        self.isolate_host_tools("java", "javac")
        self.env.update(FOUNDATION_UID="0", FOUNDATION_UNAVAILABLE_PACKAGE="openjdk-17-jdk-headless")
        result = self.script("setup.sh", "--install-system")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Package unavailable in configured repositories: openjdk-17-jdk-headless", result.stdout)
        self.assertIn("Prepare JDK 17 through environment setup", result.stdout)
        self.assertFalse(any(call[:2] == ["apt-get", "install"] for call in self.package_calls()))
        self.assertEqual([call for call in self.package_calls() if call[0] == "apt-cache"],
                         [["apt-cache", "policy", "openjdk-17-jdk-headless"]])

    def test_new_venv_requires_support_without_attempting_privileged_install(self):
        self.isolate_host_tools()
        self.python_without_venv_support()
        shutil.rmtree(self.venv)
        result = self.script("setup.sh")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Python venv/ensurepip", result.stdout)
        self.assertFalse(self.venv.exists())
        self.assertEqual(self.package_calls(), [])

    def test_sourcing_common_is_read_only_and_does_not_import_project(self):
        self.write("armport/app/server_package.py", f"BASELINE_COMMIT = {self.pin!r}\nraise RuntimeError('must not import')\n")
        nonexistent = self.work / "absent cache"
        self.env["COH_CODEX_CACHE_DIR"] = str(nonexistent)
        result = self.source_common('printf "%s %s" "$COH_CODEX_BASELINE_COMMIT" "$COH_CODEX_PILLOW_VERSION"')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout, self.pin + " 12.0.0")
        self.assertFalse(nonexistent.exists())

    def test_conflicting_pillow_pins_are_rejected(self):
        self.write(".github/workflows/armport-build.yml", "pillow==12.0.0 pillow==11.0.0\n")
        result = self.script("doctor.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Expected one Pillow", result.stdout)

    def test_setup_creates_independent_exact_checkout_and_reuses_it(self):
        baseline = self.setup_ready()
        self.assertTrue((baseline / ".git").is_dir())
        self.assertEqual(run("git", "-C", str(baseline), "rev-parse", "HEAD", env=self.env).stdout.strip(), self.pin)
        self.assertEqual(run("git", "-C", str(baseline), "status", "--porcelain", env=self.env).stdout, "")
        second = self.script("setup.sh")
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertNotIn("From ", second.stdout)
        self.assertEqual(self.git("status", "--porcelain").stdout, "")
        self.assertEqual(list(baseline.parent.glob(".coh-baseline.*")), [])

    def test_dirty_baseline_is_preserved(self):
        baseline = self.setup_ready()
        sentinel = baseline / "important-uncommitted.txt"
        sentinel.write_text("keep this work")
        result = self.script("setup.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("modified or untracked", result.stdout)
        self.assertEqual(sentinel.read_text(), "keep this work")

    def test_wrong_baseline_head_is_preserved(self):
        baseline = self.setup_ready()
        self.env["ARMPORT_SERVER_BASELINE_ROOT"] = str(self.repo)
        before = self.git("rev-parse", "HEAD").stdout
        result = self.script("setup.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Baseline HEAD must be", result.stdout)
        self.assertEqual(self.git("rev-parse", "HEAD").stdout, before)
        self.assertTrue(baseline.is_dir())

    def test_symlink_baseline_is_rejected_without_changing_target(self):
        baseline = self.setup_ready()
        alias = self.work / "baseline alias"
        alias.symlink_to(baseline, target_is_directory=True)
        self.env["ARMPORT_SERVER_BASELINE_ROOT"] = str(alias)
        result = self.script("setup.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a symlink", result.stdout)
        self.assertTrue(alias.is_symlink())
        self.assertTrue((baseline / "tools/fixture.txt").is_file())

    def test_invalid_venv_is_preserved(self):
        (self.venv / "pyvenv.cfg").unlink()
        sentinel = self.venv / "keep.txt"
        sentinel.write_text("keep")
        result = self.script("setup.sh")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(sentinel.read_text(), "keep")

    def test_skipping_required_baseline_is_explicit_partial_setup(self):
        result = self.script("setup.sh", "--skip-baseline")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("PARTIAL SETUP", result.stdout)
        self.assertFalse((self.cache / "baselines" / self.pin).exists())

    def test_activation_bounds_compilers_and_preserves_proxy(self):
        self.env.update(CMAKE_BUILD_PARALLEL_LEVEL="99", HTTPS_PROXY="http://fixture-proxy.invalid:8080")
        result = self.source_common('coh_activate; printf "%s|%s|%s" "$CMAKE_BUILD_PARALLEL_LEVEL" "$HTTPS_PROXY" "$ARMPORT_SERVER_BASELINE_ROOT"')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout, f"2|http://fixture-proxy.invalid:8080|{self.cache / 'baselines' / self.pin}")

    def test_doctor_missing_baseline_reports_setup_failure(self):
        result = self.script("doctor.sh", "--local")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("LOCAL SETUP INCOMPLETE", result.stdout)
        self.assertNotIn("Selected local tests passed", result.stdout)

    def test_doctor_local_does_not_call_github(self):
        self.setup_ready()
        result = self.script("doctor.sh", "--local")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertFalse(Path(self.env["FOUNDATION_GH_LOG"]).exists())

    def test_doctor_github_only_reads_and_disables_debug_output(self):
        self.setup_ready()
        self.env["GH_DEBUG"] = "api"
        self.env["GH_TOKEN"] = "fixture-secret-must-not-appear"
        result = self.script("doctor.sh", "--github")
        self.assertEqual(result.returncode, 0, result.stdout)
        calls = [json.loads(line) for line in Path(self.env["FOUNDATION_GH_LOG"]).read_text().splitlines()]
        self.assertEqual([c["args"] for c in calls], [["api", "repos/Russianranger/coh-android"],
                          ["api", "repos/Russianranger/coh-android/actions/workflows"]])
        self.assertTrue(all(c["debug"] == "" for c in calls))
        self.assertNotIn(self.env["GH_TOKEN"], result.stdout)

    def test_public_rate_limit_does_not_override_authenticated_success(self):
        self.setup_ready()
        self.env["FOUNDATION_HTTP_STATUS"] = "403"
        result = self.script("doctor.sh", "--github")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("public API probe returned HTTP 403", result.stdout)

    def test_github_read_failure_has_separate_exit_code(self):
        self.setup_ready()
        self.env["FOUNDATION_GH_EXIT"] = "1"
        result = self.script("doctor.sh", "--github")
        self.assertEqual(result.returncode, 3, result.stdout)
        self.assertIn("GITHUB READS UNAVAILABLE", result.stdout)

    def test_check_refuses_zero_discovered_tests(self):
        self.setup_ready()
        self.write("armport/tests/test_empty.py", "# no test cases\n")
        result = self.script("check.sh", "--armport")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("no tests discovered", result.stdout)
        self.assertNotIn("Selected local tests passed", result.stdout)

    def test_failed_suite_prevents_later_groups_and_success_claim(self):
        self.setup_ready()
        self.write("armport/tests/test_failure.py", "import unittest\nclass Failure(unittest.TestCase):\n    def test_failure(self):\n        self.fail('intentional regression')\n")
        result = self.script("check.sh", "--all")
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("intentional regression", result.stdout)
        self.assertNotIn("Selected local tests passed", result.stdout)
        self.assertNotIn("MISSING: tools/android", result.stdout)

    def test_all_runs_four_groups_with_bounded_compiler_environment(self):
        self.setup_ready()
        paths = ["armport/tests/test_core.py"] + ["tools/android/interactive/" + name for name in
                 ("test_saved_map_startup.py", "test_character_zoning.py", "test_character_monorail.py")]
        for path in paths:
            self.write(path, "import os, unittest\nclass Local(unittest.TestCase):\n    def test_environment(self):\n        self.assertEqual(os.environ['CMAKE_BUILD_PARALLEL_LEVEL'], '2')\n        self.assertTrue(os.environ['ARMPORT_SERVER_BASELINE_ROOT'])\n")
        result = self.script("check.sh", "--all")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(result.stdout.count("Ran 1 test"), 4)

    def test_ci_status_is_scoped_to_exact_head_or_explicit_run(self):
        result = self.script("ci-status.sh")
        self.assertEqual(result.returncode, 0, result.stdout)
        head = self.git("rev-parse", "HEAD").stdout.strip()
        calls = [json.loads(line)["args"] for line in Path(self.env["FOUNDATION_GH_LOG"]).read_text().splitlines()]
        self.assertEqual(calls[0][:2], ["run", "list"])
        self.assertEqual(calls[0][calls[0].index("--commit") + 1], head)
        result = self.script("ci-status.sh", "12345")
        self.assertEqual(result.returncode, 0, result.stdout)
        calls = [json.loads(line)["args"] for line in Path(self.env["FOUNDATION_GH_LOG"]).read_text().splitlines()]
        self.assertEqual(calls[1][:3], ["run", "view", "12345"])

    def test_help_and_invalid_arguments_do_not_call_github(self):
        for name in ("setup.sh", "doctor.sh", "check.sh", "ci-status.sh"):
            self.assertEqual(self.script(name, "--help").returncode, 0, name)
            self.assertEqual(self.script(name, "--invalid").returncode, 2, name)
        self.assertFalse(Path(self.env["FOUNDATION_GH_LOG"]).exists())


if __name__ == "__main__":
    unittest.main()
