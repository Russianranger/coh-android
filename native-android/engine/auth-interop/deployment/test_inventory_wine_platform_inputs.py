from pathlib import Path
import io,types,unittest,zipfile
SCRIPT=Path(__file__).with_name('inventory_wine_platform_inputs.py');m=types.ModuleType('checked_wine_inventory');exec(compile(SCRIPT.read_bytes(),str(SCRIPT),'exec'),m.__dict__)
class InventoryContracts(unittest.TestCase):
 def test_exact_module_names_case_and_api_set(self):
  for name in ('usr/lib/wine/i386-windows/KERNEL32.DLL','C:\\windows\\syswow64\\odbc32.dll','API-MS-WIN-CRT-HEAP-L1-1-0.dll'):self.assertTrue(m.target(name))
  for name in ('kernel32.dll.spec','kernel32.dll.so','libkernel32.so','kernel32.dll.fake','msvcp140.dll'):self.assertFalse(m.target(name))
 def test_central_inventory_only_no_member_execution(self):
  raw=io.BytesIO()
  with zipfile.ZipFile(raw,'w') as z:z.writestr('fake/kernel32.dll',b'not a PE');z.writestr('readme.txt',b'no')
  rows=m.zip_rows(raw.getvalue());self.assertEqual(rows,[{'name':'fake/kernel32.dll','bytes':8},{'name':'readme.txt','bytes':2}])
 def test_donor_identity_before_parse(self):
  class Wrong:
   def read_bytes(self):return b'not authentic'
  with self.assertRaises(ValueError):m.inspect(Wrong(),[])
if __name__=='__main__':unittest.main()
