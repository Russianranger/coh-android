#!/usr/bin/env python3
"""Original producer graph fixtures + bounded native ownership/negative checks."""
from pathlib import Path
import argparse, ctypes as C, hashlib, importlib.util, json, os, shutil, subprocess, tempfile, struct
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
def run(cmd,**kw):
    p=subprocess.run(cmd,text=True,capture_output=True,**kw)
    if p.returncode: raise RuntimeError(repr(cmd)+'\n'+p.stdout+p.stderr)
    return p

def prepare(source_root,directory):
    spec=importlib.util.spec_from_file_location('sg_original_groups',HERE.parent/'replication/groups_oracle.py')
    oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
    fixtures,receipt=oracle.produce_fixtures(source_root,directory)
    # Extend trusted input harness only; source producer function bodies/pins stay exact.
    src=directory/'groups-original.c'
    extra='''
int scenegraph_baseline(U32 aligned,U32 legacy,U8 *out,U32 *bits) {
 U32 footer[4];if(!groups_original(4,aligned,legacy,out,bits,footer))return 0;
 oracle_defs[1].in_use=1;oracle_refs[2].def=&oracle_defs[1];
 NetLink link={0};worldSendUpdate(&link,aligned?1:0);
 *bits=oracle_packet.stream.bitLength;memcpy(out,oracle_storage,(*bits+7)/8);return 1;
}
int scenegraph_long_property(U32 aligned,U32 legacy,U8 *out,U32 *bits) {
 U32 footer[4];static char long_value[1024];if(!groups_original(2,aligned,legacy,out,bits,footer))return 0;
 memset(long_value,'x',sizeof(long_value)-1);oracle_prop_entries[0][0].value_str=long_value;
 NetLink link={0};worldSendUpdate(&link,aligned?1:0);
 *bits=oracle_packet.stream.bitLength;memcpy(out,oracle_storage,(*bits+7)/8);return 1;
}
void scenegraph_source_roots(float *out) {memcpy(out,oracle_refs[0].mat,48);memcpy(out+12,oracle_refs[1].mat,48);memcpy(out+24,oracle_refs[2].mat,48);}
'''
    src.write_text(src.read_text()+extra)
    libpath=directory/'scenegraph-original.so'
    run(['cc','-std=c99','-O0','-fno-strict-aliasing','-fPIC','-shared','-w','-I'+str(source_root/'native-android/include'),str(src),'-lm','-lz','-o',str(libpath)])
    lib=C.CDLL(str(libpath));lib.scenegraph_baseline.argtypes=[C.c_uint32,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.scenegraph_long_property.argtypes=[C.c_uint32,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32)]
    lib.groups_original.argtypes=[C.c_uint32,C.c_uint32,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32),C.POINTER(C.c_uint32)]
    lib.scenegraph_source_roots.argtypes=[C.POINTER(C.c_float)]
    for aligned in (0,1):
        for legacy in (0,1):
            raw=(C.c_uint8*(1<<20))();bits=C.c_uint32()
            assert lib.scenegraph_baseline(aligned,legacy,raw,C.byref(bits))==1
            fixtures.append(dict(name='incremental_baseline',source_case=11,representation='byte_aligned' if aligned else 'packed',legacy_commands=legacy,payload_hex=bytes(raw[:(bits.value+7)//8]).hex(),payload_bits=bits.value))
    for aligned in (0,1):
        for legacy in (0,1):
            raw=(C.c_uint8*(1<<20))();bits=C.c_uint32()
            assert lib.scenegraph_long_property(aligned,legacy,raw,C.byref(bits))==1
            fixtures.append(dict(name='long_property',source_case=12,representation='byte_aligned' if aligned else 'packed',legacy_commands=legacy,payload_hex=bytes(raw[:(bits.value+7)//8]).hex(),payload_bits=bits.value))
    raw=(C.c_uint8*(1<<20))();bits=C.c_uint32();footer=(C.c_uint32*4)();mat=(C.c_float*36)()
    assert lib.groups_original(7,1,0,raw,C.byref(bits),footer)==1
    lib.scenegraph_source_roots(mat)
    lines=['typedef struct {const char *name;const unsigned char *data;size_t bytes,bits;unsigned aligned,legacy,which;} Fixture;\n']
    rows=[]
    for i,f in enumerate(fixtures):
        raw=bytes.fromhex(f['payload_hex']);name='sgfixture_'+str(i)
        lines.append('static const unsigned char '+name+'[]={'+','.join(map(str,raw))+'};\n')
        rows.append('{'+','.join([json.dumps(f['name']),name,str(len(raw)),str(f['payload_bits']),str(int(f['representation']=='byte_aligned')),str(f['legacy_commands']),str(f['source_case'])])+'}')
    lines.append('static const Fixture fixtures[]={'+',\n'.join(rows)+'};\n')
    lines.append('static const float source_matrices[3][4][3]={'+','.join('{'+','.join('{'+','.join(float(mat[k*12+i*3+j]).hex()+'f' for j in range(3))+'}' for i in range(4))+'}' for k in range(3))+'};\n')
    (directory/'scenegraph_fixtures.h').write_text(''.join(lines))
    # Reuse the exact catalog producer and independently invoke unchanged sendDef
    # for every stress record. Separate temporary scope is safe under parallel CI.
    catdir=directory/'catalog-source';catdir.mkdir()
    cspec=importlib.util.spec_from_file_location('graph_catalog_oracle',HERE.parent/'scenecatalog/check.py')
    catalog=importlib.util.module_from_spec(cspec);cspec.loader.exec_module(catalog)
    catreceipt,_=catalog.prepare(source_root,catdir)
    clib=C.CDLL(str(catdir/'catalog-original.so'))
    clib.catalog_original.argtypes=[C.c_uint32]*4+[C.c_void_p,C.POINTER(C.c_uint32),C.c_void_p,C.POINTER(C.c_uint32),C.c_void_p]
    clib.catalog_record_original.argtypes=[C.c_uint32,C.c_uint32,C.c_void_p,C.POINTER(C.c_uint32)]
    buf=(C.c_uint8*(32<<20))();wire=(C.c_uint8*(1<<20))();size=C.c_uint32();bits=C.c_uint32();counts=(C.c_uint32*7)()
    assert clib.catalog_original(20,1,0,0,buf,C.byref(size),wire,C.byref(bits),counts)==0
    raw=bytes(buf[:size.value]);w=bytes(wire[:(bits.value+7)//8]);at=48;compared=0
    direct=(C.c_uint8*(4<<20))();direct_size=C.c_uint32()
    for f in range(struct.unpack_from('<I',raw,24)[0]):
        index,checksum,slots,records,length=struct.unpack_from('<5I',raw,at);assert index==f;at+=20+length
        for _ in range(records):
            slot,rbits,rbytes,ralign=struct.unpack_from('<4I',raw,at);at+=16
            assert clib.catalog_record_original(f,slot,direct,C.byref(direct_size))==1
            assert direct_size.value==rbytes and bytes(direct[:rbytes])==raw[at:at+rbytes]
            at+=rbytes;compared+=1
    assert at==len(raw) and compared==12192
    with (directory/'scenegraph_fixtures.h').open('a') as f:
        for name,payload in [('stress_catalog',raw),('stress_wire',w)]:
            f.write('static const unsigned char '+name+'[]={'+','.join(map(str,payload))+'};\n')
        f.write('static const size_t stress_wire_bits='+str(bits.value)+';\n')
    receipt['stress_catalog']={'producer':catreceipt,'source_counts':list(counts),'catalog_sha256':hashlib.sha256(raw).hexdigest(),'wire_sha256':hashlib.sha256(w).hexdigest(),'independent_record_comparisons':compared,'real_server_capture':False}
    receipt['graph_extension_sha256']=hashlib.sha256(extra.encode()).hexdigest()
    receipt['graph_fixture_header_sha256']=hashlib.sha256((directory/'scenegraph_fixtures.h').read_bytes()).hexdigest()
    return receipt,len(fixtures)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=REPO);ap.add_argument('--output',type=Path);ap.add_argument('--sanitize',action='store_true');ap.add_argument('--ndk',type=Path);ap.add_argument('--android-output',type=Path);ap.add_argument('--fixtures-output',type=Path);ap.add_argument('--prepare-only',action='store_true');a=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='coh-sg-') as temp:
        d=Path(temp);receipt,n=prepare(a.source_root.resolve(),d)
        if a.fixtures_output:
            a.fixtures_output.mkdir(parents=True,exist_ok=True);shutil.copyfile(d/'scenegraph_fixtures.h',a.fixtures_output/'scenegraph_fixtures.h')
        if a.prepare_only:
            if not a.fixtures_output:ap.error('--prepare-only requires --fixtures-output')
            return
        sources=[HERE/'coh_scenegraph.c',HERE.parent/'scenecatalog/coh_scenecatalog.c',HERE.parent/'replication/coh_replication.c',HERE.parent/'replication/coh_groups.c',HERE/'tests/test_scenegraph.c']
        hashed_sources=[*sources,HERE/'coh_scenegraph.h',HERE/'check.py',HERE.parent/'replication/coh_replication.h',HERE.parent/'replication/coh_groups.h',HERE.parent/'replication/groups-source-pins.json',HERE.parent/'scenecatalog/coh_scenecatalog.h',HERE.parent/'scenecatalog/check.py',HERE.parent/'scenecatalog/source_export.inc',HERE.parent/'scenecatalog/tests/source_catalog_harness.c']
        source_hashes={str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in hashed_sources}
        fixture_sha=hashlib.sha256((d/'scenegraph_fixtures.h').read_bytes()).hexdigest()
        flags=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(d),'-I'+str(HERE),'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free']
        modes=[('release',['-O2'])]
        if a.sanitize:modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
        checks={}
        for name,extra in modes:
            binary=d/name;run([os.environ.get('CC','cc'),*flags,*extra,*map(str,sources),'-lm','-o',str(binary)])
            env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}
            checks[name]=json.loads(run([str(binary)],env=env).stdout)
        android=[]
        if a.ndk:
            if not a.android_output:ap.error('--ndk requires --android-output')
            a.android_output.mkdir(parents=True,exist_ok=True);shutil.copyfile(d/'scenegraph_fixtures.h',a.android_output/'scenegraph_fixtures.h')
            for abi,triple in [('arm64-v8a','aarch64-linux-android26'),('x86_64','x86_64-linux-android26')]:
                out=a.android_output/abi;out.mkdir(parents=True,exist_ok=True);binary=out/'coh_scenegraph_test'
                cc=a.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/str(triple+'-clang')
                run([str(cc),*flags,'-O2',*map(str,sources),'-lm','-o',str(binary)])
                r={'passed':True,'abi':abi,'binary':binary.name,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'execution_qualified':False,'fixtures_sha256':fixture_sha,'source_sha256':source_hashes}
                (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');android.append(r)
        result={'schema':1,'passed':True,'scope':'dynamic indexed GROUPS topology; source-produced synthetic 508-file catalog imported with aggregate ownership admission, not live server world','source_oracle':receipt,'fixtures':n,'fixtures_sha256':fixture_sha,'source_sha256':source_hashes,'checks':checks,'android_builds':android,'leak_sanitizer':False,'leak_sanitizer_reason':'host ptrace environment denies /proc thread enumeration; every module allocation is independently wrapped/counted and failures injected','catalog_import_adapter_tested':True,'real_import_adapter':False,'renderer_authorized':False,'real_server_capture':False,'thor_accepted':False}
        if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
if __name__=='__main__':main()
