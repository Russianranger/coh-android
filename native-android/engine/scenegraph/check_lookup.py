#!/usr/bin/env python3
"""Execute unchanged original model/library lookup functions on explicit fixtures."""
import argparse,ctypes as C,hashlib,json,os,re,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PATHS=['Common/group/groupfilelib.c','Common/group/group.c','Common/seq/anim.c',
       'libs/UtilitiesLib/src/utils/utils.c','libs/UtilitiesLib/src/components/StashTable.c']
FILES=[(3,'object_library/a.vrml','object_library/a.geo'),(7,'folder.with.dot/b','folder.with.dot/b.geo')]
LIBRARIES=[(2,3,'Box'),(5,3,'BoxLong'),(9,7,'Clone'),(10,7,'Back\\Box'),(11,3,'NoModel')]
MODELS=[(3,4,'Box__OriginalTrick'),(3,9,'BoxLong'),(3,11,'Box_1&'),(7,2,'Clone'),(7,6,'Back\\Box__Trick')]
QUERIES=['box','folder/BOX__different','Box_1&','folder/Box_2&','BoxLong','BoxL','Unknown','Back\\Box','NoModel','Clone','Clone__Tint','folder/Box__Tint_4&','BOX__','Box.Long']
EXTENSIONS=['a','a.geo','dir.v/name','dir/a.geo','dir\\a.vrml','dir/.hidden','dir/a.b.c','dir.v\\a','dir/a.']
def run(args,**kw):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True,**kw)
    if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    return p.stdout
def source(root,path):
    p=root/'upstream/ouroboros'/path
    return (p.read_bytes() if p.is_file() else subprocess.check_output(['git','-C',str(root),'show','HEAD:upstream/ouroboros/'+path])).decode().replace('\r\n','\n')
def extract(text,name):
    m=re.search(r'^([^\n;{}]+\b'+re.escape(name)+r'\s*\([^;{}]*\)\s*\{)',text,re.M)
    if not m:raise ValueError(name)
    pos=text.index('{',m.start())+1;depth=1
    while depth:depth+=(text[pos]=='{')-(text[pos]=='}');pos+=1
    return text[m.start():pos]+'\n'
