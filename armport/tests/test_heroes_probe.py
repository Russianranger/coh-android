"""0.13.87, CI only: the heroes probe (a second hero made from the character list, then the first one chosen)."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest'), str(ROOT / 'tools/android/interactive'),
                str(Path(__file__).resolve().parent)]
import interactive_host as host
from test_creator_transitions import tsv


class HeroesProbe(unittest.TestCase):
    def test_the_second_hero_s_script_opens_the_second_slot_and_then_follows_the_creator(self):
        names = [action[2] for action in host.SecondHeroInteraction.ACTIONS]
        start = names.index('wait_existing_character_list')
        self.assertEqual(names[start + 1:start + 5], ['clear_cursor_before_second_slot',
            'preposition_open_second_character_creator', 'open_second_character_creator', 'verify_creator_opened'])
        actions = dict((action[2], action) for action in host.SecondHeroInteraction.ACTIONS)
        self.assertEqual(actions['open_second_character_creator'][1], host.SECOND_SLOT)
        self.assertEqual(actions['enter_character_name'][1], host.SECOND_HERO)
        self.assertNotIn('open_character_creator', names)       # the first slot holds the first hero
        # From the origin page on it is the first hero's creator script, with its page checks.
        first = [action[2] for action in host.ArmPortCharacterInteraction.ACTIONS]
        tail = first[first.index('preposition_select_primal_earth'):]
        self.assertEqual(names[-len(tail):], tail)
        self.assertRegex(host.SECOND_HERO, r'\A[A-Z]{3,15}\Z')
        self.assertNotEqual(host.SECOND_HERO, host.character.CHARACTER)

    def test_the_creator_is_recognised_by_its_origin_page(self):
        self.assertIs(host.creator_opened(tsv([('Primal', 90), ('Earth', 88), ('Praetorian', 80)])), True)
        listed = tsv([('THORHERO', 90), ('Create', 85), ('Character', 85)])
        self.assertIs(host.creator_opened(listed, 'THORHERO'), False)      # the list is still shown
        self.assertIsNone(host.creator_opened(tsv([('Origin', 90), ('Next', 85)]), 'THORHERO'))
        self.assertIsNone(host.creator_opened(listed))

    def proof(self, **changes):
        proof = {'verified': True, 'created_in_session': True, 'name': host.SECOND_HERO, 'character_id': 2,
                 'saved_heroes_at_start': 1, 'map_id': 1,
                 'heroes': {'count': 1, 'expected_character_id': 1, 'chosen_character_id': 2,
                            'choice': 'created_in_the_character_list'}}
        proof.update(changes)
        return {'passed': True, 'character_reopen': proof}

    def test_the_second_hero_must_be_followed_as_made_in_the_character_list(self):
        summary = host.heroes_probe_validate(self.proof(), created=True)
        self.assertEqual((summary['character_id'], summary['created_in_session']), (2, True))
        for change in ({'created_in_session': False}, {'character_id': 1}, {'name': 'THORHERO'},
                       {'baseline_character_id': 2}, {'verified': False},
                       {'heroes': {'count': 1, 'expected_character_id': 1, 'chosen_character_id': 2,
                                   'choice': 'another_saved_hero'}}):
            with self.subTest(change=change), self.assertRaises(Exception):
                host.heroes_probe_validate(self.proof(**change), created=True)

    def test_the_first_hero_must_be_followed_as_another_saved_hero(self):
        chosen = {'verified': True, 'character_id': 1, 'baseline_character_id': 1, 'before_character_id': 1,
                  'name': 'THORHERO', 'login_count': 3, 'before_login_count': 2, 'map_id': 1,
                  'heroes': {'count': 2, 'expected_character_id': 2, 'chosen_character_id': 1,
                             'choice': 'another_saved_hero'}}
        report = {'passed': True, 'character_reopen': chosen}
        self.assertEqual(host.heroes_probe_validate(report, created=False)['character_id'], 1)
        for change in ({'character_id': 2}, {'login_count': 2}, {'created_in_session': True},
                       {'heroes': dict(chosen['heroes'], chosen_character_id=None, choice=None)},
                       {'heroes': dict(chosen['heroes'], expected_character_id=1)}):
            with self.subTest(change=change), self.assertRaises(Exception):
                host.heroes_probe_validate({'passed': True, 'character_reopen': dict(chosen, **change)}, created=False)


if __name__ == '__main__':
    unittest.main()
