#!/usr/bin/env python3
"""Package compressed source plus comparison-only PCM; never substitute playback."""
import argparse,hashlib,json,shutil,sys
from pathlib import Path
from acquire import ROOT,acquire

def audit_source():
    sys.path.insert(0,str(ROOT/'tools/audio_fixture'))
    from source_oracle import extract
    audit=json.loads((ROOT/'decode/source-audit.json').read_text())
    repo=ROOT.parent;source=(repo/audit['source']).read_text()
    if hashlib.sha256(source.encode()).hexdigest()!=audit['source_sha256']:
        raise ValueError('Pinned original callback source differs')
    copied=(ROOT/'decode/source_callbacks.inc').read_text()
    for name,digest in audit['functions'].items():
        original=extract(source,name)
        if hashlib.sha256(original.encode()).hexdigest()!=digest or original not in copied:
            raise ValueError('Original callback body differs: '+name)
    codecs=json.loads((ROOT/'decode/dependency-pins.json').read_text())
    dependency_source=(repo/'upstream/ouroboros/cmake/dependencies/Vorbis.cmake').read_text()
    if not all(pin['revision'] in dependency_source for pin in codecs.values()):
        raise ValueError('Codec revisions differ from original client dependency pins')
    return {'unchanged_callback_functions':list(audit['functions']),'source_sha256':audit['source_sha256'],
            'codec_revisions':{name:pin['revision'] for name,pin in codecs.items()}}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',required=True,type=Path);p.add_argument('--reference',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    pins=json.loads((ROOT/'tools/audio_fixture/pins.json').read_text());raw=(a.corpus/'headset.ogg').read_bytes();reference=a.reference.read_bytes()
    if len(raw)!=pins['record']['size'] or hashlib.sha256(raw).hexdigest()!=pins['record']['sha256']:raise ValueError('Compressed asset identity differs')
    if len(reference)!=72736 or hashlib.sha256(reference[64:]).hexdigest()!=pins['decoded']['pcm_sha256']:raise ValueError('Trusted PCM reference differs')
    if reference[:8]!=b'COHAUD11':raise ValueError('Reference blob header differs')
    audit=audit_source();acquired=acquire(ROOT/'decode/.deps');a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'headset.ogg').write_bytes(raw);(a.output/'audio-reference.bin').write_bytes(reference)
    metadata={'schema':'coh-native-compressed-audio-fixture-v1','passed':True,'source':pins['record'],'expected':pins['decoded'],
              'compressed':{'file':'headset.ogg','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},
              'comparison_reference':{'file':'audio-reference.bin','bytes':len(reference),'sha256':hashlib.sha256(reference).hexdigest(),'playback_allowed':False},
              'source_audit':audit,'dependency_acquisition':acquired,'maximum_allowed_sample_error':1,
              'scope':'Native compressed Ogg decode of authentic client asset into owned COHAUD11 for accepted AAudio sink',
              'not_qualified':['Full client sound scheduler/mixer','Multiple/streaming asset playback','Music looping/voice/3D attenuation/doppler','Gameplay sound and full native client']}
    (a.output/'decode-fixture.json').write_text(json.dumps(metadata,indent=2)+'\n')
    shutil.copytree(ROOT/'decode/licenses',a.output/'licenses',dirs_exist_ok=True)
    print(json.dumps(metadata))
if __name__=='__main__':main()