def prepare(root,directory):
    sources={p:source(root,p) for p in PATHS}
    pins={p:hashlib.sha256(s.encode()).hexdigest() for p,s in sources.items()}
    if pins!=json.loads((HERE/'lookup-source-pins.json').read_text()):raise ValueError('lookup source pins changed')
    code=(HERE/'tests/lookup_oracle_shim.h').read_text();functions={}
    for path,names in [(PATHS[3],['changeFileExt_s']),
                       (PATHS[0],['groupGetPublicName','groupNameIdx','objectLibraryFileCount','objectLibraryEntryFromIdx','objectLibraryEntryFromObj']),
                       (PATHS[2],['compareModelNamesAndLengths','compareModelBSearch','compareModelBSearchCallback','modelFind','compareModelNames','compareModelNamesCallback']),
                       (PATHS[1],['groupModelFind'])]:
        for name in names:
            body=extract(sources[path],name);functions[name]=hashlib.sha256(body.encode()).hexdigest();code+='\n'+body
    code+='\nvoid original_setup(void){\n'
    for slot,path,geo in FILES:
        code+=f'static GroupFileEntry f{slot}={{'+json.dumps(path)+f',{slot}}};file_rows[{slot}]=&f{slot};strcpy(geo_paths[{slot}],'+json.dumps(geo)+');\n'
    for slot,file,name in LIBRARIES:
        code+=f'static GroupLibNameEntry l{slot}={{'+json.dumps(name)+f',{file}}};library_rows[{slot}]=&l{slot};\n'
    for file,slot,name in MODELS:
        code+=f'static Model m{file}_{slot}={{'+json.dumps(name)+f',{len(name.split("__")[0])},{slot},{file}}};\n'
    for file,_,_ in FILES:
        rows=[f'&m{f}_{slot}' for f,slot,_ in MODELS if f==file]
        code+=f'static Model* models{file}[]={{'+','.join(rows)+f'}};qsort(models{file},{len(rows)},sizeof(Model*),compareModelNamesCallback);geos[{file}].modelheader=(ModelHeader){{models{file},{len(rows)}}};\n'
    code+='}\nint original_lookup(const char*name,unsigned*out){Model*m=groupModelFind(name);if(!m)return 0;out[0]=m->file;out[1]=m->slot;return 1;}\n'
    code+='void original_extension(const char*name,char*out){changeFileExt_s(name,".geo",out,260);}\n'
    p=directory/'lookup-original.c';p.write_text(code);so=directory/'lookup-original.so'
    run(['cc','-std=c99','-O0','-fPIC','-shared','-w',p,'-o',so]);lib=C.CDLL(str(so));lib.original_setup();lib.original_lookup.argtypes=[C.c_char_p,C.POINTER(C.c_uint)];lib.original_extension.argtypes=[C.c_char_p,C.c_void_p]
    lines=[]
    lines.append('static const CohSgLookupFile lookup_files[]={'+','.join('{%d,%d,7,{1},%s,%s}'%(slot,slot+100,json.dumps(path),json.dumps(geo)) for slot,path,geo in FILES)+'};\n')
    lines.append('static const CohSgLookupLibrary lookup_libraries[]={'+','.join('{%d,%d,%s}'%(slot,file,json.dumps(name)) for slot,file,name in LIBRARIES)+'};\n')
    lines.append('static const CohSgLookupModel lookup_models[]={'+','.join('{%d,%d,%s}'%(file,slot,json.dumps(name)) for file,slot,name in MODELS)+'};\n')
    rows=[]
    queries=list(QUERIES)
    for i in range(512):
        name=['Box','BoxLong','Clone','Back\\Box','Box_1&','Box_2&'][i%6]
        name=''.join(c.upper() if (i>>(j%9))&1 else c.lower() for j,c in enumerate(name))
        queries.append(('folder.with.dot/' if i&1 else '')+name+(['','__Trick','__Trick_4&','__'][i%4]))
    for q in queries:
        result=(C.c_uint*2)();found=lib.original_lookup(q.encode(),result)
        rows.append('{%s,%d,%d,%d}'%(json.dumps(q),found,*result))
    lines.append('typedef struct {const char*query;unsigned found,file,model;}LookupFixture;\nstatic const LookupFixture lookup_fixtures[]={'+','.join(rows)+'};\n')
    extensions=[]
    for name in EXTENSIONS:
        result=C.create_string_buffer(260);lib.original_extension(name.encode(),result)
        extensions.append('{'+json.dumps(name)+','+json.dumps(result.value.decode())+'}')
    lines.append('static const struct {const char*name,*geo;} lookup_extensions[]={'+','.join(extensions)+'};\n')
    path=directory/'lookup_fixtures.h';path.write_text(''.join(lines))
    return {'source_sha256_lf':pins,'original_function_sha256':functions,'generated_oracle_sha256':hashlib.sha256(code.encode()).hexdigest(),
            'fixtures':len(rows),'extension_fixtures':len(extensions),'fixtures_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'scope':'unchanged original groupModelFind/modelFind plus lookup/name/extension helpers; synthetic StashDefault ASCII table and geoLoad/header owners; no archive I/O, authentic manifest, trick/material lookup or draw admission',
            'source_oracle_sanitized':False}
def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=ROOT);p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='coh-lookup-') as temp:
        d=Path(temp);oracle=prepare(a.source_root,d);checks={}
        flags=['-std=c99','-Wall','-Wextra','-Werror','-pedantic','-DCOH_LOOKUP_STANDALONE','-I'+str(d),'-I'+str(HERE),'-Wl,--wrap=calloc,--wrap=free']
        sources=[HERE/'coh_scene_lookup.c',HERE/'tests/test_scene_lookup.c']
        for mode,extra in [('release',['-O2'])]+([('asan',['-O1','-g','-fsanitize=address','-fno-omit-frame-pointer','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
            binary=d/mode;run([os.environ.get('CC','cc'),*flags,*extra,*sources,'-o',binary]);checks[mode]=json.loads(run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')))
        paths=[*sources,HERE/'coh_scene_lookup.h',HERE/'tests/lookup_oracle_shim.h',HERE/'lookup-source-pins.json',HERE/'check_lookup.py',HERE.parent/'coh_contracts.h']
        result={'passed':True,'oracle':oracle,'checks':checks,'source_sha256':{str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths},'authentic_manifest':False,'renderer_authorized':False}
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
