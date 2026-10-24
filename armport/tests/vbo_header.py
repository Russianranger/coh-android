#!/usr/bin/env python3
"""Execute the original VBO queue header producer/consumer without OpenGL.

The original 64-bit producer overwrites its pointer when filling TexID. Reject
that pointer before dereferencing it in the negative control; the patched path
must preserve the pointer, allocation extent, texture IDs, triangles and verts.
"""
import argparse
from pathlib import Path
import subprocess
import tempfile


def harness(source):
    producer = (source / 'Game/src/render/model_cache.c').read_text()
    producer = producer[producer.index('    total = vert_total + tri_bytes'):]
    producer = producer[:producer.index('    idx = total - vert_total;')]
    consumer = (source / 'Game/src/render/thread/rt_model_cache.c').read_text()
    consumer = consumer[consumer.index('void createVboDirect(U8 *data)'):]
    consumer = consumer[:consumer.index('    if (!vbo->no_vbo)')]
    consumer = consumer.replace('void createVboDirect(U8 *data)', 'int consume(U8 *data, VBO *expected)')
    position = consumer.index('    tex_ids')
    consumer = consumer[:position] + '    if (vbo != expected) return 0;\n' + consumer[position:]
    return r'''
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
typedef uint8_t U8;
typedef uint32_t U32;
typedef float Vec3[3];
typedef struct { uint16_t id,count; } TexID;
typedef struct { int tex_count,tri_count; TexID *tex_ids; int *tris; } VBO;
typedef struct { int tex_count; } Model;
static int allocated;
#define DRAWCMD_CREATEVBO 1
static U8 *rdrQueueAlloc(int cmd,int n) { allocated=n; return calloc(1,n+16); }
static void modelGetTris(int *tris,Model *model) { tris[0]=3;tris[1]=7;tris[2]=11; }
''' + consumer + r'''
    int ok=vbo->tex_ids[0].id==6 && vbo->tex_ids[0].count==122 &&
           tris[0]==3 && tris[1]==7 && tris[2]==11 &&
           (*verts)[0]==1.25f && (*verts)[1]==2.5f && (*verts)[2]==5.0f;
    free(vbo->tex_ids);return ok;
}
int main(int argc,char **argv) {
    VBO *vbo=calloc(1,sizeof(VBO)); Model m={1},*model=&m;
    int vert_total=sizeof(Vec3),tri_bytes=3*sizeof(int),total; U8 *data;
    vbo->tex_count=1;vbo->tri_count=1;
''' + producer + r'''
    TexID tex={6,122}; Vec3 vertex={1.25f,2.5f,5.0f};
    memcpy(vbo->tex_ids,&tex,sizeof(tex));
    memcpy(data+total-vert_total,&vertex,sizeof(vertex));
    int allocation=allocated==sizeof(VBO*)+sizeof(TexID)+tri_bytes+vert_total;
    int payload=consume(data,vbo),want=atoi(argv[1]);
    printf("VBO header: pointer_bytes=%zu allocation=%d payload=%d expected=%d\n",
           sizeof(VBO*),allocation,payload,want);
    free(data);free(vbo);
    return allocation==want && payload==want ? 0:1;
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--expect-full-width', type=int, choices=(0, 1), required=True)
    parser.add_argument('--emit-windows', type=Path)
    args = parser.parse_args()
    code = harness(args.source)
    if args.emit_windows:
        args.emit_windows.write_text(code)
    with tempfile.TemporaryDirectory() as folder:
        c, exe = Path(folder) / 'vbo.c', Path(folder) / 'vbo'
        c.write_text(code)
        subprocess.run(['cc', '-std=c11', '-O2', '-fsanitize=address,undefined', str(c), '-o', str(exe)], check=True)
        subprocess.run([str(exe), str(args.expect_full_width)], check=True, timeout=15)


if __name__ == '__main__':
    main()
