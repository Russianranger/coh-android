#!/usr/bin/env python3
"""Compact topology ownership qualification; authentic input remains a refusal."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys, tempfile
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
def run(args,**kw):
    result=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kw)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout
def missing_audit(output):
    # Host report only. This indexes names from the fully validating walker;
    # it never changes a production edge or admits a compact graph.
    files={};definitions={};names={};children=[];report=None
    for line in output.splitlines():
        row=line.split('\t')
        if row[0]=='F' and len(row)==3:
            index=int(row[1])
            if index in files:raise ValueError('Duplicate diagnostic file')
            files[index]=row[2]
        elif row[0]=='D' and len(row)==4:
            key=(int(row[1]),int(row[2]));name=row[3]
            if key in definitions or name.lower() in names:raise ValueError('Duplicate diagnostic definition')
            definitions[key]=name;names[name.lower()]=key
        elif row[0]=='C' and len(row)==5:children.append((int(row[1]),int(row[2]),int(row[3]),row[4]))
        elif row[0]=='R' and len(row)==6 and report is None:report=list(map(int,row[1:]))
        else:raise ValueError('Unexpected diagnostic record')
    if report is None or report[0]!=len(files) or report[3]!=len(children):raise ValueError('Incomplete diagnostic walk')
    missing=[]
    for file,slot,child,name in children:
        if (file,slot) not in definitions:raise ValueError('Missing diagnostic owner')
        if name.rsplit('/',1)[-1].lower() not in names:
            missing.append({'file':file,'file_name':files[file],'slot':slot,'definition':definitions[(file,slot)],'child':child,'name':name})
    return {'scope':'complete saved-record name closure only; no roots/reachability/geometry claim','files':report[0],'slots':report[1],'records_validated':report[2],'children_inspected':report[3],'peak_record_owned_bytes':report[4],'missing':missing,'missing_references':len(missing),'missing_unique_names':len({row['name'].lower() for row in missing}),'graph_published':False,'raw_walker_output_sha256':hashlib.sha256(output.encode()).hexdigest()}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-root',type=Path,default=ROOT);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--sanitize',action='store_true');parser.add_argument('--capture-directory',type=Path);parser.add_argument('--ndk',type=Path);parser.add_argument('--android-output',type=Path);parser.add_argument('--fixtures-output',type=Path);args=parser.parse_args()
    if args.ndk and not args.android_output:parser.error('--ndk requires --android-output')
    if args.android_output and not args.ndk:parser.error('--android-output requires --ndk')
    catalog=module('compact_catalog_oracle',HERE.parent/'scenecatalog/check.py')
    captured=None
    if args.capture_directory:
        sys.path.insert(0,str(HERE.parent/'scenecatalog'))
        capture=module('compact_capture_admission',HERE.parent/'scenecatalog/check_file.py')
        captured=capture.admit_capture(args.capture_directory)
    sources=[HERE/'coh_scene_compact.c',HERE/'tests/test_scene_compact.c',HERE/'coh_scenegraph.c',HERE.parent/'scenecatalog/coh_scenecatalog.c',HERE.parent/'replication/coh_replication.c',HERE.parent/'replication/coh_groups.c']
    included=[*sources,HERE/'coh_scene_compact.h',HERE/'coh_scenegraph.h',HERE/'check_compact.py',HERE.parent/'scenecatalog/coh_scenecatalog.h',HERE.parent/'scenecatalog/check.py',HERE.parent/'scenecatalog/source_export.inc',HERE.parent/'scenecatalog/tests/source_catalog_harness.c',HERE.parent/'replication/coh_replication.h',HERE.parent/'replication/coh_groups.h',HERE.parent/'replication/groups_oracle.py',HERE.parent/'replication/groups-source-pins.json',HERE.parent/'coh_contracts.h']
    if captured:included += [HERE.parent/'scenecatalog/check_file.py',capture.CAPTURE_MANIFEST,HERE/'tests/compact_missing_audit.c']
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in included}
    with tempfile.TemporaryDirectory(prefix='coh-compact-') as temporary:
        work=Path(temporary);oracle,count=catalog.prepare(args.source_root.resolve(),work)
        fixture_sha=hashlib.sha256((work/'catalog_fixtures.h').read_bytes()).hexdigest()
        if args.fixtures_output:
            args.fixtures_output.mkdir(parents=True,exist_ok=True);shutil.copyfile(work/'catalog_fixtures.h',args.fixtures_output/'catalog_fixtures.h')
        modes=[('release',['-O2'])]
        if args.sanitize:modes += [('asan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fno-omit-frame-pointer','-fsanitize=undefined','-fno-sanitize-recover=all'])]
        checks={}
        for name,extra in modes:
            binary=work/name
            run([os.environ.get('CC','cc'),'-std=c99','-Wall','-Wextra','-Werror','-pedantic','-DCOH_COMPACT_STANDALONE','-I'+str(work),'-I'+str(HERE),*extra,*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lm','-o',binary])
            checks[name]=json.loads(run([binary,*([captured[0]] if captured else [])],env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1'}))
        if any(value!=checks['release'] for value in checks.values()):raise ValueError('Qualification modes disagree')
        audit=None
        if captured:
            binary=work/'missing-audit'
            run([os.environ.get('CC','cc'),'-std=c99','-O2','-Wall','-Wextra','-Werror','-pedantic',HERE/'tests/compact_missing_audit.c',*sources[2:],'-lm','-o',binary])
            audit=missing_audit(run([binary,captured[0]]))
        android=[]
        if args.ndk:
            args.android_output.mkdir(parents=True,exist_ok=True);shutil.copyfile(work/'catalog_fixtures.h',args.android_output/'catalog_fixtures.h')
            for abi,triple in [('arm64-v8a','aarch64-linux-android26'),('x86_64','x86_64-linux-android26')]:
                destination=args.android_output/abi;destination.mkdir(parents=True,exist_ok=True);binary=destination/'coh_scene_compact_test'
                cc=args.ndk/'toolchains/llvm/prebuilt/linux-x86_64/bin'/str(triple+'-clang')
                run([cc,'-std=c99','-O2','-Wall','-Wextra','-Werror','-pedantic','-DCOH_COMPACT_STANDALONE','-I'+str(work),'-I'+str(HERE),*sources,'-Wl,--wrap=malloc,--wrap=calloc,--wrap=free','-lm','-o',binary])
                receipt={'passed':True,'abi':abi,'binary':binary.name,'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'execution_qualified':False,'fixtures_sha256':fixture_sha,'source_sha256':hashes}
                (destination/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');android.append(receipt)
        if hashes!={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in included}:raise ValueError('Source changed during qualification')
        if captured and capture.admit_capture(args.capture_directory)!=captured:raise ValueError('Capture changed during qualification')
        result={'schema':1,'passed':True,'scope':'two-pass compact saved catalog topology on original-source fixtures; authentic captured catalog deliberately refuses unresolved child references','source_oracle':oracle,'fixtures':count,'fixtures_sha256':fixture_sha,'checks':checks,'source_sha256':hashes,'android_builds':android,'authentic_capture_refusal_tested':bool(captured),'graph_published_from_authentic_capture':False,'roots_bound':False,'assets_bound':False,'renderer_authorized':False,'android_executed':False,'physical_thor_accepted':False,'leak_sanitizer':False,'leak_sanitizer_reason':'allocation wrappers verify zero live allocations and inject failure throughout both original-record decoding passes'}
        if captured:result['capture_provenance']=captured[1];result['captured_name_closure']=audit
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
