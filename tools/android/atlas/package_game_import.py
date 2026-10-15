#!/usr/bin/env python3
"""Package pinned repository text and bounded indexes for Android asset import.

The existing reviewed binary-asset ZIP stays external. This builds only the
matching immutable text payload, preserves source database configuration
priority, and binds both inputs to streaming, ASCII inventories. No schema,
generated cache, executable, credential or runtime state belongs in this base.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/android/game"))
import prepare_game_data as game

ROOT = game.ROOT
PROPERTIES = "atlas-import.properties"
TEXT_ARCHIVE = "atlas-text.zip"
TEXT_INDEX = "atlas-text-index.tsv"
ASSET_INDEX = "atlas-assets-index.tsv"
BUILD_RECEIPT = "atlas-import-build.json"
PACKAGE_FILES = frozenset((PROPERTIES, TEXT_ARCHIVE, TEXT_INDEX, ASSET_INDEX))
RESERVE_BYTES = 256 * 1024**2
PER_FILE_BYTES = 4096
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
require = game.require
digest = game.runtime.sha256


def safe_name(name):
    """The TSV and Java parser share a printable-ASCII, unambiguous namespace."""
    game.runtime.safe_relative(name)
    require(name.isascii() and all(32 <= ord(c) < 127 and c not in '<>:"\\|?*' for c in name),
            "Nonportable import path: " + name)
    require(all(not part.endswith((" ", ".")) and not re.fullmatch(
        r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part)
        for part in name.split("/")), "Reserved import path: " + name)
    require(len(name.encode("ascii")) <= 1024, "Import path exceeds bound")
    return name


def checked_record(record):
    require(isinstance(record, dict) and type(record.get("size")) is int
            and 0 <= record["size"] <= game.MAX_BYTES
            and isinstance(record.get("sha256"), str) and SHA256.fullmatch(record["sha256"]),
            "Invalid immutable file record")
    return {"bytes": record["size"], "sha256": record["sha256"]}


def pinned_assets(root):
    """Use the reviewed external manifest, never trust a selected ZIP's claims."""
    manifest = game.regular_bytes(root / "assets/reference-inputs-manifest.json", game.assets.MAX_MANIFEST)
    require(hashlib.sha256(manifest).hexdigest() == game.ASSET_MANIFEST_SHA256,
            "Reviewed asset manifest hash differs")
    document = game.assets.decode_manifest(manifest)
    require(manifest == game.assets.canonical(document), "Reviewed asset manifest is not canonical")
    records = game.assets.validate_manifest(document, game.assets.provenance(root))
    receipt = game.assets.decode_manifest(game.regular_bytes(root / "assets/reference-inputs-receipt.json", 65536))
    pins = {"source_commit": game.SOURCE, "text_data_commit": game.DATA,
            "archive_sha256": game.ASSET_ARCHIVE_SHA256, "archive_bytes": game.ASSET_ARCHIVE_BYTES,
            "manifest_sha256": game.ASSET_MANIFEST_SHA256,
            "asset_count": game.ASSET_COUNT, "asset_bytes": game.ASSET_BYTES}
    require(all(receipt.get(key) == value for key, value in pins.items()),
            "Reviewed asset receipt differs")
    require(len(records) == game.ASSET_COUNT and sum(r["size"] for r in records) == game.ASSET_BYTES,
            "Reviewed asset totals differ")
    return manifest, records


def immutable_input(root, filename, commit):
    lock = json.loads(game.regular_bytes(root / filename, 65536))
    require(lock.get("commit") == commit, "Immutable input commit differs")
    if filename == "content-lock.json":
        require(lock.get("source_pair") == game.SOURCE, "Companion source pair differs")
    manifest_path = root / game.runtime.safe_relative(lock["manifest"])
    manifest = json.loads(game.regular_bytes(manifest_path, game.MAX_MANIFEST))
    require(manifest.get("commit") == commit and isinstance(manifest.get("entries"), list),
            "Immutable input manifest differs")
    records = {}
    for record in manifest["entries"]:
        name = game.runtime.safe_relative(record["path"]).as_posix()
        require(name not in records, "Duplicate immutable input path")
        records[name] = checked_record(record)
    destination = root / game.runtime.safe_relative(lock["destination"])
    for ancestor in (destination, *destination.parents):
        require(not ancestor.is_symlink(), "Linked immutable input ancestor")
    return destination, records


