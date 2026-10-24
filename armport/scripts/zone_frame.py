"""Conservative M3 screen evidence; a dark frame alone never proves a world."""
import math
import re
import subprocess
from pathlib import Path
import tempfile


def load_state(text):
    """Only the latest map load may provide completion evidence."""
    state = {'map': None, 'textures_done': False, 'ready_sent': False}
    for match in re.finditer(r'^ArmPort zone: \d+ (\S+)[ \t]*([^\r\n]*)', text, re.M):
        stage, detail = match.groups()
        if stage == 'map.start':
            state = {'map': detail.split(' tid=')[0].strip(),
                     'textures_done': False, 'ready_sent': False}
        elif stage == 'textures.done':
            state['textures_done'] = True
        elif stage == 'ready.sent' and state['textures_done']:
            state['ready_sent'] = True
    name = (state['map'] or '').replace('\\', '/').lower()
    state['atlas_map'] = name.startswith('maps/city_zones/city_01_01/')
    state['load_complete'] = state['atlas_map'] and state['ready_sent']
    return state


def frame_stats(png, window):
    if not png or not window:
        return None
    x, y, width, height = window
    if min(x, y) < 0 or width < 640 or height < 480:
        return None
    result = subprocess.run(['convert', str(png), '-crop', f'{width}x{height}+{x}+{y}',
        '+repage', '-colorspace', 'gray', '-format', '%[fx:mean] %[fx:standard_deviation]',
        'info:'], capture_output=True, text=True, timeout=30)
    try:
        mean, deviation = map(float, result.stdout.split())
        if result.returncode or not all(map(math.isfinite, (mean, deviation))):
            return None
        return {'mean': mean, 'deviation': deviation}
    except ValueError:
        return None


def nonblank(stats):
    return bool(stats and 0.02 < stats['mean'] < 0.8 and stats['deviation'] > 0.02)


def evaluate(png, window, stdio, ocr):
    state = load_state(stdio)
    stats = frame_stats(png, window)
    # OCR is expensive; do it only after original loading and nonblank checks.
    words = ''
    if state['load_complete'] and nonblank(stats):
        x, y, width, height = window
        # Text elsewhere on the X display is not the client's map-name UI.
        with tempfile.TemporaryDirectory(prefix='armport-frame-') as temporary:
            cropped = Path(temporary) / 'client.png'
            result = subprocess.run(['convert', str(png), '-crop', f'{width}x{height}+{x}+{y}',
                '+repage', str(cropped)], capture_output=True, timeout=30)
            if result.returncode == 0 and cropped.is_file():
                words = ocr(cropped)
    map_visible = bool(re.search(r'\batlas\s+park\b', words, re.I))
    return {**state, 'frame': stats, 'map_name_visible': map_visible,
            'ocr': words[:2000], 'rendered': state['load_complete'] and nonblank(stats) and map_visible}
