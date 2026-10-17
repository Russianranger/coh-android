#!/usr/bin/env python3
"""Read the explicit synthetic original-source sink fixture; refuse corruption.

No fixture or parser acceptance establishes live source/native generation.
"""
from pathlib import Path
import argparse,hashlib,json,os,struct,sys,tempfile,types
HERE=Path(__file__).resolve().parent
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--fixture',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 path=HERE/'inspect_groups_capture.py';source=path.read_bytes();module=types.ModuleType('frozen_groups_capture_inspector');module.__file__=str(path);exec(compile(source,str(path),'exec'),module.__dict__)
 raw=args.fixture.read_bytes();checks=0;refusals=0;offsets={};at=64
 while at<len(raw):
  kind,_,n,_=struct.unpack_from('<4I',raw,at);offsets.setdefault(kind,[]).append((at,n));at+=16+n
 with tempfile.TemporaryDirectory(prefix='coh-groups-inspection-') as temporary:
  directory=Path(temporary);candidate=directory/'candidate.cohgtx';candidate.write_bytes(raw)
  result=module.inspect(candidate,directory/'extracted');assert result['passed'] and result['envelope']['sha256']==hashlib.sha256(raw).hexdigest();checks+=1
  for key in ('source_generation_admitted','world_authority','source_provenance_verified','actual_native_receive_correlated','cache_equivalence_verified'):assert result[key] is False;checks+=1
  for name,identity in result['files'].items():
   copied=(directory/'extracted'/name).read_bytes();assert len(copied)==identity['bytes'] and hashlib.sha256(copied).hexdigest()==identity['sha256'];checks+=1
  def refuse(value,extract=False):
   nonlocal checks,refusals
   candidate.write_bytes(value)
   try:module.inspect(candidate,directory/'rollback' if extract else None)
   except ValueError:refusals+=1
   else:raise AssertionError('corrupt envelope accepted')
   assert not (directory/'rollback').exists();checks+=1
  descriptors_before=len(os.listdir('/proc/self/fd'))
  for end in range(len(raw)):refuse(raw[:end])
  for offset in [0,8,12,16,20,24,63,64,68,72,76]:
   changed=bytearray(raw);changed[offset]^=0x80;refuse(changed)
  changes=[(1,0),(1,8),(1,12),(2,20),(2,24),(3,16),(3,20),(3,24),(6,16),(6,32),(7,16),(7,20),(7,24),(7,28),(7,132),(7,156),(7,164),(9,16),(9,20),(9,24),(9,28),(9,32),(9,64),(9,100)]
  for kind,relative in changes:
   changed=bytearray(raw);offset=offsets[kind][0][0]+16+relative;changed[offset]^=0x80;refuse(changed,extract=True)
  for relative in (16,20,24):
   changed=bytearray(raw);struct.pack_into('<I',changed,offsets[1][0][0]+16+relative,0);refuse(changed,extract=True)
  # Different positive self-described owner labels remain merely observations.
  # Without independent exact source/run/receive admission, they grant nothing.
  changed=bytearray(raw);struct.pack_into('<I',changed,offsets[1][0][0]+32,227);candidate.write_bytes(changed);unproven=module.inspect(candidate);assert unproven['source_owner']['selected_dbid']==227 and not unproven['source_generation_admitted'] and not unproven['world_authority'];checks+=1
  refuse(raw+b'\0',extract=True)
  changed=bytearray(raw);struct.pack_into('<I',changed,offsets[8][0][0]+8,0xffffffff);refuse(changed,extract=True)
  candidate.write_bytes(raw)
  original_output=module.private_output
  class RefusedOutput:
   def __init__(self,output,kind):self.output=output;self.kind=kind
   @property
   def closed(self):return self.output.closed
   def fileno(self):return self.output.fileno()
   def write(self,value):
    if self.kind=='write':raise OSError('primary-write-refusal')
    return self.output.write(value)
   def flush(self):
    if self.kind in ('flush','flush_and_close'):raise OSError('primary-flush-refusal')
    return self.output.flush()
   def close(self):
    self.output.close()
    if self.kind in ('close','flush_and_close'):raise OSError('close-refusal')
  for kind in ('write','flush','close','flush_and_close'):
   used=[]
   def refused_output(path,binary):
    output=original_output(path,binary)
    if not used and binary:used.append(True);return RefusedOutput(output,kind)
    return output
   module.private_output=refused_output
   try:module.inspect(candidate,directory/'io-rollback')
   except OSError as failure:
    assert str(failure)==('primary-write-refusal' if kind=='write' else 'close-refusal' if kind=='close' else 'primary-flush-refusal');checks+=1
   else:raise AssertionError('output I/O refusal lost')
   assert not (directory/'io-rollback').exists();checks+=1
  module.private_output=original_output
  try:module.inspect(candidate,directory/'extracted')
  except FileExistsError:checks+=1
  else:raise AssertionError('existing destination accepted')
  linked=directory/'linked';linked.symlink_to(candidate)
  try:module.inspect(linked)
  except ValueError:checks+=1
  else:raise AssertionError('source symlink accepted')
  hard=directory/'hard';os.link(candidate,hard)
  try:module.inspect(candidate)
  except ValueError:checks+=1
  else:raise AssertionError('hard-linked source accepted')
  assert len(os.listdir('/proc/self/fd'))==descriptors_before;checks+=1
 assert path.read_bytes()==source
 report={'schema':'coh-source-groups-envelope-inspector-host-v1','passed':True,'checks':checks,'corruption_refusals':refusals,'parser_sha256':hashlib.sha256(source).hexdigest(),'fixture_sha256':hashlib.sha256(raw).hexdigest(),'synthetic_source_fixture':True,'source_generation_admitted':False,'world_authority':False}
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
