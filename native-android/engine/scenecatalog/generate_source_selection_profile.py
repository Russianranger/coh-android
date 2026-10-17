#!/usr/bin/env python3
"""Reproduce compiled exact-profile bytes; not a runtime admission interface."""
import argparse,hashlib,json,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent
EXPECTED=['9b74823a341fe565a978f81516b3b13ea8741ec8ecc57bb2b8bfb40130943eaa', 'e6a25d7e6429fbb856fad617c5f8eeab75325c0fb7c0083be7f91348e5765ced', '3be317b5cc4b24aad8b19cd93e18762f12270ad4284c31a81e7587e4e35fadc1', '7c42a9612e4e08ee6463c3a8f87d2cf0749ff2baa8183d6b3c58281ec004c39c', '0947a6a172c083350d3229de5facebc5862fdc1bdd98e9b6c181b14cf3a715e4', '4c704b4bec89685c75d2e157a9fc6f9df80e0161efd22d3cc2a4d0cd3b3855fa', 'd977098428d2d51058a0cfe59443d3187cd07b1de518ff7172261037f868fa1c']
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture-directory',type=Path,required=True);p.add_argument('--verify',action='store_true');p.add_argument('--output',type=Path)
a=p.parse_args();cap=a.capture_directory
files=[cap/'source-identity.json',cap/'run-identity.json',cap.parent/'control-fixture.json',cap/'resource-binding.json',cap/'capture-receipt.json',HERE/'evidence/actual-resource-bodies-source-adapter-sealed-38994607354.json',HERE/'evidence/prepared-geo-source-route-final-38994607354.json']
for path,expected in zip(files,EXPECTED):
 if not path.is_file() or path.is_symlink() or path.stat().st_size>8*1024**2 or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('Unregistered profile evidence')
rows=json.loads(files[-1].read_text())['bodies'];rows.sort(key=lambda r:r['source_geo_name'])
assert len(rows)==391 and sum(len(r['source_ordinals']) for r in rows)==3083
wire=bytearray(b'COHSEL01'+struct.pack('<6I',1,len(rows),40232,3083,0,0))
for row in rows:
 name=row['source_geo_name'].encode()+b'\0';path=row['prepared_logical_path'].encode()+b'\0';ordinals=row['source_ordinals'];size=52+len(name)+len(path)+4*len(ordinals)
 wire+=struct.pack('<5I',size,len(name),len(path),len(ordinals),row['bytes'])+bytes.fromhex(row['sha256'])+name+path+struct.pack('<'+'I'*len(ordinals),*ordinals)
out=['/* Generated exact reviewed profile; see SOURCE_SELECTION_CONTRACT.md. */','static const uint8_t profile_wire[] = {']
for k in range(0,len(wire),20):out.append(' '+','.join('0x%02x'%v for v in wire[k:k+20])+',')
out+=['};','static const uint8_t profile_wire_sha[32] = {'+','.join('0x%02x'%v for v in hashlib.sha256(wire).digest())+'};','static const uint8_t evidence_sha[7][32] = {']
for path in files:out.append(' {'+','.join('0x%02x'%v for v in hashlib.sha256(path.read_bytes()).digest())+'}, /* '+path.name+' */')
out+=['};','static const size_t evidence_sizes[7] = {'+','.join(str(path.stat().st_size) for path in files)+'};'];text='\n'.join(out)+'\n'
if a.verify:
 if text!=(HERE/'coh_source_selection_profile.inc').read_text():raise ValueError('Compiled profile differs')
else:
 if a.output is None:raise ValueError('New output required')
 with a.output.open('x') as stream:stream.write(text)
print(json.dumps({'passed':True,'wire_bytes':len(wire),'wire_sha256':hashlib.sha256(wire).hexdigest(),'profile_files':391,'root_reference_ordinals':3083,'native_admission':False}))
