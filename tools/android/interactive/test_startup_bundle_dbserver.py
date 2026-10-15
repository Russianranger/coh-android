"""Check frozen native ancestry, isolated save patch, and packaged dependency pins."""
import copy
import json
import os
import hashlib
import sys
from pathlib import Path
import struct
import shutil
import tempfile
from types import SimpleNamespace
import unittest

import package_startup_bundle_dbserver as bundle
if os.name != 'nt':
    sys.path.insert(0,str(bundle.ROOT/'android/guest'))
    import local_character_server as character
from test_local_launcher_wait import staged_base as retained_staged_base
from test_package_reference_runtime import pe_file


def staged_base(directory):
    retained_staged_base(directory)
    name='DBServer/src/container_merge.c'
    shutil.copyfile(bundle.ROOT/'upstream/ouroboros'/name,directory/name)


def staged_bundle(directory):
    staged_base(directory)
    base_manifest=bundle.ROOT/bundle.retained.ACCEPTED_BASE_MANIFEST
    bundle.retained.align_base_profile(directory,base_manifest)
    bundle.retained.apply_overlay(directory)
    return bundle.apply_overlay(directory)


def executable(path):
    image=bytearray(pe_file(('odbc32.dll',)))
    image.extend(b'\0'*(4608-len(image)))
    struct.pack_into('<4I',image,152+224+8,4096,0x1000,4096,512)
    struct.pack_into('<I',image,512,0x1200)
    for index,name in enumerate(bundle.retained.wine.REQUIRED_IMPORTS):
        rva=0x1500+index*64
        struct.pack_into('<I',image,1024+index*4,rva)
        offset=rva-0x1000+512
        image[offset:offset+len(name)+3]=b'\0\0'+name.encode()+b'\0'
    path.write_bytes(image)


class StartupBundleNativeTests(unittest.TestCase):
    def test_layer_changes_only_emitter_and_keeps_every_prior_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)
            staged_base(source)
            manifest=bundle.ROOT/bundle.retained.ACCEPTED_BASE_MANIFEST
            bundle.retained.align_base_profile(source,manifest)
            base=bundle.retained.apply_overlay(source)
            before={name:bundle.retained.wine.sha256(source/name) for name in bundle.source_closure(base)}
            receipt_files=['postgresql-build-input.json',bundle.retained.wine.RECEIPT,bundle.retained.RECEIPT]
            receipts={name:(source/name).read_bytes() for name in receipt_files}
            layer=bundle.apply_overlay(source)
            self.assertEqual(layer,bundle.expected_receipt(base_startup_build_input=base))
            self.assertEqual(layer['source_sha256'],{name:before[name] for name in bundle.PATCHED_FILES})
            self.assertEqual(layer['base_startup_build_input_canonical_sha256'],bundle.retained.canonical_hash(base))
            for name,digest in before.items():
                if name not in bundle.PATCHED_FILES:self.assertEqual(bundle.retained.wine.sha256(source/name),digest)
            for name,raw in receipts.items():self.assertEqual((source/name).read_bytes(),raw)
            self.assertEqual(base['launcher_wait'],bundle.retained.launcher_wait_contract())

    def test_changed_base_and_duplicate_layer_are_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary);staged_bundle(source)
            with self.assertRaisesRegex(ValueError,'already exists'):bundle.apply_overlay(source)
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary);staged_base(source);bundle.retained.apply_overlay(source)
            (source/'DBServer/src/container_sql.c').write_text('changed baseline')
            with self.assertRaisesRegex(ValueError,'source changed'):bundle.apply_overlay(source)

    def test_merger_mutation_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary);staged_base(source);bundle.retained.apply_overlay(source)
            (source/'DBServer/src/container_merge.c').write_text('changed merger')
            with self.assertRaisesRegex(ValueError,'production merger'):bundle.apply_overlay(source)

    def test_only_dbserver_packaged_with_original_dependency_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'source';source.mkdir();staged_bundle(source)
            binary=root/'DbServer.exe';executable(binary)
            cache=root/'CMakeCache.txt';cache.write_text('COH_PG_PERSISTENCE_TESTS:BOOL=OFF\nCMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n')
            args=SimpleNamespace(source=source,binary=binary,cache=cache,
                base_manifest=bundle.ROOT/bundle.retained.ACCEPTED_BASE_MANIFEST,
                repository_commit='a'*40,output=root/'package')
            manifest=bundle.package(args)
            self.assertEqual(bundle.validate_package(args.output,args.repository_commit),manifest)
            self.assertEqual(manifest['build_input'],json.loads((source/bundle.retained.RECEIPT).read_text()))
            self.assertEqual(manifest['startup_bundle_build_input'],json.loads((source/bundle.RECEIPT).read_text()))
            self.assertEqual(set(manifest['files']),{'DbServer.exe'})
            self.assertFalse(manifest['postgresql_persistence_fixture'])
            self.assertFalse(manifest['base_package_archive_changed'])
            self.assertFalse(manifest['gameplay_validated'])
            mutations=[('base_normal_cmake_cache_sha256','f'*64),
                ('base_startup_executable',dict(bundle.BASE_STARTUP_EXECUTABLE,sha256='f'*64)),
                ('startup_bundle_build_input',dict(manifest['startup_bundle_build_input'],patch_sha256='f'*64)),
                ('build_input',dict(manifest['build_input'],runtime_validation='passed')),
                ('retained_normal_files',{}),('postgresql_persistence_fixture',True)]
            path=args.output/bundle.MANIFEST
            for key,replacement in mutations:
                with self.subTest(key=key):
                    changed=copy.deepcopy(manifest);changed[key]=replacement;path.write_text(json.dumps(changed))
                    with self.assertRaises(ValueError):bundle.validate_package(args.output,args.repository_commit)
            path.write_text(json.dumps(manifest))
            (args.output/'DbServer.exe').write_bytes(b'changed')
            with self.assertRaises(ValueError):bundle.validate_package(args.output,args.repository_commit)

    def test_package_refuses_post_layer_source_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/'source';source.mkdir();staged_bundle(source)
            (source/'DBServer/src/container_sql.c').write_text('changed emitter')
            args=SimpleNamespace(source=source,repository_commit='a'*40,output=root/'package')
            with self.assertRaisesRegex(ValueError,'source changed'):bundle.package(args)

    def test_patch_inventory_and_build_contract_are_narrow(self):
        self.assertEqual(bundle.PATCHED_FILES,('DBServer/src/container_sql.c',))
        self.assertFalse(bundle.save_contract()['ignored_SQL_failures'])
        self.assertFalse(bundle.save_contract()['UPSERT'])
        self.assertFalse(bundle.save_contract()['schema_migration'])
        self.assertFalse(bundle.save_contract()['profile_reset'])
        with tempfile.TemporaryDirectory() as temporary:
            cache=Path(temporary)/'CMakeCache.txt'
            for text in ('COH_PG_PERSISTENCE_TESTS:BOOL=ON\nCMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n',
                         'COH_PG_PERSISTENCE_TESTS:BOOL=OFF\nCMAKE_GENERATOR_PLATFORM:INTERNAL=x64\n'):
                cache.write_text(text)
                with self.assertRaises(ValueError):bundle.retained.validate_cache(cache)


