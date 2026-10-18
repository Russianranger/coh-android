#!/usr/bin/env python3
"""Only the new standalone source-owner to typed GPU upload/lease boundary."""
from __future__ import annotations
import argparse,hashlib,json,os,shlex,shutil,struct,subprocess,tempfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASE=('coh_wr_gpu_lease.c','coh_wr_gpu_texture.c','coh_wr_texture.c','coh_wr_sampler.c',
      '../assets/coh_asset_loader.c','../../src/coh_assets.c','../../src/coh_dds.c',
      'coh_wr_tex_rgba32.c','coh_wr_tex_namespace.c')
FLAGS=('-std=c11','-Wall','-Wextra','-Werror','-pedantic','-fno-fast-math','-ffp-contract=off')
ZIP_SHA='87a999e6c1c003b96a9fa169ce11637b61eb696766517e063fafce73fdc39c24'
GREY_SHA='b628966e91a864f9edcb0634605823a7ef3d8e2305f36d1a9f6e9834b018a013'
LEGACY_FUNCTION_SHA='d04648a0cb91659284c39625ee258fcfcf15ffbc7dfe21bcf7f8447692bcc204'
FALSE=('current_namespace','default_identity','material_authority','actor_authority',
       'world_authority','source_generation_admitted','production_prepare_executed','app_context_adopted')
def need(value,code):
    if not value:raise ValueError('SOURCE_RGBA32_GPU_'+code)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def identity(path):
    path=Path(path);need(path.is_file() and not path.is_symlink(),'REGULAR')
    raw=path.read_bytes();return {'bytes':len(raw),'sha256':digest(raw)}
def project_sources(root):
    here=Path(root)/'native-android/engine/world-render-adapter'
    return [(here/name).resolve() for name in (*BASE,'tests/test_source_rgba32_gpu.c')]
def committed_sources(root,pins,revision):
    root=Path(root)
    for name,pin in pins.items():
        path=root/name;need(not path.is_symlink() and identity(path)['sha256']==pin,'CURRENT_SOURCE')
        child=subprocess.run(['git','show',revision+':'+name],cwd=root,capture_output=True,timeout=30)
        need(child.returncode==0 and digest(child.stdout)==pin,'COMMITTED_SOURCE')
def legacy_function_binding():
    source=(HERE/'coh_wr_gpu_texture.c').read_text();signature='CohStatus coh_wr_gpu_upload('
    need(source.count(signature)==1,'LEGACY_FUNCTION');start=source.index(signature);end=source.index('{',start)+1;depth=1
    while depth:
        if source[end]=='{':depth+=1
        elif source[end]=='}':depth-=1
        end+=1
    body=source[start:end]+'\n'
    new='r->report=(CohWrGpuReport){token,report,b->gpu_reservation,b->external_bytes+b->gpu_reservation+sizeof(*r),report.levels,COH_WR_GPU_SOURCE_LEGACY_DXT,{0},sizeof(*r)};'
    old='r->report=(CohWrGpuReport){token,report,b->gpu_reservation,b->external_bytes+b->gpu_reservation+sizeof(*r),report.levels};'
    need(body.count(new)==1 and digest(body.replace(new,old).encode())==LEGACY_FUNCTION_SHA,'LEGACY_BODY_UNCHANGED')
    # The old sampler qualifier must still identify its old PBO mutation once.
    need(source.count('CALL(o->bind_unpack_buffer(o->context,0));')==1,'LEGACY_MUTATION_ANCHOR')
    return {'baseline_revision':'e54ceb26cf5dbd6ca74442d2de196827c82265fe','baseline_function_sha256_lf':LEGACY_FUNCTION_SHA,
        'current_function_sha256_lf':digest(body.encode()),'only_report_initializer_changed':True}
