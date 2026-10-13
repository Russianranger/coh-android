#!/usr/bin/env python3
"""Verify exact original SDK and consumer sources before building its oracle."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import struct

ROOT = Path(__file__).resolve().parents[2]
PINS = {
    "upstream/ouroboros/3rdparty/nvdxt/Release/nvDXTlibMT_S.lib": "1e9988ad52a01f44368d8d4150990ef2a033536a7a705424f04333143cd63b73",
    "upstream/ouroboros/Game/src/render/dxtlibwrapper.cpp": "00534c9aabb61a38a46cde6a59b1a3b1115c77a733005796c1dee9c5826a4a68",
    "upstream/ouroboros/Game/CMakeLists.txt": "1c36eef4c7484c6f2f236826197ace5cf1ad17f505c9b5a5f783c0f40caf799b",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--executable", type=Path)
    ap.add_argument("--receipt", type=Path)
    args = ap.parse_args()
    files = {}
    for name, expected in PINS.items():
        data = (ROOT / name).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise SystemExit(f"Pinned original oracle input changed: {name}")
        files[name] = {"sha256": actual, "bytes": len(data)}
    receipt = {
        "format": 1,
        "oracle": "original-nvDXTlibMT_S-Win32",
        "repository_pin": "61bcde64ece0c45a1e3ba1c39f038b15dc6efd7d",
        "inputs": files,
        "host": platform.platform(),
        "architecture": "Win32 x86",
        "runtime": "/MT; original static SDK, modern MSVC CRT resolution",
        "specified_mip_maps": 1,
        "device_execution": False,
        "full_client_execution": False,
    }
    if args.executable:
        pe = args.executable.read_bytes()
        if len(pe) < 64 or pe[:2] != b"MZ":
            raise SystemExit("Oracle executable lacks DOS header")
        offset = struct.unpack_from("<I", pe, 0x3C)[0]
        if offset + 24 > len(pe) or pe[offset:offset+4] != b"PE\0\0":
            raise SystemExit("Oracle executable lacks PE header")
        if struct.unpack_from("<H", pe, offset+4)[0] != 0x14C:
            raise SystemExit("Oracle must be PE32 i386")
        receipt["executable"] = {
            "sha256": hashlib.sha256(pe).hexdigest(), "bytes": len(pe),
            "machine": "i386", "path": args.executable.name,
        }
    if args.receipt:
        args.receipt.write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"passed": True, "inputs": len(files), "executable_checked": bool(args.executable)}))

if __name__ == "__main__":
    main()
