"""Bounded complete startup log: renderer evidence precedes noisy asset loading."""
MAX_BYTES = 16 * 1024 * 1024


def read_stdio(path):
    if not path.exists():
        return ''
    if path.is_symlink():
        raise ValueError('Linked ARM64 log refused')
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('ARM64 diagnostic log exceeded 16 MiB')
    return data.decode('utf-8', 'replace')
