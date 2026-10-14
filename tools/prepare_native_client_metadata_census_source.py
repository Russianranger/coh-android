#!/usr/bin/env python3
"""Prepare a closed, nonshipping stock-constructor metadata census adapter.

The production source never registers a census. Decoding is not authentication;
a future independently qualified generation producer and current provider lease
must exist before this prototype can replace any native enumeration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import map_startup_namespace_certificate as namespace
import prepare_map_startup_observer_source as safe

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'libs/UtilitiesLib/src/utils/FolderCache.c'
NODE_SOURCE = 'libs/UtilitiesLib/src/utils/FolderCacheNode.c'
STAT_SOURCE = 'libs/UtilitiesLib/src/utils/winfiletime.c'
SIGNATURE = 'static void FolderCacheAddFolderToNode('
HELPER = 'static void cohFolderCacheAddCensusEntry('
HEADERS = ('coh_folder_census.h', 'coh_folder_census_adapter.h', 'coh_folder_census_capture.h', 'coh_folder_census_observation.h')
RECEIPT = 'native-client-metadata-census-build-input.json'
CMAKE_INJECTION = 'coh_client_metadata_capture.cmake'
QUERY_SENTINEL = '''    if (fc==NULL || relpath==NULL) {
#if defined(COH_CLIENT_METADATA_CENSUS_CAPTURE)
        if (fc==NULL && relpath==NULL) cohFolderCensusFlushStatObservations();
#endif
        return NULL;
    }'''


def digest(value):
    return hashlib.sha256(value).hexdigest()


def bytes_lf(path):
    return Path(path).read_bytes().replace(b'\r\n', b'\n')


def source_bytes(root=ROOT):
    return bytes_lf(Path(root) / 'upstream/ouroboros' / SOURCE)


def patch_stat_source(original):
    text = original.decode()
    function = namespace.function(text, 'int _AltStat(')
    start = '    if ((hndl = CreateFileA(name,\n'
    end = '                    NULL)) == INVALID_HANDLE_VALUE)'
    namespace.require(function.count(start) == function.count(end) == 1,
                      'Stock native CreateFile call differs')
    patched = function.replace(start, '    hndl = CreateFileA(name,\n', 1).replace(end, '''                    NULL);
#if defined(COH_CLIENT_METADATA_CENSUS_CAPTURE)
    if (coh_client_census_stat_scope > 0) {
        int coh_saved_errno = errno;
        DWORD coh_saved_error = GetLastError();
        cohClientCensusObserveStatStage(COH_CENSUS_STAT_CREATE, hndl != INVALID_HANDLE_VALUE);
        SetLastError(coh_saved_error);
        errno = coh_saved_errno;
    }
#endif
    if (hndl == INVALID_HANDLE_VALUE)''', 1)
    info = '        GetFileInformationByHandle(hndl, &bhfi);'
    namespace.require(patched.count(info) == 1, 'Stock native file information call differs')
    patched = patched.replace(info, '''#if defined(COH_CLIENT_METADATA_CENSUS_CAPTURE)
        {
            BOOL coh_info_result = GetFileInformationByHandle(hndl, &bhfi);
            if (coh_client_census_stat_scope > 0) {
                int coh_saved_errno = errno;
                DWORD coh_saved_error = GetLastError();
                cohClientCensusObserveStatStage(COH_CENSUS_STAT_FILE_INFORMATION, coh_info_result != 0);
                SetLastError(coh_saved_error);
                errno = coh_saved_errno;
            }
        }
#else
        GetFileInformationByHandle(hndl, &bhfi);
#endif''', 1)
    text = text.replace(function, patched, 1)
    return ('#if defined(COH_CLIENT_METADATA_CENSUS_CAPTURE)\n#include <errno.h>\n#include "coh_folder_census_observation.h"\n#endif\n' + text).encode()


def per_entry_body(original):
    function = namespace.function(original.decode(), SIGNATURE)
    begin = '    do {\n'
    end = '\n    } while (fwFindNextFile(handle, &wfd)!=0);'
    namespace.require(function.count(begin) == function.count(end) == 1,
                      'Stock metadata constructor enumeration differs')
    return function.split(begin, 1)[1].split(end, 1)[0]


def patch_source(original):
    text = original.decode()
    function = namespace.function(text, SIGNATURE)
    body = per_entry_body(original)
    namespace.require(all(word not in body for word in ('strLength', 'basepath', 'handle')),
                      'Stock per-entry constructor closure differs')
    helper = (HELPER + '\n'
              '    FolderCache *fc, FolderNode **node, FolderNode **tail, FolderNode *parent,\n'
              '    int virtual_location, const WIN32_FIND_DATAA *coh_entry)\n{\n'
              '    char buffer[1024];\n    WIN32_FIND_DATAA wfd = *coh_entry;\n'
              '    FolderNode *node2;\n' + body.replace('continue;', 'return;') + '\n}\n\n')
    anchor = '    strcpy(buffer, basepath);\n    strcat(buffer, "/*");'
    namespace.require(function.count(anchor) == 1, 'Stock pre-enumeration anchor differs')
    hook = '''#if defined(COH_CLIENT_METADATA_CENSUS_PROTOTYPE)
    {
        CohFolderCensusDirectory coh_directory;
        if (cohFolderCensusAcquireDirectory(&coh_folder_census_context,
                fc, folder_cache, basepath,
                FolderCache_GetFromVirtualLocation(fc, 0),
                FolderCache_GetNumGDDs(fc), FolderCache_GetNumPiggs(fc),
                virtual_location, *node == NULL && *tail == NULL,
                fc->nodeCreateCallback == NULL && fc->nodeDeleteCallback == NULL,
                folder_cache_update_enable == 0,
                FolderCacheGetMode() == FOLDER_CACHE_MODE_DEVELOPMENT_DYNAMIC,
                folder_cache_exclusion == FOLDER_CACHE_ALL_FOLDERS &&
                    folder_cache_exclusion_folder == NULL,
                fileIsUsingDevData(), &coh_directory)) {
            unsigned int coh_i;
            /* Complete decoder and lease preflight precede every mutation.
             * Records retain original native FindFirst/FindNext arrival order;
             * the literal stock helper still owns pruning and FolderNodeAdd. */
            for (coh_i = 0; coh_i < coh_directory.count; ++coh_i) {
                cohFolderCensusCopyFindData(&coh_directory, coh_i, &wfd);
                cohFolderCacheAddCensusEntry(fc, node, tail, parent,
                    virtual_location, &wfd);
            }
            goto coh_census_recurse;
        }
    }
#endif

'''
    patched = function.replace(anchor, hook + anchor, 1)
    stock_loop = '    do {\n' + body + '\n    } while (fwFindNextFile(handle, &wfd)!=0);'
    namespace.require(patched.count(stock_loop) == 1, 'Stock constructor loop differs')
    patched = patched.replace(stock_loop, '''    do {
        cohFolderCacheAddCensusEntry(fc, node, tail, parent, virtual_location, &wfd);
    } while (fwFindNextFile(handle, &wfd)!=0);''', 1)
    recurse = '    for(node2 = *node; node2; node2 = node2->next){'
    namespace.require(patched.count(recurse) == 1, 'Stock recursive walk differs')
    patched = patched.replace(recurse, '#if defined(COH_CLIENT_METADATA_CENSUS_PROTOTYPE)\ncoh_census_recurse:\n#endif\n' + recurse, 1)
    text = text.replace(function, helper + patched, 1)
    capture_anchor = 'static bool ban_all_overrides = false;\n'
    namespace.require(text.count(capture_anchor) == 1, 'Native capture globals anchor differs')
    text = text.replace(capture_anchor, capture_anchor + '#if defined(COH_CLIENT_METADATA_CENSUS_CAPTURE)\n#include "coh_folder_census_capture.h"\n#define COH_FOLDER_CENSUS_ALTSTAT(fc,name,out,key) cohFolderCensusObservedAltStat(fc,name,out,key)\n#else\n#define COH_FOLDER_CENSUS_ALTSTAT(fc,name,out,key) _AltStat(name,out)\n#endif\n', 1)
    pig_function = namespace.function(text, 'int FolderCacheAddAllPigs(')
    pig_end = '    }\n    return 0;\n}'
    namespace.require(pig_function.count(pig_end) == 1, 'Stock PIG initialization tail differs')
    pig_capture = pig_function.replace(pig_end, '    }\n#if defined(COH_CLIENT_METADATA_CENSUS_CAPTURE)\n    cohFolderCensusCapturePigIndex(fc);\n#endif\n    return 0;\n}', 1)
    text = text.replace(pig_function, pig_capture, 1)
    for old, new in (('_AltStat(relpath, &sbuf)', 'COH_FOLDER_CENSUS_ALTSTAT(fc,relpath,&sbuf,relpath)'), ('_AltStat(filename, &sbuf)', 'COH_FOLDER_CENSUS_ALTSTAT(fc,filename,&sbuf,relpath)')):
        namespace.require(text.count(old) == 1, 'Stock filesystem override call differs')
        text = text.replace(old, new, 1)
    old_sentinel = '    if (fc==NULL || relpath==NULL) return NULL;'
    namespace.require(text.count(old_sentinel) == 1, 'Stock query sentinel differs')
    text = text.replace(old_sentinel, QUERY_SENTINEL, 1)
    include = '#include "utilitieslib/utils/FolderCache.h"\n'
    namespace.require(text.count(include) == 1, 'Stock cache include differs')
    return text.replace(include, include + '#if defined(COH_CLIENT_METADATA_CENSUS_PROTOTYPE)\n#include "coh_folder_census_adapter.h"\n#endif\n', 1).encode()


def expected_receipt(root=ROOT):
    root = Path(root)
    original = source_bytes(root)
    node = bytes_lf(root / 'upstream/ouroboros' / NODE_SOURCE)
    patched = patch_source(original)
    return {'format': 1, 'role': 'nonshipping_native_pig_index_capture_and_scoped_census_prototype',
        'retained_game_recipe': 'package_client_render_queue_native',
        'source_sha256': {SOURCE: digest(original), NODE_SOURCE: digest(node), STAT_SOURCE: digest(bytes_lf(root / 'upstream/ouroboros' / STAT_SOURCE))},
        'patched_sha256': {SOURCE: digest(patched), STAT_SOURCE: digest(patch_stat_source(bytes_lf(root / 'upstream/ouroboros' / STAT_SOURCE)))},
        'overlay_sha256': {'libs/UtilitiesLib/src/utils/' + name: digest(bytes_lf(
            root / 'database/client-metadata-census/overlay' / name)) for name in HEADERS},
        'cmake_injection_sha256': digest(bytes_lf(root / 'database/client-metadata-census/overlay' / CMAKE_INJECTION)),
        'cmake_injection_role': 'CMAKE_PROJECT_INCLUDE; deferred UtilitiesLib-only capture define; Game-only MSVC Win32',
        'retained_FolderNodeAdd_sha256': digest(namespace.function(node.decode(), 'FolderNode *FolderNodeAdd(').encode()),
        'per_entry_body_sha256': digest(per_entry_body(original).encode()),
        'production_registration_present': False, 'production_activation_available': False,
        'compile_gate': 'COH_CLIENT_METADATA_CENSUS_PROTOTYPE; not defined by retained UtilitiesLib',
        'upstream_Game_CLIENT_macro_propagates_to_UtilitiesLib': False,
        'decoder_is_provider_authentication': False, 'lease_callback_mandatory': True,
        'registered_cache_owner_thread_required': True,
        'borrowed_directory_index_bound_to_original_context': True,
        'register_input_context_alias_refused_before_writes': True,
        'authority_token_role': 'opaque identity binding; not a cryptographic verification API',
        'source_scope': 'dedicated Game-only build macro, global folder_cache, owning thread, one GDD, dynamic dev mode, initial empty siblings, callbacks disabled, ALL-folder policy',
        'admitted_branches': ['texture_library', 'object_library', 'fx', 'scripts', 'scripts.loc'],
        'all_native_arrival_records_replayed': True, 'native_directory_recursion_retained': True,
        'native_hash_build_unchanged': True, 'native_override_and_query_cache_semantics_unchanged': True,
        'native_override_stat_observer_only': True, 'native_legacy_ignored_info_return_unchanged': True,
        'native_stat_hooks_preserve_errno_and_GetLastError': True,
        'native_stat_counters_atomic_and_scoped_by_thread_local_override': True,
        'owned_guard_or_unknown_eligible_directory_failure_revokes_registration_before_stock_recursion': True,
        'native_reserved_fields_and_padding': 'canonical zero; pinned Wine A enumeration does not initialize these fields',
        'current_metadata_claim': 'FolderCache consumed fields only; capture atime and creation provenance is not current-field authority',
        'previous_closed_prototype_source': '7f3d37fc191f3f30c124d6d57581afb64cceef42',
        'native_pig_capture_compile_gate': 'COH_CLIENT_METADATA_CENSUS_CAPTURE; absent production',
        'native_pig_capture_activation': 'COH_CLIENT_CENSUS_CAPTURE=1 plus exact64hex generation',
        'native_pig_capture_after_stock_initialization': True,
        'native_pig_capture_all_indices_under_provider_lock': True,
        'native_pig_capture_registers_provider_authority': False,
        'native_pig_capture_maximum_records': 200000,
        'native_pig_capture_maximum_output_bytes': 8388608,
        'native_source_schema_changed': False, 'provider_order_changed': False,
        'asset_payload_reads_added': False, 'game_data_or_player_sql_changed': False,
        'native_windows_executed': False, 'native_game_executed': False,
        'native_wine_executed': False, 'physical_device_executed': False,
        'publication_allowed': False}


def validate_staged_source(source, root=ROOT):
    """Retain original raw ancestry while checking every effective source pin."""
    root = Path(root).resolve()
    source = Path(source).absolute()
    namespace.require(not any(p.is_symlink() for p in (source, *source.parents)), 'Linked census validation refused')
    source = source.resolve()
    sys.path.insert(0, str(root / 'tools/android/interactive'))
    import package_client_render_queue_native as retained
    expected = expected_receipt(root)
    namespace.require(retained.typed_equal(retained.baseline.read_json(
        safe.safe_staging_file(source, RECEIPT)), expected), 'Exact census source receipt differs')
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
            'Retained Game source producer differs: ' + producer.RECEIPT)
        for field in ('native_callsite_sources_sha256', 'patched_sha256', 'overlay_sha256'):
            pins.update(previous.get(field, {}))
    for name, pin in retained.baseline.schema_pins().items():
        pins.setdefault(name, pin)
    namespace.require(pins.get(SOURCE) == expected['source_sha256'][SOURCE], 'Retained census predecessor pin differs')
    pins.update(expected['patched_sha256'])
    pins.update(expected['overlay_sha256'])
    pins[CMAKE_INJECTION] = expected['cmake_injection_sha256']
    pins[NODE_SOURCE] = expected['source_sha256'][NODE_SOURCE]
    for name, pin in pins.items():
        path = safe.safe_staging_file(source, name)
        namespace.require(path.is_file() and digest(bytes_lf(path)) == pin, 'Exact inherited Game source closure differs: ' + name)
    return {'source': expected, 'retained_game_build_input': retained.expected_receipt(),
            'historical_source_receipts': historical, 'validated_sources_sha256': pins}


def stage(source, root=ROOT):
    root = Path(root).resolve()
    source = Path(source).absolute()
    namespace.require(not any(p.is_symlink() for p in (source, *source.parents)), 'Linked census staging refused')
    source = source.resolve()
    namespace.require(source != root and source not in root.parents and root / 'upstream' not in (source, *source.parents),
                      'Repository or immutable upstream staging refused')
    sys.path.insert(0, str(root / 'tools/android/interactive'))
    import package_client_render_queue_native as retained
    retained.validate_source(source)
    receipt = expected_receipt(root)
    for name, value in receipt['source_sha256'].items():
        path = safe.safe_staging_file(source, name)
        namespace.require(path.is_file() and digest(bytes_lf(path)) == value, 'Exact retained census predecessor differs: ' + name)
    for name in (*HEADERS, RECEIPT, CMAKE_INJECTION):
        target = 'libs/UtilitiesLib/src/utils/' + name if name in HEADERS else name
        namespace.require(not safe.safe_staging_file(source, target).exists(), 'Census output already exists: ' + target)
    for name in HEADERS:
        (source / 'libs/UtilitiesLib/src/utils' / name).write_bytes(bytes_lf(root / 'database/client-metadata-census/overlay' / name))
    (source / CMAKE_INJECTION).write_bytes(bytes_lf(root / 'database/client-metadata-census/overlay' / CMAKE_INJECTION))
    (source / SOURCE).write_bytes(patch_source(bytes_lf(source / SOURCE)))
    (source / STAT_SOURCE).write_bytes(patch_stat_source(bytes_lf(source / STAT_SOURCE)))
    (source / RECEIPT).write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    return validate_staged_source(source, root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-staging', type=Path, required=True)
    print(json.dumps(stage(parser.parse_args().source_staging), sort_keys=True))
