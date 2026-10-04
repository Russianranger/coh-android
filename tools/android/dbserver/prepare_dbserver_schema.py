#!/usr/bin/env python3
"""Stage the accepted minimal fixture-OFF DbServer schema inputs, without game assets.

Generated payloads retain their exact accepted bytes. Six immutable supplemental
text files are validated with LF-normalized pins and staged with LF endings so
Windows Git checkout conversion cannot change the package's identity. No binary,
live database, generated cache or private connection configuration is included.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'database/postgresql/tests'))
from run_generated_schema import (OPTIONAL, SUPPLEMENTAL, archive_payloads,
                                  attribute_rows, schema_contract, template_columns)
from prepare_schema_source import expected_schema_receipt
from run_schema_generation import SUCCESS
import generate_runtime_data as generation

ACCEPTANCE_RUN = 36088012666
RECEIPT = 'docs/schema-generation-evidence/accepted-36088012666.json'
ARTIFACT_SHA256 = '62da453ef5673238e11b4b418692117ea7692597a079119b3aaf72504a2502ae'
ARTIFACT_BYTES = 665051
REPORT_MEMBER = 'schema-evidence/schema-generation-report.json'
ARCHIVE_MEMBER = 'schema-evidence/schema-outputs.zip'
MAX_ARTIFACT_EXPANDED = 16 * 1024 * 1024
# LF-normalized versions of the files in the immutable source/data manifests.
SUPPLEMENTAL_PINS = {
    'data/server/db/servers.cfg': '539933dabd369fe57fde2c833f44317105faa77df4a7ff04ada32dfea3c8851d',
    'data/server/db/loadBalanceDefault.cfg': 'cf6274ced5409bd9316e3f90456610753f0de37da01c0b68dc63cf7d24baf76b',
    'data/server/db/loadBalanceShardSpecific.cfg': 'ce46881bc60c94f6e35854f68cea078a726f8b549ba3a6f63980b95aabe6a63c',
    'data/server/db/maps.db': '8aaa5085acfc86eae7b6a395da6c8ac4348eba503b71e845fdbeeb4725c53cf7',
    'data/defs/account/loyaltyrewardtree.def': '8b7c96accd8448a235dfa744ff775a3df40bc9e7968b8c192ff53a5de7065d43',
    'data/defs/account/product_catalog.def': '5e5375b3aa430b88fbcdada0ac87629fa35d5826ab817d9a9abd65baa677f300',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def plain_file(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), 'Missing or linked input: ' + str(path))
    return path.read_bytes()


def accepted_payloads(root=ROOT, receipt_path=None):
    root = Path(root)
    receipt_path = Path(receipt_path) if receipt_path is not None else root / RECEIPT
    receipt = json.loads(plain_file(receipt_path))
    require(receipt.get('run_id') == ACCEPTANCE_RUN and
            receipt.get('source_commit') == generation.SOURCE_COMMIT and
            receipt.get('text_data_commit') == generation.DATA_COMMIT,
            'Accepted schema source/data/run pins differ')
    artifact = receipt.get('artifact', {})
    require(artifact.get('path') == 'accepted-36088012666.zip' and
            artifact.get('sha256') == ARTIFACT_SHA256 and artifact.get('bytes') == ARTIFACT_BYTES,
            'Accepted schema artifact pin differs')
    archive_path = receipt_path.parent / artifact['path']
    archive_bytes = plain_file(archive_path)
    require(len(archive_bytes) == ARTIFACT_BYTES and digest(archive_bytes) == ARTIFACT_SHA256,
            'Accepted schema artifact hash/size mismatch')
    with zipfile.ZipFile(archive_path) as archive:
        names = [item.filename for item in archive.infolist()]
        require(len(names) == len(set(names)) and len(names) == len({n.casefold() for n in names}),
                'Ambiguous schema artifact members')
        require(sum(item.file_size for item in archive.infolist()) <= MAX_ARTIFACT_EXPANDED,
                'Schema artifact expansion exceeds bound')
        require(REPORT_MEMBER in names and ARCHIVE_MEMBER in names, 'Missing accepted schema evidence')
        report_bytes = archive.read(REPORT_MEMBER)
        nested_bytes = archive.read(ARCHIVE_MEMBER)
    report = json.loads(report_bytes)
    require(receipt.get('schema_status') == SUCCESS and report.get('status') == SUCCESS and
            report.get('exit_code') == 0 and report.get('failures') == [] and
            report.get('queued_error_counts') and all(value == 0 for value in report['queued_error_counts']) and
            report.get('strict_reload_executed') is True and report.get('completion_marker_seen') is True and
            not report.get('timed_out') and not report.get('log_limit_exceeded'),
            'Schema generation acceptance is incomplete')
    require(report.get('source_commit') == generation.SOURCE_COMMIT and
            report.get('data_commit') == generation.DATA_COMMIT, 'Schema report source/data pins differ')
    build = report.get('schema_build_input', {})
    require(build == expected_schema_receipt(root, postgresql_build_input=build.get('postgresql_build_input')),
            'Schema build receipt differs from preserved source')
    nested_record = report.get('schema_outputs_archive', {})
    require({key: nested_record.get(key) for key in ('path', 'bytes', 'sha256')} == receipt.get('archive'),
            'Schema output archive differs from acceptance receipt')
    with tempfile.TemporaryDirectory(prefix='coh-dbserver-schema-') as temporary:
        nested_path = Path(temporary) / 'schema-outputs.zip'
        nested_path.write_bytes(nested_bytes)
        checked = archive_payloads(nested_path, nested_record)
    require(len(checked) == receipt.get('archived_files') == 56, 'Expected all 56 accepted schema outputs')
    return receipt, report, report_bytes, nested_bytes, {name: data for name, data in checked.values()}


def supplemental_payload(root, name):
    require(name in SUPPLEMENTAL_PINS, 'Unexpected supplemental input')
    subtree = 'ouroboros' if name.endswith('.cfg') else 'i24'
    value = plain_file(Path(root) / 'upstream' / subtree / name).replace(b'\r\n', b'\n')
    require(digest(value) == SUPPLEMENTAL_PINS[name], 'Supplemental text differs from immutable pin: ' + name)
    return value


def build_inputs(root=ROOT, receipt_path=None):
    root = Path(root)
    receipt, report, report_bytes, archive_bytes, files = accepted_payloads(root, receipt_path)
    templates, attributes = schema_contract(
        plain_file(root / 'upstream/ouroboros/DBServer/src/dbinit.c').decode('utf-8'))
    folded = {name.casefold(): data for name, data in files.items()}
    tables, expected_attributes = {}, {}
    for table, path in templates.items():
        require(path.casefold() in folded, 'Missing accepted table template: ' + path)
        for name, columns in template_columns(folded[path.casefold()].decode('utf-8'), table).items():
            require(name not in tables, 'Overlapping generated table: ' + name)
            tables[name] = columns
    for table, path in attributes.items():
        require(path.casefold() in folded, 'Missing accepted attribute file: ' + path)
        expected_attributes[table] = attribute_rows(folded[path.casefold()].decode('utf-8'))
        tables[table] = ['id', 'name']
    require(len(tables) == receipt.get('expected_tables') == 99 and
            sum(len(columns) for columns in tables.values()) == receipt.get('expected_columns') == 5935 and
            {name: len(rows) for name, rows in expected_attributes.items()} == receipt.get('expected_attribute_rows'),
            'Derived SQL table/column/attribute contract differs from acceptance')
    require(set(SUPPLEMENTAL) == set(SUPPLEMENTAL_PINS), 'Supplemental source contract changed')
    for name in SUPPLEMENTAL:
        require(name.casefold() not in folded, 'Supplemental path overlaps generated input')
        files[name] = supplemental_payload(root, name)
    optional = []
    for name in OPTIONAL:
        require(name not in files and not (root / 'upstream/i24' / name).exists() and
                not (root / 'upstream/ouroboros' / name).exists(),
                'Optional input unexpectedly exists; review separately: ' + name)
        optional.append({'path': name, 'status': 'absent_in_pinned_data'})
    manifest = {
        'format': 1, 'scope': 'accepted_generated_schema_inputs',
        'source_commit': generation.SOURCE_COMMIT, 'data_commit': generation.DATA_COMMIT,
        'acceptance_run_id': ACCEPTANCE_RUN, 'schema_status': report['status'],
        'accepted_artifact_sha256': ARTIFACT_SHA256,
        'schema_report_sha256': digest(report_bytes), 'schema_archive_sha256': digest(archive_bytes),
        'generated_file_count': 56, 'supplemental_file_count': len(SUPPLEMENTAL),
        'generated_payload_policy': 'exact accepted archive bytes',
        'supplemental_payload_policy': 'immutable text with canonical LF line endings',
        'files': {name: {'bytes': len(data), 'sha256': digest(data)} for name, data in sorted(files.items())},
        'expected_tables': tables, 'expected_attributes': expected_attributes,
        'optional_inputs': optional, 'android_execution_validated': False, 'gameplay_validated': False,
    }
    return files, manifest


def prepare(output, *, root=ROOT, receipt_path=None):
    output = Path(output).absolute()
    require(not output.exists() and not output.is_symlink(), 'Output must be a new directory')
    resolved = output.resolve()
    protected = (Path(root) / 'upstream').resolve()
    require(resolved != protected and protected not in resolved.parents, 'Cannot stage inside immutable source')
    files, manifest = build_inputs(root, receipt_path)
    # Validate everything before creating the destination; partial output is removed.
    output.mkdir(parents=True, exist_ok=False)
    try:
        for name, data in files.items():
            target = output / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (output / 'schema-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    except BaseException:
        shutil.rmtree(output)
        raise
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New minimal runtime directory')
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    manifest = prepare(args.output, root=args.root)
    print(json.dumps({'output': str(args.output), 'files': len(manifest['files']),
                      'tables': len(manifest['expected_tables']),
                      'attribute_rows': sum(map(len, manifest['expected_attributes'].values()))}))


if __name__ == '__main__':
    main()
