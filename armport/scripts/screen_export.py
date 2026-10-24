#!/usr/bin/env python3
"""Emit a small JPEG as base64 in GitHub notice annotations (at most 10 of
3800 characters), so the screen can be read back with the check-run
annotations API when artifact downloads are not available.
Reassemble: concatenate the parts in order and base64-decode."""
import base64
import sys

data = base64.b64encode(open(sys.argv[1], 'rb').read()).decode()
title = sys.argv[2] if len(sys.argv) > 2 else 'ArmPort screen'
parts = [data[i:i + 3800] for i in range(0, len(data), 3800)]
if len(parts) > 10:  # GitHub keeps about ten notices per step
    print(f'::warning title={title}::image too large ({len(data)} base64 chars)')
    sys.exit(0)
for i, part in enumerate(parts):
    print(f'::notice title={title} {i + 1}/{len(parts)}::{part}')
