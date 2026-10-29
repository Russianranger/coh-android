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

    def observer(self, primary_pending, costume_misses, accounts=1):
        names = [a[2] for a in host.ArmPortCharacterInteraction.ACTIONS]
        retry, account = names.index('preposition_account'), names.index('verify_rendered_account')
        start = names.index('preposition_select_primary_set')
        check, costume = names.index('verify_primary_power_selected'), names.index('verify_costume_page')
        order = (names[:retry] + names[retry:account] * accounts + names[account:start]
                 + names[start:check + 1] * (primary_pending + 1) + names[check + 1:costume]
                 + [names[costume]] * (costume_misses + 1) + names[costume + 1:])
        steps = [{'action': name, 'order': index} for index, name in enumerate(order)]
        checks = [{'check': 'verify_primary_power_selected', 'retry': i, 'primary_selection_pending': i < primary_pending,
                   'evidence': 'p%d' % i} for i in range(primary_pending + 1)]
        checks += [{'check': 'verify_costume_page', 'attempt': i + 1, 'costume_page_shown': i == costume_misses,
                    'evidence': 'c%d' % i} for i in range(costume_misses + 1)]
        return {'interaction_script': {'steps': steps, 'armport_transition_checks': checks,
                                       'account_entry_checks': [{}] * accounts}}

    def shared_expected(self, accounts):
        names = [a[2] for a in host.character.CharacterInteraction.ACTIONS]
        retry, account = names.index('preposition_account'), names.index('verify_rendered_account')
        return names[:retry] + names[retry:account] * accounts + names[account:]

    def test_validator_projects_replays_onto_the_shared_sequence(self):
        for primary, costume, accounts in ((0, 0, 1), (2, 3, 2), (1, 0, 1)):
            observer = self.observer(primary, costume, accounts)
            with mock.patch.object(host.character, 'validate_observer') as shared:
                host.armport_validate_observer(observer, {})
            projected = shared.call_args[0][0]['interaction_script']['steps']
            self.assertEqual([s['action'] for s in projected], self.shared_expected(accounts))
            orders = [s['order'] for s in projected]
            self.assertEqual(orders, sorted(orders))  # the final primary pass is the one kept
            self.assertEqual(len(observer['interaction_script']['steps']) - len(projected),
                             primary * 5 + 1 + costume + 1 if primary else 1 + costume + 1)

    def test_validator_rejects_inconsistent_evidence(self):
        observer = self.observer(1, 0)
        observer['interaction_script']['steps'].pop()
        with mock.patch.object(host.character, 'validate_observer'):
            with self.assertRaisesRegex(ValueError, 'did not finish'):
                host.armport_validate_observer(observer, {})
            observer = self.observer(1, 0)
            observer['interaction_script']['armport_transition_checks'][0]['primary_selection_pending'] = False
            with self.assertRaisesRegex(ValueError, 'transition evidence'):
                host.armport_validate_observer(observer, {})
            observer = self.observer(0, 1)
            observer['interaction_script']['armport_transition_checks'].pop()
            with self.assertRaisesRegex(ValueError, 'transition evidence'):
                host.armport_validate_observer(observer, {})


if __name__ == '__main__':
    unittest.main()
