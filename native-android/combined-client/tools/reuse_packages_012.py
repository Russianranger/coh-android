#!/usr/bin/env python3
"""Admit exact 0.1.2 build/host-qualified APKs for framework continuation."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import zipfile
from prepare import safe_zip, pin, verify

SOURCE = '377584651471e748fbbd4a24cdf08bd2c48ca4a3'
ARTIFACT = '12002281757'
ARCHIVE_SHA = '37f0a10a879ae94242a801153d6456dd33cf88e565408b22935548f3612dd43f'
APKS = {
 'arm64-v8a': ('CoH-Native-Combined-0.1.2-arm64.apk', '1913613656032400ee7ba70a46d56242567d23040b896032ad8a9bc90e9ae449'),
 'x86_64': ('CoH-Native-Combined-0.1.2-emulator-x86_64.apk', '01ddd409b320b7edee72c187324c0d5094ab2a80e83ad552b71a22fe44273824'),
}
ALLOWED = {
 'native-android/combined-client/tools/emulator_check.py',
 'native-android/combined-client/tools/driver_controls.py',
 'native-android/combined-client/tools/reuse_packages_012.py',
 '.github/workflows/native-combined-client.yml',
 '.github/workflows/native-combined-requalify.yml',
 'native-android/combined-client/README.md',
 'native-android/combined-client/THOR-TEST.md',
 'native-android/combined-client/QUALIFICATION.md',
 'native-android/README.md',
}


# This continuation accepts only driver, documentation and evidence changes.
INDEPENDENT_PREFIXES = ()
INDEPENDENT_WORKFLOW = ''
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
    value={'format':1,'status':'passed','qualified_apk_source':SOURCE,'qualified_workflow':'38795244645','artifact_id':ARTIFACT,'archive_sha256':ARCHIVE_SHA,'driver_source':git(a.source_root,'rev-parse','HEAD'),'driver_source_clean':not bool(dirty),'changed_paths_since_qualified_apk':changed,'independent_support_changes_preserved':independent,'unchanged_source_closure_sha256':closure,'source_closure_boundary':'All runtime, engine and build inputs remain unchanged from the pinned 0.1.2 source; only explicit framework-driver, documentation and evidence paths are accepted.','packages':receipts,'rebuilt':False,'actual_server_interoperability_verified':False,'scope':'Exact previously host-qualified ARM64/x86 APKs, native ELFs and Android UDP contract binary reused for a driver-only Android framework continuation. Runtime/build input changes are rejected.'}
    (a.output/'package-reuse-proof.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({'status':'passed','rebuilt':False,'qualified_apk_source':SOURCE,'driver_source':value['driver_source']}))


if __name__=='__main__':main()
