"""Independent committed SQL evidence for the disposable TestClient character.

The selected fields are fixed before execution and checked against the accepted
template table map from run_one_map.preflight. Timestamps, play time, position,
health and power timers are deliberately absent; LoginCount is reported and
checked separately. Call capture only after the protocol logout/disconnect has
settled. These SQL reads cannot establish that a client entered or left a map.
"""
import re

from run_generated_schema import query_json, require, sql_name


INFLUENCE = 12345
IDENTITY_FIELDS = ('containerid', 'authid', 'authname', 'name')
SELECTED = {
    'ents': IDENTITY_FIELDS + ('class', 'origin', 'level', 'experiencepoints',
        'influencepoints', 'description', 'motto', 'datecreated'),
    'ents2': ('containerid', 'subid', 'curbuild', 'originalprimary',
        'originalsecondary', 'praetorianprogress', 'playersubtype', 'influencetype'),
    'powers': ('containerid', 'subid', 'powerid', 'categoryname', 'powersetname',
        'powername', 'powerlevelbought', 'powernumboostsbought',
        'powersetlevelbought', 'buildnum', 'uniqueid'),
    'costumeparts': ('containerid', 'subid', 'name', 'geom', 'tex1', 'tex2',
        'displayname', 'region', 'bodyset', 'color1', 'color2', 'costumenum',
        'fxname', 'color3', 'color4'),
}
ROW_KEYS = {'ents': ('containerid',), **{name: ('containerid', 'subid')
    for name in ('ents2', 'powers', 'costumeparts')}}
ATTRIBUTE_FIELDS = {
    'ents': ('class', 'origin'),
    'powers': ('categoryname', 'powersetname', 'powername'),
    'costumeparts': ('name', 'geom', 'tex1', 'tex2', 'displayname', 'region',
        'bodyset', 'fxname'),
}
ACCOUNT = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,31}\Z', re.ASCII)


def selected_contract(tables):
    """Reject schema drift before creating a client; never drop missing fields."""
    for table, columns in SELECTED.items():
        required = columns + (('logincount',) if table == 'ents' else ())
        require(table in tables and all(column in tables[table] for column in required),
                'Accepted character schema lacks required table/columns: ' + table)
        require(tuple(tables[table][:2]) ==
                ('containerid', 'active' if table == 'ents' else 'subid'),
                'Accepted character schema has unexpected row keys: ' + table)
    return {'fields': {table: list(fields) for table, fields in SELECTED.items()},
            'row_keys': {table: list(keys) for table, keys in ROW_KEYS.items()},
            'separate_progression_field': 'ents.logincount',
            'expected_influence': INFLUENCE}


def _account(value):
    require(isinstance(value, str) and bool(ACCOUNT.fullmatch(value)),
            'Diagnostic account must be short ASCII letters/digits/underscore')
    return value


def _identifier(value):
    require(type(value) is int and value > 0, 'Character ID must be a positive integer')
    return value


def _rows(cluster, table, fields, keys, where='TRUE'):
    # Every identifier comes from a reviewed constant or accepted schema map.
    columns = ','.join(sql_name(column) for column in fields)
    order = ','.join(sql_name(column) for column in keys)
    result = query_json(cluster, f"SELECT coalesce(json_agg(x ORDER BY {order}),'[]'::json) "
                        f"FROM (SELECT {columns} FROM dbo.{sql_name(table)} WHERE {where}) x;")
    require(isinstance(result, list) and all(isinstance(row, dict) and
            set(row) == set(fields) for row in result), 'Malformed independent SQL rows: ' + table)
    return result


def account_rows(cluster, account, tables, auth_id=None):
    """Find all characters for the account; fake-auth names are case insensitive.

    Once AuthId is known, include it as a second identity check so an extra row
    cannot be hidden by a changed/case-varied AuthName or a hash collision.
    """
    selected_contract(tables)
    account = _account(account)
    where = f"lower(authname)='{account.lower()}'"
    if auth_id is not None:
        _identifier(auth_id)
        where += f' OR authid={auth_id}'
    return _rows(cluster, 'ents', IDENTITY_FIELDS + ('logincount',),
                 ROW_KEYS['ents'], where)


