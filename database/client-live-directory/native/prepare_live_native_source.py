"""Pure closed-source overlay plan. No copy, compilation or activation."""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys
import subprocess
import tempfile
import ast
import json

SOURCE = 'libs/UtilitiesLib/src/utils/FolderCache.c'
HEADER = 'libs/UtilitiesLib/include/utilitieslib/utils/FolderCache.h'
GAME = 'Game/src/game.c'
NODE = 'libs/UtilitiesLib/src/utils/FolderCacheNode.c'
SIGNATURE = 'static void FolderCacheAddFolderToNode('
RECEIPT = 'native-client-live-directory-build-input.json'
STAGED_FILES = ('coh_live_native_policy.h','coh_live_native_authorization.h','coh_live_native_adapter.h',
                'coh_live_transport.h','coh_live_transport.c','coh_live_directory_batch.h')
STOCK_PINS = {SOURCE:'93aac8a9e1a59ca47ab5a067580c36f7ed884db51038577b0453756f55af1d4c',
              HEADER:'42f1b9c5555abdc93afe7029cdf02bb551d572c18557fed00d7610d6c58e177c',
              GAME:'7a970aa0db124fb68ec37e8b4eb6f5907c4883f9f17a5475ec5b58e5dfa9adde',
              NODE:'36faafa73afd83361fb8e4f25e340961fae5fb9d33c298b1200be9a4b2a48524'}


def require(value, message):
    if not value:
        raise ValueError(message)


def function(text, signature):
    start = text.index(signature)
    require(text.count(signature) == 1, 'Ambiguous source function: ' + signature)
    body = text.index('{', start)
    # These frozen bodies have balanced braces in their ordinary comments.
    count = 1
    i = body + 1
    while count and i < len(text):
        count += (text[i] == '{') - (text[i] == '}')
        i += 1
    require(count == 0, 'Unclosed source function')
    return text[start:i]


def entry_body(original):
    body = function(original, SIGNATURE)
    begin, end = '    do {\n', '\n    } while (fwFindNextFile(handle, &wfd)!=0);'
    require(body.count(begin) == body.count(end) == 1, 'Stock enumeration loop differs')
    return body.split(begin, 1)[1].split(end, 1)[0]


def patch_cache(original):
    stock = function(original, SIGNATURE)
    body = entry_body(original)
    require(not any(word in body for word in ('strLength', 'basepath', 'handle')), 'Per-row closure differs')
    helper = '''static void cohFolderCacheAddLiveEntry(
    FolderCache *fc, FolderNode **node, FolderNode **tail, FolderNode *parent,
    int virtual_location, const WIN32_FIND_DATAA *coh_entry)
{
    char buffer[1024];
    WIN32_FIND_DATAA wfd = *coh_entry;
    FolderNode *node2;
''' + body.replace('continue;', 'return;') + '\n}\n\n'
    anchor = '    strcpy(buffer, basepath);\n    strcat(buffer, "/*");'
    require(stock.count(anchor) == 1, 'Pre-enumeration anchor differs')
    hook = '''#if defined(COH_CLIENT_LIVE_DIRECTORY)
    {
        CohLiveNativeDirectory *coh_live_directory = NULL;
        int coh_live_result = cohLiveNativeFirst(fc, folder_cache, basepath,
            FolderCache_GetFromVirtualLocation(fc, 0), FolderCache_GetNumGDDs(fc),
            virtual_location,
            fc->nodeCreateCallback == NULL && fc->nodeDeleteCallback == NULL,
            folder_cache_update_enable == 0,
            FolderCacheGetMode() == FOLDER_CACHE_MODE_DEVELOPMENT_DYNAMIC,
            folder_cache_exclusion == FOLDER_CACHE_ALL_FOLDERS && folder_cache_exclusion_folder == NULL,
            fileIsUsingDevData(), &coh_live_directory, &wfd);
        if (coh_live_result >= 0) {
            if (coh_live_result > 0) {
                do {
                    cohFolderCacheAddLiveEntry(fc, node, tail, parent, virtual_location, &wfd);
                } while (cohLiveNativeNext(coh_live_directory, &wfd) == 1);
            }
            cohLiveNativeClose(coh_live_directory);
            goto coh_live_recurse;
        }
    }
#endif

'''
    patched = stock.replace(anchor, hook + anchor, 1)
    loop = '    do {\n' + body + '\n    } while (fwFindNextFile(handle, &wfd)!=0);'
    require(patched.count(loop) == 1, 'Stock loop differs')
    patched = patched.replace(loop, '''    do {
        cohFolderCacheAddLiveEntry(fc, node, tail, parent, virtual_location, &wfd);
    } while (fwFindNextFile(handle, &wfd)!=0);''', 1)
    recursion = '    for(node2 = *node; node2; node2 = node2->next){'
    require(patched.count(recursion) == 1, 'Stock recursion differs')
    patched = patched.replace(recursion, '#if defined(COH_CLIENT_LIVE_DIRECTORY)\ncoh_live_recurse:\n#endif\n' + recursion, 1)
    result = original.replace(stock, helper + patched, 1)
    include = '#include "utilitieslib/utils/FolderCache.h"\n'
    require(result.count(include) == 1, 'Cache include differs')
    result = result.replace(include, include + '#if defined(COH_CLIENT_LIVE_DIRECTORY)\n#include "coh_live_native_adapter.h"\n#endif\n', 1)
    pig = function(result, 'int FolderCacheAddAllPigs(')
    tail = '    }\n    return 0;\n}'
    require(pig.count(tail) == 1, 'Stock PIG registration tail differs')
    pig_patched = pig.replace(tail, '''    }
#if defined(COH_CLIENT_LIVE_DIRECTORY)
    if (fc == folder_cache) cohLiveNativeRegisterCache(fc);
#endif
    return 0;
}''', 1)
    return result.replace(pig, pig_patched, 1)


