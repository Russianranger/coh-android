#!/usr/bin/env python3
"""Supplemental synthetic original-SDK probes; never counted as real assets."""
from pathlib import Path
import argparse,struct
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
for fmt in (1,3,5):
 for mode,(c0,c1) in enumerate(((0,65535),(65535,0),(0,0),(1,0))):
  h=bytearray(128);h[:4]=b'DDS '
  for o,v in ((4,124),(8,0x81007),(12,4),(16,4),(20,8 if fmt==1 else 16),(28,1),(76,32),(80,4),(108,0x1000)):struct.pack_into('<I',h,o,v)
  h[84:88]=('DXT'+str(fmt)).encode();color=struct.pack('<HHI',c0,c1,0xe4e4e4e4)
  if fmt==1:alpha=b''
  elif fmt==3:alpha=bytes.fromhex('1032547698badcfe')
  else:
   end=(200,20) if mode%2 else (20,200);bits=sum((i%8)<<(i*3) for i in range(16));alpha=bytes(end)+bits.to_bytes(6,'little')
  (a.output/f'DXT{fmt}-palette{mode}.dds').write_bytes(bytes(h)+alpha+color)
# Distinguish alpha stripping from color interpolation in the original SDK.
for fmt in (1,3,5):
 for pf in (4,5):
  h=bytearray(128);h[:4]=b'DDS '
  for o,v in ((4,124),(8,0x81007),(12,4),(16,4),(20,8 if fmt==1 else 16),(28,1),(76,32),(80,pf),(108,0x1000)):struct.pack_into('<I',h,o,v)
  h[84:88]=('DXT'+str(fmt)).encode();color=struct.pack('<HHI',0,65535,0xffffffff)
  alpha=b'' if fmt==1 else bytes(8)
  (a.output/f'DXT{fmt}-zero-alpha-flags{pf}.dds').write_bytes(bytes(h)+alpha+color)
