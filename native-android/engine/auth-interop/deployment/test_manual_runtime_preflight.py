import json,struct,types,unittest
from pathlib import Path
# Execute the exact current source, never import a cached project helper.
SCRIPT=Path(__file__).with_name('manual_runtime_preflight.py')
p=types.ModuleType('checked_runtime_preflight');p.__file__=str(SCRIPT.resolve());exec(compile(SCRIPT.read_bytes(),str(SCRIPT),'exec'),p.__dict__)
def image():
 b=bytearray(2048);b[:2]=b'MZ';struct.pack_into('<I',b,60,64);b[64:68]=b'PE\0\0';struct.pack_into('<HH',b,68,0x14c,1);struct.pack_into('<H',b,84,224);struct.pack_into('<H',b,88,0x10b);struct.pack_into('<I',b,144,0x2000);struct.pack_into('<I',b,180,16);struct.pack_into('<IIII',b,320,1536,0x1000,1536,512);return b
def imports():
 b=image();struct.pack_into('<II',b,192,0x1000,40);struct.pack_into('<IIIII',b,512,0x1100,0,0,0x1080,0x1120);b[640:650]=b'DEMO.dll\0\0';struct.pack_into('<III',b,768,0x1140,0x80000007,0);b[832:842]=b'\0\0Example\0';return b
def exports():
 b=image();struct.pack_into('<II',b,184,0x1200,256);struct.pack_into('<IIIIII',b,1040,1,2,1,0x1240,0x1250,0x1260);struct.pack_into('<II',b,1088,0x1300,0x12a0);struct.pack_into('<I',b,1104,0x1270);struct.pack_into('<H',b,1120,0);b[1136:1144]=b'Example\0';b[1184:1197]=b'KERNEL32.Test\0';return b
class RuntimePreflight(unittest.TestCase):
 def test_name_and_ordinal_imports(self):self.assertEqual(p.PE(imports()).imports(),{'demo.dll':[{'name':'Example'},{'ordinal':7}]})
 def test_exports_names_ordinals_forwarders(self):
  e=p.PE(exports()).exports();self.assertEqual(e['Example'],{'ordinal':1,'forwarder':None});self.assertEqual(e['#2']['forwarder'],'KERNEL32.Test')
 def test_parser_wrong_bitness_bounds_and_aliases(self):
  for offset,fmt,value in [(60,'I',0xffffffff),(68,'H',0x8664),(70,'H',0),(88,'H',0x20b),(192,'I',0xffffff00),(768,'I',0x80010001)]:
   b=imports();struct.pack_into('<'+fmt,b,offset,value)
   with self.assertRaises(ValueError):p.PE(b).imports()
  b=imports();struct.pack_into('<H',b,70,2);b[352:392]=b[312:352]
  with self.assertRaises(ValueError):p.PE(b).imports()
 def test_delay_imports_and_export_index_refused(self):
  b=image();struct.pack_into('<II',b,288,0x1200,32)
  with self.assertRaises(ValueError):p.PE(b)
  b=exports();struct.pack_into('<H',b,1120,2)
  with self.assertRaises(ValueError):p.PE(b).exports()
 def test_exported_zero_initialized_data_is_virtual_not_file_read(self):
  b=exports();struct.pack_into('<I',b,320,0x700);struct.pack_into('<I',b,1088,0x1680)
  self.assertIn('Example',p.PE(b).exports())
  struct.pack_into('<I',b,1088,0x1800)
  with self.assertRaises(ValueError):p.PE(b).exports()
 def test_archive_identity_fails_before_zip_parse(self):
  class Wrong:
   def read_bytes(self):return b'not a zip'
  with self.assertRaises(ValueError):p.preflight(Wrong(),Wrong(),b'wrong map')
if __name__=='__main__':unittest.main()
