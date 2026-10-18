"""Generator/admission controls only. No compiler, service or probe execution."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('fresh_platform_compile',HERE/'compile_fresh_platform.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)


def object_bytes(machine=0x8664, optional=0):
    return struct.pack('<HHIIIHH',machine,1,0,0,0,optional,0)+bytes(40)


def member(name,body):
    header=(name.ljust(16)+'0'.ljust(12)+'0'.ljust(6)+'0'.ljust(6)+'0'.ljust(8)+str(len(body)).ljust(10)+'`\n').encode()
    return header+body+(b'\n' if len(body)&1 else b'')


class FreshCompileControls(unittest.TestCase):
    def test_fixed_production_closure(self):
        self.assertEqual(len(driver.PROJECT_INPUTS),17)
        self.assertEqual(len(set(driver.PROJECT_INPUTS)),17)
        self.assertEqual(len(driver.SOURCES),2)
        self.assertTrue(all('test_' not in name and 'wrapped_' not in name for name in driver.PROJECT_INPUTS))
        self.assertFalse(any('TEST' in define for define in driver.DEFINES))
        root=HERE.parents[3]
        self.assertTrue(all((root/name).is_file() for name in driver.PROJECT_INPUTS))

    def test_safe_build_only_batch(self):
        text=driver.batch_text(Path('C:/Program Files/VS/vcvarsall.bat'),
            ['C:/Program Files/VS/cl.exe','/c','C:/owned/fresh_probe_windows.c'])
        self.assertIn('call "C:/Program Files/VS/vcvarsall.bat" x64 >nul\r\n',text)
        self.assertIn('"C:/Program Files/VS/cl.exe" /c C:/owned/fresh_probe_windows.c',text)
        for bad in ('a&b','a|b','a>b','a<b','a%b','a!b','a^b','a"b','a\nb','a\rb','a\0b','a(b','a)b'):
            with self.assertRaises(ValueError):
                driver.batch_text(Path('safe.bat'),['cl.exe',bad])

    def test_actual_include_trace_required(self):
        with tempfile.TemporaryDirectory() as directory:
            header=Path(directory)/'windows.h'
            raw=('fresh_probe_windows.c\nNote: including file: '+str(header)+'\n').encode()
            self.assertEqual(driver.includes(raw),{header.resolve()})
            with self.assertRaises(ValueError):
                driver.includes(b'compile returned zero without include evidence\n')

    def test_exact_two_x64_objects(self):
        first=object_bytes();second=object_bytes()+b'other'
        objects={'fresh_probe_windows.obj':driver.coff(first),'fresh_probe_policy.obj':driver.coff(second)}
        archive=b'!<arch>\n'+member('/',b'index')+member('first.obj/',first)+member('second.obj/',second)
        self.assertEqual(driver.archive_objects(archive,objects),2)
        for malformed in (b'!<arch>\n',archive[:-1],archive+member('extra.obj/',first),
                          b'!<arch>\n'+member('first.obj/',first)+member('second.obj/',first)):
            with self.assertRaises(ValueError):
                driver.archive_objects(malformed,objects)
        for raw in (b'MZ',object_bytes(0x14c),object_bytes(optional=224),bytes(60)):
            with self.assertRaises(ValueError):
                driver.coff(raw)

    def test_bounded_regular_inputs_and_exact_crypto_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'input';path.write_bytes(b'bounded')
            self.assertEqual(driver.identity(path)['bytes'],7)
            with self.assertRaises(ValueError):
                driver.identity(path,6)
            alias=root/'alias';alias.symlink_to(path)
            with self.assertRaises(ValueError):
                driver.identity(alias)
            (root/'manifest.json').write_text('{}')
            with self.assertRaises(ValueError):
                driver.admit_crypto(root)


if __name__=='__main__':
    unittest.main()
