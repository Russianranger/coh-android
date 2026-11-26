"""0.13.88, CI only: the single-player probe makes and reopens a real Primalist."""
import contextlib
import io
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'armport/app'), str(ROOT / 'android/guest'), str(ROOT / 'tools/android/interactive'),
                str(Path(__file__).resolve().parent)]
import interactive_host as host


def probe(**values):
    names = ('COH_SINGLE_PLAYER_PROBE', 'COH_SINGLE_PLAYER_PROBE_PART', host.HEROES_PROBE_ENV)
    return mock.patch.dict(os.environ, {name: values.get(name, '') for name in names})


class PrimalistProbe(unittest.TestCase):
    def test_the_script_picks_melee_and_the_bar_named_primalist(self):
        names = [action[2] for action in host.PrimalistCharacterInteraction.ACTIONS]
        actions = dict((action[2], action) for action in host.PrimalistCharacterInteraction.ACTIONS)
        self.assertEqual(actions['select_melee_playstyle'], ('click', host.MELEE_PLAYSTYLE, 'select_melee_playstyle'))
        self.assertEqual(actions['preposition_select_primalist'],
                         ('ocr_move', ('Primalist', host.ARCHETYPE_LIST_REGION), 'preposition_select_primalist'))
        self.assertEqual(actions['select_primalist'][0], 'ocr_click')
        for gone in ('select_ranged_playstyle', 'select_blaster', 'preposition_select_blaster'):
            self.assertNotIn(gone, names)
        # Everything else is the first hero's creator script, in its order, with its page checks.
        first = [action[2] for action in host.ArmPortCharacterInteraction.ACTIONS]
        same = lambda items: [name for name in items if 'playstyle' not in name.replace('playstyle_next', '')
                              and 'blaster' not in name and 'primalist' not in name]
        self.assertEqual(same(names), same(first))
        self.assertLess(names.index('select_melee_playstyle'), names.index('playstyle_next'))
        self.assertLess(names.index('playstyle_next'), names.index('select_primalist'))
        self.assertLess(names.index('select_primalist'), names.index('archetype_next'))
        self.assertIn('verify_primary_power_selected', names); self.assertIn('verify_costume_page', names)
        # The second play style of uiPlaystyle.c's list; the region covers the seven visible bars.
        self.assertEqual(host.MELEE_PLAYSTYLE[1], round((130 + 57) * 600 / 768))
        left, top, right, bottom = host.ARCHETYPE_LIST_REGION
        self.assertLessEqual(top, 103 * 600 / 768); self.assertGreaterEqual(bottom, (103 + 7 * 54) * 600 / 768 - 2)

    def test_only_the_probe_with_the_primalist_makes_one(self):
        with probe():
            self.assertFalse(host.primalist_creation_requested())
        with probe(COH_SINGLE_PLAYER_PROBE='1'):
            self.assertTrue(host.primalist_creation_requested())
        with probe(COH_SINGLE_PLAYER_PROBE='1', COH_SINGLE_PLAYER_PROBE_PART='primalist'):
            self.assertTrue(host.primalist_creation_requested())
        with probe(COH_SINGLE_PLAYER_PROBE='1', COH_SINGLE_PLAYER_PROBE_PART='unlock'):
            self.assertFalse(host.primalist_creation_requested())
        with probe(COH_SINGLE_PLAYER_PROBE='1', **{host.HEROES_PROBE_ENV: '1'}):
            self.assertFalse(host.primalist_creation_requested())

    def observer(self, interaction, buttons):
        names = [action[2] for action in interaction.ACTIONS]
        check, costume = names.index('verify_primary_power_selected'), names.index('verify_costume_page')
        steps = [{'action': name, 'order': index} for index, name in enumerate(names)]
        checks = [{'check': 'verify_primary_power_selected', 'retry': 0, 'primary_selection_pending': False,
                   'evidence': 'p'}, {'check': 'verify_costume_page', 'attempt': 1, 'costume_page_shown': True,
                                      'evidence': 'c'}]
        return {'interaction_script': {'steps': steps, 'armport_transition_checks': checks,
                                       'account_entry_checks': [{}], 'ocr_buttons': buttons}}

    def test_the_host_validator_follows_the_primalist_s_script(self):
        # Run 45875126986: the Primalist was made and saved, and the host then compared the
        # steps with the first hero's script ("Graphical creator script did not finish").
        stock = [{'label': label, 'x': 400, 'y': 300} for label in ('a', 'b', 'c')]
        bar = {'label': 'Primalist', 'x': 180, 'y': 140, 'confidence': 91}
        observer = self.observer(host.PrimalistCharacterInteraction, stock[:1] + [bar] + stock[1:])
        with mock.patch.object(host.character, 'validate_observer') as shared:
            host.armport_validate_observer(observer, {}, host.PrimalistCharacterInteraction)
        script = shared.call_args[0][0]['interaction_script']
        self.assertEqual([step['action'] for step in script['steps']],
                         [action[2] for action in host.character.CharacterInteraction.ACTIONS])
        self.assertEqual(script['ocr_buttons'], stock)
        renamed = {step['primalist_probe_action']: step['action'] for step in script['steps']
                   if 'primalist_probe_action' in step}
        self.assertEqual(renamed, {old: new for old, new in host.PRIMALIST_STEPS if new})
        orders = [step['order'] for step in script['steps']]
        self.assertEqual(orders, sorted(orders))
        # The observer itself is left as it was recorded.
        self.assertEqual(len(observer['interaction_script']['ocr_buttons']), 4)
        self.assertIn('select_primalist', [step['action'] for step in observer['interaction_script']['steps']])
        with mock.patch.object(host.character, 'validate_observer'):
            # The first hero's script is not a Primalist's, and the other way round.
            with self.assertRaisesRegex(ValueError, 'did not finish'):
                host.armport_validate_observer(observer, {})
            first = self.observer(host.ArmPortCharacterInteraction, stock)
            host.armport_validate_observer(first, {})
            with self.assertRaisesRegex(ValueError, 'did not finish'):
                host.armport_validate_observer(first, {}, host.PrimalistCharacterInteraction)
            # The bar must have been found once, inside the archetype list.
            for buttons in (stock, stock + [bar, dict(bar)], stock + [dict(bar, y=500)], stock + [dict(bar, x='180')]):
                with self.assertRaisesRegex(ValueError, 'Primalist bar'):
                    host.armport_validate_observer(self.observer(host.PrimalistCharacterInteraction, buttons), {},
                                                   host.PrimalistCharacterInteraction)

    def test_the_archetype_list_of_the_frame_goes_to_the_log(self):
        import base64, io, tempfile
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            evidence = Path(folder)
            frame = Image.new('RGB', (800, 600), (10, 20, 30))
            frame.paste((250, 200, 40), (80, 300, 120, 340))        # an icon inside the list
            frame.paste((0, 255, 0), (500, 300, 540, 340))          # something outside it
            frame.save(evidence / 'preposition_select_primalist-ocr-02.png')
            observer = {'interaction_script': {'ocr_buttons': [
                {'label': 'Next', 'evidence': 'x-ocr-01'},
                {'label': 'Primalist', 'evidence': 'preposition_select_primalist-ocr-02'}]}}
            lines = host.primalist_frame_lines(evidence, observer)
            self.assertTrue(lines and all(line.startswith(
                host.PRIMALIST_FRAME_MARK + 'name=preposition_select_primalist-ocr-02 part=') for line in lines))
            self.assertEqual([line.split(' ')[2] for line in lines],
                             ['part=%d/%d' % (i, len(lines)) for i in range(1, len(lines) + 1)])
            with Image.open(io.BytesIO(base64.b64decode(''.join(line.split(' ')[3] for line in lines)))) as cut:
                left, top, right, bottom = host.PRIMALIST_FRAME_REGION
                self.assertEqual(cut.size, (right - left, bottom - top))
                colours = cut.convert('RGB')
                self.assertEqual(colours.getpixel((100 - left, 320 - top)), (250, 200, 40))
                self.assertNotIn((0, 255, 0), [colour for _, colour in colours.getcolors()])
            # Nothing without a found bar, a retained frame or a plain name.
            self.assertEqual(host.primalist_frame_lines(evidence, {'interaction_script': {'ocr_buttons': []}}), [])
            self.assertEqual(host.primalist_frame_lines(evidence, None), [])
            for stem in ('missing-ocr-01', '../x', 7):
                self.assertEqual(host.primalist_frame_lines(evidence, {'interaction_script': {'ocr_buttons': [
                    {'label': 'Primalist', 'evidence': stem}]}}), [])
            self.assertEqual(host.primalist_frame_lines(evidence, observer, limit=10), [])

    def check(self, report, key):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            name = host.hero_class_check(report, key)
        return name, out.getvalue()

    def test_both_sessions_must_have_saved_a_primalist(self):
        saved = {'character_creation': {'class_name': 'class_primalist'}, 'character_reopen': {'class_name': 'Class_Primalist'}}
        with probe(COH_SINGLE_PLAYER_PROBE='1'):
            for key in saved:
                name, line = self.check(saved, key)
                self.assertEqual(name.casefold(), host.PRIMALIST_CLASS)
                self.assertIn('ARMPORT_HERO_CLASS_V1 {"session":"%s"' % key, line)
            for wrong in ({'character_creation': {'class_name': 'class_scrapper'}}, {'character_creation': {}},
                          {'character_creation': {'class_name': 7}}, {}, None):
                with self.assertRaisesRegex(Exception, 'not a Primalist'):
                    self.check(wrong, 'character_creation')
        # Any other run only names the class.
        with probe():
            self.assertEqual(self.check({'character_creation': {'class_name': 'class_blaster'}}, 'character_creation')[0],
                             'class_blaster')
            self.assertIsNone(self.check({}, 'character_reopen')[0])


if __name__ == '__main__':
    unittest.main()
