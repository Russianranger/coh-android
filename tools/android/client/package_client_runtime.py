#!/usr/bin/env python3
"""Package only the exact qualified graphical client and its dynamic DLL closure."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tools/android/game'))
from package_game_runtime import verified_donor, SOURCE, DATA
from package_reference_runtime import file_record, dependency_report, require
REFERENCE_RUN = 36088012664
MANIFEST = 'client-package.json'
ARCHIVE = 'client-runtime.zip'
ROLE = 'actual_graphical_client'


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()


def selected_files(receipt):
    return {name: record for name, record in receipt['files'].items()
            if name == 'CityOfHeroes.exe' or name.lower().endswith('.dll')}


def accepted():
    return json.loads((ROOT/'docs/reference-runtime-evidence/build-36088012664.json').read_text())


def package_contract(repository_commit):
    require(isinstance(repository_commit,str) and re.fullmatch('[0-9a-f]{40}',repository_commit),'Exact candidate commit required')
    donor = accepted(); records = selected_files(donor); deps = dependency_report(records)
    require(len(records)==21 and not deps['unresolved'],'Client dependency closure differs')
    return {'format':1,'role':ROLE,'source_commit':SOURCE,'data_commit':DATA,
            'repository_commit':repository_commit,'reference_run_id':REFERENCE_RUN,
            'reference_repository_commit':donor['repository_commit'],
            'reference_receipt_sha256':hashlib.sha256((ROOT/'docs/reference-runtime-evidence/build-36088012664.json').read_bytes()).hexdigest(),
            'files':records,'dependency_report':deps,'server_executables_included':False,
            'android_execution_validated':False,'gameplay_validated':False}


def verify_archive(path, repository_commit=None):
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist()
        require(len(names)==len(set(names)) and len(names)==22,'Wrong client archive member count')
        require(MANIFEST in names and archive.getinfo(MANIFEST).file_size<=256*1024,'Client manifest missing or oversized')
        document=json.loads(archive.read(MANIFEST))
        commit=repository_commit or document.get('repository_commit')
        require(document==package_contract(commit),'Client package provenance differs')
        require(set(names)==set(document['files'])|{MANIFEST},'Client archive payload set differs')
        for name,expected in document['files'].items():
            info=archive.getinfo(name)
            require('/' not in name and '\\' not in name and not info.is_dir() and not info.flag_bits&1,
                    'Unsafe client archive member')
            require(info.file_size==expected['size'],'Client file size differs: '+name)
            data=archive.read(info)
            require(hashlib.sha256(data).hexdigest()==expected['sha256'],'Client hash differs: '+name)
    return document


def package(reference, output, repository_commit):
    reference,output=Path(reference),Path(output)
    require(not output.exists() and not output.is_symlink(),'Fresh client output required')
    verified_donor(reference,'reference')
    document=package_contract(repository_commit)
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.client-package-',dir=output.parent) as temp:
        archive_path=Path(temp)/ARCHIVE
        with zipfile.ZipFile(archive_path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name in sorted(document['files']):
                require(file_record(reference/name)==document['files'][name],'Client donor changed')
                info=zipfile.ZipInfo(name,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0o100644<<16
                archive.writestr(info,(reference/name).read_bytes())
            info=zipfile.ZipInfo(MANIFEST,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;archive.writestr(info,canonical(document))
        verify_archive(archive_path,repository_commit)
        output.mkdir();shutil.copyfile(archive_path,output/ARCHIVE)
        (output/MANIFEST).write_bytes(canonical(document))
    return document


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--repository-commit',required=True);args=p.parse_args()
    value=package(**vars(args));print(json.dumps({'files':len(value['files']),'role':ROLE}))

if __name__=='__main__':main()
