#!/usr/bin/env python3
"""Package only the new station-aware MapServer; retain every other native byte."""
import argparse
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tarfile
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'android/guest')]
import prepare_monorail_source as source
import native_monorail_contract as contract
from package_reference_runtime import file_record,dependency_report
from package_responsiveness_native import schema_pins,read_json
require=contract.require
MANIFEST='native-monorail-build.json'
SOURCE_FILES=('tools/prepare_monorail_source.py',source.PATCH,
              *(source.OVERLAY+'/'+n for n in source.OVERLAY_FILES),
              'tools/android/interactive/package_monorail_native.py','android/guest/native_monorail_contract.py')


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def package(args):
    require(re.fullmatch('[0-9a-f]{40}',args.repository_commit),'Exact native build source required')
    require(not args.output.exists(),'Fresh native package directory required')
    build=read_json(args.source/source.RECEIPT)
    require(build==source.expected_receipt(events_build_input=build['events_build_input']),'Monorail build source differs')
    require(re.findall(r'^COH_PG_PERSISTENCE_TESTS:BOOL=(.*)$',args.cache.read_text(encoding='utf-8-sig'),re.M)==['OFF'],
            'Shipping native build must disable persistence fixtures')
    require({n:source.sha256(args.source/n) for n in source.COLLISION_FILES}==build['retained_collision_sources'],
            'Shipping MapServer collision algorithms changed')
    record=file_record(args.directory/'MapServer.exe');contract.retained.pe_record(record)
    value={'format':1,'role':'native_monorail','repository_commit':args.repository_commit,
        'source_commit':contract.retained.SOURCE,'data_commit':contract.retained.DATA,
        'configuration':'OptDebug','architecture':'Win32','postgresql_persistence_fixture':False,
        'runtime_execution_validated':False,'build_targets':['MapServer'],'build_input':build,
        'schema_sources_sha256':schema_pins(args.source),'cmake_cache_sha256':file_record(args.cache)['sha256'],
        'files':{'MapServer.exe':record},'symbols':{'MapServer.pdb':file_record(args.directory/'MapServer.pdb')},
        'run_url':args.run_url,'source_files':{n:file_record(ROOT/n) for n in SOURCE_FILES}}
    args.output.mkdir(parents=True);shutil.copyfile(args.directory/'MapServer.exe',args.output/'MapServer.exe')
    (args.output/MANIFEST).write_bytes(canonical(value))
    validate_package(args.output,args.repository_commit)
    return value


def validate_package(directory,commit):
    directory=Path(directory);value=read_json(directory/MANIFEST)
    require(set(p.name for p in directory.iterdir())=={'MapServer.exe',MANIFEST},'Unexpected native monorail package member')
    require(value.get('format')==1 and value.get('role')=='native_monorail' and value.get('repository_commit')==commit
        and value.get('source_commit')==contract.retained.SOURCE and value.get('data_commit')==contract.retained.DATA
        and value.get('configuration')=='OptDebug' and value.get('architecture')=='Win32'
        and value.get('postgresql_persistence_fixture') is False and value.get('runtime_execution_validated') is False
        and value.get('build_targets')==['MapServer'] and set(value.get('files',{}))=={'MapServer.exe'}
        and value.get('schema_sources_sha256')==schema_pins()
        and re.fullmatch('[0-9a-f]{64}',str(value.get('cmake_cache_sha256','')))
        and re.fullmatch(r'https://github\.com/Russianranger/coh-android/actions/runs/[1-9][0-9]+',str(value.get('run_url',''))),
        'Native monorail source/build identity differs')
    build=value.get('build_input',{})
    require(build==source.expected_receipt(events_build_input=build.get('events_build_input')),'Native monorail overlay receipt differs')
    require(value.get('source_files')=={n:file_record(ROOT/n) for n in SOURCE_FILES},'Native source files changed since compile')
    require(file_record(directory/'MapServer.exe')==value['files']['MapServer.exe'],'Native MapServer bytes/imports differ')
    contract.retained.pe_record(value['files']['MapServer.exe'])
    return value


def write_game_archive(path,files):
    # Fixed tar metadata and no gzip filename/time make audit reconstruction exact.
    with Path(path).open('wb') as destination,gzip.GzipFile(filename='',mode='wb',fileobj=destination,mtime=0) as compressed:
        with tarfile.open(fileobj=compressed,mode='w') as archive:
            for name,raw in sorted(files.items()):
                member=tarfile.TarInfo(name);member.size=len(raw);member.mtime=0
                member.mode=0o644;member.uid=member.gid=0;member.uname=member.gname=''
                archive.addfile(member,io.BytesIO(raw))


def patch_game(assets,native_directory,commit,native_commit=None):
    assets,native_directory=Path(assets),Path(native_directory)
    build=validate_package(native_directory,native_commit or commit)
    with tarfile.open(assets/'game-package.tar.gz','r:gz') as archive:
        entries=archive.getmembers()
        require(all(e.isfile() and '/' not in e.name and '\\' not in e.name for e in entries)
            and len({e.name.casefold() for e in entries})==len(entries),'Unexpected retained game archive member')
        files={e.name:archive.extractfile(e).read() for e in entries}
    game=json.loads(files['game-package.json'])
    contract.retained.events_progress_contract(game)
    require(set(files)==set(game['files'])|{'game-package.json'},'Retained game archive closure differs')
    for name,row in game['files'].items():
        require(len(files[name])==row.get('bytes',row.get('size')) and hashlib.sha256(files[name]).hexdigest()==row['sha256'],
            'Retained game payload differs: '+name)
    previous=copy.deepcopy(game['files']['MapServer.exe'])
    row=copy.deepcopy(build['files']['MapServer.exe']);row['bytes']=row.pop('size')
    receipt={'format':1,'role':'native_monorail','repository_commit':commit,
        'source_commit':game['source_commit'],'data_commit':game['data_commit'],'build_input':build['build_input'],
        'schema_sources_sha256':build['schema_sources_sha256'],
        'mapserver':row,'previous_mapserver':previous,
        'retained_native_files':{n:r for n,r in game['files'].items() if n!='MapServer.exe'},
        'native_build_repository_commit':build['repository_commit'],
        'native_build_manifest':{'bytes':(native_directory/MANIFEST).stat().st_size,
                                 'sha256':hashlib.sha256((native_directory/MANIFEST).read_bytes()).hexdigest()}}
    game['native_monorail']={'receipt':receipt,'receipt_sha256':contract.canonical_sha(receipt)}
    game['files']['MapServer.exe']=row
    game['dependency_report']=dependency_report(game['files'])
    require(not game['dependency_report']['unresolved'],'New MapServer imports exceed retained DLL closure')
    contract.embedded_receipt(game)
    files['MapServer.exe']=(native_directory/'MapServer.exe').read_bytes();files['game-package.json']=canonical(game)
    write_game_archive(assets/'game-package.tar.gz',files)
    return receipt,game


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('directory','source','cache','output'):parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--repository-commit',required=True);parser.add_argument('--run-url',required=True)
    value=package(parser.parse_args());print(json.dumps({'status':'packaged','MapServer.exe':value['files']['MapServer.exe']}))
