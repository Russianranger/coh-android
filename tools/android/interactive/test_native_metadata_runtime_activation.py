"""Dormant adapters under explicit unexecuted authority fixtures; no native boot."""
import copy
import io
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock
import zipfile

from test_native_startup_metadata_contract import fixture, package_fixture
import native_startup_metadata_contract as native
import native_startup_component_migration as migration
import client_gpu_profile as gpu
import client_startup_diagnostic as startup
import native_startup_metadata_admission as admission
import test_texture_header_index as textures
import character_reopen_diagnostic as reopen
import json
import hashlib
import os


def activation_fixture(kind, compatibility=None, source_compatibility=None):
    _, members, raw, original = fixture(kind)
    expected = copy.deepcopy(original)
    expected['compatibility'] = copy.deepcopy(compatibility or {})
    expected['materials']['producer'] = {'scope': 'unexecuted_controlled_unit_fixture',
        'repository_commit': 'e'*40, 'run_id': 3, 'artifact_id': 4,
        'artifact_zip': {'bytes': 5, 'sha256': 'f'*64}, 'members': {}}
    if source_compatibility is not None:
        expected['source_compatibility'] = copy.deepcopy(source_compatibility)
    receipt_pin = {'bytes': 123, 'sha256': 'a'*64}
    claims = {'scope': 'unexecuted_controlled_unit_fixture', 'fixture_passed': True}
    artifact_pin = {'bytes': 456, 'sha256': 'b'*64}
    expected['materials']['qualification'] = {'repository_commit': 'c'*40,
        'run_id': 1, 'artifact_id': 2, 'artifact_zip': artifact_pin,
        'members': {'fixture-qualification.json': receipt_pin},
        'required_receipt_values': {'fixture-qualification.json': claims}}
    with patch.dict(native.COMPONENT_AUTHORITIES, {kind: expected}):
        package = native.unique_json(migration.wrap_manifest(
            members[native.COMPONENTS[kind]['manifest']], kind, expected))
    review = {'format': 1, 'kind': kind,
        'component_authority_sha256': native.canonical_sha(expected),
        'qualification_artifact_zip': artifact_pin,
        'qualification_receipts': {'fixture-qualification.json': {'pin': receipt_pin,
            'required_values': claims}}, 'qualified_maps': [1, 5] if kind == 'mapserver' else [],
        'attempt_environment': native.ATTEMPT_ENVIRONMENTS[kind],
        'scope': {'old_native_producer_relabelled': False,
            'behavioral_collision_validated': False, 'physical_timing_validated': False}}
    return package, expected, review, raw


