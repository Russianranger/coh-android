"""Authored legacyv0 negative controls; no authentic scene/material authority."""
import struct,zlib
import rigid_fixture as base
KINDS=('valid','bone','scale','weights','matidx','missing_uv','pivot','bad_index','duplicate_model','flags','trick','grid_cell','ctris','tags','extra','truncated_record')
def geo(kind='valid'):
 ix=base.INDICES if kind!='bad_index' else [0,1,999,0,2,3]
 channels=[base.delta(ix,3,True),base.delta(base.POSITIONS,3),base.delta(base.NORMALS,3),base.delta(base.UV,2)]
 payload=bytearray();packs=[]
 for i,data in enumerate(channels):
  stored=zlib.compress(data) if i%2 else data;packs.append((len(stored) if i%2 else 0,len(data),len(payload)));payload+=stored
 packs += [(0,0,0)]*3
 if kind in ('weights','matidx'):
  at=4 if kind=='weights' else 5;packs[at]=(0,1,len(payload));payload+=b'X'
 if kind=='missing_uv':packs[3]=(0,0,0)
 textures=struct.pack('<III',2,0,6)+b'a.tga\0b.tga\0';names=b'fixture_rigid_v0\0';mats=struct.pack('<4H',0,1,1,1)
 record=bytearray(216);struct.pack_into('<f',record,4,2.);struct.pack_into('<I',record,12,2);struct.pack_into('<II',record,28,4,2);struct.pack_into('<3f',record,92,1.,1.,1.)
 for at,condition in [(0,'flags'),(20,'bone'),(24,'trick'),(40,'grid_cell'),(72,'ctris'),(76,'tags'),(84,'pivot'),(88,'extra')]:
  if kind==condition:struct.pack_into('<I',record,at,1)
 if kind=='scale':struct.pack_into('<f',record,92,2.)
 for i,pack in enumerate(packs):struct.pack_into('<3I',record,132+i*12,*pack)
 extra=bytearray(140);struct.pack_into('<I',extra,136,2 if kind=='duplicate_model' else 1)
 if kind=='truncated_record':record=record[:-1]
 header=struct.pack('<4I',len(payload),len(textures),len(names),len(mats))+textures+names+mats+extra+record+(record if kind=='duplicate_model' else b'');compressed=zlib.compress(header)
 return struct.pack('<2I',len(compressed)+4,len(header))+compressed+b'\0'*4+payload
