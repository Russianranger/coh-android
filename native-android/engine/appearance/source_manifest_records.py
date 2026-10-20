"""Select a bounded set of original provenance records from the pinned CLIENT manifest.

The compressed envelope is bounded; its decoded catalog is hashed and parsed as
a stream. Only requested provenance/entries values are retained.
"""
import base64
import codecs
import hashlib
import json
import re
import zlib
from pathlib import Path

# Existing MANIFEST_PIN and scope in
# tools/android/interactive/prepare_client_appearance_assets.py.
MANIFEST_PIN = {'bytes': 42257673, 'sha256': '8b3f579a9ff48e80f40e06e252c91fe3357daf9f0b01441dea5bceaa5801f1e6'}
SCOPE = 'coh_client_appearance_source_manifest_v1'
MAX_WRAPPER = 12 << 20
MAX_GZIP = 8 << 20
MAX_RECORD = 256 << 10
CHUNK = 64 << 10
SPECIAL = re.compile(r'["\\\x00-\x1f]')


def _require(value, message):
    if not value:
        raise ValueError(message)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'Duplicate manifest JSON field')
        result[key] = value
    return result


def _decoded(packed):
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    utf8 = codecs.getincrementaldecoder('utf-8')('strict')
    digest = hashlib.sha256()
    total = 0
    for offset in range(0, len(packed), CHUNK):
        tail = packed[offset:offset + CHUNK]
        while tail:
            raw = decoder.decompress(tail, CHUNK)
            tail = decoder.unconsumed_tail
            _require(not decoder.unused_data, 'Trailing or concatenated manifest gzip stream')
            total += len(raw)
            _require(total <= MANIFEST_PIN['bytes'], 'Decoded manifest exceeds source pin')
            digest.update(raw)
            text = utf8.decode(raw)
            if text:
                yield text
    _require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail,
             'Truncated or trailing manifest gzip stream')
    text = utf8.decode(b'', final=True)
    if text:
        yield text
    _require(total == MANIFEST_PIN['bytes'] and digest.hexdigest() == MANIFEST_PIN['sha256'],
             'Decoded manifest identity differs from existing source pin')


class _JSONStream:
    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.text = ''
        self.pos = 0
        self.done = False
        self.capture = None
        self.captured = 0

    def peek(self):
        while self.pos == len(self.text) and not self.done:
            try:
                self.text = next(self.chunks)
                self.pos = 0
            except StopIteration:
                self.done = True
        return None if self.pos == len(self.text) else self.text[self.pos]

    def take(self, count=1):
        pieces = []
        while count:
            _require(self.peek() is not None, 'Truncated manifest JSON')
            size = min(count, len(self.text) - self.pos)
            piece = self.text[self.pos:self.pos + size]
            self.pos += size
            count -= size
            pieces.append(piece)
            if self.capture is not None:
                self.captured += len(piece)
                _require(self.captured <= MAX_RECORD, 'Selected provenance record exceeds bound')
                self.capture.append(piece)
        return ''.join(pieces)

    def whitespace(self):
        while self.peek() in (' ', '\t', '\r', '\n'):
            self.take()

    def expect(self, char):
        self.whitespace()
        _require(self.take() == char, 'Invalid manifest JSON delimiter')

    def string(self, retain=False):
        self.expect('"')
        pieces = ['"'] if retain else None
        length = 0
        while True:
            _require(self.peek() is not None, 'Truncated manifest JSON string')
            match = SPECIAL.search(self.text, self.pos)
            end = match.start() if match else len(self.text)
            text = self.take(end - self.pos)
            if retain:
                length += len(text)
                _require(length <= 8192, 'Manifest key exceeds bound')
                pieces.append(text)
            if not match:
                continue
            char = self.take()
            if retain:
                pieces.append(char)
            if char == '"':
                return json.loads(''.join(pieces)) if retain else None
            _require(char == '\\', 'Unescaped control in manifest JSON string')
            escape = self.take()
            _require(escape in '"\\/bfnrtu', 'Invalid manifest JSON escape')
            if retain:
                pieces.append(escape)
            if escape == 'u':
                digits = self.take(4)
                _require(all(char in '0123456789abcdefABCDEF' for char in digits), 'Invalid manifest JSON Unicode escape')
                if retain:
                    pieces.append(digits)

    def value(self, depth=0):
        _require(depth <= 64, 'Manifest JSON nesting exceeds bound')
        self.whitespace()
        char = self.peek()
        if char == '"':
            self.string()
        elif char == '{':
            self.object(lambda key: self.value(depth + 1), retain_keys=False, depth=depth)
        elif char == '[':
            self.take()
            self.whitespace()
            if self.peek() == ']':
                self.take()
                return
            while True:
                self.value(depth + 1)
                self.whitespace()
                char = self.take()
                if char == ']':
                    return
                _require(char == ',', 'Invalid manifest JSON array')
        else:
            _require(char is not None and char in '-0123456789tfn', 'Invalid manifest JSON scalar')
            token = []
            while self.peek() is not None and self.peek() not in ' \t\r\n,]}':
                token.append(self.take())
                _require(len(token) <= 128, 'Manifest JSON scalar exceeds bound')
            value = ''.join(token)
            _require(re.fullmatch(r'(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)', value),
                     'Invalid manifest JSON scalar spelling')

    def object(self, visit, retain_keys=True, depth=0):
        _require(depth <= 64, 'Manifest JSON nesting exceeds bound')
        self.expect('{')
        self.whitespace()
        if self.peek() == '}':
            self.take()
            return
        while True:
            key = self.string(retain_keys)
            self.expect(':')
            visit(key)
            self.whitespace()
            char = self.take()
            if char == '}':
                return
            _require(char == ',', 'Invalid manifest JSON object')

    def record(self):
        _require(self.capture is None, 'Nested manifest record capture')
        self.capture, self.captured = [], 0
        self.value()
        raw = ''.join(self.capture)
        self.capture = None
        record = json.loads(raw, object_pairs_hook=_unique)
        _require(isinstance(record, dict), 'Provenance entry must remain an original object')
        return record


