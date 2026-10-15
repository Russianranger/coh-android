#!/usr/bin/env python3
"""Audit the missing authority for a native BIN freshness certificate.

This is a nonshipping readiness audit, not a certificate generator. In particular,
the existing private-tree generation must never authorize a native freshness
bypass: it does not identify every effective FolderCache provider/source leaf.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARSER = 'upstream/ouroboros/libs/UtilitiesLib/src/utils/textparser.c'
NODE = 'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCacheNode.c'
SOURCES = (PARSER, NODE,
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCache.c',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/file.c',
    'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/utils/FolderCache.h',
    'upstream/ouroboros/Common/seq/seqload.c', 'upstream/ouroboros/Common/fxinfo.c',
    'android/guest/character_server_data_cache.py', 'android/guest/server_cache_package.py',
    'upstream/ouroboros/libs/UtilitiesLib/src/utils/structInternals.c')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def function(text, signature):
    """Extract an actual C function, excluding braces in comments/quoted text."""
    require(text.count(signature) == 1, 'Native function anchor differs: ' + signature)
    start = text.index(signature)
    opening = text.index('{', start)
    depth, state, escaped, i = 0, None, False, opening
    while i < len(text):
        char, following = text[i], text[i:i + 2]
        if state == 'line':
            if char == '\n': state = None
        elif state == 'block':
            if following == '*/': state = None; i += 1
        elif state in ('"', "'"):
            if escaped: escaped = False
            elif char == '\\': escaped = True
            elif char == state: state = None
        elif following == '//': state = 'line'; i += 1
        elif following == '/*': state = 'block'; i += 1
        elif char in ('"', "'"): state = char
        elif char == '{': depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0: return text[start:i + 1]
        i += 1
    raise ValueError('Unterminated native function: ' + signature)


def audit(root=ROOT):
    root = Path(root)
    contents = {}
    for name in SOURCES:
        path = root / name
        require(path.is_file() and not path.is_symlink(), 'Missing or linked audit source: ' + name)
        contents[name] = path.read_bytes().replace(b'\r\n', b'\n')
    parser = function(contents[PARSER].decode(), 'SimpleBufHandle ParserIsPersistNewer(')
    node = function(contents[NODE].decode(), 'FolderNode *FolderNodeAdd(')
    cache = contents[SOURCES[2]].decode()
    files = contents[SOURCES[3]].decode()
    generation = contents['android/guest/character_server_data_cache.py'].decode()
    installer = contents['android/guest/server_cache_package.py'].decode()
    anchors = {
        'stock_signature_and_current_schema_crc_before_freshness':
            'SerializeReadOpen(persistfile, PARSE_SIG, crc, isProductionMode())' in parser,
        'stock_scan_set_membership_and_dependency_dates_required':
            all(value in parser for value in ('fileScanAllDataDirs(dir, DateCheckCallback)',
                'fileDatesEqual(scanfile->date, binfile->date, true)',
                'fileLastChanged(binfile->path)', 'if (!scanfile->seen)')),
        'stock_optional_prefix_existence_required':
            'g_StdAdditionalFilePrefixes' in parser and 'fileExists(scanfile->path)' in parser,
        'zero_dependency_date_resolves_actual_native_timestamp':
            'if (!date) date = fileLastChanged(path);' in contents[SOURCES[9]].decode(),
        'native_case_insensitive_provider_selection': 'stricmp(fn, node->name)' in node,
        'native_pig_order_and_loose_timestamp_selection': all(value in node for value in (
            'update = virtual_location <= node->virtual_location;',
            'update= (timestamp == node->timestamp) || (timestamp - node->timestamp)==3600;',
            'update= !((timestamp == node->timestamp) || (timestamp - node->timestamp)==3600);',
            'update = virtual_location >= node->virtual_location;')),
        'dynamic_native_query_can_resolve_loose_override':
            'node2 = FolderCacheFileSystemOverride(fc, path);' in cache,
        'native_root_order_is_significant': 'for (i=dirCount-1; i>=0; i--)' in files,
        'current_generation_checks_directories_and_bounded_anchors': all(value in generation for value in (
            "for row in record['directories']:", "for row in record['anchors']:",
            "One bounded read-only leaf per top-level input directory.")),
        'private_native_cache_files_take_precedence':
            'existing device-generated cache files always take precedence' in installer,
    }
    require(all(anchors.values()), 'Native namespace/freshness audit source semantics changed')
    return {'format': 1, 'role': 'nonshipping_native_namespace_bin_freshness_readiness_audit',
        'status': 'blocked_exact_native_provider_generation_missing',
        'production_freshness_bypass_enabled': False,
        'global_production_mode_enabled': False, 'native_loader_changed': False,
        'source_sha256': {name: hashlib.sha256(value).hexdigest() for name, value in contents.items()},
        'native_function_sha256': {
            'ParserIsPersistNewer': hashlib.sha256(parser.encode()).hexdigest(),
            'FolderNodeAdd': hashlib.sha256(node.encode()).hexdigest()},
        'source_semantics_verified': anchors,
        'missing_generation_authority': [
            'Actual ordered native source roots and FolderCache mode/ignore-prefix policy',
            'Actual ordered Pig set with authenticated archive identities and provider indices',
            'Complete case-folded effective provider namespace including loose overrides',
            'Complete top-level matching membership and optional-prefix presence/absence',
            'Exact opened BIN bytes plus current parser/defines/schema CRC and native ABI identity',
            'Every included source/generated-ID dependency bound to the same closed generation',
            'Native generation lifetime/ownership and mutation invalidation before acceptance'],
        'fallback_required_for': ['unknown_private_bin', 'modified_bin', 'changed_source',
            'changed_pig_or_root_order', 'loose_override', 'case_conflict', 'unproved_generation'],
        'safe_next_scope': ['sequencers', 'fx'],
        'next_implementation_boundary':
            'Create/qualify namespace during verified import/setup, then consume it natively; '
            'retain SerializeReadOpen signature/current CRC and ParserReadBinaryFile bounds/decode',
        'not_a_speed_measurement': True, 'physical_startup_savings_validated': False,
        'per_map_whole_tree_rehash_is_not_an_optimization': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    value = audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps({'status': value['status'], 'production_freshness_bypass_enabled': False,
                      'source_files': len(value['source_sha256'])}))


if __name__ == '__main__': main()
