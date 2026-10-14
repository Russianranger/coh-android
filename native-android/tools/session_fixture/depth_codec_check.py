#!/usr/bin/env python3
"""Check only the float32 DEPTH24 diagnostic codec and its control policy.

This host check cannot qualify an actual GPU sampler, its texture binding, or
the source renderer. The Android receipt separately requires measured clear,
world-front and actor-front samples before accepting exact equal-depth ties.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shlex
import subprocess
import tempfile

SOURCE = r'''
#include <float.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#define FAR_DEPTH 16777215u
typedef struct { uint32_t world,actor,combined; } Depth;
static uint32_t unpack_float32(uint32_t encoded) {
    float normalized=(float)encoded/(float)FAR_DEPTH;
    float scaled=normalized*(float)FAR_DEPTH;
    return (uint32_t)roundf(scaled);
}
static int controls(Depth clear,Depth world_front,Depth actor_front) {
    return clear.world==FAR_DEPTH&&clear.actor==FAR_DEPTH&&clear.combined==FAR_DEPTH&&
        world_front.world<world_front.actor&&world_front.actor<FAR_DEPTH&&
        world_front.combined==world_front.world&&
        actor_front.actor<actor_front.world&&actor_front.world<FAR_DEPTH&&
        actor_front.combined==actor_front.actor;
}
static int exact_tie(Depth sample) {
    return sample.world<FAR_DEPTH&&sample.world==sample.actor&&
        sample.world==sample.combined;
}
int main(void) {
    if(sizeof(float)!=4||FLT_RADIX!=2||FLT_MANT_DIG!=24)return 2;
    uint32_t mismatches=0,channels=0,policy_checks=0;
    for(uint32_t depth=0;depth<=FAR_DEPTH;depth++) {
        uint32_t unpacked=unpack_float32(depth);
        /* Exactly the shader's uint-to-three-byte representation. */
        uint8_t rgba[4]={(uint8_t)unpacked,(uint8_t)(unpacked>>8),
            (uint8_t)(unpacked>>16),255};
        uint32_t joined=(uint32_t)rgba[0]|(uint32_t)rgba[1]<<8|(uint32_t)rgba[2]<<16;
        if(depth!=joined)mismatches++;
    }
    for(uint32_t byte=0;byte<256;byte++) {
        float normalized=(float)byte/255.f;
        if((uint32_t)roundf(normalized*255.f)!=byte)channels++;
    }
    const Depth clear={FAR_DEPTH,FAR_DEPTH,FAR_DEPTH};
    const Depth world_front={16744001u,16744531u,16744001u};
    const Depth actor_front={16745539u,16745317u,16745317u};
    if(!controls(clear,world_front,actor_front))return 3;policy_checks++;
    const uint32_t constants[3]={0u,123456u,FAR_DEPTH};
    for(unsigned i=0;i<3;i++) {
        Depth constant={constants[i],constants[i],constants[i]};
        if(controls(constant,constant,constant))return 4;policy_checks++;
    }
    Depth disconnected_world=world_front;disconnected_world.combined++;
    if(controls(clear,disconnected_world,actor_front))return 5;policy_checks++;
    Depth disconnected_actor=actor_front;disconnected_actor.combined=world_front.combined;
    if(controls(clear,world_front,disconnected_actor))return 6;policy_checks++;
    const Depth tied={16744001u,16744001u,16744001u};
    const Depth one_bin_apart={16744001u,16744002u,16744001u};
    const Depth wrong_combined={16744001u,16744001u,16744002u};
    if(!exact_tie(tied)||exact_tie(one_bin_apart)||exact_tie(wrong_combined)||exact_tie(clear))return 7;
    policy_checks+=4;
    printf("{\"passed\":%s,\"float32_depth_bins\":16777216,"
        "\"roundtrip_mismatches\":%u,\"rgba8_channel_bins\":256,"
        "\"channel_mismatches\":%u,\"control_policy_checks\":%u}",
        !mismatches&&!channels?"true":"false",mismatches,channels,policy_checks);
    return mismatches||channels?8:0;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compiler', default=os.environ.get('CC', 'cc'))
    args = parser.parse_args()
    compiler = shlex.split(args.compiler)
    with tempfile.TemporaryDirectory(prefix='coh-depth-codec-') as directory:
        source = Path(directory) / 'codec.c'
        executable = Path(directory) / 'codec'
        source.write_text(SOURCE)
        subprocess.run([
            *compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
            '-Wno-misleading-indentation', '-ffp-contract=off', '-fno-fast-math',
            str(source), '-lm', '-o', str(executable),
        ], check=True)
        result = json.loads(subprocess.check_output([str(executable)], text=True))
    result.update({
        'schema': 'coh-host-depth24-diagnostic-codec-v1',
        'scope': 'host float32 diagnostic packing and explicit acceptance policy only',
        'gpu_executed': False,
        'source_renderer_qualified': False,
        'actual_sampler_binding_qualified': False,
        'actual_gpu_positive_controls_required': True,
        'exact_integer_tie_required': True,
        'color_tolerance_changed': False,
        'compiler': subprocess.check_output([*compiler, '--version'], text=True).splitlines()[0],
        'c_source_sha256': hashlib.sha256(SOURCE.encode()).hexdigest(),
        'checker_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