if os.name != 'nt':
    def test_linked_package_leaves_and_directory_are_refused_before_reads(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);directory=root/'package';directory.mkdir()
            for name in ('DbServer.exe','CMakeCache.txt',bundle.MANIFEST):
                (directory/name).write_bytes(b'fixture')
            for name in ('DbServer.exe','CMakeCache.txt',bundle.MANIFEST):
                with self.subTest(name=name):
                    path=directory/name;path.unlink();target=root/(name+'.original');target.write_bytes(b'fixture')
                    path.symlink_to(target)
                    with self.assertRaisesRegex(ValueError,'linked startup bundle native package leaf'):
                        bundle.validate_package(directory,'a'*40)
                    path.unlink();path.write_bytes(b'fixture')
            alias=root/'alias';alias.symlink_to(directory,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'linked startup bundle native package directory'):
                bundle.validate_package(alias,'a'*40)

    StartupBundleNativeTests.test_linked_package_leaves_and_directory_are_refused_before_reads = test_linked_package_leaves_and_directory_are_refused_before_reads

    def guest_fixture(root):
        assets=root/'assets';runtime=root/'runtime';assets.mkdir();runtime.mkdir()
        package=json.loads((bundle.ROOT/bundle.retained.ACCEPTED_BASE_MANIFEST).read_text())
        original=b'accepted donor executable';library=b'accepted donor library'
        normal=package['variants']['normal']
        normal['files']={'DbServer.exe':{'bytes':len(original),'sha256':hashlib.sha256(original).hexdigest()},
            'retained.dll':{'bytes':len(library),'sha256':hashlib.sha256(library).hexdigest()}}
        (runtime/'DbServer.exe').write_bytes(original);(runtime/'retained.dll').write_bytes(library)
        image=pe_file(('KERNEL32.dll',));(assets/'startup-dbserver.exe').write_bytes(image)
        base=bundle.retained.expected_receipt(base_wine_build_input=package['wine_build_input'])
        manifest={'format':1,'role':bundle.ROLE,'repository_commit':'a'*40,
            'source_commit':package['source_commit'],'base_package_manifest_sha256':bundle.retained.BASE_PACKAGE_SHA256,
            'replacement_scope':'fresh_owned_manual_atlas_runtime_DbServer.exe_only',
            'base_package_archive_changed':False,'architecture':'Win32','configuration':'OptDebug',
            'postgresql_persistence_fixture':False,'android_execution_validated':False,'gameplay_validated':False,
            'retained_normal_files':{'retained.dll':normal['files']['retained.dll']},
            'base_normal_executable':normal['files']['DbServer.exe'],
            'base_normal_cmake_cache_sha256':normal['cmake_cache_sha256'],
            'base_startup_executable':bundle.BASE_STARTUP_EXECUTABLE,'build_input':base,
            'startup_bundle_build_input':bundle.expected_receipt(base_startup_build_input=base),
            'files':{'DbServer.exe':{'bytes':len(image),'sha256':hashlib.sha256(image).hexdigest()}},
            'dependency_report':{'unresolved':[]},'odbc_imports':list(bundle.retained.wine.REQUIRED_IMPORTS)}
        (assets/'startup-dbserver-manifest.json').write_text(json.dumps(manifest))
        return assets,runtime,package,manifest,original,image,library


    class StartupBundleGuestTests(unittest.TestCase):
        def test_guest_layer_contract_matches_source_bound_native_receipt(self):
            package=json.loads((bundle.ROOT/bundle.retained.ACCEPTED_BASE_MANIFEST).read_text())
            base=bundle.retained.expected_receipt(base_wine_build_input=package['wine_build_input'])
            self.assertEqual(character.startup_bundle_save_contract(),bundle.save_contract())
            self.assertEqual(character.startup_bundle_build_input(base),bundle.expected_receipt(base_startup_build_input=base))
            self.assertEqual(character.STARTUP_BUNDLE_BASE_EXECUTABLE,bundle.BASE_STARTUP_EXECUTABLE)

        def test_new_role_installs_only_fresh_dbserver_and_retains_owned_libraries(self):
            with tempfile.TemporaryDirectory() as temporary:
                assets,runtime,package,value,original,image,library=guest_fixture(Path(temporary))
                result=character.install_manual_atlas_dbserver(assets,runtime,package)
                self.assertEqual((runtime/'DbServer.exe').read_bytes(),image)
                self.assertEqual((runtime/'retained.dll').read_bytes(),library)
                self.assertEqual(result['startup_bundle_save'],bundle.save_contract())
                self.assertEqual(result['startup_bundle_build_input_sha256'],character.digest_json(value['startup_bundle_build_input']))
                with self.assertRaisesRegex(character.base.DiagnosticError,'fresh accepted DbServer'):
                    character.install_manual_atlas_dbserver(assets,runtime,package)

        def test_mutated_layer_or_frozen_ancestry_is_refused_before_replacement(self):
            cases=[('source_sha256',{'DBServer/src/container_sql.c':'f'*64}),
                ('patched_sha256',{'DBServer/src/container_sql.c':'f'*64}),
                ('patch_sha256','f'*64),('patch','patches/unqualified.patch'),
                ('base_startup_build_input_canonical_sha256','f'*64),('runtime_validation','passed'),
                ('postgresql_persistence_fixture',True),('save_contract',dict(bundle.save_contract(),ignored_SQL_failures=True))]
            for key,replacement in cases:
                with self.subTest(key=key),tempfile.TemporaryDirectory() as temporary:
                    assets,runtime,package,value,original,_,_=guest_fixture(Path(temporary))
                    value['startup_bundle_build_input'][key]=replacement
                    (assets/'startup-dbserver-manifest.json').write_text(json.dumps(value))
                    with self.assertRaisesRegex(character.base.DiagnosticError,'save layer'):
                        character.install_manual_atlas_dbserver(assets,runtime,package)
                    self.assertEqual((runtime/'DbServer.exe').read_bytes(),original)
            for mode in ('old-role-new-layer','changed-old-wait-input','changed-base-startup-executable'):
                with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temporary:
                    assets,runtime,package,value,original,_,_=guest_fixture(Path(temporary))
                    if mode=='old-role-new-layer':value['role']='manual_atlas_dbserver_startup_supplement'
                    elif mode=='changed-old-wait-input':value['build_input']['patch_sha256']='f'*64
                    else:value['base_startup_executable']=dict(bundle.BASE_STARTUP_EXECUTABLE,sha256='f'*64)
                    (assets/'startup-dbserver-manifest.json').write_text(json.dumps(value))
                    with self.assertRaises(character.base.DiagnosticError):character.install_manual_atlas_dbserver(assets,runtime,package)
                    self.assertEqual((runtime/'DbServer.exe').read_bytes(),original)


if __name__=='__main__':unittest.main(verbosity=2)
