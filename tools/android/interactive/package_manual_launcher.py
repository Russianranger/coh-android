"""Build only the .35 manual client launcher using its retained MinGW recipe."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import manual_launcher_contract as contract


def build(args):
    root = contract.ROOT
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    contract.require(head==args.repository_commit and re.fullmatch('[0-9a-f]{40}',head), 'Exact helper source commit required')
    subprocess.run(['git','diff','--quiet','HEAD','--'],cwd=root,check=True)
    pins=contract.source_pins(root)
    for name in pins:
        actual=subprocess.check_output(['git','show',head+':'+name],cwd=root)
        contract.require(contract.pin(actual)==pins[name], 'Native helper source must be committed: '+name)
    run_id=os.environ.get('GITHUB_RUN_ID','')
    contract.require(re.fullmatch('[1-9][0-9]*',run_id), 'Native helper owner run required')
    contract.require(not args.output.exists() and not args.output.is_symlink(), 'Fresh native helper destination required')
    args.output.mkdir(parents=True)
    executable=args.output/contract.EXE_NAME
    compiler_version=subprocess.check_output([args.cc,'--version'],text=True)
    subprocess.run([args.cc,*contract.COMPILE_FLAGS,str(root/contract.SOURCE),*contract.LINK_FLAGS,
        '-o',str(executable)],check=True,timeout=120)
    dump=subprocess.check_output([args.objdump,'-p',str(executable)],text=True,timeout=30)
    dlls={name.lower()for name in re.findall(r'DLL Name:\s*(\S+)',dump)}
    contract.require(dlls==contract.DLLS,'Unexpected launcher native dependencies')
    receipt={'format':1,'status':'built','role':contract.ROLE,'repository_commit':head,
        'run_id':int(run_id),'run_url':'https://github.com/Russianranger/coh-android/actions/runs/'+run_id,
        'source_files':pins,'compiler':'i686-w64-mingw32-gcc','compiler_version':compiler_version,
        'compile_flags':list(contract.COMPILE_FLAGS),'link_flags':list(contract.LINK_FLAGS),
        'windows_libraries':sorted(dlls),'executable':contract.file_pin(executable),
        'previous_helper':contract.DONOR_HELPER,'game_db_map_recompiled':False,
        'native_fixture_executed':False,'physical_ayn_thor_validated':False}
    contract.validate_build(receipt,executable,head)
    (args.output/contract.MANIFEST_NAME).write_bytes(contract.encoded(receipt))
    print('Built current source-bound native helper:',receipt['executable']['sha256'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository-commit',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cc',default='i686-w64-mingw32-gcc')
    parser.add_argument('--objdump',default='i686-w64-mingw32-objdump')
    build(parser.parse_args())