def text_plan(root):
    """Follow prepare_runtime's exact traversal/casing and source-cfg precedence."""
    companion, companion_records = immutable_input(root, "content-lock.json", game.DATA)
    source, source_records = immutable_input(root, "upstream-lock.json", game.SOURCE)
    plan = game.runtime.FilePlan()
    pins = {}
    expected_companion = {name for name in companion_records if name.startswith("data/")
                          and game.runtime.excluded_reason(name[5:]) is None}
    seen_companion = set()
    for name, path in game.runtime.input_files(companion / "data"):
        if game.runtime.excluded_reason(name):
            continue
        full_name = "data/" + name
        safe_name(full_name)
        require(full_name in expected_companion, "Unlisted immutable text input: " + full_name)
        require(path.suffix.casefold() not in game.FORBIDDEN_SUFFIXES,
                "Executable or generated cache in immutable text")
        require(name.casefold() not in pins, "Case-colliding immutable text input")
        plan.add(name, path)
        pins[name.casefold()] = companion_records[full_name]
        seen_companion.add(full_name)
    require(seen_companion == expected_companion, "Missing immutable text input")
    expected_config = {name for name in source_records if name.startswith("data/server/db/")
                       and Path(name).suffix.casefold() == ".cfg"}
    seen_config = set()
    for name, path in game.runtime.input_files(source / "data/server/db"):
        if path.suffix.casefold() != ".cfg":
            continue
        full_name = "data/server/db/" + name
        safe_name(full_name)
        require(full_name in expected_config, "Unlisted source database configuration")
        target = "server/db/" + name
        plan.add(target, path, replace=True)
        pins[target.casefold()] = source_records[full_name]
        seen_config.add(full_name)
    require(seen_config == expected_config, "Missing source database configuration")
    result = {}
    for key, (name, path) in plan.files.items():
        target = safe_name("data/" + name.as_posix())
        require(path.is_file() and not path.is_symlink() and path.stat().st_size == pins[key]["bytes"],
                "Immutable text input size differs: " + target)
        result[target] = {"path": path, **pins[key]}
    return dict(sorted(result.items()))


def canonical_inventory(text, assets):
    """Mirror FilePlan's existing-directory spelling for imported binary assets.

    ZIP names remain their original lowercase names. Output parents follow the
    authoritative text tree: 1,009 reviewed assets share mixed-case text paths.
    Android must apply this same directory mapping after importing text first.
    """
    plan, actual = game.runtime.FilePlan(), {}
    for name, record in text.items():
        plan.add(name, Path("/metadata-only"))
        actual[name.casefold()] = {key: record[key] for key in ("bytes", "sha256")}
    for record in assets:
        name = safe_name("data/" + record["path"])
        require(name.casefold() not in actual, "Reviewed assets overlap authoritative text")
        plan.add(name, Path("/metadata-only"))
        actual[name.casefold()] = checked_record(record)
    return dict(sorted((name.as_posix(), actual[key]) for key, (name, _) in plan.files.items()))


def joined_inventory(root, text, assets):
    expected = game.expected_data(root, assets)
    actual = canonical_inventory(text, assets)
    require({name.casefold(): record for name, record in actual.items()} == expected,
            "Combined import inventory differs from reviewed game data")
    return actual


def index_bytes(records):
    return "".join(str(record["bytes"]) + "\t" + record["sha256"] + "\t" + safe_name(name) + "\n"
                   for name, record in records.items()).encode("ascii")


def write_text_archive(text, destination):
    """Hash the same bytes that are compressed; file metadata alone is insufficient."""
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6, allowZip64=True) as archive:
        for name, record in text.items():
            info = game.assets.zip_info(name, "deflate")
            info.file_size = record["bytes"]
            path = record["path"]
            require(path.is_file() and not path.is_symlink(), "Changed/linked text input: " + name)
            hashed, total = hashlib.sha256(), 0
            with path.open("rb") as source, archive.open(info, "w") as target:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    total += len(block)
                    require(total <= record["bytes"], "Immutable text input grew: " + name)
                    hashed.update(block)
                    target.write(block)
            require(total == record["bytes"] and hashed.hexdigest() == record["sha256"],
                    "Immutable text input hash differs: " + name)


def verify_text_archive(path, text):
    """Replay the packaged compressed bytes, checking hashes and exact members."""
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        require([info.filename for info in infos] == list(text), "Text archive member set/order differs")
        for info in infos:
            record = text[info.filename]
            require(info.file_size == record["bytes"] and info.compress_type == zipfile.ZIP_DEFLATED
                    and not info.flag_bits & 1 and not info.is_dir()
                    and stat.S_IFMT(info.external_attr >> 16) == stat.S_IFREG,
                    "Text archive entry metadata differs")
            hashed, total = hashlib.sha256(), 0
            with archive.open(info) as source:
                for block in iter(lambda: source.read(1024 * 1024), b""):
                    total += len(block)
                    require(total <= record["bytes"], "Inflated text exceeds pinned length")
                    hashed.update(block)
            require(total == record["bytes"] and hashed.hexdigest() == record["sha256"],
                    "Packaged text hash differs: " + info.filename)


