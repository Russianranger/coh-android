#!/usr/bin/env python3
"""Stage bounded ordinary metadata insertion in an isolated retained Game.

The stock FolderNodeAdd/provider/DST/attribute logic is retained exactly. This
experimental source is not a shipping qualification or a device speed claim.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import map_startup_namespace_certificate as namespace
import prepare_map_startup_observer_source as safe

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'libs/UtilitiesLib/src/utils/FolderCache.c'
NODE_SOURCE = 'libs/UtilitiesLib/src/utils/FolderCacheNode.c'
HEADER = 'coh_folder_metadata_sort.h'
TARGET = 'libs/UtilitiesLib/src/utils/' + HEADER
OVERLAY = 'database/client-folder-sort/overlay/' + HEADER
RECEIPT = 'native-client-folder-sort-build-input.json'
SIGNATURE = 'static void FolderCacheAddFolderToNode('
HELPER = 'static void cohFolderCacheAddEnumeratedEntry('


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bytes_lf(path):
    return Path(path).read_bytes().replace(b'\r\n', b'\n')


def source_bytes(root=ROOT):
    return bytes_lf(Path(root) / 'upstream/ouroboros' / SOURCE)


def per_entry_body(original):
    text = namespace.function(original.decode('utf-8'), SIGNATURE)
    begin = '    do {\n'
    end = '\n    } while (fwFindNextFile(handle, &wfd)!=0);'
    namespace.require(text.count(begin) == text.count(end) == 1,
                      'Folder constructor enumeration anchors differ')
    return text.split(begin, 1)[1].split(end, 1)[0]


def patch_source(original):
    text = original.decode('utf-8')
    original_function = namespace.function(text, SIGNATURE)
    body = per_entry_body(original)
    # Extract the literal per-entry constructor body. The only syntactic change
    # is that loop `continue` now returns from the one-entry helper. Every stock
    # constructor operation stays in the same order, including attributes and
    # node creation callbacks. FolderNodeAdd itself is not patched.
    helper_body = body.replace('continue;', 'return;')
    helper = (HELPER + '\n'
              '    FolderCache *fc, FolderNode **node, FolderNode **tail, FolderNode *parent,\n'
              '    int virtual_location, const WIN32_FIND_DATAA *coh_entry)\n{\n'
              '    char buffer[1024];\n'
              '    WIN32_FIND_DATAA wfd = *coh_entry;\n'
              '    FolderNode *node2;\n' + helper_body + '\n}\n\n')
    # The entry body also uses strLength? It must remain strictly self-contained.
    namespace.require('strLength' not in body and 'basepath' not in body and 'handle' not in body,
                      'Folder per-entry closure differs')
    start = '    do {\n' + body + '\n    } while (fwFindNextFile(handle, &wfd)!=0);'
    replacement = '''    {
        CohFolderMetadataBatch coh_batch = {0};
        int coh_collect = cohFolderMetadataEnabled() && fc == folder_cache && *node == NULL && *tail == NULL && fc->nodeCreateCallback == NULL;
        unsigned int coh_i;
        do {
            if (coh_collect) {
                if (!cohFolderMetadataAppend(&coh_batch, &wfd)) {
                    /* The one existing enumeration continues. Buffered entries
                     * and this entry are processed in their original order. */
                    cohFolderMetadataReport(&coh_batch, coh_batch.fallback);
                    for (coh_i = 0; coh_i < coh_batch.count; ++coh_i)
                        cohFolderCacheAddEnumeratedEntry(fc, node, tail, parent,
                            virtual_location, &coh_batch.rows[coh_i].data);
                    cohFolderMetadataFree(&coh_batch);
                    coh_collect = 0;
                    cohFolderCacheAddEnumeratedEntry(fc, node, tail, parent,
                        virtual_location, &wfd);
                }
            } else {
                cohFolderCacheAddEnumeratedEntry(fc, node, tail, parent,
                    virtual_location, &wfd);
            }
        } while (fwFindNextFile(handle, &wfd)!=0);
        if (coh_collect) {
            int coh_sorted = cohFolderMetadataSort(&coh_batch);
            cohFolderMetadataReport(&coh_batch, coh_sorted ? "sorted" : coh_batch.fallback);
            for (coh_i = 0; coh_i < coh_batch.count; ++coh_i)
                cohFolderCacheAddEnumeratedEntry(fc, node, tail, parent,
                    virtual_location, &coh_batch.rows[coh_i].data);
            cohFolderMetadataFree(&coh_batch);
        }
    }'''
    namespace.require(original_function.count(start) == 1, 'Folder constructor loop differs')
    patched = original_function.replace(start, replacement, 1)
    text = text.replace(original_function, helper + patched, 1)
    anchor = '#include "utilitieslib/utils/FolderCache.h"\n'
    namespace.require(text.count(anchor) == 1, 'Folder constructor include differs')
    return text.replace(anchor, anchor + '#include "' + HEADER + '"\n', 1).encode('utf-8')


def expected_receipt(root=ROOT):
    root = Path(root)
    stock = source_bytes(root)
    node = bytes_lf(root / 'upstream/ouroboros' / NODE_SOURCE)
    function = namespace.function(node.decode(), 'FolderNode *FolderNodeAdd(')
    return {
        'format': 1, 'role': 'nonshipping_retained_game_folder_constructor_sort',
        'retained_game_recipe': 'package_client_render_queue_native',
        'source_sha256': {SOURCE: digest(stock), NODE_SOURCE: digest(node)},
        'patched_sha256': {SOURCE: digest(patch_source(stock))},
        'overlay_sha256': {TARGET: digest(bytes_lf(root / OVERLAY))},
        'retained_FolderNodeAdd_sha256': digest(function.encode()),
        'per_entry_body_sha256': digest(per_entry_body(stock).encode()),
        'activation': 'COH_CLIENT_FOLDER_METADATA_SORT=1',
        'default_enabled': False, 'node_create_callback_requires_native_fallback': True,
        'admitted_cache': 'stock_global_folder_cache_only',
        'admitted_sibling_list': 'initially_empty_only; populated_PIG_or_prior_provider_uses_stock',
        'callback_closed_source_audit': callback_source_audit(root),
        'arbitrary_dynamic_callback_transition_qualified': False,
        'maximum_directory_entries': 16384, 'maximum_diagnostic_rows': 256,
        'temporary_row_bytes': 'sizeof(WIN32_FIND_DATAA)+sizeof(unsigned int), native ABI qualified separately',
        'maximum_retained_batch_payload': '16384 * native sizeof(CohFolderMetadataRow)',
        'maximum_realloc_payload_overlap': '24576 * native sizeof(CohFolderMetadataRow), plus allocator overhead',
        'temporary_storage_released_before_recursion': True,
        'enumerations_restarted': False, 'additional_payload_reads': 0,
        'fallbacks': ['foreign_cache', 'populated_sibling_list', 'callback_present', 'disabled', 'allocation_failure', 'entry_limit', 'case_alias'],
        'fallback_preserves_original_arrival_order': True,
        'provider_order_changed': False, 'source_freshness_changed': False,
        'asset_membership_changed': False, 'metadata_values_changed': False,
        'linked_list_final_order_changed': False, 'cache_schema_changed': False,
        'native_windows_executed': False, 'native_game_executed': False,
        'physical_device_executed': False, 'publication_allowed': False,
    }


def callback_source_audit(root=ROOT):
    """Record the closed retained-source scope; generic callback mutation is unsupported."""
    root = Path(root)
    upstream = root / 'upstream/ouroboros'
    references = {}
    extensions = {'.c', '.h', '.cpp', '.hpp', '.cc', '.cxx'}
    source_count = 0
    for path in sorted(upstream.rglob('*')):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        namespace.require(not path.is_symlink(), 'Linked closed-source callback audit refused')
        source_count += 1
        raw = bytes_lf(path)
        if b'nodeCreateCallback' not in raw:
            continue
        text = raw.decode('latin-1')
        namespace.require(re.search(r'nodeCreateCallback\s*=(?!=)', text) is None,
                          'Retained Game now assigns a node-create callback; sort admission refused')
        references[path.relative_to(upstream).as_posix()] = digest(raw)
    constructor = namespace.function(source_bytes(root).decode(), 'FolderCache *FolderCacheCreate(')
    namespace.require('FolderCache *fc = calloc(sizeof(FolderCache),1);' in constructor,
                      'Stock cache constructor no longer clears callback fields')
    owner_file = bytes_lf(upstream / 'libs/UtilitiesLib/src/utils/file.c')
    namespace.require(b'        folder_cache = FolderCacheCreate();' in owner_file,
                      'Retained global cache owner construction differs')
    return {'role': 'retained_closed_source_callback_admission_audit',
            'source_files_scanned': source_count, 'callback_assignments_found': 0,
            'reference_sources_sha256': references,
            'stock_factory_sha256': digest(constructor.encode()),
            'global_owner_file_sha256': digest(owner_file),
            'all_arbitrary_runtime_memory_mutations_excluded': False}


def validate_staged_source(source, root=ROOT):
    """Validate every retained receipt/schema/callsite with one explicit override.

    Historical receipts are never rewritten. Their source pins still describe
    the retained predecessor. Only the constructor path is overridden by the
    new, separately authenticated receipt; all other closures remain exact.
    """
    root = Path(root).resolve()
    source = Path(source).absolute()
    namespace.require(not any(p.is_symlink() for p in (source, *source.parents)),
                      'Linked folder-sort validation root refused')
    source = source.resolve()
    sys.path.insert(0, str(root / 'tools/android/interactive'))
    import package_client_render_queue_native as retained
    expected = expected_receipt(root)
    namespace.require(retained.typed_equal(retained.baseline.read_json(
        safe.safe_staging_file(source, RECEIPT)), expected), 'Folder-sort source receipt differs')
    producers, current = [], retained
    while hasattr(current, 'expected_receipt'):
        producers.append(current)
        if not hasattr(current, 'base'):
            break
        current = current.base
    historical = retained.baseline.source_receipts(source)
    pins = {}
    for value in historical.values():
        for field in ('patched_sha256', 'overlay_sha256', 'graphics_overlay_sha256', 'events_overlay_sha256'):
            pins.update(value.get(field, {}))
    for producer in reversed(producers):
        previous = producer.expected_receipt()
        namespace.require(retained.typed_equal(retained.baseline.read_json(
            safe.safe_staging_file(source, producer.RECEIPT)), previous),
            'Retained Game recipe receipt differs: ' + producer.RECEIPT)
        for field in ('native_callsite_sources_sha256', 'patched_sha256', 'overlay_sha256'):
            pins.update(previous.get(field, {}))
    # Serializer schemas may also be touched by older retained overlays. Apply
    # the exact already-authenticated producer overrides in the original order.
    for name, pin in retained.baseline.schema_pins().items():
        pins.setdefault(name, pin)
    namespace.require(pins.get(SOURCE) == expected['source_sha256'][SOURCE],
                      'Retained constructor predecessor pin differs')
    pins.update(expected['patched_sha256'])
    pins.update(expected['overlay_sha256'])
    pins[NODE_SOURCE] = expected['source_sha256'][NODE_SOURCE]
    for name, pin in pins.items():
        path = safe.safe_staging_file(source, name)
        namespace.require(path.is_file() and digest(bytes_lf(path)) == pin,
                          'Exact Game constructor candidate closure differs: ' + name)
    return {'source': expected, 'retained_game_build_input': retained.expected_receipt(),
            'historical_source_receipts': historical, 'validated_sources_sha256': pins}


def stage(source, root=ROOT):
    root = Path(root).resolve()
    source = Path(source).absolute()
    namespace.require(not any(p.is_symlink() for p in (source, *source.parents)),
                      'Linked folder-sort staging refused')
    source = source.resolve()
    namespace.require(source != root and source not in root.parents and
                      root / 'upstream' not in (source, *source.parents),
                      'Repository or immutable upstream folder-sort staging refused')
    sys.path.insert(0, str(root / 'tools/android/interactive'))
    import package_client_render_queue_native as retained
    retained.validate_source(source)
    expected = expected_receipt(root)
    for name, pin in expected['source_sha256'].items():
        path = safe.safe_staging_file(source, name)
        namespace.require(path.is_file() and digest(bytes_lf(path)) == pin,
                          'Exact retained folder-sort source differs: ' + name)
    for name in (TARGET, RECEIPT):
        namespace.require(not safe.safe_staging_file(source, name).exists(),
                          'Folder-sort output already exists')
    patched = patch_source(bytes_lf(source / SOURCE))
    namespace.require(digest(patched) == expected['patched_sha256'][SOURCE],
                      'Folder-sort output source differs')
    (source / TARGET).write_bytes(bytes_lf(root / OVERLAY))
    (source / SOURCE).write_bytes(patched)
    (source / RECEIPT).write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
    validate_staged_source(source, root)
    return expected


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-staging', type=Path, required=True)
    print(json.dumps(stage(parser.parse_args().source_staging)))
