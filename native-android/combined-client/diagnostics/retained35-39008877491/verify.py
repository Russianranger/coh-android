#!/usr/bin/env python3
"""Independently admit retained original32 result bytes; never execute binaries."""
import collections,hashlib,io,json,subprocess,zipfile
from pathlib import Path
PIN='365bc28e0433112e2292e44f6338da9fbc5c270e'
BASE='native-android/engine/world-render-adapter/qualification/rigid-v234-20261017/'
ZIP_SHA='a3254d830cb02378cf115ce94b3416578f6cce6662e4abcd01c42d31e5215b0d'
RECEIPT_SHA='0e18fb1bafe86a2030922394e025337675fc90a8be6e2ae3e2c307d16e435a4b'
def sha(b):return hashlib.sha256(b).hexdigest()
def require(ok,why):
 if not ok:raise ValueError(why)
def admit(root,artifact):
 require(len(artifact)==19183 and sha(artifact)==ZIP_SHA,'actual artifact identity')
 git=lambda path:subprocess.check_output(['git','--no-replace-objects','-C',str(root),'show',PIN+':'+path])
 with zipfile.ZipFile(io.BytesIO(artifact))as z:
  names=z.namelist();expected={'receipt.json'}|{'case-%02d-%s.bin'%(i,k)for i in range(35)for k in ('stdout','stderr')}
  require(len(names)==71 and set(names)==expected and z.testzip()is None,'complete actual artifact members/CRC')
  receipt=z.read('receipt.json');require(sha(receipt)==RECEIPT_SHA,'actual receipt identity');d=json.loads(receipt)
  require(d['passed']is True and d['source_revision']==PIN and d['validation_only']is False and d['source_inputs_unchanged']is True,'actual execution/source flags')
  for key in ('android_executed','apk_rebuilt','compiler_executed','live_world','material_authority','server_executed','thor_accepted'):require(d[key]is False,'qualification scope')
  required={BASE+n for n in ('all35-host.json','all35-original-source-checksums.json','all35-original-source-diagnostics.zip')}|{'native-android/combined-client/tools/run_retained_legacy35.py'}
  require(set(d['source_sha256'])==required,'complete four-source domain')
  inputs={n:git(n)for n in required}
  require(all(sha(v)==d['source_sha256'][n]for n,v in inputs.items()),'source Git bytes')
  host=json.loads(inputs[BASE+'all35-host.json']);pins=json.loads(inputs[BASE+'all35-original-source-checksums.json']);raw=inputs[BASE+'all35-original-source-diagnostics.zip']
  require(host['passed']is True and len(host['cases'])==35 and len(raw)==615638 and sha(raw)==d['archive_sha256']==pins['zip_sha256'],'retained fixture archive binding')
  with zipfile.ZipFile(io.BytesIO(raw))as fixtures:
   require(len(fixtures.infolist())==len(pins['files'])==325 and set(fixtures.namelist())==set(pins['files']) and fixtures.testzip()is None,'retained complete fixture domain')
   for n,v in pins['files'].items():
    b=fixtures.read(n);require(len(b)==v['bytes']and sha(b)==v['sha256'],'retained fixture member')
   require(len(d['cases'])==35 and [c['index']for c in d['cases']]==list(range(35)),'unique ordered actual cases')
   for i,(case,original)in enumerate(zip(d['cases'],host['cases'])):
    fact=original['original_readModel'];fixture=original['fixture'];prefix=str(i)+'/'
    source=fixtures.read(prefix+'original-read-model.c');binary=fixtures.read(prefix+'original-read-model');expected=fixtures.read(prefix+'expected-facts.bin');stdout=z.read('case-%02d-stdout.bin'%i);stderr=z.read('case-%02d-stderr.bin'%i)
    require(binary[:6]==b'\x7fELF\x01\x01' and len(expected)==220,'retained ELF32/55word extent')
    require(case['version']==fixture['version'] and case['model']==fixture['model'] and case['row']==fixture['disk_row']and case['body_sha256']==fixture['sha256'],'actual fixture identity')
    require(case['binary_sha256']==sha(binary)==fact['binary_sha256']and case['oracle_source_sha256']==sha(source)==fact['generated_oracle_sha256'],'compiled witness source/binary binding')
    require(case['original32_executed']is True and case['facts_equal']is True and case['words']==55 and not stderr and stdout==expected and sha(stdout)==case['stdout_sha256']==case['expected_stdout_sha256']==fact['expected_facts_sha256'],'actual stdout expected55facts')
  counts=dict(collections.Counter(c['version']for c in d['cases']));require(counts=={2:21,3:2,4:12},'qualified format case counts')
 return {'passed':True,'run':39008877491,'artifact':12091812003,'artifact_bytes':len(artifact),'artifact_sha256':sha(artifact),'receipt_sha256':sha(receipt),'source_revision':PIN,'source_inputs_verified':4,'retained_members_verified':325,'actual_cases':35,'versions':counts,'stdout_bytes_each':220,'all_stderr_empty':True,'all_expected55facts_equal':True,'binary_reexecuted_by_verifier':False,'compiler_executed':False,'Win32_engine_executed':False,'android_executed':False,'live_world':False}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--artifact',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=admit(a.source_root,a.artifact.read_bytes());a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
