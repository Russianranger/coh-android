"""ARM64-lane creator transition checks (Astra review 5672637914, comment 6451908706)."""
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest'), str(ROOT / 'tools/android/interactive')]
import interactive_host as host


def tsv(words):
    """Tesseract TSV rows: (text, confidence)."""
    lines = ['level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext']
    for text, conf in words:
        lines.append('5\t1\t1\t1\t1\t1\t0\t0\t10\t10\t%s\t%s' % (conf, text))
    return '\n'.join(lines) + '\n'


# Tokens measured by Astra on the retained frames.
FAILED_POWERS = tsv([('PRIMARY', 78.56), ('POWERS', 81.58), ('Choose', 62.32), ('Primary', 94.66)])
AFTER_BODY = tsv([('HEAD', 91.62), ('Colors', 90.72), ('Linked', 37.04)])
AFTER_POWERS = tsv([('Body', 61.88)])


class CreatorTransitions(unittest.TestCase):
    def test_ocr_predicates_match_the_retained_frames(self):
        self.assertTrue(host.primary_selection_pending(FAILED_POWERS))
        self.assertFalse(host.primary_selection_pending(AFTER_BODY))
        self.assertFalse(host.primary_selection_pending(tsv([('Choose', 50), ('Secondary', 80)])))
        self.assertFalse(host.primary_selection_pending(tsv([('Choose', 10), ('Primary', 15)])))  # below confidence
        self.assertTrue(host.costume_page_shown(AFTER_BODY))
        self.assertFalse(host.costume_page_shown(AFTER_POWERS))  # the Body tab label is not page proof
        self.assertFalse(host.costume_page_shown(FAILED_POWERS))

    def test_checks_follow_their_actions_and_the_shared_script_is_unchanged(self):
        names = [action[2] for action in host.ArmPortCharacterInteraction.ACTIONS]
        self.assertEqual(names[names.index('select_primary_power') + 1], 'verify_primary_power_selected')
        self.assertEqual(names[names.index('body_next') + 1], 'verify_costume_page')
        shared = [action[2] for action in host.character.CharacterInteraction.ACTIONS]
        self.assertNotIn('verify_primary_power_selected', shared)
        added = {'verify_primary_power_selected', 'verify_costume_page'}
        self.assertEqual([n for n in names if n not in added], shared)

    def interaction(self):
        value = host.ArmPortCharacterInteraction.__new__(host.ArmPortCharacterInteraction)
        value.result = {'armport_transition_checks': []}
        value.evidence = Path('/nonexistent')
        value.primary_retries = 0
        value.costume_attempts = 0
        return value

    def run_check(self, value, kind, name, frames):
        with mock.patch.object(host.character, 'read_ocr', side_effect=[(text, 'stem') for text in frames]):
            value.action = [a[2] for a in value.ACTIONS].index(name)
            handled = value.custom_action(kind, None, name, None, SimpleNamespace(), None, 7, 0.0)
        return handled

    def test_unregistered_primary_selection_is_replayed_then_fails_clearly(self):
        value = self.interaction()
        names = [a[2] for a in value.ACTIONS]
        replay = names.index('preposition_select_primary_set') - 1   # on_frame then advances by one
        for attempt in range(host.PRIMARY_RETRIES):
            self.assertTrue(self.run_check(value, 'verify_primary', 'verify_primary_power_selected', [FAILED_POWERS]))
            self.assertEqual(value.action, replay)
        with self.assertRaisesRegex(ValueError, 'Primary power selection did not register'):
            self.run_check(value, 'verify_primary', 'verify_primary_power_selected', [FAILED_POWERS])

    def test_registered_primary_selection_advances(self):
        value = self.interaction()
        index = [a[2] for a in value.ACTIONS].index('verify_primary_power_selected')
        self.assertTrue(self.run_check(value, 'verify_primary', 'verify_primary_power_selected', [AFTER_BODY]))
        self.assertEqual(value.action, index)   # unchanged: on_frame advances past the check
        self.assertEqual(value.result['armport_transition_checks'][-1]['primary_selection_pending'], False)

    def test_costume_page_is_required_before_costume_clicks(self):
        value = self.interaction()
        index = [a[2] for a in value.ACTIONS].index('verify_costume_page')
        self.assertTrue(self.run_check(value, 'verify_costume', 'verify_costume_page', [AFTER_POWERS]))
        self.assertEqual(value.action, index - 1)   # retried on a later frame
        self.assertTrue(self.run_check(value, 'verify_costume', 'verify_costume_page', [AFTER_BODY]))
        self.assertEqual(value.action, index)
        value.costume_attempts = host.COSTUME_ATTEMPTS - 1
        with self.assertRaisesRegex(ValueError, 'Costume page'):
            self.run_check(value, 'verify_costume', 'verify_costume_page', [AFTER_POWERS])


if __name__ == '__main__':
    unittest.main()
