"""Pinned readonly package sources may share an inode; mutable or extracted files may not."""
import os
from pathlib import Path
import shutil
import unittest

import test_atlas_world_assets as world_fixture
import test_client_visual_assets as visual_fixture
import test_atlas_beacon_package as beacon_fixture
import test_client_animation_package as animation_fixture
import test_character_avatar_assets as avatar_fixture


class SharedAssetInputsTests(unittest.TestCase):
    def fixture(self, cls):
        item=cls();item.setUp();self.addCleanup(item.doCleanups);return item

    def share(self,path):
        path.chmod(0o444);other=path.with_name(path.name+'.shared');os.link(path,other)
        return other

    def test_world_archive_and_manifest_share_but_installed_outputs_remain_single_link(self):
        case=self.fixture(world_fixture.WorldInstallTests);world=world_fixture.world
        for name in (world.MANIFEST,world.ARCHIVE):self.share(case.root/name)
        result=world.install(case.work,case.root,case.context);self.assertEqual(2,result['installed_files'])
        self.assertEqual('unchanged_filesystem_receipt',world.install(case.work,case.root,case.context)['reuse_validation'])
        target=case.work/next(iter(case.files));self.share(target)
        with self.assertRaisesRegex(world.client.base.DiagnosticError,'Invalid world supplement'):
            world.install(case.work,case.root,case.context)

    def test_writable_hardlinked_world_source_is_not_accepted(self):
        case=self.fixture(world_fixture.WorldInstallTests);world=world_fixture.world
        archive=case.root/world.ARCHIVE;os.link(archive,archive.with_name('writable-shared'))
        with self.assertRaisesRegex(world.client.base.DiagnosticError,'Invalid world supplement'):
            world.install(case.work,case.root,case.context)

    def test_readonly_foreign_archive_bytes_still_fail_the_reviewed_hash(self):
        case=self.fixture(world_fixture.WorldInstallTests);world=world_fixture.world
        archive=case.root/world.ARCHIVE;data=bytearray(archive.read_bytes());data[0]^=1;archive.write_bytes(data);self.share(archive)
        with self.assertRaisesRegex(world.client.base.DiagnosticError,'archive differs from reviewed'):
            world.install(case.work,case.root,case.context)
        self.assertFalse((case.work/world.MARKER).exists())

    def test_visual_source_archive_and_manifest_share_without_mutating_store(self):
        case=self.fixture(visual_fixture.InstallerTests);visual=visual_fixture.visual
        paths=[case.assets/visual.MANIFEST,case.assets/visual.ARCHIVE]
        for path in paths:self.share(path)
        before=[(p.stat().st_mode,p.stat().st_mtime_ns,p.read_bytes()) for p in paths]
        self.assertEqual(2,case.run_install()['installed_files']);self.assertTrue(case.run_install()['fingerprint_reused'])
        self.assertEqual(before,[(p.stat().st_mode,p.stat().st_mtime_ns,p.read_bytes()) for p in paths])

    def test_beacon_pinned_source_shares_but_output_graph_stays_private(self):
        case=self.fixture(beacon_fixture.AtlasBeaconPackageTests)
        self.share(case.manifest);self.share(case.archive)
        case.install();target=case.runtime/beacon_fixture.package.GRAPH
        self.assertEqual(1,target.stat().st_nlink)
        self.share(target)
        with self.assertRaisesRegex(ValueError,'Linked|beacon'):
            case.install()

    def test_animation_pack_and_manifest_share_without_chmod_of_other_generations(self):
        case=self.fixture(animation_fixture.ClientAnimationPackageTests)
        for path in (case.pigg,case.manifest):self.share(path)
        before=[(p.stat().st_mode,p.stat().st_ctime_ns,p.stat().st_nlink) for p in (case.pigg,case.manifest)]
        self.assertFalse(case.install()['reused']);self.assertTrue(case.install()['reused'])
        self.assertEqual(before,[(p.stat().st_mode,p.stat().st_ctime_ns,p.stat().st_nlink) for p in (case.pigg,case.manifest)])

    def test_avatar_pinned_source_shares_but_backing_payload_must_not(self):
        case=self.fixture(avatar_fixture.AvatarAssetsTests);avatar=avatar_fixture.avatar
        assets=case.root/'shared-avatar';assets.mkdir()
        for name in (avatar.MANIFEST,avatar.ARCHIVE):shutil.copyfile(case.assets/name,assets/name);self.share(assets/name)
        result=avatar.install(case.work,assets,case.context);self.assertEqual(21,result['installed_files'])
        target=case.work/case.first;self.share(target)
        with self.assertRaisesRegex(avatar.client.base.DiagnosticError,'Invalid avatar'):
            avatar.install(case.work,assets,case.context)