def capture(cluster, tables, account, identifier, name, expected_influence=INFLUENCE):
    """Read one existing character and its required child rows without mutation."""
    selected_contract(tables)
    _account(account)
    _identifier(identifier)
    require(isinstance(name, str) and bool(name.strip()) and len(name) <= 128 and
            not any(ord(c) < 32 for c in name), 'Invalid recorded character name')
    require(type(expected_influence) is int and expected_influence == INFLUENCE,
            'Character persistence experiment requires influence 12345')
    rows = {}
    for table, fields in SELECTED.items():
        columns = fields + (('logincount',) if table == 'ents' else ())
        values = _rows(cluster, table, columns, ROW_KEYS[table],
                       f'containerid={identifier}')
        require(bool(values), 'Required character rows are missing: ' + table)
        require(all(type(row['containerid']) is int and row['containerid'] == identifier
                    for row in values), 'Child/parent row references a different character: ' + table)
        if table in ('ents', 'ents2'):
            require(len(values) == 1, 'Expected exactly one character row: ' + table)
        if table != 'ents':
            keys = [row['subid'] for row in values]
            require(all(type(key) is int and key >= 0 for key in keys) and
                    keys == sorted(set(keys)), 'Invalid, duplicate or unordered child schema keys: ' + table)
            if table == 'ents2':
                require(keys == [0], 'Ents2[1] child must use subid zero')
        rows[table] = values
    parent = rows['ents'][0]
    require(type(parent['authid']) is int and parent['authid'] > 0 and
            isinstance(parent['authname'], str) and parent['authname'].lower() == account.lower() and
            parent['name'] == name, 'SQL character/account identity differs from recorded client')
    require(type(parent['influencepoints']) is int and parent['influencepoints'] == expected_influence,
            'Independent SQL influence differs from requested game command')
    login_count = parent.pop('logincount')
    require(type(login_count) is int and login_count > 0,
            'Saved character LoginCount must show at least one map login')
    identity = {key: parent[key] for key in IDENTITY_FIELDS}
    accounts = account_rows(cluster, account, tables, auth_id=parent['authid'])
    require(accounts == [dict(identity, logincount=login_count)],
            'Account has missing, changed or extra character rows')
    return {'identity': identity, 'login_count': login_count, 'rows': rows}


def compare(before, after, phase):
    """Stable field equality plus the separately reviewed LoginCount transition."""
    require(phase in ('restart', 'resume'), 'Unknown character comparison phase')
    require(before['identity'] == after['identity'], 'Character identity changed after ' + phase)
    for table in SELECTED:
        require(before['rows'][table] == after['rows'][table],
                'Selected character rows changed after ' + phase + ': ' + table)
    first, second = before['login_count'], after['login_count']
    require(type(first) is int and type(second) is int and first > 0 and
            second == first + (1 if phase == 'resume' else 0),
            'Unexpected LoginCount progression after ' + phase)
    return {'phase': phase, 'identity_unchanged': True, 'selected_rows_unchanged': True,
            'login_count_before': first, 'login_count_after': second,
            'row_counts': {table: len(after['rows'][table]) for table in SELECTED}}


def attribute_snapshot(cluster, tables, expected=None):
    """Read every source-derived attribute table, optionally require accepted IDs."""
    names = sorted(table for table, columns in tables.items() if list(columns) == ['id', 'name'])
    require('attributes' in names, 'Accepted schema lacks character attribute mapping')
    values = {table: _rows(cluster, table, ('id', 'name'), ('id',)) for table in names}
    for table, rows in values.items():
        ids = [row['id'] for row in rows]
        require(all(type(value) is int and value > 0 for value in ids) and
                ids == sorted(set(ids)) and all(isinstance(row['name'], str) for row in rows),
                'Malformed attribute IDs/names: ' + table)
    if expected is not None:
        require(values == expected, 'Attribute IDs/names differ from accepted generated mappings')
    return values


def compare_attributes(before, after):
    require(before == after, 'Attribute mappings changed during character persistence experiment')
    return {'unchanged': True, 'row_counts': {table: len(rows) for table, rows in after.items()}}


def validate_attribute_references(snapshot, attributes):
    """Selected serialized attribute IDs must belong to the unchanged mapping."""
    require('attributes' in attributes, 'Missing character attribute mapping')
    known = {row['id'] for row in attributes['attributes']}
    for table, columns in ATTRIBUTE_FIELDS.items():
        for row in snapshot['rows'][table]:
            for column in columns:
                value = row[column]
                # Optional costume attributes can be unset; class, origin and
                # the power identity triplet must resolve to actual attributes.
                require((table == 'costumeparts' and value in (None, 0)) or
                        (type(value) is int and value > 0 and value in known),
                        'Selected attribute ID is absent from accepted mapping: ' + table + '.' + column)
    return True
