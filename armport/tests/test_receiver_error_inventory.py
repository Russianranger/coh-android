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
