"""Additional authentic three-body combat/airborne/reaction pose qualification.

Raw key comparison executes the previously qualified original scalar decoder;
playback comparison independently executes original per-bone transition code.
No original PlayFx, registration, body morph or live session claim is made.
"""
import ctypes as C,hashlib,importlib.util,json,shutil,struct,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
NATIVE=HERE.parents[2]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out
def run(cmd):
    r=subprocess.run(list(map(str,cmd)),text=True,capture_output=True)
    if r.returncode:raise ValueError(r.stdout+r.stderr)
    return r.stdout
def qualify(root,extra,target,cc,landing=None):
    target.mkdir(parents=True,exist_ok=True)
    types=module('continuation_raw_types',NATIVE/'tools/animation_fixture/_types.py')
    prep=module('continuation_raw_prepare',NATIVE/'tools/animation_fixture/prepare.py')
    old=module('continuation_original_raw',NATIVE/'tools/animation_fixture/original_animation_check.py')
    original_dir=target/'original-source';original_dir.mkdir(exist_ok=True)
    for name,rel in old.PATHS.items():shutil.copyfile(root/rel,original_dir/name)
    source,pins=old.source_code(original_dir);source_path=target/'original-raw.c';source_path.write_text(source)
    rawso=target/'original-raw.so';run([cc,'-std=c11','-O0','-ffp-contract=off','-fno-strict-aliasing','-shared','-fPIC',source_path,'-lm','-o',rawso])
    original=C.CDLL(str(rawso));fp=C.POINTER(C.c_float)
    original.original_local.argtypes=[C.POINTER(C.c_uint8),C.POINTER(C.c_uint8),*[C.c_int]*5,C.c_float,C.c_int,fp]
    original.original_matrix.argtypes=[fp,fp,fp];original.original_math.argtypes=[fp,fp,fp,fp,fp]
    wrapper=target/'size.c';wrapper.write_text('#include "coh_seq_playback.h"\nsize_t playback_size(void){return sizeof(CohSeqPlayback);}\n')
    playbackso=target/'playback.so';run([cc,'-std=c11','-O2','-ffp-contract=off','-shared','-fPIC','-I',HERE.parent,HERE.parent/'coh_seq_playback.c',HERE.parent/'coh_sequencer.c',NATIVE/'animation/coh_animation.c',target.parent/'original-playback.c',wrapper,'-lm','-o',playbackso])
    lib=types.configure(C.CDLL(str(playbackso)));lib.playback_size.restype=C.c_size_t
    class Binding(C.Structure):_fields_=[('clip_id',C.c_uint32),('rig_id',C.c_uint32),('rig',C.POINTER(types.Rig))]
    class Selection(C.Structure):_fields_=[(x,C.c_uint32) for x in ['actor_id','rig_id','move','previous_move','clip_id','flags','cause']]+[(x,C.c_float) for x in ['frame','previous_frame','interpolate_frames']]
    class Cancel(C.Structure):_fields_=[('poll',C.c_void_p),('context',C.c_void_p)]
    class Event(C.Structure):_fields_=[('tick',C.c_uint64)]+[(x,C.c_uint32) for x in ['actor_id','rig_id','move','clip_id','type','kind','token']]+[('frame',C.c_float)]
    lib.coh_seq_playback_init.argtypes=[C.c_void_p,C.c_uint32,C.c_uint32,C.POINTER(Binding),C.c_size_t,C.c_void_p,C.c_size_t]
    lib.coh_seq_playback_sample.argtypes=[C.c_void_p,C.POINTER(Selection),C.c_uint64,C.c_float,C.c_uint64,Cancel,C.POINTER(types.Pose),C.POINTER(Event),C.c_size_t,C.POINTER(C.c_size_t)]
    lib.original_playback.argtypes=[C.POINTER(types.Rig),C.POINTER(types.Pose),C.c_int,C.c_float,C.c_float,C.c_uint32,C.POINTER(types.Pose)]
    total=0;maximum=0.;families=[];body_results=[];backing=[]
    def near(x,y,label):
        nonlocal total,maximum
        error=abs(x-y);total+=1;maximum=max(maximum,error)
        if error>3e-6+3e-6*abs(y):raise ValueError(f'{label} mismatch {x} vs {y}')
    for body,base_name in [('male','skel_ready2'),('fem','skel_ready2'),('huge','skel_ready')]:
        base_path=extra/'assets/player_library/animations'/body/(base_name+'.anim')
        if not base_path.exists():raise ValueError('missing authentic base '+str(base_path))
        base=base_path.read_bytes();base_t=old.raw_tracks(base);base_meta,parents=prep.inspect_animation(base)
        collection=[]
        for name,family in [('1_2punch','combat'),('jump_n_smash','jump power'),('fallout','reaction'),('comb_postjump' if body=='male' else 'combat_postjump','landing'),('a_yes_wave','emote')]:
            path=base_path.parent/(name+'.anim')
            if not path.exists() and landing:
                candidate=landing/'assets/player_library/animations'/body/(name+'.anim')
                if candidate.exists():path=candidate
            if not path.exists():continue
            raw=path.read_bytes();meta,_=prep.inspect_animation(raw)
            rigraw=bytearray(prep.make_rig(base,raw,[0],0));last=meta['length_frames'];struct.pack_into('<3f',rigraw,48,1.,last,30.)
            rig_path=target/(body+'-'+name+'.bin');rig_path.write_bytes(rigraw)
            mem=(C.c_uint8*len(rigraw)).from_buffer_copy(rigraw);backing.append(mem);rig=types.Rig()
            if lib.coh_animation_parse(mem,len(rigraw),C.byref(rig)):raise ValueError('qualified decoder rejected '+str(path))
            motion_t=old.raw_tracks(raw);ids=list(rig.order)[:rig.node_count]
            first={i:old.sample(original,base_t[i],0,True) for i in ids}
            initial={i:old.sample(original,motion_t[i],0) for i in motion_t}
            delta={i:[old.f32(initial[i][4+j]-first[i][4+j]) for j in range(3)] for i in motion_t if i in first}
            frames=sorted(set([1.,1.5,last/4,last/2,last-.5,last]))
            for frame in frames:
                pose=types.Pose()
                if lib.coh_animation_sample(C.byref(rig),frame,C.byref(pose)):raise ValueError('raw sample failed')
                for i in ids:
                    expected=old.sample(original,motion_t[i],frame) if i in motion_t else first[i]
                    for j in range(4):near(pose.rotation[i][j],expected[j],body+'/'+name+' rotation')
                    for j in range(3):near(pose.position[i][j],old.f32(expected[4+j]-delta[i][j]) if i in delta else expected[4+j],body+'/'+name+' translation')
            collection.append(rig);families.append({'body':body,'family':family,'asset':meta['name'],'source_sha256':meta['sha256'],'raw_bytes':len(raw),'clip_last':last,'bones':rig.node_count,'rig_file':str(rig_path),'rig_sha256':hashlib.sha256(rigraw).hexdigest()})
        bindings=(Binding*len(collection))(*[Binding(i,100,C.pointer(r)) for i,r in enumerate(collection)])
        state=C.create_string_buffer(lib.playback_size());events=(Event*257)();count=C.c_size_t();out=types.Pose();raw=types.Pose();expected=types.Pose()
        if lib.coh_seq_playback_init(state,10,100,bindings,len(collection),None,0):raise ValueError('new body playback initialization failed')
        lib.original_reset();generation=0;tick=0
        for iteration in range(250):
            move=iteration%len(collection);rig=collection[move];generation+=1
            for step in range(6):
                tick+=1;frame=min(1.+step*.5,rig.last_frame);sel=Selection(10,100,move,0,move,0,0,frame,0,5)
                if lib.coh_animation_sample(C.byref(rig),frame,C.byref(raw)):raise ValueError('family sample failed')
                if lib.coh_seq_playback_sample(state,C.byref(sel),generation,.5,tick,Cancel(),C.byref(out),events,257,C.byref(count)):raise ValueError('family playback failed')
                lib.original_playback(C.byref(rig),C.byref(raw),int(step==0),.5,5,0,C.byref(expected))
                for id in list(rig.order)[:rig.node_count]:
                    for array,n in [('position',3),('rotation',4),('world_rows',12)]:
                        for j in range(n):near(getattr(out,array)[id][j],getattr(expected,array)[id][j],body+' blended '+array)
        body_results.append({'body':body,'poses':1500,'authentic_clips':len(collection)})
    # Extend through the original graph exporter; missing links remain explicit.
    exporter=module('continuation_source_graph',HERE.parent/'tools/source_fixture.py')
    exporter.SELECTED={'player/motion/motion_jump.inc':['JumpPost'],
        'player/powers.inc':['1_2punch','1_2punchpost','jumpNsmash','jumpNsmash_post'],
        'player/reactions.inc':['Fallout']}
    graph=exporter.export(root,root.parent/'i24')
    by_name={x['asset'].casefold():x for x in families}
    for move in graph['moves']:
        for body,clip in move['types'].items():
            identity=clip.get('asset','').removeprefix('ANIMS/').removesuffix('.anim').casefold()
            if identity in by_name and clip.get('last_frame') is None:clip['last_frame']=by_name[identity]['clip_last']
    graph_pin=HERE/'fixtures/expanded_graph.json'
    if graph_pin.exists() and json.loads(graph_pin.read_text())!=graph:raise ValueError('expanded authored graph pins changed; inspect before admission')
    (target/'expanded_graph.json').write_text(json.dumps(graph,indent=2)+'\n');exporter.write_header(graph,target/'expanded_graph.h')
    fem=[]
    for index,move in enumerate(graph['moves']):
        clip=move['types'].get('fem');identity=clip.get('asset','').removeprefix('ANIMS/').removesuffix('.anim').casefold() if clip else ''
        if not clip or clip.get('last_frame') is None or identity not in by_name:fem.append('{{NULL,1},'+str(index)+',0,0,0,1},')
        else:fem.append('{{'+json.dumps(clip['asset'])+',1},'+f'{index},1,{clip["first_frame"]}f,{clip["last_frame"]}f,{clip["type_scale"]}f'+'},')
    with (target/'expanded_graph.h').open('a') as f:f.write('\nstatic const CohSeqClip fem_clips[]={\n'+'\n'.join(fem)+'\n};\n')
    original_graph=module('continuation_original_graph',HERE.parent/'tools/original_oracle.py');original_graph.write(root,target/'original-graph.c')
    exe=target/'expanded-graph-test';run([cc,'-std=c11','-O2','-ffp-contract=off','-I',HERE.parent,'-I',target,HERE/'tests/family_graph_test.c',HERE.parent/'coh_sequencer.c',NATIVE/'animation/coh_animation.c',target/'original-graph.c','-lm','-o',exe]);graph_result=json.loads(run([exe]))
    raw_pins=HERE/'extra-asset-pins.json'
    actual={x['asset']:{'sha256':x['source_sha256'],'bytes':x['raw_bytes']} for x in families}
    if raw_pins.exists():
        expected=json.loads(raw_pins.read_text())
        if expected!=actual:raise ValueError('additional original raw asset pins changed; inspect before admission')
    return {'status':'original raw-key + original per-bone transition comparisons passed','raw_assets':families,'body_playback':body_results,'raw_decoder_source_commit':pins['source_commit'],'expanded_source_graph':graph_result,'scalar_comparisons':total,'maximum_error':maximum,'limitations':['Full raw clip ranges tested; full original move graph, CANTMOVE/NOCOLLISION side effects and authored PlayFx routing remain pending.','No new Android execution or device pose acceptance.','Wave asset is raw-pose evidence; its authored emote state binding is not qualified.']}
