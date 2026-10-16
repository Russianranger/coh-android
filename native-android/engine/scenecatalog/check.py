#!/usr/bin/env python3
"""Exact original sendDef/catalog producer and bounded native ownership checks."""
from pathlib import Path
import argparse, ctypes as C, hashlib, importlib.util, json, os, shutil, struct, subprocess, tempfile
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
def run(command,**kwargs):
    p=subprocess.run(list(map(str,command)),text=True,capture_output=True,**kwargs)
    if p.returncode:raise RuntimeError(repr(command)+'\n'+p.stdout+p.stderr)
    return p

def prepare(root,d):
    spec=importlib.util.spec_from_file_location('catalog_original_groups',root/'native-android/engine/replication/groups_oracle.py')
    oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
    _,receipt=oracle.produce_fixtures(root,d)
    original=d/'groups-original.c';extension=(HERE/'tests/source_catalog_harness.c').read_text()
    original.write_text(original.read_text()+'\n'+extension)
    library=d/'catalog-original.so'
    run(['cc','-std=c99','-O0','-fno-strict-aliasing','-fPIC','-shared','-w','-I'+str(HERE),'-I'+str(root/'native-android/include'),original,'-lm','-lz','-o',library])
    lib=C.CDLL(str(library));lib.catalog_original.argtypes=[C.c_uint32]*4+[C.c_void_p,C.POINTER(C.c_uint32),C.c_void_p,C.POINTER(C.c_uint32),C.c_void_p]
    lib.catalog_record_original.argtypes=[C.c_uint32,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32)]
    compared=0
    fixtures=[];lines=['typedef struct {const unsigned char *catalog,*wire;size_t bytes,wire_bytes,wire_bits;unsigned which,aligned,legacy;unsigned counts[7];} CatalogFixture;\n'];rows=[]
    for which in (0,1,2,7,8,9,10,20,21,22):
        variants=((1,0),) if which in (20,21,22) else ((0,0),(1,0),(1,1))
        for aligned,legacy in variants:
            buf=(C.c_uint8*(32<<20))();wire=(C.c_uint8*(1<<20))();size=C.c_uint32();bits=C.c_uint32();counts=(C.c_uint32*7)()
            assert lib.catalog_original(which,aligned,legacy,0,buf,C.byref(size),wire,C.byref(bits),counts)==0
            raw=bytes(buf[:size.value]);w=bytes(wire[:(bits.value+7)//8]);idx=len(fixtures)
            if which not in (20,22):
                at=48
                for f in range(struct.unpack_from('<I',raw,24)[0]):
                    index,checksum,slots,records,n=struct.unpack_from('<5I',raw,at);assert index==f;at+=20+n
                    for _ in range(records):
                        slot,rbits,rbytes,ralign=struct.unpack_from('<4I',raw,at);at+=16
                        direct=(C.c_uint8*(4<<20))();direct_size=C.c_uint32()
                        assert lib.catalog_record_original(f,slot,direct,C.byref(direct_size))==1
                        assert direct_size.value==rbytes and bytes(direct[:rbytes])==raw[at:at+rbytes]
                        at+=rbytes;compared+=1
                assert at==len(raw)
            for suffix,payload in [('catalog',raw),('wire',w)]:lines.append('static const unsigned char catalog_fixture_'+str(idx)+'_'+suffix+'[]={'+','.join(map(str,payload))+'};\n')
            rows.append('{catalog_fixture_%d_catalog,catalog_fixture_%d_wire,%d,%d,%d,%d,%d,%d,{%s}}'%(idx,idx,len(raw),len(w),bits.value,which,aligned,legacy,','.join(map(str,counts))))
            fixtures.append(dict(which=which,aligned=aligned,legacy=legacy,catalog_bytes=len(raw),catalog_sha256=hashlib.sha256(raw).hexdigest(),wire_bytes=len(w),wire_bits=bits.value,wire_sha256=hashlib.sha256(w).hexdigest(),source_counts=list(counts)))
    # Real producer output rejection/change controls produce partial, unaccepted
    # envelopes and prove callback errors are observable without packet sending.
    statuses=[]
    for mode in (1,2,3):
        buf=(C.c_uint8*(32<<20))();wire=(C.c_uint8*(1<<20))();size=C.c_uint32();bits=C.c_uint32();counts=(C.c_uint32*7)()
        status=lib.catalog_original(2,1,0,mode,buf,C.byref(size),wire,C.byref(bits),counts);assert status in (5,6)
        statuses.append(dict(mode=mode,status=status,partial_bytes=size.value))
    lib.catalog_source_negatives.argtypes=[C.c_void_p];source_negatives=lib.catalog_source_negatives((C.c_uint8*(1<<20))());assert source_negatives==7
    lines.append('static const CatalogFixture catalog_fixtures[]={'+',\n'.join(rows)+'};\n')
    header=d/'catalog_fixtures.h';header.write_text(''.join(lines))
    receipt.update(catalog_exporter_sha256=hashlib.sha256((HERE/'source_export.inc').read_bytes()).hexdigest(),catalog_harness_sha256=hashlib.sha256(extension.encode()).hexdigest(),catalog_fixtures=fixtures,exact_record_comparisons=compared,source_shape_negative_controls=source_negatives,exporter_negative_controls=statuses)
    return receipt,len(fixtures)

def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=REPO);p.add_argument('--output',type=Path);p.add_argument('--sanitize',action='store_true');p.add_argument('--ndk',type=Path);p.add_argument('--android-output',type=Path);p.add_argument('--fixtures-output',type=Path);p.add_argument('--prepare-only',action='store_true');a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='coh-catalog-') as temp:
        d=Path(temp);receipt,n=prepare(a.source_root.resolve(),d)
        fixture_sha=hashlib.sha256((d/'catalog_fixtures.h').read_bytes()).hexdigest()
        if a.fixtures_output:a.fixtures_output.mkdir(parents=True,exist_ok=True);shutil.copyfile(d/'catalog_fixtures.h',a.fixtures_output/'catalog_fixtures.h')
        if a.prepare_only:
            if not a.fixtures_output:p.error('--prepare-only requires --fixtures-output')
            return
        sources=[HERE/'coh_scenecatalog.c',HERE.parent/'scenegraph/coh_scenegraph.c',HERE.parent/'replication/coh_replication.c',HERE.parent/'replication/coh_groups.c',HERE/'tests/test_scenecatalog.c']
        hashed=[*sources,HERE/'coh_scenecatalog.h',HERE/'source_export.inc',HERE/'tests/source_catalog_harness.c',HERE/'tests/test_walk.c.inc',HERE/'check.py',HERE/'CMakeLists.txt',HERE.parent/'scenegraph/coh_scenegraph.h',HERE.parent/'replication/groups-source-pins.json']
        source_hashes={str(x.relative_to(REPO)):hashlib.sha256(x.read_bytes()).hexdigest() for x in hashed}
        flags=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(d),'-I'+str(HERE),'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free']
        modes=[('release',['-O2'])]
        if a.sanitize:modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
        checks={}
        for name,extra in modes:
            exe=d/name;run([os.environ.get('CC','cc'),*flags,*extra,*sources,'-lm','-o',exe])
            checks[name]=json.loads(run([exe],env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}).stdout)
        android=[]
        if a.ndk:
            if not a.android_output:p.error('--ndk requires --android-output')
            a.android_output.mkdir(parents=True,exist_ok=True);shutil.copyfile(d/'catalog_fixtures.h',a.android_output/'catalog_fixtures.h')
            for abi,triple in [('arm64-v8a','aarch64-linux-android26'),('x86_64','x86_64-linux-android26')]:
                out=a.android_output/abi;out.mkdir(parents=True,exist_ok=True);exe=out/'coh_scenecatalog_test';cc=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/str(triple+'-clang')
                run([cc,*flags,'-O2',*sources,'-lm','-o',exe])
                r=dict(passed=True,abi=abi,binary=exe.name,binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),fixtures_sha256=fixture_sha,source_sha256=source_hashes,execution_qualified=False)
                (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');android.append(r)
        result=dict(schema=1,passed=True,scope='original-source catalog envelopes; no deployed server catalog or live world',source_oracle=receipt,fixtures=n,fixtures_sha256=fixture_sha,source_sha256=source_hashes,checks=checks,android_builds=android,real_server_capture=False,real_imported_library_assets=False,renderer_authorized=False,thor_accepted=False,leak_sanitizer=False,allocation_tracking=True)
        if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
if __name__=='__main__':main()
