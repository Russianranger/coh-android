#!/usr/bin/env python3
"""Read-only proof of THORHERO's first native trained level/power purchase.

The stock successful BuyPower record precedes svrSendEntListToDb; it alone
never proves a commit. Only the existing ordinary logout pipeline and selected
SQL rows establish persistence. No native input or database mutation is added.
"""
import hashlib
from pathlib import Path
import re
import time

import stationary_contact_evidence as contact

server = contact.server
NATIVE_CONTRACT_FILES = (
    'MapServer/src/entity/character_net_server.c',
    'MapServer/src/entity/character_db.c', 'Common/entity/character_base.c',
    'Common/entity/character_level.c', 'Common/entity/powers_load.c',
    'Common/entity/powers.c', 'MapServer/src/dbghelper.c',
)
DATA_CONTRACT_FILES = (
    'data/defs/powers/inherent.powersets',
    'data/defs/powers/inherent_inherent.powers',
    'data/defs/powers/inherent_fitness.powers',
    'data/defs/powers/blaster_ranged.powersets',
    'data/defs/powers/blaster_support.powersets', 'data/defs/experience.def',
)
SCOPE = 'owned_atlas_first_trained_level_exact_native_purchase_and_committed_sql'
# The stock first training grants the newly available automatic powers in the
# existing Inherent/Fitness sets. Already owned automatic powers remain exact.
# Walk, Rest, Fitness_Fix and all Fitness powers become available at internal 1.
AUTO_POWERS = {
    'Inherent.Inherent.Brawl': 0, 'Inherent.Inherent.Sprint': 0,
    'Inherent.Inherent.Vision_Phase': 0, 'Inherent.Inherent.Defiance': 0,
    'Inherent.Inherent.Walk': 1, 'Inherent.Inherent.Rest': 1,
    'Inherent.Inherent.Fitness_Fix': 1,
    'Inherent.Fitness.Swift': 1, 'Inherent.Fitness.Hurdle': 1,
    'Inherent.Fitness.Health': 1, 'Inherent.Fitness.Stamina': 1,
}
PURCHASABLE = frozenset({
    'Blaster_Ranged.Archery.Snap_Shot', 'Blaster_Ranged.Archery.Aimed_Shot',
    'Blaster_Ranged.Archery.Fistful_of_Arrows',
    'Blaster_Support.Gadgets.Web_Grenade', 'Blaster_Support.Gadgets.Caltrops',
})
CANONICAL_POWERS = {name.casefold(): name for name in (*AUTO_POWERS, *PURCHASABLE)}
ROW_LIMIT = 128
PURCHASE = re.compile(contact.PREFIX + r'BuyPower Click (?P<power>[A-Za-z0-9_]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+)'
                      + contact.SUFFIX + '$')
ROUTE = re.compile(r'^(?P<timestamp>\d{6} \d{2}:\d{2}:\d{2}) '
    r'(?:(?P<local_level>1)|(?P<map_instance>(?i:City_01_01)_1):127\.0\.0\.1:127\.0\.0\.1) +'
    r'(?P<message>[^\r\n]+)$')


def _zero(value):
    return 0 if value is None else value if type(value) is int and 0 <= value <= 0x7fffffff else -1


