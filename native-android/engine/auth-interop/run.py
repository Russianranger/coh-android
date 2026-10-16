#!/usr/bin/env python3
"""Opt-in disposable Auth/DB/Map probe. Credentials use private stdin only."""
import argparse
import getpass
import ipaddress
import re
import secrets
import subprocess
import sys
from pathlib import Path


def endpoint(text):
    try:
        address, port = text.rsplit(':', 1)
        address = str(ipaddress.IPv4Address(address))
        if not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535:
            raise ValueError
        return address, str(int(port))
    except (ValueError, ipaddress.AddressValueError):
        raise argparse.ArgumentTypeError('Expected explicit numeric IPv4:port') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--auth', type=endpoint, required=True)
    parser.add_argument('--db', type=endpoint, required=True)
    parser.add_argument('--map', type=endpoint, required=True)
    parser.add_argument('--shard', type=int, choices=range(1, 256), required=True, metavar='1..255')
    parser.add_argument('--slot', type=int, choices=range(64), required=True, metavar='0..63')
    parser.add_argument('--version', required=True, help='Exact independently checked server-compatible version')
    parser.add_argument('--checksum', required=True, help='32 hexadecimal digits of approved client checksum')
    parser.add_argument('--timeout-ms', type=int, default=30000)
    args = parser.parse_args()
    if (not re.fullmatch(r'[0-9a-fA-F]{32}', args.checksum) or int(args.checksum, 16) == 0
            or not 1 <= len(args.version) <= 99 or not args.version.isascii()
            or any(ord(c) < 32 or ord(c) > 126 for c in args.version)
            or not 1000 <= args.timeout_ms <= 300000):
        parser.error('Invalid explicit checksum/version/timeout policy')
    # No noninteractive getpass fallback may echo credentials to a log/pipe.
    if not sys.stdin.isatty():
        parser.error('Interactive private terminal required; no credentials in argv/environment')
    account = getpass.getpass('Disposable account (hidden): ')
    password = getpass.getpass('Disposable password (hidden): ')
    try:
        account_bytes = account.encode('ascii')
        password_bytes = password.encode('utf-8')
    except UnicodeError:
        parser.error('Account must be ASCII')
    if (not 1 <= len(account_bytes) <= 14 or len(password_bytes) > 16
            or any(c in account_bytes + password_bytes for c in (b'\0', b'\n', b'\r'))):
        parser.error('Credential length/encoding rejected')
    credential_input = bytearray(account_bytes + b'\n' + password_bytes + b'\n')
    account = password = account_bytes = password_bytes = None
    # Fresh IDs per isolated process; no automatic retry or reuse after suspend.
    connection_id = secrets.randbelow(2**32 - 2) + 1
    command = [str(args.probe.resolve()), *args.auth, *args.db, *args.map, str(args.shard), str(args.slot),
               args.version, args.checksum, str(args.timeout_ms), str(connection_id)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(credential_input, timeout=args.timeout_ms / 1000 + 10)
    except (KeyboardInterrupt, subprocess.TimeoutExpired):
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
    finally:
        credential_input[:] = b'\0' * len(credential_input)
    sys.stdout.buffer.write(stdout)
    sys.stderr.buffer.write(stderr)
    return process.returncode


if __name__ == '__main__':
    raise SystemExit(main())
