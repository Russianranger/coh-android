"""Single-player content (0.13.85): the Primalist archetype's definition files.

The app carries `single-player-content.zip`: text definitions that replace or add to the
imported game text (armport/content/single-player in the repository: the class file, its
power files, their animation bindings and two text lines). The imported game data stays
read-only. A zone server's private data tree gets a private regular copy of each file in
place of the link to the import (`install`); the compiled definition files (bins) made from
the replaced text are removed so the server builds them again from the new text (`drop_stale_bins`);
and the class name is appended to the database's name list (`append_class_attribute`), at
the end, as the game's own template tool does, so every existing name keeps its number.

The content is used only when the session asks for it (`COH_PRIMALIST=1`) or when the
database already holds the class name: once a Primalist can exist in the saved game, the
server must always know the class.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import zipfile

ARCHIVE = 'single-player-content.zip'
MANIFEST = 'manifest.json'
ENABLE_ENVIRONMENT = 'COH_PRIMALIST'
MAX_ARCHIVE = 16 * 1024 * 1024
MAX_FILES = 256
MAX_FILE = 4 * 1024 * 1024
TOP_LEVEL = frozenset({'defs', 'menu', 'texts'})
# Modification time of every installed copy: not the imported text's normalized time, so the
# game's own freshness check (a server that does not trust its bins) rebuilds from them too.
FILE_TIME = 1795564800
CLASS_ATTRIBUTE = 'Class_Primalist'
ATTRIBUTE_FILE = 'data/server/db/templates/vars.attribute'
ATTRIBUTE_TABLE = 'attributes'
BIN_ROOTS = ('server/bin', 'bin')
MARKER = 'server/bin/armport-single-player-content.json'
NAME = re.compile(r'[a-z0-9_][a-z0-9_.-]{0,95}(?:/[a-z0-9_][a-z0-9_.-]{0,95}){1,11}')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def requested():
    return os.environ.get(ENABLE_ENVIRONMENT) == '1'


class Content:
    """The verified archive, held in memory (under 2 MB of text)."""

    def __init__(self, identity, files, archive):
        self.identity, self.files, self.archive = identity, files, archive

    def top_level(self, name):
        return name.split('/', 1)[0]

    def selected(self, skip=(), only=None):
        """Entries whose top-level folder this mirror stages."""
        skip = {value.casefold() for value in skip}
        only = None if only is None else {value.casefold() for value in only}
        return {name: entry for name, entry in self.files.items()
                if self.top_level(name) not in skip and (only is None or self.top_level(name) in only)}

    def summary(self):
        return {'format': 1, 'identity': self.identity, 'archive': dict(self.archive),
                'files': len(self.files), 'bytes': sum(len(entry['data']) for entry in self.files.values()),
                'replaced': sum(1 for entry in self.files.values() if not entry['new']),
                'added': sum(1 for entry in self.files.values() if entry['new'])}


def load(assets):
    """The app's content archive, or None when this package carries none."""
    path = Path(assets) / ARCHIVE
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= MAX_ARCHIVE, 'Invalid single-player content archive')
    data = path.read_bytes()
    pin = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) and MANIFEST in names and len(names) <= MAX_FILES + 1,
                'Invalid single-player content members')
        require(archive.getinfo(MANIFEST).file_size <= 1024 * 1024, 'Oversized single-player content manifest')
        manifest = json.loads(archive.read(MANIFEST))
        listed = manifest.get('files')
        require(isinstance(manifest, dict) and manifest.get('format') == 1
                and manifest.get('name') == 'single-player-content' and isinstance(listed, dict) and listed
                and set(names) == {MANIFEST} | {'data/' + name for name in listed},
                'Single-player content manifest differs from its archive')
        identity = hashlib.sha256(json.dumps(listed, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        require(manifest.get('files_sha256') == identity, 'Single-player content identity differs')
        files = {}
        for name, record in listed.items():
            require(isinstance(name, str) and NAME.fullmatch(name) and name.split('/', 1)[0] in TOP_LEVEL
                    and '..' not in name.split('/') and isinstance(record, dict), 'Unsafe single-player content path')
            info = archive.getinfo('data/' + name)
            require(not info.is_dir() and not info.flag_bits & 1 and not stat.S_ISLNK(info.external_attr >> 16)
                    and info.file_size == record.get('bytes') and 0 < info.file_size <= MAX_FILE,
                    'Invalid single-player content member: ' + name)
            payload = archive.read(info)
            require(hashlib.sha256(payload).hexdigest() == record.get('sha256'),
                    'Single-player content digest differs: ' + name)
            replaces = record.get('replaces')
            require(replaces is None or (isinstance(replaces, dict)
                    and str(replaces.get('path', '')).casefold() == name), 'Invalid replaced path: ' + name)
            files[name] = {'data': payload, 'new': replaces is None, 'sha256': record['sha256']}
    return Content(identity, files, pin)


def write_copy(path, data, *, read_only=False):
    """A private regular file with the content's fixed time, replacing a link or an older copy."""
    path = Path(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        info = None
    require(info is None or stat.S_ISLNK(info.st_mode) or stat.S_ISREG(info.st_mode),
            'Single-player content target is not a file: ' + path.name)
    pending = path.with_name('.' + path.name + '.single-player-pending')
    pending.unlink(missing_ok=True)
    descriptor = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as output:
        output.write(data)
    os.utime(pending, (FILE_TIME, FILE_TIME))
    pending.chmod(0o400 if read_only else 0o600)
    os.replace(pending, path)


def install_new(content, data_root, *, skip=(), only=None, read_only=False):
    """Write the files the import does not have; their folders are already mirrored.

    Returns the relative names as spelled in the tree (the folder's own spelling).
    """
    data_root, written = Path(data_root), []
    for name, entry in sorted(content.selected(skip, only).items()):
        if not entry['new']:
            continue
        current, spelled = data_root, []
        parts = name.split('/')
        for part in parts[:-1]:
            match = [item.name for item in os.scandir(current) if item.name.casefold() == part]
            require(len(match) == 1 and not (current / match[0]).is_symlink() and (current / match[0]).is_dir(),
                    'Single-player content folder is missing or ambiguous: ' + name)
            current /= match[0]; spelled.append(match[0])
        require(not any(item.name.casefold() == parts[-1] for item in os.scandir(current)
                        if item.name != parts[-1]), 'Case-conflicting single-player content file: ' + name)
        # The folder may be read-only while this mirror is being built again over a kept tree.
        write_copy(current / parts[-1], entry['data'], read_only=read_only)
        written.append('/'.join(spelled + [parts[-1]]))
    return written


def parse6_dependencies(path, limit=32 * 1024 * 1024):
    """Source file names of a Parse6 bin (its Files1 table), or None when it is not one.

    Reads the header only. Unlike server_cache_package.inspect_parse6 this accepts any
    recorded file time: bins the server wrote itself carry real times.
    """
    with open(path, 'rb') as stream:
        head = stream.read(12)
        if len(head) < 12 or head[:8] != b'CrypticS':
            return None

        def string(maximum):
            raw = stream.read(2)
            if len(raw) < 2:
                return None
            size = struct.unpack('<H', raw)[0]
            if size > maximum:
                return None
            padded = ((size + 2 + 3) & ~3) - 2
            body = stream.read(padded)
            return body[:size] if len(body) == padded else None

        if string(16) != b'Parse6' or string(16) != b'Files1':
            return None
        raw = stream.read(8)
        if len(raw) < 8:
            return None
        block, count = struct.unpack('<II', raw)
        if not 4 <= block <= limit or count > block // 8:
            return None
        names = []
        for unused in range(count):
            name = string(1024)
            if not name or len(stream.read(4)) < 4:
                return None
            names.append(name.decode('utf-8', errors='replace').replace('\\', '/').casefold())
        return names


def drop_stale_bins(content, data_root, installed=()):
    """Remove bins compiled from text this content replaced; the server rebuilds a missing bin.

    The first pass over a tree checks every bin and leaves a marker; later passes check only
    the bins a prepared-cache package has just seeded (`installed`, names like
    'data/server/bin/x.bin'), which were compiled from the original text by construction.
    A file added by the content is reached through the replaced file that includes it.
    """
    data_root = Path(data_root)
    marker = data_root / MARKER
    replaced = {name for name, entry in content.files.items() if not entry['new']}
    first = True
    try:
        record = json.loads(marker.read_text())
        first = not (isinstance(record, dict) and record.get('identity') == content.identity)
    except (OSError, ValueError):
        pass
    candidates = []
    if first:
        for root in BIN_ROOTS:
            try:
                candidates += [entry.path for entry in os.scandir(data_root / root)
                               if entry.name.casefold().endswith('.bin') and entry.is_file(follow_symlinks=False)]
            except OSError:
                continue
    else:
        for name in installed:
            relative = PurePosixPath(name)
            if relative.parts[:1] == ('data',) and '..' not in relative.parts:
                candidates.append(str(data_root.joinpath(*relative.parts[1:])))
    dropped, checked = [], 0
    for path in sorted(set(candidates)):
        try:
            names = parse6_dependencies(path)
        except OSError:
            continue
        checked += 1
        if names is not None and replaced.intersection(names):
            os.unlink(path)
            dropped.append(Path(path).relative_to(data_root).as_posix())
    if first:
        marker.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        pending = marker.with_name(marker.name + '.pending')
        pending.write_text(json.dumps({'format': 1, 'identity': content.identity, 'dropped': dropped}))
        pending.replace(marker)
    return {'format': 1, 'pass': 'every_bin' if first else 'seeded_bins_only', 'checked': checked,
            'dropped': dropped}


def attribute_line(number):
    return ('%d "%s"\r\n' % (number, CLASS_ATTRIBUTE)).encode()


def append_class_attribute(runtime, schema):
    """Add the class name after the last name of this session's vars.attribute and of the expected rows.

    The DbServer inserts trailing names it does not have yet into its table. Returns the
    name's number. Idempotent for the file; the expected rows gain the name once.
    """
    path = Path(runtime) / ATTRIBUTE_FILE
    data = path.read_bytes()
    rows = schema['expected_attributes'][ATTRIBUTE_TABLE]
    require(isinstance(rows, list) and rows and data.endswith(b'\r\n'), 'Unexpected database name list')
    names = [row['name'] for row in rows]
    if CLASS_ATTRIBUTE.casefold() in names:
        number = names.index(CLASS_ATTRIBUTE.casefold()) + 1
        require(number == len(rows), 'The Primalist class name is not the last database name')
    else:
        number = len(rows) + 1
        rows.append({'id': number, 'name': CLASS_ATTRIBUTE.casefold()})
    last = data[:-2].rsplit(b'\n', 1)[-1]
    if last + b'\r\n' != attribute_line(number):
        require(last.split(b' ', 1)[0] == str(number - 1).encode(),
                'Database name list does not end where the accepted schema ends')
        with open(path, 'ab') as output:
            output.write(attribute_line(number))
    return number


def attribute_present(rows):
    """Whether the database's own name table (id, name rows) already holds the class name."""
    return any(str(row.get('name', '')).casefold() == CLASS_ATTRIBUTE.casefold() for row in rows)
