import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'scripts'),
               str(Path(__file__).resolve().parents[1] / 'replay')]
import client_errors
import run_ci


class ErrorInventory(unittest.TestCase):
    def test_full_isolated_message_ignores_stdio_interleaving(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'stdio.txt'
            trace = Path(temporary) / 'trace.jsonl'
            output = Path(temporary) / 'errors.json'
            source.write_text('BAArmPort zone: 8 client.error cut at 240 tid=42\n'
                              'BAD DATA duplicated stdout fragment\n')
            message = 'Long error ' + 'X' * 1000 + '\nLine two; literal tid=42 retained'
            trace.write_text((json.dumps(dict(stage='client.error', text=message)) + '\n') * 2)
            result = client_errors.inventory(source, output, trace)
            self.assertEqual(result['count'], 2)
            self.assertEqual(result['errors'], [dict(text='client.error ' + message, count=2)])
            self.assertTrue(result['complete_messages'])
            source.write_text('ARMPORT_ZONE_LOG_FAILED\n')
            self.assertEqual(client_errors.inventory(source, output, trace)['count'], 3)

    def test_legacy_prefix_and_embedded_thread_ids_removed(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'stdio.txt'
            source.write_text('BAArmPort zone: 12 client.error missing tid=42\n'
                              'ArmPort zone: 99 client.error missing tid=99\n')
            result = client_errors.inventory(source, source.with_suffix('.json'))
            self.assertEqual(result['errors'], [dict(text='client.error missing', count=2)])
            self.assertFalse(result['complete_messages'])

    def test_multiline_errors_are_preserved_and_counted(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'stdio.txt'
            output = Path(temporary) / 'errors.json'
            source.write_text('ArmPort zone: 12 client.error File: tricks/test.txt\n'
                              'Missing texture One tid=42\nArmPort zone: 15 textures.done \n'
                              'ArmPort zone: 99 client.error File: tricks/test.txt\n'
                              'Missing texture One tid=99\n')
            result = client_errors.inventory(source, output)
            self.assertEqual(result['count'], 2)
            self.assertEqual(result['unique'], 1)
            self.assertEqual(result['errors'][0]['text'],
                             'client.error File: tricks/test.txt\nMissing texture One')
            self.assertEqual(json.loads(output.read_text()), result)

    def test_exception_control_requires_both_execution_and_trace(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'seh.txt'
            marker = 'ARMPORT_HANDLED_SEH_CONTROL passed\n'
            trace = '0024:trace:seh:dispatch_exception code=e0424242 flags=0\n'
            for text in (marker, trace, ''):
                source.write_text(text)
                with self.assertRaisesRegex(ValueError, 'marker/trace missing'):
                    run_ci.check_exception_control(source)
            source.write_text(trace + marker)
            run_ci.check_exception_control(source)

    def test_partial_isolated_loss_is_rejected_even_with_nonzero_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stdio, trace = root / 'stdio', root / 'trace'
            stdio.write_text('ArmPort zone: 1 client.error x tid=1\n' * 2)
            trace.write_text(json.dumps(dict(stage='client.error', text='x')) + '\n')
            result = client_errors.inventory(stdio, root / 'out', trace)
            self.assertEqual(result['count'], 1)
            self.assertTrue(result['integrity_failures'])

    def test_texture_resolution_is_case_insensitive_and_groups_are_symbolic(self):
        with tempfile.TemporaryDirectory() as temporary:
            data = Path(temporary)
            (data / 'texture_library/People').mkdir(parents=True)
            (data / 'texture_library/People/PRESENT.texture').write_bytes(b'texture')
            errors = dict(errors=[dict(text="Player texture 1 'present' missing", count=1),
                                  dict(text='A:\nDeleted reference Streets/Sign', count=2),
                                  dict(text='Texture Trick "trick" references missing texture "absent".', count=3)],
                          phase_errors=[dict(phase='startup', text="Player texture 1 'present' missing", count=1)])
            result = client_errors.asset_lookup(errors, data)
            self.assertEqual(result['textures']['present'][0]['path'], 'texture_library/People/PRESENT.texture')
            self.assertEqual(result['textures']['absent'], [])
            self.assertEqual(result['group_references'], {'streets/sign': 2})
            self.assertEqual(result['phase_classes'][0]['phase'], 'startup')

    def test_texswap_and_group_declarations_do_not_conflate_missing_models_with_files(self):
        self.assertEqual(client_errors.texture_names(
            "*** TexSwap Warning: error finding texture 'DEST' to swap with 'SRC'"), ['dest', 'src'])
        self.assertEqual(client_errors.texture_names(
            "*** TexSwap Warning: was unable to find source texture 'SRC.tga' to swap"), ['src'])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'object_library/Signs'
            folder.mkdir(parents=True)
            (folder / 'Road.rootnames').write_text('Def StopSign\n Obj StopSign\nDefEnd\nDef Private&\n')
            names = ['streets/stopsign', 'stopsign__instance', 'unknown', 'private&']
            result = client_errors.group_definition_lookup(names, root)
            self.assertEqual(result['streets/stopsign'][0]['path'], 'object_library/Signs/Road.rootnames')
            self.assertFalse(result['streets/stopsign'][0]['geometry_present'])
            self.assertEqual(result['unknown'], [])
            self.assertEqual(result['private&'], [])
            (folder / 'ROAD.geo').write_bytes(b'present; model content unverified')
            result = client_errors.group_definition_lookup(names, root)
            self.assertTrue(result['stopsign__instance'][0]['geometry_present'])
            self.assertIn('geometry_sha256', result['streets/stopsign'][0])
