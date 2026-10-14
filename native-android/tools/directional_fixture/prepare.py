#!/usr/bin/env python3
"""Preserve authentic Huge locomotion and male parent fallback raw keys."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,struct
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
MOVES=[('Ready','ready',1,60),('RunCycle','run',1,25),('RunPost','post',1,23),
       ('RunPre','run',18,25),('Idle_Walk_Post','walk',47,48),('Idle_Ready','idle',1,60),
       ('Run_Back_Pre','back',1,24),('Run_Back_Cycle','back',1,24),
       ('Run_Left_Pre','left',15,25),('Run_Left_Cycle','left',1,25),
       ('Run_Right_Pre','right',1,25),('Run_Right_Cycle','right',1,25)]
def require(v,s):
    if not v:raise ValueError(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def make(corpus,output):
    pins=json.loads((HERE/'pins.json').read_text())
    spec=importlib.util.spec_from_file_location('accepted_directional_animation',ROOT/'tools/animation_fixture/prepare.py')
    animation=importlib.util.module_from_spec(spec);spec.loader.exec_module(animation)
    clips={};inspections={}
    for pin in pins['records']:
        raw=(corpus/pin['file_name']).read_bytes()
        require(len(raw)==pin['size'] and sha(raw)==pin['sha256'],'source clip hash/size differs: '+pin['id'])
        item,_=animation.inspect_animation(raw)
        require(item['name'].casefold()==pins['clip_names'][pin['id']],'source clip name differs')
        inspections[pin['id']]=item;clips[pin['id']]=raw
    parts=[];moves=[]
    for name,key,first,last in MOVES:
        base_key='idle' if key in ('walk','idle') else 'ready'
        require(inspections[key]['base_anim_name'].casefold()==inspections[base_key]['name'].casefold(),'source base binding differs')
        require(inspections[key]['length_frames']>=last,'authored range exceeds source clip')
        rig=bytearray(animation.make_rig(clips[base_key],clips[key],[9,5,7],72))
        struct.pack_into('<3f',rig,48,float(first),float(last),30.0);parts.append(bytes(rig))
        moves.append({'name':name,'clip':key,'first':first,'last':last,'interpolate':8 if name=='RunPost' else 5,
                      'move_rate':.525 if key=='back' else .7 if key in ('run','left','right') else None,
                      'actor_hierarchy':'huge/skel_ready','animation_base':inspections[base_key]['name'],
                      'male_parent_fallback':key in ('walk','idle')})
    header=bytearray(128);total=128+sum(map(len,parts))
    struct.pack_into('<8s4I',header,0,b'COHLOCO2',2,128,len(parts),total);offset=128
    for i,raw in enumerate(parts):struct.pack_into('<2I',header,24+i*8,offset,len(raw));offset+=len(raw)
    data=bytes(header)+b''.join(parts);require(len(data)<=512*1024,'bundle exceeds runtime budget')
    output.mkdir(parents=True,exist_ok=True);(output/'locomotion.bin').write_bytes(data)
    meta={'schema':'coh-native-directional-fixture-v2','status':'prepared','source_release':pins['release_tag'],
          'source_commit':pins['source_commit'],'data_commit':pins['data_commit'],'original_encoded_keys_preserved':True,
          'native_container':'COHLOCO2','clips':inspections,'moves':moves,'scope':pins['scope'],
          'assets':{'locomotion.bin':{'bytes':len(data),'sha256':sha(data)}},
          'idle_requirement_policy':'Wretch HUGE state does not set IDLE; forced Idle_Ready loses IDLE and returns Ready next tick',
          'direction_input_policy':'original desired local velocity flags; wall collision retains flags and minimum MoveScale .25'}
    (output/'directional-fixture.json').write_text(json.dumps(meta,indent=2)+'\n');return meta
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--corpus',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();meta=make(a.corpus,a.output);print(json.dumps({'status':'prepared','assets':meta['assets']}))
