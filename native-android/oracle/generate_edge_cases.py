#!/usr/bin/env python3
"""Generate explicitly synthetic cases that probe the original SDK's edge contracts."""
import argparse
import json
from pathlib import Path
import struct

def dds(code, block, pixel_flags=4):
    header = bytearray(128)
    header[:4] = b"DDS "
    for offset, value in ((4,124),(8,0x81007),(12,4),(16,4),(20,len(block)),(28,1),(76,32),(80,pixel_flags),(108,0x1000)):
        struct.pack_into("<I", header, offset, value)
    header[84:88] = code.encode("ascii")
    return bytes(header) + block

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    color_transparent = struct.pack("<HHI", 0, 0xFFFF, 0xFFFFFFFF)
    color_reverse = struct.pack("<HHI", 0, 0xFFFF, 0xAAAAAAAA)
    color_white = struct.pack("<HHI", 0xFFFF, 0, 0)
    color_round = struct.pack("<HHI", 0xB48D, 0x4EB2, 0xE4E4E4E4)
    cases = {
        "synthetic-dxt1-transparent-fourcc": dds("DXT1",color_transparent,4),
        "synthetic-dxt1-transparent-alpha-flag": dds("DXT1",color_transparent,5),
        "synthetic-dxt3-reversed-endpoints": dds("DXT3",b"\xff"*8+color_reverse),
        "synthetic-dxt3-zero-alpha": dds("DXT3",b"\0"*8+color_white),
        "synthetic-dxt5-zero-alpha": dds("DXT5",b"\0"*8+color_white),
        "synthetic-dxt5-zero-selected-alpha": dds("DXT5",bytes([255,0])+int(sum(1<<(i*3)for i in range(16))).to_bytes(6,"little")+color_white),
        "synthetic-dxt5-reversed-endpoints": dds("DXT5",bytes([255,0])+b"\0"*6+color_reverse),
        "synthetic-dxt1-color-rounding": dds("DXT1",color_round),
    }
    selectors = sum((i%8)<<(i*3) for i in range(16)).to_bytes(6,"little")
    for pair in ((211,17),(17,211),(0,0),(255,255),(1,0),(0,1)):
        cases[f"synthetic-dxt5-alpha-{pair[0]}-{pair[1]}"] = dds("DXT5",bytes(pair)+selectors+color_round)
    for name, data in cases.items():
        (a.output/(name+".dds")).write_bytes(data)
    print(json.dumps({"synthetic_cases":len(cases),"scope":"DXT1 CPU alpha stripping, DXT3/5 endpoint order, all-zero alpha and rounding probes; not game assets"}))

if __name__ == "__main__":
    main()
