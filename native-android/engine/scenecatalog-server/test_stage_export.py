"""Exercise the private MapServer overlay and fail-closed staging boundary.

The prerequisite receipt validator and overlay payloads are isolated in staging
tests.  The actual upstream C sources still exercise the pinned transformation;
the prerequisite validator has separate receipt-shape and identity tests here.
"""
from __future__ import annotations

import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import stage_export as stage


GROUP = 'MapServer/src/group/groupnetsend.c'
INIT = 'MapServer/src/svr/svr_init.c'
EXPORT = 'MapServer/src/group/coh_source_catalog_export.inc'
SINK = 'MapServer/src/group/coh_source_catalog_sink.inc'
GROUP_SHA256 = 'cd739e2a1b424bf089017be73d3c42adef0f23aca7563e8577cfc98ecdfebff9'
NORMAL = (b'        groupLoadMap(db_state.map_name,0,!server_state.beaconProcessOnLoad);\n'
          b'        dbSetupMap();\n'
          b'        dbReadyForPlayers();\n')
HOOK = b'        coh_source_catalog_export_startup();\n'
PROTOTYPE = b'void coh_source_catalog_export_startup(void);'
OVERLAYS = {
    EXPORT: b'/* isolated bounded exporter test input */\n',
    SINK: b'/* isolated sink test input */\n',
}
PREREQUISITE = {
    'schema_version': 1,
    'build_role': 'map_startup_certified_animation',
    'build_targets': ['MapServer'],
    'animation_certificate': {},
    'monorail_build_input': {},
    'patched_sha256': {},
    'overlay_sha256': {},
    'retained_sources_sha256': {},
}


def tree_state(root):
    """Capture every regular file/link so refusals also prove no partial output."""
    root = Path(root)
    result = {}
    for target in sorted(root.rglob('*')):
        name = target.relative_to(root).as_posix()
        if target.is_symlink():
            result[name] = ('link', os.readlink(target))
        elif target.is_file():
            result[name] = ('file', target.read_bytes())
        elif target.is_dir():
            result[name] = ('directory', None)
    return result


class StageExportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.source = self.work / 'private-mapserver'
        self.source.mkdir()
        self.originals = {
            name: (ROOT / 'upstream/ouroboros' / name).read_bytes().replace(b'\r\n', b'\n')
            for name in (GROUP, INIT)
        }
        for name, payload in self.originals.items():
            target = self.source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        self.prior = copy.deepcopy(PREREQUISITE)
        self.write_prior(self.prior)
        self.overlay_patch = mock.patch.object(stage, 'overlay_bytes', return_value=copy.deepcopy(OVERLAYS))
        self.overlay_patch.start()
        self.addCleanup(self.overlay_patch.stop)

    def write_prior(self, value):
        (self.source / stage.PRIOR).write_text(json.dumps(value) + '\n', encoding='utf-8')

    def prepare(self, root=ROOT, source=None):
        with mock.patch.object(stage, 'validate_prior', return_value=copy.deepcopy(self.prior)):
            return stage.prepare(root, self.source if source is None else source)

    def verify(self):
        with mock.patch.object(stage, 'expected_prior', return_value=copy.deepcopy(self.prior)):
            return stage.verify_staged(ROOT, self.source)

    def assert_refused_unchanged(self, action, root=None):
        observed = self.work if root is None else root
        before = tree_state(observed)
        with self.assertRaises(ValueError) as caught:
            action()
        self.assertRegex(str(caught.exception), r'^COH_SCENE_CATALOG_STAGE_[0-9]+$')
        self.assertEqual(tree_state(observed), before)
        return str(caught.exception)

    def repository_fixture(self):
        root = self.work / 'source-repository'
        for name, payload in self.originals.items():
            target = root / 'upstream/ouroboros' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        return root

    def test_real_group_input_has_the_reviewed_lf_pin(self):
        self.assertEqual(hashlib.sha256(self.originals[GROUP]).hexdigest(), GROUP_SHA256)

    def test_transformation_preserves_group_prefix_and_only_adds_include_tail(self):
        original, transformed = stage.transformed_sources(ROOT)
        self.assertEqual(original[GROUP], self.originals[GROUP])
        self.assertEqual(original[INIT], self.originals[INIT])
        self.assertTrue(transformed[GROUP].startswith(self.originals[GROUP]))
        tail = transformed[GROUP][len(self.originals[GROUP]):]
        self.assertEqual(tail.count(b'#include "coh_source_catalog_export.inc"'), 1)
        self.assertEqual(tail.count(b'#include "coh_source_catalog_sink.inc"'), 1)
        self.assertNotIn(b'pktSend', tail)

    def test_startup_hook_is_only_between_normal_setup_and_ready(self):
        original, transformed = stage.transformed_sources(ROOT)
        init = transformed[INIT]
        self.assertEqual(init.count(HOOK), 1)
        self.assertEqual(init.count(PROTOTYPE), 1)
        self.assertIn(NORMAL.replace(b'        dbReadyForPlayers();\n', HOOK + b'        dbReadyForPlayers();\n'), init)
        restored = init.replace(HOOK, b'').replace(PROTOTYPE + b'\n', b'')
        self.assertEqual(restored, original[INIT])

    def test_stage_writes_exact_outputs_receipt_and_keeps_prior(self):
        before = tree_state(self.source)
        receipt = self.prepare()
        after = tree_state(self.source)
        changed = {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
        self.assertEqual(changed, {GROUP, INIT, EXPORT, SINK, stage.RECEIPT})
        self.assertEqual(json.loads((self.source / stage.RECEIPT).read_text()), receipt)
        self.assertEqual(json.loads((self.source / stage.PRIOR).read_text()), self.prior)
        self.assertEqual(receipt['build_targets'], ['MapServer'])
        self.assertEqual(receipt['source_sha256'], {
            name: hashlib.sha256(payload).hexdigest() for name, payload in self.originals.items()})
        self.assertEqual(receipt['patched_sha256'], {
            name: hashlib.sha256((self.source / name).read_bytes()).hexdigest() for name in (GROUP, INIT)})
        self.assertEqual(receipt['overlay_sha256'], {
            name: hashlib.sha256(payload).hexdigest() for name, payload in OVERLAYS.items()})
        for name, payload in OVERLAYS.items():
            self.assertEqual((self.source / name).read_bytes(), payload)
        self.assertTrue((self.source / GROUP).read_bytes().startswith(self.originals[GROUP]))
        self.assertEqual({name: (ROOT / 'upstream/ouroboros' / name).read_bytes().replace(b'\r\n', b'\n')
                          for name in (GROUP, INIT)}, self.originals)

    def test_valid_inherited_init_additions_are_preserved(self):
        inherited = self.originals[INIT].replace(b'#include <conio.h>\n', b'#include <conio.h>\n/* inherited startup instrumentation */\n', 1)
        (self.source / INIT).write_bytes(inherited)
        self.prepare()
        patched = (self.source / INIT).read_bytes()
        self.assertEqual(patched.replace(HOOK, b'').replace(PROTOTYPE + b'\n', b''), inherited)

    def test_inherited_progress_startup_preserves_marks_and_verify_roundtrip(self):
        inherited = self.originals[INIT].replace(
            NORMAL, stage.NORMAL_PROGRESS + b'        /* inherited startup instrumentation */\n', 1)
        (self.source / INIT).write_bytes(inherited)
        self.prior['patched_sha256'][INIT] = hashlib.sha256(inherited).hexdigest()
        self.write_prior(self.prior)
        prior_bytes = (self.source / stage.PRIOR).read_bytes()
        receipt = self.prepare()
        init = (self.source / INIT).read_bytes()
        expected_anchor = stage.NORMAL_PROGRESS.replace(
            b'        dbSetupMap();\n', b'        dbSetupMap();\n' + HOOK, 1)
        self.assertEqual(init.count(expected_anchor), 1)
        self.assertIn(HOOK + b'        cohMapProgressMark(COH_MAP_STAGE_READY_PUBLISH);\n', init)
        self.assertEqual(init.replace(HOOK, b'').replace(PROTOTYPE + b'\n', b''), inherited)
        self.assertEqual(self.verify(), receipt)
        self.assertEqual((self.source / stage.PRIOR).read_bytes(), prior_bytes)

    def test_missing_drifted_duplicate_or_ambiguous_progress_anchor_is_refused(self):
        inherited = self.originals[INIT].replace(NORMAL, stage.NORMAL_PROGRESS, 1)
        cases = (
            ('missing', inherited.replace(stage.NORMAL_PROGRESS, b'', 1)),
            ('drifted', inherited.replace(b'COH_MAP_STAGE_READY_PUBLISH', b'COH_MAP_STAGE_READY_CHANGED', 1)),
            ('duplicate', inherited + stage.NORMAL_PROGRESS),
            ('ambiguous', inherited + NORMAL),
        )
        for label, changed in cases:
            with self.subTest(anchor=label):
                (self.source / INIT).write_bytes(changed)
                self.assert_refused_unchanged(self.prepare)

    def test_crlf_inputs_keep_original_bytes_and_verify_roundtrip(self):
        originals = {name: raw.replace(b'\n', b'\r\n') for name, raw in self.originals.items()}
        for name, payload in originals.items():
            (self.source / name).write_bytes(payload)
        self.prior['patched_sha256'][INIT] = hashlib.sha256(originals[INIT]).hexdigest()
        self.write_prior(self.prior)
        receipt = self.prepare()
        group = (self.source / GROUP).read_bytes()
        init = (self.source / INIT).read_bytes()
        self.assertTrue(group.startswith(originals[GROUP]))
        self.assertNotIn(b'\n', group.replace(b'\r\n', b''))
        self.assertNotIn(b'\n', init.replace(b'\r\n', b''))
        self.assertEqual(init.replace(HOOK.replace(b'\n', b'\r\n'), b'').replace(
            PROTOTYPE + b'\r\n', b''), originals[INIT])
        self.assertEqual(receipt['source_sha256'], {
            name: hashlib.sha256(payload).hexdigest() for name, payload in originals.items()})
        self.assertEqual(self.verify(), receipt)

    def test_group_source_drift_is_refused_before_writes(self):
        target = self.source / GROUP
        target.write_bytes(target.read_bytes() + b'\n/* unreceipted edit */\n')
        self.assert_refused_unchanged(self.prepare)

    def test_pinned_repository_group_drift_is_refused(self):
        root = self.repository_fixture()
        target = root / 'upstream/ouroboros' / GROUP
        target.write_bytes(target.read_bytes() + b'\n/* source pin drift */\n')
        self.assert_refused_unchanged(lambda: self.prepare(root))

    def test_missing_and_duplicate_normal_startup_anchors_are_refused(self):
        for modified in (self.originals[INIT].replace(NORMAL, b'', 1), self.originals[INIT] + NORMAL):
            with self.subTest(occurrences=modified.count(NORMAL)):
                (self.source / INIT).write_bytes(modified)
                self.assert_refused_unchanged(self.prepare)

    def test_missing_and_duplicate_prototype_anchors_are_refused(self):
        anchor = b'#include <conio.h>\n'
        for modified in (self.originals[INIT].replace(anchor, b'', 1), self.originals[INIT] + anchor):
            with self.subTest(occurrences=modified.count(anchor)):
                (self.source / INIT).write_bytes(modified)
                self.assert_refused_unchanged(self.prepare)

    def test_existing_overlay_file_or_dangling_link_is_refused(self):
        for name in (EXPORT, SINK):
            for linked in (False, True):
                with self.subTest(name=name, linked=linked):
                    target = self.source / name
                    if linked:
                        target.symlink_to(self.work / 'absent-overlay')
                    else:
                        target.write_bytes(b'existing private output\n')
                    self.assert_refused_unchanged(self.prepare)
                    target.unlink()

    def test_repeat_stage_is_refused_without_changing_any_output(self):
        self.prepare()
        self.assert_refused_unchanged(self.prepare)

    def test_existing_receipt_or_dangling_receipt_link_is_refused(self):
        target = self.source / stage.RECEIPT
        for linked in (False, True):
            with self.subTest(linked=linked):
                if linked:
                    target.symlink_to(self.work / 'absent-receipt')
                else:
                    target.write_text('{}\n', encoding='utf-8')
                self.assert_refused_unchanged(self.prepare)
                target.unlink()

    def test_symlinked_stage_root_is_refused(self):
        link = self.work / 'linked-private-mapserver'
        link.symlink_to(self.source, target_is_directory=True)
        self.assert_refused_unchanged(lambda: self.prepare(source=link))

    def test_symlinked_stage_parent_is_refused(self):
        parent = self.work / 'linked-parent'
        parent.symlink_to(self.work, target_is_directory=True)
        self.assert_refused_unchanged(lambda: self.prepare(source=parent / self.source.name))

    def test_symlinked_input_files_are_refused(self):
        for name in (GROUP, INIT):
            with self.subTest(name=name):
                target = self.source / name
                outside = self.work / (target.name + '.outside')
                shutil.copyfile(target, outside)
                target.unlink()
                target.symlink_to(outside)
                self.assert_refused_unchanged(self.prepare)
                target.unlink()
                shutil.copyfile(outside, target)

    def test_symlinked_input_parent_is_refused(self):
        parent = (self.source / GROUP).parent
        outside = self.work / 'external-group'
        parent.rename(outside)
        parent.symlink_to(outside, target_is_directory=True)
        self.assert_refused_unchanged(self.prepare)

    def test_hardlinked_upstream_source_is_refused(self):
        root = self.repository_fixture()
        for name in (GROUP, INIT):
            with self.subTest(name=name):
                target = self.source / name
                target.unlink()
                os.link(root / 'upstream/ouroboros' / name, target)
                self.assert_refused_unchanged(lambda: self.prepare(root))
                target.unlink()
                target.write_bytes(self.originals[name])

    def test_repository_and_upstream_stage_aliases_are_refused(self):
        root = self.repository_fixture()
        for source in (root, root / 'upstream', root / 'upstream/ouroboros'):
            with self.subTest(alias=source.relative_to(root).as_posix()):
                self.assert_refused_unchanged(lambda: self.prepare(root, source))

    def test_wrong_prior_role_schema_or_build_targets_are_refused(self):
        cases = (
            ('build_role', 'map_startup_unqualified'),
            ('schema_version', 2),
            ('schema_version', True),
            ('build_targets', ['MapServer', 'Game']),
            ('build_targets', ['Game']),
        )
        for field, wrong in cases:
            with self.subTest(field=field, value=wrong):
                prior = copy.deepcopy(self.prior)
                prior[field] = wrong
                self.write_prior(prior)
                with mock.patch.object(stage, 'expected_prior') as expected:
                    self.assert_refused_unchanged(lambda: stage.validate_prior(ROOT, self.source))
                    expected.assert_not_called()

    def test_missing_malformed_or_linked_prior_is_refused(self):
        path = self.source / stage.PRIOR
        for kind in ('missing', 'malformed', 'link'):
            with self.subTest(kind=kind):
                path.unlink(missing_ok=True)
                if kind == 'malformed':
                    path.write_text('{ invalid json\n', encoding='utf-8')
                elif kind == 'link':
                    outside = self.work / 'prior-outside.json'
                    outside.write_text(json.dumps(self.prior), encoding='utf-8')
                    path.symlink_to(outside)
                self.assert_refused_unchanged(lambda: stage.validate_prior(ROOT, self.source))

    def test_prior_must_equal_trusted_reconstruction(self):
        expected = copy.deepcopy(self.prior)
        expected['source_commit'] = 'a' * 40
        with mock.patch.object(stage, 'expected_prior', return_value=expected):
            self.assert_refused_unchanged(lambda: stage.validate_prior(ROOT, self.source))

    def test_missing_trusted_prerequisite_module_has_numeric_error(self):
        original_path = list(sys.path)
        with mock.patch.object(stage.importlib, 'import_module', side_effect=ModuleNotFoundError('private prerequisite module')):
            self.assert_refused_unchanged(lambda: stage.expected_prior(ROOT, self.prior))
        self.assertEqual(sys.path, original_path)

    def test_trusted_prerequisite_operational_failures_have_numeric_errors(self):
        failures = (
            subprocess.CalledProcessError(1, ['git', 'apply', '--check'], stderr='private source detail'),
            RuntimeError('private prerequisite runtime detail'),
        )
        for failure in failures:
            with self.subTest(failure=type(failure).__name__):
                imported = mock.Mock()
                imported.expected_receipt.side_effect = failure
                original_path = list(sys.path)
                with mock.patch.object(stage.importlib, 'import_module', return_value=imported):
                    self.assert_refused_unchanged(lambda: stage.expected_prior(ROOT, self.prior))
                self.assertEqual(sys.path, original_path)

    def test_cli_prerequisite_failure_outputs_only_static_failure_json(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        before = tree_state(self.work)
        arguments = ['stage_export.py', '--source-root', str(ROOT), '--already-staged', str(self.source)]
        with mock.patch.object(sys, 'argv', arguments), mock.patch.object(
                stage.importlib, 'import_module', side_effect=ModuleNotFoundError('private module detail')):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = stage.main()
        self.assertEqual(result, 2)
        self.assertEqual(json.loads(stdout.getvalue()), {'schema': 1, 'status': 1, 'staged': False})
        self.assertEqual(stderr.getvalue(), '')
        self.assertEqual(tree_state(self.work), before)

    def test_prior_nested_numbers_and_booleans_must_match_trusted_types(self):
        expected = copy.deepcopy(self.prior)
        expected['animation_certificate'] = {
            'validation': {'counts': [1, 0], 'qualified': True, 'runtime_executed': False}}
        cases = (
            ('count true', lambda data: data['counts'].__setitem__(0, True)),
            ('count false', lambda data: data['counts'].__setitem__(1, False)),
            ('qualified one', lambda data: data.update(qualified=1)),
            ('runtime zero', lambda data: data.update(runtime_executed=0)),
        )
        for label, change in cases:
            with self.subTest(mutation=label):
                changed = copy.deepcopy(expected)
                change(changed['animation_certificate']['validation'])
                self.write_prior(changed)
                with mock.patch.object(stage, 'expected_prior', return_value=copy.deepcopy(expected)):
                    self.assert_refused_unchanged(lambda: stage.validate_prior(ROOT, self.source))

    def test_read_json_rejects_overflowing_floats_without_mutation(self):
        target = self.work / 'overflow.json'
        for payload in ('{"count":1e999}', '{"count":-1e999}', '{"nested":{"count":1e999}}'):
            with self.subTest(payload=payload):
                target.write_text(payload, encoding='utf-8')
                self.assert_refused_unchanged(lambda: stage.read_json(target))

    def test_read_json_rejects_duplicate_keys_at_every_depth(self):
        target = self.work / 'duplicate.json'
        for payload in ('{"schema":1,"schema":1}', '{"nested":{"count":1,"count":1}}'):
            with self.subTest(payload=payload):
                target.write_text(payload, encoding='utf-8')
                self.assert_refused_unchanged(lambda: stage.read_json(target))

    def test_oversized_prior_json_is_refused_without_changing_it(self):
        path = self.source / stage.PRIOR
        with path.open('wb') as target:
            target.write(b'{}')
            target.truncate(8 * 1024 * 1024 + 2)
        code = self.assert_refused_unchanged(lambda: stage.validate_prior(ROOT, self.source))
        self.assertEqual(code, 'COH_SCENE_CATALOG_STAGE_6')

    def test_prepare_propagates_prior_refusal_before_any_mutation(self):
        with mock.patch.object(stage, 'validate_prior', side_effect=ValueError('COH_SCENE_CATALOG_STAGE_999')):
            self.assert_refused_unchanged(lambda: stage.prepare(ROOT, self.source))

    def test_inherited_output_hash_drift_is_refused(self):
        target_name = 'Common/seq/animtrack.c'
        target = self.source / target_name
        target.parent.mkdir(parents=True)
        target.write_bytes(b'inherited certified animation source\n')
        self.prior['patched_sha256'][target_name] = hashlib.sha256(target.read_bytes()).hexdigest()
        self.write_prior(self.prior)
        with mock.patch.object(stage, 'expected_prior', return_value=copy.deepcopy(self.prior)):
            self.assertEqual(stage.validate_prior(ROOT, self.source), self.prior)
            target.write_bytes(target.read_bytes() + b'unreceipted drift\n')
            self.assert_refused_unchanged(lambda: stage.validate_prior(ROOT, self.source))

    def test_verify_accepts_exact_stage_without_mutation(self):
        receipt = self.prepare()
        before = tree_state(self.source)
        self.assertEqual(self.verify(), receipt)
        self.assertEqual(tree_state(self.source), before)

    def test_verify_rejects_each_modified_staged_source_and_overlay(self):
        self.prepare()
        for name in (GROUP, INIT, EXPORT, SINK):
            with self.subTest(name=name):
                target = self.source / name
                original = target.read_bytes()
                target.write_bytes(original + b'\n/* post-stage mutation */\n')
                self.assert_refused_unchanged(self.verify)
                target.write_bytes(original)

    def test_verify_rejects_receipt_hash_and_claim_mutations(self):
        receipt = self.prepare()
        path = self.source / stage.RECEIPT
        mutations = (
            ('stager hash', lambda value: value.update(stager_sha256='0' * 64)),
            ('source hash', lambda value: value['source_sha256'].update({GROUP: '0' * 64})),
            ('prior hash', lambda value: value.update(prior_build_input_canonical_sha256='0' * 64)),
            ('runtime claim', lambda value: value['contract'].update(runtime_executed=True)),
            ('shipping claim', lambda value: value['contract'].update(shipping_executable=True)),
            ('extra target', lambda value: value['build_targets'].append('Game')),
        )
        for label, change in mutations:
            with self.subTest(mutation=label):
                mutated = copy.deepcopy(receipt)
                change(mutated)
                path.write_text(json.dumps(mutated), encoding='utf-8')
                self.assert_refused_unchanged(self.verify)
        path.write_text(json.dumps(receipt), encoding='utf-8')
        self.assertEqual(self.verify(), receipt)

    def test_verify_rejects_integer_substitutions_for_boolean_contract_claims(self):
        receipt = self.prepare()
        path = self.source / stage.RECEIPT
        for field, value in (('nonshipping', 1), ('runtime_executed', 0)):
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(receipt)
                changed['contract'][field] = value
                path.write_text(json.dumps(changed), encoding='utf-8')
                self.assert_refused_unchanged(self.verify)

    def test_verify_rejects_changed_prior(self):
        self.prepare()
        changed = copy.deepcopy(self.prior)
        changed['source_commit'] = 'f' * 40
        self.write_prior(changed)
        self.assert_refused_unchanged(self.verify)

    def test_verify_rejects_changed_current_overlay_inputs(self):
        self.prepare()
        for name in (EXPORT, SINK):
            with self.subTest(name=name):
                changed = copy.deepcopy(OVERLAYS)
                changed[name] += b'/* changed producer or sink input */\n'
                with mock.patch.object(stage, 'overlay_bytes', return_value=changed):
                    self.assert_refused_unchanged(self.verify)

    def test_verify_restores_inherited_init_bytes_for_prior_hash_validation(self):
        self.prior['patched_sha256'][INIT] = hashlib.sha256(self.originals[INIT]).hexdigest()
        self.write_prior(self.prior)
        receipt = self.prepare()
        self.assertEqual(self.verify(), receipt)

    def test_verify_rejects_other_inherited_output_drift(self):
        name = 'Common/seq/coh_animation_certificate.h'
        target = self.source / name
        target.parent.mkdir(parents=True)
        target.write_bytes(b'certified inherited animation input\n')
        self.prior['overlay_sha256'][name] = hashlib.sha256(target.read_bytes()).hexdigest()
        self.write_prior(self.prior)
        receipt = self.prepare()
        self.assertEqual(self.verify(), receipt)
        target.write_bytes(target.read_bytes() + b'changed\n')
        self.assert_refused_unchanged(self.verify)


if __name__ == '__main__':
    unittest.main()
