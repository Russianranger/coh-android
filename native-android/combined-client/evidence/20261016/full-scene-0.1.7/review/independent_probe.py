#!/usr/bin/env python3
"""Independent adversarial API review; synthetic inputs, not an original oracle.

Run against the integrated repository with --source-root. Exact production file
hashes and compiler/stack evidence bind the result to the source under review.
"""
import argparse, hashlib, json, os, struct, subprocess, tempfile
from pathlib import Path


class Writer:
    def __init__(self, aligned):
        self.aligned = aligned
        self.fields = []

    def u(self, width, value):
        self.fields.extend((value >> bit) & 1 for bit in range(((width + 7) & ~7) if self.aligned else width))
        return self

    def p(self, value, width=1):
        if self.aligned:
            return self.u(32, value)
        while width < 32 and value >= (1 << width) - 1:
            maximum = (1 << width) - 1
            self.u(width, maximum)
            value -= maximum
            width = min(32, width * 2)
        return self.u(width, value)

    def s(self, value):
        for byte in value.encode() + b'\0':
            self.u(8, byte)
        return self

    def f(self, value):
        return self.u(32, struct.unpack('<I', struct.pack('<f', value))[0])

    def raw(self, values=None):
        self.u(1, 0)
        for value in (values if values is not None else [1, 0, 0, 0, 1, 0, 0, 0, 1, 4, -5, 6]):
            self.f(value)
        return self

    def identity(self):
        return self.u(1, 1).u(1, 0).u(1, 0).u(1, 0)

    def data(self):
        data = bytearray((len(self.fields) + 7) // 8)
        for bit, value in enumerate(self.fields):
            data[bit // 8] |= value << (bit % 8)
        return data


def prefix(w, files=0):
    return w.p(0).p(0).u(1, 0).u(1, 1).p(files)


def footer(w, files=0, active=0):
    return w.p(0xffffffff).p(files).p(active).u(32, 0x12345678).u(32, 0x89abcdef)


def minimal_def(w, ident=1, children=None):
    w.p(ident).u(1, 1).s('root').u(32, 0).p(1 if children else 0)
    if children:
        w.s('forward_child')
        children(w)
    return w.u(1, 0).u(1, 0).u(1, 0).u(1, 0).u(1, 0).p(0).u(1, 0).u(1, 0)


def normal_file(w):
    return w.u(1, 1).s('maps/test.txt').u(32, 0).u(1, 0)


def to_tricks(w):
    w.p(1).u(1, 1).s('root').u(32, 0).p(0)
    w.u(1, 0).u(1, 0).u(1, 0).u(1, 0).u(1, 1)
    w.s('').u(1, 0)
    for _ in range(8):
        w.u(1, 0)  # light, ambient, cube, sound, fog, volume, beacon, tint
    return w


def fixtures():
    rows = []

    def add(name, w, status, good=False):
        rows.append((name, w, status, good))

    for mode in (0, 1):
        w = footer(prefix(Writer(mode)))
        add('empty-' + str(mode), w, 0, True)
        w = normal_file(prefix(Writer(mode), 1))
        minimal_def(w, 65536, lambda v: v.identity())
        w.p(0).p(1048575).s('root').raw()
        footer(w, 1, 19)  # Active count deliberately differs from update count.
        add('sparse-boundaries-' + str(mode), w, 0, True)
        for badid, expected in [(65537, 4), (0x80000000, 1), (0xffffffff, 1)]:
            w = normal_file(prefix(Writer(mode), 1)).p(badid)
            add('bad-def-id-%d-%d' % (mode, badid), w, expected)
        for badroot, expected in [(1048576, 4), (0x80000000, 1), (0xfffffffe, 1)]:
            w = prefix(Writer(mode)).p(badroot)
            add('bad-root-id-%d-%d' % (mode, badroot), w, expected)
        w = normal_file(prefix(Writer(mode), 1)).p(2).u(1, 0).p(2)
        add('duplicate-def-' + str(mode), w, 1)
        w = prefix(Writer(mode)).p(2).s('').p(1)
        add('descending-root-' + str(mode), w, 1)
        w = footer(prefix(Writer(mode), 0), 1)
        add('wrong-file-count-' + str(mode), w, 1)
        w = prefix(Writer(mode), 1025)
        add('file-count-limit-' + str(mode), w, 4)
        w = prefix(Writer(mode), 1).u(1, 1).s('base').u(32, 0).u(1, 1)
        add('base-unsupported-' + str(mode), w, 2)
        w = normal_file(prefix(Writer(mode), 1)).p(1).u(1, 1).s('def').u(32, 0).p(0xffffffff)
        add('children-limit-' + str(mode), w, 4)
        w = to_tricks(normal_file(prefix(Writer(mode), 1))).p(4)
        add('unknown-texture-mask-' + str(mode), w, 2)
        w = to_tricks(normal_file(prefix(Writer(mode), 1))).p(0).u(1, 0).p(1).u(32, 0xffffffff)
        add('property-count-limit-' + str(mode), w, 4)
        w = to_tricks(normal_file(prefix(Writer(mode), 1))).p(0).u(1, 0).p(2)
        add('has-properties-highbits-' + str(mode), w, 1)
        w = to_tricks(normal_file(prefix(Writer(mode), 1))).p(0).u(1, 0).p(1).u(32, 1).s('n' * 64)
        add('property-name-overlimit-' + str(mode), w, 4)
        w = to_tricks(normal_file(prefix(Writer(mode), 1))).p(0).u(1, 0).p(1).u(32, 1).s('n').s('v' * 4096)
        add('property-value-overlimit-' + str(mode), w, 4)
        w = to_tricks(normal_file(prefix(Writer(mode), 1))).p(0).u(1, 0).p(1).u(32, 1).s('n' * 63).s('v' * 4095).u(1, 1)
        w.p(0).u(1, 0).u(1, 0).p(0)
        footer(w, 1)
        add('property-string-boundaries-' + str(mode), w, 0)
        w = normal_file(prefix(Writer(mode), 1))
        minimal_def(w, 1, lambda v: v.raw([float('inf')] + [0] * 11))
        add('nonfinite-matrix-' + str(mode), w, 1)
        w = footer(prefix(Writer(mode))).u(8, 0)
        add('extra-zero-byte-' + str(mode), w, 2)
        w = footer(prefix(Writer(mode))).u(1, 1)
        add('extra-one-' + str(mode), w, 2)
    # Byte-aligned original scalar writes zero unused bits. These cannot
    # authorize an unrecognized variant by carrying high flag bits.
    add('rounded-boolean-highbits', Writer(1).p(0).p(0).u(1, 2), 1)
    return rows


HARNESS = r'''
#include "coh_groups.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned measuring, allocations, checks, cases, truncations;
void *__real_malloc(size_t); void *__real_calloc(size_t,size_t);
void *__real_realloc(void*,size_t); void __real_free(void*);
void *__wrap_malloc(size_t n){if(measuring)allocations++;return __real_malloc(n);}
void *__wrap_calloc(size_t n,size_t z){if(measuring)allocations++;return __real_calloc(n,z);}
void *__wrap_realloc(void*p,size_t n){if(measuring)allocations++;return __real_realloc(p,n);}
void __wrap_free(void*p){if(measuring)allocations++;__real_free(p);}
static void check(int yes,const char *what,const char *name){checks++;if(!yes){fprintf(stderr,"%s: %s\n",name,what);exit(1);}}
static void test(const unsigned char *data,size_t bytes,size_t bits,int mode,int expected,const char *name) {
 CohRepReader r; CohGroupsInspection out, before; CohGroupsFailure failure;
 check(coh_rep_reader_bounded(&r,(CohBytes){data,bytes},bits,mode,COH_REP_BOUNDED_MESSAGE_MAX)==COH_OK,"reader",name);
 CohRepReader original=r;memset(&out,0x5a,sizeof(out));before=out;memset(&failure,0x7f,sizeof(failure));
 allocations=0;measuring=1;CohStatus status=coh_rep_groups(&r,&out,&failure);measuring=0;cases++;
 check((expected<0 ? status!=COH_OK : status==(CohStatus)expected),"status",name);
 check(!allocations,"no allocation/free inside parser",name);
 if(status!=COH_OK) {
  check(!memcmp(&r,&original,sizeof(r)),"reader rollback",name);
  check(!memcmp(&out,&before,sizeof(out)),"inspection rollback",name);
  check(failure.status==status,"failure status",name);
  check(failure.stage>=COH_GROUPS_STAGE_NONE&&failure.stage<=COH_GROUPS_STAGE_END,"stage bounded",name);
  check(failure.bit_offset<=bits,"offset bounded",name);
 } else {
  check(r.cursor==bits&&out.consumed_bits==bits,"exact end",name);
  check(!failure.stage&&!failure.status&&!failure.bit_offset,"failure clear",name);
  check(out.work_units<=COH_GROUPS_WORK_MAX&&out.string_bytes<=COH_GROUPS_STRING_BYTES_MAX,"counters bounded",name);
 }
}
@CASES@
int main(void) {
 for(size_t i=0;i<sizeof(fixtures)/sizeof(fixtures[0]);i++) {
  const Fixture *f=&fixtures[i];test(f->data,f->bytes,f->bits,f->mode,f->expected,f->name);
  if(f->good)for(size_t n=0;n<f->bits;n++){test(f->data,f->bytes,n,f->mode,-1,f->name);truncations++;}
 }
 printf("{\"passed\":true,\"assertions\":%u,\"cases\":%u,\"truncations\":%u,\"parser_allocation_calls\":0}\n",checks,cases,truncations);
 return 0;
}
'''


def run(argv, **kwargs):
    p = subprocess.run(argv, text=True, capture_output=True, **kwargs)
    if p.returncode:
        raise RuntimeError(repr(argv) + '\n' + p.stdout + p.stderr)
    return p.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    root = args.source_root.resolve()
    module = root / 'native-android/engine/replication'
    rows = fixtures()
    arrays, table = [], []
    for i, (name, w, status, good) in enumerate(rows):
        arrays.append('static const unsigned char d%d[]={%s};' % (i, ','.join(map(str, w.data()))))
        table.append('{d%d,sizeof(d%d),%du,%d,%d,%d,%s}' % (i, i, len(w.fields), w.aligned, status, good, json.dumps(name)))
    code = '\n'.join(arrays) + '\ntypedef struct {const unsigned char *data;size_t bytes,bits;int mode,expected,good;const char*name;} Fixture;\nstatic const Fixture fixtures[]={' + ',\n'.join(table) + '};\n'
    proof = {'schema': 1, 'scope': 'independent synthetic adversarial parser/API review; not original producer oracle, server capture, authenticated session, or device acceptance', 'source_sha256': {name: hashlib.sha256((module/name).read_bytes()).hexdigest() for name in ['coh_groups.h', 'coh_groups.c', 'coh_replication.h', 'coh_replication.c']}, 'checks': {}}
    with tempfile.TemporaryDirectory(prefix='coh-groups-review-') as tmp:
        directory = Path(tmp)
        harness = directory / 'review.c'
        harness.write_text(HARNESS.replace('@CASES@', code))
        common = ['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic', '-I' + str(module)]
        for name, flags in [('release', ['-O2']), ('asan', ['-O1', '-g', '-fno-omit-frame-pointer', '-fsanitize=address', '-no-pie']), ('ubsan', ['-O1', '-g', '-fno-omit-frame-pointer', '-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
            binary = directory / name
            run(common + flags + [str(module/'coh_groups.c'), str(module/'coh_replication.c'), str(harness), '-Wl,--wrap=malloc,--wrap=calloc,--wrap=realloc,--wrap=free', '-lm', '-o', str(binary)])
            env = os.environ.copy()
            env['ASAN_OPTIONS'] = 'detect_leaks=0:halt_on_error=1'
            env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
            proof['checks'][name] = json.loads(run([str(binary)], env=env))
        obj = directory/'groups.o'
        run(common + ['-O2', '-fstack-usage', '-c', str(module/'coh_groups.c'), '-o', str(obj)])
        proof['undefined_symbols'] = run(['nm', '-u', str(obj)]).strip().splitlines()
        proof['stack_usage'] = (directory/'groups.su').read_text().strip().splitlines()
    proof['passed'] = True
    args.output.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
