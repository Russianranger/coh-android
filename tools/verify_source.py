#!/usr/bin/env python3
"""Verify the immutable imported snapshot; exit nonzero on any discrepancy."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', default='upstream-lock.json')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / args.lock).read_text())
    manifest = json.loads((root / lock["manifest"]).read_text())
    source = root / lock["destination"]
    failures = []
    entries = manifest["entries"]
    expected = {entry["path"] for entry in entries}
    if manifest["commit"] != lock["commit"]:
        failures.append("Manifest commit differs from lock")
    if len(entries) != lock["files"] or len(expected) != len(entries):
        failures.append("File count differs or duplicate manifest paths exist")
    if sum(entry["size"] for entry in entries) != lock["bytes"]:
        failures.append("Manifest byte total differs from lock")
    actual = {
        str(path.relative_to(source))
        for path in source.rglob("*")
        if path.is_file() or path.is_symlink()
    }
    for path in sorted(actual - expected):
        failures.append(f"Unexpected file: {path}")
    for entry in entries:
        name = entry["path"]
        path = source / name
        if path.is_symlink() or not path.is_file():
            failures.append(f"Missing or non-regular file: {name}")
            continue
        data = path.read_bytes()
        if len(data) != entry["size"]:
            failures.append(f"Size differs: {name}")
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            failures.append(f"SHA-256 differs: {name}")
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data)
        if blob.hexdigest() != entry["git_blob"]:
            failures.append(f"Git blob differs: {name}")
        if os.name != "nt":
            executable = bool(path.stat().st_mode & 0o111)
            if executable != (entry["mode"] == "100755"):
                failures.append(f"Executable bit differs: {name}")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"PASS: {len(entries):,} files, {lock['bytes']:,} bytes; "
          f"snapshot {lock['commit']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
