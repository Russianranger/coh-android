"""Closed-source overlay and dormant lifetime checks, not native execution."""
from pathlib import Path
import os
import unittest
import prepare_live_native_source as source

ROOT = Path(os.environ.get('COH_LIVE_REPOSITORY',str(Path(__file__).resolve().parents[2]/'client-census-wine-037'))).resolve()
UPSTREAM = ROOT/'upstream/ouroboros'


class SourceOverlay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan,cls.patched=source.source_plan(UPSTREAM,ROOT)
        cls.original=(UPSTREAM/source.SOURCE).read_text()

    def test_inherits_exact_qualified_game_source_layers(self):
        self.assertEqual(self.plan['native_Game_predecessor_sha256'],
                         '5eed5c92eadccff067c2821d82601578f825f758ba12842b2d40af99208f1546')
        effective,_=source.retained_effective_game(UPSTREAM,ROOT)
        text=self.patched[source.GAME].decode()
        removed=text.replace('#if defined(COH_CLIENT_LIVE_DIRECTORY)\n    FolderCacheLiveDirectorySetMainThread();\n#endif\n','',1)
        removed=removed.replace('#if defined(COH_CLIENT_LIVE_DIRECTORY)\n    FolderCacheLiveDirectoryStop();\n#endif\n','',1)
        self.assertEqual(removed.encode(),effective)

    def test_literal_entry_body_and_native_recursion_are_retained(self):
        text=self.patched[source.SOURCE].decode()
        helper=source.function(text,'static void cohFolderCacheAddLiveEntry(')
        self.assertIn(source.entry_body(self.original).replace('continue;','return;'),helper)
        original=source.function(self.original,source.SIGNATURE)
        patched=source.function(text,source.SIGNATURE)
        recursion='    for(node2 = *node; node2; node2 = node2->next){'
        self.assertEqual(original.split(recursion,1)[1],patched.split(recursion,1)[1])
        self.assertLess(patched.index('cohLiveNativeClose(coh_live_directory)'),patched.index(recursion))
        self.assertLess(patched.index('fwFindClose(handle)'),patched.index(recursion))

    def test_original_lookup_provider_and_timestamp_code_unchanged(self):
        text=self.patched[source.SOURCE].decode()
        for signature in ('FolderNode *FolderCacheQuery(', 'FolderNode *FolderCacheFileSystemOverride('):
            # The conditional Xbox alternate branches have duplicate lexical
            # braces. Both entire unchanged tails are stronger than a naive
            # preprocessor-unaware function-body extraction.
            self.assertEqual(text.split(signature,1)[1],self.original.split(signature,1)[1])
        self.assertNotIn('coh_live', (UPSTREAM/source.NODE).read_text())
        self.assertIn('_FileTimeToUnixTime(&wfd.ftLastWriteTime, &utc_time, FALSE)',text)

    def test_native_main_thread_precedes_initialization_and_stop_precedes_callbacks(self):
        text=self.patched[source.GAME].decode()
        before=source.function(text,'void game_beforeParseArgs(')
        loop=source.function(text,'void game_beforeLoop(')
        self.assertLess(before.index('FolderCacheLiveDirectorySetMainThread'),before.index('FolderCacheChooseMode'))
        self.assertLess(loop.index('FolderCacheLiveDirectoryStop'),loop.index('FolderCacheEnableCallbacks(1)'))
        self.assertLess(loop.index('FolderCacheLiveDirectoryStop'),loop.index('checkQuickLogin'))

    def test_exact_global_cache_registration_after_all_native_pigs(self):
        pig=source.function(self.patched[source.SOURCE].decode(),'int FolderCacheAddAllPigs(')
        self.assertLess(pig.index('FolderCacheAddPig'),pig.index('cohLiveNativeRegisterCache'))
        self.assertIn('if (fc == folder_cache)',pig)
        self.assertFalse(self.plan['native_registration_allowed'])
        self.assertFalse(self.plan['publication_allowed'])

    def test_changed_stock_loop_or_duplicate_hook_refuses(self):
        for value in (self.original.replace('    do {\n','    do { \n',1),
                      self.original+self.original,
                      self.original.replace('    strcpy(buffer, basepath);','    strcpy(buffer, "other");',1)):
            with self.assertRaises((ValueError,IndexError)):
                source.patch_cache(value)

    def test_msvc_compile_gate_is_private_game_only(self):
        cmake=(Path(__file__).parent/'coh_live_directory.cmake').read_text()
        self.assertIn('COX_BUILD_MAPSERVER OR COX_BUILD_BEACONSERVER',cmake)
        self.assertIn('target_compile_definitions(UtilitiesLib PRIVATE COH_CLIENT_LIVE_DIRECTORY=1)',cmake)
        self.assertIn('target_compile_definitions(Game PRIVATE COH_CLIENT_LIVE_DIRECTORY=1)',cmake)
        self.assertNotIn('COH_CLIENT_METADATA_CENSUS',cmake)
        self.assertNotIn('PUBLIC',cmake)


if __name__=='__main__':
    unittest.main()
