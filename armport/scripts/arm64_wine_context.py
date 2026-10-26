"""Bounded candidate Windows context for the exact pinned Wine source layout.

Wine b073859675060c9211fcbccfd90e4e87520dc2c2:
dlls/ntdll/unix/signal_arm64.c, syscall_frame and arm64_thread_data.
This is supplementary diagnostic evidence, not a PE unwind implementation.
"""
import struct

WINE_COMMIT = 'b073859675060c9211fcbccfd90e4e87520dc2c2'


def saved_context(read, teb):
    if not teb or teb % 16:
        raise ValueError('unaligned/null TEB')
    # NT_TIB: StackBase +8, StackLimit +16, Self +48 (64-bit Windows).
    tib = bytes(read(teb, 56))
    base, limit = struct.unpack_from('<QQ', tib, 8)
    if struct.unpack_from('<Q', tib, 48)[0] != teb:
        raise ValueError('TEB self pointer mismatch')
    if not 0 < limit < base or base - limit > 64 * 1024 * 1024:
        raise ValueError('invalid Windows stack bounds')
    frame = struct.unpack('<Q', bytes(read(teb + 0x2f0, 8)))[0]
    if not frame or frame % 16:
        raise ValueError('unaligned/null Wine syscall frame')
    fp, lr, sp, pc = struct.unpack('<QQQQ', bytes(read(frame + 0xe8, 32)))
    if sp % 16 or not limit <= sp < base:
        raise ValueError('saved SP outside Windows stack')
    result = dict(frame=frame, pc=pc, lr=lr, fp=fp, sp=sp, frames=[])
    # Only ascending, aligned frames in the first MiB above the saved SP.
    high = min(base, sp + 1024 * 1024)
    for _ in range(16):
        if fp % 16 or not sp <= fp <= high - 16:
            break
        parent, ret = struct.unpack('<QQ', bytes(read(fp, 16)))
        result['frames'].append((fp, ret))
        if parent <= fp:
            break
        fp = parent
    return result
