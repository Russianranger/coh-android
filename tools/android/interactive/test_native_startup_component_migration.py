"""Bounded archive tests using real retained bytes and controlled fixtures.

These tests execute no Game/Map process and do not establish native behavior,
collision parity, device performance or promotion authority.
"""
import copy
import os
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import native_startup_component_migration as migration
import native_startup_metadata_contract as native
from test_native_startup_metadata_contract import fixture


def zip_raw(members):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, raw in members.items(): archive.writestr(name, raw)
    return output.getvalue()


class NativeStartupComponentMigrationTests(unittest.TestCase):
    def test_absent_authorities_stop_before_candidate_file_read(self):
        for kind in ('game', 'mapserver'):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'not frozen'):
                migration.authenticate_materials(kind, dict.fromkeys(native.MATERIAL_ROLES, '/missing'))

    def test_real_game_and_map_archive_migrations_preserve_every_other_member(self):
        for kind in ('game', 'mapserver'):
            original, before, raw, expected = fixture(kind)
            with self.subTest(kind=kind), patch.dict(native.COMPONENT_AUTHORITIES, {kind: expected}):
                migrated, report = migration.migrate_archive(original, kind, raw, expected)
                reader = migration.zip_members if kind == 'game' else migration.game_members
                after, _ = reader(migrated)
                changed = {name for name in before if before[name] != after[name]}
                self.assertEqual(changed, {native.COMPONENTS[kind]['executable'], native.COMPONENTS[kind]['manifest']})
                previous, _ = native.previous_package(native.unique_json(after[native.COMPONENTS[kind]['manifest']]), kind)
                self.assertEqual(native.encoded(previous), before[native.COMPONENTS[kind]['manifest']])
                self.assertFalse(report['shipping_allowed'])
                self.assertFalse(report['runtime_activation_allowed'])
                self.assertFalse(report['behavioral_collision_validated'])
                self.assertFalse(report['physical_timing_validated'])

    def test_candidate_content_and_actual_pe_must_match_frozen_authority(self):
        original, _, raw, expected = fixture('game')
        with patch.dict(native.COMPONENT_AUTHORITIES, {'game': expected}):
            with self.assertRaises(ValueError): migration.migrate_archive(original, 'game', raw+b'x', expected)
            changed = copy.deepcopy(expected)
            changed['native_record']['imports'] = []
            with patch.dict(native.COMPONENT_AUTHORITIES, {'game': changed}), self.assertRaises(ValueError):
                migration.migrate_archive(original, 'game', raw, changed)

    def test_arbitrary_caller_authority_rejected(self):
        original, _, raw, expected = fixture('mapserver')
        changed = copy.deepcopy(expected); changed['compatibility']['fake_cache'] = True
        with patch.dict(native.COMPONENT_AUTHORITIES, {'mapserver': expected}), self.assertRaises(ValueError):
            migration.migrate_archive(original, 'mapserver', raw, changed)

    def test_actual_whole_material_and_member_bytes_bound_independently(self):
        _, _, raw, initial = fixture('game')
        expected = copy.deepcopy(initial)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            paths = {}
            for role in native.MATERIAL_ROLES:
                receipt = native.encoded({'format': 1, 'role': 'controlled_unit_receipt_only',
                    'repository_commit': '1'*40, 'native_process_executed': False})
                members = {role+'.json': receipt}
                if role == 'producer': members['CityOfHeroes.exe'] = raw
                data = zip_raw(members); target = directory/(role+'.zip'); target.write_bytes(data)
                paths[role] = target
                expected['materials'][role] = {'repository_commit': '1'*40, 'run_id': 1,
                    'artifact_id': 1, 'artifact_zip': migration.content_pin(data),
                    'members': {name: migration.content_pin(value) for name, value in members.items()},
                    'required_receipt_values': {role+'.json': {'repository_commit': '1'*40,
                        'native_process_executed': False, 'role': 'controlled_unit_receipt_only'}}}
            with patch.dict(native.COMPONENT_AUTHORITIES, {'game': expected}):
                received, executable = migration.authenticate_materials('game', paths)
                self.assertEqual(received, expected)
                self.assertEqual(executable, raw)
                paths['recovery'].write_bytes(paths['recovery'].read_bytes()+b'x')
                with self.assertRaisesRegex(ValueError, 'artifact bytes differ'):
                    migration.authenticate_materials('game', paths)

    def test_actual_large_Map_qualification_bytes_parse_after_complete_material_authentication(self):
        # These are real >8 MiB JSON/ZIP bytes, explicitly unexecuted fixtures.
        # A source-frozen synthetic authority is local to this size test only.
        _,_,executable,initial=fixture('mapserver')
        expected=copy.deepcopy(initial)
        length=9437282
        prefix=b'{"scope":"unexecuted_material_parser_size_fixture","native_process_executed":false,"padding":"'
        world=prefix+b'x'*(length-len(prefix)-2)+b'"}'
        self.assertEqual(len(world),length)
        with tempfile.TemporaryDirectory() as temporary:
            paths={}
            for role in native.MATERIAL_ROLES:
                name='native-map-world-037-qualification.json' if role=='qualification' else role+'.json'
                body=world if role=='qualification' else native.encoded({'scope':'unexecuted_material_parser_size_fixture',
                    'native_process_executed':False})
                members={name:body}
                if role=='producer':members['MapServer.exe']=executable
                data=zip_raw(members);path=Path(temporary)/(role+'.zip');path.write_bytes(data);paths[role]=path
                expected['materials'][role]={'repository_commit':'1'*40,'run_id':1,'artifact_id':1,
                    'artifact_zip':migration.content_pin(data),'members':{key:migration.content_pin(raw) for key,raw in members.items()},
                    'required_receipt_values':{name:{'scope':'unexecuted_material_parser_size_fixture','native_process_executed':False}}}
            with patch.dict(native.COMPONENT_AUTHORITIES,{'mapserver':expected}):
                received,actual=migration.authenticate_materials('mapserver',paths)
                self.assertEqual(received,expected);self.assertEqual(actual,executable)
        parsed=migration.material_receipt('mapserver','qualification','native-map-world-037-qualification.json',world)
        self.assertEqual(parsed['scope'],'unexecuted_material_parser_size_fixture')
        self.assertFalse(parsed['native_process_executed'])
        self.assertEqual(native.COMPONENT_AUTHORITIES,{'game':None,'mapserver':None})

    def test_world_raw_JSON_size_exception_is_exact_and_preserves_strict_refusal(self):
        name='native-map-world-037-qualification.json'
        large=b'{"padding":"'+b'x'*(8*1024**2)+b'"}'
        for kind,role,member in (('game','qualification',name),('mapserver','recovery',name),
            ('mapserver','producer',name),('mapserver','qualification','unknown-world.json'),
            ('mapserver','qualification','case/'+name)):
            with self.subTest(kind=kind,role=role,name=member),self.assertRaises(ValueError):
                migration.material_receipt(kind,role,member,large)
        oversized=b'{"padding":"'+b'x'*(65*1024**2)+b'"}'
        with self.assertRaisesRegex(ValueError,'Bounded exact Map'):
            migration.material_receipt('mapserver','qualification',name,oversized)
        for raw in (b'{"padding":"'+b'x'*(8*1024**2)+b'","nested":{"key":1,"key":2}}',
            b'{"nested":{"value":NaN}}',b'{"nested":{"value":Infinity}}',b'{"nested":{"value":-Infinity}}',b'{"nested":{"value":1e999}}',b'{"nested":{"value":-1e999}}',b'[]',large.decode()):
            with self.subTest(prefix=str(raw[:40])),self.assertRaises(ValueError):
                migration.material_receipt('mapserver','qualification',name,raw)
        with self.assertRaises(ValueError):native.unique_json(large)

    def test_json_receipt_flags_cannot_override_actual_artifact_identity(self):
        _, _, raw, initial = fixture('game')
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'fake.zip'
            path.write_bytes(zip_raw({'producer.json': native.encoded({'status': 'passed',
                'native_process_executed': True}), 'CityOfHeroes.exe': raw}))
            expected = copy.deepcopy(initial)
            expected['materials']['producer'] = {'repository_commit': '1'*40, 'run_id': 1,
                'artifact_id': 1, 'artifact_zip': {'bytes': 1, 'sha256': 'a'*64},
                'members': {}}
            with patch.dict(native.COMPONENT_AUTHORITIES, {'game': expected}), self.assertRaisesRegex(ValueError, 'artifact bytes differ'):
                migration.authenticate_materials('game', dict.fromkeys(native.MATERIAL_ROLES, path))

    def test_original_Map_producer_native_member_is_bound_to_exact_archive_and_source(self):
        from test_native_startup_metadata_admission import actual_archive_comparison_fixture
        import prepare_native_metadata_qualification_fixtures as fixtures
        _,_,_,_,initial=actual_archive_comparison_fixture()
        expected=copy.deepcopy(initial)
        producer=Path(os.environ['COH_METADATA_RECOVERY'])/fixtures.ARTIFACTS['map_producer']['filename']
        raw=producer.read_bytes();members,_=migration.material_members(raw)
        spec=fixtures.ARTIFACTS['map_producer']
        expected['materials']['producer']={'repository_commit':spec['source'],'run_id':spec['run_id'],
            'artifact_id':spec['artifact_id'],'artifact_zip':migration.content_pin(raw),
            'members':{n:migration.content_pin(b) for n,b in members.items()},
            'native_member':'MapServer-prefetch.exe'}
        with tempfile.TemporaryDirectory() as temporary:
            paths={'producer':producer}
            for role in ('recovery','qualification'):
                body=native.encoded({'scope':'unexecuted_material_layout_fixture','native_process_executed':False})
                data=zip_raw({role+'.json':body});target=Path(temporary)/(role+'.zip');target.write_bytes(data);paths[role]=target
                expected['materials'][role]={'repository_commit':'1'*40,'run_id':1,'artifact_id':1,
                    'artifact_zip':migration.content_pin(data),'members':{role+'.json':migration.content_pin(body)}}
            with patch.dict(native.COMPONENT_AUTHORITIES,{'mapserver':expected}):
                received,executable=migration.authenticate_materials('mapserver',paths)
                self.assertEqual(migration.content_pin(executable),{'bytes':7480832,
                    'sha256':'5927f87fdac50c5a839ac067ccbb34b5dfad6223e579287a66a2f866a7d4b2e6'})
                self.assertEqual(received,expected)
            for key,value in (('native_member','unknown.exe'),('repository_commit','1'*40),('run_id',1),('artifact_id',1)):
                changed=copy.deepcopy(expected);changed['materials']['producer'][key]=value
                with self.subTest(key=key),patch.dict(native.COMPONENT_AUTHORITIES,{'mapserver':changed}),self.assertRaises(ValueError):
                    migration.authenticate_materials('mapserver',paths)
        self.assertEqual(native.COMPONENT_AUTHORITIES,{'game':None,'mapserver':None})

    def test_zip_alias_traversal_symlink_and_oversized_names_refused(self):
        for members in ({'../escape': b'a'}, {'a': b'a', 'A': b'b'}, {'a/b': b'a'}):
            with self.subTest(members=members), self.assertRaises(ValueError): migration.zip_members(zip_raw(members))
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w') as archive:
            entry = zipfile.ZipInfo('alias'); entry.external_attr = (0o120777 << 16)
            archive.writestr(entry, 'target')
        with self.assertRaises(ValueError): migration.zip_members(output.getvalue())

    def test_evidence_layout_supports_297_bounded_relative_members_without_payload_relaxation(self):
        rows={'native-client-paired/case-%03d/receipt.json'%index:b'{"scope":"unexecuted"}' for index in range(297)}
        raw=zip_raw(rows)
        members,_=migration.material_members(raw)
        self.assertEqual(members,rows)
        with self.assertRaises(ValueError):migration.zip_members(raw)
        with self.assertRaises(ValueError):migration.material_members(zip_raw({
            'proof/member-%03d.json'%index:b'{}' for index in range(513)}))

    def test_evidence_empty_logs_are_bound_while_native_payloads_remain_nonempty(self):
        raw=zip_raw({'proof/qualification.json':b'{"scope":"unexecuted"}','proof/stderr.log':b''})
        members,_=migration.material_members(raw)
        self.assertEqual(members['proof/stderr.log'],b'')
        self.assertEqual(migration.content_pin(members['proof/stderr.log']),
            {'bytes':0,'sha256':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'})
        with self.assertRaises(ValueError):migration.zip_members(zip_raw({'CityOfHeroes.exe':b''}))
        with self.assertRaises(ValueError):native.unique_json(members['proof/stderr.log'])

    def test_evidence_path_traversal_aliases_conflicts_and_links_fail_closed(self):
        invalid=({'../escape.json':b'{}'},{'/absolute.json':b'{}'},
            {'a\\b.json':b'{}'},{'C:/drive.json':b'{}'},
            {'Case/a.json':b'{}','case/b.json':b'{}'},
            {'parent':b'{}','parent/child.json':b'{}'},
            {'/'.join(['level']*8)+'/too-deep.json':b'{}'})
        for rows in invalid:
            with self.subTest(rows=rows),self.assertRaises(ValueError):migration.material_members(zip_raw(rows))
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w') as opened:
            entry=zipfile.ZipInfo('proof/link');entry.external_attr=0o120777<<16;opened.writestr(entry,'target')
        with self.assertRaises(ValueError):migration.material_members(output.getvalue())

    def test_tar_link_and_parent_paths_refused(self):
        for name, kind in (('../escape', tarfile.REGTYPE), ('alias', tarfile.SYMTYPE)):
            output = io.BytesIO()
            with tarfile.open(fileobj=output, mode='w:gz') as archive:
                row = tarfile.TarInfo(name); row.type = kind
                row.size = 1 if kind == tarfile.REGTYPE else 0; row.linkname = 'target'
                archive.addfile(row, io.BytesIO(b'a') if row.size else None)
            with self.subTest(name=name), self.assertRaises(ValueError): migration.game_members(output.getvalue())

    def test_symlink_material_paths_cannot_be_resolved_into_accepted_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); actual = root/'actual'; actual.write_bytes(b'x')
            link = root/'link'; link.symlink_to(actual)
            with self.assertRaises(ValueError): migration.read_regular(link)


if __name__ == '__main__': unittest.main()