def _dds(w,h,count,rgba):
    out=bytearray(128);out[:4]=b'DDS '
    for offset,value in {4:124,8:0x2100f if rgba else 0x21007,12:h,16:w,20:w*4 if rgba else 8,
                         28:count,76:32,80:0x41 if rgba else 4,84:0 if rgba else 0x31545844,
                         88:32 if rgba else 0,92:0xff0000 if rgba else 0,96:0xff00 if rgba else 0,
                         100:0xff if rgba else 0,104:0xff000000 if rgba else 0,108:0x401008}.items():
        struct.pack_into('<I',out,offset,value)
    if not rgba:return bytes(out)+struct.pack('<HHI',0xf800,0,0)
    for level in range(count):
        for y in range(h):
            for x in range(w):
                alpha=0 if x==y==0 else 255 if x==w-1 and y==h-1 else (x*37+y*71+level*61)%256
                out.extend(((11+x*29+y*7+level*31)%256,(37+x*3+y*47+level*13)%256,
                            (173+x*53+y*19+level*5)%256,alpha))
        w=max(1,w//2);h=max(1,h//2)
    return bytes(out)
def _wrapper(name,dds,w,h,tx2=b''):
    name=name.encode()+b'\0';header=bytearray(32)
    struct.pack_into('<5I',header,0,32+len(name)+len(tx2),len(dds),w,h,0)
    header[28]=1;header[29:32]=b'TX2' if tx2 else b'TEX'
    return bytes(header)+name+tx2+dds
def _mips(body,legacy=False):
    start=struct.unpack_from('<I',body)[0];dds=body[start:]
    w,h,count=struct.unpack_from('<I',dds,16)[0],struct.unpack_from('<I',dds,12)[0],struct.unpack_from('<I',dds,28)[0]
    if legacy:
        need(w==h==4 and count==1 and dds[128:]==struct.pack('<HHI',0xf800,0,0),'LEGACY_CONTROL')
        return [(4,4,bytes((255,0,0,255))*16)]
    at=128;out=[]
    for _ in range(count or 1):
        raw=dds[at:at+w*h*4];need(len(raw)==w*h*4,'MIP_EXTENT')
        pixels=bytearray(raw)
        for n in range(0,len(raw),4):pixels[n],pixels[n+2]=raw[n+2],raw[n]
        out.append((w,h,bytes(pixels)));at+=len(raw);w=max(1,w//2);h=max(1,h//2)
    need(at==len(dds),'CHAIN_EXTENT');return out
def prepare_fixture(archive,output):
    output=Path(output);need(not output.exists(),'FRESH_FIXTURE');output.mkdir(parents=True,mode=0o700)
    raw=Path(archive).read_bytes();need(len(raw)==12308 and digest(raw)==ZIP_SHA,'EXACT_ARCHIVE')
    with zipfile.ZipFile(archive) as z:
        manifest=z.read('fresh-default-headers/manifest.json');report=z.read('default-headers.json')
        need(digest(manifest)=='1fe575013883344e4ce9f04d83739356e5605f9d6caf7e8190385f420ea5e2c5'
             and digest(report)=='ab1cf2773b540061c62fd9b42e3ca5f6d58e191805b8a35c8dbf0a06646789a5','ADMISSION_RECEIPTS')
        files=json.loads(manifest)['files'];names={'default-headers.json','fresh-default-headers/manifest.json'}|{'fresh-default-headers/'+x['filename'] for x in files}
        need(len(files)==7 and len(z.namelist())==9 and set(z.namelist())==names and z.testzip() is None,'ARCHIVE_MEMBERS')
        selected=[x for x in files if x['virtual_asset_path']=='data/texture_library/world/filler/grey.texture'];need(len(selected)==1,'GREY_MEMBER')
        grey=z.read('fresh-default-headers/'+selected[0]['filename']);need(len(grey)==894 and digest(grey)==GREY_SHA,'GREY_BYTES')
    pattern=_wrapper('texture_library/qualification/pattern.dds',_dds(8,8,4,True),8,8,b'pattern-TX2')
    legacy=_wrapper('texture_library/qualification/legacy.dds',_dds(4,4,1,False),4,4)
    bodies=[grey,pattern,legacy];paths=['texture_library/world/filler/grey.texture','texture_library/qualification/pattern.texture','texture_library/qualification/legacy.texture']
    names=['grey.texture','pattern.texture','legacy.texture'];header=['/* finite exact-byte digest predicates, not a general SHA implementation */']
    for i,body in enumerate(bodies):header.append('static const uint8_t source_fixture_data%d[]={%s};'%(i,','.join(str(x) for x in body)))
    header.append('static const SourceFixture source_fixtures[]={')
    for i,(name,path,body) in enumerate(zip(names,paths,bodies)):
        header.append('{%s,%s,source_fixture_data%d,sizeof(source_fixture_data%d),{%s}},'%(json.dumps(name),json.dumps(path),i,i,','.join(str(x) for x in hashlib.sha256(body).digest())))
    header.append('};\n');contents=dict(zip(names,bodies));contents['source_rgba32_fixture.h']='\n'.join(header).encode()
    for name,data in contents.items():(output/name).write_bytes(data)
    decoded=[_mips(grey),_mips(pattern),_mips(legacy,True)];packet=b'';segments=[]
    for epoch in range(2):
        for index in (2,0,1):
            for level,(w,h,pixels) in enumerate(decoded[index]):
                segments.append({'epoch':epoch,'fixture':names[index],'level':level,'width':w,'height':h,'offset':len(packet),'bytes':len(pixels),'sha256':digest(pixels)})
                packet+=pixels
    need(len(packet)==1488 and len(segments)==18,'READBACK_PROFILE')
    return {'schema':'coh-source-rgba32-finite-input-v1','archive':{'bytes':len(raw),'sha256':ZIP_SHA},
        'files':{name:identity(output/name) for name in contents},'expected_readback':{'bytes':len(packet),'sha256':digest(packet)},
        'segments':segments,'authentic_fixture':'grey.texture','controlled_fixtures':['pattern.texture','legacy.texture'],
        'fixture_provider_generation_only':True,'finite_fixture_digest_is_general_sha256':False}
def validate_result(raw,readback,fixture):
    need(type(raw) is bytes and 0<len(raw)<=16384,'STDOUT_BOUND')
    def pairs(rows):
        out={}
        for key,value in rows:need(key not in out,'DUPLICATE_JSON');out[key]=value
        return out
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:need(False,'JSON_NUMBER'))
    fixed={'schema':'coh-source-rgba32-gpu-v1','passed':True,'actual_gles':True,'cleanup_verified':True,
        'rgba32_uploads':2,'legacy_uploads':1,'images':20,'readbacks':18,'cancelled_uploads':6,
        'pending_journal_recovered':True,'provider_holds':2,'provider_drops':2,
        'source_retired_before_rgba32_upload':True,'all_cpu_retired_before_lease_readback':True,
        'registry_retains':1,'registry_releases':1,'generated':9,'deleted':9,'tracked_calloc_blocks_live':0,
        'rgba32_preparation_reserve':16384,'gpu_external_reservation':33554432,'lease_external_reservation':50331648,
        'contexts_created':1,'contexts_destroyed':1,'surfaces_created':1,'surfaces_destroyed':1,
        'finite_fixture_digest_only':True,'sampler_fixture_only':True,'provider_fixture_only':True,
        **{key:False for key in FALSE}}
    extra={'checks','gpu_owner_bytes','gpu_report_bytes','prior_gpu_owner_bytes','gpu_owner_growth_bytes','gl_version','gl_renderer'}
    need(type(value) is dict and set(value)==set(fixed)|extra,'RESULT_FIELDS')
    for key,want in fixed.items():need(type(value[key]) is type(want) and value[key]==want,'RESULT_'+key)
    for key in ('checks','gpu_owner_bytes','gpu_report_bytes','prior_gpu_owner_bytes','gpu_owner_growth_bytes'):need(type(value[key]) is int and 0<value[key]<10000,'RESULT_INTEGER')
    need(value['checks']==367 and value['gpu_owner_bytes']==1328 and value['gpu_report_bytes']==176
         and value['prior_gpu_owner_bytes']==1296 and value['gpu_owner_growth_bytes']==32,'ACTUAL_OWNER_SIZE_AND_CHECKS')
    for key in ('gl_version','gl_renderer'):need(type(value[key]) is str and 0<len(value[key])<192 and all(32<=ord(c)<127 for c in value[key]),'GL_IDENTITY')
    need(identity(readback)==fixture['expected_readback'],'EXACT_READBACK')
    data=Path(readback).read_bytes()
    for item in fixture['segments']:need(digest(data[item['offset']:item['offset']+item['bytes']])==item['sha256'],'MIP_READBACK')
    return value
def _call(command,cwd,output,label,env=None,success=True):
    child=subprocess.run(list(map(str,command)),cwd=cwd,capture_output=True,timeout=180,env=env)
    need(len(child.stdout)+len(child.stderr)<=4*1024**2,'CHILD_BOUND')
    (output/(label+'.stdout')).write_bytes(child.stdout);(output/(label+'.stderr')).write_bytes(child.stderr)
    if success:need(child.returncode==0,'CHILD_'+label)
    return child
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source-root','actual-defaults-zip','host-headers','host-egl','host-gles','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--sanitize',action='store_true');args=p.parse_args();root=args.source_root.resolve();out=args.output.resolve();headers=args.host_headers.resolve()
    need(root==ROOT and not out.exists(),'ROOT_FRESH_OUTPUT');out.mkdir(parents=True,mode=0o700)
    fixture=prepare_fixture(args.actual_defaults_zip,out/'input');include=['-I'+str(root/'native-android/include'),'-I'+str(headers),'-I'+str(out/'input')]
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();sources=project_sources(root)
    dependency=_call(['cc',*FLAGS,*include,'-MM',*sources],root,out,'dependencies').stdout.decode()
    pins={str(path.relative_to(root)):identity(path)['sha256'] for path in (Path(__file__),HERE/'tests/run_source_rgba32_android.py',HERE/'SOURCE_RGBA32_GPU_QUALIFICATION.md',HERE/'egl-host-header-pins.json')}
    for line in dependency.replace('\\\n',' ').splitlines():
        need(':' in line,'DEPENDENCY_SYNTAX')
        for name in shlex.split(line.split(':',1)[1]):
            path=Path(name).resolve()
            if path.is_relative_to(root):pins[str(path.relative_to(root))]=identity(path)['sha256']
            else:need(path.is_relative_to(headers) or path==out/'input/source_rgba32_fixture.h','EXTERNAL_DEPENDENCY')
    committed_sources(root,pins,revision)
    legacy_binding=legacy_function_binding()
    header_pins=json.loads((HERE/'egl-host-header-pins.json').read_bytes())
    for name,pin in header_pins.items():need(identity(headers/name)=={'bytes':pin['bytes'],'sha256':pin['sha256']},'HOST_HEADERS')
    libraries={str(path.resolve()):identity(path.resolve()) for path in (args.host_egl,args.host_gles)}
    modes=[('release',['-O2'])]
    if args.sanitize:modes += [('address',['-O1','-g','-fsanitize=address','-no-pie']),('undefined',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]
    compiler=Path(shutil.which('cc')).resolve();compiler_before=identity(compiler)
    compiler_version=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0]
    results={};frames={};env=dict(os.environ,EGL_PLATFORM='surfaceless',LIBGL_ALWAYS_SOFTWARE='1',ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
    link=[str(args.host_egl.resolve()),str(args.host_gles.resolve()),'-pthread','-lz','-lm','-Wl,--wrap=calloc','-Wl,--wrap=free']
    for mode,flags in modes:
        directory=out/mode;directory.mkdir();binary=directory/'coh_source_rgba32_gpu'
        _call(['cc',*FLAGS,*flags,'-fstack-usage',*include,*sources,*link,'-o',binary],root,out,'compile-'+mode)
        binary_before=identity(binary)
        result=_call([binary,*(out/'input'/name for name in ('grey.texture','pattern.texture','legacy.texture')),directory/'readback.rgba'],root,out,'execute-'+mode,env)
        need(identity(binary)==binary_before,'EXECUTED_BINARY_UNCHANGED')
        results[mode]={'binary':binary_before,'readback':identity(directory/'readback.rgba'),'native':validate_result(result.stdout,directory/'readback.rgba',fixture)}
        if mode=='release':
            for report in directory.glob('*.su'):
                for row in report.read_text().splitlines():
                    location,size,kind=row.split('\t')
                    if 'coh_wr_gpu_texture.c:' in location:
                        need(kind in ('static','dynamic,bounded'),'GPU_STACK_KIND');name=location.rsplit(':',1)[-1]
                        frames[name]=max(frames.get(name,0),int(size))
    need(len({x['native']['checks'] for x in results.values()})==1,'MODE_CHECKS')
    need(frames and 4*sum(frames.values())<=16384,'GPU_PREPARATION_STACK')
    # Actual production C objects are call-linked from C++; no C source is
    # compiled as C++, and this probe creates no GL context.
    objects=[];object_pins={}
    for index,source in enumerate(sources[:-1]):
        obj=out/('cpp-'+str(index)+'.o');_call(['cc',*FLAGS,'-O2',*include,'-c',source,'-o',obj],root,out,'cpp-object-'+str(index));objects.append(obj);object_pins[obj.name]=identity(obj)
    cpp=out/'link.cpp';cpp.write_text('#include "coh_wr_gpu_texture.h"\nint main(){auto p=&coh_wr_gpu_upload_rgba32;(void)p;return coh_wr_gpu_report(nullptr,nullptr)==COH_INVALID?0:1;}\n')
    cpp_binary=out/'cpp-link';_call(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I'+str(HERE),cpp,*objects,'-pthread','-lz','-lm','-o',cpp_binary],root,out,'cpp-link')
    cpp_before=identity(cpp_binary);_call([cpp_binary],root,out,'cpp-execute');need(identity(cpp_binary)==cpp_before,'CPP_BINARY_UNCHANGED')
    source=(HERE/'coh_wr_gpu_texture.c').read_text();mutations=[]
    changes=(('source_aggregate_minimum','b->external_bytes<minimum','0'),
        ('missing_RGBA_mip','for(uint32_t level=0;level<view.mip_count;level++){\n        if(cancelled','for(uint32_t level=0;level+1<view.mip_count;level++){\n        if(cancelled'),
        ('source_kind_erased','aggregate,view.mip_count,COH_WR_GPU_SOURCE_NAMESPACE_RGBA32','aggregate,view.mip_count,COH_WR_GPU_SOURCE_LEGACY_DXT'),
        ('late_cancel_ignored','s=restore(&staging,o);if(s!=COH_OK)goto rgba_fail;\n    if(cancelled(cancel)){s=COH_CANCELLED;goto rgba_fail;}','s=restore(&staging,o);if(s!=COH_OK)goto rgba_fail;'),
        ('pending_journal_error_erased','rgba_fail:\n    *j=staging;free(r);(void)coh_wr_gpu_retry_cleanup(j,o);return j->pending?COH_STATE:s;','rgba_fail:\n    *j=staging;free(r);(void)coh_wr_gpu_retry_cleanup(j,o);return s;'))
    for label,before,after in changes:
        need(source.count(before)==1,'MUTATION_TARGET_'+label);mutated=out/(label+'.c');mutated.write_text(source.replace(before,after));binary=out/label
        translated=[mutated if path==HERE/'coh_wr_gpu_texture.c' else path for path in sources]
        _call(['cc',*FLAGS,'-O2','-I'+str(HERE),*include,*translated,*link,'-o',binary],root,out,'compile-mutation-'+label)
        result=_call([binary,*(out/'input'/name for name in ('grey.texture','pattern.texture','legacy.texture')),out/(label+'.rgba')],root,out,'mutation-'+label,env,success=False)
        need(result.returncode!=0 and b'source_gpu:' in result.stderr,'MUTATION_REFUSED_'+label);mutations.append(label)
    committed_sources(root,pins,revision)
    with tempfile.TemporaryDirectory(prefix='coh-source-gpu-readmit-') as temporary:
        need(prepare_fixture(args.actual_defaults_zip,Path(temporary)/'input')==fixture,'FINAL_FIXTURE_REGENERATION')
    for name,pin in fixture['files'].items():need(identity(out/'input'/name)==pin,'FINAL_INPUT')
    for mode,item in results.items():
        need(identity(out/mode/'coh_source_rgba32_gpu')==item['binary'] and identity(out/mode/'readback.rgba')==item['readback'],'FINAL_BINARY_READBACK')
    need(identity(cpp_binary)==cpp_before and identity(compiler)==compiler_before,'FINAL_CPP_COMPILER')
    for obj in objects:need(identity(obj)==object_pins[obj.name],'FINAL_CPP_OBJECT')
    for name,pin in header_pins.items():need(identity(headers/name)=={'bytes':pin['bytes'],'sha256':pin['sha256']},'FINAL_HOST_HEADERS')
    need(libraries=={str(path.resolve()):identity(path.resolve()) for path in (args.host_egl,args.host_gles)},'FINAL_LIBRARIES')
    proof={'schema':'coh-source-rgba32-gpu-host-v1','passed':True,'source_revision':revision,'source_sha256':pins,
        'current_committed_source_verified':True,'fixture':fixture,'host_headers':header_pins,'host_library_files_before':libraries,'host_library_files_after':libraries,
        'legacy_upload_function_binding':legacy_binding,
        'loaded_platform_mapping_verified':False,'system_driver_sanitized':False,'asan_leak_detection':False,'tracked_module_calloc_lifetime_checked':True,
        'declared_compiler_file_before':compiler_before,'declared_compiler_file_after':identity(compiler),'compiler_version':compiler_version,
        'host_full_system_toolchain_and_standard_headers_verified':False,'gpu_adapter_stack_frames':frames,'gpu_adapter_frame_sum_times_four':4*sum(frames.values()),
        'stack_scope_excludes_namespace_loader_backend_callbacks_libc_and_driver':True,
        'semantic_mutations_refused':mutations,'actual_C_objects_CPP_call_link':{'passed':True,'binary':cpp_before,'objects':object_pins},
        'results':results,'old_gpu_602_replayed':False,'old_qualifiers_replayed':False,'android_built':False,'android_executed':False,
        'nine_world_prerequisites_admitted':False,**{key:False for key in FALSE}}
    (out/'qualification.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'passed':True,'modes':list(results),'world_authority':False}))
if __name__=='__main__':main()
