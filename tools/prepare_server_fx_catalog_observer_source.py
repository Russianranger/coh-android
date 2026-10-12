#!/usr/bin/env python3
"""Stage a NONSHIPPING native stock-parser/FX-ID observer after monorail.

It adds an observation after ordinary Parse6 acceptance and stock indexed-name
construction. No parser, comparison, reorder or gameplay algorithm is replaced.
The observer exits after FX only when its explicit output environment is present.
Its executable must never enter a release or normal runtime package.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import prepare_monorail_source as monorail
from prepare_runtime import require, sha256

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = 'server-fx-catalog-observer-build-input.json'
FX = 'Common/fxinfo.c'
PARSER = 'libs/UtilitiesLib/src/utils/textparser.c'
ENVIRONMENT = 'COH_HOST_ONLY_FX_IDS_OUTPUT'
OBSERVER = r'''
#ifdef SERVER
#include <utilitieslib/utils/wininclude.h>
/* Host-only observer. The ordinary stock parser and registry have completed. */
extern int cohHostOnlyFxBinaryAccepted;
static void cohHostOnlyFxObserve(void)
{
    char path[2048], line[2048];
    DWORD length, written;
    HANDLE file;
    int i, count, outer;
    length = GetEnvironmentVariableA("COH_HOST_ONLY_FX_IDS_OUTPUT", path, sizeof(path));
    if (!length) return;
    if (length >= sizeof(path)) exit(74);
    file = CreateFileA(path, GENERIC_WRITE, 0, NULL, CREATE_NEW, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) exit(75);
    count = numIndexedStringsInStringTable();
    outer = eaSize(&fx_infolist.fxinfos);
    if (count != 19606 || outer != 19607 || cohHostOnlyFxBinaryAccepted != 1) exit(76);
    sprintf_s(line, sizeof(line), "COH_FX_NATIVE_IDS_V1\t%d\t%d\t%08x\t%d\n",
              outer, count, ParseTableCRC(ParseFxInfoList, NULL), cohHostOnlyFxBinaryAccepted);
    length = (DWORD)strlen(line);
    if (!WriteFile(file, line, length, &written, NULL) || written != length) exit(77);
    for (i = 1; i <= count; ++i) {
        const char *name = stringFromReference(i);
        int reference;
        if (!name || strlen(name) > 1024 || strpbrk(name, "\t\r\n")) exit(78);
        reference = stringToReference(name);
        if (reference != i) exit(79);
        sprintf_s(line, sizeof(line), "%d\t%s\t%d\n", i, name, reference);
        length = (DWORD)strlen(line);
        if (!WriteFile(file, line, length, &written, NULL) || written != length) exit(77);
    }
    strcpy_s(line, sizeof(line), "COH_FX_NATIVE_DONE_V1\n");
    length = (DWORD)strlen(line);
    if (!WriteFile(file, line, length, &written, NULL) || written != length
        || !FlushFileBuffers(file) || !CloseHandle(file)) exit(77);
    printf("COH_HOST_ONLY_FX_IDS_COMPLETE_V1\n");
    exit(0);
}
#endif
'''


def observed_sources(root=ROOT):
    root = Path(root)
    original = {n: (root/'upstream/ouroboros'/n).read_bytes().replace(b'\r\n', b'\n') for n in (FX, PARSER)}
    fx = original[FX].decode('utf-8')
    anchor = 'void fxBuildFxStringHandles()\n'
    require(fx.count(anchor) == 1, 'FX observer definition anchor differs')
    fx = fx.replace(anchor, OBSERVER + '\n' + anchor)
    anchor = '    stringReorder();\n}'
    require(fx.count(anchor) == 1, 'FX stock reorder anchor differs')
    fx = fx.replace(anchor, '    stringReorder();\n#ifdef SERVER\n    cohHostOnlyFxObserve();\n#endif\n}')
    parser = original[PARSER].decode('utf-8')
    anchor = 'int ParserReadBinaryFile(SimpleBufHandle binfile,'
    require(parser.count(anchor) == 1, 'Native binary-reader anchor differs')
    parser = parser.replace(anchor, 'int cohHostOnlyFxBinaryAccepted = 0;\n\n' + anchor)
    begin = parser.index('int ParserReadBinaryFile(SimpleBufHandle binfile,')
    end = parser.index('///////////////////////////////////////////////////////////////////////////////// ParserLoadFiles', begin)
    function = parser[begin:end]
    anchor = '    SerializeClose(file);\n    return success;\n}'
    require(function.count(anchor) == 1, 'Native binary-reader completion anchor differs')
    function = function.replace(anchor, '    SerializeClose(file);\n'
        '    if (success && filename && !stricmp(filename, "bin/fxinfo.bin"))\n'
        '        ++cohHostOnlyFxBinaryAccepted;\n    return success;\n}')
    parser = parser[:begin] + function + parser[end:]
    return original, {FX: fx.encode('utf-8'), PARSER: parser.encode('utf-8')}


def expected(root=ROOT, base=None):
    original, output = observed_sources(root)
    base = monorail.expected_receipt(root) if base is None else base
    return {'format': 1, 'build_role': 'host_only_server_fx_catalog_observer',
        'source_commit': base['source_commit'], 'base_monorail': base,
        'source_sha256': {n: hashlib.sha256(raw).hexdigest() for n, raw in original.items()},
        'patched_sha256': {n: hashlib.sha256(raw).hexdigest() for n, raw in output.items()},
        'source_transform_sha256': sha256(Path(root)/'tools/prepare_server_fx_catalog_observer_source.py'),
        'contract': {'environment': ENVIRONMENT, 'after': 'stock_fxBuildFxStringHandles_stringReorder',
            'binary_acceptance': 'ordinary_Parse6_ReadBinaryFile_success_before_ID_observation',
            'indexed_names': 19606, 'outer_records': 19607, 'schema_crc': '4cb7d9cb',
            'native_id_roundtrips': True, 'early_exit_after_fx_observation': True,
            'shipping_executable': False, 'ship_observer_forbidden': True},
        'build_targets': ['MapServer'], 'runtime_validation': 'pending_native_ids_and_provider_proof'}


def prepare(output, root=ROOT, *, already_staged=False):
    output, root = Path(output).resolve(), Path(root).resolve()
    require(output != root and root/'upstream' not in (output, *output.parents), 'Immutable source mutation refused')
    if not already_staged:
        monorail.prepare(output, root)
    previous = json.loads((output/monorail.RECEIPT).read_text())
    require(previous == monorail.expected_receipt(root), 'Observer requires exact monorail ancestry')
    require(not (output/RECEIPT).exists(), 'Observer already staged')
    receipt = expected(root, previous); original, contents = observed_sources(root)
    for name, raw in original.items():
        require((output/name).read_bytes().replace(b'\r\n', b'\n') == raw, 'Observer source differs: ' + name)
    for name, raw in contents.items(): (output/name).write_bytes(raw)
    (output/RECEIPT).write_text(json.dumps(receipt, indent=2)+'\n')
    return receipt


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True); p.add_argument('--already-staged', action='store_true')
    receipt = prepare(**vars(p.parse_args()))
    print(json.dumps({'status': 'staged_host_only', 'contract': receipt['contract']}))