def _purchase(logs, start_ms, end_ms):
    if not (type(logs) in (list, tuple) and len(logs) <= server.SERVER_LOG_COUNT_LIMIT):
        return None
    total, found = 0, []
    for item in logs:
        if not (type(item) in (list, tuple) and len(item) == 2
                and type(item[0]) is str and type(item[1]) is str):
            return None
        name, text = item
        size = len(text.encode(errors='surrogateescape')); total += size
        if size > server.SERVER_LOG_FILE_LIMIT or total > server.SERVER_LOG_TOTAL_LIMIT:
            return None
        path = Path(name)
        local = path.parent == Path('logs/mapserver') and path.name == 'entity.log'
        embedded = path.parent == Path('logs/dbserver') and re.fullmatch(r'entity_[0-9][0-9_-]*\.log', path.name)
        if not local and not embedded:
            continue
        tail = text[text.rfind('\n') + 1:]
        if re.search(r'"THORHERO:COHLOCAL" -?\d+ BuyPower(?: |$)', tail):
            return None
        for line in text[:text.rfind('\n') + 1].splitlines():
            routed = ROUTE.fullmatch(line)
            if routed is None or (routed['local_level'] is not None) != bool(local):
                continue
            message = routed['message']
            if not re.match(contact.PREFIX + r'BuyPower(?: |$)', message):
                continue
            try:
                stamp = int(time.mktime(time.strptime(routed['timestamp'], '%y%m%d %H:%M:%S')) * 1000)
            except (ValueError, OverflowError):
                return None
            if not start_ms <= stamp <= end_ms:
                continue
            parsed = PURCHASE.fullmatch(message)
            if (parsed is None or len(message) > 2048 or parsed['level'] != '2'
                    or parsed['alignment'] != '0' or parsed['archetype'] != 'Class_Blaster'
                    or parsed['incarnate'] != '0' or not -0x80000000 <= int(parsed['teamup']) <= 0x7fffffff):
                return None
            found.append({'power': parsed['power'], 'utc_ms': stamp,
                'log_timestamp': routed['timestamp'], 'path': name,
                'line_sha256': hashlib.sha256(line.encode(errors='surrogateescape')).hexdigest(),
                'log_route': 'local_mapserver' if local else 'embedded_dbserver_logserver',
                'map_instance': routed['map_instance']})
            if len(found) > 1:
                return None  # Ambiguous or mirrored positive purchases fail closed.
    return found[0] if len(found) == 1 else None


def verify(logs, proof, delivery, logout, previous, current, attributes, *, session, client_pid, now_utc_ms):
    """Return a narrow exception for internal level 0→1 with one real purchase."""
    identity = contact.binding(proof, session, client_pid, now_utc_ms)
    if (identity is None or type(delivery) is not dict or delivery.get('session_id') != session
            or type(delivery.get('client_pid')) is not int or delivery['client_pid'] != client_pid
            or type(delivery.get('character_id')) is not int or delivery['character_id'] != 1
            or delivery.get('action') != 'quittologin' or type(delivery.get('sent_utc_ms')) is not int
            or not identity['client_ready_observed_utc_ms'] <= delivery['sent_utc_ms'] <= now_utc_ms
            or logout is None or not server.logout_follows_delivery(logout, delivery)):
        return None
    try:
        end_ms = int(time.mktime(time.strptime(logout['log_timestamp'], '%y%m%d %H:%M:%S')) * 1000)
    except (KeyError, ValueError, OverflowError):
        return None
    if not identity['client_ready_observed_utc_ms'] <= end_ms <= now_utc_ms:
        return None
    if (type(previous) is not dict or type(current) is not dict
            or set(previous) != set(server.evidence.SELECTED) or set(current) != set(previous)
            or len(previous['ents']) != 1 or len(current['ents']) != 1
            or _zero(previous['ents'][0].get('level')) != 0
            or type(current['ents'][0].get('level')) is not int or current['ents'][0]['level'] != 1
            or previous['ents'][0].get('containerid') != 1
            or previous['ents'][0].get('authid') != identity['auth_id']):
        return None
    purchase = _purchase(logs, identity['client_ready_observed_utc_ms'], end_ms)
    if purchase is None or purchase['power'] not in PURCHASABLE:
        return None
    # 106 is original ExperienceRequired[1], not an injected game balance.
    if _zero(current['ents'][0].get('experiencepoints')) < 106:
        return None
    if not (type(attributes) is list and all(type(row) is dict and type(row.get('id')) is int
            and type(row.get('name')) is str for row in attributes)):
        return None
    # vars.attribute is shipped lower-case; the stock power dictionary/native
    # BuyPower logger retains its authored capitalization. Native lookup uses
    # stricmp, so compare attribute names with the same ASCII case semantics.
    names = {row['id']: row['name'].casefold() if row['name'].isascii() else row['name']
             for row in attributes}
    if len(names) != len(attributes):
        return None
    if (names.get(previous['ents'][0].get('class')) != 'class_blaster'
            or previous['ents2'][0].get('originalprimary') != 'Archery'
            or previous['ents2'][0].get('originalsecondary') != 'Gadgets'):
        return None
    prior, after = {}, {}
    for rows, index in ((previous['powers'], prior), (current['powers'], after)):
        if not (type(rows) is list and 0 < len(rows) <= ROW_LIMIT):
            return None
        for row in rows:
            uid = row.get('uniqueid')
            if (type(uid) is not int or not 0 < uid <= 0x7fffffff or uid in index
                    or row.get('containerid') != 1):
                return None
            index[uid] = row
    semantic_fields = set(server.evidence.SELECTED['powers']) - {'subid', 'powerid'}
    for uid, row in prior.items():
        if uid not in after or not server.evidence._same(
                {key: row[key] for key in semantic_fields},
                {key: after[uid][key] for key in semantic_fields}):
            return None
    # packageEntPowers assigns contiguous SQL rows and PowerID=index+1. Their
    # renumbering is allowed only while every prior semantic power stays exact.
    if any(type(row.get('subid')) is not int or row['subid'] != position
            or type(row.get('powerid')) is not int or row['powerid'] != position + 1
            for position, row in enumerate(current['powers'])):
        return None
    added, purchased, automatic, power_names = [], [], [], set()
    owned_pairs = {(row['categoryname'], row['powersetname']) for row in prior.values()}
    for uid, row in after.items():
        parts = [names.get(row[key]) for key in ('categoryname', 'powersetname', 'powername')]
        if any(type(part) is not str for part in parts):
            return None
        full = '.'.join(parts)
        if full in power_names:
            return None
        power_names.add(full)
        if uid in prior:
            continue
        if (_zero(row.get('buildnum')) != 0 or _zero(row.get('powernumboostsbought')) != 0
                or _zero(row.get('powersetlevelbought')) != 0):
            return None
        canonical = CANONICAL_POWERS.get(full)
        record = {'uniqueid': uid, 'power': canonical, 'subid': row['subid'], 'powerid': row['powerid']}
        added.append(record)
        if (full == purchase['power'].casefold() and _zero(row.get('powerlevelbought')) == 1
                and (row['categoryname'], row['powersetname']) in owned_pairs):
            purchased.append(record)
        elif canonical in AUTO_POWERS and _zero(row.get('powerlevelbought')) == AUTO_POWERS[canonical]:
            automatic.append(record)
        else:
            return None
    if len(purchased) != 1 or not 1 <= len(added) <= len(AUTO_POWERS) + 1:
        return None
    return {'format': 1, 'verified': True, 'scope': SCOPE, 'connection': identity,
        'before_internal_level': 0, 'saved_internal_level': 1, 'saved_displayed_level': 2,
        'native_purchase': purchase, 'purchased_power': purchased[0],
        'automatic_power_additions': automatic, 'prior_powers_preserved_by_uniqueid': True,
        'prior_power_count': len(prior), 'saved_power_count': len(after),
        'before_power_rows_sha256': server.digest_json(previous['powers']),
        'saved_power_rows_sha256': server.digest_json(current['powers']),
        'structural_power_row_policy': 'stock_contiguous_SubId_and_PowerID_only_in_witnessed_training',
        'logout_timer_evidence': logout, 'logout_delivery': delivery,
        'sql_game_mutations_performed': False, 'trainer_identity_verified': False,
        'trainer_dialogue_visual_verified': False}