def selected_records(path, requested_paths):
    """Return original provenance records keyed by the caller's requested paths.

    Matching is case-insensitive and exact; missing or ambiguous requested keys
    raise ValueError. The complete decoded source is verified before returning.
    """
    _require(not isinstance(requested_paths, (str, bytes)), 'Requested paths must be a bounded collection')
    requested = {}
    for name in requested_paths:
        _require(isinstance(name, str) and name and len(name) <= 8192 and '\0' not in name,
                 'Invalid requested manifest path')
        key = name.casefold()
        _require(key not in requested and len(requested) < 64, 'Repeated requested path or selection limit')
        requested[key] = name
    _require(requested, 'At least one requested manifest path is required')
    path = Path(path)
    _require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= MAX_WRAPPER,
             'Source manifest wrapper must be a bounded regular file')
    raw = path.read_bytes()
    _require(len(raw) <= MAX_WRAPPER, 'Source manifest wrapper grew beyond bound')
    wrapper = json.loads(raw, object_pairs_hook=_unique)
    _require(isinstance(wrapper, dict) and set(wrapper) == {'format', 'scope', 'encoding', 'decoded', 'gzip', 'data'}
             and type(wrapper['format']) is int and wrapper['format'] == 1
             and wrapper['scope'] == SCOPE and wrapper['encoding'] == 'gzip+base64'
             and isinstance(wrapper['decoded'], dict) and type(wrapper['decoded'].get('bytes')) is int
             and wrapper['decoded'] == MANIFEST_PIN, 'Source manifest wrapper identity differs')
    pin = wrapper['gzip']
    _require(isinstance(pin, dict) and set(pin) == {'bytes', 'sha256'}
             and type(pin['bytes']) is int and 0 < pin['bytes'] <= MAX_GZIP
             and isinstance(pin['sha256'], str) and re.fullmatch('[0-9a-f]{64}', pin['sha256'])
             and isinstance(wrapper['data'], str) and len(wrapper['data']) == 4 * ((pin['bytes'] + 2) // 3),
             'Source manifest gzip envelope differs')
    packed = base64.b64decode(wrapper['data'], validate=True)
    _require(len(packed) == pin['bytes'] and hashlib.sha256(packed).hexdigest() == pin['sha256'],
             'Source manifest gzip identity differs')
    del raw, wrapper
    stream = _JSONStream(_decoded(packed))
    found = {}
    sections = set()

    def entry(key):
        folded = key.casefold()
        if folded in requested:
            name = requested[folded]
            _require(name not in found, 'Ambiguous requested provenance path')
            found[name] = stream.record()
        else:
            stream.value()

    def provenance(key):
        if key == 'entries':
            _require('entries' not in sections, 'Repeated provenance entries table')
            sections.add('entries')
            stream.object(entry)
        else:
            stream.value()

    def root(key):
        if key == 'provenance':
            _require('provenance' not in sections, 'Repeated manifest provenance section')
            sections.add('provenance')
            stream.object(provenance)
        else:
            stream.value()

    stream.object(root)
    stream.whitespace()
    _require(stream.peek() is None, 'Trailing manifest JSON data')
    _require(sections == {'provenance', 'entries'}, 'Original provenance entries table missing')
    _require(len(found) == len(requested), 'Requested original provenance records missing')
    return found
