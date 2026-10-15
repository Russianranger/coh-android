"""Immediate events compose after progress without touching immutable source."""
import copy
import json
from pathlib import Path
import unittest

import prepare_character_events_source as events
import test_prepare_mapserver_progress_source as fixture


class CharacterEventsSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.MapServerProgressSourceTests.setUpClass()
        cls.expected = events.expected_events_receipt()

    def setUp(self):
        base = fixture.MapServerProgressSourceTests()
        base.setUp()
        self.addCleanup(base.doCleanups)
        self.source = base.source
        self.progress = events.progress.apply_progress_overlay(self.source)

    def test_composes_exact_after_progress_preserves_old_receipts_and_immutable_sources(self):
        immutable = {name: events.sha256(events.ROOT / 'upstream/ouroboros' / name)
                     for name in events.EVENTS_FILES}
        receipts = {name: (self.source / name).read_bytes() for name in
                    (events.progress.RECEIPT, events.progress.game.RECEIPT, 'postgresql-build-input.json')}
        actual = events.apply_events_overlay(self.source)
        self.assertEqual(actual, self.expected)
        self.assertEqual(actual['progress_build_input'], self.progress)
        self.assertEqual({name: (self.source / name).read_bytes() for name in receipts}, receipts)
        self.assertEqual({name: events.sha256(self.source / name) for name in events.EVENTS_FILES},
                         actual['patched_sha256'])
        self.assertEqual({name: events.sha256(self.source / name) for name in events.OVERLAY_FILES},
                         actual['events_overlay_sha256'])
        self.assertEqual({name: events.sha256(events.ROOT / 'upstream/ouroboros' / name)
                          for name in immutable}, immutable)
        self.assertEqual(json.loads((self.source / events.RECEIPT).read_text()), actual)
        tick = (self.source / 'MapServer/src/svr/svr_tick.c').read_text()
        resumed = tick.index('cohCharacterEventReady(')
        self.assertGreater(resumed, tick.index('resumeResult = resumeCharacter('))
        self.assertGreater(resumed, tick.index('else if (resumeResult == -1)'))
        self.assertIn('if(timerSecondsSince2000CheckAndSet(&periodic_timer,30))', tick)
        self.assertIn('if (e && e->ready && !e->dbcomm_state.map_xfer_step)', tick)

    def test_dirty_progress_game_pg_and_overlay_are_rejected_before_mutation(self):
        native = self.progress
        game = native['game_build_input']
        for name in (events.EVENTS_FILES[-1], next(iter(native['progress_overlay_sha256'])),
                     next(iter(game['patched_sha256'])),
                     next(iter(game['postgresql_build_input']['overlay_sha256']))):
            with self.subTest(name=name):
                path = self.source / name
                original = path.read_bytes()
                path.write_bytes(original + b'\n// dirty\n')
                before = {name: events.sha256(self.source / name) for name in events.EVENTS_FILES}
                with self.assertRaisesRegex(ValueError, 'Staged character event source SHA-256 mismatch'):
                    events.apply_events_overlay(self.source)
                self.assertEqual(before, {name: events.sha256(self.source / name) for name in events.EVENTS_FILES})
                self.assertFalse((self.source / events.RECEIPT).exists())
                path.write_bytes(original)

    def test_stale_receipts_links_repeat_and_upstream_do_not_modify_anything(self):
        path = self.source / events.progress.RECEIPT
        original = path.read_bytes()
        stale = copy.deepcopy(self.progress)
        stale['source_commit'] = 'f' * 40
        path.write_text(json.dumps(stale))
        with self.assertRaisesRegex(ValueError, 'progress source receipt mismatch'):
            events.apply_events_overlay(self.source)
        path.write_bytes(original)
        overlay = self.source / events.OVERLAY_FILES[0]
        overlay.write_text('foreign')
        with self.assertRaisesRegex(ValueError, 'would overwrite source'):
            events.apply_events_overlay(self.source)
        overlay.unlink()
        overlay.symlink_to(self.source / events.EVENTS_FILES[-1])
        with self.assertRaisesRegex(ValueError, 'would overwrite source'):
            events.apply_events_overlay(self.source)
        overlay.unlink()
        events.apply_events_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            events.apply_events_overlay(self.source)
        with self.assertRaisesRegex(ValueError, 'immutable snapshots'):
            events.apply_events_overlay(events.ROOT / 'upstream/ouroboros')


if __name__ == '__main__': unittest.main(verbosity=2)
