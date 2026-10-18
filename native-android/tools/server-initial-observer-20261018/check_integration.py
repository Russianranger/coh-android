#!/usr/bin/env python3
"""Check new hook integration against retained accepted source; never build/run.

New uncommitted suppliers receive an explicitly prospective raw-byte closure.
The production recipe still requires actual committed Git admission in CI.
"""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEC = importlib.util.spec_from_file_location('coh_new_initial_integration_recipe', HERE / 'recipe.py')
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)
ARCHIVE = ('native-android/engine/scenecatalog-server/evidence/'
           'fresh-callback-profile-20261018/compile-initial-owner-20261018/'
           'fresh-map-initial-owner-build-39099315295.zip')
ARCHIVE_BYTES = 6784966
ARCHIVE_SHA256 = 'cd27cda26fae3bf5ab76889f82c2b467cc97423c260e69c997a62cff9756156b'


def check():
    _, fresh, hooks = r.context(ROOT)

    def prospective(_):
        result = fresh.checkout_closure(ROOT)
        for folder in (HERE, ROOT / r.HOOKS):
            for source in folder.iterdir():
                if source.is_file() and source.suffix in ('.py', '.json', '.h', '.c', '.inc'):
                    result[source.relative_to(ROOT).as_posix()] = r.sha(r.read(source))
        return result

    before = prospective(ROOT)
    archive = ROOT / ARCHIVE
    raw = r.read(archive)
    r.require(len(raw) == ARCHIVE_BYTES and r.sha(raw) == ARCHIVE_SHA256, 'INTEGRATION_ACCEPTED_ARCHIVE_PIN')
    with zipfile.ZipFile(archive) as bundle:
        candidates = [n for n in bundle.namelist() if n.endswith('/compile-only-receipt.json')
                      and 'UNADMITTED' not in n]
        r.require(len(candidates) == 1, 'INTEGRATION_ACCEPTED_RECEIPT_MEMBER')
        prefix = candidates[0].removesuffix('compile-only-receipt.json')
        old = r.decode(bundle.read(candidates[0]))
        # Do not extract or duplicate the accepted PE. Its exact ZIP stays put.
        store = {n: bundle.read(prefix + n) for n in old['artifacts'] if n != 'MapServer.exe'}
    for name, value in store.items():
        r.require(r.pin(value) == old['artifacts'][name], 'INTEGRATION_ACCEPTED_SOURCE_PIN')
    originals = {}
    for name in hooks.PATCHED:
        originals[name] = (store['source/' + name] if 'source/' + name in store
                           else r.read(ROOT / 'upstream/ouroboros' / name))
    output = hooks.transform(originals)
    r.require(hooks.reverse(output) == originals, 'INTEGRATION_EXACT_REVERSAL')
    overlay = hooks.overlays(ROOT)
    store.update({'source/' + n: raw for n, raw in output.items()})
    store.update({'source/' + n: raw for n, raw in overlay.items()})
    with patch.object(r, 'checkout_closure', prospective):
        prior = r.decode(store[fresh.RECEIPT])
        declared = r.stage_expected(ROOT, prior, originals, output, overlay)
        store[r.STAGE_RECEIPT] = r.encoded(declared)

        def get(name):
            return store[name if name in (r.STAGE_RECEIPT, fresh.RECEIPT, fresh.old.RECEIPT, fresh.old.PRIOR)
                         else 'source/' + name]

        actual = r.verify_bytes(ROOT, get)
        r.require(fresh.base.json_equal(actual, declared), 'INTEGRATION_NEW_ROLE_RECEIPT')
        names = r.artifact_names(ROOT)
        invalid = dict(declared)
        invalid['world_authority'] = 0
        store[r.STAGE_RECEIPT] = r.encoded(invalid)
        try:
            r.verify_bytes(ROOT, get)
        except ValueError as error:
            r.require(str(error) == 'INITIAL_STAGE_RECEIPT', 'INTEGRATION_TYPE_REFUSAL')
        else:
            raise ValueError('INTEGRATION_TYPE_GUARD_NOT_REFUSED')
    r.require(prospective(ROOT) == before, 'INTEGRATION_SUPPLIERS_CHANGED')
    result = {'schema': 'coh-server-initial-source-integration-v1', 'passed': True,
              'accepted_archive': {'bytes': ARCHIVE_BYTES, 'sha256': ARCHIVE_SHA256},
              'accepted_compile_source_revision': old['source_revision'],
              'actual_accepted_source_subset_hashes_reverified': True,
              'patched_files': {n: {'original': r.pin(originals[n]), 'patched': r.pin(output[n])}
                                for n in hooks.PATCHED},
              'overlay': {n: r.pin(value) for n, value in overlay.items()},
              'artifact_names': sorted(names | {r.RECEIPT}), 'selected_artifact_members': len(names) + 1,
              'fresh_inherited_source_verifier_executed_for_new_role': True,
              'stage_receipt_integer_boolean_rejected': True,
              'new_supplier_closure_raw_sha256': {n: value for n, value in before.items()
                     if n.startswith(r.HOOKS + '/') or n.startswith('native-android/tools/server-initial-observer-20261018/')},
              'new_supplier_raw_bytes_bracketed': True,
              'new_supplier_Git_admission': 'prospective_only_pending_primary_commit',
              'actual_full_private_stage_executed': False,
              'accepted_test_or_qualifier_entrypoints_reexecuted': False,
              'compiler_executed': False, 'services_executed': False, 'world_authority': False}
    destination = HERE / 'qualification/source-integration.json'
    with destination.open('xb') as stream:
        stream.write(r.encoded(result))
    print(json.dumps({'passed': True, 'patched_existing_files': len(hooks.PATCHED),
                      'new_overlays': len(overlay), 'selected_artifact_members': len(names) + 1,
                      'proof_sha256': r.sha(r.read(destination)), 'new_Git_admission': 'prospective_only'}, sort_keys=True))


if __name__ == '__main__':
    check()