def read_index(path, prefix):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= game.MAX_MANIFEST,
            "Missing, linked or oversized import index")
    records, folded, directories, previous = {}, set(), {}, ""
    with path.open("r", encoding="ascii", newline="") as source:
        for line in source:
            require(line.endswith("\n") and "\r" not in line and len(line) <= 2048,
                    "Noncanonical import index line")
            fields = line[:-1].split("\t")
            require(len(fields) == 3 and re.fullmatch(r"0|[1-9][0-9]*", fields[0])
                    and SHA256.fullmatch(fields[1]), "Invalid import index record")
            size, hashed, name = int(fields[0]), fields[1], safe_name(fields[2])
            require(0 <= size <= game.MAX_BYTES and name.startswith(prefix)
                    and name > previous and name.casefold() not in folded
                    and name.casefold() not in directories,
                    "Unordered, duplicate or out-of-scope import index")
            parts = name.split("/")
            for number in range(1, len(parts)):
                directory = "/".join(parts[:number])
                key = directory.casefold()
                require(key not in folded and directories.get(key, directory) == directory,
                        "Ambiguous import directory casing or file/directory collision")
                directories[key] = directory
            records[name] = {"bytes": size, "sha256": hashed}
            folded.add(name.casefold())
            previous = name
            require(len(records) <= game.MAX_FILES, "Import index exceeds entry bound")
    require(records, "Empty import index")
    return records


def verify_package(directory, repository_commit=None, *, root=ROOT, verify_archive=True):
    """Verify candidate inputs before APK packaging, without immutable payload trees.

    The optional build receipt is diagnostic only. Every property/index value is
    recomputed against the checked-in immutable receipts, and archive replay is
    enabled by default. Returns the typed import properties for the APK builder.
    """
    root, directory = Path(root), Path(directory)
    require(directory.is_dir() and not directory.is_symlink(), "Missing or linked import package")
    found = {path.name for path in directory.iterdir()}
    require(found in (set(PACKAGE_FILES), set(PACKAGE_FILES) | {BUILD_RECEIPT})
            and all(path.is_file() and not path.is_symlink() for path in directory.iterdir()),
            "Unexpected import package files")
    manifest_bytes, asset_records = pinned_assets(root)
    properties = {}
    raw = game.regular_bytes(directory / PROPERTIES, 65536).decode("ascii")
    for line in raw.splitlines(keepends=True):
        require(line.endswith("\n") and "\r" not in line and line.count("=") == 1,
                "Noncanonical import properties")
        key, value = line[:-1].split("=", 1)
        require(key and value and key not in properties, "Invalid or duplicate import property")
        properties[key] = value
    commit = properties.get("repository.commit", "")
    require(COMMIT.fullmatch(commit) and (repository_commit is None or repository_commit == commit),
            "Import repository commit differs")
    text = read_index(directory / TEXT_INDEX, "data/")
    asset_index = read_index(directory / ASSET_INDEX, "assets/")
    expected_asset_index = {"assets/" + record["path"]: checked_record(record) for record in asset_records}
    require(asset_index == expected_asset_index, "Asset index differs from accepted manifest")
    expected = joined_inventory(root, text, asset_records)
    archive = directory / TEXT_ARCHIVE
    require(0 < archive.stat().st_size <= game.MAX_BYTES, "Text archive exceeds size bound")
    wanted = {
        "format": 1, "source.commit": game.SOURCE, "data.commit": game.DATA,
        "repository.commit": commit,
        "asset.archive.bytes": game.ASSET_ARCHIVE_BYTES, "asset.archive.sha256": game.ASSET_ARCHIVE_SHA256,
        "asset.manifest.bytes": len(manifest_bytes), "asset.manifest.sha256": game.ASSET_MANIFEST_SHA256,
        "asset.count": game.ASSET_COUNT, "asset.bytes": game.ASSET_BYTES,
        "text.archive.bytes": archive.stat().st_size, "text.archive.sha256": digest(archive),
        "text.count": len(text), "text.bytes": sum(record["bytes"] for record in text.values()),
        "text.index.bytes": (directory / TEXT_INDEX).stat().st_size,
        "text.index.sha256": digest(directory / TEXT_INDEX),
        "asset.index.bytes": (directory / ASSET_INDEX).stat().st_size,
        "asset.index.sha256": digest(directory / ASSET_INDEX),
        "total.count": len(expected), "total.bytes": sum(record["bytes"] for record in expected.values()),
        "storage.reserve.bytes": RESERVE_BYTES, "storage.per.file.bytes": PER_FILE_BYTES,
    }
    require(properties == {key: str(value) for key, value in wanted.items()},
            "Import properties differ from checked payload and source receipts")
    require(raw == "".join(key + "=" + str(value) + "\n" for key, value in sorted(wanted.items())),
            "Import properties are not in canonical order")
    if verify_archive:
        verify_text_archive(archive, text)
    return wanted


