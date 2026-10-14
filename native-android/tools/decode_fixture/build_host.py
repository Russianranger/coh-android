#!/usr/bin/env python3
"""Build and exercise the same statically pinned source used in the APK."""
import argparse,hashlib,json,math,os,shlex,struct,subprocess,sys
from pathlib import Path
from acquire import ROOT,acquire
VORBIS='mdct smallft block envelope window lsp lpc analysis synthesis psy info floor1 floor0 res0 mapping0 registry codebook sharedbook lookup bitrate vorbisfile'.split()
HERE=Path(__file__).resolve().parent

def build(output,compiler,sanitize):
    deps=ROOT/'decode/.deps';receipt=acquire(deps);output.mkdir(parents=True,exist_ok=True)
    command=shlex.split(compiler)
    flags=['-DHAVE_ALLOCA_H=1','-std=c11','-O1' if sanitize else '-O2','-g','-ffp-contract=off']
    if sanitize: flags+=['-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie']
    includes=['-I',str(deps/'ogg/include'),'-I',str(deps/'vorbis/include'),'-I',str(deps/'vorbis/lib'),'-I',str(ROOT/'decode')]
    sources=[deps/'ogg/src/bitwise.c',deps/'ogg/src/framing.c']+[deps/'safe/sharedbook.c' if n=='sharedbook' else deps/'vorbis/lib'/f'{n}.c' for n in VORBIS]
    objects=[]
    for n,source in enumerate(sources+[ROOT/'decode/coh_decode.c']):
        object_path=output/f'{n}.o'
        strict=['-Wall','-Wextra','-Werror'] if source.name=='coh_decode.c' else []
        subprocess.run(command+flags+strict+includes+['-c',str(source),'-o',str(object_path)],check=True)
        objects.append(str(object_path))
    link_extra=['-no-pie'] if sanitize else []
    exe=output/'decode-host-test'
    subprocess.run(command+flags+['-Wall','-Wextra','-Werror']+includes+[str(HERE/'host_test.c')]+objects+['-lm']+link_extra+['-o',str(exe)],check=True)
    oracle=output/'source-decoder'
    # Header includes original callback bodies without wrapper modifications.
    subprocess.run(command+flags+['-Wall','-Wextra','-Werror','-Wno-unused-parameter']+includes+[str(ROOT/'tools/audio_fixture/source_decoder.c')]+objects[:-1]+['-lm']+link_extra+['-o',str(oracle)],check=True)
    callbacks=output/'callback-bound-test'
    subprocess.run(command+flags+['-Wall','-Wextra','-Werror']+includes+[str(HERE/'callback_test.c')]+link_extra+['-o',str(callbacks)],check=True)
    return exe,oracle,callbacks,receipt

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus',required=True,type=Path);p.add_argument('--reference',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--compiler',default=os.environ.get('CC','cc'))
    p.add_argument('--sanitize',action='store_true');a=p.parse_args()
    exe,oracle,callbacks,acquisition=build(a.output,a.compiler,a.sanitize)
    pins=json.loads((ROOT/'tools/audio_fixture/pins.json').read_text());ogg=a.corpus/'headset.ogg';raw=ogg.read_bytes();ref=a.reference.read_bytes()
    if len(raw)!=pins['record']['size'] or hashlib.sha256(raw).hexdigest()!=pins['record']['sha256']:raise ValueError('Authentic compressed fixture identity differs')
    if len(ref)!=72736 or hashlib.sha256(ref[64:]).hexdigest()!=pins['decoded']['pcm_sha256']:raise ValueError('Trusted reference PCM identity differs')
    environment=os.environ.copy()
    if a.sanitize:
        environment['ASAN_OPTIONS']='detect_leaks=0:abort_on_error=1';environment['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    callback_proof=json.loads(subprocess.check_output([str(callbacks)],env=environment,text=True,timeout=60))
    decoded=json.loads(subprocess.check_output([str(oracle),str(ogg),str(a.output/'original-source.pcm')],env=environment,text=True,timeout=60))
    source_pcm=(a.output/'original-source.pcm').read_bytes()
    expected=struct.unpack('<'+'h'*(len(ref[64:])//2),ref[64:]);actual=struct.unpack('<'+'h'*(len(source_pcm)//2),source_pcm)
    delta=[a-b for a,b in zip(actual,expected)]
    if len(actual)!=len(expected) or max(map(abs,delta))>1:raise ValueError('Pinned-codec source oracle exceeds fixed accepted reference <=1 LSB bound')
    oracle_comparison={'compared_samples':len(delta),'different_samples':sum(d!=0 for d in delta),
                       'maximum_sample_error':max(map(abs,delta)),'sample_rms_error':math.sqrt(sum(d*d for d in delta)/len(delta)),
                       'exact':source_pcm==ref[64:],'fixed_maximum_allowed_sample_error':1}
    receipt=json.loads(subprocess.check_output([str(exe),str(ogg),str(a.reference),str(a.output/'original-source.pcm')],env=environment,text=True,timeout=60))
    receipt.update(unchanged_callback_bounds=callback_proof,schema='coh-native-compressed-audio-host-proof-v1',sanitizers=['address','undefined'] if a.sanitize else [],dependency_acquisition=acquisition,
                   leak_sanitizer_available=False,leak_sanitizer_limitation='LSan cannot run under execution ptrace; ASan and UBSan remain enabled with immediate abort',unchanged_source_oracle=decoded,unchanged_source_pcm_sha256=hashlib.sha256(source_pcm).hexdigest(),
                   native_source_sha256=hashlib.sha256((ROOT/'decode/coh_decode.c').read_bytes()).hexdigest(),native_header_sha256=hashlib.sha256((ROOT/'decode/coh_decode.h').read_bytes()).hexdigest(),floating_contract='-ffp-contract=off',native_pcm_exact_to_unchanged_callback_oracle=True,trusted_reference_oracle_comparison=oracle_comparison,input_sha256=hashlib.sha256(raw).hexdigest())
    (a.output/'host-proof.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
