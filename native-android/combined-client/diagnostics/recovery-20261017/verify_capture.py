"""Read-only, exact historical artifact consistency audit; never admits a live scene."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

PIN = '3e8b5c9f5b794b58a66c6d8c62a593b926a10873'
PINS = {'evidence.zip': (2024961, '8763048abd0d55070159955f02ae9d72e452aa44d1da6e6603a22637732d764d', 34, 12324476),
        'win32-compile.zip': (3298274, '2d6444b5f7ac3a1b06cc841fe15710d298c9a913a09f0de658f8dc9b945743df', 12, 7774302)}

def require(value, message):
    if not value:
        raise ValueError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def load_archive(path, pin):
    require(path.stat().st_size == pin[0], 'archive size')
    data = path.read_bytes()
    require(digest(data) == pin[1], 'archive hash')
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        require(len(infos) == pin[2] and sum(i.file_size for i in infos) == pin[3], 'archive bounds')
        names = [i.filename for i in infos]
        require(len(set(names)) == len(names), 'duplicate member')
        require(all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts and '\\' not in n for n in names), 'member path')
        return {n: z.read(n) for n in names}  # Every CRC checked, bounded by pinned expanded size.

def match(data, record):
    require(len(data) == record['bytes'] and digest(data) == record['sha256'], 'member hash/size')

def audit(runtime, compiled, repo):
    js = lambda n: json.loads(runtime[n])
    receipt = js('capture/capture-receipt.json')
    binding = js('capture/snapshot-binding.json')
    source = js('capture/source-identity.json')
    run = js('capture/run-identity.json')
    diagnostic = js('runtime-graph-diagnostic.json')
    compile_receipt = json.loads(compiled['compile-only-receipt.json'])
    require(compile_receipt['source_revision'] == PIN and compile_receipt['passed'] is True and compile_receipt['nonshipping'] is True, 'compile provenance')
    for name, record in compile_receipt['artifacts'].items():
        match(compiled[name], record)
    require(digest(compiled['compile-only-receipt.json']) == source['compile_receipt_sha256'], 'compile binding')
    match(compiled['MapServer.exe'], source['exporter'])
    require(source['exporter']['sha256'] == receipt['exporter_sha256'], 'PE binding')
    require(source['orchestration_source_sha256'] == receipt['source_sha256'], 'source map binding')
    for name, expected in source['orchestration_source_sha256'].items():
        require('..' not in PurePosixPath(name).parts and not name.startswith('/'), 'source path')
        original = subprocess.check_output(['git', '-C', str(repo), 'show', PIN + ':' + name])
        require(digest(original) == expected, 'original source hash: ' + name)
    for kind, name in [('catalog', 'catalog.cohcat'), ('snapshot', 'runtime.cohrts')]:
        match(runtime['capture/' + name], binding[kind])
        require(binding[kind] == receipt[kind], 'payload receipt binding')
    for kind in ['source_identity', 'run_identity']:
        require(digest(runtime['capture/' + binding[kind]['file']]) == binding[kind]['sha256'] == receipt[kind + '_sha256'], 'identity binding')
    require(run['source_identity_sha256'] == binding['source_identity']['sha256'], 'run source binding')
    require(run['orchestration_source_revision'] == source['exporter_source_revision'] == receipt['orchestration_source_revision'] == PIN, 'revision')
    require(source['runtime_inventory'] == receipt['source_runtime_inventory'], 'inventory binding')
    require(binding['asset_generation'] == source['asset_generation'] == receipt['generation'] == diagnostic['capture_pins']['asset_generation'], 'generation binding')
    for key in ['catalog', 'snapshot']:
        require(binding[key]['sha256'] == diagnostic['capture_pins'][key + '_sha256'], 'diagnostic payload binding')
    for kind, prefix in [('source_identity', 'source'), ('run_identity', 'run')]:
        require(binding[kind]['sha256'] == diagnostic['capture_pins'][prefix + '_sha256'], 'diagnostic identity binding')
    for d in receipt['diagnostics']:
        match(runtime['capture/' + d['file']], d)
    for k in ['passed', 'runtime_executed', 'runtime_snapshot_captured', 'catalog_exact_equality', 'cleanup_verified', 'owned_process_groups_absent', 'source_runtime_unchanged', 'source_snapshot_only']:
        require(receipt[k] is True, 'capture gate: ' + k)
    require(binding['cleanup_verified'] is True and binding['source_snapshot_only'] is True, 'binding scope')
    for k in ['live_groups_transaction', 'physical_thor_generation_verified', 'renderer_authorized', 'player_profile_opened']:
        require(receipt[k] is False, 'capture authority scope: ' + k)
    require(binding['live_groups_transaction'] is False, 'binding authority')
    require(diagnostic['passed'] is True and diagnostic['actual_snapshot_qualified'] is True, 'diagnostic passed')
    modes = diagnostic['captured']
    require(modes['release'] == modes['asan'] == modes['ubsan'], 'diagnostic mode disagreement')
    result = modes['release']
    for k in ['graph_published', 'groups_received', 'assets_admitted', 'actor_admitted', 'world_authority']:
        require(result[k] is False and diagnostic[k] is False, 'diagnostic authority: ' + k)
    for key, sink_key in [('files', 'files'), ('slots', 'slots'), ('children', 'children'), ('root_slots', 'root_slots'), ('active_roots', 'active_roots'), ('external_count', 'external_count'), ('source_defs_crc', 'defs_crc'), ('source_refs_crc', 'refs_crc')]:
        require(result[key] == receipt['sink'][sink_key], 'sink disagreement: ' + key)
    require(result['root_matrices_verified'] == result['active_roots'] and result['definitions_crc_verified'] == 1 and result['references_crc_verified'] == 1, 'CRC/matrix verification')
    require(sum(e['reachable'] for e in result['external']) == result['reachable_external'], 'external reachability count')
    return {'schema': 'coh-independent-retained-capture-audit-v1', 'passed': True, 'source_revision': PIN,
            'source_files_verified': len(source['orchestration_source_sha256']), 'compile_members_verified': len(compile_receipt['artifacts']),
            'diagnostic_files_verified': len(receipt['diagnostics']), 'captured': result,
            'memory_scope': diagnostic['memory_scope'], 'live_world_admitted': False, 'new_server_execution': False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('corpus', type=Path)
    p.add_argument('repo', type=Path)
    a = p.parse_args()
    runtime = load_archive(a.corpus / 'evidence.zip', PINS['evidence.zip'])
    compiled = load_archive(a.corpus / 'win32-compile.zip', PINS['win32-compile.zip'])
    print(json.dumps(audit(runtime, compiled, a.repo), indent=2, sort_keys=True))

if __name__ == '__main__':
    main()