def package(output, repository_commit, *, root=ROOT):
    root, output = Path(root), Path(output)
    require(isinstance(repository_commit, str) and COMMIT.fullmatch(repository_commit),
            "Repository commit must be a full lowercase Git commit")
    game.assets.safe_new(output, root)
    manifest_bytes, asset_records = pinned_assets(root)
    text = text_plan(root)
    expected = joined_inventory(root, text, asset_records)
    asset_index = {"assets/" + record["path"]: checked_record(record) for record in asset_records}
    text_bytes = sum(record["bytes"] for record in text.values())
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".atlas-import-", dir=output.parent) as temporary:
        staging = Path(temporary) / "package"
        staging.mkdir(mode=0o700)
        (staging / TEXT_INDEX).write_bytes(index_bytes(text))
        (staging / ASSET_INDEX).write_bytes(index_bytes(asset_index))
        write_text_archive(text, staging / TEXT_ARCHIVE)
        verify_text_archive(staging / TEXT_ARCHIVE, text)
        properties = {
            "format": 1, "source.commit": game.SOURCE, "data.commit": game.DATA,
            "repository.commit": repository_commit,
            "asset.archive.bytes": game.ASSET_ARCHIVE_BYTES, "asset.archive.sha256": game.ASSET_ARCHIVE_SHA256,
            "asset.manifest.bytes": len(manifest_bytes), "asset.manifest.sha256": game.ASSET_MANIFEST_SHA256,
            "asset.count": game.ASSET_COUNT, "asset.bytes": game.ASSET_BYTES,
            "text.archive.bytes": (staging / TEXT_ARCHIVE).stat().st_size,
            "text.archive.sha256": digest(staging / TEXT_ARCHIVE),
            "text.count": len(text), "text.bytes": text_bytes,
            "text.index.bytes": (staging / TEXT_INDEX).stat().st_size,
            "text.index.sha256": digest(staging / TEXT_INDEX),
            "asset.index.bytes": (staging / ASSET_INDEX).stat().st_size,
            "asset.index.sha256": digest(staging / ASSET_INDEX),
            "total.count": len(expected), "total.bytes": sum(r["bytes"] for r in expected.values()),
            "storage.reserve.bytes": RESERVE_BYTES, "storage.per.file.bytes": PER_FILE_BYTES,
        }
        (staging / PROPERTIES).write_bytes("".join(key + "=" + str(value) + "\n"
            for key, value in sorted(properties.items())).encode("ascii"))
        files = {name: {"bytes": (staging / name).stat().st_size, "sha256": digest(staging / name)}
                 for name in sorted(PACKAGE_FILES)}
        receipt = {"format": 1, "scope": "reviewed_android_game_import_package",
                   "repository_commit": repository_commit, "source_commit": game.SOURCE,
                   "data_commit": game.DATA, "files": files, "contract": properties,
                   "text_archive_roundtrip_verified": True,
                   "reviewed_binary_assets_included": False,
                   "schema_and_generated_caches_included": False,
                   "android_execution_validated": False, "gameplay_validated": False}
        (staging / BUILD_RECEIPT).write_bytes(game.assets.canonical(receipt))
        require(not output.exists() and not output.is_symlink(), "Output appeared during packaging")
        staging.rename(output)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository-commit", required=True)
    args = parser.parse_args()
    receipt = package(args.output, args.repository_commit)
    print(json.dumps({"output": str(args.output), "files": receipt["files"],
                      "text_count": receipt["contract"]["text.count"],
                      "text_bytes": receipt["contract"]["text.bytes"],
                      "total_count": receipt["contract"]["total.count"],
                      "total_bytes": receipt["contract"]["total.bytes"]}, indent=2))


if __name__ == "__main__":
    main()
