"""Extract and execute two unchanged client source volume kernels."""
from pathlib import Path
import ctypes as C,hashlib,json,math,re,shlex,subprocess,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];REPO=ROOT.parent
def require(v,s):
    if not v:raise ValueError(s)
def extract(text,name):
    matches=list(re.finditer(r'(?m)^static [^\n]+\b'+re.escape(name)+r'\([^\n]*\)\s*\{',text))
    require(len(matches)==1,'Source function identity differs: '+name)
    start=matches[0].start();i=text.find('{',start)+1;depth=1
    while depth:
        require(i<len(text),'Unbalanced source '+name);depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i]
def sources(source_directory=None):
    pins=json.loads((HERE/'pins.json').read_text());texts={}
    for rel,pin in pins['sources'].items():
        p=(source_directory/Path(rel).name) if source_directory else REPO/rel
        raw=p.read_bytes();require(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],'Audio source pin differs: '+rel)
        texts[Path(rel).name]=raw.decode('latin1').replace('\r\n','\n')
    decoder=texts['ogg_decode.c'];require('ov_read(&ogg->vf,decode->decode_buffer + decode->decode_count,decode->decode_len - decode->decode_count,0,2,1,&ogg->current_section)' in decoder,'Original ov_read parameters differ')
    require(re.search(r'^#define DEFAULT_VOLUME_FX\s+0\.6f',texts['sound.h'],re.M),'Original FX volume differs')
    sys=texts['sound_sys.c'];require('#define MIN_VOLUME_DB (-10000)' in sys and '#define MAX_VOLUME_DB (0)' in sys,'Original dB clamp differs')
    callbacks='\n'.join(extract(decoder,n) for n in ['readbytes','seekbytes','closebytes','tellbytes'])
    kernels='\n'.join(extract(sys,n) for n in ['volumeDbToRatio','volumeRatioToDb'])
    return pins,texts,callbacks,kernels
def qualify(compiler='cc',source_directory=None):
    pins,texts,callbacks,kernels=sources(source_directory)
    pre='#include <math.h>\ntypedef float F32;\n#define MIN_VOLUME_DB (-10000)\n#define MAX_VOLUME_DB (0)\n#define MINMAX(v,lo,hi) ((v)<(lo)?(lo):((v)>(hi)?(hi):(v)))\n'
    suffix='\nint source_db(float v){return volumeRatioToDb(v);}\nfloat source_gain(int db){return volumeDbToRatio(db);}\n'
    with tempfile.TemporaryDirectory(prefix='coh-audio-oracle-') as d:
        t=Path(d);c=t/'source.c';c.write_text(pre+kernels+suffix)
        subprocess.run([*shlex.split(compiler),'-std=c11','-O0','-ffp-contract=off','-shared','-fPIC',str(c),'-lm','-o',str(t/'source.so')],check=True)
        subprocess.run([*shlex.split(compiler),'-std=c11','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'audio/coh_audio.c'),'-lm','-o',str(t/'native.so')],check=True)
        orig=C.CDLL(str(t/'source.so'));native=C.CDLL(str(t/'native.so'))
        orig.source_db.argtypes=[C.c_float];orig.source_db.restype=C.c_int
        orig.source_gain.argtypes=[C.c_int];orig.source_gain.restype=C.c_float
        native.coh_audio_ratio_to_db.argtypes=[C.c_float,C.POINTER(C.c_int)];native.coh_audio_ratio_to_db.restype=C.c_int
        native.coh_audio_db_to_ratio.argtypes=[C.c_int];native.coh_audio_db_to_ratio.restype=C.c_float
        cases=[];maximum=0.;count=0
        for v in [-1,0,1e-6,1e-5,1e-4,.001,.01,.1,.25,.3,.5,.6,.8,1,2]:
            v=C.c_float(v).value;db=orig.source_db(v);gain=orig.source_gain(db);ndb=C.c_int()
            require(native.coh_audio_ratio_to_db(v,C.byref(ndb))==0 and ndb.value==db,'Native/source volume dB differs')
            error=abs(native.coh_audio_db_to_ratio(db)-gain);maximum=max(maximum,error);require(error==0,'Host native/source volume gain differs')
            cases.append({'input':v,'db':db,'effective_gain':gain});count+=2
        for db in [-2147483648,-12000,-10000,-9999,-443,-1,0,1,10000,2147483647]:
            require(native.coh_audio_db_to_ratio(db)==orig.source_gain(db),'Native/source dB clamp differs');count+=1
    return {'schema':'coh-native-audio-source-gain-v1','passed':True,'source_revision':pins['source_revision'],'source_functions':2,'source_comparisons':count,'maximum_source_error':maximum,'cases':cases,'sources':pins['sources'],'function_sha256':{n:hashlib.sha256(extract(texts['sound_sys.c'],n).encode()).hexdigest() for n in ['volumeDbToRatio','volumeRatioToDb']},'callback_sha256':{n:hashlib.sha256(extract(texts['ogg_decode.c'],n).encode()).hexdigest() for n in ['readbytes','seekbytes','closebytes','tellbytes']},'adapters':['Standalone F32 and MINMAX types/macros with pinned source dB constants','Full Win32 DirectSound and undocumented sample rounding do not execute'],'android_libm_float_gain_tolerance':1e-6}
