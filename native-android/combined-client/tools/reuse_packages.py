#!/usr/bin/env python3
"""Admit exact qualified APKs for a driver-only Android framework continuation."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import zipfile
from prepare import safe_zip, pin, verify

SOURCE = '5637133133a3654bb1a4f4b0fdb74ae575d05520'
ARTIFACT = '11987440686'
ARCHIVE_SHA = '77856abfca3df1975f1b4d13908246286de2116ac1b1bfc12bb578d26aa74729'
APKS = {
 'arm64-v8a': ('CoH-Native-Combined-0.1.0-arm64.apk', '4ae4ef25c6ea60bfdcac000f4ff9016ae202aa42e3414024a40c99dcf66b97ee'),
 'x86_64': ('CoH-Native-Combined-0.1.0-emulator-x86_64.apk', '09a6a6a8f43cb8e1f574bb407ea4682ac95c39ba716e6cb906212161b21ed482'),
}
ALLOWED = {
 'native-android/combined-client/tools/emulator_check.py',
 'native-android/combined-client/tools/driver_controls.py',
 'native-android/combined-client/tools/reuse_packages.py',
 '.github/workflows/native-combined-client.yml',
 '.github/workflows/native-combined-requalify.yml',
 'native-android/combined-client/README.md',
 'native-android/combined-client/THOR-TEST.md',
 'native-android/combined-client/QUALIFICATION.md',
 'native-android/README.md',
}


# The independent offline-support coordinator uses explicit source sets that the
# combined client neither compiles nor imports. Both CMake closures and the
# Gradle Java source allowlist remain byte-identical to the qualified APK source.
INDEPENDENT_PREFIXES = (
 'native-android/support-client/',
 'native-android/engine/appearance/', 'native-android/engine/audio/',
 'native-android/engine/perf/', 'native-android/engine/physics/',
 'native-android/engine/sequencer/', 'native-android/engine/ui/',
 'native-android/engine/support-batch/',
)
INDEPENDENT_WORKFLOW = '.github/workflows/native-support-client.yml'
CLOSURE_FILES = (
 'native-android/combined-client/app/build.gradle',
 'native-android/combined-client/app/src/main/cpp/CMakeLists.txt',
 'native-android/session-client/app/src/main/cpp/CMakeLists.txt',
)


def git(root, *args):
    return subprocess.run(['git','-C',str(root),*args],check=True,capture_output=True,text=True).stdout.strip()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[3])
    p.add_argument('--require-clean',action='store_true')
    a=p.parse_args()
    verify(a.archive,ARCHIVE_SHA)
    git(a.source_root,'merge-base','--is-ancestor',SOURCE,'HEAD')
    changed=git(a.source_root,'diff','--name-only','--no-renames',SOURCE,'HEAD').splitlines()
    independent=[v for v in changed if v.startswith(INDEPENDENT_PREFIXES) or v==INDEPENDENT_WORKFLOW]
    rejected=[v for v in changed if v not in ALLOWED and v not in independent and not v.startswith('native-android/combined-client/evidence/')]
    closure={v:hashlib.sha256(subprocess.run(['git','-C',str(a.source_root),'show',SOURCE+':'+v],check=True,capture_output=True).stdout).hexdigest() for v in CLOSURE_FILES}
    for v,digest in closure.items():
        if hashlib.sha256((a.source_root/v).read_bytes()).hexdigest()!=digest:raise ValueError('APK source closure changed: '+v)
    if rejected:raise ValueError('Qualified runtime/build inputs changed; require a new APK: '+repr(rejected))
    dirty=git(a.source_root,'status','--porcelain','--untracked-files=no')
    if a.require_clean and dirty:raise ValueError('Qualification driver source is modified')
    if a.output.exists():raise ValueError('Preserve existing qualification output; choose a fresh directory')
    a.output.mkdir(parents=True)
    with zipfile.ZipFile(a.archive) as z:
        safe_zip(z)
        total=0
        for i in z.infolist():
            if i.is_dir():continue
            total+=i.file_size
            if i.file_size>32<<20 or total>128<<20:raise ValueError('Qualified package artifact exceeds bounds')
            target=a.output/i.filename;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(i))
    receipts={}
    for abi,(name,digest) in APKS.items():
        apk=a.output/name;verify(apk,digest)
        receipt_name='arm64-package.json' if abi=='arm64-v8a' else 'x86_64-package.json'
        receipt=json.loads((a.output/receipt_name).read_text())
        if receipt['status']!='passed' or receipt['abi']!=abi or receipt['source_commit']!=SOURCE or receipt['tracked_source_clean'] is not True or receipt['apk']!=dict(name=name,**pin(apk.read_bytes())):
            raise ValueError('Qualified package receipt is not the exact successful source/binary')
        with zipfile.ZipFile(apk) as z:
            for path,value in receipt['native_libraries'].items():
                if pin(z.read(path))!=value:raise ValueError('Qualified native ELF changed')
        receipts[abi]={'apk':receipt['apk'],'build_receipt':receipt_name,'build_receipt_sha256':hashlib.sha256((a.output/receipt_name).read_bytes()).hexdigest()}
    value={'format':1,'status':'passed','qualified_apk_source':SOURCE,'qualified_workflow':'38763514350','artifact_id':ARTIFACT,'archive_sha256':ARCHIVE_SHA,'driver_source':git(a.source_root,'rev-parse','HEAD'),'driver_source_clean':not bool(dirty),'changed_paths_since_qualified_apk':changed,'independent_support_changes_preserved':independent,'unchanged_source_closure_sha256':closure,'source_closure_boundary':'Combined JNI and accepted renderer explicit CMake source/include lists plus explicit Gradle Java allowlist do not reference the independent support-client/appearance/audio/perf/physics/sequencer/ui/support-batch scopes. Runtime and other build inputs remain strictly rejected.','packages':receipts,'rebuilt':False,'actual_server_interoperability_verified':False,'scope':'Exact previously host-qualified ARM64/x86 APKs, native ELFs and Android UDP contract binary reused for a driver-only Android framework continuation. Runtime/build input changes are rejected.'}
    (a.output/'package-reuse-proof.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'status':'passed','rebuilt':False,'qualified_apk_source':SOURCE,'driver_source':value['driver_source']}))


if __name__=='__main__':main()
