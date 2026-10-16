#!/usr/bin/env python3
"""Pinned original-source explanation of seven catalog misses; no replacement definitions."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import check as catalog

PINS = {
    'native-android/engine/scenecatalog/source_export.inc': 'ab5690d6be457ee90aa468781709891f770eb55cee894c3c0546602fb26e739b',
    'upstream/ouroboros/Common/group/groupfileload.c': '5fc2891ed78626b9fa38b181fd5fc975b69f000bf2f79bbb3c5527c86503e8d7',
    'upstream/ouroboros/Common/group/group.c': 'dc7c70b59b565a0a358fbedfba291e6018805efa6442d0ad0419e52f3908f7d7',
    'upstream/ouroboros/Common/group/groupfilelib.c': '07abf29638a3b3400f97f9caffdfd36f95c2db38c60063573b8cf67d10e1c5e8',
    'upstream/ouroboros/Game/src/group/groupnetrecv.c': 'f4cccb5a51acea3448191965470eaa349034c4f6fa1c729fa52aed0888c7004d',
    'upstream/i24/data/object_library/Villain_Lairs/cot/elements/magicrunes/magicrunes.txt': 'a226d1faa949633b92e50f297b585e0e676f7b0d944d42f7b091ca9e7852a062',
    'upstream/i24/data/object_library/Villain_Lairs/cot/elements/magicrunes/magicrunes.rootnames': '744563122e9edc74c0add3d154e622cab8531e5d00b170e5930976a1e73da51a',
    'upstream/i24/data/object_library/Villain_Lairs/unique/mother_mayhem/mmayhem_details/mmayhem_details.txt': '93416b392a2aba9a7f055b9d17a09aeb5de4de3a3a5710eb7d99fe5827fa5e9f',
    'upstream/i24/data/object_library/Villain_Lairs/unique/mother_mayhem/mmayhem_details/mmayhem_details.rootnames': '7c13eefc934e82ab9a296d5d2bd9670a91f55f198d5017bfb704ef45fd8cdbc5',
}
ROWS = [(110,61,1,'_cot_warpgate_base'),(110,61,2,'_cot_warpgate_glow'),
        (376,32,1,'_mmayhem_curtain_8_01c'),(376,33,1,'_mmayhem_curtain_8_02c'),
        (376,34,1,'_mmayhem_curtain_8_03c'),(376,35,1,'_mmayhem_curtain_16_01c'),
        (376,36,1,'_mmayhem_curtain_16_02c')]


def body(source, signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 0
    for at in range(opening, len(source)):
        if source[at] == '{': depth += 1
        elif source[at] == '}':
            depth -= 1
            if not depth: return source[start:at+1]
    raise ValueError('Incomplete pinned function')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists(): raise ValueError('New output required')
    text = {}
    for path, sha in PINS.items():
        raw = (a.source_root/path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha: raise ValueError('Source identity differs: '+path)
        text[path] = raw.decode('utf-8')
    observations = []
    for file,slot,child,name in ROWS:
        path = next(k for k in PINS if k.endswith('.txt') and (('magicrunes' in k) == name.startswith('_cot_')))
        rootpath = path[:-4]+'.rootnames'
        matches = list(re.finditer(r'^RootMod\s+'+re.escape(name)+r'\s*\nEnd\s*$',text[path],re.M))
        if len(matches) != 1: raise ValueError('Expected exactly one empty RootMod')
        if re.search(r'^\s*(?:Def|Obj)\s+'+re.escape(name)+r'\s*$',text[rootpath],re.M|re.I):
            raise ValueError('Previously absent rootname now exists')
        if not re.search(r'^\s+Group\s+'+re.escape(name)+r'\s*$',text[path],re.M):
            raise ValueError('Missing parent source reference')
        observations.append(dict(file=file,slot=slot,child=child,name=name,empty_rootmod=True,
                                 rootmod_line=text[path].count('\n',0,matches[0].start())+1,
                                 library_text=path,rootnames=rootpath,rootname_object_binding_present=False))
    loader = text['upstream/ouroboros/Common/group/groupfileload.c']
    group = text['upstream/ouroboros/Common/group/group.c']
    exporter = text['native-android/engine/scenecatalog/source_export.inc']
    if 'group_info.pre_alloc' in exporter or exporter.count('for (f = 0; f < file_count; ++f)') != 2:
        raise ValueError('Regular-file-only exporter boundary changed')
    original_new = body(group, 'GroupDef *groupDefNew(GroupFile *file)')
    original_future = body(loader, 'GroupDef *groupDefFuture(const char *name)')
    original_guard = body(loader, 'if ( 0 == eaSize(&defload->groups) && !defload->obj_name)')
    shim = r'''
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
typedef struct GroupFile GroupFile;
typedef struct GroupDef {int id,in_use,pre_alloc,try_to_weld;GroupFile *file;const char *name;} GroupDef;
struct GroupFile {int count,pre_alloc;GroupDef **defs;};
typedef struct {GroupFile **files,*pre_alloc;int file_count;void *def_mempool,*groupDefNameHashTable;} GroupInfo;
typedef struct Element {const char *name;GroupDef *def;} *StashElement;
static GroupInfo group_info,*group_ptr=&group_info;
static struct Element entries[16];static unsigned count,checks,bounds_calls;
static GroupDef *allocated[16];static unsigned allocated_count;
static void groupFileNew(void){assert(0);}
static void *createMemoryPool(void){return &count;}
static void initMemoryPool(void *p,size_t n,int size){assert(p&&n==sizeof(GroupDef)&&size==1024);}
static void *mpAlloc(void *p){assert(p&&allocated_count<16);return allocated[allocated_count++]=calloc(1,sizeof(GroupDef));}
static void groupDefModify(GroupDef *d){assert(d&&!d->pre_alloc);}
static void stashAddPointerAndGetElement(void *table,const char *name,GroupDef *d,int replace,StashElement *out){
    (void)table;assert(!replace&&count<16);entries[count]=(struct Element){name,d};*out=&entries[count++];
}
static const char *stashElementGetStringKey(StashElement e){return e->name;}
static int objectLibraryGetBounds(const char *name,GroupDef *d){assert(name&&d);bounds_calls++;return 0;}
#define false 0
#define PERFINFO_AUTO_STOP_CHECKED(x) ((void)(x))
typedef struct {int group_count;char *obj_name;int *groups;} DefLoad;
static int eaSize(int *const *p){return *p?**p:0;}
'''
    main = r'''
int main(void){
    GroupFile regular={0};GroupFile *files[]={&regular};group_info.files=files;group_info.file_count=1;
    for(unsigned n=0;n<4;n++)for(unsigned obj=0;obj<2;obj++){
        int count_=(int)n;DefLoad d={(int)n,obj?"model":NULL,n?&count_:NULL};
        assert((source_guard(&d)!=NULL)==(n||obj));checks++;
    }
    const char *names[]={NAMES};
    for(unsigned n=0;n<7;n++){
        GroupDef *d=groupDefFuture(names[n]);assert(d&&d->pre_alloc&&d->in_use&&d->file==group_info.pre_alloc);
        assert(d->file->pre_alloc&&d->file->count==0&&!d->file->defs);
        assert(group_info.file_count==1&&regular.count==0&&!regular.defs&&strcmp(d->name,names[n])==0);checks+=3;
    }
    assert(bounds_calls==7&&count==7);checks++;
    GroupDef *normal=groupDefNew(&regular);assert(normal&&!normal->pre_alloc&&regular.count==1&&regular.defs[0]==normal);checks++;
    for(unsigned n=0;n<allocated_count;n++)free(allocated[n]);free(regular.defs);free(group_info.pre_alloc);
    printf("{\"passed\":true,\"checks\":%u,\"unmodified_whole_source_functions\":2,\"original_guard_blocks\":1}\n",checks);
    return 0;
}
'''.replace('NAMES', ','.join(json.dumps(row[3]) for row in ROWS))
    harness = shim+'\n'+original_new+'\n'+original_future+'\nstatic DefLoad *source_guard(DefLoad *defload){\n'+original_guard+'\nreturn defload;\n}\n'+main
    outcomes = {}
    with tempfile.TemporaryDirectory(prefix='coh-missing-source-') as temporary:
        tmp = Path(temporary);source=tmp/'source.c';source.write_text(harness)
        for mode,flags in [('release',['-O2']),('asan',['-O1','-fsanitize=address','-no-pie']),
                           ('ubsan',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
            exe=tmp/mode;catalog.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',*flags,source,'-o',exe])
            outcomes[mode]=json.loads(catalog.run([exe],env={**os.environ,'ASAN_OPTIONS':'detect_leaks=0:halt_on_error=1','UBSAN_OPTIONS':'halt_on_error=1'}).stdout)
    result=dict(schema=1,passed=True,source_sha256=PINS,missing_names=observations,checks=outcomes,
                source_functions_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in
                    [('groupDefNew',original_new),('groupDefFuture',original_future),('addDef_early_guard',original_guard)]},
                harness_sha256=hashlib.sha256(harness.encode()).hexdigest(),
                scope='two unchanged original allocation functions plus exact early guard in bounded fixture shims; full loader/model/bounds services not executed',
                inference='empty RootMods and absent rootname Obj bindings explain source future references outside regular catalog file slots; actual captured pre_alloc objects were not exported',
                actual_root_reachability_verified=False,actual_prealloc_capture_verified=False,
                complete_object_library_generation_verified=False,placeholder_definitions_published=False,
                next_input='matching GROUPS roots and exact loaded library/model generation or explicit nonrenderable-source-future semantics, with independent source qualification')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'passed':True,'missing_names':len(observations),'checks':outcomes}))


if __name__=='__main__':main()