class NativeMetadataRuntimeActivationTests(unittest.TestCase):
    def enable(self, kind, expected, review):
        self.enterContext(patch.dict(native.COMPONENT_AUTHORITIES, {kind: expected}))
        self.enterContext(patch.dict(native.REVIEWED_EXECUTION_AUTHORITIES, {kind: review}))
        self.enterContext(patch.object(native, 'ACTIVATION_IMPLEMENTED', True))

    def executable(self, kind, raw):
        work = Path(self.enterContext(tempfile.TemporaryDirectory()))
        path = work / native.COMPONENTS[kind]['executable']
        path.write_bytes(raw)
        return path

    def test_production_authorities_reviews_and_execution_remain_closed(self):
        self.assertFalse(native.ACTIVATION_IMPLEMENTED)
        self.assertEqual(native.COMPONENT_AUTHORITIES, {'game': None, 'mapserver': None})
        self.assertEqual(native.REVIEWED_EXECUTION_AUTHORITIES, {'game': None, 'mapserver': None})
        package, expected, _, _ = activation_fixture('game')
        with patch.dict(native.COMPONENT_AUTHORITIES, {'game': expected}), self.assertRaisesRegex(ValueError, 'disabled'):
            native.runtime_admission(package, 'game')

    def test_retained_path_removes_inherited_switch_without_new_authority(self):
        for kind in ('game', 'mapserver'):
            env = {native.ATTEMPT_ENVIRONMENTS[kind]: '1', 'WINEPREFIX': 'retained'}
            result = native.apply_attempt_environment({}, kind, None, env)
            self.assertIsNone(result)
            self.assertEqual(env, {'WINEPREFIX': 'retained'})

    def test_exact_current_owned_bytes_and_separate_old_producer_admitted_in_fixture(self):
        package, expected, review, raw = activation_fixture('game')
        self.enable('game', expected, review)
        path = self.executable('game', raw)
        result = native.runtime_admission(package, 'game', path)
        self.assertEqual(result['previous_consumer_sha256'],
            '5f9597fac6e5c4eb2bf6ab091a8b2b5d71c341371da04dc135cef7e5fe00010b')
        self.assertEqual(native.encoded(result['previous_package']), fixture('game')[1]['client-package.json'])
        self.assertFalse(result['physical_timing_validated'])
        env = {'COH_CLIENT_FOLDER_METADATA_SORT': 'untrusted', 'DISPLAY': ':99'}
        original = dict(env)
        proof = native.apply_attempt_environment(package, 'game', path, env)
        self.assertEqual(env['COH_CLIENT_FOLDER_METADATA_SORT'], '1')
        self.assertEqual(proof['current_consumer_sha256'], expected['native_record']['sha256'])
        self.assertEqual(original['COH_CLIENT_FOLDER_METADATA_SORT'], 'untrusted')

    def test_current_bytes_change_refuses_opt_in_before_attempt(self):
        package, expected, review, raw = activation_fixture('game')
        self.enable('game', expected, review)
        path = self.executable('game', raw+b'corrupt')
        env = {'COH_CLIENT_FOLDER_METADATA_SORT': '1'}
        with self.assertRaises(ValueError): native.apply_attempt_environment(package, 'game', path, env)
        self.assertNotIn('COH_CLIENT_FOLDER_METADATA_SORT', env)

    def test_review_receipt_claim_pin_and_numeric_alias_tamper_rejected(self):
        package, expected, review, _ = activation_fixture('game')
        variants = []
        for field, value in (('component_authority_sha256', '9'*64), ('format', True),
                ('qualification_artifact_zip', {'bytes': True, 'sha256': 'b'*64}),
                ('qualification_receipts', {}), ('qualified_maps', [1])):
            changed = copy.deepcopy(review); changed[field] = value; variants.append(changed)
        changed = copy.deepcopy(review)
        changed['qualification_receipts']['fixture-qualification.json']['required_values']['fixture_passed'] = 1
        variants.append(changed)
        changed = copy.deepcopy(review); changed['scope']['physical_timing_validated'] = 0
        variants.append(changed)
        with patch.object(native, 'ACTIVATION_IMPLEMENTED', True), patch.dict(native.COMPONENT_AUTHORITIES, {'game': expected}):
            for changed in variants:
                with self.subTest(changed=changed), patch.dict(native.REVIEWED_EXECUTION_AUTHORITIES, {'game': changed}), self.assertRaises(ValueError):
                    native.runtime_admission(package, 'game')

    def warm_worktree(self, invalid_bridge=False):
        """Actual .36 native bytes, two controlled imported textures, no native process."""
        root = Path(self.enterContext(tempfile.TemporaryDirectory(prefix='coh-metadata-work-unit-')))
        work_root=root/'worktrees';work_root.mkdir();assets=root/'assets';assets.mkdir();data=root/'imported';data.mkdir()
        donor=Path(os.environ.get('COH_ZONE_STARTUP_TEST_DONOR_APK',
            '/workspace/scratch/5d16603ca7ff/publication-037-evidence/COH-Atlas-Gameplay-0.13.36.apk'))
        with zipfile.ZipFile(donor) as opened:
            for name in ('client-runtime.zip','client-prerequisites.zip'):
                (assets/name).write_bytes(opened.read('assets/runtime/'+name))
        previous=native.unique_json(fixture('game')[1]['client-package.json'])
        cache_source=Path(os.environ.get('COH_FX_TEST_CLIENT_CACHES',
            '/workspace/scratch/5d16603ca7ff/native037-recovery/public-asset-cache-donor/client-caches.zip'))
        cached=migration.read_regular(cache_source.absolute())
        self.assertEqual(migration.content_pin(cached),previous['native_responsiveness']['receipt']['retained_cache']['archive'])
        (assets/'client-caches.zip').write_bytes(cached)
        (assets/'native-responsiveness.json').write_bytes(native.encoded(previous['native_responsiveness']['receipt']))
        imported={'generation':'generation-'+'a'*32,'receipt_sha256':'5'*64,'contract_sha256':'4'*64,
            'file_count':173011,'total_bytes':2977730517}
        inputs={'format':1,'source_data':str(data),'import':imported,
            'cache_archive_sha256':startup.base.file_hash(assets/'client-caches.zip'),
            'prerequisites_archive_sha256':startup.base.file_hash(assets/'client-prerequisites.zip'),
            'prerequisites_manifest_sha256':startup.PREREQUISITES_MANIFEST_SHA,
            'normalized_mtime_epoch':startup.CACHE_EPOCH}
        old_content=startup.identity_sha256({'data':inputs,'native':startup.native_closure_identity(previous)})
        work=work_root/('client-work-'+old_content[:24]);work.mkdir();(work/'tools').mkdir();(work/'data').mkdir()
        for name in startup.PRIVATE_CACHE_ROOTS:(work/'data'/name).mkdir(parents=True,exist_ok=True)
        for name,body in fixture('game')[1].items():
            if name!='client-package.json':(work/name).write_bytes(body)
        with zipfile.ZipFile(assets/'client-prerequisites.zip') as opened:
            for name in startup.PREREQUISITES:
                target=work/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(opened.read(name))
                os.utime(target,(startup.CACHE_EPOCH,startup.CACHE_EPOCH));target.chmod(0o400)
        folder=work/'data/texture_library/test';folder.mkdir(parents=True)
        for name in ('a','b'):
            leaf=data/(name+'.texture');leaf.write_bytes(textures.texture(name,b'controlled-mip'));leaf.chmod(0o444)
            (folder/leaf.name).symlink_to(leaf)
        generated=work/'data/bin/after-play.bin';generated.write_bytes(b'preserved private cache')
        supplement=work/'data/object_library/qualified.geo';supplement.parent.mkdir();supplement.write_bytes(b'preserved world supplement')
        server=root/'owned-server-link';server.symlink_to(supplement)
        saved=dict(inputs,package_sha256=startup.base.file_hash(assets/'client-runtime.zip'),
            content_identity_sha256=old_content,worktree_key=work.name,verified_legacy_receipts=[])
        (work/'client-work.json').write_text(json.dumps(saved,indent=2)+'\n')
        context=textures.Context({'client_worktree':dict(saved,reused=True)})
        _,_=textures.module.prepare(work,imported,previous['files']['CityOfHeroes.exe']['sha256'],context)
        closure={name:{'bytes':100,'sha256':'8'*64} for name in native.TEXTURE_SOURCE_PATHS}
        recipe={name:inputs[name] for name in ('cache_archive_sha256','prerequisites_archive_sha256',
            'prerequisites_manifest_sha256','normalized_mtime_epoch')}
        recipe.update(import_contract_sha256='4'*64,imported_file_count=173011,imported_total_bytes=2977730517)
        bridge={'policy':'exact_verified_input_recipe_and_unchanged_texture_schema',
            'previous_executable_sha256':previous['files']['CityOfHeroes.exe']['sha256'],
            'client_executable_sha256':fixture('game')[3]['native_record']['sha256'],
            'texture_header_struct_bytes':32,'unchanged_texture_source_pins':closure,'immutable_input_recipe':recipe}
        if invalid_bridge:bridge['immutable_input_recipe']['prerequisites_archive_sha256']='0'*64
        package,expected,review,raw=activation_fixture('game',{'texture_header_index':bridge},
            {'previous_texture_source_pins':closure,'current_texture_source_pins':closure})
        self.enable('game',expected,review)
        migrated,_=migration.migrate_archive(fixture('game')[0],'game',raw,expected)
        (assets/'client-runtime.zip').write_bytes(migrated)
        return root,work_root,work,assets,data,imported,context,package,(generated,supplement,server)

    def test_worktree_preflight_failure_preserves_executable_receipt_index_and_every_input(self):
        root,work_root,work,assets,data,imported,context,_,extra=self.warm_worktree(invalid_bridge=True)
        paths=[work/'CityOfHeroes.exe',work/'client-work.json',work/textures.module.PACK,work/textures.module.MARKER,*extra]
        before={str(path):(path.lstat().st_ino,path.lstat().st_mtime_ns,path.read_bytes(),os.readlink(path) if path.is_symlink() else None) for path in paths}
        with patch.object(startup.os,'replace',side_effect=AssertionError('Native was replaced before bridge validation')), \
                patch.object(startup.base,'private_write',side_effect=AssertionError('Receipt changed before bridge validation')), self.assertRaisesRegex(ValueError,'immutable texture input recipe'):
            startup.prepare_worktree(work_root,data,assets,imported,context)
        self.assertEqual(before,{str(path):(path.lstat().st_ino,path.lstat().st_mtime_ns,path.read_bytes(),os.readlink(path) if path.is_symlink() else None) for path in paths})

    def test_actual_worktree_upgrade_and_index_rebind_preserve_payload_caches_links_and_root(self):
        root,work_root,work,assets,data,imported,context,package,extra=self.warm_worktree()
        originals={str(path):(path.lstat().st_ino,path.lstat().st_mtime_ns,path.read_bytes(),os.readlink(path) if path.is_symlink() else None) for path in extra}
        pack_before=(work/textures.module.PACK).read_bytes()
        with patch.object(startup.os,'scandir',side_effect=AssertionError('Warm tree was mirrored again')):
            selected,report=startup.prepare_worktree(work_root,data,assets,imported,context)
        self.assertEqual(selected,work);self.assertTrue(report['native_executable_upgraded'])
        self.assertEqual(originals,{str(path):(path.lstat().st_ino,path.lstat().st_mtime_ns,path.read_bytes(),os.readlink(path) if path.is_symlink() else None) for path in extra})
        self.assertEqual(startup.base.file_hash(work/'CityOfHeroes.exe'),package['files']['CityOfHeroes.exe']['sha256'])
        valid_proof=copy.deepcopy(report['native_texture_index_migration'])
        context.report['client_worktree']=report
        with patch.object(textures.module,'make_pack',side_effect=AssertionError('Header payload decoded again')):
            result,_=textures.module.prepare(work,imported,package['files']['CityOfHeroes.exe']['sha256'],context)
        self.assertTrue(result['native_layer_identity_migrated'])
        self.assertEqual((work/textures.module.PACK).read_bytes()[64:],pack_before[64:])
        before=(work/textures.module.PACK).read_bytes()
        bad=copy.deepcopy(report['native_texture_index_migration']);bad['layer_manifest_sha256']='0'*64
        # Restore the old envelope/marker to force a second migration attempt.
        # A forged proof must not update it; ordinary regeneration is disabled.
        context.report['client_worktree']['native_texture_index_migration']=bad
        with self.assertRaisesRegex(ValueError,'current consumer/source/input proof differs'):
            textures.module.prepare(work,imported,package['files']['CityOfHeroes.exe']['sha256'],context)
        self.assertEqual((work/textures.module.PACK).read_bytes(),before)
        context.report['client_worktree']['native_texture_index_migration']=valid_proof
        marker_before=(work/textures.module.MARKER).read_bytes()
        changed_source=copy.deepcopy(valid_proof);changed_source['native_source_closure_verified']=False
        context.report['client_worktree']['native_texture_index_migration']=changed_source
        with self.assertRaisesRegex(ValueError,'current consumer/source/input proof differs'):
            textures.module.prepare(work,imported,package['files']['CityOfHeroes.exe']['sha256'],context)
        context.report['client_worktree']['native_texture_index_migration']=valid_proof
        game=work/'CityOfHeroes.exe';game.chmod(0o600);game.write_bytes(game.read_bytes()[:-1]+b'X')
        with self.assertRaisesRegex(ValueError,'Actual native consumer bytes differ'):
            textures.module.prepare(work,imported,package['files']['CityOfHeroes.exe']['sha256'],context)
        self.assertEqual((work/textures.module.PACK).read_bytes(),before)
        self.assertEqual((work/textures.module.MARKER).read_bytes(),marker_before)

    def test_same_process_native_hash_reuse_requires_exact_inode_ctime_and_all_pins(self):
        package, expected, review, raw = activation_fixture('game')
        self.enable('game', expected, review)
        path = self.executable('game', raw)
        first = native.runtime_admission(package, 'game', path)
        again = native.runtime_admission(package, 'game', path)
        self.assertEqual(first['executable_validation'], 'full_current_owned_native_byte_hash')
        self.assertEqual(again['executable_validation'], 'same_process_exact_unchanged_owned_inode')
        info = path.stat()
        path.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
        __import__('os').utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
        with self.assertRaisesRegex(ValueError, 'Actual native consumer bytes differ'):
            native.runtime_admission(package, 'game', path)

    def test_texture_input_migration_derives_generation_and_root_specific_identities(self):
        previous = native.unique_json(fixture('game')[1]['client-package.json'])
        current_sha = fixture('game')[3]['native_record']['sha256']
        closure = {name: {'bytes': 100, 'sha256': '8'*64} for name in native.TEXTURE_SOURCE_PATHS}
        recipe = {'cache_archive_sha256': '1'*64, 'prerequisites_archive_sha256': '2'*64,
            'prerequisites_manifest_sha256': '3'*64, 'normalized_mtime_epoch': 1767225600,
            'import_contract_sha256': '4'*64, 'imported_file_count': 173011,
            'imported_total_bytes': 2977730517}
        bridge = {'policy': 'exact_verified_input_recipe_and_unchanged_texture_schema',
            'previous_executable_sha256': previous['files']['CityOfHeroes.exe']['sha256'],
            'client_executable_sha256': current_sha, 'texture_header_struct_bytes': 32,
            'unchanged_texture_source_pins': closure, 'immutable_input_recipe': recipe}
        package, expected, review, _ = activation_fixture('game', {'texture_header_index': bridge},
            {'previous_texture_source_pins': closure, 'current_texture_source_pins': closure})
        self.enable('game', expected, review)
        data = {'format': 1, 'source_data': '/owned/test/generation-a/data',
            'import': {'generation': 'generation-'+'a'*32, 'receipt_sha256': '5'*64,
                'contract_sha256': '4'*64, 'file_count': 173011, 'total_bytes': 2977730517},
            **{name: recipe[name] for name in ('cache_archive_sha256', 'prerequisites_archive_sha256',
                'prerequisites_manifest_sha256', 'normalized_mtime_epoch')}}
        def content(native_package, inputs):
            return startup.identity_sha256({'data': inputs, 'native': startup.native_closure_identity(native_package)})
        for generation in ('a', 'b'):
            selected = copy.deepcopy(data)
            selected['source_data'] = '/owned/test/generation-'+generation+'/data'
            selected['import']['generation'] = 'generation-'+generation*32
            old = {'data_contract': selected, 'content_identity_sha256': content(previous, selected)}
            new = content(package, selected)
            proof = native.game_texture_index_migration(package, old, new)
            self.assertEqual(proof['content_identity_sha256'], new)
            self.assertEqual(proof['previous_client_identity'], old)
            with self.assertRaises(ValueError): native.game_texture_index_migration(package, old, '9'*64)
        for key, value in (('cache_archive_sha256', '0'*64), ('normalized_mtime_epoch', True)):
            changed = copy.deepcopy(data); changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                native.game_texture_index_migration(package,
                    {'data_contract': changed, 'content_identity_sha256': content(previous, changed)}, content(package, changed))
        changed = copy.deepcopy(data); changed['import']['contract_sha256'] = '0'*64
        with self.assertRaises(ValueError): native.game_texture_index_migration(package,
            {'data_contract': changed, 'content_identity_sha256': content(previous, changed)}, content(package, changed))

    def test_execution_review_selects_exact_bounded_relative_qualification_receipt(self):
        package,expected,review,raw=activation_fixture('game')
        old='fixture-qualification.json';new='native-client-paired/fixture-qualification.json'
        material=expected['materials']['qualification']
        material['members'][new]=material['members'].pop(old)
        material['required_receipt_values'][new]=material['required_receipt_values'].pop(old)
        review['qualification_receipts'][new]=review['qualification_receipts'].pop(old)
        review['component_authority_sha256']=native.canonical_sha(expected)
        wrapper=package[native.WRAPPER]
        wrapper['receipt']['materials']=copy.deepcopy(expected['materials'])
        wrapper['receipt']['authority_sha256']=native.canonical_sha(expected)
        wrapper['receipt_sha256']=native.canonical_sha(wrapper['receipt'])
        self.enable('game',expected,review)
        self.assertTrue(native.runtime_admission(package,'game',self.executable('game',raw))['runtime_activation_allowed'])
        review['qualification_receipts']['../escape']=review['qualification_receipts'].pop(new)
        with self.assertRaises(ValueError):native.runtime_admission(package,'game')

    def test_map_world_switch_only_supported_fresh_maps(self):
        package, expected, review, raw = activation_fixture('mapserver')
        self.enable('mapserver', expected, review)
        path = self.executable('mapserver', raw)
        for map_id in (1, 5):
            env = {}; native.apply_attempt_environment(package, 'mapserver', path, env, map_id=map_id)
            self.assertEqual(env, {'COH_MAP_ANIMATION_METADATA_PREFETCH': '1'})
        for map_id in (101, 0, True, '5', None):
            env = {'COH_MAP_ANIMATION_METADATA_PREFETCH': 'inherited'}
            with self.subTest(map_id=map_id), self.assertRaises(ValueError):
                native.apply_attempt_environment(package, 'mapserver', path, env, map_id=map_id)
            self.assertEqual(env, {})

    def test_client_constructor_scrubs_shared_prerequisite_environments(self):
        def initialize(owner, args, context):
            owner.base_env={name:'inherited' for name in native.ATTEMPT_ENVIRONMENTS.values()}
            owner.wine_env=dict(owner.base_env, WINEPREFIX='retained')
        root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        args=SimpleNamespace(state=root,session_id='a'*32)
        with patch.object(startup.presentation.PresentationDiagnostic,'__init__',initialize):
            owner=startup.ClientStartupDiagnostic(args,SimpleNamespace())
        self.assertEqual(owner.base_env,{})
        self.assertEqual(owner.wine_env,{'WINEPREFIX':'retained'})

    def test_full_current_pipeline_queue_controls_keep_raw_producers_and_label_new_source(self):
        root,work_root,work,assets,data,imported,context,package,_=self.warm_worktree()
        sockets=root/'sockets';sockets.mkdir(mode=0o700)
        context.stage=Mock();context.passed=Mock()
        owner=object.__new__(reopen.StartupOnlyCharacterReopenDiagnostic)
        owner.root=work_root;owner.ctx=context;owner.presentation_socket=sockets/'presentation.sock'
        owner.args=SimpleNamespace(assets=assets,wine=root/'unused-wine',wineserver=root/'unused-wineserver',
            socket_dir=sockets,game_data=data,session_id='a'*32)
        with patch.object(startup,'verify_assets',return_value={}), \
                patch.object(startup.base,'arm64_elf'),patch.object(startup.platform,'machine',return_value='aarch64'), \
                patch.object(startup.os,'geteuid',return_value=1000),patch.object(startup,'import_identity',return_value=imported):
            startup.ClientStartupDiagnostic.initialize(owner)
        raw_reports={name:native.encoded(context.report[name]) for name in ('client_render_pipeline','client_render_queue')}
        queue=gpu.verified_render_queue_producer(owner)
        pipeline=gpu.verified_render_pipeline_producer(owner)
        self.assertNotIn('repository_commit',queue)
        self.assertNotIn('current_Game_repository_commit',pipeline)
        self.assertEqual(pipeline['native_metadata_consumer']['native_producer']['repository_commit'],'e'*40)
        self.assertNotEqual(pipeline['retained_control_Game_repository_commit'],'e'*40)
        env={};startup.apply_client_render_pipeline_environment(owner,env,'unexecuted-fixture')
        emitted=context.report['client_render_pipeline_environment']
        self.assertNotIn('current_Game_repository_commit',emitted)
        self.assertEqual(emitted['native_metadata_consumer']['native_producer']['repository_commit'],'e'*40)
        self.assertEqual(emitted['retained_control_Game_repository_commit'],pipeline['retained_control_Game_repository_commit'])
        self.assertEqual(raw_reports,{name:native.encoded(context.report[name]) for name in raw_reports})
        owner.wine_env={'DISPLAY':':99','WINEPREFIX':str(root/'unused-prefix')}
        original_environment=dict(owner.wine_env)
        context.start=Mock(return_value=SimpleNamespace(scope='unexecuted_argv_fixture'))
        for label in ('actual-coh-client','actual-coh-client-retry'):
            owner.launch_client_attempt(label=label)
            attempt=context.start.call_args
            self.assertEqual(attempt.args[0],label)
            self.assertEqual(attempt.args[1][-1],'--character-manual')
            self.assertEqual(attempt.kwargs['env']['COH_CLIENT_FOLDER_METADATA_SORT'],'1')
            self.assertNotIn('COH_MAP_ANIMATION_METADATA_PREFETCH',attempt.kwargs['env'])
            self.assertEqual(owner.wine_env,original_environment)
            self.assertEqual(raw_reports,{name:native.encoded(context.report[name]) for name in raw_reports})

    def test_gpu_prerequisite_children_receive_neither_game_nor_map_opt_in(self):
        original = {'COH_CLIENT_FOLDER_METADATA_SORT': '1',
            'COH_MAP_ANIMATION_METADATA_PREFETCH': 'inherited', 'DISPLAY': ':99'}
        child = SimpleNamespace(process=SimpleNamespace(poll=lambda: 0),
            reader=SimpleNamespace(is_alive=lambda: False, join=Mock()), writer=SimpleNamespace(join=Mock()),
            output=[], overflow=False, started=__import__('time').monotonic(), text=lambda: 'controlled fixture')
        owner = SimpleNamespace(ctx=SimpleNamespace(start=Mock(return_value=child), record=Mock(return_value={'exit_code': 0})))
        with patch.object(gpu, 'check_probe_owner'):
            self.assertEqual(gpu.run_probe(owner, 'fixture-only', [], original, 1), 'controlled fixture')
        self.assertEqual(owner.ctx.start.call_args.kwargs['env'], {'DISPLAY': ':99'})
        self.assertEqual(original['COH_CLIENT_FOLDER_METADATA_SORT'], '1')
        cache = SimpleNamespace(release=Mock())
        with patch.object(gpu, 'ProbePrefixCache', return_value=cache) as constructor, \
                patch.object(gpu, '_private_wgl_probe', return_value={'scope': 'unexecuted'}) as probe:
            gpu.private_wgl_probe(owner, original, Path('/unused/fixture'), Path('/unused'), {})
            self.assertEqual(constructor.call_args.args[1], {'DISPLAY': ':99'})
            self.assertEqual(probe.call_args.args[1], {'DISPLAY': ':99'})
            cache.release.assert_called_once()

    def test_game_gpu_adaptor_preserves_historical_producer_separately(self):
        package, expected, review, raw = activation_fixture('game')
        self.enable('game', expected, review)
        path = self.executable('game', raw)
        owner = SimpleNamespace(client_native_metadata_package=package, work=path.parent,
            client_executable_sha256=expected['native_record']['sha256'])
        self.assertEqual(gpu.retained_client_sha256(owner), review and native.runtime_admission(package, 'game')['previous_consumer_sha256'])
        old = {'client_executable_sha256': gpu.retained_client_sha256(owner), 'repository_commit': 'd'*40}
        before = copy.deepcopy(old)
        current = gpu.current_consumer_result(owner, old)
        self.assertEqual(old, before)
        self.assertEqual(current['client_executable_sha256'], owner.client_executable_sha256)
        self.assertEqual(current['retained_control_producer_executable_sha256'], before['client_executable_sha256'])
        self.assertNotIn('repository_commit', current)
        self.assertEqual(current['retained_producer']['repository_commit'], before['repository_commit'])
        self.assertEqual(current['native_metadata_consumer']['native_producer'], expected['materials']['producer'])
        with self.assertRaises(gpu.GPUProfileError): gpu.current_consumer_result(owner, dict(old, client_executable_sha256='9'*64))

    def test_dormant_artifact_preparation_fails_before_io(self):
        self.assertFalse(admission.PROMOTIONS_IMPLEMENTED)
        with self.assertRaisesRegex(ValueError, 'disabled'):
            admission.prepare_reviewed_native_archives('/missing/donor.apk', {'game': {}})

    def test_authenticated_fixture_artifacts_prepare_only_one_native_and_receipt(self):
        # Real retained PE is changed in an unused last byte and never run.
        # All three deliberately synthetic authority ZIPs are byte-bound.
        _, members, raw, initial = fixture('game')
        expected = copy.deepcopy(initial)
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        paths = {}
        for role in native.MATERIAL_ROLES:
            receipt_name = role+'-fixture.json'
            claims = {'scope': 'unexecuted_controlled_unit_fixture', 'fixture_passed': True}
            rows = {receipt_name: native.encoded(claims)}
            if role == 'producer': rows['CityOfHeroes.exe'] = raw
            target = directory/(role+'.zip')
            with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as opened:
                for name, body in rows.items(): opened.writestr(name, body)
            paths[role] = target
            expected['materials'][role] = {'repository_commit': 'c'*40,
                'run_id': 1, 'artifact_id': 2, 'artifact_zip': migration.content_pin(target.read_bytes()),
                'members': {name: migration.content_pin(body) for name, body in rows.items()},
                'required_receipt_values': {receipt_name: claims}}
        qualified = expected['materials']['qualification']
        review = {'format': 1, 'kind': 'game', 'component_authority_sha256': native.canonical_sha(expected),
            'qualification_artifact_zip': qualified['artifact_zip'],
            'qualification_receipts': {'qualification-fixture.json': {
                'pin': qualified['members']['qualification-fixture.json'],
                'required_values': qualified['required_receipt_values']['qualification-fixture.json']}},
            'qualified_maps': [], 'attempt_environment': native.ATTEMPT_ENVIRONMENTS['game'],
            'scope': {'old_native_producer_relabelled': False,
                'behavioral_collision_validated': False, 'physical_timing_validated': False}}
        self.enable('game', expected, review)
        donor = Path(__import__('os').environ.get('COH_ZONE_STARTUP_TEST_DONOR_APK',
            '/workspace/scratch/5d16603ca7ff/publication-037-evidence/COH-Atlas-Gameplay-0.13.36.apk'))
        with patch.object(admission, 'PROMOTIONS_IMPLEMENTED', True):
            archives, proofs = admission.prepare_reviewed_native_archives(donor, {'game': paths})
            self.assertEqual(set(archives), {'assets/runtime/client-runtime.zip'})
            after, _ = migration.zip_members(archives['assets/runtime/client-runtime.zip'])
            self.assertEqual({name for name in after if after[name] != members[name]},
                {'CityOfHeroes.exe', 'client-package.json'})
            self.assertEqual(proofs['game']['unchanged_native_members'], 20)
            self.assertFalse(proofs['game']['apk_publication_authorized'])
            self.assertFalse(proofs['game']['native_process_executed_by_preparer'])
            paths['qualification'].write_bytes(paths['qualification'].read_bytes()+b'tamper')
            with self.assertRaisesRegex(ValueError, 'artifact bytes differ'):
                admission.prepare_reviewed_native_archives(donor, {'game': paths})

    def test_actual_wrapped_client_archive_validates_old_receipt_and_new_record(self):
        package, expected, review, raw = activation_fixture('game')
        self.enable('game', expected, review)
        archive, report = migration.migrate_archive(fixture('game')[0], 'game', raw, expected)
        assets = Path(self.enterContext(tempfile.TemporaryDirectory()))
        old = fixture('game')[1]['client-package.json']
        receipt = native.unique_json(old)['native_responsiveness']['receipt']
        (assets/'native-responsiveness.json').write_bytes(native.encoded(receipt))
        with zipfile.ZipFile(io.BytesIO(archive)) as opened:
            result = startup.archive_manifest(opened, assets)
        self.assertEqual(result, package)
        self.assertEqual(report['unchanged_native_members'], 20)
        self.assertFalse(report['shipping_allowed'])


if __name__ == '__main__': unittest.main()
