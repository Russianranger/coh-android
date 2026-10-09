"""Bounded reopen phases; neither network timeout nor character-save proof."""
import math
import re

CONNECTED_SECONDS = 1200
LAUNCHER_BUDGET_SECONDS = 34 * 60
PRESENTATION_BUDGET_SECONDS = 35 * 60
OPERATION_RESERVE_SECONDS = 120
RECOVERY_MAX_AGE_MS = 600000
SAVE_REQUEST_AGE_MS = 420000
NEUTRAL_RESERVE_MS = 60000
SAVE_PROOF_RESERVE_MS = 180000


def require(value, message):
    if not value:
        raise ValueError(message)


def finite_seconds(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def utc_milliseconds(value):
    return type(value) is int and 0 < value < 2**63


class SessionBudget:
    """Connection grants a finite play/save window; optional recovery can shorten it."""
    def __init__(self, session_id, client_pid, launcher_started, operation_deadline,
                 *, presentation_ready=None):
        require(isinstance(session_id, str) and re.fullmatch(r'[0-9a-f]{32}', session_id)
                and type(client_pid) is int and 0 < client_pid <= 4294967295,
                'Invalid reopen budget session or owned client identity')
        require(finite_seconds(launcher_started) and finite_seconds(operation_deadline),
                'Invalid reopen budget launcher or operation deadline')
        require(presentation_ready is None or finite_seconds(presentation_ready)
                and presentation_ready <= launcher_started,
                'Invalid reopen budget presentation clock')
        self.session_id, self.client_pid = session_id, client_pid
        self.launcher_started = launcher_started
        self.hardcap = min(launcher_started + LAUNCHER_BUDGET_SECONDS,
                           operation_deadline - OPERATION_RESERVE_SECONDS)
        if presentation_ready is not None:
            # Match the earlier Android display bound without extending the
            # launcher, operation, neutral-wait or ordinary-save allowances.
            self.hardcap = min(self.hardcap,
                               presentation_ready + PRESENTATION_BUDGET_SECONDS)
        require(finite_seconds(self.hardcap) and self.hardcap > launcher_started,
                'Reopen budget has no reserved launcher/operation lifetime')
        self.revision = 0
        self.deadline = None
        self.receipt = None
        self.events = []
        self.last_now = self.last_utc_ms = None

    def clocks(self, now, now_utc_ms):
        require(finite_seconds(now) and now >= self.launcher_started
                and utc_milliseconds(now_utc_ms), 'Invalid reopen budget clocks')
        require(self.last_now is None or now >= self.last_now,
                'Reopen budget monotonic clock moved backwards')
        self.last_now, self.last_utc_ms = now, now_utc_ms

    def identity(self, proof):
        require(isinstance(proof, dict) and proof.get('session_id') == self.session_id
                and type(proof.get('client_pid')) is int and proof['client_pid'] == self.client_pid
                and type(proof.get('character_id')) is int and proof['character_id'] == 1
                and type(proof.get('before_character_id')) is int and proof['before_character_id'] == 1
                and type(proof.get('baseline_character_id')) is int and proof['baseline_character_id'] == 1
                and type(proof.get('map_id')) is int and proof['map_id'] == 1
                and proof.get('name') == 'THORHERO' and proof.get('account') == 'COHLOCAL'
                and all(proof.get(key) is True for key in ('connected_on_atlas', 'reopen_verified',
                    'existing_character_verified', 'preserved_existing_identity',
                    'native_client_ready_observed')),
                'Reopen budget differs from the validated native character connection')

    def event(self, phase, now, now_utc_ms, deadline, *, save_ms=0, movement_ms=0):
        deadline_ms = now_utc_ms + int(round((deadline - now) * 1000))
        require(utc_milliseconds(deadline_ms) and now_utc_ms < deadline_ms,
                'Reopen phase deadline is exhausted')
        value = {'format': 1, 'session_id': self.session_id, 'client_pid': self.client_pid,
            'character_id': 1, 'name': 'THORHERO', 'account': 'COHLOCAL', 'map_id': 1,
            'revision': self.revision, 'phase': phase, 'generated_utc_ms': now_utc_ms,
            'deadline_utc_ms': deadline_ms, 'save_request_deadline_utc_ms': save_ms,
            'movement_deadline_utc_ms': movement_ms, 'native_client_ready_observed': True,
            'reopen_verified': True}
        if phase == 'grounded':
            value.update(recovery_requested=True, recovery_verified=True,
                         ordinary_stuck_observed=True, stable_ground_verified=True)
        self.events.append(value)
        return dict(value)

    def connected(self, proof, now, now_utc_ms):
        self.clocks(now, now_utc_ms)
        self.identity(proof)
        if self.revision:
            return None
        deadline = min(now + CONNECTED_SECONDS, self.hardcap)
        require(deadline > now, 'Native connection arrived after the reserved session lifetime')
        finish_ms = now_utc_ms + int(round((deadline - now) * 1000))
        save_ms = finish_ms - SAVE_PROOF_RESERVE_MS
        movement_ms = save_ms - NEUTRAL_RESERVE_MS
        require(now_utc_ms < movement_ms < save_ms < finish_ms,
                'Connected budget is exhausted before neutral wait and ordinary save reserves')
        self.revision, self.deadline = 1, deadline
        return self.event('connected', now, now_utc_ms, deadline,
                          save_ms=save_ms, movement_ms=movement_ms)

    def grounded(self, proof, now, now_utc_ms):
        self.clocks(now, now_utc_ms)
        self.identity(proof)
        require(self.revision >= 1 and all(proof.get(key) is True for key in (
                    'recovery_requested', 'recovery_verified', 'ordinary_stuck_observed',
                    'on_atlas_safe_position', 'stable_ground_verified')),
                'Ground budget requires current ordinary recovery and stable native evidence')
        receipt = proof.get('relocation_delivery')
        ready_ms = proof.get('client_ready_observed_utc_ms')
        require(isinstance(receipt, dict) and set(receipt) == {
                    'format', 'session_id', 'client_pid', 'character_id', 'action', 'sent_utc_ms'}
                and type(receipt['format']) is int and receipt['format'] == 1
                and receipt['session_id'] == self.session_id
                and type(receipt['client_pid']) is int and receipt['client_pid'] == self.client_pid
                and type(receipt['character_id']) is int and receipt['character_id'] == 1
                and receipt['action'] == 'stuck' and utc_milliseconds(receipt['sent_utc_ms'])
                and utc_milliseconds(ready_ms) and ready_ms <= receipt['sent_utc_ms']
                and 0 <= now_utc_ms - receipt['sent_utc_ms'] <= RECOVERY_MAX_AGE_MS,
                'Ground budget recovery receipt is foreign, replayed or outside its existing age limit')
        if self.revision == 2:
            require(receipt == self.receipt, 'Ground budget recovery receipt changed after acceptance')
            return None
        require(now < self.deadline, 'Ground budget cannot revive the expired connected deadline')
        hardcap_ms = now_utc_ms + int(round((min(self.hardcap, self.deadline) - now) * 1000))
        finish_ms = min(receipt['sent_utc_ms'] + RECOVERY_MAX_AGE_MS, hardcap_ms)
        save_ms = min(receipt['sent_utc_ms'] + SAVE_REQUEST_AGE_MS,
                      finish_ms - SAVE_PROOF_RESERVE_MS)
        movement_ms = save_ms - NEUTRAL_RESERVE_MS
        require(now_utc_ms < movement_ms < save_ms < finish_ms
                and finish_ms <= receipt['sent_utc_ms'] + RECOVERY_MAX_AGE_MS
                and finish_ms - save_ms >= SAVE_PROOF_RESERVE_MS,
                'Ground budget is exhausted before neutral wait, ordinary save and proof reserves')
        self.revision, self.receipt = 2, dict(receipt)
        self.deadline = now + (finish_ms - now_utc_ms) / 1000
        return self.event('grounded', now, now_utc_ms, self.deadline,
                          save_ms=save_ms, movement_ms=movement_ms)
