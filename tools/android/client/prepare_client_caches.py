#!/usr/bin/env python3
"""Generate source-matched Parse6 caches with native x86 Wine, independently of FEX."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, secrets, shutil, struct, subprocess, sys, tempfile, time, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).resolve().parent))
import package_client_runtime as client
import prepare_client_prerequisites as prerequisites
import build_apk as builder
sys.path.insert(0,str(ROOT/'tools'))
import generate_runtime_data as generator
require=client.require
EPOCH=1767225600
ROLE='actual_client_generated_caches'
MANIFEST='client-cache-manifest.json'
ARCHIVE='client-caches.zip'
PREFIXES=('data/bin/','data/server/bin/','data/geobin/')
ACCEPTED_CACHE_RUN=36707839624
ACCEPTED_CACHE_COMMIT='a40250b0032bd05a333514920722ddffa4427730'
ACCEPTED_CACHE_FILES={
    ARCHIVE:{'bytes':27071659,'sha256':'5d7f5b5c1932cf755f4063092ba56a30b16d1a705c6716a98b71f9738d61c051'},
    MANIFEST:{'bytes':20195,'sha256':'e5bc9ff306f90f96b6d34d4d481b30804af078b0e07845dafd71f7324dff6352'},
    ARCHIVE+'.sha256':{'bytes':84,'sha256':'d93561c7e4f0c1e26c3b90172faf7aa1ab80334db2d6743e8f702920736bdf1c'},
}


def pin(path):return builder.file_pin(path)

def safe_cache(name):
    return (isinstance(name,str) and name.isascii() and name.startswith(PREFIXES)
            and name.lower().endswith('.bin') and all(p not in ('','.','..') for p in name.split('/'))
            and '\\' not in name and ':' not in name)

def validate_dependency_dates(data):
    def string_at(position):
        size=struct.unpack_from('<H',data,position)[0]
        require(size<=1024,'Oversized cache dependency path')
        return data[position+2:position+2+size],position+((size+2+3)&~3)
    _,position=string_at(12)
    _,position=string_at(position)
    block_bytes,count=struct.unpack_from('<II',data,position);position+=8
    require(4<=block_bytes<=32*1024*1024 and count<=block_bytes//8,'Cache dependency block exceeds bound')
    for _ in range(count):
        name,position=string_at(position)
        require(name and not name.startswith((b'/',b'\\')) and b':' not in name
                and b'..' not in name.replace(b'\\',b'/').split(b'/'),'Unsafe cache dependency path')
        timestamp=struct.unpack_from('<I',data,position)[0];position+=4
        require(timestamp in (0,EPOCH-3600,EPOCH,EPOCH+3600),'Cache dependency timestamp is not normalized: '+name.decode('utf-8','replace'))


def verify_cache_archive(path):
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist()
        require(len(names)==len(set(n.casefold() for n in names)) and 1<len(names)<=1025,'Duplicate or oversized cache inventory')
        require(MANIFEST in names and archive.getinfo(MANIFEST).file_size<=1024*1024,'Cache manifest missing or oversized')
        manifest=json.loads(archive.read(MANIFEST))
        require(manifest.get('format')==1 and manifest.get('role')==ROLE
                and manifest.get('source_commit')==client.SOURCE and manifest.get('data_commit')==client.DATA
                and manifest.get('executable_sha256')==client.accepted()['files']['CityOfHeroes.exe']['sha256']
                and manifest.get('reference_run_id')==client.REFERENCE_RUN
                and manifest.get('prerequisites_manifest_sha256')==prerequisites.manifest_sha256()
                and manifest.get('normalized_mtime_epoch')==EPOCH,'Cache generation identity differs')
        require(manifest.get('generated_noncache_outputs')==[],'Unexpected generated noncache outputs')
        require(manifest.get('asset_archive_sha256')==builder.accepted_import_receipt()['bundle_contract']['asset.archive.sha256'],
                'Cache binary asset identity differs')
        files=manifest.get('files',{})
        require(isinstance(files,dict) and set(files)|{MANIFEST}==set(names) and files,'Cache payload inventory differs')
        total=0
        for name,record in files.items():
            require(safe_cache(name),'Unsafe cache path')
            entry=archive.getinfo(name);mode=entry.external_attr>>16
            require(not entry.is_dir() and (mode&0o170000) in (0,0o100000) and not entry.flag_bits&1,'Unsafe cache entry')
            require(type(record.get('bytes')) is int and 0<record['bytes']<=256*1024*1024 and entry.file_size==record['bytes'],'Cache size differs')
            total+=entry.file_size;require(total<=512*1024*1024,'Cache package exceeds bound')
            data=archive.read(name)
            require(hashlib.sha256(data).hexdigest()==record['sha256'],'Cache payload hash differs')
            with tempfile.TemporaryDirectory() as temporary:
                inspected=Path(temporary)/'cache.bin';inspected.write_bytes(data)
                envelope=generator.parse6_envelope(inspected)
            require(envelope['format']=='Parse6' and envelope['schema_crc']==record.get('schema_crc'),
                    'Cache envelope or schema CRC differs')
            validate_dependency_dates(data)
    return manifest


def verify_accepted_cache_donor(directory):
    """Reuse exact native-generated bytes while checking current client input compatibility."""
    directory=Path(directory)
    require(directory.is_dir() and not directory.is_symlink()
            and {p.name for p in directory.iterdir()}==set(ACCEPTED_CACHE_FILES),'Accepted cache donor inventory differs')
    for name,expected in ACCEPTED_CACHE_FILES.items():
        path=directory/name
        require(path.is_file() and not path.is_symlink() and pin(path)==expected,'Accepted cache donor changed: '+name)
    # This checks the current game executable/source/data, reviewed assets,
    # prerequisites and normalization policy, independently of wrapper revisions.
    manifest=verify_cache_archive(directory/ARCHIVE)
    require(manifest==json.loads((directory/MANIFEST).read_text())
            and manifest.get('repository_commit')==ACCEPTED_CACHE_COMMIT
            and len(manifest['files'])==100,'Accepted cache generation provenance differs')
    return {'format':1,'scope':'exact_prepared_client_cache_reuse','donor_run_id':ACCEPTED_CACHE_RUN,
            'donor_artifact_id':11092897979,'generator_repository_commit':ACCEPTED_CACHE_COMMIT,
            'files':ACCEPTED_CACHE_FILES,'source_commit':manifest['source_commit'],'data_commit':manifest['data_commit'],
            'executable_sha256':manifest['executable_sha256'],
            'prerequisites_manifest_sha256':manifest['prerequisites_manifest_sha256'],
            'normalized_mtime_epoch':EPOCH,'cache_files':len(manifest['files']),
            'caches_regenerated':False,'gameplay_validated':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('atlas-apk','reference','archive','work','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--repository-commit',required=True);parser.add_argument('--wine',default='wine')
    args=parser.parse_args();args.work=args.work.resolve();args.output=args.output.resolve()
    require(not args.work.exists() and not args.output.exists(),'Fresh cache work/output required')
    args.work.mkdir(parents=True);args.output.mkdir(parents=True)
    imports=args.work/'import-assets';builder.extract_import_donor(args.atlas_apk,imports)
    import host_smoke as host
    data=host.import_game_data(imports,args.archive.resolve(),args.work,args.output)
    runtime=data.parent
    prerequisites.install(runtime)
    for directory,dirs,files in os.walk(data,followlinks=False):
        for name in dirs:require(not (Path(directory)/name).is_symlink(),'Linked imported directory')
        for name in files:
            path=Path(directory)/name;require(path.is_file() and not path.is_symlink(),'Linked imported file')
            os.utime(path,(EPOCH,EPOCH),follow_symlinks=False)
    (runtime/'tools').mkdir()
    receipt,folder,_=client.verified_donor(args.reference.resolve(),'reference')
    for name in client.selected_files(receipt):shutil.copyfile(folder/name,runtime/name)
    inputs={'source_commit':client.SOURCE,'data_commit':client.DATA,
            'build_file_sha256':{name:record['sha256'] for name,record in client.selected_files(receipt).items()},
            'import_donor':builder.import_donor(),'normalized_mtime_epoch':EPOCH,
            'prerequisites':prerequisites.contract(),'prerequisites_manifest_sha256':prerequisites.manifest_sha256()}
    (runtime/'runtime-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    os.environ.update(WINEPREFIX=str(args.work/'wine-prefix'),WINEDEBUG='-all',TZ='UTC',
                      LIBGL_ALWAYS_SOFTWARE='1',GALLIUM_DRIVER='llvmpipe',LP_NUM_THREADS='2',
                      WINEDLLOVERRIDES='mscoree,mshtml=d')
    wine_version=subprocess.check_output([args.wine,'--version'],text=True).strip()
    launcher=args.work/'client-launcher.exe'
    subprocess.run(['i686-w64-mingw32-gcc','-std=c11','-O2','-Wall','-Wextra','-Werror','-static-libgcc','-mconsole',
                    str(ROOT/'android/native/client-launcher.c'),'-luser32','-lkernel32','-o',str(launcher)],check=True)
    windows_work='Z:'+str(runtime).replace('/','\\')
    # The exact game remains the checked phase executable. Only its owned console
    # bridge is a runner prefix; no accepted generation tool or game is patched.
    generator.PHASES['client-bins']=('CityOfHeroes.exe',[windows_work,'--generate-caches'])
    try:
        result=generator.run_generation(runtime,args.output/'generation',phases=('client-bins',),
            runner=(args.wine,str(launcher),secrets.token_hex(16)),timeout=900)
    finally:
        subprocess.run(['wineserver','-k'],check=False,timeout=30)
    require(result['status']=='output_checks_passed_runtime_unvalidated','Native client cache generation did not complete')
    stdout=(args.output/'generation/client-bins/stdout.log').read_text(errors='replace')
    require('COH_CLIENT_CONSOLE_TRUNCATED_V1' not in stdout,'Console capture exceeded its evidence bound')
    require(not result['phases'][0]['removed_outputs'],'Client generation removed source inputs')
    noncache=[r for r in result['phases'][0]['written_outputs'] if not safe_cache(r['path'])]
    require(not noncache,'Client generation changed noncache inputs: '+', '.join(r['path'] for r in noncache))
    files={}
    for record in result['phases'][0]['written_outputs']:
        name=record['path']
        if not safe_cache(name):continue
        path=runtime/name;envelope=generator.parse6_envelope(path)
        if envelope['format']!='Parse6':continue
        validate_dependency_dates(path.read_bytes())
        files[name]={**pin(path),'schema_crc':envelope['schema_crc']}
    require(files and 'data/bin/sequencers.bin' in {n.lower() for n in files},'Required sequencer Parse6 cache missing')
    manifest={'format':1,'role':ROLE,'source_commit':client.SOURCE,'data_commit':client.DATA,
              'repository_commit':args.repository_commit,'reference_run_id':client.REFERENCE_RUN,
              'executable_sha256':receipt['files']['CityOfHeroes.exe']['sha256'],
              'asset_archive_sha256':builder.accepted_import_receipt()['bundle_contract']['asset.archive.sha256'],
              'import_donor':builder.import_donor(),'normalized_mtime_epoch':EPOCH,
              'prerequisites_manifest_sha256':prerequisites.manifest_sha256(),
              'generator_platform':'native_x86_64_linux_wine_x86_client','wine_version':wine_version,
              'generation_report':pin(args.output/'generation/generation-report.json'),
              'launcher_source_sha256':pin(ROOT/'android/native/client-launcher.c')['sha256'],
              'launcher_sha256':pin(launcher)['sha256'],
              'generated_noncache_outputs':[],
              'files':dict(sorted(files.items())),'nonfatal_queued_errors_reviewed':False,
              'cache_consumption_validated':False,'android_execution_validated':False,'gameplay_validated':False}
    (args.output/MANIFEST).write_bytes(client.canonical(manifest))
    with zipfile.ZipFile(args.output/ARCHIVE,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        archive.writestr(MANIFEST,client.canonical(manifest))
        for name in sorted(files):archive.write(runtime/name,name)
    verify_cache_archive(args.output/ARCHIVE)
    (args.output/(ARCHIVE+'.sha256')).write_text(pin(args.output/ARCHIVE)['sha256']+'  '+ARCHIVE+'\n')
    print(json.dumps({'files':len(files),'bytes':sum(r['bytes'] for r in files.values()),'archive':pin(args.output/ARCHIVE)},indent=2))
if __name__=='__main__':main()
