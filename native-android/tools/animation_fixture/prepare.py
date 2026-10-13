#!/usr/bin/env python3
"""Package original encoded CoH animation tracks for bounded native sampling.

This tool validates disk records bytewise, keeps every source key unmodified,
and delegates independent pose-reference generation to the source oracle.
"""
from pathlib import Path
import argparse,hashlib,json,math,struct,sys,subprocess,shutil
ROOT=Path(__file__).resolve().parents[2]
def sha(b):return hashlib.sha256(b).hexdigest()
def require(v,s):
 if not v:raise ValueError(s)
def span(b,o,n):
 require(0<=o<=len(b) and 0<=n<=len(b)-o,'animation span exceeds file');return b[o:o+n]
def u32(b,o):return struct.unpack('<I',span(b,o,4))[0]
def i32(b,o):return struct.unpack('<i',span(b,o,4))[0]
def text(b,o):
 raw=span(b,o,256);require(b'\0' in raw,'unterminated animation name');return raw.split(b'\0',1)[0].decode('ascii').replace('\\','/')
def inspect_animation(b):
 require(len(b)>=596,'animation header truncated');header=u32(b,0);boneoff=u32(b,524);count=i32(b,528);hier=u32(b,540);length=struct.unpack('<f',span(b,520,4))[0]
 require(596<=header<=len(b) and 1<=count<=99 and boneoff>=596 and boneoff+count*20==header,'animation header/bone table bounds differ');require(math.isfinite(length) and length>=0,'animation length invalid');tracks=[];ids=set()
 for index in range(count):
  ro,po,rf,pf,rc,pc,glob,flags,pad=struct.unpack('<IIHHHHbBH',span(b,boneoff+index*20,20));rot=flags&0x87;pos=flags&0x18;require(0<=glob<99 and glob not in ids,'animation bone ID invalid or duplicated');ids.add(glob);require(not(flags&0x60),'delta animation keys unsupported');require(rot in (1,2,4,128) and pos in (8,16),'ambiguous animation compression flags');require(0<rc<=rf and 0<pc<=pf,'animation key counts invalid');rs={1:16,2:5,4:8,128:5}[rot];ps=12 if pos==8 else 6;require(ro>=header and po>=header,'animation key points into header');span(b,ro,rf*rs);span(b,po,pf*ps)
  if rs==5:require(all(b[ro+j*5]<64 for j in range(rf)),'compressed rotation top bits invalid')
  if rs==16:
   for j in range(rf):require(all(math.isfinite(v) for v in struct.unpack('<4f',span(b,ro+j*16,16))),'nonfinite rotation key')
  if ps==12:
   for j in range(pf):require(all(math.isfinite(v) and abs(v)<2000000 for v in struct.unpack('<3f',span(b,po+j*12,12))),'nonfinite or out of bound position key')
  tracks.append({'global_id':glob,'flags':flags,'rotation_full_keys':rf,'position_full_keys':pf,'rotation_count':rc,'position_count':pc,'rotation_offset':ro,'position_offset':po,'rotation_stride':rs,'position_stride':ps})
 parents={};links=[];root=-1;capacity=0
 if hier:
  require(hier==596 and boneoff>hier+4 and (boneoff-hier-4)%12==0,'hierarchy envelope differs');capacity=(boneoff-hier-4)//12;require(capacity<=100,'hierarchy capacity exceeds source');root=i32(b,hier);stack=[(root,-1)]
  while stack:
   glob,parent=stack.pop()
   if glob==-1:continue
   require(0<=glob<min(capacity,99) and glob not in parents,'hierarchy repeated/out-of-bound bone');child,sibling,id=struct.unpack('<iii',span(b,hier+4+glob*12,12));require(id==glob,'hierarchy global ID differs');parents[glob]=parent;links.append({'global_id':glob,'parent_global_id':parent,'child_global_id':child,'next_global_id':sibling});stack.append((sibling,parent));stack.append((child,glob))
  require(ids.issubset(parents),'base tracks absent from hierarchy')
 else:require(boneoff==596,'motion has unexpected pre-bone bytes')
 return {'name':text(b,4),'base_anim_name':text(b,260),'bytes':len(b),'sha256':sha(b),'header_bytes':header,'bone_count':count,'length_frames':length,'hierarchy_capacity':capacity,'hierarchy_root':root,'hierarchy':sorted(links,key=lambda v:v['global_id']),'tracks':tracks},parents

def make_rig(base,motion,palette,socket):
 baseoff=128;motionoff=baseoff+len(base);paletteoff=motionoff+len(motion);total=paletteoff+len(palette)*4
 h=bytearray(128);struct.pack_into('<8s10I',h,0,b'COHRIG01',1,128,baseoff,len(base),motionoff,len(motion),paletteoff,len(palette),socket,0);struct.pack_into('<3fI',h,48,1.0,25.0,30.0,total)
 raw=bytes(h)+base+motion+struct.pack('<'+'I'*len(palette),*palette);require(len(raw)==total,'rig canonical size differs');return raw

