#!/usr/bin/env python3
"""Map dispatched game command ids to their original handleGameCmd handlers.

Input: the prepared original source and the `game_commands` histogram that
run_ci.py reports (id -> count). Output: one row per dispatched command with
its enum name and the original handler, for the receiver coverage inventory.
This reads source only; it does not claim any destination is covered.
"""
import argparse
import json
from pathlib import Path
import re


def enum_ids(source):
    """ServerCommCmd: SERVER_UPDATE = COMM_MAX_CMD, then sequential ids."""
    net = (source / 'libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h').read_text(errors='replace')
    base = int(re.search(r'COMM_MAX_CMD\s*=\s*(\d+)', net)[1])
    text = (source / 'Common/comm_game.h').read_text(errors='replace')
    body = text[text.index('typedef enum ServerCommCmd'):text.index('} ServerCommCmd;')]
    body = re.sub(r'//[^\n]*|/\*.*?\*/', '', body, flags=re.S)
    names, value = {}, None
    for name, explicit in re.findall(r'\b(SERVER_[A-Z0-9_]+)\s*(?:=\s*([A-Za-z0-9_]+))?\s*,', body):
        if explicit:
            value = base if explicit == 'COMM_MAX_CMD' else int(explicit, 0)
        names[value] = name
        value += 1
    return names


def handlers(source):
    text = (source / 'Game/src/clientcomm/clientcomm.c').read_text(errors='replace')
    body = text[text.index('static int handleGameCmd('):]
    body = body[:body.index('\n}\n')]
    mapping = dict(re.findall(r'_Ch\((SERVER_[A-Z0-9_]+),\s*([A-Za-z0-9_]+)\)', body))
    for name in re.findall(r'xcase (SERVER_[A-Z0-9_]+):', body):
        mapping.setdefault(name, 'inline')
    return mapping


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--histogram', required=True, help='JSON object id -> count')
    a = ap.parse_args()
    ids, handled = enum_ids(a.source), handlers(a.source)
    histogram = json.loads(a.histogram)
    rows = []
    for key, count in sorted(histogram.items(), key=lambda kv: int(kv[0])):
        name = ids.get(int(key), 'UNKNOWN')
        rows.append(dict(id=int(key), name=name, count=count, handler=handled.get(name, 'not in handleGameCmd')))
    print(json.dumps(rows, indent=1))


if __name__ == '__main__':
    main()
