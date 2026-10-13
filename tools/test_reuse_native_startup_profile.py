#!/usr/bin/env python3
"""Exact historical artifact admission; no generic Windows path repair."""
import argparse
import copy
import json
from pathlib import Path, PureWindowsPath
import shutil
import tempfile
import unittest

import reuse_native_startup_profile as reuse

PACKAGE = None


class RecipeTests(unittest.TestCase):
    def recipe(self):
        cg=copy.deepcopy(reuse.package.cg_profile.expected_receipt())
        cg['overlay_sha256']={reuse.WINDOWS_OVERLAY:cg['overlay_sha256'][reuse.POSIX_OVERLAY]}
        return {'repository_commit':reuse.SOURCE,'run_url':f'https://github.com/Russianranger/coh-android/actions/runs/{reuse.RUN}',
            'role':'nonshipping_native_startup_profile','publication_allowed':False,'native_game_executed':False,
            'map_world_entry_executed':False,'physical_device_executed':False,
            'map_profile':reuse.package.map_profile.expected_receipt(),'cg_profile':cg,
            'cg_control_flow':{'source':copy.deepcopy(cg),'status':'passed','native_windows_executed':True,
                'gpu_executed':False,'cases':10}}

    def test_current_overlay_identity_remains_posix_on_windows(self):
        self.assertEqual(str(PureWindowsPath(reuse.package.cg_profile.SOURCE).parent/reuse.package.cg_profile.HEADER),reuse.WINDOWS_OVERLAY)
        self.assertEqual(reuse.package.cg_profile.TARGET,reuse.POSIX_OVERLAY)
        self.assertEqual(set(reuse.package.cg_profile.expected_receipt()['overlay_sha256']),{reuse.POSIX_OVERLAY})

    def test_only_exact_old_recipe_is_admitted(self):
        old=self.recipe();before=copy.deepcopy(old)
        self.assertIs(reuse.validate_recipe(old),old)
        self.assertEqual(old,before)

    def test_other_path_mappings_do_not_become_authority(self):
        for key in (reuse.POSIX_OVERLAY,'Game/../Game/src/render/thread/coh_native_cg_profile.h',
                    'Game\\src/render/thread/coh_native_cg_profile.h','other.h'):
            with self.subTest(key=key):
                value=self.recipe();row=value['cg_profile']['overlay_sha256'];pin=row.pop(reuse.WINDOWS_OVERLAY);row[key]=pin
                with self.assertRaises(ValueError):reuse.validate_recipe(value)

    def test_native_scope_and_producer_cannot_be_upgraded(self):
        for key,replacement in (('repository_commit','0'*40),('publication_allowed',True),
                ('native_game_executed',True),('map_world_entry_executed',True),('physical_device_executed',True),
                ('run_url','https://github.com/Russianranger/coh-android/actions/runs/1')):
            with self.subTest(key=key):
                value=self.recipe();value[key]=replacement
                with self.assertRaises(ValueError):reuse.validate_recipe(value)

    def test_header_or_decoder_drift_is_not_a_path_fix(self):
        for which in ('header','decoder','fixture'):
            with self.subTest(which=which):
                value=self.recipe()
                if which=='header':value['cg_profile']['overlay_sha256'][reuse.WINDOWS_OVERLAY]='0'*64
                if which=='decoder':value['map_profile']['freshness_bypass_enabled']=True
                if which=='fixture':value['cg_control_flow']['cases']=9
                with self.assertRaises(ValueError):reuse.validate_recipe(value)

    def metadata(self):
        return ({'id':reuse.RUN,'head_sha':reuse.SOURCE,'head_branch':'codex/native-startup-profile-036',
            'path':'.github/workflows/android-native-startup-profile.yml','status':'completed','conclusion':'cancelled'},
            {'jobs':[{'id':reuse.JOB,'name':'native','status':'completed','conclusion':'success'}]},
            {'id':reuse.ARTIFACT,'name':'coh-nonshipping-native-startup-profile','expired':False,
                'size_in_bytes':reuse.ZIP['bytes'],'digest':'sha256:'+reuse.ZIP['sha256'],
                'workflow_run':{'id':reuse.RUN,'head_sha':reuse.SOURCE}})

    def test_successful_windows_job_is_retained_without_upgrading_cancelled_run(self):
        value=reuse.validate_metadata(*self.metadata())
        self.assertEqual(value['run_conclusion'],'cancelled')
        self.assertEqual(value['windows_job_conclusion'],'success')
        self.assertFalse(reuse.provenance()['overall_historical_workflow_claimed_successful'])

    def test_wrong_job_artifact_and_source_metadata_fail(self):
        for which in ('job','source','artifact','digest','expired'):
            with self.subTest(which=which):
                run,jobs,artifact=self.metadata()
                if which=='job':jobs['jobs'][0]['conclusion']='failure'
                if which=='source':run['head_sha']='0'*40
                if which=='artifact':artifact['id']+=1
                if which=='digest':artifact['digest']='sha256:'+'0'*64
                if which=='expired':artifact['expired']=True
                with self.assertRaises(ValueError):reuse.validate_metadata(run,jobs,artifact)

    def test_unknown_zip_is_rejected_before_creating_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);archive=root/'bad.zip';archive.write_bytes(b'unrelated')
            with self.assertRaises(ValueError):reuse.extract(archive,root/'out')
            self.assertFalse((root/'out').exists())


class ActualArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if PACKAGE is None:raise unittest.SkipTest('Pass --package for exact historical native artifact tests')

    def test_actual_original_receipt_and_all_native_bytes_are_accepted_unchanged(self):
        before={n:reuse.package.pin(PACKAGE/n) for n in reuse.FILES}
        value=reuse.validate_package(PACKAGE)
        self.assertEqual(value['repository_commit'],reuse.SOURCE)
        self.assertEqual(before,{n:reuse.package.pin(PACKAGE/n) for n in reuse.FILES})

    def test_new_generic_package_gate_correctly_refuses_original_platform_recipe(self):
        with self.assertRaisesRegex(ValueError,'source recipe changed'):
            reuse.package.validate(PACKAGE,reuse.SOURCE)

    def test_one_byte_mutated_native_is_not_historical(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'package';shutil.copytree(PACKAGE,target)
            path=target/'MapServer-profile.exe'
            with path.open('r+b') as f:f.seek(-1,2);b=f.read(1);f.seek(-1,2);f.write(bytes([b[0]^1]))
            with self.assertRaisesRegex(ValueError,'member changed'):reuse.validate_package(target)

    def test_same_bytes_at_linked_input_are_refused(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'package';target.symlink_to(PACKAGE,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'Regular private'):reuse.validate_package(target)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True)
    args=p.parse_args();PACKAGE=args.package.resolve()
    unittest.main(argv=['test_reuse_native_startup_profile'])
