#!/usr/bin/env python3
"""Recover the one completed nonshipping Map candidate without rebuilding it."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import stat
import zipfile
import package_native_map_prefetch as candidate
import package_native_startup_profile as base
from map_startup_namespace_certificate import require

SOURCE='47e40d4d586d29e273e31ed4d0d51d160832b89d'
RUN=38350813669
JOB=115142552789
ARTIFACT=11790609618
ZIP={'bytes':3307410,'sha256':'69bfc9f44e5304eae786d0668ba30f183f5b99a58586f8db7861f697d8e23aab'}
FILES={
 'native-map-prefetch-checks.json':{'bytes':5053,'sha256':'56555e6e89b1adbae2ec24d02d3b1511b93e71ede45af361afc446b147547c02'},
 'native-map-prefetch-package.json':{'bytes':12283,'sha256':'877207e8889a4e5c97e39aa8fb87f113592f062eb74b89d7a41a82faf1e6cafe'},
 'native-map-prefetch-fixture.exe':{'bytes':152576,'sha256':'ac723e27bafd46e1c21ecaf62556079d32a84d5745058c9d4e380c57d9393a5d'},
 'MapServer-prefetch.exe':{'bytes':7480832,'sha256':'5927f87fdac50c5a839ac067ccbb34b5dfad6223e579287a66a2f866a7d4b2e6'}}


def provenance():
    return {'source_commit':SOURCE,'run_id':RUN,'job_id':JOB,'artifact_id':ARTIFACT,'artifact_zip':ZIP,
        'actual_native_build_and_Win32_fixture_passed':True,'native_binaries_rebuilt':False,
        'native_world_or_Wine_preload_claimed':False,'publication_allowed':False}


def validate_metadata(run,jobs,artifact):
    require(all(type(value) is int for value in (run.get('id'),artifact.get('id'),
        artifact.get('size_in_bytes'),artifact.get('workflow_run',{}).get('id'))),
        'Exact integer native producer metadata required')
    require(run.get('id')==RUN and run.get('head_sha')==SOURCE and run.get('status')=='completed'
        and run.get('conclusion')=='success' and run.get('head_branch')=='codex/native-map-prefetch-036'
        and run.get('path')=='.github/workflows/android-native-map-prefetch.yml','Exact successful candidate producer run required')
    found=[j for j in jobs.get('jobs',[]) if j.get('id')==JOB]
    require(len(found)==1 and type(found[0].get('id')) is int and type(found[0].get('run_id')) is int
        and found[0].get('run_id')==RUN and found[0].get('name')=='native-candidate'
        and found[0].get('status')=='completed' and found[0].get('conclusion')=='success',
        'Exact successful native candidate producer job required')
    require(artifact.get('id')==ARTIFACT and artifact.get('name')=='coh-nonshipping-map-metadata-prefetch'
        and artifact.get('size_in_bytes')==ZIP['bytes'] and artifact.get('digest')=='sha256:'+ZIP['sha256']
        and artifact.get('expired') is False and artifact.get('workflow_run',{}).get('id')==RUN
        and artifact['workflow_run'].get('head_sha')==SOURCE,'Exact candidate artifact metadata required')
    return provenance()


def validate_package(directory,baseline):
    directory=Path(directory).absolute()
    require(not any(p.is_symlink() for p in (directory,*directory.parents)),
        'Linked candidate artifact directory/ancestor refused')
    require(directory.is_dir() and not directory.is_symlink()
        and {p.name for p in directory.iterdir()}==set(FILES),'Exact candidate artifact member closure required')
    for name,pin in FILES.items():require(base.pin(directory/name)==pin,'Candidate retained member bytes differ: '+name)
    return candidate.validate(directory,SOURCE,baseline)


def extract(archive,output,baseline):
    archive=Path(archive).absolute();output=Path(output).absolute()
    require(not any(p.is_symlink() for p in (archive,*archive.parents,output,*output.parents)),
        'Linked candidate recovery input/output ancestor refused')
    require(base.pin(archive)==ZIP,'Exact completed candidate ZIP required')
    require(not output.exists() and not output.is_symlink(),'Fresh retained candidate directory required')
    with zipfile.ZipFile(archive) as z:
        members=z.infolist()
        require(len(members)==len(FILES) and {m.filename for m in members}==set(FILES),
            'Candidate ZIP member closure differs')
        for member in members:
            require(not member.is_dir() and member.file_size==FILES[member.filename]['bytes']
                and stat.S_IFMT(member.external_attr>>16) in (0,stat.S_IFREG)
                and not member.flag_bits&1,'Candidate ZIP linked/encrypted/member size differs')
        output.mkdir(parents=True)
        for member in members:
            data=z.read(member);(output/member.filename).write_bytes(data)
    return validate_package(output,baseline)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('archive','output','baseline','run-metadata','jobs-metadata','artifact-metadata'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();proof=validate_metadata(base.read(a.run_metadata),base.read(a.jobs_metadata),base.read(a.artifact_metadata))
    extract(a.archive,a.output,a.baseline);print(json.dumps(proof,sort_keys=True))