def patch_game(original):
    before = 'void game_beforeParseArgs(int doLogging)\n{\n'
    require(original.count(before) == 1, 'Main-thread hook differs')
    result = original.replace(before, before + '''#if defined(COH_CLIENT_LIVE_DIRECTORY)
    FolderCacheLiveDirectorySetMainThread();
#endif
''', 1)
    loop = function(result, 'void game_beforeLoop(')
    anchor = '    FolderCacheEnableCallbacks(1);'
    require(loop.count(anchor) == 1, 'Before gameplay callback enable differs')
    loop_patched = loop.replace(anchor, '''#if defined(COH_CLIENT_LIVE_DIRECTORY)
    FolderCacheLiveDirectoryStop();
#endif
''' + anchor, 1)
    return result.replace(loop, loop_patched, 1)


def patch_header(original):
    anchor = '#define MAX_IGNORE_PREFIXES 50\n'
    require(original.count(anchor) == 1, 'Native declaration hook differs')
    return original.replace(anchor, anchor + '''
#if defined(COH_CLIENT_LIVE_DIRECTORY)
void FolderCacheLiveDirectorySetMainThread(void);
void FolderCacheLiveDirectoryStop(void);
#endif
''', 1)


def retained_effective_game(upstream, repository):
    """Restore only this small source from its two historical retained layers.

    Native package ancestry remains unchanged. The exact output pin is the
    authenticated .36 Game/source closure; the new hook cannot drop either
    already-qualified gameplay/scene layer.
    """
    # Read names from the retained recipe rather than inventing historical paths.
    scene = Path(repository)/'tools/android/interactive/package_client_scene_performance_native.py'
    gameplay = Path(repository)/'tools/android/interactive/package_client_gameplay_performance_native.py'
    patches=[]
    for module_path in (scene,gameplay):
        assignments=[node for node in ast.parse(module_path.read_text()).body
                     if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PATCHES' for t in node.targets)]
        require(len(assignments)==1,'Historical patch list differs')
        value=ast.literal_eval(assignments[0].value)
        require(isinstance(value,tuple) and all(isinstance(n,str) and n.startswith('patches/') and '..' not in Path(n).parts for n in value),
                'Historical patch list is not a closed relative tuple')
        patches.extend(value)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        game = root/GAME
        game.parent.mkdir(parents=True)
        game.write_bytes((Path(upstream)/GAME).read_bytes().replace(b'\r\n',b'\n'))
        for name in patches:
            raw=(Path(repository)/name).read_bytes().replace(b'\r\n',b'\n')
            subprocess.run(['git','apply','--include='+GAME,'-'], cwd=root,input=raw,
                           check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        effective=game.read_bytes()
    require(hashlib.sha256(effective).hexdigest()=='5eed5c92eadccff067c2821d82601578f825f758ba12842b2d40af99208f1546',
            'Exact historical native Game gameplay/scene layers differ')
    return effective,{name:hashlib.sha256((Path(repository)/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for name in patches}


def source_plan(upstream,repository=None):
    upstream = Path(upstream)
    repository = Path(repository) if repository else upstream.parents[1]
    original = {name: (upstream/name).read_bytes().replace(b'\r\n', b'\n') for name in (SOURCE, HEADER, GAME, NODE)}
    require({n:hashlib.sha256(v).hexdigest() for n,v in original.items()}==STOCK_PINS,
            'Exact retained stock native input pins differ')
    effective_game,game_patches=retained_effective_game(upstream,repository)
    patched = {SOURCE: patch_cache(original[SOURCE].decode()).encode(),
               HEADER: patch_header(original[HEADER].decode()).encode(),
               GAME: patch_game(effective_game.decode()).encode()}
    digest = lambda data: hashlib.sha256(data).hexdigest()
    return {'role': 'dormant_live_constructor_source_plan', 'source_sha256': {n: digest(v) for n,v in original.items()},
            'native_Game_predecessor_sha256':digest(effective_game),'inherited_native_Game_patches_sha256':game_patches,
            'patched_sha256': {n: digest(v) for n,v in patched.items()},
            'stock_per_entry_body_sha256': digest(entry_body(original[SOURCE].decode()).encode()),
            'stock_FolderNodeAdd_sha256': digest(function(original[NODE].decode(), 'FolderNode *FolderNodeAdd(').encode()),
            'branches': ['fx','scripts.loc'], 'source_recipe': 'wine-b073-constructor-v1',
            'initial_stock_fallback_before_any_global_rows': True,
            'later_failure_is_nonzero_startup_exit': True,
            'stock_parent_close_then_recursion_retained': True,
            'ordinary_native_leaf_reads_stat_and_timestamp_conversion_unchanged': True,
            'current_native_directory_inode_join_before_NEXT': True,
            'windows_volume_serial_is_host_device': False,
            'startup_only_zoning_uses_stock': True,
            'current_source_lease_required': False,
            'persistent_namespace_scan_or_replay': False,
            'SDK_executed': False, 'Wine_executed': False, 'Android_runtime_executed': False,
            'native_registration_allowed': False, 'publication_allowed': False}, patched


def expected_receipt(repository,overlay_root=None):
    repository=Path(repository).resolve()
    overlay_root=Path(overlay_root) if overlay_root else Path(__file__).resolve().parent.parent
    plan,_=source_plan(repository/'upstream/ouroboros',repository)
    native=overlay_root/'native'
    transport=overlay_root/'transport'
    files={n:(native/n if (native/n).is_file() else transport/n) for n in STAGED_FILES}
    require(all(p.is_file() and not p.is_symlink() for p in files.values()),'Missing or linked native overlay')
    return {'format':1,'role':'dormant_live_native_constructor_build_input','source_plan':plan,
            'overlay_sha256':{'libs/UtilitiesLib/src/utils/'+n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in files.items()},
            'cmake_injection_sha256':hashlib.sha256((native/'coh_live_directory.cmake').read_bytes()).hexdigest(),
            'retained_game_recipe':'package_client_render_queue_native',
            'all_historical_native_source_receipts_retained_raw':True,
            'all_current_native_runtime_gates':False,'publication_allowed':False}


def _retained(repository):
    root=Path(repository).resolve()
    sys.path.insert(0,str(root/'tools'))
    sys.path.insert(0,str(root/'tools/android/interactive'))
    import package_client_render_queue_native as retained
    import prepare_map_startup_observer_source as safe
    require(retained.ROOT.resolve()==root,'Foreign imported native recipe refused')
    return retained,safe


def validate_staged_source(staging,repository,overlay_root=None):
    retained,safe=_retained(repository)
    staging=Path(staging).absolute()
    require(not any(p.is_symlink() for p in (staging,*staging.parents)),'Linked staging refused')
    expected=expected_receipt(repository,overlay_root)
    actual=retained.baseline.read_json(safe.safe_staging_file(staging,RECEIPT))
    require(retained.typed_equal(actual,expected),'Exact live source receipt differs')
    current=retained
    producers=[]
    while hasattr(current,'expected_receipt'):
        producers.append(current)
        if not hasattr(current,'base'):
            break
        current=current.base
    historical=retained.baseline.source_receipts(staging)
    pins={}
    for value in historical.values():
        for field in ('patched_sha256','overlay_sha256','graphics_overlay_sha256','events_overlay_sha256'):
            pins.update(value.get(field,{}))
    for producer in reversed(producers):
        previous=producer.expected_receipt()
        require(retained.typed_equal(retained.baseline.read_json(safe.safe_staging_file(staging,producer.RECEIPT)),previous),
                'Historical native receipt differs: '+producer.RECEIPT)
        for field in ('native_callsite_sources_sha256','patched_sha256','overlay_sha256'):
            pins.update(previous.get(field,{}))
    for name,pin in retained.baseline.schema_pins().items():
        pins.setdefault(name,pin)
    plan=expected['source_plan']
    require(pins.get(GAME)==plan['native_Game_predecessor_sha256'],'Historical native Game predecessor differs')
    pins.update(plan['patched_sha256'])
    pins.update(expected['overlay_sha256'])
    pins['coh_live_directory.cmake']=expected['cmake_injection_sha256']
    pins[NODE]=plan['source_sha256'][NODE]
    for name,pin in pins.items():
        path=safe.safe_staging_file(staging,name)
        require(path.is_file() and hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==pin,
                'Exact effective native source closure differs: '+name)
    return {'source':expected,'retained_game_build_input':retained.expected_receipt(),
            'historical_source_receipts':historical,'validated_sources_sha256':pins}


def stage(staging,repository,overlay_root=None):
    repository=Path(repository).resolve()
    staging=Path(staging).absolute()
    require(not any(p.is_symlink() for p in (staging,*staging.parents)),'Linked staging refused')
    require(staging!=repository and staging not in repository.parents and repository/'upstream' not in (staging,*staging.parents),
            'Immutable repository or upstream staging refused')
    retained,safe=_retained(repository)
    retained.validate_source(staging)
    expected=expected_receipt(repository,overlay_root)
    plan=expected['source_plan']
    overlay_root=Path(overlay_root) if overlay_root else Path(__file__).resolve().parent.parent
    _,patched=source_plan(repository/'upstream/ouroboros',repository)
    for name in (SOURCE,HEADER,GAME,NODE):
        target=safe.safe_staging_file(staging,name)
        expected_pin=plan['native_Game_predecessor_sha256'] if name==GAME else plan['source_sha256'][name]
        require(hashlib.sha256(target.read_bytes().replace(b'\r\n',b'\n')).hexdigest()==expected_pin,
                'Exact retained predecessor differs: '+name)
    for name in (*expected['overlay_sha256'],RECEIPT,'coh_live_directory.cmake'):
        require(not safe.safe_staging_file(staging,name).exists(),'Native overlay output already exists: '+name)
    for name in STAGED_FILES:
        source=overlay_root/'native'/name
        if not source.is_file():
            source=overlay_root/'transport'/name
        safe.safe_staging_file(staging,'libs/UtilitiesLib/src/utils/'+name).write_bytes(source.read_bytes())
    safe.safe_staging_file(staging,'coh_live_directory.cmake').write_bytes((overlay_root/'native/coh_live_directory.cmake').read_bytes())
    for name,data in patched.items():
        safe.safe_staging_file(staging,name).write_bytes(data)
    safe.safe_staging_file(staging,RECEIPT).write_text(json.dumps(expected,sort_keys=True,indent=2)+'\n')
    return validate_staged_source(staging,repository,overlay_root)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--staging',type=Path)
    parser.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    if args.staging:
        value=validate_staged_source(args.staging,args.repository) if args.validate else stage(args.staging,args.repository)
    else:
        require(not args.validate,'Validation requires exact staging')
        value=expected_receipt(args.repository)
    print(json.dumps(value,sort_keys=True,indent=2))
