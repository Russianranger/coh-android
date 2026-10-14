#!/usr/bin/env python3
"""Prepare the source Atlas bench branch, raw camera inputs and references."""
from pathlib import Path
import argparse, ctypes as C, json, struct, subprocess, sys, zlib
import geo_prepare as geo

ROOT=Path(__file__).resolve().parents[2]

def scene(meshes,parts,textures,math_inputs):
    geo.require(len(meshes)==len(parts)==2 and len(textures)==4,'exact world closure differs')
    geo.require(len(math_inputs)==520 and math_inputs[:8]==b'COHWRI09','world raw math input envelope differs')
    po=128;to=po+len(parts)*96;mo=to+len(textures)*32;dataoff=mo+len(math_inputs)
    cursor=dataoff;mesh_spans=[];texture_spans=[]
    for raw in meshes:mesh_spans.append((cursor,len(raw)));cursor+=len(raw)
    for texture in textures:
        raw=texture['rgba'];texture_spans.append((cursor,len(raw)));cursor+=len(raw)
    header=struct.pack('<8s14I',b'COHWOR09',1,128,len(parts),len(textures),
        512,564,po,96,to,32,mo,len(math_inputs),dataoff,cursor)+bytes(64)
    records=[]
    for i,p in enumerate(parts):
        rec=bytearray(96);struct.pack_into('<6I',rec,0,*mesh_spans[i],5,p['base_texture'],p['dual_texture'],p['flags'])
        for off,key in [(24,'color1'),(40,'color2')]:
            color=[geo.f32(geo.f32(v)*geo.f32(1./255.)) for v in p[key]]+[1.]
            struct.pack_into('<4f',rec,off,*color)
        struct.pack_into('<3fI',rec,56,p['diffuse_scale'],p['ambient_scale'],p['alpha_ref'],p['mode'])
        records.append(bytes(rec))
    trecords=[]
    for i,t in enumerate(textures):
        trecords.append(struct.pack('<4I',*texture_spans[i],t['width'],t['height'])+bytes(16))
    raw=header+b''.join(records)+b''.join(trecords)+math_inputs+b''.join(meshes)+b''.join(t['rgba'] for t in textures)
    geo.require(len(raw)==cursor,'world scene container size differs')
    return raw,{'container':'COHWOR09','header_bytes':128,'part_stride':96,'texture_stride':32,
        'part_count':len(parts),'texture_count':len(textures),'canonical_vertices':512,'indices':564,
        'source_vertices':256,'source_root_instances':1,'source_group_nodes':6,'source_group_node_per_part':5,
        'static_identity_adapter':True,'input_math_container':'COHWRI09','input_math_bytes':520,
        'reference_matrices_drive_rendering':False,'world_coordinates_preserved':True,'bytes':len(raw),'sha256':geo.sha(raw)}

