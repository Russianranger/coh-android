#!/usr/bin/env python3
"""Build the real bounded Wretch character fixture and independent references.

The APK receives original raw animation keys and authored morphology inputs.
Palettes and vertex goldens exist only in the independent comparison asset.
The selected material is the original automatic low quality COLORBLEND_DUAL
fallback; high quality MULTI/bump/reflection rendering remains a later gate.
"""
from pathlib import Path
import argparse, ctypes as C, importlib.util, json, subprocess, sys
import geo, morph, scene

ROOT=Path(__file__).resolve().parents[2]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec); spec.loader.exec_module(obj); return obj

def make(corpus,output,library,bones_source):
    pins=json.loads(Path(__file__).with_name('pins.json').read_text())
    binding=json.loads((ROOT/'character-probe/contract/binding.json').read_text())
    materials=json.loads((ROOT/'character-probe/contract/materials.json').read_text())
    geo.require(len(materials['parts'])==11,'source material part count differs')
    for pin in pins['records']:
        raw=(corpus/pin['file_name']).read_bytes()
        geo.require(len(raw)==pin['size'] and geo.sha(raw)==pin['sha256'],'source fixture size/SHA256 differs: '+pin['id'])
    meshes=[]; meshmeta=[]; parts=[]; textures=[]; texturemeta=[]; texture_ids={}
    lib=C.CDLL(str(library.resolve())); decoder=lib.coh_dds_rgba
    decoder.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.c_void_p,C.c_size_t]
    def texture(alias):
        alias=alias.casefold()
        if alias in texture_ids:return texture_ids[alias]
        index=len(textures)
        file=pins['texture_files'].get(alias)
        geo.require(file is not None,'source texture alias not pinned: '+alias)
        rgba,w,h,meta=geo.accepted.decode_texture((corpus/file).read_bytes(),decoder)
        meta.update(name=alias,source_file=file,alpha_range=[min(rgba[3::4]),max(rgba[3::4])])
        if alias=='white':
            geo.require(rgba==bytes([255])*(w*h*4),'actual stock white pixels differ')
            meta.update(stock_engine_texture_default=True,
                source_semantics='tex.c white_tex=texFind("white"); source none fallback',
                synthetic_game_fixture=False)
        textures.append({'name':alias,'rgba':rgba,'width':w,'height':h})
        meta.update(index=index,rgba_bytes=len(rgba),rgba_sha256=geo.sha(rgba),
            alpha_minimum=min(rgba[3::4]),alpha_maximum=max(rgba[3::4]),alpha_unique_values=len(set(rgba[3::4])))
        texturemeta.append(meta); texture_ids[alias]=index; return index
    for authored,resolved in zip(binding['parts'],materials['parts']):
        geo.require(authored['index']==resolved['part_index'] and authored['part']==resolved['part'] and authored['effective_colors_rgb']==resolved['effective_colors_rgb'],'source material/costume draw mapping differs')
        raw,vertices,bones,meta=geo.mesh((corpus/authored['file_name']).read_bytes(),authored['model'],authored['socket_global_id'])
        geo.require(bones==authored['palette_global_ids'] and len(vertices)==authored['vertex_count'] and meta['triangle_count']==authored['triangle_count'],'authored part identity differs')
        meshes.append(raw); meshmeta.append(meta)
        base,dual=resolved['base_alias'].casefold(),resolved['dual_alias'].casefold()
        part=dict(authored); part.update(base_texture=texture(base),dual_texture=texture(dual),
            fallback_base_alias=base,fallback_dual_alias=dual,
            source_double_sided=resolved['double_sided'],source_material=resolved,
            color1=authored['effective_colors_rgb'][0],color2=authored['effective_colors_rgb'][1])
        parts.append(part)
    geo.require(sum(x['vertex_count'] for x in meshmeta)==2626 and sum(x['triangle_count'] for x in meshmeta)==2986 and sum(x['genuinely_blended_vertices'] for x in meshmeta)==620,'full character cardinalities differ')
    character,cmeta=scene.make(meshes,parts,textures)
    mraw,mmeta=morph.make(corpus,bones_source)
    anim=module('character_accepted_animation_preparer',ROOT/'tools/animation_fixture/prepare.py')
    base,motion=(corpus/'base.anim').read_bytes(),(corpus/'motion.anim').read_bytes()
    bm,_=anim.inspect_animation(base); mm,_=anim.inspect_animation(motion)
    geo.require(bm['name'].casefold()=='huge/skel_ready' and mm['name'].casefold()=='huge/run' and bm['bone_count']==60 and mm['bone_count']==44,'real rig identity differs')
    rig=anim.make_rig(base,motion,[9,5,7],72)
    material=module('character_material_oracle',ROOT/'character-probe/contract/build_character_material_reference.py')
    material.self_check(); materialraw,cases=material.prepare(parts,textures)
    output.mkdir(parents=True,exist_ok=True)
    for index,raw in enumerate(meshes):(output/('mesh'+str(index)+'.bin')).write_bytes(raw)
    assets={'character.bin':character,'rig.bin':rig,'morph.bin':mraw,'material-reference.bin':materialraw}
    for name,raw in assets.items():(output/name).write_bytes(raw)
    meta={'format':1,'name':'Arachnos_Wretch complete authored NPC geometry and morphology',
        'source_release':pins['release_tag'],'source_commit':pins['source_commit'],
        'parts':parts,'meshes':meshmeta,'textures':texturemeta,'scene':cmeta,'morphology':mmeta,
        'animation':{'base':bm,'motion':mm,'first_frame':1,'last_frame':25,'ticks_per_second':30,'effective_rate':1,
            'movement_derived_rate':False,'raw_encoded_source_keys_preserved':True,'native_runtime_sampler_required':True},
        'material':{'container':'COHCMAT8','oracle':'independent source-semantic scalar',
            'width':64,'height':64,'case_count':len(cases),'cases_per_part':6,
            'original_cg_execution':False,'original_gpu_driver_texture_capture':False,'cases':cases},
        'binding':binding,'resolved_materials':materials,'native_generator_library_sha256':geo.sha(library.read_bytes()),
        'oracle_kind':'unchanged-original-source-actor-locals + independent hierarchy/socket + source-semantic material',
        'scope_limits':binding['scope_limits'],
        'assets':{name:{'bytes':len(raw),'sha256':geo.sha(raw)} for name,raw in assets.items()}}
    return meta,meshes

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--corpus',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--evidence-output',type=Path); ap.add_argument('--source-directory',type=Path)
    ap.add_argument('--extra-source-directory',type=Path); ap.add_argument('--library',type=Path)
    ap.add_argument('--original-actor-samples',type=Path)
    a=ap.parse_args(); evidence=a.evidence_output or ROOT/'results/character-fixture-evidence'
    evidence.mkdir(parents=True,exist_ok=True)
    library=a.library
    if library is None:
        build=evidence/'native-core'; subprocess.run([sys.executable,str(ROOT/'tools/build.py'),'--output',str(build)],check=True,stdout=subprocess.DEVNULL)
        library=build/'libcoh_native_core.so'
    bones=(a.extra_source_directory/'bones.h') if a.extra_source_directory else (a.source_directory/'bones.h' if a.source_directory else ROOT.parent/'upstream/ouroboros/Common/seq/bones.h')
    meta,meshes=make(a.corpus,a.output,library,bones)
    source=(a.source_directory/'anim.c') if a.source_directory else ROOT.parent/'upstream/ouroboros/Common/seq/anim.c'
    cmd=[sys.executable,str(Path(__file__).with_name('original_delta_check.py')),'--corpus',str(a.corpus.resolve()),'--source',str(source.resolve()),'--output',str((evidence/'original-delta-parity.json').resolve())]
    subprocess.run(cmd,check=True)
    locals_path=a.original_actor_samples or evidence/'original-actor-samples.json'
    if a.original_actor_samples is None:
        cmd=[sys.executable,str(Path(__file__).with_name('original_actor_check.py')),
            '--rig',str((a.output/'rig.bin').resolve()),'--morph',str((a.output/'morph.bin').resolve()),
            '--output',str(locals_path.resolve()),'--report',str((evidence/'original-actor-parity.json').resolve())]
        if a.source_directory:cmd+=['--source-directory',str(a.source_directory.resolve())]
        if a.extra_source_directory:cmd+=['--extra-source-directory',str(a.extra_source_directory.resolve())]
        subprocess.run(cmd,check=True)
    contract=module('character_hierarchy_oracle',ROOT/'character-probe/contract/hierarchy_reference.py')
    reference,rmeta=contract.generate(json.loads(locals_path.read_text()),meshes,meta['binding'])
    (a.output/'character-reference.bin').write_bytes(reference)
    meta['reference']=rmeta; meta['assets']['character-reference.bin']={'bytes':len(reference),'sha256':geo.sha(reference)}
    meta['source_actor_samples_sha256']=geo.sha(locals_path.read_bytes())
    (a.output/'character-fixture.json').write_text(json.dumps(meta,indent=2)+'\n')
    for index in range(11):(a.output/('mesh'+str(index)+'.bin')).unlink()
    (evidence/'fixture-metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps({'prepared':True,'parts':11,'vertices':2626,'triangles':2986,
        'textures':len(meta['textures']),'material_cases':meta['material']['case_count'],'assets':meta['assets']},indent=2))

if __name__=='__main__':main()
