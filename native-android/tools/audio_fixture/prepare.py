#!/usr/bin/env python3
"""Prepare authentic signed-16 PCM with original source callback/ov_read contract."""
from pathlib import Path
import argparse,hashlib,json,os,shlex,struct,subprocess,tempfile
from source_oracle import HERE,sources,qualify,require
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--corpus',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--source-directory',type=Path);p.add_argument('--compiler',default=os.environ.get('CC','cc'));a=p.parse_args()
    pins,texts,callbacks,kernels=sources(a.source_directory);record=pins['record'];raw=(a.corpus/record['file_name']).read_bytes()
    require(len(raw)==record['size'] and hashlib.sha256(raw).hexdigest()==record['sha256'],'Source Ogg identity differs')
    acquisition=json.loads((a.corpus/'corpus.json').read_text());require(acquisition['acquisition_passed'] is True,'Source acquisition not qualified')
    oracle=qualify(a.compiler,a.source_directory)
    with tempfile.TemporaryDirectory(prefix='coh-source-audio-decode-') as d:
        t=Path(d);(t/'source_callbacks.inc').write_text(callbacks+'\n');exe=t/'decode';pcm=t/'audio.pcm'
        subprocess.run([*shlex.split(a.compiler),'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-I',str(t),str(HERE/'source_decoder.c'),'-lvorbisfile','-lvorbis','-logg','-o',str(exe)],check=True)
        decoded=json.loads(subprocess.check_output([str(exe),str(a.corpus/record['file_name']),str(pcm)],text=True))
        payload=pcm.read_bytes()
    expected=pins['decoded'];require(decoded['passed'] and all(decoded[k]==expected[k] for k in ['sample_rate','channels','frames','pcm_bytes']),'Decoded format differs')
    require(len(payload)==expected['pcm_bytes'] and hashlib.sha256(payload).hexdigest()==expected['pcm_sha256'],'Exact decoded PCM hash differs')
    header=struct.pack('<8s7I',b'COHAUD11',1,64,expected['sample_rate'],expected['channels'],expected['frames'],expected['pcm_bytes'],16)+bytes(28)
    fixture=header+payload;a.output.mkdir(parents=True,exist_ok=True);(a.output/'audio.bin').write_bytes(fixture)
    samples=struct.unpack('<'+'h'*(len(payload)//2),payload)
    metadata={'schema':'coh-native-audio-fixture-v1','audio':{'file':'audio.bin','bytes':len(fixture),'sha256':hashlib.sha256(fixture).hexdigest()},'fixture':expected,
              'source':record,'acquisition':acquisition,'decode':decoded,'source_gain_oracle':oracle,
              'pcm_nonzero_samples':sum(v!=0 for v in samples),'pcm_peak':max(abs(v) for v in samples),
              'scope':'Authentic client Ogg offline decoded with four unchanged memory callbacks and source signed16 little-endian ov_read parameters; native AAudio sink only',
              'not_qualified':['Native compressed Ogg decoder','Full client sound scheduler/mixer, voiceover/music/3D attenuation/doppler','Physical speaker audibility from engine counters','Latency or underrun-free gameplay audio','Original DirectSound sample rounding']}
    (a.output/'audio-fixture.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps({'passed':True,'audio':metadata['audio'],'source_comparisons':oracle['source_comparisons']}))
if __name__=='__main__':main()
