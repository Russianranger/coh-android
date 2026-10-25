import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'replay'))
import exit_diagnostics
import stage_composite_dependencies as composite
import smoke_run


class Review12(unittest.TestCase):
    def test_failure_evidence_retains_terminal_row_and_witnesses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'receiver.jsonl').write_text('{"type":"failure","reason":"cursor"}\n')
            (root / 'zone-trace.jsonl').write_text('{"stage":"replay.cleanup.begin"}\n')
            (root / 'client-stdio.txt').write_text('ArmPort replay state failed at line 42\n')
            (root / 'wine-output.txt').write_text('dispatch_exception code=c0000005\n')
            (root / 'failed-exit-inventory.txt').write_text('unclosed dispatch')
            result = exit_diagnostics.collect(root)
            self.assertEqual(result['receiver_failure']['reason'], 'cursor')
            self.assertTrue(result['cleanup_begin'])
            self.assertFalse(result['exit_begin'])
            self.assertIn('line 42', result['client_failure']['text'])
            self.assertIn('c0000005', result['wine_exception']['text'])
            self.assertEqual(result['failed_inventory'], 'unclosed dispatch')
            (root / 'receiver.jsonl').write_text('{"type":"result"}\n{')
            result = exit_diagnostics.collect(root)
            self.assertEqual(result['terminal_receiver']['type'], 'result')
            self.assertTrue(result['read_errors'])
            (root / 'zone-trace.jsonl').unlink()
            self.assertTrue(exit_diagnostics.collect(root)['read_errors'])

    def test_complete_runtime_audit_counts_and_rejects_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'Foo').mkdir()
            (root / 'Foo/a').write_bytes(b'x')
            self.assertEqual(smoke_run.audit_runtime_tree(root),
                             dict(files=1, directories=1, case_duplicates=0))
            (root / 'foo').mkdir()
            with self.assertRaisesRegex(ValueError, 'Case-equivalent'):
                smoke_run.audit_runtime_tree(root)

    def test_composite_scope_recomputed_and_drift_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / 'armport/evidence'
            evidence.mkdir(parents=True)
            # Eight distinct leaves, one previously staged leaf and one unresolved.
            declaration = 'Texture X_Test\n' + '\n'.join(
                f'{slot} leaf{i}' for i, slot in enumerate(
                    ('Base1', 'Base2', 'Multiply1', 'Multiply2', 'DualColor1',
                     'DualColor2', 'BumpMap1', 'BumpMap2', 'Mask'))) + '\nEnd\n'
            (root / 'source.txt').write_text(declaration)
            names = [f'data/texture_library/leaf{i}.texture' for i in range(9)]
            pins = {name: dict(bytes=(658461 - 7) if i == 0 else 1, sha256='a'*64)
                    for i, name in enumerate(names)}
            definitions = dict(x_test=dict(source='source.txt',
                source_sha256=hashlib.sha256(declaration.encode()).hexdigest(),
                texture_block='X_Test', leaves={f'leaf{i}': [] for i in range(9)}))
            (evidence / 'm3-dispatch-errors-40113107670.json').write_text(
                json.dumps(dict(composite_definitions=definitions)))
            (evidence / 'm3-reviewed-file-selection.json').write_text(
                json.dumps(dict(selected={'client-visual': {names[8]: pins[names[8]]}})))
            document = dict(files=pins, archive=dict(bytes=1, sha256='b'*64))
            empty = dict(files={}, archive=dict(bytes=2, sha256='c'*64))
            decoded = dict(bytes=3, sha256='d'*64)
            proposal = dict(files={n: dict(source='client-visual', referenced_by='x_test', **pins[n])
                                   for n in names[:8]}, file_count=8, payload_bytes=658461,
                sources={s: dict(manifest='assets/'+s+'-manifest.json', decoded=decoded, archive=d['archive'])
                         for s, d in (('client-visual', document), ('zones-world-supplement', empty))})
            def load(path):
                return (document if path.name == 'client-visual-manifest.json' else empty), decoded
            def write(p):
                (root / composite.PROPOSAL).write_text(json.dumps(p))
            write(proposal)
            with patch.object(composite, 'load_manifest', side_effect=load):
                self.assertEqual(composite.checked_plan(root)[0], proposal)
                bad = copy.deepcopy(proposal)
                bad['files'][names[0]]['sha256'] = '0'*64
                write(bad)
                with self.assertRaisesRegex(ValueError, 'Recomputed'):
                    composite.checked_plan(root)
                write(proposal)
                (root / 'source.txt').write_text(declaration + 'changed')
                with self.assertRaisesRegex(ValueError, 'declaration digest'):
                    composite.checked_plan(root)

    def test_composite_cache_rejects_modified_extra_missing_and_linked_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / 'a.texture'
            p.write_bytes(b'x')
            plan = dict(files={'data/a.texture': dict(bytes=1, sha256=hashlib.sha256(b'x').hexdigest())})
            composite.verify(root, plan)
            p.write_bytes(b'y')
            with self.assertRaises(ValueError): composite.verify(root, plan)
            p.write_bytes(b'x')
            (root / 'extra').write_bytes(b'z')
            with self.assertRaises(ValueError): composite.verify(root, plan)
            (root / 'extra').unlink()
            p.unlink()
            with self.assertRaises(ValueError): composite.verify(root, plan)
            p.symlink_to('/dev/null')
            with self.assertRaisesRegex(ValueError, 'Linked'): composite.verify(root, plan)
