#!/usr/bin/env python3
"""Build the unchanged auth provider against pinned public Android libcrypto.

No Android-private crypto API, prebuilt binary, secret or server endpoint is used.
The output contains a static provider, link-tested shared library and executable
of the existing auth checks. Cross-compilation is never reported as execution.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
AUTH = HERE.parent
NATIVE = AUTH.parents[1]
ABIS = {
    "arm64-v8a": ("android-arm64", "aarch64-linux-android", "AArch64"),
    "x86_64": ("android-x86_64", "x86_64-linux-android", "Advanced Micro Devices X86-64"),
}
OPTIONS = ["no-shared", "no-module", "no-dso", "no-engine", "no-tests",
           "no-docs", "no-apps", "-DOPENSSL_NO_AUTOLOAD_CONFIG",
           "--prefix=/coh-native/openssl", "--openssldir=/coh-native/openssl/ssl",
           "--libdir=lib"]


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(command, *, cwd=None, env=None, log=None):
    command = [str(value) for value in command]
    result = subprocess.run(command, cwd=cwd, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if log:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command!r}\n"
                           + result.stdout[-12000:])
    return result.stdout


def source_archive(args, pin):
    if args.source_archive:
        archive = args.source_archive.resolve()
    else:
        args.cache.mkdir(parents=True, exist_ok=True)
        archive = args.cache / pin["archive"]
        if not archive.exists():
            temporary = archive.with_suffix(".download")
            try:
                run(["curl", "--fail", "--location", "--retry", "2",
                     "--connect-timeout", "20", "--max-time", "300",
                     pin["url"], "--output", temporary])
                if digest(temporary) != pin["sha256"]:
                    raise ValueError("Downloaded OpenSSL archive SHA256 mismatch")
                temporary.replace(archive)
            finally:
                temporary.unlink(missing_ok=True)
    if not archive.is_file() or digest(archive) != pin["sha256"]:
        raise ValueError("OpenSSL archive must match the committed source pin")
    return archive


def extract(archive, target, pin):
    # No links or traversal are needed for the official source distribution.
    # Validate everything before writing, rather than trusting tar paths.
    prefix = "openssl-" + pin["version"]
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or path.parts[0] != prefix:
                raise ValueError("Unexpected source archive member")
            if not (member.isdir() or member.isfile()):
                raise ValueError("Links and special files are not admitted")
        tar.extractall(target, filter="data")
    source = target / prefix
    if digest(source / pin["license_file"]) != pin["license_sha256"]:
        raise ValueError("OpenSSL license differs from the reviewed source")
    return source


def build(args, archive, pin, abi):
    target, triple, machine = ABIS[abi]
    output = args.output / abi
    work = args.output / "build" / abi
    if work.exists() or output.exists():
        # A complete receipt is required for intentional reuse. Never reuse a
        # partially built or stale dependency simply because libcrypto exists.
        if not args.rebuild:
            raise ValueError(f"Output already exists for {abi}; use --rebuild or a fresh output directory")
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(output, ignore_errors=True)
    source = extract(archive, work / "source", pin)
    output.mkdir(parents=True)
    toolchain = args.ndk / "toolchains/llvm/prebuilt/linux-x86_64/bin"
    compiler = toolchain / f"{triple}{args.api}-clang"
    if not compiler.is_file():
        raise ValueError(f"Missing NDK Linux compiler {compiler}")
    env = dict(os.environ)
    # Do not inherit host compiler overrides or loader/provider configuration.
    for name in ("CC", "CXX", "AR", "AS", "LD", "RANLIB", "CFLAGS", "CPPFLAGS",
                 "LDFLAGS", "CROSS_COMPILE", "CROSS_SYSROOT", "OPENSSL_CONF", "OPENSSL_MODULES"):
        env.pop(name, None)
    env["ANDROID_NDK_ROOT"] = str(args.ndk)
    env["PATH"] = str(toolchain) + os.pathsep + os.environ.get("PATH", "")
    env["LC_ALL"] = "C"
    env["SOURCE_DATE_EPOCH"] = str(int(datetime.datetime.fromisoformat(
        pin["release_date"]).replace(tzinfo=datetime.timezone.utc).timestamp()))
    configure = ["perl", "Configure", target, f"-D__ANDROID_API__={args.api}", *OPTIONS,
                 f"-ffile-prefix-map={work}=openssl-build", "-fPIC"]
    run(configure, cwd=source, env=env, log=output / "configure.log")
    run(["make", f"-j{args.jobs}", "build_libs"], cwd=source, env=env,
        log=output / "openssl-build.log")
    staging = work / "install"
    run(["make", f"DESTDIR={staging}", "install_dev"], cwd=source, env=env,
        log=output / "openssl-install.log")
    install = staging / "coh-native/openssl"
    shutil.copytree(install / "include", output / "include")
    (output / "lib").mkdir()
    shutil.copy2(install / "lib/libcrypto.a", output / "lib/libcrypto.a")
    shutil.copy2(source / pin["license_file"], output / "OPENSSL-LICENSE.txt")
    return finish(args, pin, abi, output, work, env)


def finish(args, pin, abi, output, work, env):
    """Compile/link the adapter, keeping an already built libcrypto unchanged."""
    target, triple, machine = ABIS[abi]
    toolchain = args.ndk / "toolchains/llvm/prebuilt/linux-x86_64/bin"
    compiler = toolchain / f"{triple}{args.api}-clang"
    flags = ["-std=c99", "-Wall", "-Wextra", "-Werror", "-O2", "-fPIC",
             "-fvisibility=hidden", "-I" + str(NATIVE / "include"),
             "-I" + str(output / "include"),
             f"-ffile-prefix-map={NATIVE}=native-android"]
    objects = []
    for item in (AUTH / "coh_auth.c", AUTH / "coh_auth_openssl.c",
                 NATIVE / "src/coh_blowfish.c", NATIVE / "protocol/coh_protocol.c"):
        obj = work / (item.stem + ".o")
        run([compiler, *flags, "-c", item, "-o", obj])
        objects.append(obj)
    # Only provider object belongs in this archive. The integrated build owns
    # the accepted auth, protocol and Blowfish modules already.
    run([toolchain / "llvm-ar", "rcsD", output / "lib/libcoh_auth_android_crypto.a", objects[1]])
    crypto = output / "lib/libcrypto.a"
    link = ["-Wl,-z,defs", "-Wl,-z,max-page-size=16384", "-Wl,--exclude-libs,ALL", "-ldl"]
    shared = output / "lib/libcoh_auth_android_check.so"
    run([compiler, "-shared", *objects, crypto, *link, "-o", shared])
    executable = output / "test_auth_android"
    # Execute the existing substantial suite unchanged on Android via adb.
    run([compiler, *flags, "-DCOH_AUTH_TEST_OPENSSL", AUTH / "tests/test_auth.c",
         *objects, crypto, *link, "-o", executable])
    inspection = run([toolchain / "llvm-readelf", "-h", "-d", shared])
    if machine not in inspection or "libcrypto.so" in inspection or "libssl.so" in inspection:
        raise ValueError("Android ELF architecture or static-crypto dependency check failed")
    (output / "elf-inspection.txt").write_text(
        "\n".join(line.rstrip() for line in inspection.splitlines()) + "\n")
    ndk_properties = (args.ndk / "source.properties").read_text()
    ndk_revision = next(line.split("=", 1)[1].strip() for line in ndk_properties.splitlines()
                        if line.startswith("Pkg.Revision"))
    files = [crypto, output / "lib/libcoh_auth_android_crypto.a", shared, executable]
    receipt = {
        "status": "PASS", "scope": "Android compile and link qualification only",
        "abi": abi, "api": args.api, "ndk_revision": ndk_revision,
        "compiler": run([compiler, "--version"]).splitlines()[0],
        "openssl_version": pin["version"], "openssl_archive_sha256": pin["sha256"],
        "openssl_license": pin["license"], "openssl_license_sha256": pin["license_sha256"],
        "source_pin_sha256": digest(HERE / "openssl-source.json"),
        "configure_options": [target, f"-D__ANDROID_API__={args.api}", *OPTIONS,
                              f"-ffile-prefix-map={work}=openssl-build", "-fPIC"],
        "source_date_epoch": env["SOURCE_DATE_EPOCH"],
        "native_source_sha256": {str(item.relative_to(NATIVE)): digest(item) for item in
                                  (AUTH / "coh_auth.c", AUTH / "coh_auth_openssl.c",
                                   AUTH / "tests/test_auth.c", NATIVE / "src/coh_blowfish.c",
                                   NATIVE / "protocol/coh_protocol.c")},
        "artifacts_sha256": {str(item.relative_to(output)): digest(item) for item in files},
        "shared_elf_machine": machine, "private_android_crypto_dependency": False,
        "dynamic_openssl_dependency": False, "android_crypto_provider_linked": True,
        "android_test_executed": False, "emulator_qualified": False,
        "physical_thor_accepted": False, "actual_server_interoperability_verified": False,
        "authenticated_server_session": False,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ndk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, default=Path("/tmp/coh-auth-android-cache"))
    parser.add_argument("--source-archive", type=Path)
    parser.add_argument("--api", type=int, default=26)
    parser.add_argument("--abis", choices=ABIS, nargs="+", default=list(ABIS))
    parser.add_argument("--jobs", type=int, default=min(3, os.cpu_count() or 1))
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    args.ndk = args.ndk.resolve()
    args.output = args.output.resolve()
    if args.api < 26 or args.api > 33 or args.jobs < 1:
        parser.error("Use API 26..33 for the Android 13 profile and at least one build job")
    pin = json.loads((HERE / "openssl-source.json").read_text())
    archive = source_archive(args, pin)
    results = [build(args, archive, pin, abi) for abi in args.abis]
    print(json.dumps({"status": "PASS", "receipts": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
