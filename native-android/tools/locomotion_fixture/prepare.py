#!/usr/bin/env python3
"""Preserve original idle/run/postrun keys in a canonical bounded runtime bundle."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,struct
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def require(value,message):
    if not value:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def make(corpus,output):
    pins=json.loads((HERE/'pins.json').read_text())
    spec=importlib.util.spec_from_file_location('accepted_animation_prepare',ROOT/'tools/animation_fixture/prepare.py')
    animation=importlib.util.module_from_spec(spec);spec.loader.exec_module(animation)
    clips={};inspections={}
    for item in pins['records']:
        raw=(corpus/item['file_name']).read_bytes()
        require(len(raw)==item['size'] and sha(raw)==item['sha256'],'source clip hash/size differs: '+item['id'])
        inspections[item['id']],_=animation.inspect_animation(raw);clips[item['id']]=raw
    base=clips['ready'];raws=[]
    for key,first,last in [('ready',1,60),('run',1,25),('post',1,23)]:
        require(inspections[key]['name'].casefold()==pins['clip_names'][key],'source clip name differs')
        require(inspections[key]['base_anim_name'].casefold()=='huge/skel_ready','source base binding differs')
        require(inspections[key]['length_frames']>=last,'source authored range exceeds clip')
        rig=bytearray(animation.make_rig(base,clips[key],[9,5,7],72))
        struct.pack_into('<3f',rig,48,float(first),float(last),30.0);raws.append(bytes(rig))
    header=bytearray(64);total=64+sum(map(len,raws))
    struct.pack_into('<8s4I',header,0,b'COHLOCO1',1,64,3,total)
    offset=64
    for i,raw in enumerate(raws):struct.pack_into('<2I',header,24+i*8,offset,len(raw));offset+=len(raw)
    data=bytes(header)+b''.join(raws);require(len(data)==total,'canonical bundle differs')
    output.mkdir(parents=True,exist_ok=True);(output/'locomotion.bin').write_bytes(data)
    meta={'schema':'coh-native-locomotion-fixture-v1','status':'prepared',
          'source_release':pins['release_tag'],'data_commit':pins['data_commit'],
          'native_container':'COHLOCO1','original_encoded_keys_preserved':True,
          'clips':inspections,'assets':{'locomotion.bin':{'bytes':len(data),'sha256':sha(data)}},
          'moves':pins['moves'],'scope':pins['scope'],'source_pins':'source-pins.json'}
    (output/'locomotion-fixture.json').write_text(json.dumps(meta,indent=2)+'\n')
    return meta
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--corpus',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();meta=make(a.corpus,a.output);print(json.dumps({'status':'prepared','assets':meta['assets']}))
if __name__=='__main__':main()
