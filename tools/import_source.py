#!/usr/bin/env python3
"""Import only the pinned upstream tree into an empty destination.

This preserves all tracked bytes and modes, builds the integrity manifest, and
stages the result only after checking the original Git tree identity. An existing
snapshot is verified instead of overwritten. Run from a clean repository.
"""

import collections
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile


def git(directory, *args):
    return subprocess.check_output(["git", "-C", str(directory), *args])


def main():
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "upstream-lock.json").read_text())
    destination = root / lock["destination"]
    if destination.exists():
        subprocess.run(["python3", str(root / "tools/verify_source.py")],
                       check=True)
        return
    if git(root, "status", "--porcelain").strip():
        raise SystemExit("Commit or stash local changes before importing")
    with tempfile.TemporaryDirectory(prefix="coh-source-") as directory:
        scratch = Path(directory)
        source = scratch / "source"
        source.mkdir()
        git(source, "init", "--quiet")
        git(source, "remote", "add", "origin", lock["acquisition_url"])
        git(source, "fetch", "--quiet", "--depth=1", "origin", lock["commit"])
        actual_tree = git(source, "rev-parse", "FETCH_HEAD^{tree}")
        if actual_tree.decode().strip() != lock["tree"]:
            raise SystemExit("Fetched source tree differs from lock")
        archive = scratch / "source.tar"
        git(source, "archive", "--format=tar", "--output=" + str(archive),
            lock["commit"])
        destination.mkdir(parents=True)
        with tarfile.open(archive) as bundle:
            for member in bundle:
                name = PurePosixPath(member.name)
                if name.is_absolute() or ".." in name.parts:
                    raise SystemExit("Unsafe archive path")
                path = destination / str(name)
                if member.isdir():
                    path.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(bundle.extractfile(member).read())
                    path.chmod(0o755 if member.mode & 0o111 else 0o644)
                else:
                    raise SystemExit("Unsupported archive entry")
        entries = []
        groups = collections.defaultdict(lambda: {"files": 0, "bytes": 0})
        extensions = collections.Counter()
        listing = git(source, "ls-tree", "-r", "-l", "-z", lock["commit"])
        for raw in listing.split(b"\0"):
            if not raw:
                continue
            metadata, raw_path = raw.split(b"\t", 1)
            mode, kind, blob, size = metadata.split()
            if kind != b"blob" or mode not in (b"100644", b"100755"):
                raise SystemExit("Unsupported Git entry")
            name = raw_path.decode()
            data = (destination / name).read_bytes()
            if len(data) != int(size):
                raise SystemExit("Extracted file size differs")
            entries.append({"path": name, "mode": mode.decode(),
                            "git_blob": blob.decode(), "size": len(data),
                            "sha256": hashlib.sha256(data).hexdigest()})
            group = name.split("/")[0] if "/" in name else "(root)"
            groups[group]["files"] += 1
            groups[group]["bytes"] += len(data)
            extensions[Path(name).suffix.lower()] += 1
        if len(entries) != lock["files"]:
            raise SystemExit("Source count differs from lock")
        if sum(entry["size"] for entry in entries) != lock["bytes"]:
            raise SystemExit("Source bytes differ from lock")
        manifest = {"commit": lock["commit"], "entries": entries}
        (root / lock["manifest"]).write_text(json.dumps(manifest, indent=2) + "\n")
        inventory = {"commit": lock["commit"], "files": len(entries),
                     "bytes": lock["bytes"],
                     "directories": dict(sorted(groups.items())),
                     "extensions": dict(extensions.most_common())}
        (root / "docs/source-inventory.json").write_text(
            json.dumps(inventory, indent=2) + "\n")
        subprocess.run(["python3", str(root / "tools/verify_source.py")],
                       check=True)
        git(root, "add", "-f", lock["destination"])
        staged = git(root, "write-tree").decode().strip()
        imported = git(root, "rev-parse", staged + ":" + lock["destination"])
        if imported.decode().strip() != lock["tree"]:
            raise SystemExit("Staged source tree differs from lock")
        git(root, "add", lock["manifest"], "docs/source-inventory.json")
        print("PASS: source imported and staged with exact upstream tree")


if __name__ == "__main__":
    main()
