#!/usr/bin/env python3
"""Only optimized-Python entry refusals; no donor, project import or compiler."""
import argparse,ast,gzip,hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BASE='662d05a1527a0bfe6c8a17c4474d19be84d8ba40'
def need(ok,why):
 if not ok:raise ValueError(why)
def sha(b):return hashlib.sha256(b).hexdigest()
def git(revision,p):return subprocess.check_output(['git','-C',ROOT,'show',revision+':'+str(p.relative_to(ROOT))])
def main():
 need(__debug__,'Python optimization unsupported')
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True,type=Path);a=ap.parse_args();need(not a.output.exists(),'new output required')
 revision=subprocess.check_output(['git','-C',ROOT,'rev-parse','HEAD'],text=True).strip();target=HERE/'check_proficiencies.py';own=Path(__file__).resolve();receipt=HERE/'qualification/proficiencies-662d05a15.json.gz';b=receipt.read_bytes();need(sha(b)=='2b7fafc66cc64ec529478f96188af387cc08cb782b118611a3f9aa21681ffcf9','historical proof')
 proof=json.loads(gzip.decompress(b));frozen={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (target,own,receipt)}
 for p,d in frozen.items():need(sha(git(revision,ROOT/p))==d,'committed source required')
 old=git(BASE,target);new=target.read_bytes();need(proof['source_sha256'][str(target.relative_to(ROOT))]==sha(old),'historical checker')
 before=ast.parse(old);after=ast.parse(new);body=next(x for x in after.body if isinstance(x,ast.FunctionDef) and x.name=='main').body
 expected=ast.parse("if not __debug__:raise ValueError('Python optimization unsupported')").body[0];need(ast.dump(body[0])==ast.dump(expected),'fixed first main guard');del body[0];need(ast.dump(before)==ast.dump(after),'only main-entry guard AST change')
 unchanged={p:d for p,d in proof['source_sha256'].items() if p!=str(target.relative_to(ROOT))}
 for p,d in unchanged.items():need(sha((ROOT/p).read_bytes())==d and sha(git(revision,ROOT/p))==d,'unchanged historical native/oracle source')
 results=[]
 with tempfile.TemporaryDirectory(prefix='proficiency-guard-') as temp:
  work=Path(temp)
  for name,flags,env in [('O',['-O'],{}),('OO',['-OO'],{}),('environment',[],{'PYTHONOPTIMIZE':'1'})]:
   output=work/(name+'.json.gz');donor=work/'DONOR_MUST_NOT_BE_OPENED.zip';p=subprocess.run([sys.executable,*flags,str(target),'--actual-caches-zip',str(donor),'--output',str(output)],env=dict(os.environ,**env),capture_output=True,timeout=10)
   need(p.returncode!=0 and not p.stdout and b'Python optimization unsupported' in p.stderr and b'FileNotFoundError' not in p.stderr,'optimized execution must stop at guard');need(not output.exists() and not donor.exists() and not list(work.iterdir()),'no fixture/output work');results.append({'mode':name,'returncode':p.returncode,'empty_stdout':True,'fixed_guard_refusal':True,'no_file_created':True})
 need(subprocess.check_output(['git','-C',ROOT,'rev-parse','HEAD'],text=True).strip()==revision,'HEAD changed')
 for p,d in frozen.items():need(sha((ROOT/p).read_bytes())==d,'source changed')
 result={'schema':'coh-proficiencies-python-entry-guard-followup-v1','passed':True,'source_revision':revision,'source_sha256':frozen,'historical_qualification':{'source_revision':BASE,'gzip_sha256':sha(b),'checks_each':55193,'modes':['release','asan','ubsan'],'unchanged_source_sha256':unchanged},'checker_transition':{'path':str(target.relative_to(ROOT)),'previous_sha256':sha(old),'sha256':sha(new),'only_AST_change':'first main entry unconditional non-assert __debug__ refusal'},'optimized_controls':results,'native_recompiled':False,'native_tests_reexecuted':False,'project_helpers_imported':False,'donor_opened':False,'services_or_sockets_executed':False,'runtime_generation':False,'actor_authority':False}
 with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
 print(json.dumps({'passed':True,'optimized_controls':len(results),'unchanged_historical_sources':len(unchanged),'native_reexecuted':False}))
if __name__=='__main__':main()
