#!/usr/bin/env python3
"""Qualify fixture bounds, unchanged gain kernels and PCM adapter on the host."""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,os,shlex,struct,subprocess,tempfile
from source_oracle import ROOT,qualify,require
class Fixture(C.Structure):
    _fields_=[('sample_rate',C.c_uint32),('channels',C.c_uint32),('frames',C.c_uint32),('pcm_bytes',C.c_uint32),('pcm',C.POINTER(C.c_uint8))]
class Proof(C.Structure):
    _fields_=[('checks',C.c_uint),('failed',C.c_uint),('source_cases',C.c_uint),('maximum_source_error',C.c_double)]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--compiler',default=os.environ.get('CC','cc'));a=p.parse_args();raw=a.fixture.read_bytes()
    oracle=qualify(a.compiler);checks=0;malformed=0;scaled_components=0
    with tempfile.TemporaryDirectory(prefix='coh-audio-proof-') as d:
        t=Path(d);lib=t/'audio.so';subprocess.run([*shlex.split(a.compiler),'-std=c11','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'audio/coh_audio.c'),'-lm','-o',str(lib)],check=True)
        n=C.CDLL(str(lib));n.coh_audio_parse.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(Fixture)];n.coh_audio_parse.restype=C.c_int
        n.coh_audio_scale.argtypes=[C.POINTER(Fixture),C.c_uint32,C.c_uint32,C.c_int,C.POINTER(C.c_int16)];n.coh_audio_scale.restype=C.c_int
        n.coh_audio_selftest.argtypes=[C.POINTER(Proof)];n.coh_audio_selftest.restype=C.c_int
        mem=(C.c_uint8*len(raw)).from_buffer_copy(raw);f=Fixture();require(n.coh_audio_parse(mem,len(raw),C.byref(f))==0,'Real PCM fixture rejected');checks+=1
        proof=Proof();require(n.coh_audio_selftest(C.byref(proof))==0 and proof.failed==0 and proof.source_cases==15,'Native source golden selfcheck failed');checks+=proof.checks
        for cut in list(range(64))+[64,65,4096,len(raw)-1]:
            require(n.coh_audio_parse(mem,cut,C.byref(Fixture()))==-1,'Truncated audio accepted');malformed+=1
        for offset,value in [(8,2),(12,60),(16,1),(20,3),(24,0),(28,0),(32,8)]:
            b=bytearray(raw);struct.pack_into('<I',b,offset,value);x=(C.c_uint8*len(b)).from_buffer_copy(b);require(n.coh_audio_parse(x,len(b),C.byref(Fixture()))==-1,'Malformed audio accepted');malformed+=1
        for offset in [0,36,63]:
            b=bytearray(raw);b[offset]^=1;x=(C.c_uint8*len(b)).from_buffer_copy(b);require(n.coh_audio_parse(x,len(b),C.byref(Fixture()))==-1,'Malformed audio accepted');malformed+=1
        require(n.coh_audio_parse(mem,len(raw)+1,C.byref(Fixture()))==-1,'Oversized span accepted');malformed+=1
        samples=struct.unpack('<'+'h'*(f.frames*f.channels),raw[64:]);out=(C.c_int16*len(samples))()
        for db in [0,-443,-1045,-10000]:
            require(n.coh_audio_scale(C.byref(f),0,f.frames,db,out)==0,'PCM scale rejected');checks+=1
            gain=next(case['effective_gain'] for case in oracle['cases'] if case['db']==db)
            # Python binary64 multiply is not the source float PCM adapter:
            # round each product to binary32 before nearest/even integer round.
            for original,actual in zip(samples,out):
                expected=round(C.c_float(C.c_float(original).value*gain).value)
                require(actual==expected,'PCM adapter rounding differs');scaled_components+=1
        for offset,count in [(f.frames,1),(f.frames-1,2),(0,0),(0,0xffffffff)]:
            require(n.coh_audio_scale(C.byref(f),offset,count,-443,out)==-1,'Invalid PCM span accepted');malformed+=1
    # Address/undefined sanitizer guard over every short header and exact tail.
    code='''#include "coh_audio.h"\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\nint main(int argc,char**argv){if(argc!=2)return 2;FILE*f=fopen(argv[1],"rb");if(!f)return 3;fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);unsigned char*b=malloc((size_t)n);if(!b)return 4;if(fread(b,1,(size_t)n,f)!=(size_t)n)return 5;fclose(f);CohAudioFixture o;for(size_t k=0;k<64;k++){unsigned char*cut=malloc(k?k:1);if(!cut)return 11;memcpy(cut,b,k);int result=coh_audio_parse(cut,k,&o);free(cut);if(result!=-1)return 6;}unsigned char*tail=malloc((size_t)n-1);if(!tail)return 12;memcpy(tail,b,(size_t)n-1);int result=coh_audio_parse(tail,(size_t)n-1,&o);free(tail);if(result!=-1)return 7;if(coh_audio_parse(b,(size_t)n,&o))return 8;short*out=malloc(o.pcm_bytes);if(!out)return 9;if(coh_audio_scale(&o,0,o.frames,-443,out))return 10;free(out);free(b);return 0;}\n'''
    with tempfile.TemporaryDirectory(prefix='coh-audio-asan-') as d:
        t=Path(d);c=t/'guard.c';c.write_text(code);exe=t/'guard'
        subprocess.run([*shlex.split(a.compiler),'-std=c11','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(ROOT/'audio'),str(c),str(ROOT/'audio/coh_audio.c'),'-lm','-o',str(exe)],check=True)
        env=dict(os.environ);env['ASAN_OPTIONS']='detect_leaks=0:abort_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1';subprocess.run([str(exe),str(a.fixture)],check=True,env=env)
    result={'schema':'coh-native-audio-host-proof-v1','passed':True,'audio_sha256':hashlib.sha256(raw).hexdigest(),'checks':checks,'malformed_spans_rejected':malformed,'pcm_scale_components':scaled_components,'source_gain_oracle':oracle,'asan_ubsan':{'passed':True,'guard_checks':66,'leak_sanitizer_enabled':False,'scope':'Portable fixture parser and PCM scaling only'},'native_android_backend_executed':False}
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['passed','checks','malformed_spans_rejected','pcm_scale_components']}))
if __name__=='__main__':main()
