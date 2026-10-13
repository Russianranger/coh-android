#!/usr/bin/env python3
"""Isolated Map-only ordinary animation metadata scheduling experiment.

This is not a cache authority: every existing CRC, dependency date, directory
membership, decoder and failure path remains active. Do not ship this source.
UtilitiesLib does not inherit SERVER; this explicit isolated build targets only
MapServer and adds no global compiler option or Game source change.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import package_native_startup_profile as baseline
import prepare_native_startup_profile_source as profile
from map_startup_namespace_certificate import require

ROOT=Path(__file__).resolve().parents[1]
SOURCE=profile.PARSER
RECEIPT='native-map-metadata-prefetch-build-input.json'
ENVIRONMENT='COH_MAP_ANIMATION_METADATA_PREFETCH'
REFERENCE='patches/client-startup-followup/0001-preload-power-dependency-tree.patch'
HELPER=r'''// Nonshipping Map-only scheduling of the same ordinary FolderCache metadata
// request already qualified for Game. This grants no BIN/source authority.
extern FolderCache *folder_cache;
static void cohMapPreloadSequencerDependencies(const char *dir,
    const char *filemask, const char *persistfile)
{
    const char *enabled = getenv("COH_MAP_ANIMATION_METADATA_PREFETCH");
    if (!enabled || strcmp(enabled, "1") != 0 || !folder_cache
        || !dir || !filemask || !persistfile)
        return;
    if (strcmp(dir, "sequencers") == 0 && strcmp(filemask, ".txt") == 0
        && strcmp(persistfile, "bin/sequencers.bin") == 0)
    {
        DWORD begin = GetTickCount();
        FolderCacheRequestTree(folder_cache, "player_library/animations");
        printf("COH_MAP_ANIMATION_METADATA_PREFETCH_V1 tree=player_library/animations cache=bin/sequencers.bin milliseconds=%.3f source_freshness_preserved=1 crc_validation_preserved=1\n",
            (double)(DWORD)(GetTickCount() - begin));
    }
}

'''
CALL='    cohMapPreloadSequencerDependencies(dir, filemask, persistfile);\n'


def digest(data):return hashlib.sha256(data).hexdigest()


def original_parser(root=ROOT):
    return profile.parser_source(profile.source_bytes(SOURCE,root))


def patch_source(original):
    require(original == original_parser(), 'Exact observed retained Map parser required')
    text=original.decode()
    signature='SimpleBufHandle ParserIsPersistNewer('
    require(text.count(signature)==1, 'Unique native freshness definition required')
    current=text.replace(signature,HELPER+signature,1)
    anchor='    COH_MAP_BIN_PHASE(2);\n\n    // assemble file list from directories\n'
    require(current.count(anchor)==1,'Actual after-dependency-header prefetch callsite differs')
    current=current.replace(anchor,CALL+anchor,1)
    require(current.replace(HELPER,'',1).replace(CALL,'',1)==text,
        'Metadata scheduling changed existing native statements')
    return current.encode()


def expected_receipt(root=ROOT):
    root=Path(root);original=original_parser(root)
    callsites=('Common/seq/seqload.c','libs/UtilitiesLib/src/utils/FolderCache.c',
        'libs/UtilitiesLib/src/utils/FolderCacheNode.c','libs/UtilitiesLib/src/utils/file.c')
    return {'format':1,'role':'nonshipping_map_sequencer_metadata_prefetch','publication_allowed':False,
        'build_targets':['MapServer'],'architecture':'Win32','configuration':'OptDebug',
        'source_local_Map_only_staging':True,'UtilitiesLib_SERVER_define_assumed':False,
        'source_sha256':{SOURCE:digest(original)},'patched_sha256':{SOURCE:digest(patch_source(original))},
        'retained_callsites_sha256':{n:digest(profile.source_bytes(n,root)) for n in callsites},
        'staged_callsites_sha256':{n:(profile.expected_receipt(root)['patched_sha256'][n]
            if n==profile.SEQUENCER else digest(profile.source_bytes(n,root))) for n in callsites},
        'helper_sha256':digest(HELPER.encode()),'retained_Game_reference':{REFERENCE:baseline.pin(root/REFERENCE)},
        'environment':{'name':ENVIRONMENT,'enabled_value':'1','disabled_by_default':True},
        'exact_request':{'directory':'sequencers','filemask':'.txt','persistfile':'bin/sequencers.bin',
            'tree':'player_library/animations'},
        'scope':'ordinary_FolderCache_metadata_only_after_valid_BIN_dependency_header',
        'freshness_body_exact_except_request':True,'CRC_and_schema_checks_preserved':True,
        'native_decoder_preserved':True,'source_date_and_membership_checks_preserved':True,
        'stock_text_and_failure_fallback_preserved':True,'provider_precedence_preserved':True,
        'new_asset_bytes_preloaded':False,'persistent_cache_authority_added':False,
        'shipping_allowed':False,'native_execution_validated':False,'physical_savings_validated':False}


def source_pins(source):
    value=baseline.read(source/baseline.retained_map.RECEIPT)
    require(value==baseline.retained_map.expected_receipt(value['animation_certificate'],
        monorail_build_input=value['monorail_build_input']), 'Retained Map producer recipe differs')
    observed=profile.expected_receipt();require(baseline.read(source/profile.RECEIPT)==observed,
        'Retained Map observer recipe differs')
    pins={**value['patched_sha256'],**value['overlay_sha256'],**value['retained_sources_sha256'],
        **value['monorail_build_input']['retained_collision_sources'],**observed['patched_sha256']}
    pins.update({(Path(n).parent/profile.HEADER).as_posix():observed['header_sha256']
        for n in (profile.PARSER,profile.SEQUENCER)})
    pins[profile.freshness.TARGET]=observed['activated_freshness_header_sha256']
    return value,pins


def validate_source(source):
    source=Path(source);expected=expected_receipt()
    require(baseline.read(source/RECEIPT)==expected,'Map metadata prefetch recipe differs')
    retained,pins=source_pins(source)
    pins.update(expected['staged_callsites_sha256']);pins.update(expected['patched_sha256'])
    for name,pin in pins.items():require(baseline.pin(source/name)['sha256']==pin,'Map source changed: '+name)
    return expected,retained


def stage(source):
    source=Path(source).absolute()
    require(not any(p.is_symlink() for p in (source,*source.parents)), 'Linked candidate source refused')
    source=source.resolve()
    require(source!=ROOT and source not in ROOT.parents and ROOT/'upstream' not in (source,*source.parents),
        'Immutable repository/native source may not be patched')
    require(not (source/RECEIPT).exists(),'Candidate source already staged')
    baseline.map_input(source,profiled=True)
    expected=expected_receipt()
    for name,pin in expected['staged_callsites_sha256'].items():
        require(baseline.pin(source/name)['sha256']==pin,'Retained source callsite differs: '+name)
    current=(source/SOURCE).read_bytes();patched=patch_source(current)
    (source/SOURCE).write_bytes(patched);baseline.write(source/RECEIPT,expected)
    validate_source(source)
    return expected


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-staging',type=Path,required=True)
    args=p.parse_args();print(json.dumps(stage(args.source_staging),sort_keys=True))
