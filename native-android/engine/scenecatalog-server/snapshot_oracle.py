"""Original sendDef/sendMat4 with bounded test-owned runtime objects only."""
import hashlib
import importlib.util
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent


def prepare(root, directory):
    spec = importlib.util.spec_from_file_location('snapshot_groups_oracle',
        root / 'native-android/engine/replication/groups_oracle.py')
    oracle = importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)
    sources, pins = oracle.sources_and_pins(root)
    import json
    assert pins == json.loads((root / 'native-android/engine/replication/groups-source-pins.json').read_text())
    oracle.compile_oracle(root, directory, sources)
    path = directory / 'groups-original.c'
    code = path.read_text()
    group = oracle.read_source(root, 'Common/group/group.h')
    group_sha = hashlib.sha256(group.encode()).hexdigest()
    if group_sha != '17e9d423ef7f8e389f9ce39dc6d7f601d9aee500a7a617f0caa8bc049e994a48':
        raise ValueError('Original GroupBounds definition changed')
    bounds = group[group.index('#define GroupBoundsMembers'):group.index('typedef struct GroupBounds {')]
    code = code.replace('struct GroupDef {', 'typedef struct GroupFile GroupFile;\n' + bounds +
        '\ntypedef struct { GroupBoundsMembers } GroupBounds;\nstruct GroupDef {\n GroupBoundsMembers\n')
    replacements = {
        'F32 lod_scale,lod_near,lod_far,lod_nearfade,lod_farfade;': 'F32 lod_near,lod_far,lod_nearfade,lod_farfade;',
        'int lod_fadenode,no_fog_clip,no_coll,child_parent_fade,parent_fade;': 'int lod_fadenode,child_parent_fade,parent_fade;',
        'int child_light,child_ambient,child_volume,child_beacon,open_tracker,child_no_fog_clip;': '',
        'F32 sound_radius,shadow_dist;': 'F32 sound_radius;',
        'int has_light,has_cubemap,has_ambient,lib_ungroupable,has_sound,has_volume,has_fog,has_beacon;': 'int lib_ungroupable,has_sound;',
        'int has_tint_color,has_tex,has_properties,has_alpha;': 'int has_tint_color,has_tex,has_alpha;',
        'int hideForGameplay,file_idx,saved;': 'int hideForGameplay,file_idx,saved,pre_alloc; GroupFile *file;',
        'typedef struct {char *fullname;U32 bounds_checksum,mod_time;Base *base;int count,force_reload,modified_on_disk;GroupDef **defs;} GroupFile;':
        'struct GroupFile {char *fullname;U32 bounds_checksum,mod_time;Base *base;int count,force_reload,modified_on_disk,pre_alloc;GroupDef **defs;};',
        'static struct {int file_count,ref_count;GroupFile **files;DefTracker **refs;char *loadscreen;} group_info;':
        'static struct OracleGroupInfo {int file_count,ref_count;GroupFile **files;DefTracker **refs;char *loadscreen;GroupFile *pre_alloc;} group_info;\nstatic struct OracleGroupInfo *group_ptr=&group_info;',
    }
    for before, after in replacements.items():
        assert code.count(before) == 1, before
        code = code.replace(before, after)
    # Legacy original bit-packing is independently qualified at O0; do not
    # reclassify its known signed-shift behavior as new producer UB. Bodies stay
    # byte-identical. Newly added source_snapshot.inc remains fully instrumented.
    for path_name, names in oracle.SOURCE_FUNCTIONS.items():
        for name in names:
            original = oracle.extract(sources[path_name], name)
            assert code.count(original) == 1
            code = code.replace(original, '__attribute__((no_sanitize("undefined")))\n' + original)
    code += '\n' + (HERE / 'test_snapshot.c').read_text()
    path.write_text(code)
    return path, {'original_source': pins, 'original_group_header_sha256_lf': group_sha,
        'original_bounds_macro_sha256': hashlib.sha256(bounds.encode()).hexdigest(),
        'fixture_shim_extended': True, 'original_function_bodies_unchanged': True,
        'legacy_original_ubsan_instrumentation': False, 'actual_snapshot_include_sanitized': True}


def run(command, **kwargs):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=120, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result
