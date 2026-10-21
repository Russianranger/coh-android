"""Select original costume source pins from the accepted all-zone supplement.

Stream the source index; retain only requested body pins and donor metadata
identities. Missing entries here do not establish absence from earlier imports.
"""
import codecs
import hashlib
from pathlib import Path, PurePosixPath
from source_manifest_records import _JSONStream
from imported_archive import safe_path

# Existing pins in tools/android/interactive/prepare_zones_world_assets.py.
MANIFEST_PIN = {'bytes': 4237139, 'sha256': 'f466ad6c8ab6e84dabd16d404c3a05bcb9fbca3cfad5746852d53b04132d8f74'}
ARCHIVE_PIN = {'filename': 'zones-world-supplement.zip', 'bytes': 1663681523,
               'sha256': 'f12a0994cec20ab6d13c158495fe01402e89113ae756e412357e9c4a04833ad3'}
PROVENANCE_PIN = {'bytes': 29961724, 'sha256': '6b49594e9136925644a88246b53110f42c78f383a4c525ed0059622cc2987464'}


def pinned_chunks(path, pin):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size != pin['bytes']:
        raise ValueError('Pinned source index file differs')
    digest, size = hashlib.sha256(), 0
    utf8 = codecs.getincrementaldecoder('utf-8')('strict')
    with path.open('rb') as stream:
        while True:
            raw = stream.read(65536)
            if not raw:
                break
            size += len(raw)
            if size > pin['bytes']:
                raise ValueError('Pinned source index grew')
            digest.update(raw)
            yield utf8.decode(raw)
    end = utf8.decode(b'', final=True)
    if end:
        yield end
    if size != pin['bytes'] or digest.hexdigest() != pin['sha256']:
        raise ValueError('Pinned source index SHA differs')


def zone_records(path, paths=(), texture_names=(), metadata_archives=()):
    if (len(paths) + len(texture_names) + len(metadata_archives) > 64
            or any(not safe_path(name) for name in paths)
            or any(not safe_path(name) or '/' in name for name in texture_names)):
        raise ValueError('Selected supplement lookup exceeds bounded requests')
    wanted = {name.casefold() for name in paths}
    textures = {PurePosixPath(name).stem.casefold() for name in texture_names}
    donors = set(metadata_archives)
    found, identities, seen = {}, {}, set()
    source = _JSONStream(pinned_chunks(path, MANIFEST_PIN))

    def files(name):
        match = name.casefold() in wanted or (name.startswith('data/texture_library/')
                    and name.endswith('.texture') and PurePosixPath(name).stem.casefold() in textures)
        if match:
            if name in found or len(found) >= 64:
                raise ValueError('Duplicate or oversized selected supplement paths')
            found[name] = source.record()
        else:
            source.value()

    def metadata():
        source.expect('[')
        source.whitespace()
        if source.peek() == ']':
            source.take()
            return
        while True:
            row = source.record()
            if row['archive'] in donors:
                if row['archive'] in identities:
                    raise ValueError('Duplicate selected donor identity')
                identities[row['archive']] = row
            source.whitespace()
            separator = source.take()
            if separator == ']':
                return
            if separator != ',':
                raise ValueError('Invalid donor identity array')

    def root(key):
        if key in ('files', 'frozen_metadata_archives', 'archive'):
            if key in seen:
                raise ValueError('Duplicate supplement source field')
            seen.add(key)
        if key == 'files':
            source.object(files)
        elif key == 'frozen_metadata_archives':
            metadata()
        elif key == 'archive':
            if source.record() != ARCHIVE_PIN:
                raise ValueError('Supplement archive identity differs')
        else:
            source.value()

    source.object(root)
    source.whitespace()
    if source.peek() is not None or seen != {'files', 'frozen_metadata_archives', 'archive'} or set(identities) != donors:
        raise ValueError('Supplement source structure differs')
    return {'files': found, 'metadata_archives': identities, 'archive': dict(ARCHIVE_PIN),
            'scope': 'Selected supplement pins only; earlier imported sources remain separate'}


def selected_provenance(chunks, paths):
    """Consume hash-verifying chunks; only return after their complete EOF proof."""
    requested = {name.casefold() for name in paths}
    if not 0 < len(requested) <= 64 or any(not safe_path(name) for name in requested):
        raise ValueError('Selected provenance request differs')
    source = _JSONStream(chunks)
    found, seen = {}, False

    def entry(name):
        if name.casefold() in requested:
            if name in found:
                raise ValueError('Duplicate selected provenance path')
            found[name] = source.record()
        else:
            source.value()

    def root(key):
        nonlocal seen
        if key == 'entries':
            if seen:
                raise ValueError('Duplicate provenance entries')
            seen = True
            source.object(entry)
        else:
            source.value()

    source.object(root)
    source.whitespace()
    if source.peek() is not None or not seen or set(found) != requested:
        raise ValueError('Selected original provenance is incomplete')
    return found
