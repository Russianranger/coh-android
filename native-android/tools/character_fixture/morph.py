#!/usr/bin/env python3
"""Serialize raw authored morphology inputs and original scale-model triples."""
from pathlib import Path
import json, re, struct
import geo

ROOT=Path(__file__).resolve().parents[2]
def bone_names(source):
    original=source.read_bytes()
    pins=json.loads((ROOT/'character-probe/contract/source-hashes.json').read_text())
    expected=next(row['sha256'] for row in pins['files'] if row['path']=='upstream/ouroboros/Common/seq/bones.h')
    geo.require(geo.sha(original)==expected,'original bone ID source SHA256 differs')
    raw=original.decode('ascii'); block=raw.split('typedef enum BoneId',1)[1].split('BONEID_COUNT',1)[0]
    names=re.findall(r'\bBONEID_([A-Z0-9_]+)\s*,',block)
    geo.require(len(names)==99,'source bone ID enum differs')
    return names

def make(corpus,bones_source,config=None):
    config=config or json.loads((ROOT/'character/wretch-morph.json').read_text())
    names=bone_names(bones_source); ids={name.casefold():i for i,name in enumerate(names)}
    endpoints=[]; metadata=[]
    for file in ('scalel.geo','scales.geo'):
        raw=(corpus/file).read_bytes(); version,_,models=geo.records(raw)
        geo.require(version==0 and len(models)==39,'source morphology geometry differs')
        resolved={}
        for model in models:
            id=ids.get(model['name'].casefold()); geo.require(id is not None and id not in resolved,'scale model bone mapping differs')
            resolved[id]=model['scale']
        endpoints.append(resolved)
        metadata.append({'source_file':file,'source_sha256':geo.sha(raw),'source_version':version,
            'model_count':len(models),'scale_models':[{ 'bone_id':id,'bone_name':names[id],
                'raw_float32_scale':values} for id,values in sorted(resolved.items())]})
    header=bytearray(256)
    struct.pack_into('<8s8I',header,0,b'COHMOR01',1,256,99,256,28,3028,config['body_type'],0)
    floats=config['geom_scale']+[config[name] for name in ('bone_scale','shoulder_scale','chest_scale','waist_scale','hip_scale','leg_scale','arm_scale')]
    floats+=config['head_scales']+[config['leg_scale_ratio']]
    for name in ('shoulder_skinny','shoulder_fat','hip','neck','head_min','head_max'):floats+=config[name]
    floats+=[x for row in config['face_scales'] for x in row]
    geo.require(len(floats)==53,'morphology authored field count differs')
    struct.pack_into('<53f',header,40,*floats)
    body=b''.join(struct.pack('<I6f',id,*endpoints[0].get(id,[1,1,1]),*endpoints[1].get(id,[1,1,1])) for id in range(99))
    raw=bytes(header)+body; geo.require(len(raw)==3028,'morphology container size differs')
    return raw,{'container':'COHMOR01','raw_authored_config':config,'bone_order':names,
        'scale_geometry':metadata,'missing_scale_model_rule':'original per-bone unit default',
        'native_runtime_morphology_required':True,'contains_baked_palette':False}
