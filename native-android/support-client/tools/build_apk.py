#!/usr/bin/env python3
"""Build the separate offline native support client with pinned SDK/NDK tools.

No Gradle, accepted-client source editing, workflow mutation or production runtime
dependency is needed. A coordinator-owned source manifest defines the new module
closure. Output APK identity and every admitted source/asset are recorded.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import zipfile

PACKAGE='org.coh.nativesupport'
VERSION='0.2.0-gameplay'
VERSION_CODE=201
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
TARGETS={'arm64-v8a':'aarch64-linux-android26-clang','x86_64':'x86_64-linux-android26-clang'}

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(argv,cwd=None,env=None):
    p=subprocess.run([str(x) for x in argv],cwd=cwd,env=env,capture_output=True,text=True)
    require(p.returncode==0,'Command failed: '+' '.join(map(str,argv))+'\n'+p.stdout[-5000:]+p.stderr[-8000:])
    return p.stdout

def variables(a,generated):
    return {'source_root':str(a.source_root),'generated':str(generated),
            'codec_root':str(a.codec_root) if a.codec_root else '', 'python':shutil.which('python3') or 'python3'}

def expand(value,values):return str(value).format_map(values)

def resolve(value,a,values):
    result=Path(expand(value,values))
    return result if result.is_absolute() else a.source_root/result

def identity(path,root):
    try:name=str(path.relative_to(root))
    except ValueError:name=str(path)
    return {'file':name,'bytes':path.stat().st_size,'sha256':sha(path)}

def source_config(a,generated):
    config=json.loads(a.config.read_text());require(config.get('schema')==1,'Unsupported source manifest schema')
    values=variables(a,generated)
    for step in config.get('generated',[]):
        command=[expand(x,values) for x in step['command']]
        run(command,cwd=a.source_root)
        for path in step.get('outputs',[]):require(resolve(path,a,values).is_file(),'Generated output missing: '+path)
    sources=[resolve(x,a,values) for x in config['sources']]
    require(0<len(sources)<=512 and len(sources)==len(set(sources)),'Source closure is empty/duplicate/oversized')
    require(all(p.is_file() and p.suffix=='.c' for p in sources),'Missing or non-C source in native manifest')
    includes=[resolve(x,a,values) for x in config.get('include_dirs',[])]+[generated]
    require(all(p.is_dir() for p in includes),'Missing native include directory')
    return config,values,sources,includes

def compile_native(a,abi,config,values,sources,includes,build):
    native=build/abi;native.mkdir()
    tools=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin';cc=tools/TARGETS[abi]
    require(cc.is_file(),'NDK compiler missing: '+str(cc))
    common=['-std=c11','-O2','-fPIC','-Wall','-Wextra','-ffp-contract=off','-fno-strict-aliasing']
    common += [expand(x,values) for x in config.get('cflags',[])]
    for include in includes:common+=['-I',str(include)]
    per_source=config.get('per_source_cflags',{})
    jobs=[]
    for source_entry,source in zip(config['sources'],sources):
        obj=native/(source.stem+'-'+hashlib.sha256(str(source).encode()).hexdigest()[:12]+'.o')
        try:key=str(source.relative_to(a.source_root))
        except ValueError:key=str(source)
        selected=per_source.get(source_entry,per_source.get(key,per_source.get(str(source),[])))
        flags=[expand(x,values) for x in selected]
        jobs.append(([cc,*common,*flags,'-MMD','-MF',obj.with_suffix('.d'),'-c',source,'-o',obj],obj))
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        list(pool.map(lambda item:run(item[0],cwd=a.source_root),jobs))
    name=config.get('library','coh_support_client')
    require(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',name),'Invalid library name')
    so=native/('lib'+name+'.so')
    ldlibs=config.get('ldlibs',['android','EGL','GLESv3','z','m'])
    require(all(re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',x) for x in ldlibs),'Invalid linker library')
    run([cc,'-shared','-Wl,--no-undefined','-Wl,-z,max-page-size=16384',*[x[1] for x in jobs],
         *['-l'+x for x in ldlibs],*config.get('ldflags',[]),'-o',so])
    elf=run([tools/'llvm-readelf','-h',so]);machine='AArch64' if abi=='arm64-v8a' else 'Advanced Micro Devices X86-64'
    require(machine in elf,'Native ELF architecture differs')
    dependencies=set()
    for _,obj in jobs:
        depfile=obj.with_suffix('.d')
        require(depfile.is_file(),'Compiler dependency receipt missing')
        body=depfile.read_text().replace('\\\n',' ').partition(':')[2]
        for name in shlex.split(body):
            dependency=Path(name)
            if not dependency.is_absolute():dependency=a.source_root/dependency
            dependency=dependency.resolve()
            require(dependency.is_file(),'Compiler dependency disappeared')
            dependencies.add(dependency)
    return so,{'abi':abi,'elf_machine':machine,'sha256':sha(so),'bytes':so.stat().st_size,
               'compiler':run([cc,'--version']).splitlines()[0],
               'compiled_inputs':[identity(p,a.source_root) for p in sorted(dependencies)],
               'compiled_inputs_scope':'Compiler -MMD closure includes direct/indirect non-system headers and generated inputs; NDK system headers are bound by NDK revision.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,default=REPO)
    p.add_argument('--sdk',type=Path,default=os.environ.get('ANDROID_HOME',os.environ.get('ANDROID_SDK_ROOT','')))
    p.add_argument('--ndk',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--config',type=Path)
    p.add_argument('--assets',type=Path)
    p.add_argument('--codec-root',type=Path)
    p.add_argument('--abis',nargs='+',choices=list(TARGETS),default=list(TARGETS))
    p.add_argument('--keystore',type=Path)
    p.add_argument('--key-alias',default='androiddebugkey')
    p.add_argument('--jobs',type=int,default=min(8,os.cpu_count() or 1))
    a=p.parse_args();a.source_root=a.source_root.resolve();a.sdk=a.sdk.resolve();a.ndk=a.ndk.resolve();a.output=a.output.resolve()
    app=a.source_root/'native-android/support-client'
    a.config=(a.config or app/'build-sources.json').resolve();a.assets=(a.assets or app/'assets').resolve()
    if a.codec_root:a.codec_root=a.codec_root.resolve()
    require(0<a.jobs<=64,'Invalid parallel compilation limit')
    require(a.config.is_file() and (app/'AndroidManifest.xml').is_file() and a.assets.is_dir(),'Coordinator app manifest/assets/source closure not ready')
    a.output.mkdir(parents=True,exist_ok=True)
    tools=a.sdk/'build-tools/35.0.0';android_jar=a.sdk/'platforms/android-35/android.jar'
    for tool in ('aapt2','d8','zipalign','apksigner'):require((tools/tool).is_file(),'SDK tool missing: '+tool)
    require(android_jar.is_file(),'android-35 platform missing')
    java=shutil.which('java');require(java,'Java runtime missing')
    with tempfile.TemporaryDirectory(prefix='coh-support-package-') as temporary:
        build=Path(temporary);generated=build/'generated';generated.mkdir()
        config,values,sources,includes=source_config(a,generated)
        classes=build/'classes';classes.mkdir();dex=build/'dex';dex.mkdir();generated_java=build/'java';generated_java.mkdir()
        resources=build/'resources.apk'
        link=[tools/'aapt2','link','--manifest',app/'AndroidManifest.xml','-I',android_jar,
              '--min-sdk-version','26','--target-sdk-version','33','--version-code',str(VERSION_CODE),
              '--version-name',VERSION,'--rename-manifest-package',PACKAGE,'--java',generated_java,
              '-A',a.assets,'-o',resources]
        if (app/'res').is_dir():
            compiled=build/'resources.zip';run([tools/'aapt2','compile','--dir',app/'res','-o',compiled]);link+=['-R',compiled]
        run(link)
        java_sources=list((app/'java').rglob('*.java'))+list(generated_java.rglob('*.java'))
        for entry in config.get('java_sources',[]):
            path=resolve(entry,a,values)
            java_sources.extend(path.rglob('*.java') if path.is_dir() else [path])
        java_sources=list(dict.fromkeys(java_sources))
        require(java_sources and all(x.is_file() for x in java_sources),'Java source closure is incomplete')
        run([java,'-m','jdk.compiler/com.sun.tools.javac.Main','-encoding','UTF-8','-source','8','-target','8',
             '-classpath',android_jar,'-d',classes,*java_sources])
        classfiles=list(classes.rglob('*.class'));require(classfiles,'Java compiler produced no classes')
        env=dict(os.environ);env['JAVA_HOME']=str(Path(java).resolve().parents[1])
        run([tools/'d8','--min-api','26','--lib',android_jar,'--output',dex,*classfiles],env=env)
        dexfiles=list(dex.glob('*.dex'));require(dexfiles,'D8 produced no dex')
        key=a.keystore or build/'debug.keystore'
        if not key.is_file():
            require(a.keystore is None,'Requested signing key is missing')
            keytool=shutil.which('keytool');require(keytool,'keytool missing')
            run([keytool,'-genkeypair','-keystore',key,'-storepass','android','-keypass','android',
                 '-alias',a.key_alias,'-dname','CN=CoH Native Offline Support Debug,O=CoH Android,C=US',
                 '-keyalg','RSA','-keysize','2048','-validity','10000','-noprompt'])
        artifacts=[]
        for abi in a.abis:
            so,native=compile_native(a,abi,config,values,sources,includes,build)
            unsigned=build/(abi+'-unsigned.apk');shutil.copyfile(resources,unsigned)
            with zipfile.ZipFile(unsigned,'a') as z:
                for d in dexfiles:z.write(d,d.name,compress_type=zipfile.ZIP_DEFLATED)
                z.write(so,'lib/'+abi+'/'+so.name,compress_type=zipfile.ZIP_STORED)
            aligned=build/(abi+'-aligned.apk');run([tools/'zipalign','-P','16','-f','4',unsigned,aligned])
            label='arm64' if abi=='arm64-v8a' else 'emulator-x86_64'
            apk=a.output/('CoH-Native-Support-Client-'+VERSION+'-code'+str(VERSION_CODE)+'-'+label+'.apk')
            run([tools/'apksigner','sign','--ks',key,'--ks-key-alias',a.key_alias,'--ks-pass','pass:android',
                 '--key-pass','pass:android','--out',apk,aligned])
            signature=run([tools/'apksigner','verify','--verbose','--print-certs',apk])
            badging=run([tools/'aapt2','dump','badging',apk]);require("package: name='"+PACKAGE+"'" in badging,'APK identity differs')
            require("versionName='"+VERSION+"'" in badging,'APK version differs')
            require("versionCode='"+str(VERSION_CODE)+"'" in badging,'APK version code differs')
            certificates=re.findall(r'Signer #\d+ certificate SHA-256 digest: ([0-9a-f]{64})',signature)
            require(len(certificates)==1,'APK must have exactly one verified signing identity')
            with zipfile.ZipFile(apk) as z:
                require(z.testzip() is None,'APK zip integrity failure')
                require(all(not name.startswith('lib/') or name.startswith('lib/'+abi+'/') for name in z.namelist()),'Unexpected APK ABI')
                for asset in a.assets.rglob('*'):
                    if asset.is_file():require(hashlib.sha256(z.read('assets/'+str(asset.relative_to(a.assets)))).hexdigest()==sha(asset),'Packaged asset differs')
            (a.output/('apk-signature-'+abi+'.txt')).write_text(signature)
            (a.output/('apk-badging-'+abi+'.txt')).write_text(badging)
            artifacts.append(dict(identity(apk,a.output),signature_verified=True,manifest_verified=True,
                                  packaged_assets_verified=True,native=native,
                                  signer_certificate_sha256=certificates[0]))
        try:commit=run(['git','rev-parse','HEAD'],cwd=a.source_root).strip()
        except ValueError:commit=None
        compiled_paths=sorted({entry['file'] for artifact in artifacts for entry in artifact['native']['compiled_inputs']
                               if not Path(entry['file']).is_absolute()})
        try:dirty=run(['git','status','--porcelain','--','native-android/support-client',*compiled_paths,
                       *[str(s.relative_to(a.source_root)) for s in java_sources if s.is_relative_to(a.source_root)]],cwd=a.source_root).splitlines()
        except ValueError:dirty=['No Git checkout: packaging smoke or external source tree']
        receipt={'schema':1,'passed':True,'source_commit':commit,'package':PACKAGE,'version':VERSION,
                 'version_name':VERSION,'version_code':VERSION_CODE,
                 'source_tree_clean':not dirty,'source_tree_changes':dirty,
                 'scope':'separate offline support client; accepted0.3 APK unchanged; no live server',
                 'source_manifest':identity(a.config,a.source_root),'sources':[identity(x,a.source_root) for x in sources],
                 'java_sources':[identity(x,a.source_root) for x in java_sources if x.is_relative_to(a.source_root)],
                 'assets':[identity(x,a.assets) for x in sorted(a.assets.rglob('*')) if x.is_file()],
                 'artifacts':artifacts,'android_emulator_qualified':False,'physical_thor_accepted':False,
                 'ndk':(a.ndk/'source.properties').read_text(),'build_tools':'35.0.0','platform':'android-35',
                 'signing':'separate disposable debug certificate' if a.keystore is None else 'explicit debug keystore'}
        (a.output/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        (a.output/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['file']+'\n' for x in artifacts))
        print(json.dumps({'passed':True,'source_commit':commit,'artifacts':artifacts}))

if __name__=='__main__':main()
