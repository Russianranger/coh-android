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
