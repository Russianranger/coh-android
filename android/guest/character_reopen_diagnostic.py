#!/usr/bin/env python3
"""Reopen preserved THORHERO, recover through /stuck, and save normally."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import character_creation_diagnostic as creation

base, require, character = creation.base, creation.require, creation.character
SCOPE = 'actual_character_reopen_guest'
REQUIRED = creation.REQUIRED | {'character_reopen_diagnostic.py', 'atlas_world_assets.py',
                              'atlas-world-supplement.zip', 'atlas-world-supplement-manifest.json'}


def character_identity(proof, session):
    return (creation.character_identity(proof, session)
        and proof.get('character_id') == 1
        and type(proof.get('before_character_id')) is int and proof['before_character_id'] == 1
        and type(proof.get('baseline_character_id')) is int and proof['baseline_character_id'] == 1
        and all(proof.get(key) is True for key in ('existing_character_verified', 'reopen_verified',
            'preserved_existing_identity', 'native_client_ready_observed')))


def save_verified(proof, session):
    if not (character_identity(proof, session) and creation.save_verified(proof, session)
            and all(proof.get(key) is True for key in ('powers_preserved', 'costume_preserved',
                'selected_rows_preserved', 'ordinary_stuck_observed', 'on_atlas_safe_position',
                'stable_ground_verified', 'committed_safe_position_verified'))):
        return False
    before, after = proof.get('before_login_count'), proof.get('login_count')
    return type(before) is int and 0 < before < 2**31 - 1 and type(after) is int and after == before + 1


class CharacterReopenDiagnostic(creation.CharacterCreationDiagnostic):
    REPORT_KEY = 'character_reopen'
    REQUIRED = REQUIRED
    identity_verified = staticmethod(character_identity)
    proof_verified = staticmethod(save_verified)

    def make_server(self):
        return character.LocalCharacterReopenServer(self)

    def initialize(self):
        request = self.args.state / 'character-relocation.json'
        require(not request.exists() and not request.is_symlink(), 'Stale character recovery delivery receipt')
        super().initialize()

    def connected_event_data(self, proof):
        return {'reopen_verified': True, 'baseline_character_id': proof['baseline_character_id'],
                'existing_character_verified': True, 'preserved_existing_identity': True,
                'native_client_ready_observed': True}

    def saved_event_data(self, proof):
        return {'reopen_verified': True, 'powers_preserved': True, 'costume_preserved': True,
                'preserved_existing_identity': True, 'stable_ground_verified': True}

    def observe_console(self):
        result = super().observe_console()
        proof = self.ctx.report.get(self.REPORT_KEY, {})
        if (self.connected_announced and proof.get('stable_ground_verified') is True
                and not getattr(self, 'relocated_announced', False)):
            require(self.identity_verified(proof, self.args.session_id)
                    and proof.get('ordinary_stuck_observed') is True
                    and proof.get('on_atlas_safe_position') is True
                    and proof.get('client_pid') == result[1]['pid'],
                    'Stable character recovery differs from the current graphical connection')
            self.relocated_announced = True
            self.ctx.event('character_relocated', session_id=self.args.session_id,
                client_pid=proof['client_pid'], character_id=proof['character_id'],
                name=creation.CHARACTER_NAME, account=creation.login.server.ACCOUNT, map_id=1,
                ordinary_stuck_observed=True, on_atlas_safe_position=True, stable_ground_verified=True)
        return result


def main(argv=None):
    return creation.run(argv, CharacterReopenDiagnostic, SCOPE, 'actual_character_reopen')


if __name__ == '__main__':
    sys.exit(main())