def source_file(source_dir,name,relative):
    return source_dir/name if source_dir else ROOT.parent/relative

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--corpus',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--evidence-output',type=Path);ap.add_argument('--source-directory',type=Path)
    ap.add_argument('--source-trick-audit',type=Path,
        help='Previously verified full immutable source declaration receipt; absent stays explicitly pending')
    ap.add_argument('--library',type=Path);a=ap.parse_args()
    evidence=a.evidence_output or ROOT/'results/world-fixture-evidence';evidence.mkdir(parents=True,exist_ok=True)
    a.output.mkdir(parents=True,exist_ok=True)
    pins=json.loads(Path(__file__).with_name('pins.json').read_text())
    recovery_path=ROOT/'evidence/phase9/scene-recovery.json'
    recovery=json.loads(recovery_path.read_text())
    scene_relative='upstream/i24/data/maps/city_zones/city_01_01/city_01_01_layer_geometry.txt'
    authored=source_file(a.source_directory,'city_01_01_layer_geometry.txt',scene_relative).read_bytes()
    scene_pin=next(pin for pin in recovery['source_pins'] if pin['path']==scene_relative)
    geo.require(len(authored)==scene_pin['bytes'] and geo.sha(authored)==scene_pin['sha256'],
        'original authored scene source pin differs')
    for pin in pins['records']:
        raw=(a.corpus/pin['file_name']).read_bytes()
        geo.require(len(raw)==pin['size'] and f'{zlib.crc32(raw):08x}'==pin['crc32']
            and geo.sha(raw)==pin['sha256'],'world corpus member identity differs: '+pin['id'])
    library=a.library
    if library is None:
        build=evidence/'native-core';subprocess.run([sys.executable,str(ROOT/'tools/build.py'),'--output',str(build)],check=True,stdout=subprocess.DEVNULL)
        library=build/'libcoh_native_core.so'
    lib=C.CDLL(str(library.resolve()));decoder=lib.coh_dds_rgba
    decoder.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.c_void_p,C.c_size_t]
    textures=[];texmeta=[]
    for i,name in enumerate(['signmetal','grey','modern_bench','white']):
        filename=pins['texture_files'][name];raw=(a.corpus/filename).read_bytes()
        rgba,w,h,meta=geo.accepted.decode_texture(raw,decoder)
        head,size,ww,hh,flags,fade0,fade1,alpha,version=struct.unpack_from('<iiiiIffB3s',raw)
        dds=geo.span(raw,head,size);mips=max(1,geo.u32(dds,28))
        geo.require((w,h)==(ww,hh),'world wrapper/DDS dimensions differ')
        if name=='white':geo.require(rgba==bytes([255])*(w*h*4),'actual white pixels differ')
        if name=='grey':geo.require(rgba==bytes([128,128,128,255])*(w*h),'actual grey pixels differ')
        textures.append({'name':name,'rgba':rgba,'width':w,'height':h})
        meta.update(index=i,name=name,source_file=filename,wrapper_flags=flags,
            wrapper_fade=[fade0,fade1],wrapper_alpha=alpha,wrapper_version=version.decode('ascii'),
            source_mip_count=mips,selected_mip=0,rgba_bytes=len(rgba),rgba_sha256=geo.sha(rgba),
            alpha_minimum=min(rgba[3::4]),alpha_maximum=max(rgba[3::4]),
            synthetic_game_fixture=False,stock_engine_texture_default=name in ('white','grey'))
        texmeta.append(meta)
    source=(a.corpus/'misc.geo').read_bytes();meshes,vertices,meshmeta,_=geo.make(source)
    materials=json.loads((ROOT/'world-probe/contract/materials.json').read_text())
    source_trick_audit=None
    if a.source_trick_audit:
        source_trick_audit=json.loads(a.source_trick_audit.read_text())
        material_pins=json.loads((ROOT/'world-probe/contract/source-material-pins.json').read_text())
        geo.require(source_trick_audit.get('passed') is True
            and source_trick_audit.get('kind')=='complete immutable original trick declaration audit'
            and source_trick_audit.get('git_tree_sha')==material_pins['tricks_tree']['git_tree_sha']
            and source_trick_audit.get('source_files_verified')==material_pins['tricks_tree']['file_count']
            and source_trick_audit.get('primary_source_files_verified')==[
                {k:p[k] for k in ('path','bytes','sha256')} for p in material_pins['source_files']],
            'source declaration audit receipt has not passed')
    geo.require(len(materials['parts'])==2,'world material closure count differs')
    lookup={t['name']:i for i,t in enumerate(textures)};parts=[]
    for i,resolved in enumerate(materials['parts']):
        original=meshmeta['parts'][i]
        geo.require(resolved['part_index']==i and resolved['geometry_texture'].casefold()==original['name'].casefold(),
            'world material partition mapping differs')
        p=dict(original);p.update(base_texture=lookup[resolved['base_alias'].casefold()],dual_texture=lookup[resolved['dual_alias'].casefold()],
            flags=(1 if resolved.get('double_sided',False) else 0)|(2 if resolved.get('blend_enabled',False) else 0),
            color1=resolved['effective_colors_rgb'][0],color2=resolved['effective_colors_rgb'][1],
            diffuse_scale=resolved['diffuse_scale'],ambient_scale=resolved['ambient_scale'],
            alpha_ref=resolved['alpha_ref'],mode=resolved['mode'],source_material=resolved)
        parts.append(p)
    original=geo.original_delta_check(source,source_file(a.source_directory,'anim.c','upstream/ouroboros/Common/seq/anim.c'))
    (evidence/'original-delta-parity.json').write_text(json.dumps(original,indent=2)+'\n')
    # Camera/group source execution and independent references are a separate
    # contract. Runtime reads raw Pos/PYR, never these golden matrices.
    contract=geo.module('world_camera_reference',Path(__file__).with_name('world_reference.py'))
    flat_vertices=[v for part in vertices for v in part]
    math_inputs=contract.make_inputs(flat_vertices)
    reference=contract.generate(math_inputs,flat_vertices)
    original_world=geo.module('world_original_camera_group',Path(__file__).with_name('original_world_check.py'))
    samples,parity=original_world.qualify(math_inputs,flat_vertices,a.source_directory)
    (evidence/'original-world-samples.json').write_text(json.dumps(samples,indent=2)+'\n')
    (evidence/'original-world-parity.json').write_text(json.dumps(parity,indent=2)+'\n')
    rmeta={'container':'COHWRF09','bytes':len(reference),'sha256':geo.sha(reference),
        'reference_cameras':6,'reference_nodes':6,'reference_vertices':512,
        'reference_parts':2,'camera_matrix_floats':40,'vertex_output_floats':13,
        'camera_case_stride':26784,'camera_geometry_offset':160,
        'original_eye_traversal_composition_order':True,
        'source_map_group_locals':True,'source_ancestor_chain_retained':True,
        'reference_kind':'independent Python row-matrix binary32 semantic oracle',
        'reference_data_drive_rendering':False,'camera_inputs':'controlled PYR/FOV/aspect at actual source world coordinates',
        'gameplay_fov_adjustment_selected':False,'clip_space_convention':'original OpenGL frustum'}
    world,smeta=scene(meshes,parts,textures,math_inputs)
    material=geo.module('world_material_reference',ROOT/'world-probe/contract/build_material_reference.py')
    material.self_check();material_raw,cases=material.prepare(parts,textures)
    assets={'world.bin':world,'world-reference.bin':reference,'material-reference.bin':material_raw}
    for name,raw in assets.items():(a.output/name).write_bytes(raw)
    meta={'format':1,'name':'Atlas Park authored modern_bench_2wide branch',
        'source_release':pins['release_tag'],'source_commit':pins['source_commit'],
        'parts':parts,'meshes':meshmeta,'textures':texmeta,'scene':smeta,'reference':rmeta,
        'resolved_materials':materials,
        'source_trick_resolution_qualified':source_trick_audit is not None,
        'source_trick_resolution_audit':source_trick_audit,
        'authored_scene':{'source_file':scene_relative,'source_bytes':len(authored),
            'source_sha256':geo.sha(authored),'selected_transform_chain':recovery['selected_transform_chain'],
            'selected_group_block_pins':recovery['source_group_block_pins'],
            'inherited_authored_properties':recovery['inherited_authored_properties'],
            'source_tint_rgb':[[67,139,202],[0,0,0]],'source_ambient_rgb':[28,31,40],
            'complete_ancestor_chain_preserved':True,'sibling_branches_loaded':False,
            'texswap_cubemap_runtime_resolved':False,'atlas_ambient_lighting_reconstructed':False,
            'full_original_scene_sorter_qualified':False,'source_lod_trick':'mbench',
            'source_lod_far':250,'source_lod_far_fade':75,'runtime_lod_selection_qualified':False},
        'material':{'container':'COHWMAT9','oracle':'independent source-semantic scalar',
            'width':64,'height':64,'case_count':len(cases),'cases_per_part':6,
            'original_cg_execution':False,'original_gpu_driver_texture_capture':False,'cases':cases},
        'native_generator_library_sha256':geo.sha(library.read_bytes()),
        'original_world_parity_sha256':geo.sha((evidence/'original-world-parity.json').read_bytes()),
        'original_delta_parity_sha256':geo.sha((evidence/'original-delta-parity.json').read_bytes()),
        'oracle_kind':'unchanged source camera/group kernels plus independent hierarchy, geometry and shader scalar references',
        'assets':{name:{'bytes':len(raw),'sha256':geo.sha(raw)} for name,raw in assets.items()}}
    encoded=(json.dumps(meta,indent=2)+'\n').encode()
    geo.require(len(encoded)<=512<<10,'world fixture metadata exceeds bounded loader budget')
    (a.output/'world-fixture.json').write_bytes(encoded);(evidence/'fixture-metadata.json').write_bytes(encoded)
    print(json.dumps({'prepared':True,'parts':len(parts),'source_vertices':256,'vertices':512,
        'triangles':188,'indices':564,'textures':len(textures),'material_cases':len(cases),'assets':meta['assets']},indent=2))

if __name__=='__main__':main()
