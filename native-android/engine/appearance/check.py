#!/usr/bin/env python3
"""Opt-in Gate31 costume assembly qualification; no accepted files are modified.
--source-root is a full checkout with upstream original source/data. --corpus-root
may provide hash-pinned authentic GEO files, rig.bin and morph.bin. A compile is
not an Android execution/physical qualification. JSON explicitly records gaps.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,os,shlex,struct,subprocess,sys,tempfile,time
HERE=Path(__file__).resolve().parent;NATIVE=HERE.parents[1]
sys.path.insert(0,str(HERE/'tests'))
from bindings import *
import source_data,original_oracle

def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run(cmd,**kw):return subprocess.run(list(map(str,cmd)),check=True,**kw)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def defs_from(records):return (Def*len(records))(*(Def(b(d['name']),b(d['geometry_name']),b(d['texture_name']),b(d['base_name']),(u32*2)(*(d['sockets']+[0])[:2]),len(d['sockets']),0) for d in records))
def parts_from(records):return (Part*len(records))(*(Part(p['definition'],b(p['geometry']),(C.c_char_p*2)(*map(b,p['textures'])),((C.c_uint8*4)*4)(*((C.c_uint8*4)(*col) for col in p['colors']))) for p in records))
def source_compare(lib,ref,corpus):
 configure(lib);ref.ref_ent.argtypes=[C.c_int];ref.ref_ent.restype=C.c_char_p;ref.ref_tex.argtypes=[C.c_int];ref.ref_tex.restype=C.c_char_p
 ref.ref_geometry.argtypes=[C.POINTER(Body),C.POINTER(Def),C.c_char_p,C.POINTER(C.c_char_p),C.c_int,Probe,C.c_void_p,C.c_void_p,C.c_void_p]
 ref.ref_textures.argtypes=[C.POINTER(Body),C.POINTER(Def),C.c_char_p,C.c_char_p,Probe,C.c_void_p,C.c_void_p]
 ref.ref_colors.argtypes=[C.c_void_p,C.c_void_p,C.c_char_p,C.c_void_p]
 for body in range(9):
  result=Body();ent=b'custom' if body==6 else None;assert lib.coh_appearance_body(body,ent,ent,C.byref(result))==0
  assert result.ent_type==(ent or ref.ref_ent(body));assert result.texture_prefix==(ent or ref.ref_tex(body))
 defs=defs_from(corpus['definitions']);workspace=Workspace();out=(Draw*120)();n=C.c_size_t();diag=Diagnostics();rows=[];comparisons=0;colors=0
 # Existence behavior varied independently; these are mocked asset inventories,
 # clearly distinct from the authentic costume data and original executed code.
 probe_sets=[set(),{'SF_FACE_none.tga','SH_HIPS_none.tga','SM_CHEST_skin_01a.tga'}, {'huge_BACK.GEO_BACK_Armored_Tight','V_Wretch_FACE_skin_01a.tga'}]
 for original in corpus['costumes']:
  parts=parts_from(original['parts']);body=Body();assert lib.coh_appearance_body(original['body'],b(original['ent_type']),b(original['prefix']),C.byref(body))==0
  total_draws=0
  for inventory in probe_sets:
   callback=Probe(lambda ctx,kind,key:int(key.decode() in inventory));links=(C.c_char_p*2)(b'Armored',b'Jacket')
   request=Request(body,defs,len(defs),parts,len(parts),17,(C.c_uint8*4)(*original['skin']),links,2,callback,None,Cancel())
   status=lib.coh_appearance_assemble(C.byref(request),C.byref(workspace),out,120,C.byref(n),C.byref(diag));assert status==0,(original['name'],status)
   wanted=[]
   for p in parts:
    d=defs[p.definition];raw=C.create_string_buffer(512);bones=(C.c_int*2)();count=ref.ref_geometry(C.byref(body),C.byref(d),p.geometry,links,2,callback,None,raw,bones)
    calls={bones[j]:raw.raw[j*256:(j+1)*256].split(b'\0')[0] for j in range(count)}
    if not calls:continue
    tex=C.create_string_buffer(512);ref.ref_textures(C.byref(body),C.byref(d),p.texture[0],p.texture[1],callback,None,tex)
    color=C.create_string_buffer(8);ref.ref_colors(request.skin,p.color,p.texture[0],color)
    for socket,key in calls.items():wanted.append((p.definition,socket,key,tex.raw[:256].split(b'\0')[0],tex.raw[256:].split(b'\0')[0],color.raw))
   assert n.value==len(wanted),(original['name'],n.value,len(wanted))
   for d,want in zip(out,wanted):
    observed=(d.definition,d.socket,d.geometry_key,bytes(d.texture[0]).split(b'\0')[0],bytes(d.texture[1]).split(b'\0')[0],bytes(d.color)[:8])
    assert observed==want,(original['name'],observed,want);assert d.generation==17;comparisons+=5;colors+=8
   total_draws=n.value
  rows.append({'name':original['name'],'body_type':original['body'],'parts':len(parts),'draw_requests':total_draws,'source':original['source'],'source_sha256_lf':original['source_sha256_lf'],'all_names_sockets_colors_exact':True,'actual_new_model_rendering':False})
 # Target branches beyond fixture coverage, compared against original source.
 branch_defs=[Def(b'Boots',b'LLeg',b'BOOT',b'BOOT',(u32*2)(25,26),2,0),Def(b'Back',b'BACK',b'BACK',b'BACK',(u32*2)(48,0),1,0)]
 branch_geos=['file.geo/GEO_LLeg*_Test','file.geo/GEO_LLegR_Test','file.geo/GEO_LLegL_Test','file.geo/GEO_Unspecified','None','Smooth','file.geo/GEO_Back_Test']
 for bd in branch_defs:
  for geo in branch_geos:
   parts=(Part*1)(Part(0,b(geo),(C.c_char_p*2)(b'skin_01a',b'mask'),((C.c_uint8*4)*4)()))
   callback=Probe(lambda ctx,kind,key:int(key.decode().endswith('_Armored') or key.decode().endswith('_Armored_Smooth') or key==b'SF_BACK_skin_01a.tga'))
   body=Body();assert lib.coh_appearance_body(1,None,None,C.byref(body))==0;links=(C.c_char_p*1)(b'Armored');request=Request(body,C.pointer(bd),1,parts,1,1,(C.c_uint8*4)(1,2,3,255),links,1,callback,None,Cancel())
   assert lib.coh_appearance_assemble(C.byref(request),C.byref(workspace),out,120,C.byref(n),C.byref(diag))==0
   raw=C.create_string_buffer(512);bones=(C.c_int*2)();count=ref.ref_geometry(C.byref(body),C.byref(bd),b(geo),links,1,callback,None,raw,bones);wanted={bones[j]:raw.raw[j*256:(j+1)*256].split(b'\0')[0] for j in range(count)}
   assert {out[j].socket:out[j].geometry_key for j in range(n.value)}==wanted,(geo,bd.name,wanted,[x.geometry_key for x in out[:n.value]])
   comparisons+=n.value
 return {'passed':True,'body_descriptors_exact':9,'authentic_costumes':rows,'source_identity_comparisons':comparisons,'color_bytes_compared':colors,'branch_cases':len(branch_defs)*len(branch_geos),'existence_inventories_mocked':True,'original_gpu_or_fullclient_execution':False}

def adapters(lib,root,source_root,temp):
 if not root:return {'run':False,'reason':'No corpus supplied'}
 asset=module('appearance_asset_types',NATIVE/'engine/assets/check.py');lib.coh_asset_geo_workspace.argtypes=[asset.Bytes,C.POINTER(C.c_size_t)];lib.coh_asset_geo_open.argtypes=[asset.Bytes,C.c_void_p,C.c_size_t,u32,C.POINTER(asset.Geo)];lib.coh_appearance_geo_model.argtypes=[C.POINTER(asset.Geo),C.POINTER(Draw),u32,C.POINTER(u32),C.POINTER(asset.Model)]
 models=0;files=[];items=[];pins={r['file_name']:r for r in json.loads((HERE/'corpus-pins.json').read_text())['records']}
 for p in sorted(root.glob('*.geo')):
  raw=p.read_bytes();pin=pins[p.name];assert len(raw)==pin['size'] and sha(p)==pin['sha256'];items.append({'virtual':pin['name'],'raw':raw,'sha256':pin['sha256'],'pin':'engine/appearance/corpus-pins.json'});data=C.create_string_buffer(raw);span=asset.Bytes(C.addressof(data),len(raw));size=C.c_size_t();assert lib.coh_asset_geo_workspace(span,C.byref(size))==0;pinned=C.create_string_buffer(size.value);geo=asset.Geo();assert lib.coh_asset_geo_open(span,pinned,size.value,4096,C.byref(geo))==0
  version,payload,reference=asset.reference(raw)
  for i,want in enumerate(reference):
   draw=Draw();draw.model_name=want['name'].split('__')[0].swapcase().encode();index=u32(999);model=asset.Model();assert lib.coh_appearance_geo_model(C.byref(geo),C.byref(draw),4096,C.byref(index),C.byref(model))==0;assert index.value==i and model.name.decode()==want['name'];models+=1
  absent=Draw();absent.model_name=b'GEO_Missing';index=u32(999);model=asset.Model();before=bytes(model);assert lib.coh_appearance_geo_model(C.byref(geo),C.byref(absent),4096,C.byref(index),C.byref(model))==3 and index.value==999 and bytes(model)==before
  files.append({'name':p.name,'bytes':len(raw),'sha256':sha(p),'model_count':len(reference),'source_GEO_reference_exact':True})
 rigs={'run':False};rigpath=root/'rig.bin';morphpath=root/'morph.bin'
 if rigpath.is_file() and morphpath.is_file():
  types=module('appearance_actor_types',NATIVE/'tools/character_fixture/_types.py');types.configure(lib);Rig,Pose,Morph=types.Rig,types.Pose,types.Morph;rb=C.create_string_buffer(rigpath.read_bytes());mb=C.create_string_buffer(morphpath.read_bytes());rig=Rig();morph=Morph();assert lib.coh_animation_parse(C.cast(rb,C.POINTER(C.c_uint8)),len(rb)-1,C.byref(rig))==0 and lib.coh_character_parse_morph(C.cast(mb,C.POINTER(C.c_uint8)),len(mb)-1,C.byref(morph))==0
  lib.coh_appearance_palette.argtypes=[C.POINTER(Draw),u32,C.POINTER(Rig),C.POINTER(Morph),C.POINTER(Pose),C.POINTER(u32),u32,C.c_void_p,C.c_size_t]
  binding=json.loads((NATIVE/'character-probe/contract/binding.json').read_text());samples=0
  for frame in [1.,1.125,7.,13.,24.999,25.]:
   pose=Pose();assert lib.coh_character_sample(C.byref(rig),C.byref(morph),frame,C.byref(pose))==0
   for part in binding['parts']:
    ids=(u32*len(part['palette_global_ids']))(*part['palette_global_ids']);a=(C.c_float*(len(ids)*12))();d=(C.c_float*len(a))();draw=Draw();draw.socket=part['socket_global_id']
    assert lib.coh_appearance_palette(C.byref(draw),4,C.byref(rig),C.byref(morph),C.byref(pose),ids,len(ids),a,len(a))==0
    assert lib.coh_character_palette(C.byref(rig),C.byref(morph),C.byref(pose),draw.socket,ids,len(ids),d)==0 and bytes(a)==bytes(d);samples+=len(a)
   before=bytes(a);assert lib.coh_appearance_palette(C.byref(draw),1,C.byref(rig),C.byref(morph),C.byref(pose),ids,len(ids),a,len(a))==2 and bytes(a)==before
  rigs={'run':True,'passed':True,'accepted_palette_float_components_exact':samples,'rig_sha256':sha(rigpath),'morph_sha256':sha(morphpath),'new_body_morph_support':False,'reference':'existing accepted unchanged character palette kernel'}
 decode_temp=temp/'original-delta';decode_temp.mkdir()
 decode=asset.source_oracle(lib,items,source_root,decode_temp) if items else {'passed':False,'reason':'No authenticated GEO files supplied'}
 return {'run':True,'GEO_models_exact':models,'files':files,'accepted_rig_regression':rigs,'original_source_delta_decode':decode}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--corpus-root',type=Path);p.add_argument('--sanitize',action='store_true');p.add_argument('--ndk',type=Path);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True)
 corpus=source_data.load(a.source_root);base=['cc','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-ffp-contract=off','-fno-fast-math'];sources=[HERE/'coh_appearance.c',HERE/'coh_appearance_adapters.c',NATIVE/'character/coh_character.c',NATIVE/'engine/assets/coh_asset_geo.c',NATIVE/'engine/assets/coh_asset_loader.c',NATIVE/'src/coh_assets.c',NATIVE/'src/coh_dds.c'];include=['-I',str(NATIVE/'include')];main_sources=[*sources,HERE/'tests/host.c',HERE/'tests/adapters.c',HERE/'tests/corpus.c']
 with tempfile.TemporaryDirectory(prefix='coh-appearance-') as td:
  temp=Path(td);exe=temp/'host';run([*base,'-O2',*include,*main_sources,'-lz','-lm','-o',exe]);host=json.loads(subprocess.check_output([str(exe)]+([str(a.corpus_root)] if a.corpus_root else []),text=True));so=temp/'appearance.so';run([*base,'-O0','-fPIC','-shared',*include,*sources,'-lz','-lm','-o',so]);lib=C.CDLL(str(so));ref,pins=original_oracle.build(a.source_root,temp,HERE);oracle=source_compare(lib,ref,corpus);adapter_result=adapters(lib,a.corpus_root,a.source_root,temp)
  pin_report={'source_files':corpus['source_pins'],'executed_functions':pins};pinfile=HERE/'source-pins.json'
  assert pin_report==json.loads(pinfile.read_text()),'source pin mismatch'
  san={'run':False}
  if a.sanitize:
   sx=temp/'san';run([*base,'-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',*include,*main_sources,'-lz','-lm','-o',sx]);env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1');san={'run':True,'asan':True,'ubsan':True,'result':json.loads(subprocess.check_output([str(sx)]+([str(a.corpus_root)] if a.corpus_root else []),text=True,env=env)),'leak_detection':False,'note':'Fixed caller workspace and output. Module uses no heap. LeakSanitizer disabled for restricted /proc environment.'}
  arm={'built':False}
  if a.ndk:
   cc=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/aarch64-linux-android26-clang';objects=[]
   for source in sources:
    obj=temp/(source.stem+'.o');run([cc,*base[1:],'-O2','-fPIC',*include,'-c',source,'-o',obj]);objects.append(obj)
   target=temp/'libcoh_appearance.so';run([cc,'-shared','-Wl,--no-undefined',*objects,'-lz','-lm','-o',target]);elf=subprocess.check_output([str(a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-readelf'),'-h',str(target)],text=True);assert 'AArch64' in elf;arm={'built':True,'api':26,'abi':'arm64-v8a','library_sha256':sha(target),'library_bytes':target.stat().st_size,'elf_machine':'AArch64','undefined_symbols_link_rejected':True,'emulator_executed':False,'physical_executed':False}
  report={'schema':'coh-appearance-gate31-v1','implemented':True,'host_qualified':True,'arm64_built':arm['built'],'emulator_qualified':False,'physical_qualified':False,'host':host,'source_oracle':oracle,'adapters':adapter_result,'sanitizers':san,'android':arm,'source_pins':pin_report,'limitations':['Full Gate31 remains pending: new Male/Female morphology/rig/GPU output is not qualified.','New original GEO resources are parsed/resolved without full costume texture/material/GPU playback.','Source Costume/BodyPart parsing is test tooling; production importer must construct validated public API records.','No live server, session, renderer, JNI, accepted APK or network code changes.']};a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ['implemented','host_qualified','arm64_built','emulator_qualified','physical_qualified','host']}))
if __name__=='__main__':main()
