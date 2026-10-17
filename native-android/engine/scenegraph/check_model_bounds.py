#!/usr/bin/env python3
"""Original readModel field-copy + trick-stage fixture oracle; no services."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,tempfile
from check_group_bounds import extract
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def run(args,**kw):
 p=subprocess.run(list(map(str,args)),capture_output=True,text=True,timeout=180,**kw)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--sanitize',action='store_true');a=p.parse_args()
original=ROOT/'upstream/ouroboros/Common/seq/anim.c';text=original.read_text();functions=[extract(text,n) for n in ['readModel','modelInitTrickNodeFromName']]
code=(HERE/'tests/model_bounds_oracle_shim.h').read_text()+'\n#pragma GCC diagnostic push\n#pragma GCC diagnostic ignored "-Wpointer-sign"\n'+functions[0]+'\n#pragma GCC diagnostic pop\n'+functions[1]+'''
unsigned original_model_bounds(const CohModelBoundsTable *t,const CohModelBoundsView *v){
 Model m={0};GeoLoadData g={"source_fixture.geo"};unsigned checks=0;
 int n=readModel(&m,(char*)v->record.data,(int)t->version,(U8*)t->names.data,(U8*)t->header.data);
 #define SAME(x) do{checks++;if(!(x))abort();}while(0)
 SAME(n==(int)v->record.size);SAME(!strcmp(m.name,v->name));SAME(!memcmp(m.min,v->numbers.min,12));SAME(!memcmp(m.max,v->numbers.max,12));SAME(!memcmp(m.scale,v->numbers.scale,12));SAME(!memcmp(&m.radius,&v->numbers.radius,4));
 m.gld=&g;for(int mode=0;mode<3;mode++){original_has_trick=mode==1;modelInitTrickNodeFromName(m.name,&m);SAME(!memcmp(m.min,v->numbers.min,12));SAME(!memcmp(m.max,v->numbers.max,12));SAME(!memcmp(m.scale,v->numbers.scale,12));SAME(!memcmp(&m.radius,&v->numbers.radius,4));}free(m.trick);return checks;
}
'''
sources=[HERE/'coh_model_bounds.c',HERE/'tests/test_model_bounds.c'];deps=sources+[HERE/'coh_model_bounds.h',HERE/'tests/model_bounds_oracle_shim.h',Path(__file__),HERE/'check_group_bounds.py',original,ROOT/'upstream/ouroboros/Common/seq/anim.h',ROOT/'upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/components/gridpoly.h'];pins={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest() for x in deps};modes={}
with tempfile.TemporaryDirectory(prefix='coh-model-bounds-') as directory:
 d=Path(directory);(d/'original.c').write_text(code)
 for mode,flags in [('release',['-O2'])]+([('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])] if a.sanitize else []):
  binary=d/mode;run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(HERE),*sources,d/'original.c','-lm','-o',binary]);modes[mode]=json.loads(run([binary],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
result={'passed':True,'modes':modes,'source_sha256':pins,'original_function_sha256':[hashlib.sha256(f.encode()).hexdigest() for f in functions],'oracle_sha256':hashlib.sha256(code.encode()).hexdigest(),'fixture_scope':'unchanged readModel and modelInitTrickNodeFromName with explicit32-bit disk-layout shells, not originalWin32ABI','source_generation_admitted':False,'world_authority':False,'android_execution':False,'leak_sanitizer':False}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
