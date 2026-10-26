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


def frame_stats(png, window, minimum=(640, 480)):
    if not png or not window:
        return None
    x, y, width, height = window
    if min(x, y) < 0 or width < minimum[0] or height < minimum[1]:
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


def world_region(window):
    """Central client area between the original HUD windows (nav/target top,
    chat/tray bottom, power/team side windows). 3D world pixels only."""
    x, y, width, height = window
    return (x + width // 5, y + height * 3 // 20, width * 3 // 5, height * 9 // 20)


# The original in-world HUD (uiNav/uiTarget/uiChat/uiTray) labels. The original
# client never prints the zone display name in-world: uiCompass draws only
# destination names and uiAutomap's footer prints the gMapName file path.
# Run 40356647478 OCR: "Navy, Menu, 1 No Target ... GontactmMission ... Actions
# ... Salvage ... Global"; individual labels drop out between frames.
HUD_LABELS = ('target', 'nav', 'menu', 'contact', 'mission', 'actions', 'chat', 'tray',
              'salvage', 'global')
# uiHelp.c displayHelperStatusPopup (DoYouWantToFlagForHelp), modal over the world.
HELPER_DIALOG = re.compile(r'this\s+character\s+is\s+new', re.I)


def hud_labels(words):
    return [label for label in HUD_LABELS if re.search(label, words, re.I)]


def evaluate(png, window, stdio, ocr):
    state = load_state(stdio)
    stats = frame_stats(png, window)
    world = frame_stats(png, world_region(window), (64, 48)) if stats else None
    # OCR is expensive; do it only after original loading and nonblank checks.
    words = ''
    if state['load_complete'] and nonblank(stats):
        x, y, width, height = window
        # Text elsewhere on the X display is not the client's UI.
        with tempfile.TemporaryDirectory(prefix='armport-frame-') as temporary:
            cropped = Path(temporary) / 'client.png'
            result = subprocess.run(['convert', str(png), '-crop', f'{width}x{height}+{x}+{y}',
                '+repage', str(cropped)], capture_output=True, timeout=30)
            if result.returncode == 0 and cropped.is_file():
                words = ocr(cropped)
    labels = hud_labels(words)
    helper = bool(HELPER_DIALOG.search(words))
    world_visible = bool(world and 0.02 < world['mean'] < 0.8 and world['deviation'] > 0.04)
    return {**state, 'frame': stats, 'world_region': world, 'world_region_visible': world_visible,
            'hud_labels': labels, 'helper_dialog_visible': helper,
            # Diagnostic only; see HUD_LABELS. Not part of the verdict.
            'map_name_visible': bool(re.search(r'\batlas\s+park\b', words, re.I)),
            'ocr': words[:2000],
            'rendered': (state['load_complete'] and nonblank(stats) and world_visible
                         and len(labels) >= 4 and not helper)}
