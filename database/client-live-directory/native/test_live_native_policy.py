"""Execute native admission boundaries; no Wine/runtime authority is claimed."""
import ctypes
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


class NativePolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        path = Path(cls.temp.name)
        (path / 'fixture.c').write_text('''
#include "coh_live_native_policy.h"
int path_valid(const char *p){return cohLiveGuestPathValid(p);}
int guest(const char *p,char *o){return cohLiveGuestFromDos(p,o);}
int selected(const char *r,const char *g,const char *p,char *o){return cohLiveSelectedGuestPath(r,g,p,o);}
int decimal(const char *s,uint64_t *v){return cohLiveDecimalU64(s,v);}
int hex(const char *s,unsigned char *v){return cohLiveAsciiHex(s,v,16);}
int endpoint(const char *s,unsigned short *v){return cohLiveEndpoint(s,v);}
int final_scope(const char *r,const char *p,const char *f){return cohLiveAuthorizedFinalScope(r,p,f);}
''')
        subprocess.run(['cc', '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-Wno-misleading-indentation', '-shared', '-fPIC',
                        '-I', str(ROOT), str(path / 'fixture.c'), '-o', str(path / 'fixture.so')], check=True)
        cls.lib = ctypes.CDLL(str(path / 'fixture.so'))
        for name in ('path_valid', 'guest', 'selected', 'decimal', 'hex', 'endpoint', 'final_scope'):
            getattr(cls.lib, name).restype = ctypes.c_int
        cls.lib.path_valid.argtypes = [ctypes.c_char_p]
        cls.lib.guest.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
        cls.lib.selected.argtypes = [ctypes.c_char_p] * 3 + [ctypes.c_void_p]
        cls.lib.decimal.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint64)]
        cls.lib.hex.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
        cls.lib.endpoint.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_ushort)]
        cls.lib.final_scope.argtypes = [ctypes.c_char_p]*3

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_guest_path_boundaries_and_dot_aliases(self):
        for value in (b'/state/work/data/fx', b'/game-import/data/scripts.loc', b'/' + b'a' * 1023):
            self.assertEqual(self.lib.path_valid(value), 1)
        for value in (None, b'', b'/', b'/data/', b'/data//fx', b'/data/./fx', b'/data/../fx',
                      b'/data/fx\\a', b'/data/fx:a', b'/data/*', b'/data/\x80', b'/' + b'a' * 1024):
            self.assertEqual(self.lib.path_valid(value), 0, value)

    def test_only_reviewed_z_drive_maps(self):
        out = ctypes.create_string_buffer(1025)
        self.assertEqual(self.lib.guest(b'Z:\\state\\work\\data\\SCRIPTS.LOC', out), 1)
        self.assertEqual(out.value, b'/state/work/data/SCRIPTS.LOC')
        for value in (b'X:\\data\\fx', b'\\\\?\\Z:\\data', b'Z:data', b'Z:\\', b'/data/fx', b'Z:\\data\\..\\fx'):
            self.assertEqual(self.lib.guest(value, out), 0, value)

    def test_selected_branch_only_and_no_whole_path_folding(self):
        out = ctypes.create_string_buffer(1025)
        root = b'/state/Operation/data'
        self.assertEqual(self.lib.selected(root, root, root + b'/SCRIPTS.LOC/Player_Created', out), 1)
        self.assertEqual(out.value, root + b'/scripts.loc/Player_Created')
        self.assertEqual(self.lib.selected(root, root, root + b'/FX/Effects', out), 1)
        self.assertEqual(out.value, root + b'/fx/Effects')
        for gdd, directory in ((b'/state/operation/data', root + b'/fx'),
                               (root, b'/state/operation/data/fx'), (root, root + b'2/fx'),
                               (root, root + b'/scripts'), (root, root + b'/fx2'),
                               (root, root + b'/texture_library'), (root, root)):
            self.assertEqual(self.lib.selected(root, gdd, directory, out), 0)

    def test_u64_canonical_and_overflow(self):
        out = ctypes.c_uint64()
        for value, expected in ((b'0', 0), (b'18446744073709551615', 2**64-1), (b'12345', 12345)):
            self.assertEqual(self.lib.decimal(value, ctypes.byref(out)), 1)
            self.assertEqual(out.value, expected)
        for value in (None, b'', b'00', b'+1', b'-1', b' 1', b'1\n', b'18446744073709551616'):
            self.assertEqual(self.lib.decimal(value, ctypes.byref(out)), 0)

    def test_exact_lowercase_session_hex(self):
        out = ctypes.create_string_buffer(16)
        self.assertEqual(self.lib.hex(b'0123456789abcdef0123456789abcdef', out), 1)
        self.assertEqual(out.raw, bytes.fromhex('0123456789abcdef0123456789abcdef'))
        for value in (None, b'', b'0'*31, b'0'*33, b'A'*32, b'g'*32):
            self.assertEqual(self.lib.hex(value, out), 0)

    def test_endpoint_is_literal_ipv4_loopback_only(self):
        out = ctypes.c_ushort()
        self.assertEqual(self.lib.endpoint(b'127.0.0.1:65535', ctypes.byref(out)), 1)
        self.assertEqual(out.value, 65535)
        for value in (None, b'localhost:1234', b'0.0.0.0:1234', b'127.0.0.2:1234', b'127.0.0.1:0',
                      b'127.0.0.1:01234', b'127.0.0.1:65536', b'127.0.0.1:12/extra'):
            self.assertEqual(self.lib.endpoint(value, ctypes.byref(out)), 0)

    def test_finite_current_import_alias_final_scope_requires_same_branch(self):
        root=b'/state/operation/data'
        request=root+b'/SCRIPTS.LOC/Alias'
        self.assertEqual(self.lib.final_scope(root,request,b'/game-import/data/scripts.loc/Actual'),1)
        self.assertEqual(self.lib.final_scope(root,request,root+b'/scripts.loc/Actual'),1)
        for value in (b'/game-import/data/fx/Actual',b'/game-import/database/scripts.loc/Actual',
                      b'/GAME-IMPORT/data/scripts.loc/Actual',b'/tmp/scripts.loc/Actual',
                      b'/game-import/data/scripts.loc2/Actual'):
            self.assertEqual(self.lib.final_scope(root,request,value),0)


if __name__ == '__main__':
    unittest.main()
