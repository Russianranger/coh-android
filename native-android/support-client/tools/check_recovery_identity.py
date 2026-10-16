#!/usr/bin/env python3
"""Negative controls for immutable artifact recovery; never mutates source/APKs."""
import argparse, copy, hashlib, json, sys, tempfile
from pathlib import Path
from verify_qualified_artifact import source_audit
from emulator_check import verify_report_identity

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--artifact-dir',type=Path,required=True)
p.add_argument('--source-root',type=Path,default=Path('.'))
p.add_argument('--pins',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();r=json.loads((a.artifact_dir/'build-receipt.json').read_text());pins=json.loads(a.pins.read_text())
report=json.loads((a.artifact_dir/'emulator-final-report.json').read_text());apk=pins['apks']['x86_64']
verify_report_identity(report,r,apk)
checks=[]
for field,bad in [('package','org.coh.nativecombined'),('version_name','0.1.0-support-batch'),('version_code',1),('installed_apk.sha256','0'*64),('installed_apk.bytes',apk['bytes']+1)]:
 mutated=copy.deepcopy(report);owner=mutated['app'];parts=field.split('.')
 for k in parts[:-1]:owner=owner[k]
 owner[parts[-1]]=bad
 try:verify_report_identity(mutated,r,apk)
 except ValueError:checks.append({'case':'wrong_report_'+field,'rejected':True})
 else:raise AssertionError('Admitted '+field)
# The compiler-recorded header digest must be checked even when that file was
# already visited through the C/quoted-header source closure.
mutated=copy.deepcopy(r)
item=next(x for x in mutated['artifacts'][0]['native']['compiled_inputs'] if x['file']=='native-android/engine/ui/coh_hud.h')
item['sha256']='0'*64
try:source_audit(a.source_root.resolve(),mutated,pins)
except ValueError:checks.append({'case':'tampered_compiler_recorded_header','rejected':True})
else:raise AssertionError('Admitted altered compiler header digest')
result={'schema':'coh-support-recovery-negative-v1','passed':True,'qualified_source_commit':pins['qualified_source_commit'],'tests':checks,'runtime_files_modified':False,'android_build_performed':False,'emulator_run_performed':False,'physical_acceptance':False}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'negative_controls':len(checks)}))
