"""Private-server staging: real ZIP/hash/merge paths, miniature trust fixture."""
import ast
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'armport/scripts'))
import server_atlas_data as server


class ServerAtlasData(unittest.TestCase):
    def setUp(self):
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.source = self.root / 'source'; self.source.mkdir()
        self.runtime = self.root / 'runtime'; self.data = self.runtime / 'data'
        self.data.mkdir(parents=True)
        self.name = 'data/object_library/atlas/terrain.geo'
        self.payload = b'geometry fixture'
        self.document = {'file_count': 1, 'payload_bytes': len(self.payload), 'files': {
            self.name: {'bytes': len(self.payload), 'sha256': hashlib.sha256(self.payload).hexdigest()}}}
        self.manifest = self.root / 'reviewed.json'
        self.manifest.write_text(json.dumps(self.document))
        self.archive = self.source / 'atlas-world-supplement.zip'
        with zipfile.ZipFile(self.archive, 'w') as z: z.writestr(self.name, self.payload)

    def stage(self):
        # Only replace the production archive identity with this tiny fixture;
        # actual unpacking, per-file hashing, collision checks and merge execute.
        with patch.object(server.atlas, 'verify_inputs', return_value=self.document):
            return server.stage(self.source, self.data, self.manifest)

    def test_case_join_preserves_configuration_and_rechecks_identical_collision(self):
        folder = self.data / 'Object_Library/Atlas'; folder.mkdir(parents=True)
        (folder / 'terrain.txt').write_bytes(b'original text')
        config = self.data / 'server/db/servers.cfg'; config.parent.mkdir(parents=True)
        config.write_bytes(b'original config')
        result = self.stage()
        self.assertEqual((folder / 'terrain.geo').read_bytes(), self.payload)
        self.assertFalse((self.data / 'object_library').exists())
        self.assertEqual(config.read_bytes(), b'original config')
        self.assertEqual(result['merged_tree']['case_duplicates'], 0)
        self.assertFalse(result['server_binaries_changed'])
        self.assertFalse(result['rendered_world_verified'])
        self.assertEqual(self.stage()['matching_collisions'], 1)

    def test_conflict_rejected_before_new_bytes(self):
        folder = self.data / 'OBJECT_LIBRARY/ATLAS'; folder.mkdir(parents=True)
        original = folder / 'TERRAIN.GEO'; original.write_bytes(b'different')
        with self.assertRaisesRegex(ValueError, 'earlier data'): self.stage()
        self.assertEqual(original.read_bytes(), b'different')
        self.assertEqual(list(self.runtime.glob('armport-atlas-*')), [])

    def test_bad_hash_extra_member_and_forbidden_configuration_fail(self):
        self.document['files'][self.name]['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'digest'): self.stage()
        self.assertEqual(list(self.data.iterdir()), [])
        with zipfile.ZipFile(self.archive, 'a') as z: z.writestr('data/extra.geo', b'extra')
        with self.assertRaisesRegex(ValueError, 'inventory'): self.stage()
        name = 'data/server/db/servers.cfg'
        self.document['files'] = {name: {'bytes':len(self.payload),'sha256':hashlib.sha256(self.payload).hexdigest()}}
        with zipfile.ZipFile(self.archive, 'w') as z: z.writestr(name, self.payload)
        with self.assertRaisesRegex(ValueError, 'Unsafe'): self.stage()
        self.assertEqual(list(self.data.iterdir()), [])

    def test_production_identity_rejects_fixture_without_copying(self):
        tools = self.root / 'tools'; tools.mkdir()
        with self.assertRaises(ValueError): server.copy_inputs(self.source, tools)
        self.assertEqual(list(tools.iterdir()), [])

    def test_guest_never_uses_links_and_copied_bytes_survive_temp_removal(self):
        with patch.object(server.smoke_run.os, 'link', side_effect=AssertionError('PRoot link2symlink')):
            self.stage()
        target=self.data/'object_library/atlas/terrain.geo'
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.read_bytes(),self.payload)
        self.assertEqual(list(self.runtime.glob('armport-atlas-*')),[])

    def test_real_guest_executes_staging_after_base_before_any_service(self):
        calls = []
        class Stop(Exception): pass
        class Original:
            runtime = self.runtime
            game = {}
            ctx = SimpleNamespace(stage=lambda *a: calls.append(a[0]), passed=lambda **k: calls.append('staged'))
            def prepare_runtime(self): calls.append('base')
            def initialize(self): calls.append('initialize'); raise Stop()
        node = next(n for n in ast.parse((ROOT/'armport/server/armport_game_guest.py').read_text()).body
                    if isinstance(n,ast.ClassDef) and n.name=='ArmPortGame')
        def stage(*args):
            calls.append('supplement')
            self.assertEqual(args[1],self.data)
            return {'files':2877}
        ns = dict(gd=SimpleNamespace(GameDiagnostic=Original), SERVER_OUTPUT_LIMIT=8*1024**2,
                  Path=Path, server_atlas_data=SimpleNamespace(stage=stage))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<actual guest>','exec'),ns)
        with self.assertRaises(Stop): ns['ArmPortGame']().execute()
        self.assertEqual(calls,['base','armport_server_atlas_supplement','supplement','staged','initialize'])
        calls.clear()
        ns['server_atlas_data'].stage=lambda *a: (_ for _ in ()).throw(ValueError('bad input'))
        with self.assertRaisesRegex(ValueError,'bad input'): ns['ArmPortGame']().execute()
        self.assertEqual(calls,['base','armport_server_atlas_supplement'])

    def test_workflow_passes_the_existing_client_archive_and_host_copies_helpers(self):
        workflow=(ROOT/'.github/workflows/armport-build.yml').read_text()
        self.assertIn('--atlas-supplement "$RUNNER_TEMP/atlas-supplement"', workflow)
        host=(ROOT/'armport/server/armport_game_host.py').read_text()
        self.assertIn("server_atlas_data.copy_inputs(a.atlas_supplement, work / 'm3-tools')",host)
        for name in ('server_atlas_data.py','stage_atlas_supplement.py','smoke_run.py'):
            self.assertIn(repr(name),host)
