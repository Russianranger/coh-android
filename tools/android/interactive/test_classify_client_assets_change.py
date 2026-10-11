"""Explicit .28 ownership avoids duplicate builds without hiding foreign edits."""
import unittest
import classify_client_assets_change as change
import classify_storage_cleanup_change as storage
import classify_interactive_change as interactive

class AssetOwnership(unittest.TestCase):
    def test_all_retained_publishers_defer_only_for_closed_explicit_028_scope(self):
        names=sorted(change.CLIENT_ASSETS_ALLOWED)
        functions=[getattr(storage,name) for name in dir(storage) if name.endswith('_required')]
        functions.append(interactive.runtime_required)
        self.assertTrue(change.client_assets_owned('push','a'*40,'b'*40,'a'*40,names))
        self.assertEqual(len(functions),16)
        for function in functions:
            with self.subTest(function=function.__name__):
                self.assertFalse(function('push','a'*40,'b'*40,'a'*40,names))
                for extra in ('upstream/ouroboros/Game/src/render/thread/rt_queue.c',
                    'upstream/ouroboros/MapServer/src/svr/svrinit.c','android/guest/native_responsiveness_contract.py',
                    'android/interactive/src/main/AndroidManifest.xml','assets/reference-inputs-manifest.json','foreign.py'):
                    self.assertTrue(function('push','a'*40,'b'*40,'a'*40,names+[extra]),extra)

    def test_dispatch_history_ambiguity_and_unmarked_shared_edits_do_not_skip(self):
        names=sorted(change.CLIENT_ASSETS_ALLOWED)
        for event,before,head,parent in (('workflow_dispatch','a'*40,'b'*40,'a'*40),
            ('pull_request','a'*40,'b'*40,'a'*40),('push','c'*40,'b'*40,'a'*40),
            ('push','0'*40,'b'*40,'0'*40),('push','a'*40,'a'*40,'a'*40),
            ('push','a'*40,'b'*40,None)):
            with self.subTest(event=event,before=before,parent=parent):
                self.assertFalse(change.client_assets_owned(event,before,head,parent,names))
        self.assertFalse(change.client_assets_owned('push','a'*40,'b'*40,'a'*40,['android/guest/game_diagnostic.py']))
        self.assertTrue(change.client_assets_owned('push','a'*40,'b'*40,'a'*40,[
            'android/guest/game_diagnostic.py','tools/android/interactive/release-client-assets-0.13.28.json']))

    def test_classifier_does_not_own_retained_game_or_dbserver_compile_inputs(self):
        for name in change.CLIENT_ASSETS_ALLOWED:
            self.assertFalse(name.startswith('upstream/'))
            self.assertFalse(name.startswith('database/client-'))
            self.assertFalse(name.startswith('database/startup-dbserver/'))
            self.assertFalse(name.startswith('patches/client-'))
