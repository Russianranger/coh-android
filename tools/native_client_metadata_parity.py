#!/usr/bin/env python3
"""NONSHIPPING metadata hydration parity over unchanged native C algorithms.

This is a bounded algorithm fixture, not a Game/Wine test, source authenticator,
BIN freshness bypass, import certificate or provider-generation authority.
The manifest accepts caller-supplied synthetic provider observations only.
Production must independently establish their completeness and immutability.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import map_startup_namespace_certificate as stock

NODE = ROOT / stock.NODE
FILE = ROOT / 'upstream/ouroboros/libs/UtilitiesLib/src/utils/file.c'
CACHE = ROOT / 'upstream/ouroboros/libs/UtilitiesLib/src/utils/FolderCache.c'
FORMAT = 'coh_nonshipping_metadata_parity_v1'
LIMIT = 100000
FIELDS = ('path', 'timestamp', 'bytes', 'provider', 'file_index', 'seen_in_fs', 'attributes', 'is_dir')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def source_contract():
    functions = {'FolderNodeAdd': stock.function(NODE.read_text(), 'FolderNode *FolderNodeAdd('),
                 'FolderNodeFind': stock.function(NODE.read_text(), 'FolderNode *FolderNodeFind('),
                 'fileDatesEqual': stock.function(FILE.read_text(), 'bool fileDatesEqual(')}
    contract = {name: digest(text.encode()) for name, text in functions.items()}
    cache_text = CACHE.read_text()
    folder = stock.function(cache_text, 'static void FolderCacheAddFolderToNode(')
    pig = stock.function(cache_text, 'static void FolderCacheAddPig(FolderCache *fc, PigFile *pigfile, int virtual_location)\n')
    require('node2->writeable = !(wfd.dwFileAttributes & FILE_ATTRIBUTE_READONLY);' in folder
            and 'node2->hidden = wfd.dwFileAttributes & FILE_ATTRIBUTE_HIDDEN ? 1 : 0;' in folder
            and 'node2->system = wfd.dwFileAttributes & FILE_ATTRIBUTE_SYSTEM ? 1 : 0;' in folder
            and not any(name in pig for name in ('->writeable', '->hidden', '->system')),
            'native metadata adapter contract changed')
    contract.update(FolderCacheAddFolderToNode=digest(folder.encode()), FolderCacheAddPig=digest(pig.encode()))
    return functions, contract


def validate_identity(identity):
    require(set(identity) == {'mode', 'roots', 'pigs', 'ignore_policy', 'generation',
                             'consumer', 'ownership', 'complete_namespace', 'immutable'}, 'identity schema')
    require(identity['mode'] == 'FOLDER_CACHE_MODE_DEVELOPMENT_DYNAMIC', 'unsupported mode')
    require(identity['complete_namespace'] is True and identity['immutable'] is True,
            'complete immutable namespace assertion absent')
    # These are fixture assertions, NEVER authentication. No production acceptance
    # API exists in this prototype, even when the structural validation succeeds.
    for field in ('generation', 'consumer', 'ownership', 'ignore_policy'):
        require(isinstance(identity[field], str) and identity[field], 'missing identity: ' + field)
    require(isinstance(identity['roots'], list) and identity['roots'], 'ordered roots absent')
    require(isinstance(identity['pigs'], list), 'ordered pigs absent')
    for field in ('roots', 'pigs'):
        require(all(isinstance(x, str) and x for x in identity[field]) and
                len(set(identity[field])) == len(identity[field]), 'ambiguous providers')


def validate_rows(rows, identity):
    require(isinstance(rows, list) and 0 < len(rows) <= LIMIT, 'row bound')
    for row in rows:
        require(set(row) == set(FIELDS), 'row schema')
        path = row['path']
        require(isinstance(path, str) and path and len(path) < 259 and path.isascii()
                and all(32 <= ord(c) < 127 and c not in '\\:\t' for c in path)
                and all(p not in ('', '.', '..') for p in path.split('/')), 'noncanonical path')
        for field in FIELDS[1:]:
            require(type(row[field]) is int, 'integer field: ' + field)
        require(0 <= row['timestamp'] <= 2147483647 and 0 <= row['bytes'] <= 0xffffffff,
                'native 32-bit timestamp/size bound')
        provider = row['provider']
        require(-len(identity['pigs']) <= provider < len(identity['roots']), 'unknown provider')
        require(0 <= row['file_index'] <= 2147483647 if provider < 0 else row['file_index'] == -1,
                'provider file index')
        require(row['seen_in_fs'] in (0, 1) and row['is_dir'] in (0, 1)
                and 0 <= row['attributes'] <= 7, 'native attribute bound')


def c_source():
    functions, _ = source_contract()
    prefix = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdbool.h>
#define MAX_PATH 260
#define stricmp strcasecmp
#define ABS_UNS_DIFF(a,b) ((uint32_t)(a) > (uint32_t)(b) ? (uint32_t)(a)-(uint32_t)(b) : (uint32_t)(b)-(uint32_t)(a))
typedef int32_t __time32_t;
typedef struct FolderNode {
    struct FolderNode *next,*prev,*parent,*contents,*contents_tail;
    int virtual_location,file_index,is_dir,seen_in_fs,attributes;
    size_t size; int32_t timestamp; char *name;
} FolderNode;
static int folder_cache_debug,update_count,discard_count;
static FolderNode *FolderNodeCreate(void) {return calloc(1,sizeof(FolderNode));}
static char *allocAddString(const char *s) {return strdup(s);}
static char *firstSlash(char *s) {while(*s) {if(*s=='/'||*s=='\\') return s; ++s;} return NULL;}
'''
    suffix = r'''
static void emit(FolderNode *node,const char *parent) {
    for(;node;node=node->next) {
        char path[260];
        assert(strlen(parent)+strlen(node->name)+2<sizeof(path));
        strcpy(path,parent);if(*parent) strcat(path,"/");strcat(path,node->name);
        printf("%s\t%d\t%zu\t%d\t%d\t%d\t%d\t%d\n",path,node->timestamp,
               node->size,node->virtual_location,node->file_index,node->seen_in_fs,node->attributes,node->is_dir);
        if(node->contents) emit(node->contents,path);
    }
}
static void release(FolderNode *node) {
    while(node) {FolderNode *next=node->next;release(node->contents);free(node->name);free(node);node=next;}
}
int main(int argc,char **argv) {
    FolderNode *head=NULL,*tail=NULL,*node;char line[1024],path[260],adding[260];
    int date,provider,index,seen,attrs,is_dir,made,hydrate;
    unsigned long long bytes;
    assert(argc==2);hydrate=!strcmp(argv[1],"hydrate");
    assert(hydrate || !strcmp(argv[1],"replay"));
    /* Exercise actual native DST comparison, not a reimplemented equality. */
    assert(fileDatesEqual(1767225600,1767229200,true));
    assert(fileDatesEqual(1767229200,1767225600,true));
    assert(!fileDatesEqual(1767225600,1767229200,false));
    assert(!fileDatesEqual(1767225600,1767229201,true));
    while(fgets(line,sizeof(line),stdin)) {
        assert(sscanf(line,"%259[^\t]\t%d\t%llu\t%d\t%d\t%d\t%d\t%d",
                      path,&date,&bytes,&provider,&index,&seen,&attrs,&is_dir)==8);
        assert(strlen(path)+(is_dir?1:0)<sizeof(adding));
        strcpy(adding,path);if(is_dir) strcat(adding,"/");
        node=FolderNodeAdd(&head,&tail,NULL,adding,date,(size_t)bytes,provider,index,&made);
        if(hydrate) {
            assert(node);node->timestamp=date;node->size=(size_t)bytes;
            node->virtual_location=provider;node->file_index=index;
            node->seen_in_fs=seen;node->attributes=attrs;node->is_dir=is_dir;
        } else if(node && !is_dir && provider>=0) node->attributes=attrs;
        assert(FolderNodeFind(head,path));
    }
    emit(head,"");release(head);return 0;
}
'''
    return prefix + '\n'.join(functions.values()) + suffix


class NativeFixture:
    def __init__(self, directory):
        directory = Path(directory)
        self.source = directory / 'metadata_native_fixture.c'
        self.binary = directory / 'metadata_native_fixture'
        self.source.write_text(c_source())
        subprocess.run(['cc', '-std=c11', '-D_POSIX_C_SOURCE=200809L', '-O2', '-Wall', '-Werror',
                        str(self.source), '-o', str(self.binary)], check=True, capture_output=True)

    def run(self, rows, mode):
        text = ''.join('\t'.join(str(row[field]) for field in FIELDS) + '\n' for row in rows)
        result = subprocess.run([str(self.binary), mode], input=text, text=True,
                                capture_output=True, timeout=30, check=True)
        output = []
        for line in result.stdout.splitlines():
            values = line.split('\t')
            require(len(values) == len(FIELDS), 'native output schema')
            output.append(dict(zip(FIELDS, [values[0], *map(int, values[1:])])))
        return output


def make_manifest(rows, identity, native):
    validate_identity(identity)
    validate_rows(rows, identity)
    effective = native.run(rows, 'replay')
    return {'format': FORMAT, 'production_acceptance_allowed': False,
            'identity': identity, 'native_source_contract': source_contract()[1],
            'ordered_observations_sha256': digest(canonical(rows)),
            'effective': effective, 'effective_sha256': digest(canonical(effective))}


def qualify(manifest, current_rows, identity, native):
    validate_identity(identity)
    validate_rows(current_rows, identity)
    require(set(manifest) == {'format', 'production_acceptance_allowed', 'identity',
                            'native_source_contract', 'ordered_observations_sha256',
                            'effective', 'effective_sha256'}, 'manifest schema')
    require(manifest['format'] == FORMAT and manifest['production_acceptance_allowed'] is False,
            'nonshipping manifest only')
    require(manifest['identity'] == identity, 'generation/provider order/consumer changed')
    require(manifest['native_source_contract'] == source_contract()[1], 'native source changed')
    require(manifest['ordered_observations_sha256'] == digest(canonical(current_rows)),
            'namespace membership/metadata/order changed')
    validate_rows(manifest['effective'], identity)
    require(manifest['effective_sha256'] == digest(canonical(manifest['effective'])), 'payload changed')
    actual = native.run(current_rows, 'replay')
    require(actual == manifest['effective'], 'effective provider closure differs')
    require(native.run(manifest['effective'], 'hydrate') == actual, 'hydration parity differs')
    return {'status': 'passed', 'observed_rows': len(current_rows), 'effective_nodes': len(actual),
            'native_algorithm_execution': 'host_C_with_bounded_IO_adapters',
            'full_Game_execution': False, 'Wine_execution': False,
            'production_acceptance_allowed': False, 'performance_claim': False}


def row(path, *, timestamp=1767225600, size=100, provider=0, index=-1, attributes=0, is_dir=0):
    return dict(zip(FIELDS, [path, timestamp, size, provider, index, int(provider >= 0), attributes, is_dir]))


def fixture_identity():
    return {'mode': 'FOLDER_CACHE_MODE_DEVELOPMENT_DYNAMIC',
            'roots': ['fixture://base', 'fixture://override'],
            'pigs': ['fixture://first.pigg', 'fixture://second.pigg'],
            'ignore_policy': 'fixture_stock_policy_identity', 'generation': 'fixture_closed_generation',
            'consumer': 'fixture_exact_Game_and_FolderCache_source',
            'ownership': 'fixture_exclusive_closed_namespace',
            'complete_namespace': True, 'immutable': True}


if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='coh-metadata-fixture-') as temporary:
        native = NativeFixture(temporary)
        rows = [row('fx/Test.fx'), row('FX/test.FX', provider=-1, index=4),
                row('fx/test.fx', provider=-2, index=7), row('fx/test.fx', provider=1),
                row('fx/optional.fx', timestamp=0), row('fx/empty', size=0, is_dir=1)]
        identity = fixture_identity()
        manifest = make_manifest(rows, identity, native)
        print(json.dumps(qualify(manifest, rows, identity, native), indent=2))