def verify_reopen_normalization(logs, proof, delivery, logout, previous, current,
                                attributes, *, session, client_pid, now_utc_ms):
    """Prove the finite stock level-2 auto-set load/save normalization.

    character_db.c unpack resets autoissue set levels to piAvailable, then
    stores the last loaded power's level on its shared PowerSet. Packaging
    serializes that parent level for every row in the set. The first trained
    save still has zero set levels; the following native load sets Inherent
    and Fitness to one. No UID, row order, power or purchase field may change.
    """
    if not (type(logs) in (list, tuple) and len(logs) <= server.SERVER_LOG_COUNT_LIMIT):
        return None
    total = 0
    for item in logs:
        if not (type(item) in (list, tuple) and len(item) == 2
                and type(item[0]) is str and type(item[1]) is str):
            return None
        size = len(item[1].encode(errors='surrogateescape')); total += size
        if size > server.SERVER_LOG_FILE_LIMIT or total > server.SERVER_LOG_TOTAL_LIMIT:
            return None
    if server.logout_record(logs) != logout:
        return None
    identity = contact.binding(proof, session, client_pid, now_utc_ms)
    if (identity is None or type(delivery) is not dict or delivery.get('session_id') != session
            or type(delivery.get('client_pid')) is not int or delivery['client_pid'] != client_pid
            or type(delivery.get('character_id')) is not int or delivery['character_id'] != 1
            or delivery.get('action') != 'quittologin' or type(delivery.get('sent_utc_ms')) is not int
            or not identity['client_ready_observed_utc_ms'] <= delivery['sent_utc_ms'] <= now_utc_ms
            or logout is None or not server.logout_follows_delivery(logout, delivery)):
        return None
    try:
        end_ms = int(time.mktime(time.strptime(logout['log_timestamp'], '%y%m%d %H:%M:%S')) * 1000)
    except (KeyError, ValueError, OverflowError):
        return None
    if not identity['client_ready_observed_utc_ms'] <= end_ms <= now_utc_ms:
        return None
    if (type(previous) is not dict or type(current) is not dict
            or set(previous) != set(server.evidence.SELECTED) or set(current) != set(previous)
            or len(previous['ents']) != 1 or len(current['ents']) != 1
            or type(previous['ents'][0].get('level')) is not int or previous['ents'][0]['level'] != 1
            or type(current['ents'][0].get('level')) is not int or current['ents'][0]['level'] != 1
            or previous['ents'][0].get('containerid') != 1
            or previous['ents'][0].get('authid') != identity['auth_id']
            or len(previous['ents2']) != 1 or len(current['ents2']) != 1
            or not (type(attributes) is list and all(type(row) is dict and type(row.get('id')) is int
                and type(row.get('name')) is str for row in attributes))):
        return None
    names = {row['id']: row['name'].casefold() if row['name'].isascii() else row['name']
             for row in attributes}
    if (len(names) != len(attributes) or names.get(previous['ents'][0].get('class')) != 'class_blaster'
            or previous['ents2'][0].get('originalprimary') != 'Archery'
            or previous['ents2'][0].get('originalsecondary') != 'Gadgets'):
        return None
    before, after = previous['powers'], current['powers']
    if not (type(before) is list and type(after) is list and 0 < len(before) == len(after) <= ROW_LIMIT):
        return None
    seen, identifiers, changed = set(), set(), []
    fields = set(server.evidence.SELECTED['powers'])
    for old, new in zip(before, after):
        if not (type(old) is dict and type(new) is dict and set(old) == fields and set(new) == fields):
            return None
        if (type(old['uniqueid']) is not int or not 0 < old['uniqueid'] <= 0x7fffffff
                or old['uniqueid'] in identifiers or type(old['containerid']) is not int
                or old['containerid'] != 1):
            return None
        identifiers.add(old['uniqueid'])
        parts = [names.get(old[key]) for key in ('categoryname', 'powersetname', 'powername')]
        if any(type(part) is not str for part in parts):
            return None
        full = '.'.join(parts)
        canonical = CANONICAL_POWERS.get(full)
        if full.startswith(('inherent.inherent.', 'inherent.fitness.')):
            if (canonical not in AUTO_POWERS or canonical in seen
                    or _zero(old.get('powerlevelbought')) != AUTO_POWERS[canonical]
                    or _zero(old.get('powersetlevelbought')) not in (0, 1)
                    or type(new.get('powersetlevelbought')) is not int or new['powersetlevelbought'] != 1
                    or not server.evidence._same(
                        {key: old[key] for key in fields - {'powersetlevelbought'}},
                        {key: new[key] for key in fields - {'powersetlevelbought'}})):
                return None
            seen.add(canonical)
            if not server.evidence._same(old, new):
                changed.append({'uniqueid': old['uniqueid'], 'power': canonical,
                    'before_set_level': old['powersetlevelbought'], 'saved_set_level': 1})
        elif not server.evidence._same(old, new):
            return None
    if seen != set(AUTO_POWERS) or not changed:
        return None
    return {'format': 1, 'verified': True,
        'scope': 'owned_atlas_level2_exact_autoissue_shared_set_load_normalization',
        'connection': identity, 'saved_internal_level': 1, 'changed_auto_set_rows': changed,
        'prior_powers_preserved_by_uniqueid': True, 'all_other_power_fields_preserved': True,
        'before_power_rows_sha256': server.digest_json(before),
        'saved_power_rows_sha256': server.digest_json(after),
        'native_source': 'unpackEntPowers_autoissue_piAvailable_then_packageEntPowers_parent_set_level',
        'logout_timer_evidence': logout, 'logout_delivery': delivery,
        'sql_game_mutations_performed': False, 'new_purchase_verified': False}
