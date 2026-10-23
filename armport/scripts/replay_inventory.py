#!/usr/bin/env python3
"""Validate the saved Thor logical-message envelopes, without decoding CoH.

Formats: native-android/combined-client InitialReplayStore.java and
post_ready_replay.h. This is input qualification, not M3 receive-code replay.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct


INITIAL_SHA = 'cc949b01f5db6ff108efcf6afcbfe9567c432b4aa15f3a02c8f193e380cc7b39'
POST_SHA = 'f134c3c083e571b679ed6976bec36c672028854f4a48879cc0f2d47423db96a9'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


def u64(data, offset):
    return struct.unpack_from('<Q', data, offset)[0]


def payload(data, size, bits, cursor, aligned, digest):
    require(0 < size <= 4 * 1024 * 1024 and len(data) == size, 'payload size')
    require(0 < bits <= size * 8 and cursor <= bits, 'payload bit bounds')
    require(aligned in (0, 1) and (not aligned or cursor % 8 == 0), 'payload alignment')
    require(hashlib.sha256(data).digest() == digest, 'payload SHA-256')


def initial(data):
    require(88 < len(data) <= 88 + 65536, 'INITIAL file size')
    require(data[:8] == b'COHIRP01' and u32(data, 8) == 88, 'INITIAL header')
    size, bits, cursor = u32(data, 12), u64(data, 16), u64(data, 24)
    appearance, aligned, selected = u64(data, 32), u32(data, 40), u32(data, 44)
    require(appearance <= bits and (not aligned or appearance % 8 == 0), 'appearance cursor')
    require(selected < 10 or selected == 0xffffffff, 'costume index')
    require((u32(data, 48), u32(data, 52)) == (28, 3), 'INITIAL protocol/command')
    payload(data[88:], size, bits, cursor, aligned, data[56:88])
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                payload_bytes=size, logical_bits=bits, post_command_cursor=cursor,
                appearance_cursor=appearance, byte_aligned=aligned, selected_costume=selected,
                packet_id=None, command=3, payload_sha256=data[56:88].hex())


def post_ready(data):
    require(160 <= len(data) <= 8 * 1024 * 1024, 'POST file size')
    require(data[:8] == b'COHPRP01', 'POST magic')
    require(tuple(u32(data, n) for n in (8, 12, 16, 20)) == (64, 112, 96, 128), 'POST header sizes')
    require((u64(data, 24), u64(data, 32), u32(data, 40), u32(data, 44))
            == (8 * 1024 * 1024, 30000, 4 * 1024 * 1024, 4096), 'POST limits')
    require(data[48:64] == bytes(16), 'POST reserved bytes')
    at, records = 64, []
    while data[at:at+8] == b'COHMSG01':
        require(len(records) < 128 and at + 112 <= len(data) - 96, 'record bounds')
        h = data[at:at+112]
        require(u32(h, 8) == 112 and h[108:112] == bytes(4), 'record header')
        size, bits, cursor = u32(h, 12), u64(h, 16), u64(h, 24)
        now, generation, packet_id = u64(h, 32), u64(h, 40), u64(h, 48)
        command, aligned, ordered, ordered_id = (u32(h, n) for n in (56, 60, 64, 68))
        require(at + 112 + size <= len(data) - 96, 'record payload bounds')
        require(generation > 0 and ordered in (0, 1), 'record transport fields')
        require(u32(h, 104) == 0 and command != 0xffffffff, 'unavailable command')
        require(not records or now >= records[-1]['monotonic_ms'], 'record timestamp order')
        payload(data[at+112:at+112+size], size, bits, cursor, aligned, h[72:104])
        records.append(dict(payload_bytes=size, logical_bits=bits, post_command_cursor=cursor,
                            monotonic_ms=now, generation=generation, packet_id=packet_id,
                            command=command, byte_aligned=aligned, ordered=ordered,
                            ordered_id=ordered_id, payload_sha256=h[72:104].hex()))
        at += 112 + size
    trailer = data[at:]
    require(len(trailer) == 96 and trailer[:8] == b'COHPEND1' and u32(trailer, 8) == 96,
            'terminal trailer or trailing bytes')
    require(tuple(u32(trailer, n) for n in (12, 16, 20, 24, 28))
            == (len(records), len(records), 0, 0, 1), 'incomplete observation')
    require(u64(trailer, 32) == sum(r['payload_bytes'] for r in records)
            and u64(trailer, 40) == sum(r['logical_bits'] for r in records), 'trailer totals')
    require((u64(trailer, 48), u64(trailer, 56)) ==
            ((records[0]['monotonic_ms'], records[-1]['monotonic_ms']) if records else (0, 0)),
            'trailer timestamps')
    require(hashlib.sha256(data[:at]).digest() == trailer[64:96], 'prefix SHA-256')
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                record_count=len(records), command_counts=dict(Counter(r['command'] for r in records)),
                payload_bytes=u64(trailer, 32), logical_bits=u64(trailer, 40),
                complete=True, records=records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('initial', type=Path)
    parser.add_argument('post_ready', type=Path)
    parser.add_argument('--records', action='store_true', help='include every record header')
    args = parser.parse_args()
    # Read at most the format caps plus one byte, before inspecting headers.
    with args.initial.open('rb') as stream:
        first = initial(stream.read(88 + 65536 + 1))
    with args.post_ready.open('rb') as stream:
        post = post_ready(stream.read(8 * 1024 * 1024 + 1))
    require(first['sha256'] == INITIAL_SHA and post['sha256'] == POST_SHA,
            'files differ from the HANDOFF Thor session')
    if not args.records:
        records = post.pop('records')
        post.update(first=records[0], last=records[-1])
    print(json.dumps(dict(scope='envelope_validation_only', receive_code_replayed=False,
                          initial=first, post_ready=post), indent=2))


if __name__ == '__main__':
    main()
