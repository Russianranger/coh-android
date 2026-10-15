#!/usr/bin/env python3
"""Exercise the real native snapshot serializer without a renderer or GPU.

The exact Session declarations and snapshot implementation are extracted from
session_renderer.c. Only the JNI string-return operation and OpenGL scalar type
are mocked. This checks structured report integrity, bounded diagnostic capacity
and source directional names; it cannot qualify native Android execution.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


PREAMBLE = r'''
#include <pthread.h>
#include <stddef.h>
#include <stdarg.h>
#include <math.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "coh_world_scene.h"
#include "coh_scene.h"
#include "coh_character.h"
#include "coh_motion.h"
#include "coh_locomotion.h"
#include "coh_walk.h"
#include "coh_walkable_scene.h"
#include "session_stream_world.h"
typedef unsigned GLuint;
typedef intptr_t jlong;
typedef void *jclass;
typedef const char *jstring;
struct MockJNI;
typedef const struct MockJNI *JNIEnv;
struct MockJNI { jstring (*NewStringUTF)(JNIEnv *,const char *); };
#define JNIEXPORT
#define JNICALL
static char received[16384];
static jstring mock_string(JNIEnv *env,const char *text) {
    (void)env; size_t n=strlen(text);
    if(n>=sizeof received)abort();
    memcpy(received,text,n+1);return received;
}
'''

DRIVER = r'''
static void positive_controls(Session *s) {
    s->depth_diagnostics_count=DEPTH_DIAGNOSTICS;
    s->clear_control=(DepthDiagnostic){.world_depth=0xffffff,.actor_depth=0xffffff,.combined_depth=0xffffff};
    s->world_front_control=(DepthDiagnostic){.x=63,.y=31,.world_depth=107,.actor_depth=115,.combined_depth=107};
    s->actor_front_control=(DepthDiagnostic){.x=91,.y=17,.world_depth=1029,.actor_depth=1023,.combined_depth=1023};
    s->depth_sampler_controls_passed=1;s->depth_codec_float_precision=23;
    for(unsigned i=0;i<DEPTH_DIAGNOSTICS;i++) {
        DepthDiagnostic *d=&s->depth_diagnostics[i];
        d->x=i*17;d->y=i*19;d->world_depth=d->actor_depth=d->combined_depth=16700000u+i;
        for(unsigned k=0;k<4;k++){d->world[k]=255-k;d->actor[k]=i+k;d->forward[k]=71+k;d->reverse[k]=81+k;}
    }
}
int main(void) {
    const struct MockJNI methods={mock_string};JNIEnv env=&methods;
    puts(Java_org_coh_sessionclient_SessionNative_snapshot(&env,NULL,0));
    Session s={0};if(pthread_mutex_init(&s.mutex,NULL))return 2;
    s.valid=1;s.frames=2237;s.walking_ticks=901;s.walking_grounded_ticks=900;
    s.walking_blocked_ticks=41;s.walking_slide_ticks=17;s.walking_bounded_ticks=2;
    s.walking.grounded=1;s.walking.collision_queries=23951;s.walking.triangle_tests=82391;
    s.walk_world.triangle_count=276;s.walking.contact_hits=352;s.walking.wall_hits=42;s.walking.ground_hits=310;
    s.walkable_draws=12123;s.walkable_tf_components=2600;s.walkable_visible_pixels=15700;
    s.motion.position[0]=31.25f;s.motion.position[1]=12.5f;s.motion.position[2]=-21.75f;
    s.walkable.spawn_yaw=.5f;s.obstacle_min[0]=1;s.obstacle_max[2]=9;
    s.stream_stats=(CohSessionWorldStats){.catalog_instances=11,.selected_instances=6,.resident_bytes=12345,.budget_bytes=524288,
        .peak_resident_bytes=20000,.selection_updates=3,.cache_hits=41,.cache_misses=8,.evictions=2,
        .generation=3,.draws=120,.view_radius=24,.geo_loads=3,.texture_loads=6,.errors=0,
        .draw_packets=120,.tf_components=6144,.tf_mismatches=0,.visible_pixels=41000,.material_mode_mask=3,
        .owned_cpu_bytes=462508,.gpu_bytes=902144,.tf_max_error=.000001f};
    s.animation.move=COH_LOCOMOTION_RIGHT;
    for(unsigned i=0;i<COH_LOCOMOTION_CLIPS;i++)s.animation_move_samples[i]=1000u+i*13u;
    snprintf(s.failure,sizeof s.failure,"Test quoted \"failure\" \\ path\nline");
    snprintf(s.gl_renderer,sizeof s.gl_renderer,"Test \"renderer\" \\ slash");
    positive_controls(&s);
    puts(Java_org_coh_sessionclient_SessionNative_snapshot(&env,NULL,(jlong)(intptr_t)&s));
    /* Maximum bounded diagnostics, counters and escaped driver strings must
     * remain parseable even during failure-report export. */
    s.failed=1;s.frames=UINT64_MAX;s.walking_ticks=UINT64_MAX;
    s.walking_grounded_ticks=s.walking_blocked_ticks=s.walking_slide_ticks=s.walking_bounded_ticks=UINT64_MAX;
    s.walkable_draws=s.walkable_tf_components=s.walkable_tf_mismatches=s.walkable_visible_pixels=UINT64_MAX;
    s.walking.collision_queries=s.walking.triangle_tests=s.walking.contact_hits=s.walking.wall_hits=s.walking.ground_hits=UINT32_MAX;
    s.stream_stats.catalog_instances=s.stream_stats.selected_instances=s.stream_stats.resident_bytes=UINT64_MAX;
    s.stream_stats.budget_bytes=s.stream_stats.peak_resident_bytes=s.stream_stats.selection_updates=UINT64_MAX;
    s.stream_stats.cache_hits=s.stream_stats.cache_misses=s.stream_stats.evictions=s.stream_stats.draws=UINT64_MAX;
    s.stream_stats.geo_loads=s.stream_stats.texture_loads=s.stream_stats.errors=s.stream_stats.draw_packets=UINT64_MAX;
    s.stream_stats.tf_components=s.stream_stats.tf_mismatches=s.stream_stats.visible_pixels=UINT64_MAX;
    s.stream_stats.owned_cpu_bytes=s.stream_stats.gpu_bytes=UINT64_MAX;
    s.stream_stats.generation=s.stream_stats.material_mode_mask=UINT32_MAX;
    s.stream_stats.tf_max_error=s.stream_stats.view_radius=3.402823466e38f;
    memset(s.failure,255,sizeof s.failure-1);s.failure[sizeof s.failure-1]=0;
    memset(s.gl_renderer,255,sizeof s.gl_renderer-1);s.gl_renderer[sizeof s.gl_renderer-1]=0;
    for(unsigned i=0;i<COH_LOCOMOTION_CLIPS;i++)s.animation_move_samples[i]=UINT64_MAX;
    for(unsigned i=0;i<DEPTH_DIAGNOSTICS;i++) {
        DepthDiagnostic *d=&s.depth_diagnostics[i];d->x=d->y=d->world_depth=d->actor_depth=d->combined_depth=UINT32_MAX;
        memset(d->world,255,4);memset(d->actor,255,4);memset(d->forward,255,4);memset(d->reverse,255,4);
    }
    puts(Java_org_coh_sessionclient_SessionNative_snapshot(&env,NULL,(jlong)(intptr_t)&s));
    pthread_mutex_destroy(&s.mutex);return 0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compiler', default=os.environ.get('CC', 'cc'))
    args = parser.parse_args()
    core = Path(__file__).resolve().parents[2]
    renderer = core / 'session-client/app/src/main/cpp/session_renderer.c'
    raw = renderer.read_bytes()
    source = raw.decode()
    declarations = source[source.index('#define MAX_ASSET'):source.index('typedef struct { GLuint id;')]
    snapshot = source[source.index('static void escaped('):source.index('JNIEXPORT void JNICALL Java_org_coh_sessionclient_SessionNative_destroy(')]
    extracted = PREAMBLE + declarations + snapshot + DRIVER
    compiler = shlex.split(args.compiler)
    include_paths = [core / 'world-probe/app/src/main/cpp',
                     core / 'character-probe/app/src/main/cpp',
                     core / 'material-probe/app/src/main/cpp',
                     core / 'session-client/app/src/main/cpp', core / 'world', core / 'animation', core / 'character',
                     core / 'motion', core / 'locomotion', core / 'walk', core / 'walkable']
    with tempfile.TemporaryDirectory(prefix='coh-snapshot-') as directory:
        code = Path(directory) / 'snapshot.c'
        executable = Path(directory) / 'snapshot'
        code.write_text(extracted)
        flags = ['-std=c11', '-O1', '-Wall', '-Wextra', '-Werror',
                 '-Wno-misleading-indentation', '-ffunction-sections', '-fdata-sections',
                 '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                 '-ffp-contract=off', '-fno-fast-math', '-Wl,--gc-sections']
        for path in include_paths:
            flags += ['-I', str(path)]
        subprocess.run([*compiler, *flags, str(code), str(core / 'locomotion/coh_locomotion.c'),
                        '-lpthread', '-lm', '-o', str(executable)], check=True)
        environment = dict(os.environ)
        # LeakSanitizer cannot inspect process threads in some task runners.
        # The bounded stack serializer owns no allocations; keep address and
        # undefined-behavior checking active without claiming leak coverage.
        environment['ASAN_OPTIONS'] = 'detect_leaks=0:halt_on_error=1'
        lines = subprocess.check_output([str(executable)], text=True, env=environment).splitlines()
    assert len(lines) == 3
    empty, normal, maximum = [json.loads(line) for line in lines]
    assert empty == {'valid': False}
    assert normal['valid'] is True and normal['failed'] is False
    assert normal['collision'] is True and normal['live_server'] is False
    assert normal['full_atlas'] is False and normal['gpu_palette_skinning'] is False
    assert normal['frames'] == 2237 and normal['movement_ticks'] == 901
    assert normal['failure'] == 'Test quoted "failure" \\ path\nline'
    assert normal['gl_renderer'] == 'Test "renderer" \\ slash'
    assert normal['actor_position'] == [31.25, 12.5, -21.75]
    assert normal['walk'] == {
        'grounded': True, 'ground_y': 12.5, 'ground_hits': 900, 'blocked_ticks': 41,
        'sliding_ticks': 17, 'bounded_ticks': 2, 'collision_queries': 23951,
        'triangle_tests': 82391, 'triangles': 276, 'bounded_scene': True,
        'spawn_yaw': .5, 'obstacle_bounds_min': [1, 0, 0], 'obstacle_bounds_max': [0, 0, 9]}
    assert normal['stream'] == {'catalog_instances':11,'selected_instances':6,'resident_bytes':12345,
        'budget_bytes':524288,'peak_resident_bytes':20000,'selection_updates':3,'cache_hits':41,
        'cache_misses':8,'evictions':2,'generation':3,'draws':120,'view_radius':24}
    assert normal['source_assets'] == {'geo_loads':3,'texture_loads':6,'errors':0}
    assert normal['static_renderer']['tf_components'] == 6144
    assert normal['static_renderer']['tf_mismatches'] == 0
    assert normal['static_renderer']['visible_pixels'] == 41000
    assert normal['static_renderer']['material_mode_mask'] == 3
    assert normal['static_renderer']['owned_cpu_bytes'] == 462508
    assert normal['static_renderer']['gpu_bytes'] == 902144
    assert abs(normal['static_renderer']['tf_max_error']-1e-6) < 1e-12
    assert maximum['stream']['draws'] == maximum['source_assets']['texture_loads'] == (1<<64)-1
    assert maximum['static_renderer']['owned_cpu_bytes'] == (1<<64)-1
    assert maximum['stream']['generation'] == maximum['static_renderer']['material_mode_mask'] == (1<<32)-1
    assert normal['walk_contact_hits'] == 352 and normal['walk_wall_hits'] == 42 and normal['walk_ground_hits'] == 310
    assert normal['walkable_tf_components'] == 2600 and normal['walkable_tf_mismatches'] == 0
    assert normal['walkable_visible_pixels'] == 15700 and normal['walkable_draws'] == 12123
    assert normal['animation_move_samples'] == [1000 + i*13 for i in range(12)]
    assert normal['animation_move'] == 'Run_Right_Cycle'
    assert normal['depth_sampler_controls_passed'] is True
    controls = normal['depth_sampler_controls']
    assert controls['clear']['world_depth'] == controls['clear']['actor_depth'] == controls['clear']['combined_depth'] == 16777215
    assert controls['world_front']['world_depth'] < controls['world_front']['actor_depth']
    assert controls['world_front']['combined_depth'] == controls['world_front']['world_depth']
    assert controls['actor_front']['actor_depth'] < controls['actor_front']['world_depth']
    assert controls['actor_front']['combined_depth'] == controls['actor_front']['actor_depth']
    assert len(normal['depth_tie_diagnostics']) == len(maximum['depth_tie_diagnostics']) == 16
    for i, diagnostic in enumerate(normal['depth_tie_diagnostics']):
        assert diagnostic['x'] == i*17 and diagnostic['y'] == i*19
        assert diagnostic['world_depth'] == diagnostic['actor_depth'] == diagnostic['combined_depth'] == 16700000+i
        assert diagnostic['world_rgba'] == [255-k for k in range(4)]
        assert diagnostic['actor_rgba'] == [i+k for k in range(4)]
    assert maximum['valid'] is True and maximum['failed'] is True
    assert maximum['frames'] == maximum['movement_ticks'] == (1 << 64)-1
    assert maximum['animation_move_samples'] == [(1 << 64)-1]*12
    assert maximum['walk']['collision_queries'] == (1 << 32)-1
    for diagnostic in maximum['depth_tie_diagnostics']:
        assert all(diagnostic[k] == (1 << 32)-1 for k in ['x', 'y', 'world_depth', 'actor_depth', 'combined_depth'])
        assert all(diagnostic[k] == [255]*4 for k in ['world_rgba', 'actor_rgba', 'forward_rgba', 'reverse_rgba'])
    assert max(map(len, lines)) < 16384
    receipt = {
        'schema': 'coh-native-session-snapshot-host-v1', 'passed': True,
        'scope': 'Exact source native snapshot serialization, mock JNI string return, no Android or renderer execution',
        'renderer_source_sha256': hashlib.sha256(raw).hexdigest(),
        'extracted_serializer_sha256': hashlib.sha256(snapshot.encode()).hexdigest(),
        'host_harness_sha256': hashlib.sha256(extracted.encode()).hexdigest(),
        'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'json_cases': 3, 'directional_clip_counters': 12, 'maximum_depth_diagnostics': 16,
        'maximum_snapshot_bytes': max(map(len, lines)), 'snapshot_capacity_bytes': 16384,
        'quoted_backslash_newline_fields_verified': True,
        'walk_and_authored_scene_counters_verified': True, 'indexed_world_and_asset_renderer_counters_verified': True,
        'uint64_max_counter_preserved': True, 'positive_control_values_preserved': True,
        'address_and_undefined_sanitizers_passed': True,
        'leak_sanitizer_executed': False,
        'gpu_executed': False, 'native_android_execution_verified': False,
        'physical_device_qualified': False,
        'compiler': subprocess.check_output([*compiler, '--version'], text=True).splitlines()[0],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
