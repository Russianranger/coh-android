"""Current-generation safety tests; projections are deliberately nonshipping."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'android/guest/folder_cache_census.py'
spec = importlib.util.spec_from_file_location('fresh_census_prototype', SOURCE)
census = importlib.util.module_from_spec(spec); spec.loader.exec_module(census)


def pin(path):
    raw = path.read_bytes()
    return {'path':str(path), 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


class CurrentCensusTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.root = self.base/'work/data'; self.root.mkdir(parents=True)
        self.imported = self.base/'imported'; self.imported.mkdir()
        for branch in census.BRANCHES:
            (self.root/branch).mkdir()
            target = self.root/branch/'ordinary.dat'
            target.write_bytes(branch.encode()); target.chmod(0o444)
        (self.root/'fx/empty').mkdir()
        (self.root/'fx/.hidden-dir').mkdir()
        (self.root/'fx/.hidden-dir/nontexture.txt').write_bytes(b'retained hidden membership')
        (self.root/'fx/.hidden-dir/nontexture.txt').chmod(0o444)
        self.alias_target = self.imported/'original.texture'
        self.alias_target.write_bytes(b'immutable original bytes'); self.alias_target.chmod(0o444)
        (self.root/'texture_library/linked.texture').symlink_to(self.alias_target)
        (self.root/'bin').mkdir(); (self.root/'bin/private.bin').write_bytes(b'private cache stays mutable')
        consumer=self.base/'Game-unit-bytes'; consumer.write_bytes(b'UNEXECUTED_UNIT_CONSUMER')
        runtime=self.base/'runtime-unit-bytes'; runtime.write_bytes(b'UNEXECUTED_UNIT_RUNTIME')
        self.recipe = {'format':1,'branches':list(census.BRANCHES),'mode':'development_dynamic',
            'exclusion':{'mode':'all','name':None},'ignore_prefixes':['d_'],
            'gdd_roots':[str(self.root)],'source_roots':[str(self.root),str(self.imported)],
            'pig_providers':[],'consumer':pin(consumer),'runtime_files':[pin(runtime)],
            'wine_source_commit':census.WINE_SOURCE,'supplements_finalized':True}
        self.operation='a'*32

    def capture(self, **kwargs):
        return census.capture(self.root,self.recipe,self.operation,**kwargs)

    def rows(self, packet):
        count, offset=struct.unpack_from('<II',packet,20)
        return [packet[offset+i*328:offset+(i+1)*328] for i in range(count)]

    def test_complete_nontexture_empty_dot_and_link_membership_is_present_but_inert(self):
        before=(self.root/'bin/private.bin').read_bytes()
        packet,report=self.capture()
        self.assertEqual(packet[:8],b'COHCNS1\0')
        self.assertEqual(struct.unpack_from('<I',packet,12)[0],len(packet))
        self.assertEqual(packet[32:64].hex(),report['generation_token'])
        rows=self.rows(packet)
        names=[row[52:312].split(b'\0',1)[0] for row in rows]
        self.assertIn(b'nontexture.txt',names);self.assertIn(b'.hidden-dir',names)
        self.assertIn(b'empty',names);self.assertIn(b'linked.texture',names)
        self.assertNotIn(b'private.bin',names)
        self.assertEqual(before,(self.root/'bin/private.bin').read_bytes())
        self.assertFalse(report['root_anchor_complete'])
        self.assertEqual(report['linked_files'],1)
        self.assertEqual(report['fresh_full_metadata_passes'],2)
        self.assertFalse(report['prior_fingerprint_receipt_used'])
        self.assertFalse(report['native_registration_allowed'])
        self.assertFalse(report['actual_Wine_WFD_parity_qualified'])
        self.assertFalse(report['mutable_BIN_schema_or_ID_certification'])
        for row in rows:
            self.assertEqual(row[44:52],bytes(8))
            self.assertEqual(row[312:],bytes(16))

    def test_mutation_in_place_with_restored_mtime_is_detected_without_content_rehash(self):
        target=self.root/'fx/ordinary.dat';info=target.stat()
        def mutate():
            target.chmod(0o600);target.write_bytes(b'zz');target.chmod(0o444)
            os.utime(target,ns=(info.st_atime_ns,info.st_mtime_ns))
        with self.assertRaisesRegex(census.CensusRefused,'changed between fresh passes'):
            self.capture(_between_passes=mutate)

    def test_added_removed_and_renamed_membership_each_refuse_replay(self):
        for change in ('add','remove','rename'):
            with self.subTest(change=change):
                path=self.root/'scripts/ordinary.dat'
                def mutate():
                    if change=='add':
                        q=path.parent/'new.dat';q.write_bytes(b'new');q.chmod(0o444)
                    elif change=='remove':path.unlink()
                    else:path.rename(path.parent/'renamed.dat')
                with self.assertRaises(census.CensusRefused):self.capture(_between_passes=mutate)
                for q in path.parent.iterdir():q.unlink()
                path.write_bytes(b'scripts');path.chmod(0o444)

    def test_case_aliases_directory_aliases_and_escape_fail_before_packet_publication(self):
        duplicate=self.root/'fx/ORDINARY.DAT';duplicate.write_bytes(b'x');duplicate.chmod(0o444)
        with self.assertRaisesRegex(census.CensusRefused,'Case-aliased'):self.capture()
        duplicate.unlink()
        link=self.root/'fx/aliased-dir';link.symlink_to(self.imported,target_is_directory=True)
        with self.assertRaisesRegex(census.CensusRefused,'Directory aliases'):self.capture()
        link.unlink()
        outside=self.base/'outside';outside.write_bytes(b'x');outside.chmod(0o444)
        link.symlink_to(outside)
        with self.assertRaisesRegex(census.CensusRefused,'escaped'):self.capture()

    def test_relative_and_chained_aliases_are_unknown_and_preserved(self):
        link=self.root/'fx/alias';link.symlink_to('../scripts/ordinary.dat')
        with self.assertRaisesRegex(census.CensusRefused,'relative/chained'):self.capture()
        self.assertTrue(link.is_symlink());link.unlink()
        intermediary=self.imported/'chain';intermediary.symlink_to(self.alias_target)
        link.symlink_to(intermediary)
        with self.assertRaisesRegex(census.CensusRefused,'Chained'):self.capture()

    def test_replaced_source_ancestor_is_not_hidden_by_leaf_metadata(self):
        def mutate():
            previous=self.imported.with_name('previous-import');self.imported.rename(previous)
            self.imported.mkdir()
            previous.joinpath('original.texture').rename(self.imported/'original.texture')
        with self.assertRaisesRegex(census.CensusRefused,'changed between fresh passes'):
            self.capture(_between_passes=mutate)

    def test_mutable_private_bin_dbidmap_hardlink_or_unreadable_leaf_cannot_donate(self):
        ordinary=self.root/'fx/ordinary.dat'
        ordinary.chmod(0o600)
        with self.assertRaisesRegex(census.CensusRefused,'Mutable'):self.capture()
        ordinary.chmod(0o000)
        with self.assertRaisesRegex(census.CensusRefused,'Unreadable'):self.capture()
        ordinary.chmod(0o444)
        for filename in ('private.bin','generated.dbidmap'):
            path=ordinary.parent/filename;path.write_bytes(b'x');path.chmod(0o444)
            with self.subTest(filename=filename),self.assertRaisesRegex(census.CensusRefused,'BIN/DB-ID'):self.capture()
            path.unlink()
        os.link(ordinary,ordinary.parent/'hardlink.dat')
        with self.assertRaisesRegex(census.CensusRefused,'hardlinked'):self.capture()

    def test_complete_owned_readonly_import_store_alias_group_is_captured_without_copying(self):
        store=self.base/'immutable-store';store.mkdir()
        alias=store/'pinned-input';os.link(self.alias_target,alias)
        self.recipe['source_roots'].append(str(store))
        self.recipe['known_readonly_hardlinks']=[sorted([str(alias),str(self.alias_target)])]
        before=(self.alias_target.stat().st_ino,self.alias_target.stat().st_nlink)
        _,report=self.capture()
        self.assertEqual(report['known_readonly_shared_inode_alias_paths'],2)
        self.assertEqual(before,(self.alias_target.stat().st_ino,self.alias_target.stat().st_nlink))
        self.assertFalse(report['native_registration_allowed'])
        extra=store/'unknown-extra';os.link(self.alias_target,extra)
        with self.assertRaisesRegex(census.CensusRefused,'Unknown hardlinked'):self.capture()

    def test_shared_inode_group_requires_every_current_alias_and_rejects_outside_or_changed(self):
        store=self.base/'immutable-store';store.mkdir();alias=store/'pinned-input'
        os.link(self.alias_target,alias)
        self.recipe['known_readonly_hardlinks']=[sorted([str(alias),str(self.alias_target)])]
        with self.assertRaisesRegex(census.CensusRefused,'escaped source/import'):self.capture()
        self.recipe['source_roots'].append(str(store))
        def mutate():
            alias.unlink();alias.write_bytes(b'foreign');alias.chmod(0o444)
        with self.assertRaisesRegex(census.CensusRefused,'changed between fresh passes'):
            self.capture(_between_passes=mutate)

    def test_provider_mode_exclusion_pig_multiple_root_and_unfinished_supplement_fail_closed(self):
        original=copy.deepcopy(self.recipe)
        changes={'mode':'filesystem_only','exclusion':{'mode':'exclude','name':'texture_library'},
            'pig_providers':[{'claimed_nonoverlap':True}],'gdd_roots':[str(self.root),str(self.imported)],
            'supplements_finalized':1,'wine_source_commit':'0'*40}
        for key,value in changes.items():
            self.recipe=copy.deepcopy(original);self.recipe[key]=value
            with self.subTest(key=key),self.assertRaises(census.CensusRefused):self.capture()
        self.recipe=original

    def test_actual_pig_blob_is_captured_only_and_never_claims_member_authority(self):
        pigs=self.root.parent/'piggs';pigs.mkdir();pig=pigs/'animations.pigg'
        pig.write_bytes(b'UNEXECUTED_UNIT_PIG_BYTES')
        self.recipe['pig_providers']=[pin(pig)]
        _,report=self.capture()
        self.assertEqual(report['current_pig_blob_facts'][0]['sha256'],pin(pig)['sha256'])
        self.assertFalse(report['native_pig_index_complete'])
        self.assertFalse(report['native_pig_branch_nonoverlap_qualified'])
        self.assertFalse(report['native_registration_allowed'])
        self.recipe['pig_providers'][0]['claimed_members']=['animations/test.anim']
        with self.assertRaises(census.CensusRefused):self.capture()

    def test_unannounced_pig_or_extra_native_data_root_requires_fallback(self):
        for extra in ('localdata','serverdata','gamedatadir.txt'):
            target=self.root.parent/extra;target.write_bytes(b'unknown provider')
            with self.subTest(extra=extra),self.assertRaisesRegex(census.CensusRefused,'additional native source'):self.capture()
            target.unlink()
        pigs=self.root.parent/'piggs';pigs.mkdir();(pigs/'unknown.pigg').write_bytes(b'unknown')
        with self.assertRaisesRegex(census.CensusRefused,'PIG discovery differs'):self.capture()

    def test_exact_native_runtime_bytes_and_lifetime_changes_refuse_generation(self):
        consumer=Path(self.recipe['consumer']['path'])
        consumer.write_bytes(b'CORRUPT')
        with self.assertRaises(census.CensusRefused):self.capture()
        consumer.write_bytes(b'UNEXECUTED_UNIT_CONSUMER')
        def mutate():consumer.write_bytes(b'UNEXECUTED_UNIT_CONSUMEX')
        with self.assertRaisesRegex(census.CensusRefused,'Native/runtime changed'):self.capture(_between_passes=mutate)

    def test_current_stat_and_generation_identity_are_not_reused_across_calls(self):
        first,one=self.capture()
        with patch.object(census,'scan',wraps=census.scan) as observed:
            again,two=self.capture()
            self.assertEqual(observed.call_count,2)
        self.assertEqual(one['vector_sha256'],two['vector_sha256'])
        self.assertEqual(one['generation_token'],two['generation_token'])
        other=dict(self.recipe,ignore_prefixes=[])
        _,different=census.capture(self.root,other,'b'*32)
        self.assertNotEqual(one['generation_token'],different['generation_token'])

    def test_alias_hidden_name_and_source_attribute_projection_remain_explicitly_unqualified(self):
        link=self.root/'fx/.hidden-alias';link.symlink_to(self.alias_target)
        with patch.object(census.os,'getxattr',side_effect=OSError(61,'no data')):
            packet,report=self.capture()
        row=next(p for p in self.rows(packet) if p[52:312].split(b'\0',1)[0]==b'.hidden-alias')
        attrs=struct.unpack_from('<I',row,8)[0]
        self.assertEqual(attrs&3,3)
        self.assertEqual(report['native_projection'],'source_derived_consumed_fields_unqualified')
        self.assertFalse(report['native_short_names_observed'])
        self.assertFalse(report['current_access_creation_field_parity_claimed'])

    def test_directory_native_size_is_zero_and_regular_size_and_utc_write_time_are_exact(self):
        packet,_=self.capture();rows=self.rows(packet)
        directory=next(p for p in rows if p[52:312].split(b'\0',1)[0]==b'empty')
        self.assertEqual(struct.unpack_from('<II',directory,36),(0,0))
        regular=next(p for p in rows if p[52:312].split(b'\0',1)[0]==b'linked.texture')
        self.assertEqual(struct.unpack_from('<II',regular,36),(0,self.alias_target.stat().st_size))
        self.assertEqual(struct.unpack_from('<Q',regular,28)[0],census.filetime(self.alias_target.stat().st_mtime_ns))

    def test_unknown_dos_attributes_and_changed_xattrs_do_not_become_false_success(self):
        with patch.object(census.os,'getxattr',side_effect=PermissionError(13,'denied')):
            with self.assertRaisesRegex(census.CensusRefused,'attributes unavailable'):self.capture()
        with patch.object(census.os,'getxattr',return_value=b'not-native-format'):
            with self.assertRaisesRegex(census.CensusRefused,'encoding'):self.capture()
        state=[b'0x2']
        with patch.object(census.os,'getxattr',side_effect=lambda *a,**k:state[0]):
            with self.assertRaisesRegex(census.CensusRefused,'changed between fresh passes'):
                self.capture(_between_passes=lambda:state.__setitem__(0,b'0x4'))

    def test_directory_row_and_packet_caps_refuse_before_native_activation(self):
        for symbol,value in (('MAX_ROWS',2),('MAX_DIRS',2),('MAX_DIRECTORY_ENTRIES',2),('MAX_BYTES',64)):
            with self.subTest(symbol=symbol),patch.object(census,symbol,value),self.assertRaises(census.CensusRefused):self.capture()
        self.assertIsNone(census.PRODUCTION_AUTHORITY);self.assertFalse(census.ACTIVATION_IMPLEMENTED)

    def test_long_native_paths_and_unsearchable_directories_preserve_ordinary_fallback(self):
        folder=self.root/'fx'/('a'*130);folder.mkdir()
        nested=folder/('b'*130);nested.mkdir()
        with self.assertRaisesRegex(census.CensusRefused,'ASCII path'):self.capture()
        nested.rmdir();folder.rmdir()
        folder=self.root/'fx/empty';folder.chmod(0o600)
        with self.assertRaisesRegex(census.CensusRefused,'access differs'):self.capture()
        folder.chmod(0o700)

    def test_scripts_localized_scope_is_explicit_and_not_an_accidental_prefix_match(self):
        self.assertIn('scripts.loc',census.BRANCHES)
        outside=self.root/'scripts_extra';outside.mkdir();(outside/'mutable.dat').write_bytes(b'outside')
        _,report=self.capture()
        self.assertIn('scripts.loc',report['complete_branches'])
        self.assertEqual(report['outscope_root_reference_entries'],2)

    def test_phase_totals_include_full_fresh_validation_and_bounded_encoding(self):
        _,report=self.capture()
        self.assertAlmostEqual(sum(report['phase_seconds'].values()),report['whole_preflight_seconds'],places=4)
        self.assertGreaterEqual(report['process_maxrss_kib_after'],report['process_maxrss_kib_before'])
        self.assertFalse(report['same_operation_observations_reused'])
        self.assertFalse(report['persistent_native_provider_authority_created'])
        self.assertTrue(report['started_at_utc'].endswith('Z'))
        self.assertLessEqual(report['started_at_utc'],report['completed_at_utc'])
        self.assertFalse(report['provider_inputs_changed_by_producer'])

    def test_cli_failure_exports_current_inert_report_without_native_packet_or_input_changes(self):
        output=self.base/'evidence';output.mkdir();recipe_path=self.base/'recipe.json'
        recipe=dict(self.recipe,mode='unsupported');recipe_path.write_text(json.dumps(recipe))
        before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        command=[sys.executable,str(SOURCE),'--data-root',str(self.root),'--recipe',str(recipe_path),
            '--operation-id',self.operation,'--output',str(output)]
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(result.returncode,2,result.stderr)
        report=json.loads((output/('folder-census-'+self.operation+'.json')).read_text())
        self.assertEqual(report['operation_id'],self.operation)
        self.assertEqual(report['status'],'ordinary_native_fallback_required')
        self.assertFalse(report['native_activation_allowed'])
        self.assertFalse(any(output.glob('*.bin')))
        self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_cli_repeated_operation_or_unknown_output_is_preserved_without_unattributed_packet(self):
        output=self.base/'evidence';output.mkdir();recipe_path=self.base/'recipe.json'
        recipe_path.write_text(json.dumps(self.recipe))
        command=[sys.executable,str(SOURCE),'--data-root',str(self.root),'--recipe',str(recipe_path),
            '--operation-id',self.operation,'--output',str(output)]
        report_path=output/('folder-census-'+self.operation+'.json')
        report_path.write_bytes(b'UNRELATED_PREEXISTING_EVIDENCE')
        result=subprocess.run(command,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('preserve prior evidence',result.stderr)
        self.assertEqual(report_path.read_bytes(),b'UNRELATED_PREEXISTING_EVIDENCE')
        self.assertFalse(any(output.glob('*.bin')))
        report_path.unlink()
        first=subprocess.run(command,capture_output=True,text=True)
        self.assertEqual(first.returncode,0,first.stderr)
        before={p.name:p.read_bytes() for p in output.iterdir()}
        second=subprocess.run(command,capture_output=True,text=True)
        self.assertNotEqual(second.returncode,0)
        self.assertEqual(before,{p.name:p.read_bytes() for p in output.iterdir()})


if __name__ == '__main__':unittest.main()
