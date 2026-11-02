"""Host-only admission of the modern candidate before unchanged save validators.

No guest code or game data is rewritten. A narrow projection removes only four
independently checked asset stages and renames one proved owned map label for
legacy host validators. All SQL/save/identity/cleanup evidence remains intact.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess

VARIANT = 'thor_certified_startup'
OPTIONAL_STAGES = ('client_visual_assets', 'client_animation_pack',
                   'client_all_zone_assets', 'client_all_zone_audio')
COMPONENTS = ('client_visual_supplement', 'client_animation_pack',
              'client_zone_supplement', 'client_zone_audio_supplement')
BASE_STAGES = ('client_inputs', 'client_private_data', 'persistent_server_profile', 'postgres_local_login',
               'presentation_display', 'wine_initialization', 'local_login_odbc', 'local_dbserver_startup',
               'local_atlas_startup', 'win32_runtime_dll', 'actual_client_startup', 'actual_client_interaction')


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def finite(value, *, maximum=None):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0 and (maximum is None or value <= maximum)


def integer(value, low=0, high=None):
    return type(value) is int and value >= low and (high is None or value <= high)


def verify_candidate_checkout(root, commit):
    root = Path(root).resolve()
    require(re.fullmatch('[0-9a-f]{40}', commit), 'Exact candidate source commit required')
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    require(actual == commit, 'Candidate checkout belongs to another source commit')
    status = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=all'], text=True)
    require(not status, 'Candidate tracked source was modified')
    return root


def verify_runtime_run(value, commit, run_id):
    require(integer(run_id, 1) and value.get('id') == run_id and type(value.get('id')) is int
            and value.get('head_sha') == commit and value.get('event') == 'workflow_dispatch'
            and value.get('status') == 'completed' and value.get('conclusion') == 'success'
            and value.get('path') == '.github/workflows/armport-app-runtime.yml'
            and value.get('repository', {}).get('full_name') == 'Russianranger/coh-android'
            and value.get('head_repository', {}).get('full_name') == 'Russianranger/coh-android',
            'Exact successful candidate runtime run required')
    return value


def native_admission(report, runtime_manifest):
    expected = runtime_manifest.get('armport_server_metrics')
    build = runtime_manifest.get('armport_server_metrics_build', {})
    key = {'actual_character_creation_guest': 'character_creation',
           'actual_character_reopen_guest': 'character_reopen'}.get(report.get('scope'))
    session = report.get('session_id')
    character = report.get(key, {})
    require(isinstance(expected, dict) and expected.get('variant') == VARIANT
            and isinstance(session, str) and re.fullmatch('[0-9a-f]{32}', session)
            and key is not None and character.get('session_id') == session,
            'Modern admission requires the actual candidate character session')
    producer = character.get('mapserver_producer', {})
    proof = producer.get('armport_server_metrics', {})
    require(canonical({key: proof.get(key) for key in expected}) == canonical(expected)
            and producer.get('mapserver_sha256') == expected['mapserver']['sha256']
            and producer.get('repository_commit') == expected['repository_commit']
            and type(producer.get('run_id')) is int and producer['run_id'] == expected['run_id']
            and producer.get('manifest_sha256') == expected['build_manifest']['sha256']
            and proof.get('policy') == 'authenticated_metrics_only_overlay'
            and proof.get('actual_mapserver_sha256') == expected['mapserver']['sha256']
            and proof.get('previous_mapserver_sha256') == build['predecessor']['mapserver']['sha256']
            and proof.get('package_receipt_sha256') == hashlib.sha256(canonical(build)).hexdigest()
            and all(proof.get(key) is False for key in ('runtime_execution_validated',
                'physical_device_validated', 'parser_or_definition_sources_changed', 'gameplay_decisions_changed')),
            'Modern guest PE/run/source/package admission differs')
    return {'session_id': session, 'producer': copy.deepcopy(proof)}


def contracts(assets, runtime_manifest):
    assets = Path(assets)
    names = ('client-visual-manifest.json', 'server-animation-manifest.json',
             'zones-world-supplement-manifest.json', 'zones-audio-supplement-manifest.json')
    result = {}
    for name in names:
        path = assets / name
        require(path.is_file() and not path.is_symlink(), 'Regular modern manifest required: ' + name)
        raw = path.read_bytes()
        require({'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} == runtime_manifest['files'][name],
                'Modern component metadata changed: ' + name)
        result[name] = json.loads(raw)
    return result


def validate_components(report, runtime_manifest, documents):
    """Verify complete modern stages before any legacy-stage projection."""
    stages = report.get('stages', [])
    require(all(isinstance(row, dict) for row in stages), 'Malformed modern stage evidence')
    expected = list(BASE_STAGES[:9]) + list(OPTIONAL_STAGES) + ['armport_client_data'] + list(BASE_STAGES[9:])
    require([row.get('stage') for row in stages] == expected
            and all(row.get('status') == 'passed' for row in stages),
            'Modern stages are missing, failed, duplicated, unknown or misordered')
    work = report.get('client_worktree', {})
    visual = report.get('client_visual_supplement', {})
    doc = documents['client-visual-manifest.json']
    require(all(visual.get(key) == doc[key] for key in ('scope', 'file_count', 'payload_bytes', 'files_sha256'))
            and visual.get('manifest_sha256') == runtime_manifest['files']['client-visual-manifest.json']['sha256']
            and visual.get('archive_sha256') == runtime_manifest['files']['client-visual-assets.zip']['sha256']
            and visual.get('worktree') == work.get('worktree_key')
            and integer(visual.get('installed_files'), high=doc['file_count'])
            and integer(visual.get('reused_files'), high=doc['file_count'])
            and visual['installed_files'] + visual['reused_files'] == doc['file_count']
            and visual.get('decoded_files') == visual['installed_files']
            and type(visual.get('fingerprint_reused')) is bool
            and visual.get('retained_baseline_payloads_preserved') is True
            and all(visual.get(key) is False for key in ('imported_files_modified', 'generated_caches_modified',
                'existing_supplements_modified', 'runtime_visual_validated', 'full_global_asset_closure'))
            and finite(visual.get('preparation_elapsed_seconds')),
            'Modern visual stage lacks complete pinned preservation evidence')
    expected_read = 0 if visual['fingerprint_reused'] else runtime_manifest['files']['client-visual-assets.zip']['bytes']
    require(type(visual.get('archive_read_bytes')) is int and visual['archive_read_bytes'] == expected_read,
            'Modern visual archive work differs from declared reuse')
    if visual['fingerprint_reused']:
        require(visual['installed_files'] == 0 and visual['decoded_files'] == 0,
                'Reused modern visual stage claimed new decoding')
    animation = report.get('client_animation_pack', {})
    doc = documents['server-animation-manifest.json']
    closure = runtime_manifest['armport_server_native_closure']
    proof = animation.get('client_contract', {})
    require(animation.get('installed') is True and type(animation.get('reused')) is bool
            and animation.get('pigg') == doc['pigg']
            and animation.get('storage') == 'owned_link_to_verified_runtime_payload'
            and animation.get('verified_payload_read_only') is True
            and animation.get('loose_inputs_preserved') is True
            and animation.get('additional_animation_payload_bytes') == 0
            and type(animation.get('additional_animation_payload_bytes')) is int
            and all(animation.get(key) is False for key in ('native_animation_reader_changed', 'physical_startup_timing_validated'))
            and proof.get('import') == work.get('import')
            and proof.get('source_data') == work.get('source_data')
            and proof.get('game_sha256') == closure['files']['CityOfHeroes.exe']['sha256']
            and proof.get('source_commit') == closure['source_commit']
            and proof.get('data_commit') == closure['data_commit']
            and proof.get('animation_inventory_sha256') == doc['identity']['animation_inventory_sha256']
            and proof.get('loose_animation_count') == len(doc['files'])
            and finite(animation.get('elapsed_seconds')),
            'Modern animation stage changed original loose/native inputs or identity')
    for component, manifest_name, selection in (
        ('client_zone_supplement', 'zones-world-supplement-manifest.json', 'all_zone_client_resources'),
        ('client_zone_audio_supplement', 'zones-audio-supplement-manifest.json', 'all_zone_client_audio')):
        observed, doc = report.get(component, {}), documents[manifest_name]
        require(observed.get('version') == doc['version'] and observed.get('scope') == selection
                and observed.get('file_count') == doc['file_count']
                and observed.get('files_sha256') == doc['files_sha256']
                and observed.get('manifest_sha256') == runtime_manifest['files'][manifest_name]['sha256']
                and integer(observed.get('installed_files'), high=doc['file_count'])
                and integer(observed.get('decoded_payload_bytes'), high=doc['payload_bytes'])
                and type(observed.get('fingerprint_reused')) is bool
                and type(observed.get('source_generation_rebound')) is bool
                and all(observed.get(key) is False for key in ('imported_files_modified', 'prepared_caches_modified',
                    'runtime_visual_validated', 'physical_zoning_verified'))
                and finite(observed.get('elapsed_seconds')),
                'Modern zone/audio stage lacks complete pinned preservation evidence: ' + component)
        require(not observed['source_generation_rebound'] or observed['fingerprint_reused'],
                'Rebound modern zone/audio stage lacks reused fingerprint evidence')
        if observed['fingerprint_reused']:
            require(observed['installed_files'] == 0 and observed['decoded_payload_bytes'] == 0,
                    'Reused modern zone/audio stage claimed new decoding')


def validate_readiness(report, progress):
    key = 'character_creation' if report.get('scope') == 'actual_character_creation_guest' else 'character_reopen'
    character = report.get(key, {})
    guard = character.get('map_startup_guard', {})
    protocol = guard.get('protocol', {})
    require(character.get('map_ready') is True and guard.get('passed') is True
            and guard.get('requires_completed_tick_before_protocol') is True
            and protocol.get('ready') is True and type(protocol.get('map_id')) is int and protocol['map_id'] == 1
            and protocol.get('address') == '127.0.0.1' and type(protocol.get('port')) is int and protocol['port'] == 7001
            and all(integer(protocol.get(key), high=20) for key in ('network_age_seconds', 'stats_age_seconds')),
            'Modern map lacks fresh registered DbServer protocol readiness')
    for sample in (guard.get('before', {}), guard.get('after', {})):
        require(sample.get('available') is True and finite(sample.get('unchanged_seconds'), maximum=20),
                'Modern map tick witness is missing or stale')
        decoded = progress.decode_record(bytes.fromhex(sample.get('raw_record_hex', '')))
        require(all(sample.get(key) == value for key, value in decoded.items())
                and integer(sample.get('tick_completed'), 1), 'Modern tick witness differs from its actual raw record')
    progress.compare_records(guard['after'], guard['before'])
    return character


class ModernProjector:
    def __init__(self, interactive, runtime_manifest, client_manifest, documents, progress):
        self.interactive = interactive
        self.runtime_manifest = runtime_manifest
        self.client_manifest = client_manifest
        self.documents = documents
        self.progress = progress
        self.legacy = interactive.legacy_report
        self.records = {}

    def project(self, report, runtime_manifest, client_manifest):
        require(runtime_manifest is self.runtime_manifest and client_manifest is self.client_manifest,
                'Modern host changed its authenticated staged inputs')
        admission = native_admission(report, runtime_manifest)
        validate_components(report, runtime_manifest, self.documents)
        character = validate_readiness(report, self.progress)
        reopening = report.get('scope') == 'actual_character_reopen_guest'
        if reopening:
            zoning = report.get('character_zoning', {})
            saved = zoning.get('saved_startup', {})
            require(report.get('zoning_enabled') is True and character.get('zoning_enabled') is True
                    and character.get('connected_on_supported_map') is True and character.get('map_id') == 1
                    and saved.get('map_id') == 1 and saved.get('native_ready_verified') is True
                    and saved.get('character_world_entry_verified') is True and saved.get('native_maps_started') == [1]
                    and saved.get('sql_game_mutations_performed') is False and zoning.get('transfers') == [],
                    'Modern reopen did not use the exact Atlas zoning route')
            labels = [row.get('label') for row in report.get('processes', [])]
            require(labels.count('local-character-zoning-1') == 1 and 'local-character-atlas' not in labels,
                    'Modern reopen lacks exactly one owned Atlas MapServer')
        else:
            require(report.get('scope') == 'actual_character_creation_guest', 'Unsupported modern guest mode')
        # Host-only dependency injection: the existing legacy projector repeats
        # full actual modern admission. It does not receive fabricated old pins.
        original = self.interactive.server_pipeline.guest_admission
        self.interactive.server_pipeline.guest_admission = native_admission
        try:
            projected = self.legacy(report, runtime_manifest, client_manifest)
        finally:
            self.interactive.server_pipeline.guest_admission = original
        projected['stages'] = [row for row in projected['stages'] if row.get('stage') not in OPTIONAL_STAGES]
        require([row.get('stage') for row in projected['stages']] == list(BASE_STAGES), 'Modern stage projection changed the base lifecycle')
        if reopening:
            for row in projected['processes']:
                if row.get('label') == 'local-character-zoning-1':
                    row['label'] = 'local-character-atlas'
        # Save/account/character/container, SQL, asset and cleanup fields remain
        # those checked by the unchanged common validator immediately afterwards.
        self.records[report['session_id']] = admission
        return projected
