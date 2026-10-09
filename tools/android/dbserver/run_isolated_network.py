#!/usr/bin/env python3
"""Run one PRoot command as the original user in a new loopback-only network."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def network_identity():
    return os.readlink("/proc/self/ns/net")


def loopback_state():
    interfaces = sorted(name for _, name in socket.if_nameindex())
    require(interfaces == ["lo"], "Isolated namespace has a non-loopback interface")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        flags = struct.unpack_from("H", fcntl.ioctl(probe.fileno(), 0x8913, struct.pack("16sH", b"lo", 0)), 16)[0]
    require(flags & 1 and flags & 8, "Private loopback interface is not up")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
    return interfaces


def clean_environment(loader, temporary):
    return {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "LANG": "C.UTF-8", "TZ": "UTC", "PYTHONDONTWRITEBYTECODE": "1",
            "PROOT_LOADER": str(loader), "PROOT_TMP_DIR": str(temporary), "PROOT_NO_SECCOMP": "1"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uid", type=int, required=True)
    parser.add_argument("--gid", type=int, required=True)
    parser.add_argument("--host-netns", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--proot-loader", type=Path, required=True)
    parser.add_argument("--proot-tmp", type=Path, required=True)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    require(bool(command) and Path(command[0]).is_absolute(), "Expected an absolute PRoot command")
    require(args.uid > 0 and args.gid >= 0, "The DbServer guest must run as the original non-root user")
    require(re.fullmatch(r"net:\[\d+\]", args.host_netns), "Invalid host network namespace identity")
    require(network_identity() != args.host_netns, "A distinct network namespace is mandatory")
    if not args.child:
        require(os.geteuid() == 0, "Namespace setup must run through sudo unshare")
        ip = shutil.which("ip")
        setpriv = shutil.which("setpriv")
        require(ip is not None and setpriv is not None, "iproute2 and util-linux are required")
        subprocess.run([ip, "link", "set", "lo", "up"], check=True,
                       env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"})
        loopback_state()
        child = [setpriv, "--reuid", str(args.uid), "--regid", str(args.gid), "--init-groups",
                 sys.executable, str(Path(__file__).resolve()), "--child", "--uid", str(args.uid),
                 "--gid", str(args.gid), "--host-netns", args.host_netns,
                 "--receipt", str(args.receipt), "--proot-loader", str(args.proot_loader),
                 "--proot-tmp", str(args.proot_tmp), "--", *command]
        os.execve(setpriv, child, clean_environment(args.proot_loader, args.proot_tmp))
    require(os.getuid() == args.uid and os.geteuid() == args.uid
            and os.getgid() == args.gid and os.getegid() == args.gid,
            "The DbServer guest did not drop to the original user/group")
    interfaces = loopback_state()
    receipt = {"format": 1, "scope": "isolated_loopback_only_host_network",
               "host_network_namespace": args.host_netns, "guest_network_namespace": network_identity(),
               "distinct_network_namespace": True, "original_uid": args.uid, "original_gid": args.gid,
               "effective_uid": os.geteuid(), "effective_gid": os.getegid(), "interfaces": interfaces,
               "loopback_up": True, "external_network_disabled": True, "guest_runs_as_root": False}
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    os.execve(command[0], command, clean_environment(args.proot_loader, args.proot_tmp))


if __name__ == "__main__":
    main()
