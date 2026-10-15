"""Execute all-zone missing-only installation and finite Map 5 isolation.

Small synthetic resources validate filesystem behavior, not rendered fidelity.
The production publication audit separately validates original donor contents.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT/'android/guest'), str(Path(__file__).resolve().parent)]
import zone_asset_package as zones
import client_startup_diagnostic as client
import local_character_server as server


class ZonePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root/'assets'; self.assets.mkdir()
        self.work = self.root/'work'; (self.work/'data').mkdir(parents=True)
        self.ctx = SimpleNamespace(check=mock.Mock(), event=mock.Mock())
        self.payload = {f'data/object_library/kings/new{n}.geo': ('original'+str(n)).encode() for n in range(52)}
        self.payload['data/texture_library/other/new.texture'] = b'original texture'
        self.payload['data/sound/ogg/other/new.ogg'] = b'OggS\x00fixture'
        self.files = {name: self.pin(raw) for name, raw in self.payload.items()}
        with zipfile.ZipFile(self.assets/zones.ARCHIVE, 'w') as archive:
            for name, raw in self.payload.items():
                entry = zipfile.ZipInfo(name); entry.external_attr = (stat.S_IFREG|0o444)<<16
                archive.writestr(entry, raw)
        collision = {n: p for n, p in self.files.items() if n.endswith('.geo')}
        self.document = {'format': 1, 'scope': zones.SCOPE, 'version': zones.VERSION,
            'source_commit': client.SOURCE, 'data_commit': client.DATA,
            'missing_only': True, 'retained_resources_preserved': True, 'original_payloads_verified': True,
            'donor_generated_caches_installed': False,
            'archive': {'filename': zones.ARCHIVE, **self.pin((self.assets/zones.ARCHIVE).read_bytes())},
            'file_count': len(self.files), 'payload_bytes': sum(p['bytes'] for p in self.files.values()),
            'files': self.files, 'files_sha256': hashlib.sha256(zones.canonical(self.files)).hexdigest(),
            'kings_row_collision_files': collision,
            'kings_row_collision_files_sha256': hashlib.sha256(zones.canonical(collision)).hexdigest(),
            'kings_row_source_world_graph_complete': True}
        self.publish()
        zones._PACKAGES.clear(); client._VERIFIED_ASSET_STATES.clear()

    @staticmethod
    def pin(raw):
        return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    def publish(self):
        raw = zones.canonical(self.document)
        (self.assets/zones.MANIFEST).write_bytes(raw)
        owner = {'format': 1, 'scope': client.SCOPE, 'files': {
            zones.MANIFEST: self.pin(raw), zones.ARCHIVE: self.document['archive'].copy()}}
        owner['files'][zones.ARCHIVE].pop('filename')
        (self.assets/'client-manifest.json').write_bytes(zones.canonical(owner))

    def publish_audio(self, payload=None):
        self.audio_payload = payload or {'data/sound/ogg/voices/dialog_hero.ogg': b'OggS\x00dialog fixture',
                                         'data/sound/ogg/music/theme_new.ogg': b'OggS\x00music fixture'}
        with zipfile.ZipFile(self.assets/zones.AUDIO_ARCHIVE, 'w') as archive:
            for name, raw in self.audio_payload.items():
                entry = zipfile.ZipInfo(name); entry.external_attr = (stat.S_IFREG|0o444)<<16
                archive.writestr(entry, raw)
        files = {name: self.pin(raw) for name, raw in self.audio_payload.items()}
        self.audio_document = {key: value for key, value in self.document.items() if not key.startswith('kings_row_')}
        self.audio_document.update(scope=zones.AUDIO_SCOPE, files=files, file_count=len(files),
            payload_bytes=sum(pin['bytes'] for pin in files.values()),
            files_sha256=hashlib.sha256(zones.canonical(files)).hexdigest(),
            archive={'filename': zones.AUDIO_ARCHIVE, **self.pin((self.assets/zones.AUDIO_ARCHIVE).read_bytes())},
            base_zones_archive_pin={key: self.document['archive'][key] for key in ('bytes', 'sha256')},
            combined_native_sound_inventory={'unique_names': len(files)+1, 'duplicate_basename_count': 0,
                'native_80_byte_path_bound_verified': True, 'prior_zone_sounds_preserved': 1,
                'additional_original_sounds': len(files)})
        self.write_audio_manifest()

    def write_audio_manifest(self):
        raw = zones.canonical(self.audio_document)
        (self.assets/zones.AUDIO_MANIFEST).write_bytes(raw)
        owner = json.loads((self.assets/'client-manifest.json').read_bytes())
        owner['files'][zones.AUDIO_MANIFEST] = self.pin(raw)
        owner['files'][zones.AUDIO_ARCHIVE] = {key: self.audio_document['archive'][key] for key in ('bytes', 'sha256')}
        (self.assets/'client-manifest.json').write_bytes(zones.canonical(owner))

    def test_client_installs_all_original_resources_once(self):
        receipt = zones.install(self.work, self.assets, self.ctx)
        self.assertEqual(receipt['installed_files'], 54)
        for name, raw in self.payload.items():
            path = self.work/name
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(path.stat().st_mode & 0o777, 0o444)
        with mock.patch.object(zones.zipfile, 'ZipFile', side_effect=AssertionError('warm ZIP read')):
            reused = zones.install(self.work, self.assets, self.ctx)
        self.assertTrue(reused['fingerprint_reused']); self.assertEqual(reused['installed_files'], 0)

    def test_new_runtime_sources_rebind_exact_world_and_audio_output_proofs(self):
        self.publish_audio()
        for audio in (False, True):
            zones.install(self.work, self.assets, self.ctx, audio=audio)
        for name in (zones.ARCHIVE, zones.MANIFEST, zones.AUDIO_ARCHIVE, zones.AUDIO_MANIFEST):
            path = self.assets / name; raw = path.read_bytes()
            path.unlink(); path.write_bytes(raw)
            client._VERIFIED_ASSET_STATES[str(path)] = (self.pin(raw), client.asset_fingerprint(path))
        with mock.patch.object(zones.world, 'verify_target', side_effect=AssertionError('duplicate output hash')), \
                mock.patch.object(zones.zipfile, 'ZipFile', side_effect=AssertionError('duplicate archive read')):
            for audio in (False, True):
                result = zones.install(self.work, self.assets, self.ctx, audio=audio)
                self.assertTrue(result['source_generation_rebound'])
                self.assertTrue(result['fingerprint_reused'])
                self.assertEqual(0, result['installed_files'])

    def test_rebound_sources_do_not_authorize_rewritten_output_or_unverified_archive(self):
        zones.install(self.work, self.assets, self.ctx)
        for name in (zones.ARCHIVE, zones.MANIFEST):
            path = self.assets / name; raw = path.read_bytes()
            path.unlink(); path.write_bytes(raw)
        with mock.patch.object(zones.world, 'verify_target', wraps=zones.world.verify_target) as verify:
            result = zones.install(self.work, self.assets, self.ctx)
        self.assertFalse(result['fingerprint_reused'])
        self.assertEqual(len(self.files), verify.call_count)
        for name in (zones.ARCHIVE, zones.MANIFEST):
            path = self.assets / name; raw = path.read_bytes()
            path.unlink(); path.write_bytes(raw)
            client._VERIFIED_ASSET_STATES[str(path)] = (self.pin(raw), client.asset_fingerprint(path))
        target = self.work / next(iter(self.files)); before = target.stat()
        target.chmod(0o644); target.write_bytes(b'x' * before.st_size); target.chmod(0o444)
        os.utime(target, ns=(before.st_mtime_ns, before.st_mtime_ns))
        with self.assertRaisesRegex(client.base.DiagnosticError, 'conflicts'):
            zones.install(self.work, self.assets, self.ctx)

    def test_kings_server_gets_exact_geometry_subset_only(self):
        receipt = zones.install(self.work, self.assets, self.ctx, collision_only=True)
        self.assertEqual(receipt['installed_files'], 52)
        self.assertFalse((self.work/'data/texture_library').exists())
        self.assertFalse((self.work/'data/sound').exists())
        self.assertEqual({p.relative_to(self.work).as_posix() for p in (self.work/'data').rglob('*') if p.is_file()},
                         set(self.document['kings_row_collision_files']))

    def test_present_conflicting_file_is_preserved_and_rejected(self):
        path = self.work/next(iter(self.payload)); path.parent.mkdir(parents=True)
        path.write_bytes(b'incorrect0'); path.chmod(0o444)
        os.utime(path, (client.CACHE_EPOCH, client.CACHE_EPOCH))
        with self.assertRaises((ValueError, client.base.DiagnosticError)):
            zones.install(self.work, self.assets, self.ctx)
        self.assertEqual(path.read_bytes(), b'incorrect0')

    def test_symlink_destination_and_linked_source_are_refused(self):
        outside = self.root/'outside'; outside.mkdir()
        (self.work/'data/object_library').symlink_to(outside, target_is_directory=True)
        with self.assertRaises((ValueError, client.base.DiagnosticError)):
            zones.install(self.work, self.assets, self.ctx)
        self.assertEqual(list(outside.iterdir()), [])
        source = self.assets/zones.ARCHIVE; saved = self.root/'source.zip'; source.rename(saved); source.symlink_to(saved)
        with self.assertRaises(client.base.DiagnosticError): zones.package(self.assets)

    def test_changed_manifest_and_incomplete_collision_refused(self):
        (self.assets/zones.MANIFEST).write_bytes(b'{}')
        with self.assertRaises(client.base.DiagnosticError): zones.package(self.assets)
        self.document['kings_row_collision_files'].pop(next(iter(self.document['kings_row_collision_files'])))
        self.publish()
        with self.assertRaises(client.base.DiagnosticError): zones.package(self.assets)

    def test_unsafe_inventory_refused_even_with_matching_outer_pin(self):
        self.document['files']['data/../outside.geo'] = self.document['files'].pop(next(iter(self.files)))
        self.document['files_sha256'] = hashlib.sha256(zones.canonical(self.document['files'])).hexdigest()
        self.publish()
        with self.assertRaises(client.base.DiagnosticError): zones.package(self.assets)

    def test_verified_same_inode_skips_duplicate_archive_hash_only(self):
        pin = self.document['archive'].copy(); pin.pop('filename')
        client._VERIFIED_ASSET_STATES[str(self.assets/zones.ARCHIVE)] = (pin, client.asset_fingerprint(self.assets/zones.ARCHIVE))
        with mock.patch.object(zones.world, 'hash_stream', side_effect=AssertionError('duplicate whole archive hash')):
            self.assertEqual(zones.install(self.work, self.assets, self.ctx)['installed_files'], 54)
        archive = self.assets/zones.ARCHIVE
        raw = archive.read_bytes(); archive.write_bytes(raw)
        self.assertFalse(client.verified_asset_matches(archive, pin))

    def test_hardlinked_readonly_archives_keep_shared_source_unchanged(self):
        source = self.assets/zones.ARCHIVE; source.chmod(0o444)
        shared = self.root/'shared-object'; os.link(source, shared)
        self.assertEqual(zones.install(self.work, self.assets, self.ctx)['installed_files'], 54)
        self.assertEqual(shared.read_bytes(), source.read_bytes())
        self.assertEqual(shared.stat().st_nlink, 2)

    def test_atlas_mirror_excludes_all_zone_resources_on_later_cold_start(self):
        self.publish_audio()
        zones.install(self.work, self.assets, self.ctx)
        zones.install(self.work, self.assets, self.ctx, audio=True)
        keep = self.work/'data/object_library/atlas.geo'; keep.write_bytes(b'accepted atlas'); keep.chmod(0o444)
        imported = self.root/'import'; imported.mkdir()
        value = server.LocalCharacterServer.__new__(server.LocalCharacterServer)
        value.owner = SimpleNamespace(work=self.work, args=SimpleNamespace(game_data=imported))
        value.ctx = self.ctx; value.creation_report = {}
        value.zone_asset_exclusions = {name[5:] for name in set(self.files)|set(self.audio_payload)}
        target = self.root/'atlas/data'
        receipt = value.stage_map_data(self.work/'data', target)
        actual = {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
        self.assertEqual(actual, {'object_library/atlas.geo'})
        self.assertEqual(receipt['linked_immutable_files'], 1)
        self.assertTrue((target/'object_library/atlas.geo').is_symlink())

    def test_combined_client_zone_and_audio_fresh_then_reuse(self):
        self.publish_audio()
        zones.install(self.work, self.assets, self.ctx)
        before = {name: (self.work/name).read_bytes() for name in self.files}
        receipt = zones.install(self.work, self.assets, self.ctx, audio=True)
        self.assertEqual(receipt['scope'], 'all_zone_client_audio')
        self.assertEqual(receipt['installed_files'], 2)
        self.assertEqual({name: (self.work/name).read_bytes() for name in self.files}, before)
        for name, raw in self.audio_payload.items(): self.assertEqual((self.work/name).read_bytes(), raw)
        with mock.patch.object(zones.zipfile, 'ZipFile', side_effect=AssertionError('warm ZIP read')):
            self.assertTrue(zones.install(self.work, self.assets, self.ctx)['fingerprint_reused'])
            self.assertTrue(zones.install(self.work, self.assets, self.ctx, audio=True)['fingerprint_reused'])

    def test_audio_native_basename_conflict_is_rejected(self):
        self.publish_audio({'data/sound/ogg/somewhere/new.ogg': b'OggS\x00duplicate basename'})
        with self.assertRaisesRegex(client.base.DiagnosticError, 'native sound names'):
            zones.install(self.work, self.assets, self.ctx, audio=True)
        self.assertFalse((self.work/'data/sound').exists())

    def test_audio_scope_and_native_path_bound_are_enforced(self):
        for name in ('data/object_library/new.geo', 'data/sound/ogg/'+'x'*80+'.ogg'):
            self.publish_audio({name: b'OggS\x00fixture'})
            with self.assertRaises(client.base.DiagnosticError): zones.package(self.assets, audio=True)

    def test_audio_wrong_base_zone_pin_and_incomplete_pair_rejected(self):
        self.publish_audio()
        self.audio_document['base_zones_archive_pin']['sha256'] = 'f'*64
        self.write_audio_manifest()
        with self.assertRaises(client.base.DiagnosticError): zones.package(self.assets, audio=True)
        (self.assets/zones.AUDIO_ARCHIVE).unlink()
        with self.assertRaises(client.base.DiagnosticError): zones.present(self.assets, audio=True)

    def test_audio_cannot_be_selected_as_collision_overlay(self):
        self.publish_audio()
        with self.assertRaises(client.base.DiagnosticError):
            zones.install(self.work, self.assets, self.ctx, audio=True, collision_only=True)

    def test_kings_runtime_isolated_and_warm_cache_avoids_second_mirror(self):
        zones.install(self.work, self.assets, self.ctx)
        data = self.work/'data'
        keep = data/'object_library/atlas.geo'; keep.write_bytes(b'accepted atlas'); keep.chmod(0o444)
        for name in ('bin', 'geobin', 'server/db'):
            (data/name).mkdir(parents=True, exist_ok=True)
        (data/'server/db/servers.cfg').write_text('schema')
        imported = self.root/'import'; imported.mkdir()
        schema = self.root/'schema'; (schema/'data/server/db').mkdir(parents=True)
        (schema/'data/server/db/servers.cfg').write_text('schema')
        state = self.root/'state'; state.mkdir()
        identity = {'format': 2, 'source_data': str(data), 'source_device': data.stat().st_dev,
            'source_inode': data.stat().st_ino, 'source_roots': [
                {'path': str(p), 'identity': server.server_data_cache.fingerprint(p, directory=True)}
                for p in (self.work, imported)]}

        def instance(session):
            value = server.LocalCharacterServer.__new__(server.LocalCharacterServer)
            value.owner = SimpleNamespace(work=self.work, root=state,
                args=SimpleNamespace(game_data=imported, assets=self.assets, session_id=session),
                cleanup_status={'wine_prefix_stopped': True, 'owned_processes_reaped': True})
            value.ctx = SimpleNamespace(check=mock.Mock(), event=mock.Mock(), report={})
            value.creation_report = {}; value.zone_asset_document = zones.package(self.assets)
            value.zone_asset_exclusions = {n[5:] for n in self.files}
            value.kings_row_beacon_graph = {'verified': True, 'map_id': 5}
            value.kings_row_beacon_lock = {'manifest': {'bytes': 1, 'sha256': 'f'*64}}
            value.runtime = state/('session-'+session)
            (value.runtime/'data/server/db').mkdir(parents=True)
            (value.runtime/'data/server/db/servers.cfg').write_text('current credentials '+session)
            (value.runtime/'MapServer.exe').write_bytes(b'fixture native closure')
            value.map_package = {'files': {'MapServer.exe': self.pin(b'fixture native closure')}}
            value.data_cache = SimpleNamespace(identity=identity)
            value.schema_dir = schema; value.schema = {'files': {'data/server/db/servers.cfg': {}}}
            return value

        with mock.patch('server_cache_package.verify_mapserver_compatibility', return_value={'verified': True}), \
             mock.patch('server_cache_package.build_expected_identity', return_value={}), \
             mock.patch('server_cache_package.install', return_value={'installed_files': 1}), \
             mock.patch('server_animation_package.install', return_value={'installed_files': 1}), \
             mock.patch('kings_row_beacon_package.install', return_value={'verified': True, 'map_id': 5}):
            first = instance('1'*32)
            prepared = first.prepare_kings_row_runtime()
            king = prepared['runtime']
            self.assertNotEqual(king, first.runtime)
            self.assertEqual(len(list((king/'data/object_library/kings').glob('*.geo'))), 52)
            self.assertFalse((first.runtime/'data/object_library/kings').exists())
            self.assertEqual((king/'data/server/db/servers.cfg').read_text(), 'current credentials '+'1'*32)
            self.assertIs(first.prepare_kings_row_runtime(), prepared)
            first.kings_row_data_cache.release(king/'data', first.owner.cleanup_status)
            second = instance('2'*32)
            with mock.patch.object(second, 'stage_map_data', side_effect=AssertionError('warm full data mirror')):
                reused = second.prepare_kings_row_runtime()
            self.assertTrue(reused['preparation']['server_data_cache']['reused'])
            self.assertEqual((reused['runtime']/'data/server/db/servers.cfg').read_text(), 'current credentials '+'2'*32)
            self.assertEqual(reused['preparation']['geometry']['installed_files'], 0)


if __name__ == '__main__':
    unittest.main()
