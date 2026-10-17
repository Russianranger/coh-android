#!/usr/bin/env python3
"""Qualify explicit guarded texFixName policy; strict default remains unchanged."""
import argparse,difflib,hashlib,importlib.util,json,os,subprocess,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
 if a.output.exists():raise ValueError('Fresh output required')
 original=module('strict_name_qualification',HERE/'check_texname.py');repair=module('isolated_name_repair',HERE/'texname_guard_candidate.py');pins=json.loads((HERE/'texname-source-pins.json').read_text())
 for path,h in pins.items():
  if sha(ROOT/path)!=h:raise ValueError('Original source differs')
 tex=(ROOT/'upstream/ouroboros/Game/src/render/tex.c').read_text();model=(ROOT/'upstream/ouroboros/Game/src/render/model.c').read_text()
 signatures=[(tex,'static int texFixName('),(tex,'char *texCheckForSceneMaterialSwap('),(tex,'TexBind *texFindComposite('),(tex,'TexBind *texLoad('),(model,'static TexBind ** buildTexBindArrayFromTexNames(')];parts=[original.extract(t,s) for t,s in signatures]
 candidate,correction=repair.patch(parts[0]);fixed=[candidate,*parts[1:]]
 if tex.count(parts[0])!=1:raise ValueError('Unique full-source candidate context differs')
 correction['original_full_source_sha256_lf']=hashlib.sha256(tex.encode()).hexdigest();correction['candidate_full_source_sha256_lf']=hashlib.sha256(tex.replace(parts[0],candidate,1).encode()).hexdigest()
 expected_patch=''.join(difflib.unified_diff(tex.splitlines(True),tex.replace(parts[0],candidate,1).splitlines(True),fromfile='a/upstream/ouroboros/Game/src/render/tex.c',tofile='b/upstream/ouroboros/Game/src/render/tex.c'))
 if (HERE/'texname-guard-original.patch').read_text()!=expected_patch:raise ValueError('Exact isolated original source diff differs')
 strict_receipt=HERE/'qualification/client-texname-strict-20261017/host.json'
 if sha(strict_receipt)!='a2b3c7a162f5e79b00e1f43549e4c0f0555aaefc8563195cc34880ceaf36d2bf':raise ValueError('Exact strict baseline receipt differs')
 strict=json.loads(strict_receipt.read_text())
 if strict['passed'] is not True or any(sha(ROOT/path)!=h for path,h in strict['source_sha256'].items()):raise ValueError('Strict default source baseline changed')
 try:repair.patch(parts[0]+' ')
 except ValueError:pass
 else:raise ValueError('Candidate source mutation not refused')
 fixture=json.loads((HERE/'texname-fixtures.json').read_text());report=ROOT/fixture['report_path']
 if sha(report)!=fixture['report_sha256']:raise ValueError('Exact captured source report differs')
 j=json.loads(report.read_text());names=sorted({p[2] for f in j['files'] for m in f['models'] for o in m['source_observations'] for p in o['texture_partitions']})
 if len(names)!=1769:raise ValueError('Captured source count differs')
 names+=fixture['qualified_manifest_examples']
 deps=[HERE/'coh_wr_texname.c',HERE/'coh_wr_texname.h',HERE/'coh_wr_texname_guarded.c',HERE/'coh_wr_texname_guarded.h',HERE/'texname_guard_candidate.py',HERE/'texname-guard-original.patch',HERE/'tests/test_texname_guarded.c',HERE/'check_texname_guarded.py',HERE/'check_texname.py',HERE/'texname-source-pins.json',HERE/'texname-fixtures.json',HERE.parent/'coh_contracts.h',report,strict_receipt,*[ROOT/x for x in pins],*[ROOT/x for x in fixture['manifest_example_proof_paths']]]
 hashes={str(x.relative_to(ROOT)):sha(x) for x in deps};results={}
 with tempfile.TemporaryDirectory(prefix='coh-texname-guarded-') as directory:
  t=Path(directory);(t/'original.c').write_text(original.oracle(parts)+'\nint original_fix_direct(const char*s,char*out,int inplace){if(inplace){strcpy(out,s);return texFixName(out,out,-1);}return texFixName(s,out,128); }\n');(t/'guarded-original.c').write_text('#define texLoad guarded_source_texLoad\n#define texFindComposite guarded_source_texFindComposite\n#define texCheckForSceneMaterialSwap guarded_source_sceneMaterialSwap\n#define original_texname guarded_original_texname\n'+original.oracle(fixed)+'\nint guarded_fix_direct(const char*s,char*out,int inplace){if(inplace){strcpy(out,s);return texFixName(out,out,-1);}return texFixName(s,out,128); }\n')
  (t/'texname_fixture.h').write_text('#define TEXNAME_FIXTURE_COUNT '+str(len(names))+'u\n#define TEXNAME_CAPTURED_COUNT 1769u\nstatic const char*texname_fixture[]={'+','.join(json.dumps(x) for x in names)+'};\n')
  flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-I',HERE,'-I',t]
  for mode,extra in [('release',['-O2']),('address',['-O1','-fsanitize=address','-no-pie']),('undefined',['-O1','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
   original.run(['cc',*flags,*extra,HERE/'tests/test_texname_guarded.c',HERE/'coh_wr_texname.c',HERE/'coh_wr_texname_guarded.c',t/'original.c',t/'guarded-original.c','-o',t/mode]);results[mode]=json.loads(original.run([t/mode],env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')))
  src=(HERE/'coh_wr_texname_guarded.c').read_text();before="else if(n>=8&&name[n-8]=='.')";assert before in src;(t/'mutation.c').write_text(src.replace(before,"else if(n<8)return COH_UNSUPPORTED;else if(name[n-8]=='.')"))
  original.run(['cc',*flags,'-O2',HERE/'tests/test_texname_guarded.c',HERE/'coh_wr_texname.c',t/'mutation.c',t/'original.c',t/'guarded-original.c','-o',t/'mutation']);r=subprocess.run([str(t/'mutation')],capture_output=True,timeout=60)
  if not r.returncode:raise ValueError('Guarded policy regression mutation escaped')
 if hashes!={str(x.relative_to(ROOT)):sha(x) for x in deps}:raise ValueError('Source changed')
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps({'passed':True,'source_revision':original.run(['git','-C',ROOT,'rev-parse','HEAD']).decode().strip(),'source_inputs_unchanged':True,'source_sha256':hashes,'isolated_original_source_correction':correction,'modes':results,'native_guard_regression_mutation_rejected':True,'strict_default_unchanged':True,'asset_generation_permit':False,'material_authority':False,'world_authority':False,'android_execution':False},indent=2)+'\n');print(json.dumps({'passed':True,'modes':results}))
if __name__=='__main__':main()
