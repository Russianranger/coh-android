#!/usr/bin/env python3
"""Disposable source-function fixtures for offline operation attribution.

The unchanged original beacon install/proof functions run on tiny fake files.
Asset admission helpers are deterministic fixture adapters; this is NOT a real
beacon, cache-authority, server execution, production optimization or APK test.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import tempfile
import time
from types import MappingProxyType, SimpleNamespace
import zipfile

ROOT = Path(__file__).resolve().parents[3]
PINNED = 'cda93d96f8696e6a0f2ec6940a0c96e5b852f281'
SOURCE = 'android/guest/atlas_beacon_package.py'
SOURCE_SHA256 = '37a8db39c4af994bcd5b4fd077319801bacfe90c70d4414d06929408b010d981'
FUNCTIONS = ('canonical', 'install', 'proof_owner_identity', 'eligible_shared_provider',
             'mint_shared_inputs', 'reusable_shared_inputs', 'VerifiedCollisionInputs')


def source_functions(namespace):
    raw = subprocess.run(['git', '-C', str(ROOT), 'show', PINNED + ':' + SOURCE],
                         check=True, capture_output=True, timeout=30).stdout
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError('SOURCE_IDENTITY')
    tree = ast.parse(raw)
    selected = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
                and node.name in FUNCTIONS]
    if len(selected) != len(FUNCTIONS):
        raise ValueError('SOURCE_FUNCTION_IDENTITY')
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])), SOURCE, 'exec'), namespace)
    return {node.name: hashlib.sha256(ast.get_source_segment(raw.decode(), node).encode()).hexdigest()
            for node in selected}


def original_beacon_cases():
    """Exercise exact warm, cold, retained-files and proof-refusal branches.

    Independent actual pin/read/write counters, not the returned source
    counters, form the comparison oracle. No existing runtime/cache is opened.
    """
    with tempfile.TemporaryDirectory(prefix='coh-startup-oracle-') as directory:
        root = Path(directory); runtime = root / 'private'; runtime.mkdir()
        inputs_dir = runtime / 'inputs'; inputs_dir.mkdir()
        input_paths = {'data/input-a': inputs_dir / 'a', 'data/input-b': inputs_dir / 'b'}
        for index, path in enumerate(input_paths.values()):
            path.write_bytes(bytes([index + 65]) * (index * 7 + 11)); path.chmod(0o400)
        binary = runtime / 'MapServer.exe'; binary.write_bytes(b'fixture-not-executable')
        graph, date, marker = 'data/server/fixture.v8.bcn', 'data/server/fixture.v8.bcn.date', 'data/server/receipt.json'
        bodies = {graph: b'fixture-not-a-real-graph', date: struct.pack('<iII', 9, 0, 31415)}
        counters = {}
        def pin(path, context=None):
            path = Path(path); raw = path.read_bytes()
            if path in input_paths.values():
                counters['input_hash_bytes'] += len(raw); counters['input_hash_files'] += 1
            return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        counters.update(input_hash_bytes=0, input_hash_files=0)
        selected = {name: pin(path) for name, path in input_paths.items()}
        value = {'files': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                           for name, raw in bodies.items()}, 'native': {'full_world_crc': '0x00007ab7'}}
        manifest = root / 'manifest.json'; manifest.write_text(json.dumps(value))
        archive = root / 'fixture.zip'
        with zipfile.ZipFile(archive, 'w') as out:
            out.write(manifest, 'manifest.json')
            for name, raw in bodies.items(): out.writestr(name, raw)
        def regular(path, maximum, **kwargs):
            if not Path(path).is_file() or Path(path).stat().st_size > maximum:
                raise ValueError('FIXTURE_REGULAR')
        def target(rt, name, context):
            path = rt / name; path.parent.mkdir(parents=True, exist_ok=True); return path
        def fingerprints(rt, names, context):
            return {name: {'size': (rt/name).stat().st_size, 'mtime_ns': (rt/name).stat().st_mtime_ns}
                    for name in names}
        def profile(rt, document, context, *, provider_records=None):
            counters['inventory_walks'] += 1
            providers = {name: {'source': str(path), 'path': str(path),
                'uid': path.stat().st_uid, 'mode': stat.S_IMODE(path.stat().st_mode),
                'size': path.stat().st_size, 'mtime_ns': path.stat().st_mtime_ns}
                for name, path in input_paths.items()}
            if provider_records is not None: provider_records.update(providers)
            return 'fixture-profile', selected, providers, input_paths
        def atomic(path, raw):
            counters['marker_writes' if Path(path) == runtime / marker else 'graph_writes'] += 1
            Path(path).write_bytes(raw)
        class CountedZip:
            def __init__(self, *args, **kwargs):
                counters['archive_opens'] += 1; self.archive = zipfile.ZipFile(*args, **kwargs)
            def __enter__(self): return self
            def __exit__(self, *args): self.archive.close()
            def infolist(self): return self.archive.infolist()
            def getinfo(self, name): return self.archive.getinfo(name)
            def read(self, name):
                raw = self.archive.read(name)
                if name in bodies: counters['archive_payload_read_bytes'] += len(raw)
                return raw
        def require(condition, message):
            if not condition: raise ValueError(message)
        namespace = {'Path': Path, 'time': time, 'stat': stat, 'json': json, 'hashlib': hashlib,
            'struct': struct, 're': re, 'MappingProxyType': MappingProxyType, '_SHARED_PROOF_TOKEN': object(),
            'zipfile': SimpleNamespace(ZipFile=CountedZip), 'require': require,
            'MARKER': marker, 'MAP': 'fixture-only', 'POLICY': 'fixture-only', 'MANIFEST': 'manifest.json',
            'MANIFEST_SHA256': pin(manifest)['sha256'], 'ARCHIVE_SHA256': pin(archive)['sha256'],
            'ARCHIVE_BYTES': archive.stat().st_size, 'STOCK_MAPSERVER_SHA256': pin(binary)['sha256'],
            'MAX_MANIFEST': 4096, 'MAX_GRAPH': 4096, 'DATE': date, 'pin': pin,
            'read_manifest': lambda path: value, 'profile_snapshot': profile, 'private_target': target,
            'fingerprints': fingerprints, 'regular': regular, 'atomic_bytes': atomic}
        methods = source_functions(namespace)
        identity = {'format': 2, 'source_roots': [{'path': str(inputs_dir)}, {'path': str(root)}],
                    'native_closure_sha256': 'a' * 64}
        proof = []; cases = []
        for case in ('cold_missing', 'warm_hit', 'existing_graph_missing_marker',
                     'shared_proof', 'changed_generation', 'missing_generation', 'changed_provider'):
            if case not in ('cold_missing', 'warm_hit'): (runtime/marker).unlink()
            counters.clear(); counters.update(input_hash_bytes=0, input_hash_files=0,
                inventory_walks=0, graph_writes=0, marker_writes=0, archive_opens=0, archive_payload_read_bytes=0)
            used_identity = identity
            used_proof = proof[0] if case in ('shared_proof', 'changed_generation', 'missing_generation', 'changed_provider') else None
            if case == 'changed_generation': used_identity = {**identity, 'native_closure_sha256': 'b' * 64}
            if case == 'missing_generation': used_identity = None
            if case == 'changed_provider':
                path = input_paths['data/input-b']; state = path.stat()
                os.utime(path, ns=(state.st_atime_ns, state.st_mtime_ns + 1000000))
            receipt = namespace['install'](archive, manifest, runtime, context=SimpleNamespace(check=lambda: None),
                imported_inputs_readonly=True, source_cache_identity=used_identity, owner_root=root,
                source_input_proof=used_proof, input_proof_sink=proof.append if case == 'cold_missing' else None)
            cases.append({'case': case, 'receipt': receipt, 'observed': dict(counters)})
        return {'fixture_only': True, 'source_commit': PINNED, 'source_sha256': SOURCE_SHA256,
                'unchanged_function_sha256': methods, 'cases': cases}


def original_resource_semantics():
    """Execute the original resource producer with distinct controlled values."""
    path = 'native-android/combined-client/runtime/server_runtime.py'
    raw = subprocess.run(['git', '-C', str(ROOT), 'show', PINNED + ':' + path],
                         capture_output=True, check=True, timeout=30).stdout
    expected = '36d4853bfd696254a326f8fd6b9595b1dbac3a9c761808b2a9654ceae91b5895'
    if hashlib.sha256(raw).hexdigest() != expected: raise ValueError('RESOURCE_SOURCE_IDENTITY')
    node = next(n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef) and n.name == 'guest_resource_sample')
    seen = []
    def usage(who):
        seen.append(who); return SimpleNamespace(ru_maxrss={'self': 41, 'children': 73}[who])
    env = {'rss_kib': lambda: 29, 'resource': SimpleNamespace(RUSAGE_SELF='self', RUSAGE_CHILDREN='children', getrusage=usage)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), path, 'exec'), env)
    return {'source_sha256': expected, 'function_sha256': hashlib.sha256(ast.get_source_segment(raw.decode(), node).encode()).hexdigest(),
            'observed': env['guest_resource_sample'](), 'getrusage_sources': seen,
            'fixture_only': True, 'real_process_measurement': False}
