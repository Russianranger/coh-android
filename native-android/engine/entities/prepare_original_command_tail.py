#!/usr/bin/env python3
"""Generate unchanged client command handlers, enum and source fixture senders."""
import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
def source(root, path):
    file = root / 'upstream/ouroboros' / path
    text = file.read_text() if file.is_file() else subprocess.check_output(
        ['git', '-C', root, 'show', 'HEAD:upstream/ouroboros/' + path], text=True)
    return text.replace('\r\n', '\n')
def generate(root):
    spec = importlib.util.spec_from_file_location('command_extract', HERE / 'prepare_original_costume_receive.py')
    extract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(extract)
    paths = ['Game/src/clientcomm/clientcomm.c', 'Game/src/clientcomm/clientcommreceive.c',
             'Game/src/storyarc/contactClient.c', 'Common/comm_game.h',
             'Common/entity/entPlayer.h', 'libs/UtilitiesLib/include/utilitieslib/network/net_structdefs.h',
             'Game/src/storyarc/storyarcClient.c', 'MapServer/src/storyarc/storySend.c',
             'Common/storyarc/contactCommon.h', 'Common/entity/gametypes.h',
             'Game/src/UI/uiCompass.h', 'Game/src/UI/uiNet.c', 'Game/src/UI/uiTurnstile.c',
             'Common/storyarc/ScriptUIEnum.h', 'Common/gameComm/wdwbase.h',
             'Common/entity/character_karma.c', 'Common/entity/character_karma.h',
             'MapServer/src/gameComm/sendToClient.c', 'MapServer/src/entity/entserver.c',
             'MapServer/src/player/parseClientInput.c', 'MapServer/src/gameSys/EndGameRaid.c']
    texts = {path: source(root, path) for path in paths}
    assert re.search(r'COMM_MAX_CMD\s*=\s*2\b', texts[paths[5]])
    assert re.search(r'#define\s+MAX_MAPVISIT_CELLS\s+\(32\*32\*8\)', texts[paths[4]])
    for key, value, index in [('ALIGNMENT_POINT_MAX_COUNT', 5, 8), ('LEN_CONTACT_DIALOG', 20000, 8),
                              ('LEN_MISSION_INTRO', 256, 8), ('MAX_NAME_LEN', 128, 9),
                              ('MAX_ZOWIE_NAME', 128, 9), ('MAX_ZOWIE_TYPE', 8, 9)]:
        assert re.search(r'#define\s+' + key + r'\s+' + str(value) + r'\b', texts[paths[index]])
    assert re.search(r'char\s+name\[256\]', texts[paths[10]])
    assert re.search(r'char\s+mapName\[512\]', texts[paths[10]])
    comm = texts[paths[3]]
    start = comm.index('typedef enum ServerCommCmd')
    enum = comm[start:comm.index('} ServerCommCmd;', start) + len('} ServerCommCmd;')]
    functions = [(paths[0], 'receiveByteAlignmentTag'), (paths[1], 'receiveStaticMapCells'),
        (paths[2], 'ContactStatusReceive'), (paths[2], 'ContactStatusListReceive'),
        (paths[2], 'ContactStatusDestroyAdapter'), (paths[2], 'ContactStatusAccessibleListReceive'),
        (paths[1], 'receiveVisitLocations'), (paths[2], 'TaskStatusReceive'),
        (paths[2], 'TaskStatusListReceive'), (paths[6], 'ClueReceive'),
        (paths[6], 'StoryClueDestroyAdapter'), (paths[6], 'ClueListReceive'),
        (paths[6], 'KeyClueListReceive'), (paths[6], 'scReceiveHeader'), (paths[6], 'scReceiveAllHeaders'), (paths[11], 'receiveKarmaStats'),
        (paths[11], 'receiveIncarnateTrialStatus'), (paths[11], 'receiveChangeWindowColors'),
        (paths[12], 'turnstileGame_HandleEventStartStatus')]
    senders = [(paths[7], 'ContactStatusSendEmpty'), (paths[7], 'ClueSend'),
        (paths[15], 'CharacterKarmaStatsSend'), (paths[17], 'sendIncarnateTrialStatus')]
    guards = {key: texts[paths[2]][:texts[paths[2]].index(needle)].count('\n') + 1
        for key, needle in {'CONTACT_INDEX': 'contactNumber = pktGetBitsAuto(pak);',
            'CONTACT_SIZE': 'contactSize = pktGetBitsAuto(pak);',
            'TASK_INDEX': 'taskIndex = pktGetBitsPack(pak, 1);',
            'TASK_SIZE': 'taskSize = pktGetBitsPack(pak, 1);'}.items()}
    guards['KARMA_COUNT'] = texts[paths[11]][:texts[paths[11]].index('count = pktGetBitsAuto(pak);', texts[paths[11]].index('void receiveKarmaStats'))].count('\n') + 1
    def original_enum(path, name):
        text = texts[path]
        start = text.index('typedef enum ' + name)
        return text[start:start + re.search(r'}\s*' + name + r';', text[start:]).end()]
    extra_types = '\n'.join(original_enum(paths[index], name) for index, name in ((13, 'ScriptUIType'), (13, 'TrialStatus'), (14, 'WindowName'), (16, 'CharacterKarmaReason')))
    dispatch = []
    for match in re.finditer(r'_Ch\(\s*(SERVER_\w+)\s*,\s*(\w+)\s*\)', texts[paths[0]]):
        line = texts[paths[0]].rfind('\n', 0, match.start()) + 1
        disabled = texts[paths[0]][line:match.start()].lstrip().startswith('//')
        dispatch.append({'command': match[1], 'handler': match[2], 'enabled': not disabled})
    assert len(dispatch) == 213 and sum(row['enabled'] for row in dispatch) == 212
    assert [row['command'] for row in dispatch if not row['enabled']] == ['SERVER_ENABLE_ASSERT_ON_BS_ERRORS']
    def packet_block(path, anchor):
        text = texts[path];start = text.index(anchor);end = text.index('END_PACKET', start) + len('END_PACKET')
        return text[start:end]
    fixture_blocks = {name: packet_block(paths[index], anchor) for name, index, anchor in (
        ('window_colors', 18, 'START_PACKET(pak, e, SERVER_CHANGE_WINDOW_COLORS)'),
        ('event_start', 20, 'START_PACKET(pak_out, e, SERVER_EVENT_START_STATUS)'))}
    fixture_senders = '\nvoid original_window_colors_send(Entity *e,U32 oldColor,U32 newColor){' + fixture_blocks['window_colors'] + ';}\nvoid original_event_start_send(Entity *e){' + fixture_blocks['event_start'] + ';}\n'
    def whole(items):
        result = ''
        for path, name in items:
            body = extract.extract(texts[path], name)
            line = texts[path][:texts[path].index(body.strip())].count('\n') + 1
            result += '#line ' + str(line) + ' "' + path + '"\n' + body
        return result
    output = ('/* Unchanged source functions; bounded typed staging and no-I/O shims. */\n'
        '#ifdef COH_ORIGINAL_COMMAND_TYPES\n#define COMM_MAX_CMD 2\n' +
        ''.join('#define COMMAND_' + key + '_LINE ' + str(value) + '\n' for key, value in guards.items()) +
        enum + '\n' + extra_types + '\n#elif defined(COH_ORIGINAL_COMMAND_SENDERS)\n' + whole(senders) + fixture_senders +
        '#else\n' + whole(functions) + '#endif\n')
    expected_dispatch = {'SERVER_ALL_STATIC_MAP_CELLS': 'receiveStaticMapCells',
        'SERVER_CONTACT_STATUS': 'ContactStatusListReceive',
        'SERVER_ACCESSIBLE_CONTACT_STATUS': 'ContactStatusAccessibleListReceive',
        'SERVER_TASK_VISITLOCATION_UPDATE': 'receiveVisitLocations',
        'SERVER_TASK_STATUS': 'TaskStatusListReceive', 'SERVER_CLUE_UPDATE': 'ClueListReceive',
        'SERVER_KEYCLUE_UPDATE': 'KeyClueListReceive', 'SERVER_SOUVENIRCLUE_UPDATE': 'scReceiveAllHeaders',
        'SERVER_BEGIN_BYTE_ALIGNED_DATA': 'receiveByteAlignmentTag',
        'SERVER_SEND_KARMA_STATS': 'receiveKarmaStats',
        'SERVER_EVENT_START_STATUS': 'turnstileGame_HandleEventStartStatus',
        'SERVER_INCARNATE_TRIAL_STATUS': 'receiveIncarnateTrialStatus',
        'SERVER_CHANGE_WINDOW_COLORS': 'receiveChangeWindowColors'}
    for command, name in expected_dispatch.items():
        assert re.search(r'_Ch\(\s*' + command + r'\s*,\s*' + name + r'\s*\)', texts[paths[0]])
    dispatch_text = ''.join(('COH_COMMAND_DISPATCH' if row['enabled'] else 'COH_COMMAND_DISABLED') + '(' + row['command'] + ', ' + row['handler'] + ', ' + str(int(row['command'] in expected_dispatch)) + ')\n' for row in dispatch)
    output = output.replace('#elif defined(COH_ORIGINAL_COMMAND_SENDERS)', '#elif defined(COH_ORIGINAL_COMMAND_DISPATCH)\n' + dispatch_text + '#elif defined(COH_ORIGINAL_COMMAND_SENDERS)')
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
    proof = {'sources_sha256_lf': {path: digest(text) for path, text in texts.items()},
        'whole_functions_sha256_lf': {name: digest(extract.extract(texts[path], name)) for path, name in functions + senders},
        'source_bounds_guard_lines': guards, 'original_dispatch': expected_dispatch,
        'dispatch_table': [{**row, 'qualified_by_this_adapter': row['command'] in expected_dispatch} for row in dispatch],
        'dispatch_active': 212, 'dispatch_textual': 213, 'dispatch_qualified': len(expected_dispatch),
        'entry_fixture_blocks_sha256_lf': {name: digest(block) for name, block in fixture_blocks.items()},
        'enum_sha256_lf': digest(enum), 'generated_sha256': digest(output)}
    return output, proof
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text, proof = generate(args.source_root)
    output = HERE / 'original_command_tail.inc'
    if args.check:
        assert output.read_text() == text
    else:
        output.write_text(text)
    print(json.dumps(proof))
