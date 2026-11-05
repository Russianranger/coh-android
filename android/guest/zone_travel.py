"""The game's own zone travel on the device: which requested zones to start.

With `COH_STOCK_TRAVEL=1` the station wait is gone. Doors, zone tunnels and the
monorail take the stock path: the MapServer freezes the player (untargetable,
invincible), the client shows its loading screen at once, and the DbServer
asks for the destination (external-maps layer). `ExternalMapSupervisor` reads
that request; this policy decides whether the zoning server starts it with the
request's cookie or delinks it, in which case the player is told the map failed
and stays where they were (dbUndoMapXfer).

Memory (owner's choice, 2026-11-05): at most two zone servers, the player's
current zone and one more. A third request first stops the resident zone the
player is not on (the least recently occupied); the current zone and a zone
still starting are never stopped for it.
"""
import os

ENABLE_ENVIRONMENT = 'COH_STOCK_TRAVEL'
FORMAT = 1
MAX_ZONE_SERVERS = 2
# The session flow's fixed ports; other zones take the first free port above.
FIXED_PORTS = {1: 7001, 101: 7002, 5: 7003}
FIRST_FREE_PORT = 7004
LAST_PORT = 7099
# Cold start on the Thor: King's Row 191 s with Atlas running (0.13.54), Atlas
# 174 s; a cold tree adds its one-time preparation. Generous, then delink.
START_SECONDS = 900


def requested():
    return os.environ.get(ENABLE_ENVIRONMENT) == '1'


class ZoneTravelPolicy:
    """policy(record, options) for ExternalMapSupervisor.

    tree_for(map_id) -> a tree label the owner can prepare, or None;
    running() -> {map_id: {'ready': bool, 'port': int, 'last_occupied': float}};
    occupied() -> the map id the player is on, or None when unknown.
    """

    def __init__(self, *, tree_for, running, occupied, capacity=MAX_ZONE_SERVERS):
        if type(capacity) is not int or capacity < 1:
            raise ValueError('Invalid zone server capacity')
        self.tree_for = tree_for
        self.running = running
        self.occupied = occupied
        self.capacity = capacity
        self.decisions = []

    def port(self, map_id, maps):
        used = {state.get('port') for state in maps.values()}
        if map_id in FIXED_PORTS:
            return FIXED_PORTS[map_id] if FIXED_PORTS[map_id] not in used else None
        for port in range(FIRST_FREE_PORT, LAST_PORT + 1):
            if port not in used:
                return port
        return None

    def __call__(self, record, options):
        decision = self.decide(record)
        self.decisions.append({'map_id': record['map_id'], 'cookie': record['cookie'],
                               'decision': decision[0],
                               'detail': decision[1] if decision[0] == 'delink' else dict(decision[1])})
        del self.decisions[:-16]
        return decision

    def decide(self, record):
        map_id = record['map_id']
        if record['is_static'] != 1:
            return 'delink', 'not_static'          # missions and instances: a later milestone
        tree = self.tree_for(map_id)
        if tree is None:
            return 'delink', 'zone_not_served'
        maps = self.running()
        if map_id in maps:
            return 'delink', 'already_running'     # the DbServer asks only for maps it lacks
        evict = []
        if len(maps) >= self.capacity:
            current = self.occupied()
            if current is None:
                return 'delink', 'player_zone_unknown'
            idle = sorted((other for other, state in maps.items() if other != current and state.get('ready')),
                          key=lambda other: (maps[other].get('last_occupied', 0), other))
            need = len(maps) - self.capacity + 1
            if len(idle) < need:
                return 'delink', 'capacity'
            evict = idle[:need]
        remaining = {other: state for other, state in maps.items() if other not in evict}
        port = self.port(map_id, remaining)
        if port is None:
            return 'delink', 'no_port'
        return 'start', {'tree': tree, 'evict': evict, 'port': port, 'budget_seconds': START_SECONDS}

    def report(self):
        return {'format': FORMAT, 'capacity': self.capacity, 'decisions': list(self.decisions)}
