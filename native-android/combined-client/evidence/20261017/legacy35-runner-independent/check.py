#!/usr/bin/env python3
"""Read-only frozen runner guard controls; never executes retained binaries."""
from pathlib import Path
import argparse,hashlib,io,json,struct,subprocess,zipfile
REV='da80e73ae315363ffcbc08ff1ef86e7290c4eefc'
SCRIPT='native-android/combined-client/tools/run_retained_legacy35.py'
WORKFLOW='.github/workflows/native-retained-legacy35.yml'
p=argparse.ArgumentParser();p.add_argument('--repository',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
def raw(path):return subprocess.check_output(['git','--no-replace-objects','-C',a.repository,'show',REV+':'+path])
source=raw(SCRIPT);scope={'__name__':'reviewed_runner_guard','__file__':str(a.repository/SCRIPT)};exec(compile(source,SCRIPT,'exec'),scope)
base=scope['BASE'];archive=raw(base+'all35-original-source-diagnostics.zip');assert hashlib.sha256(archive).hexdigest()==scope['ARCHIVE_SHA']
with zipfile.ZipFile(io.BytesIO(archive))as z:binary=z.read('0/original-read-model')
validate=scope['validate_elf'];validate(binary);controls=['exact_retained_elf_admitted_without_execution']
def refuse(name,data):
 try:validate(data)
 except ValueError:controls.append(name)
 else:raise AssertionError(name)
refuse('short_header',binary[:51]);x=bytearray(binary);x[4]=2;refuse('elf64',x);x=bytearray(binary);struct.pack_into('<H',x,18,62);refuse('wrong_machine',x)
x=bytearray(binary);ph=struct.unpack_from('<I',x,28)[0];struct.pack_into('<I',x,ph,3);refuse('dynamic_interpreter',x)
x=bytearray(binary);struct.pack_into('<I',x,28,len(x)-1);refuse('program_header_extent',x)
x=bytearray(binary);struct.pack_into('<8I',x,ph,1,len(x),0,0,1,1,0,0);refuse('load_file_extent',x)
try:scope['require'](False,'case domain')
except ValueError:controls.append('failed_domain_guard')
else:raise AssertionError('domain guard')
w=raw(WORKFLOW)
for text in [b'branches: [native-android]',b'[retained-legacy35-check]',b'contents: read',b'cancel-in-progress: false',b'persist-credentials: false',b'if: always()',b'--expected-commit "$GITHUB_SHA"']:assert text in w
assert w.count(b'runs-on:')==1 and b'--validate-only'not in w
sha=lambda b:hashlib.sha256(b).hexdigest()
a.output.write_text(json.dumps({'approved':True,'historical_source_commit':REV,'script_sha256':sha(source),'workflow_sha256':sha(w),'archive_sha256':sha(archive),'controls':controls,'source_review':['Fixed35 version2/3/4 metadata binaries only; no compiler/assets/server/NDK','ExactGit/325members/615638bytes/source/binary/220byte expected facts binding before execution','ELF class/data/machine/EXEC/nointerp/load extents guarded','Per-case subprocess timeout and CPU/AS/file/FD/core limits, emptyenv, temporary executable cleanup','Zeroexit+empty stderr+wholestdout exact equality required; validation_only never sets execution flags','Source/head clean and inputhashes rechecked; always artifact preserves partial refusal'],'binary_executed_by_review':False,'compile_or_service_started':False,'original32_future_execution_not_yet_qualified_here':True},indent=2)+'\n');print(len(controls))