def main():
 p=argparse.ArgumentParser();p.add_argument('--corpus',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--mesh',type=Path);p.add_argument('--original-samples',type=Path);p.add_argument('--material-corpus',type=Path);p.add_argument('--library',type=Path);p.add_argument('--source-directory',type=Path);p.add_argument('--evidence-output',type=Path);a=p.parse_args();pins=json.loads(Path(__file__).with_name('pins.json').read_text());a.output.mkdir(parents=True,exist_ok=True)
 evidence=a.evidence_output or ROOT/'results/animation-fixture-evidence';evidence.mkdir(parents=True,exist_ok=True);material_meta={}
 if a.material_corpus is not None:
  material=evidence/'material-prepared';cmd=[sys.executable,str(ROOT/'tools/material_fixture/prepare.py'),'--corpus',str(a.material_corpus.resolve()),'--output',str(material.resolve())]
  if a.library is not None:cmd+=['--library',str(a.library.resolve())]
  subprocess.run(cmd,check=True);material_meta=json.loads((material/'material-fixture.json').read_text())
  for name in ['mesh.bin','texture0.rgba','texture1.rgba','material-reference.bin']:shutil.copyfile(material/name,a.output/name)
  a.mesh=a.output/'mesh.bin'
 source={}
 for pin in pins['records']:
  b=(a.corpus/pin['file_name']).read_bytes();require(sha(b)==pin['sha256'] and len(b)==pin['size'],'source animation SHA/size differs');source[pin['id']]=b
 bm,parents=inspect_animation(source['base']);mm,_=inspect_animation(source['motion']);require(bm['name'].casefold()==bm['base_anim_name'].casefold()==mm['base_anim_name'].casefold(),'base animation links do not match');require(bm['name'].casefold()=='huge/skel_ready' and mm['name'].casefold()=='huge/run','selected source names differ');require(mm['length_frames']>=25,'motion does not cover authored range')
 required=set(pins['palette_global_ids']+[pins['socket_global_id']])
 for glob in tuple(required):
  while glob!=-1:require(glob in parents,'required bone missing from base hierarchy');required.add(glob);glob=parents[glob]
 require(required.issubset({t['global_id'] for t in bm['tracks']}),'required base tracks missing')
 rig=make_rig(source['base'],source['motion'],pins['palette_global_ids'],pins['socket_global_id']);(a.output/'rig.bin').write_bytes(rig)
 assets={'rig.bin':{'bytes':len(rig),'sha256':sha(rig)}}
 for name in ['mesh.bin','texture0.rgba','texture1.rgba','material-reference.bin']:
  if material_meta:
   data=(a.output/name).read_bytes();assets[name]={'bytes':len(data),'sha256':sha(data)}
 reference_meta={}
 if a.original_samples is None and a.material_corpus is not None:
  a.original_samples=evidence/'original-locals.json';report=evidence/'original-local-parity.json';cmd=[sys.executable,str(Path(__file__).with_name('original_animation_check.py')),'--rig',str((a.output/'rig.bin').resolve()),'--output',str(a.original_samples.resolve()),'--report',str(report.resolve())]
  if a.source_directory is not None:cmd+=['--source-directory',str(a.source_directory.resolve())]
  subprocess.run(cmd,check=True)
 if a.original_samples is not None:
  require(a.mesh is not None,'mesh needed for independent reference generation');sys.path.insert(0,str(ROOT/'animation-probe/contract'));from hierarchy_reference import generate,self_check
  self_check()
  ref,reference_meta=generate(json.loads(a.original_samples.read_text()),a.mesh.read_bytes())
  for name,b in [('rig-reference.bin',ref)]:
   (a.output/name).write_bytes(b);assets[name]={'bytes':len(b),'sha256':sha(b)}
 meta={'format':1,'name':'Real huge RunCycle encoded-track probe for GEO_Sleeves_Wretch','container':'COHRIG01','base':bm,'motion':mm,'palette_global_ids':pins['palette_global_ids'],'socket_global_id':pins['socket_global_id'],'required_global_ids':sorted(required),'first_frame':1,'last_frame':25,'diagnostic_ticks_per_second':30,'source_move_rate':.7,'full_sequencer_speed_model_applied':False,'geom_scale_applied':False,'bone_morphing_applied':False,'encoded_source_keys_preserved':True,'runtime_sampler_required':True,'reference':reference_meta,'model':material_meta.get('model',{}),'textures':material_meta.get('textures',[]),'material':material_meta.get('material',{}),'material_binding':material_meta.get('material_binding',{}),'oracle_kind':'original-source-local-sampler + independent-source-semantic-hierarchy-palette','original_cg_execution':False,'original_gpu_driver_texture_capture':False,'binding':pins['binding'],'assets':assets}
 (a.output/'animation-fixture.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps({'prepared':True,'assets':assets,'base_bones':bm['bone_count'],'motion_bones':mm['bone_count'],'required_global_ids':sorted(required),'frame_interval':[1,25]},indent=2))
if __name__=='__main__':main()
