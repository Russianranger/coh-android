#!/usr/bin/env python3
"""Reopen preserved THORHERO and save normally; /stuck is optional recovery."""
from pathlib import Path
import copy
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import character_creation_diagnostic as creation
import character_session_budget as session_budget

base, require, character = creation.base, creation.require, creation.character
SCOPE = 'actual_character_reopen_guest'
REQUIRED = creation.REQUIRED | {'character_reopen_diagnostic.py', 'character_session_budget.py',
                              'stationary_contact_evidence.py', 'atlas_world_assets.py',
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
                'selected_rows_preserved', 'committed_native_position_verified'))
            and type(proof.get('recovery_requested')) is bool
            and (proof['recovery_requested'] is False and all(proof.get(key) is False for key in (
                    'recovery_verified', 'ordinary_stuck_observed', 'on_atlas_safe_position',
                    'stable_ground_verified', 'committed_safe_position_verified'))
                or proof['recovery_requested'] is True and all(proof.get(key) is True for key in (
                    'recovery_verified', 'ordinary_stuck_observed', 'on_atlas_safe_position',
                    'stable_ground_verified', 'committed_safe_position_verified')))):
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
                'preserved_existing_identity': True,
                'committed_native_position_verified': True,
                'recovery_requested': proof['recovery_requested'],
                'recovery_verified': proof['recovery_verified']}

    def interaction_deadline(self, deadline, launch):
        if not self.connected_announced:
            return deadline
        proof = self.ctx.report.get(self.REPORT_KEY, {})
        require(self.identity_verified(proof, self.args.session_id)
                and isinstance(launch, dict) and proof.get('client_pid') == launch.get('pid'),
                'Reopen phase budget lacks the current validated graphical character')
        now, utc_ms = time.monotonic(), int(time.time() * 1000)
        if not hasattr(self, 'session_budget'):
            require(session_budget.finite_seconds(deadline) and now < deadline,
                    'Native connection arrived after the current menu deadline')
            self.session_budget = session_budget.SessionBudget(self.args.session_id, launch['pid'],
                self.launcher_started_monotonic, self.ctx.deadline)
        events = [self.session_budget.connected(proof, now, utc_ms)]
        if getattr(self, 'relocated_announced', False):
            if self.session_budget.revision < 2:
                require(now < self.session_budget.deadline,
                        'Ground verification arrived after the current connected deadline')
            events.append(self.session_budget.grounded(proof, now, utc_ms))
        for event in events:
            if event is not None:
                budgets = self.ctx.report.setdefault('character_session_budgets', [])
                budgets.append(dict(event))
                self.ctx.event('character_session_budget', **event)
        return self.session_budget.deadline

    def observe_console(self):
        result = super().observe_console()
        proof = self.ctx.report.get(self.REPORT_KEY, {})
        ready = proof.get('client_ready_evidence')
        metrics = self.ctx.report.setdefault('character_observer_metrics', {})
        if (self.connected_announced and isinstance(ready, dict)
                and type(proof.get('client_ready_observed_utc_ms')) is int
                and 'native_ready_to_observation_ms' not in metrics):
            native_ms = (ready['utc_ms'] if type(ready.get('utc_ms')) is int else
                int(time.mktime(time.strptime(ready['log_timestamp'], '%y%m%d %H:%M:%S')) * 1000))
            metrics['native_ready_to_observation_ms'] = proof['client_ready_observed_utc_ms'] - native_ms
        if (self.connected_announced and proof.get('recovery_requested') is True
                and proof.get('recovery_verified') is True and proof.get('stable_ground_verified') is True
                and not getattr(self, 'relocated_announced', False)):
            require(self.identity_verified(proof, self.args.session_id)
                    and proof.get('ordinary_stuck_observed') is True
                    and proof.get('on_atlas_safe_position') is True
                    and proof.get('client_pid') == result[1]['pid'],
                    'Stable character recovery differs from the current graphical connection')
            self.relocated_announced = True
            # Save revalidates the latest two physics samples. Preserve the
            # original gate evidence separately so its observed latency remains
            # reviewable after that later validation replaces ground_evidence.
            ground = proof.get('ground_evidence')
            if isinstance(ground, dict):
                metrics = self.ctx.report.setdefault('character_observer_metrics', {})
                metrics['initial_ground_evidence'] = copy.deepcopy(ground)
                metrics['ground_observed_utc_ms'] = proof.get('ground_observed_utc_ms')
                samples = ground.get('samples')
                if (isinstance(samples, list) and samples
                        and isinstance(samples[-1], dict)
                        and type(samples[-1].get('utc_ms')) is int
                        and type(proof.get('ground_observed_utc_ms')) is int):
                    metrics['last_native_ground_sample_to_event_ms'] = (
                        proof['ground_observed_utc_ms'] - samples[-1]['utc_ms'])
            self.ctx.event('character_relocated', session_id=self.args.session_id,
                client_pid=proof['client_pid'], character_id=proof['character_id'],
                name=creation.CHARACTER_NAME, account=creation.login.server.ACCOUNT, map_id=1,
                recovery_requested=True, recovery_verified=True,
                ordinary_stuck_observed=True, on_atlas_safe_position=True, stable_ground_verified=True)
        return result


def main(argv=None):
    return creation.run(argv, CharacterReopenDiagnostic, SCOPE, 'actual_character_reopen')


if __name__ == '__main__':
    sys.exit(main())
