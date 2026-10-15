#!/usr/bin/env python3
"""Recover only three exact accepted identifier attributes required by the client."""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import zipfile
import package_client_runtime as client

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = 'client-prerequisites.zip'
MANIFEST = 'client-prerequisites-manifest.json'
ROLE = 'actual_client_prerequisites'
DONOR = ROOT/'docs/reference-runtime-evidence/reference-template-comparison-36176806895.zip'
DONOR_PIN = {'bytes':1513061,'sha256':'2746438d739a2f13c5d3d15fb96ff6e717de471b635ebdb5fd2100842e46d7c5'}
INNER_PIN = {'bytes':682745,'sha256':'30014f78a60fb3a7d4fd9ca6d285d8a2dc3cb82ad361f2988efc252b2fb68d3d'}
REPORT_SHA256 = '5425672253f7e6f9de4751500115052ac9ca1f0d2fe78471ddeec93add47eb4b'
FILES = {
    'data/server/db/templates/badges.attribute':{'bytes':51724,'sha256':'789ed244ac7c686cc275a8a2914de95bbb044b00483875df950a713f05b66fea'},
    'data/server/db/templates/pophelp.attribute':{'bytes':2185,'sha256':'34195086d3223c717dca5e1cd00bc35a947a05d5fe31b2408a863e85aea617a1'},
    'data/server/db/templates/supergroup_badges.attribute':{'bytes':1039,'sha256':'d63b3c490fc23086aa6af4fd9add6c2af0892452011d32d6984cac2198d65a7e'},
}
require = client.require


def pin(data):
    return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def contract():
    return {'format':1,'role':ROLE,'source_commit':client.SOURCE,'data_commit':client.DATA,
            'reference_run_id':client.REFERENCE_RUN,'schema_run_id':36088012666,
            'ordinary_comparison_run_id':36176806895,'ordinary_comparison_archive':DONOR_PIN,
            'ordinary_comparison_report_sha256':REPORT_SHA256,'schema_outputs_archive':INNER_PIN,
            'files':FILES,'server_execution_required':False}


def manifest_sha256():
    return hashlib.sha256(client.canonical(contract())).hexdigest()


def accepted_payloads():
    raw=DONOR.read_bytes();require(pin(raw)==DONOR_PIN,'Accepted prerequisite donor differs')
    report_data=DONOR.with_suffix('.json').read_bytes()
    require(hashlib.sha256(report_data).hexdigest()==REPORT_SHA256,'Accepted prerequisite comparison receipt differs')
    report=json.loads(report_data)
    require(report.get('status')=='reference_template_comparison_passed_gameplay_unvalidated'
            and report.get('source_commit')==client.SOURCE and report.get('data_commit')==client.DATA
            and all(report['seeded_identifier_sha256'].get(name)==record['sha256'] for name,record in FILES.items()),
            'Prerequisite comparison identity differs')
    with zipfile.ZipFile(io.BytesIO(raw)) as outer:
        data=outer.read('schema-outputs.zip');require(pin(data)==INNER_PIN,'Accepted prerequisite inner archive differs')
    with zipfile.ZipFile(io.BytesIO(data)) as inner:
        result={name:inner.read(name) for name in FILES}
    require(all(pin(data)==FILES[name] for name,data in result.items()),'Accepted prerequisite payload differs')
    return result


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist()
        require(len(names)==4 and len(set(names))==4 and set(names)==set(FILES)|{MANIFEST},
                'Client prerequisite inventory differs')
        require(archive.getinfo(MANIFEST).file_size<=16384,'Oversized prerequisite manifest')
        require(json.loads(archive.read(MANIFEST))==contract(),'Client prerequisite provenance differs')
        for name,expected in FILES.items():
            entry=archive.getinfo(name);mode=entry.external_attr>>16
            require(not entry.is_dir() and not entry.flag_bits&1 and (mode&0o170000) in (0,0o100000)
                    and entry.file_size==expected['bytes'],'Unsafe prerequisite entry')
            require(pin(archive.read(entry))==expected,'Client prerequisite hash differs')
    return contract()


def prepare(path):
    payloads=accepted_payloads()
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,data in sorted({**payloads,MANIFEST:client.canonical(contract())}.items()):
            info=zipfile.ZipInfo(name,(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;archive.writestr(info,data)
    return verify_archive(path)


def install(runtime):
    """Install before the generator takes its source snapshot and normalizes dates."""
    for name,data in accepted_payloads().items():
        target=Path(runtime)/name
        require(not target.exists() and not target.is_symlink(),'Client prerequisite input collision')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    return contract()
