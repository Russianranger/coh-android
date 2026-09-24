"""Offline checks for the pinned CoH .texture container and DDS mip envelope.

References in upstream/ouroboros: Game/src/render/{tex.h,tex.c,texEnums.h}
and Utilities/GetTex/src/gettex.c (writeMipMapHeader). No image is decoded,
no graphics API is called, and the result does not establish runtime usability.
"""
import struct

_HEADER = struct.Struct('<iiiiIffB3s')
_MIP_HEADER = struct.Struct('<4i')
_DDS_HEADER = struct.Struct('<31I')
_FORMATS = {b'DXT1': ('DXT1', 0x83F1, 8),
            b'DXT3': ('DXT3', 0x83F2, 16),
            b'DXT5': ('DXT5', 0x83F3, 16)}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _size(width, height, block_bytes, bits):
    if block_bytes:
        return ((width + 3) // 4) * ((height + 3) // 4) * block_bytes
    return width * height * (bits // 8)


def _texture_header(data):
    """Return JSON-safe structural evidence; reject truncated/inconsistent data.

    Unsupported payload formats are reported instead of treated as corruption.
    DDS bytes beyond the advertised mip footprints are reported, not discarded:
    legacy files can have such padding and the pinned reader reads all of it.
    """
    _require(len(data) >= _HEADER.size, 'Truncated texture header')
    head, size, width, height, flags, fade0, fade1, alpha, version = _HEADER.unpack_from(data)
    _require(_HEADER.size < head <= len(data), 'Texture header outside file bounds')
    _require(size >= 0 and head + size == len(data), 'Texture payload size mismatch')
    _require(width > 0 and height > 0 and alpha in (0, 1), 'Invalid texture dimensions/alpha')
    name_end = data.find(b'\0', _HEADER.size, head)
    _require(name_end > _HEADER.size, 'Missing or empty terminated texture name')
    # Never use this embedded name as an extraction path.
    name = data[_HEADER.size:name_end].decode('utf-8', errors='replace')
    payload = data[head:]
    cache = data[name_end + 1:head]
    result = {
        'version': version.decode('ascii', errors='replace'),
        'header_bytes': head, 'payload_bytes': size, 'width': width, 'height': height,
        'flags': flags, 'alpha': bool(alpha), 'embedded_name': name,
        'header_bounds_verified': True, 'payload_size_verified': True,
        'baseline_loader_accepts_container': version in (b'TEX', b'TX2') and head - 32 <= 1024,
        'baseline_dimension_limit_exceeded': width > 1024 or height > 1024,
        'baseline_loader_accepts_payload_format': False,
        'runtime_compatibility': 'unverified',
        'image_pixels_decoded': False,
        'validation_status': 'unsupported_format', 'errors': [], 'warnings': [],
    }
    if version not in (b'TEX', b'TX2'):
        result['structural_validation'] = 'wrapper_only_unknown_version'
        return result
    extension = name.rsplit('.', 1)[-1]
    if extension == 'jpg':
        result.update({'payload_format': 'JPEG',
                       'baseline_loader_accepts_payload_format': bool(flags & (1 << 17)),
                       'structural_validation': 'wrapper_and_jpeg_signature_only'})
        _require(payload.startswith(b'\xff\xd8'), 'Texture JPEG signature mismatch')
        return result
    if extension == 'tga':
        result.update({'payload_format': 'TGA', 'structural_validation': 'wrapper_only',
                       'unsupported_reason': 'Pinned texLoadData refuses TGA payloads'})
        return result
    _require(len(payload) >= 128 and payload[:4] == b'DDS ', 'Truncated or missing DDS header')
    dds = _DDS_HEADER.unpack_from(payload, 4)
    _require(dds[0] == 124, 'Invalid DDS header size')
    # texWriteFile itself writes 124 here; standard DDS writers use 32.
    _require(dds[18] in (32, 124), 'Invalid DDS pixel format header size')
    dw, dh, levels, depth, caps2 = dds[3], dds[2], dds[6], dds[5], dds[27]
    _require(dw > 0 and dh > 0, 'Invalid DDS dimensions')
    _require(levels <= max(dw, dh).bit_length(), 'DDS mip count exceeds dimensions')
    result.update({'dds_width': dw, 'dds_height': dh, 'dds_mip_count': levels,
                   'dds_pixel_format_header_size': dds[18],
                   'dds_dimensions_match_texture_canvas':
                       (dw, dh) == (1 << (width - 1).bit_length(), 1 << (height - 1).bit_length()),
                   'cached_mip_bytes': len(cache) if version == b'TX2' else 0})
    fourcc = payload[84:88]
    pf_flags, bits, green, alpha_mask = dds[19], dds[21], dds[23], dds[25]
    block_bytes = 0
    if fourcc in _FORMATS:
        fmt, format_id, block_bytes = _FORMATS[fourcc]
    elif pf_flags == 65 and bits == 32 and alpha_mask == 0xff000000:
        fmt, format_id = 'ARGB8888', 7
    elif pf_flags == 64 and bits == 24:
        fmt, format_id = 'RGB888', 8
    elif pf_flags == 64 and bits == 16 and green == 0x7e0:
        fmt, format_id = 'RGB565', 4
    elif pf_flags == 65 and bits == 16 and alpha_mask == 0x8000:
        fmt, format_id = 'ARGB1555', 3
    elif pf_flags == 65 and bits == 16 and alpha_mask == 0xf000:
        fmt, format_id = 'ARGB4444', 5
    else:
        result.update({'payload_format': 'DDS_UNSUPPORTED', 'dds_fourcc_hex': fourcc.hex(),
                       'structural_validation': 'wrapper_and_dds_header_only'})
        return result
    result['payload_format'] = fmt
    # CoH stores each cube face separately. Do not pretend to check arrays or volumes.
    if depth not in (0, 1) or caps2 != 0:
        result.update({'structural_validation': 'wrapper_and_dds_header_only',
                       'unsupported_reason': 'DDS volume/cubemap layout not checked'})
        return result
    result['baseline_loader_accepts_payload_format'] = True
    footprint, offsets = 0, []
    mw, mh = dw, dh
    for level in range(max(1, levels)):
        offsets.append((mw, mh, footprint))
        footprint += _size(mw, mh, block_bytes, bits)
        mw, mh = max(1, mw // 2), max(1, mh // 2)
    pixels = payload[128:]
    _require(footprint <= len(pixels), 'Truncated DDS mip payload')
    result.update({'dds_mip_bounds_verified': True, 'dds_mip_bytes': footprint,
                   'dds_uninterpreted_trailing_bytes': len(pixels) - footprint,
                   'structural_validation': 'wrapper_dds_mip_bounds',
                   'cached_mip_verified': None})
    if len(pixels) != footprint:
        result['warnings'].append('DDS has bytes beyond advertised mip footprints; preserved, not interpreted')
    if result['baseline_dimension_limit_exceeded']:
        result['warnings'].append('Logical dimensions exceed the pinned client MAX_TEX_SIZE of 1024')
    if version == b'TX2' and cache:
        _require(len(cache) >= _MIP_HEADER.size, 'Truncated cached mip header')
        structsize, cw, ch, cf = _MIP_HEADER.unpack_from(cache)
        _require(structsize == 16 and cw > 0 and ch > 0, 'Invalid cached mip header')
        _require(cf == format_id, 'Cached mip format differs from DDS')
        matches = [offset for mw, mh, offset in offsets if (mw, mh) == (cw, ch)]
        _require(matches and cache[16:] == pixels[matches[0]:],
                 'Cached mip data differs from DDS mip suffix')
        result.update({'cached_mip_verified': True,
                       'cached_mip_width': cw, 'cached_mip_height': ch})
    if result['baseline_loader_accepts_container']:
        result['validation_status'] = 'structural_checks_passed'
    return result


def texture_header(data):
    """Return check results, including explicit failures, without executing assets."""
    try:
        return _texture_header(data)
    except (ValueError, struct.error) as error:
        return {'validation_status': 'structural_checks_failed', 'errors': [str(error)],
                'warnings': [], 'runtime_compatibility': 'unverified',
                'image_pixels_decoded': False}
