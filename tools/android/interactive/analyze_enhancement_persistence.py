#!/usr/bin/env python3
"""Offline Boosts observation comparison; never executes SQL or certifies gameplay.

The shipped .32 character proof intentionally remains unchanged. This tool
prints an optional read-only query and compares separately captured snapshots.
The snapshots, including any self-declared session identity, are unauthenticated.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = 'docs/schema-generation-evidence/accepted-36088012666.zip'
ARCHIVE_SHA256 = '62da453ef5673238e11b4b418692117ea7692597a079119b3aaf72504a2502ae'
SCHEMA_SHA256 = 'a7bb94cd936198850f1a35ac58df925b3638caae29c02f47dca1cb3e21dbc132'
TEMPLATE_SHA256 = '295e82df5c9cd84d0571b5e5e4f44caf7a68e35faadfdb57952bf4fe9308c913'
TEMPLATE = 'data/server/db/templates/ents.template'
SOURCE = 'upstream/ouroboros/MapServer/src/container/containerloadsave.c'
PLACEMENT_SOURCE = 'upstream/ouroboros/MapServer/src/entity/character_db.c'
BOOST_FIELDS = ('containerid', 'subid', 'powerid', 'idx', 'categoryname',
    'powersetname', 'boostname', 'level', 'numcombines', 'var0', 'var1', 'var2', 'var3',
    'slottedpowerupsmask', *(field for index in range(10)
        for field in (f'powerupslottype{index}', f'powerupslotid{index}')))
POWER_FIELDS = ('containerid', 'subid', 'powerid', 'uniqueid', 'buildnum',
    'categoryname', 'powersetname', 'powername')
IDENTITY_FIELDS = ('containerid', 'authid', 'authname', 'name')
FLOAT_FIELDS = ('var0', 'var1', 'var2', 'var3')
ATTR_FIELDS = ('categoryname', 'powersetname', 'boostname')
MAX_BYTES = 8 * 1024 * 1024


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def generated_contract(root=ROOT):
    """Verify existing accepted schema bytes, rather than guess Boosts columns."""
    root = Path(root)
    raw = (root / ARCHIVE).read_bytes()
    require(digest(raw) == ARCHIVE_SHA256, 'Accepted schema artifact changed')
    with zipfile.ZipFile(io.BytesIO(raw)) as outer:
        schema = outer.read('schema-evidence/schema-outputs.zip')
    require(digest(schema) == SCHEMA_SHA256, 'Accepted generated schema archive changed')
    with zipfile.ZipFile(io.BytesIO(schema)) as archive:
        template = archive.read(TEMPLATE)
    require(digest(template) == TEMPLATE_SHA256, 'Accepted character template changed')
    text = template.decode('utf-8')
    boosts = re.findall(r'^Boosts\[6010\]\.([A-Za-z0-9_]+) ', text, re.M)
    require(tuple(name.lower() for name in boosts) == BOOST_FIELDS[2:],
            'Generated Boosts table differs from reviewed complete field selection')
    powers = {name.lower() for name in re.findall(r'^Powers\[1000\]\.([A-Za-z0-9_]+) ', text, re.M)}
    require(set(POWER_FIELDS[2:]) <= powers, 'Generated Powers relation fields missing')
    source = (root / SOURCE).read_text()
    section = source[source.index('LineDesc boost_line_desc[]'):source.index('StructDesc boost_desc[]')]
    native_fields = re.findall(r'PACKTYPE_[A-Z]+,\s+[A-Z0-9_]+,\s+"([A-Za-z0-9_]+)"', section)
    require(tuple(name.lower() for name in native_fields) == BOOST_FIELDS[2:],
            'Native Boosts persistence fields differ from generated schema')
    placement = (root / PLACEMENT_SOURCE).read_text()
    inventory = placement[placement.index('static int convertInventoryBoosts('):placement.index('static int convertInspirations(')]
    require('pboost[iCntBoosts].iID = -1;' in inventory
            and 'pboost[iCntBoosts].iIdx = i;' in inventory
            and 's_dbpows.powers[iCntPowers].iID = iCntPowers+1;' in placement,
            'Native inventory or serialized power placement semantics changed')
    return {'format': 1, 'scope': 'offline_read_only_enhancement_observation',
        'generated_template_sha256': TEMPLATE_SHA256,
        'schema_archive_sha256': SCHEMA_SHA256,
        'native_boost_fields_source_sha256': digest((root / SOURCE).read_bytes()),
        'native_placement_source_sha256': digest((root / PLACEMENT_SOURCE).read_bytes()),
        'boost_fields': list(BOOST_FIELDS), 'power_fields': list(POWER_FIELDS),
        'row_keys': ['containerid', 'subid'], 'max_boost_rows': 6010,
        'inventory_location': 'powerid=-1, idx=inventory_slot; idx=-1 is invalid',
        'slotted_location': 'powerid references powers.powerid; idx=power_slot',
        'query_executed': False, 'device_validation': False}


def query(character_id=1, root=ROOT):
    """Return one coherent, read-only PG observation with relation/name closure."""
    generated_contract(root)
    require(type(character_id) is int and 0 < character_id < 2**31,
            'Character ID must be a positive int32')
    selects = []
    for table, fields in (('powers', POWER_FIELDS), ('boosts', BOOST_FIELDS)):
        selects.append(f"'{table}', (SELECT coalesce(json_agg(r ORDER BY subid), '[]'::json) "
            f"FROM (SELECT {','.join(fields)} FROM dbo.{table} WHERE containerid={character_id}) r)")
    attr_ids = ' UNION '.join(f'SELECT {field} AS id FROM dbo.{table} WHERE containerid={character_id}'
        for table, fields in (('powers', ('categoryname', 'powersetname', 'powername')),
                              ('boosts', ATTR_FIELDS)) for field in fields)
    return ('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;\n'
        "SELECT json_build_object('format',1,'identity', "
        f"(SELECT row_to_json(i) FROM (SELECT {','.join(IDENTITY_FIELDS)} FROM dbo.ents "
        f"WHERE containerid={character_id}) i), 'login_count', "
        f"(SELECT logincount FROM dbo.ents WHERE containerid={character_id}), 'rows', "
        f"json_build_object({','.join(selects)}), 'attribute_rows', "
        "(SELECT coalesce(json_agg(a ORDER BY id), '[]'::json) FROM "
        f"(SELECT id,name FROM dbo.attributes WHERE id IN ({attr_ids})) a));\nCOMMIT;\n")


def _integer(value, message, *, minimum=0):
    require(type(value) is int and minimum <= value < 2**31, message)
    return value


def _snapshot(value):
    require(type(value) is dict, 'Snapshot must be a JSON object')
    require(type(value.get('format')) is int and value['format'] == 1,
            'Unsupported enhancement observation format')
    identity = value.get('identity')
    require(type(identity) is dict and set(identity) == set(IDENTITY_FIELDS), 'Character identity fields missing')
    identifier = _integer(identity['containerid'], 'Invalid character ID', minimum=1)
    _integer(identity['authid'], 'Invalid auth ID', minimum=1)
    require(identity['authname'] == 'COHLOCAL' and identity['name'] == 'THORHERO',
            'Snapshot is outside the existing local THORHERO scope')
    login_count = _integer(value.get('login_count'), 'Committed LoginCount missing', minimum=1)
    attrs = value.get('attribute_rows')
    require(type(attrs) is list and len(attrs) <= 22000, 'Attribute mapping missing or oversized')
    attributes = {}
    names = set()
    for row in attrs:
        require(type(row) is dict and set(row) == {'id', 'name'}, 'Malformed attribute mapping')
        attr_id = _integer(row['id'], 'Invalid attribute ID', minimum=1)
        name = row['name']
        require(type(name) is str and 0 < len(name) <= 1024 and name not in names
                and attr_id not in attributes, 'Duplicate or invalid attribute mapping')
        attributes[attr_id] = name
        names.add(name)

    def attr(number):
        _integer(number, 'Enhancement/power attribute is not a positive ID', minimum=1)
        require(number in attributes, 'Attribute ID lacks exact name mapping')
        return attributes[number]

    rows = value.get('rows')
    require(type(rows) is dict, 'SQL rows missing')
    powers, boosts = rows.get('powers'), rows.get('boosts')
    require(type(powers) is list and len(powers) <= 1000, 'Powers relation missing or oversized')
    require(type(boosts) is list and len(boosts) <= 6010, 'Boosts rows missing or oversized')
    power_ids, power_keys, power_subids = {}, set(), set()
    for power in powers:
        require(type(power) is dict and set(POWER_FIELDS) <= set(power)
                and power['containerid'] == identifier and type(power['containerid']) is int,
                'Invalid or foreign power row')
        subid = _integer(power['subid'], 'Invalid power subid')
        power_id = _integer(power['powerid'], 'Invalid serialized PowerID', minimum=1)
        unique_id = _integer(power['uniqueid'], 'Missing stable power UniqueID', minimum=1)
        build = power['buildnum']
        if build is None:
            build = 0  # The retained serializer emits the default build as SQL NULL.
        _integer(build, 'Invalid power build')
        key = (unique_id, build, *(attr(power[name]) for name in ('categoryname', 'powersetname', 'powername')))
        require(subid not in power_subids and power_id not in power_ids and key not in power_keys,
                'Duplicate power key or relation')
        power_ids[power_id], power_keys = key, power_keys | {key}
        power_subids.add(subid)
    result, subids, locations = [], set(), set()
    for boost in boosts:
        require(type(boost) is dict and set(boost) == set(BOOST_FIELDS)
                and type(boost['containerid']) is int and boost['containerid'] == identifier,
                'Incomplete or foreign Boosts row')
        subid = _integer(boost['subid'], 'Invalid Boosts subid')
        require(subid not in subids, 'Duplicate Boosts subid')
        subids.add(subid)
        power_id = _integer(boost['powerid'], 'Invalid boost PowerID', minimum=-1)
        require(power_id != 0, 'Boosts PowerID zero has no inventory/power meaning')
        index = boost['idx']
        if index is None:
            index = 0  # Missing integer members reload into the zeroed DBBoost.
        _integer(index, 'Invalid enhancement slot index')
        if power_id == -1:
            require(index < 70, 'Inventory enhancement index exceeds CHAR_BOOST_MAX')
            location = ('inventory', index)
        else:
            require(power_id in power_ids and index < 6, 'Slotted boost lacks its exact power/slot relation')
            location = ('power', power_ids[power_id], index)
        require(location not in locations, 'Duplicate enhancement placement')
        locations.add(location)
        payload = {name: boost[name] for name in BOOST_FIELDS[4:]}
        for name in ATTR_FIELDS:
            payload[name] = attr(payload[name])
        for name in set(payload) - set(ATTR_FIELDS):
            scalar = payload[name]
            if name in FLOAT_FIELDS:
                require(scalar is None or type(scalar) in (int, float) and math.isfinite(scalar),
                        'Invalid enhancement floating value')
            else:
                require(scalar is None or type(scalar) is int and 0 <= scalar < 2**31,
                        'Invalid enhancement integer value')
        result.append({'location': location, 'payload': payload})
    return identity, login_count, sorted(result, key=canonical)


def compare(before, after):
    result = {'format': 1, 'scope': 'offline_unauthenticated_snapshot_observation',
        'session_attribution_verified': False, 'committed_sql_verified': False,
        'enhancement_persistence_verified': False, 'physical_device_verified': False,
        'observed_snapshot_schema_verified': False,
        'query_executed': False, 'ordinary_save_gates_changed': False}
    missing = [side for side, value in (('before', before), ('after', after))
        if type(value) is not dict or type(value.get('rows')) is not dict
        or 'boosts' not in value['rows'] or 'attribute_rows' not in value]
    if missing:
        return dict(result, status='missing_evidence', semantic_rows_equal=None,
                    missing_snapshot_sides=missing,
                    reason='Boosts rows and matching attribute names are absent; existing .32 save proofs cannot establish enhancement equality')
    first_id, first_count, first = _snapshot(before)
    second_id, second_count, second = _snapshot(after)
    require(first_id == second_id, 'Character identity differs between snapshots')
    require(second_count == first_count + 1, 'Snapshot pair is not a consecutive save/reopen observation')
    equal = canonical(first) == canonical(second)
    return dict(result, status='observed_equal' if equal else 'observed_changed',
        semantic_rows_equal=equal, before_boost_count=len(first), after_boost_count=len(second),
        nonempty_enhancements_observed=bool(first and second),
        before_semantic_sha256=digest(canonical(first).encode()),
        after_semantic_sha256=digest(canonical(second).encode()),
        before_login_count=first_count, after_login_count=second_count,
        serialized_subid_and_powerid_reordering_ignored=True,
        payload_values_compared='all generated Boosts fields; typed NULL/value differences retained',
        required_additional_gates=['authenticated current Android session and native ordinary logout',
            'committed read after logout with matching identity/schema',
            'physical reopen showing the same inventory and slotted enhancements'])


def read_json(path):
    path = Path(path)
    require(path.stat().st_size <= MAX_BYTES, 'Snapshot exceeds 8 MiB offline bound')
    raw = path.read_bytes()
    require(len(raw) <= MAX_BYTES, 'Snapshot exceeds 8 MiB offline bound')
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON field refused')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(EvidenceError('Nonfinite JSON scalar refused')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--query', action='store_true', help='Print optional PG read-only query; execute nothing')
    parser.add_argument('--character-id', type=int, default=1)
    parser.add_argument('--before', type=Path)
    parser.add_argument('--after', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    require((args.query and args.before is None and args.after is None)
            or (not args.query and args.before is not None and args.after is not None),
            'Choose --query or both --before/--after')
    if args.query:
        payload = query(args.character_id)
    else:
        result = compare(read_json(args.before), read_json(args.after))
        result['schema_contract'] = generated_contract()
        payload = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        require(not args.output.exists(), 'Refusing to overwrite an existing observation')
        args.output.write_text(payload)
    else:
        sys.stdout.write(payload)


if __name__ == '__main__':
    try:
        main()
    except (EvidenceError, OSError, json.JSONDecodeError, zipfile.BadZipFile) as failure:
        print(f'Enhancement observation refused: {failure}', file=sys.stderr)
        raise SystemExit(2)
