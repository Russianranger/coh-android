#!/usr/bin/env python3
"""New GPU lease owner controls and actual private EGL pbuffer qualification.

No server, APK, application context adoption, production prepare or source/
material/actor authority is qualified. Every executing project byte is committed
and source-pinned before builds; external Mesa/vendor drivers remain unsanitized.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,shlex,subprocess,sys,types
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
TEXTURE_SHA='c36001854f75ff7e8ef5304138537f1de4b71dcc3529a9a40f6093fde959df9a'
CHAIN_SHA='93ca8bfe6e2985b9e20c7c097038fb365199565c9eaed57f524416e456c4667c'
PACKET_SHA='a622fe7d6e50064073704108cc5b58975fe4d4b7ba68eae4919dca72de6c8523'
BASE=('coh_wr_gpu_lease.c','coh_wr_gpu_texture.c','coh_wr_texture.c','coh_wr_sampler.c',
      '../assets/coh_asset_loader.c','../../src/coh_assets.c','../../src/coh_dds.c')
COMMON=('-std=c11','-Wall','-Wextra','-Werror','-pedantic','-fno-fast-math','-ffp-contract=off')
def require(value,code):
    if not value:raise ValueError('COH_GPU_LEASE_'+code)
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],text=True,timeout=30).strip()
def call(command,output,label,env=None,success=True):
    child=subprocess.run(list(map(str,command)),cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=180,env=env)
    require(len(child.stdout)+len(child.stderr)<=4*1024**2,'CHILD_OUTPUT')
    (output/(label+'.stdout')).write_bytes(child.stdout);(output/(label+'.stderr')).write_bytes(child.stderr)
    if success:require(child.returncode==0,'CHILD_FAILED_'+label)
    return child
def dependencies(headers):
    sources=[HERE/name for name in (*BASE,'tests/test_gpu_lease.c','tests/test_gpu_lease_egl.c')]
    child=subprocess.run(['cc',*COMMON,'-I'+str(ROOT/'native-android/include'),'-I'+str(headers),'-MM',*map(str,sources)],cwd=ROOT,capture_output=True,text=True,timeout=60)
    require(child.returncode==0 and len(child.stdout)<1024**2,'DEPENDENCIES')
    files={Path(__file__),HERE/'GPU_LEASE_OWNER.md',HERE/'egl-host-header-pins.json',HERE/'sampler-authentic-pins.json',HERE/'check_sampler.py'}
    for line in child.stdout.replace('\\\n',' ').splitlines():
        require(':' in line,'DEPENDENCY_SYNTAX')
        for name in shlex.split(line.split(':',1)[1]):
            p=Path(name).resolve()
            if p.is_relative_to(ROOT):files.add(p)
            else:require(p.is_relative_to(headers),'EXTERNAL_HEADER')
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}
def committed(pins,revision):
    require(git('rev-parse','HEAD')==revision,'REVISION_CHANGED')
    for name,digest in pins.items():
        require(sha(ROOT/name)==digest,'SOURCE_CHANGED')
        body=subprocess.run(['git','show',revision+':'+name],cwd=ROOT,capture_output=True,timeout=30)
        require(body.returncode==0 and hashlib.sha256(body.stdout).hexdigest()==digest,'UNCOMMITTED_SOURCE')
def native(value,actual):
    require(type(value) is dict and value.get('passed') is True,'NATIVE_RESULT')
    for key in ('world_authority','actor_authority','source_generation_admitted'):require(value.get(key) is False,'AUTHORITY')
    require(value.get('actual_gles') is actual and type(value.get('checks')) is int and value['checks']==(602 if actual else 96),'NATIVE_SCOPE')
    if actual:
        expected={'cleanup_verified':True,'uploads':4,'readbacks':37,'registry_retains':4,'registry_releases':4,
            'verified_deletes':3,'destroyed_context_disposals':1,'contexts_created':2,'contexts_destroyed':2,
            'surfaces_created':3,'surfaces_destroyed':3,'generation_fixture_only':True,'sampler_fixture_only':True,'production_prepare_executed':False}
        require(set(value)==set(expected)|{'passed','checks','actual_gles','world_authority','actor_authority','source_generation_admitted','context_name_reuse_observed','gl_version','gl_renderer'},'NATIVE_FIELDS')
        for key,want in expected.items():require(type(value[key]) is type(want) and value[key]==want,'NATIVE_'+key)
        require(type(value['context_name_reuse_observed']) is bool,'NAME_REUSE_TYPE')
        for key in ('gl_version','gl_renderer'):
            require(type(value[key]) is str and 0<len(value[key])<192 and all(32<=ord(c)<127 for c in value[key]),'GL_IDENTITY')
        require(re.match(r'^OpenGL ES 3\.',value['gl_version']) is not None,'GLES3')
    else:require(set(value)=={'passed','checks','model_only','actual_gles','world_authority','actor_authority','source_generation_admitted'} and value['model_only'] is True,'MODEL_FIELDS')
    return value
def packet(path):
    require(path.stat().st_size==4*349524 and sha(path)==PACKET_SHA,'READBACK_PACKET')
    raw=path.read_bytes()
    require(all(hashlib.sha256(raw[i*349524:(i+1)*349524]).hexdigest()==CHAIN_SHA for i in range(4)),'READBACK_CHAINS')
    return {'bytes':len(raw),'sha256':PACKET_SHA,'chains':4,'each_chain_sha256':CHAIN_SHA}
def prepare(args):
    require(__debug__,'ASSERTIONS_REQUIRED')
    require(args.source_root.resolve()==ROOT and Path(__file__).resolve()==ROOT/'native-android/engine/world-render-adapter/check_gpu_lease.py','SOURCE_ROOT')
    output=args.output.absolute();require(not output.exists() and output.parent.is_dir(),'NEW_OUTPUT')
    require(args.actual_texture.is_file() and not args.actual_texture.is_symlink() and args.actual_texture.stat().st_size==43990 and sha(args.actual_texture)==TEXTURE_SHA,'AUTHENTIC_TEXTURE')
    headers=args.host_headers.resolve();header_pins=json.loads((HERE/'egl-host-header-pins.json').read_bytes())
    for name,pin in header_pins.items():
        path=headers/name;require(path.is_file() and not path.is_symlink() and path.stat().st_size==pin['bytes'] and sha(path)==pin['sha256'],'PRIMARY_HEADERS')
    libraries={str(p.resolve()):sha(p.resolve()) for p in (args.host_egl,args.host_gles)}
    revision=git('rev-parse','HEAD');pins=dependencies(headers);committed(pins,revision)
    output.mkdir(mode=0o700);(output/'box-1.texture').write_bytes(args.actual_texture.read_bytes())
    raw=(output/'box-1.texture').read_bytes();pin=bytes.fromhex(TEXTURE_SHA)
    fixture_header=('/* FINITE byte-equality fixture only; NOT general SHA256 or authentication. */\n'
        '#include <stdint.h>\n#include <stddef.h>\n#include <string.h>\n'
        'static const uint8_t coh_egl_fixture[]={'+','.join(map(str,raw))+'};\n'
        'static uint8_t*coh_egl_fixture_digest(const uint8_t*p,size_t n,uint8_t*out){static const uint8_t pin[]={'+','.join(map(str,pin))+'};'
        'if(n!=sizeof(coh_egl_fixture)||memcmp(p,coh_egl_fixture,n))return NULL;memcpy(out,pin,32);return out;}\n')
    (output/'egl_fixture_digest.h').write_text(fixture_header)
    inc=['-I'+str(ROOT/'native-android/include'),'-I'+str(HERE),'-I'+str(headers)]
    base=[HERE/name for name in BASE];link=['-lcrypto','-lz','-lm','-lpthread'];gl_link=[args.host_egl.resolve(),args.host_gles.resolve(),*link]
    environment=dict(os.environ,EGL_PLATFORM='surfaceless',ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
    results={};frames=[]
    modes={'release':['-O2','-fstack-usage']}
    if args.sanitize:modes.update(asan=['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie'],ubsan=['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])
    modes['finite-fixture']=['-O2','-DCOH_GPU_LEASE_FIXTURE_DIGEST','-I'+str(output)]
    for mode,flags in modes.items():
        directory=output/mode;directory.mkdir()
        for kind,test,extra in (('model','tests/test_gpu_lease.c',['-Wl,--wrap=calloc',*link]),('egl','tests/test_gpu_lease_egl.c',gl_link)):
            exe=directory/kind
            call(['cc',*COMMON,*flags,*inc,*base,HERE/test,*extra,'-o',exe],output,'compile-'+mode+'-'+kind)
            command=[exe,output/'box-1.texture']
            if kind=='egl':command.append(directory/'readback.rgba')
            value=native(json.loads(call(command,output,'execute-'+mode+'-'+kind,environment).stdout),kind=='egl')
            item={'binary_sha256':sha(exe),'native':value}
            if kind=='egl':item['readback']=packet(directory/'readback.rgba')
            results[mode+'-'+kind]=item
        if mode=='release':
            for file in directory.glob('*.su'):
                for line in file.read_text().splitlines():
                    location,size,kind=line.split('\t')
                    if 'coh_wr_gpu_lease.c:' in location:
                        require(kind in ('static','dynamic,bounded'),'STACK_KIND');name=location.rsplit(':',1)[-1]
                        prior=next((row for row in frames if row['function']==name),None)
                        if prior is None:frames.append({'function':name,'bytes':int(size)})
                        else:prior['bytes']=max(prior['bytes'],int(size))
    require(frames and 4*sum(row['bytes'] for row in frames)<65536,'CONTROL_STACK')
    for kind in ('model','egl'):
        require(len({v['native']['checks'] for key,v in results.items() if key.endswith('-'+kind)})==1,'MODE_CHECK_COUNTS')
    # Only this existing independent all-mip oracle is imported, after its exact
    # executed source was committed/pinned. No old qualifier main is called.
    helper=HERE/'check_sampler.py';module=types.ModuleType('coh_gpu_lease_pillow');module.__file__=str(helper)
    exec(compile(helper.read_bytes(),str(helper),'exec'),module.__dict__)
    first=output/'first-chain.rgba';first.write_bytes((output/'release/readback.rgba').read_bytes()[:349524])
    pillow=module.texture_oracle(output/'box-1.texture',first)
    # Actual C object is linked from C++, rather than compiling public C as C++.
    cpp=output/'link.cpp';cpp.write_text('#include "coh_wr_gpu_lease.h"\nint main(){CohWrGpuLease*p=nullptr;return coh_wr_gpu_lease_collect(&p)==COH_INVALID?0:1;}\n')
    objects=[]
    for i,source in enumerate(base):
        obj=output/('c-'+str(i)+'.o');call(['cc',*COMMON,'-O2',*inc,'-c',source,'-o',obj],output,'cpp-object-'+str(i));objects.append(obj)
    call(['c++','-std=c++11','-Wall','-Wextra','-Werror',*inc,cpp,*objects,*link,'-o',output/'cpp-link'],output,'cpp-link')
    call([output/'cpp-link'],output,'cpp-execute')
    symbols=subprocess.check_output(['nm','-g','--defined-only',str(objects[0])],text=True,timeout=30)
    exported=sorted(line.split()[-1] for line in symbols.splitlines())
    require(exported==sorted('coh_wr_gpu_lease_'+name for name in ('adopt','resources','retire','drain','collect','report')),'PUBLIC_SYMBOLS')
    source=(HERE/'coh_wr_gpu_lease.c').read_text();mutations=[]
    changes=(('identity_digest','memcmp(report.source.sha256,in[i].source_sha256,32)','0'),
        ('retire_while_leased','if(!r->report.retired || r->report.leases)','if(!r->report.retired)'),
        ('registry_pin','CohStatus s=backend->retain_registry(backend->gpu.context);','CohStatus s=COH_OK;'),
        ('missing_transfer','for(size_t i=0;i<count;i++)*in[i].take=NULL;','/* missing ownership transfer */'),
        ('cleanup_error_ignored','if(s!=COH_OK && failure==COH_OK)failure=s;','if(0)failure=s;'))
    for name,before,after in changes:
        require(source.count(before)==1,'MUTATION_TARGET')
        path=output/(name+'.c');path.write_text(source.replace(before,after));exe=output/name
        call(['cc',*COMMON,'-O2',*inc,path,*base[1:],HERE/'tests/test_gpu_lease.c','-Wl,--wrap=calloc',*link,'-o',exe],output,'compile-mutation-'+name)
        result=call([exe,output/'box-1.texture'],output,'mutation-'+name,environment,success=False)
        require(result.returncode!=0,'MUTATION_SURVIVED');mutations.append(name)
    committed(pins,revision)
    for name,pin in header_pins.items():
        path=headers/name;require(path.stat().st_size==pin['bytes'] and sha(path)==pin['sha256'],'PRIMARY_HEADERS_CHANGED')
    require((output/'egl_fixture_digest.h').read_text()==fixture_header,'FINITE_HEADER_CHANGED')
    for key,item in results.items():
        mode,kind=key.rsplit('-',1);require(sha(output/mode/kind)==item['binary_sha256'],'BINARY_CHANGED')
        if kind=='egl':packet(output/mode/'readback.rgba')
    require(libraries=={str(p.resolve()):sha(p.resolve()) for p in (args.host_egl,args.host_gles)},'LIBRARIES_CHANGED')
    require(sha(args.actual_texture)==TEXTURE_SHA and sha(output/'box-1.texture')==TEXTURE_SHA,'TEXTURE_CHANGED')
    proof={'schema':'coh-gpu-lease-host-egl-v1','passed':True,'source_revision':revision,'source_sha256':pins,
        'current_committed_sources_verified':True,'fixture':{'bytes':43990,'sha256':TEXTURE_SHA},'host_headers':header_pins,
        'compiler':subprocess.check_output(['cc','--version'],text=True).splitlines()[0],
        'host_library_files_before':libraries,'host_library_files_after':libraries,'host_loaded_mapping_verified':False,
        'results':results,'mode_flags':modes,'finite_fixture_digest_header_sha256':sha(output/'egl_fixture_digest.h'),
        'finite_fixture_digest_is_general_sha256':False,'independent_pillow':pillow,'native_stack':frames,'stack_sum_times_four':4*sum(row['bytes'] for row in frames),
        'cpp_link_passed':True,'cpp_binary_sha256':sha(output/'cpp-link'),
        'production_c_object_sha256':sha(objects[0]),'public_symbols':exported,'semantic_mutations_refused':mutations,
        'actual_host_gles_executed':True,'android_built':False,'android_executed':False,'system_driver_sanitized':False,
        'asan_leak_detection':False,'nine_world_prerequisites_admitted':False,'production_prepare_executed':False,
        'current_generation_admitted':False,'source_generation_admitted':False,'actor_authority':False,'material_authority':False,'world_authority':False}
    (output/'qualification.json').write_text(json.dumps(proof,indent=2)+'\n');return proof
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source-root','actual-texture','host-headers','host-egl','host-gles','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--sanitize',action='store_true');args=parser.parse_args()
    result=prepare(args);print(json.dumps({'passed':True,'actual_host_gles_executed':True,'modes':list(result['results']),
        'world_authority':False,'actor_authority':False,'source_generation_admitted':False}))
if __name__=='__main__':main()
