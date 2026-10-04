#!/usr/bin/env python3
"""Independent boundaries for the native persisted MessageStore source gate."""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).with_name('server_message_source_contract.py')
SPEC = importlib.util.spec_from_file_location('message_source_contract_test_subject', PATH)
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


class MessageSourceContractTests(unittest.TestCase):
    def test_native_sources_are_exact_accepted_mapserver_inputs(self):
        for name, sha in contract.NATIVE_SOURCES.items():
            self.assertEqual(hashlib.sha256((contract.ROOT / name).read_bytes()).hexdigest(), sha)

    def test_native_declarations_cover_five_fixed_files_and_twenty_seven_dirs(self):
        actual = contract.persisted_source_contract()
        self.assertEqual(set(actual['fixed_files']), {
            'data/texts/english/menumessages.ms', 'data/texts/menumessages.types',
            'data/texts/english/powers.txt', 'data/texts/english/storyarcstrings.ms',
            'data/texts/storyarcstrings.types',
        })
        self.assertEqual(set(actual['directory_prefixes']), {'data/texts/english/' + name + '/' for name in (
            'powers', 'badges', 'server/badges_svr', 'server/lockeddoors', 'reward', 'classes',
            'origins', 'boostset', 'attribs', 'bases', 'inventions', 'villains', 'contacts',
            'v_contacts', 'notorietycontacts', 'npcs', 'v_npcs', 'spawndefs', 'storyarcs',
            'alignment_missions', 'supergroupcontacts', 'player_created', 'striketeams',
            'test', 'scriptdefs', 'dialogdefs', 'defs',
        )})

    def test_fixed_txt_and_unlocalized_types_are_forbidden(self):
        for name in contract.persisted_source_contract()['fixed_files']:
            self.assertTrue(contract.is_persisted_source(name))
        self.assertFalse(contract.is_persisted_source('data/texts/english/menumessages.types'))

    def test_all_nonbackup_leaf_extensions_in_native_dirs_are_forbidden(self):
        for prefix in contract.persisted_source_contract()['directory_prefixes']:
            for leaf in ('nested/message.ms', 'name.txt', 'message.def', 'extensionless', 'old.bak2'):
                self.assertTrue(contract.is_persisted_source(prefix + leaf), prefix + leaf)

    def test_uncached_commands_and_other_text_sources_remain_outside_scope(self):
        for name in ('data/texts/english/cmdMessagesServer.ms', 'data/texts/english/copyright.txt',
                     'data/texts/english/server/names/female.txt', 'data/texts/english/server/npc_chatter.txt',
                     'data/texts/english/cebsnar.txt', 'data/texts/english/titles.def',
                     'data/texts/english/unrelated.ms', 'data/player_library/animations/foo.anim'):
            self.assertFalse(contract.is_persisted_source(name), name)

    def test_native_backup_filter_and_directory_boundaries(self):
        for name in ('data/texts/English/Powers/nested/old.BAK', 'data/texts/english/powers-old/a.ms',
                     'data/texts/english/powers/', 'data/texts/french/powers/a.ms'):
            self.assertFalse(contract.is_persisted_source(name), name)

    def test_normalized_slashes_and_case(self):
        self.assertTrue(contract.is_persisted_source(r'DATA\TEXTS\English\POWERS.TXT'))
        self.assertTrue(contract.is_persisted_source(r'data\texts\English\V_Contacts\nested\a.TXT'))

    def test_unsafe_paths_cannot_alias_native_scope(self):
        for name in (None, '', '/data/texts/english/powers/a.ms', 'data/texts/english/powers/../a.ms',
                     'data/texts/english/powers/./a.ms', 'data/texts//english/powers/a.ms'):
            self.assertFalse(contract.is_persisted_source(name), name)

    def test_changed_or_incomplete_native_source_closure_fails_closed(self):
        sources = {name: (contract.ROOT / name).read_bytes() for name in contract.NATIVE_SOURCES}
        altered = dict(sources); name = next(iter(altered)); altered[name] += b'\n'
        with self.assertRaises(ValueError): contract.derive_contract(altered)
        with self.assertRaises(ValueError): contract.derive_contract({name: sources[name]})

    def test_c_comments_preserve_native_scan_pattern_and_quoted_paths(self):
        text = 'char *items[]={"texts/ok",NULL}; /* remove */\n// remove\nprintf("%s/*.*");'
        self.assertEqual(contract.declaration(text, 'items'), ['texts/ok'])
        self.assertIn('"%s/*.*"', contract.uncomment(text))
        self.assertNotIn('remove', contract.uncomment(text))

    def test_native_declaration_rejects_missing_duplicate_or_expressions(self):
        for text in ('', 'char *items[]={"texts/ok"};',
                     'char *items[]={"texts/ok",NULL}; char *items[]={"texts/other",NULL};',
                     'char *items[]={MACRO,NULL};', 'char *items[]={"texts/../bad",NULL};'):
            with self.assertRaises(ValueError): contract.declaration(text, 'items')


if __name__ == '__main__':
    unittest.main()
