#!/usr/bin/env python3
"""Execute the shipped reuse selector against independently created Git histories."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    path=Path(__file__).with_name('reuse_qualified_package.py')
    spec=importlib.util.spec_from_file_location('shipped_package_reuse_guard',path)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    checks=0
    def check(value,label):
        nonlocal checks
        checks+=1
        assert value,label
    with tempfile.TemporaryDirectory(prefix='coh-reuse-guard-') as directory:
        root=Path(directory)
        def git(*arguments):
            return subprocess.run(['git',*arguments],cwd=root,check=True,capture_output=True,timeout=30).stdout.decode().strip()
        def write(name,text='independent literal fixture\n'):
            file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text)
        def commit():
            git('add','-A');git('-c','user.name=Reuse guard test','-c','user.email=guard@example.invalid','commit','--allow-empty','-m','independent guard fixture')
            return git('rev-parse','HEAD')
        git('init','-q')
        write('README.md');write('native-android/session-client/app/src/main/cpp/session_renderer.c','runtime fixture\n')
        base=commit()
        check(helper.guard(root,base,base)['eligible'] is True,'Unchanged runtime tree may reuse exact bytes')
        for name in ['native-android/session-client/tools/emulator_check.py','native-android/session-client/tools/tap_host_check.py',
                     '.github/workflows/native-session-client.yml','native-android/evidence/phases16-18/third-ui-failure.json',
                     'native-android/PHASES16-18.md','native-android/session-client/THOR-TEST.md']:
            git('reset','--hard',base);git('clean','-fdq');write(name);head=commit()
            check(helper.guard(root,base,head)['eligible'] is True,'Allow explicit non-runtime path '+name)
        for name in ['native-android/session-client/app/src/main/cpp/session_renderer.c',
                     'native-android/session-client/app/src/main/java/org/coh/sessionclient/MainActivity.java',
                     'native-android/session-client/app/build.gradle','native-android/session-client/app/src/main/assets/world.bin',
                     'native-android/animation/coh_animation.c','native-android/world-probe/shaders/world.vert',
                     'native-android/tools/locomotion_fixture/prepare.py','native-android/session-client/tools/lifecycle_host_check.py',
                     'native-android/evidence/phases16-18-other/runtime.c']:
            git('reset','--hard',base);git('clean','-fdq');write(name,'changed runtime or unapproved dependency\n');head=commit()
            check(helper.guard(root,base,head)['eligible'] is False,'Reject runtime/build/asset/oracle/dependency '+name)
        git('reset','--hard',base);git('clean','-fdq')
        (root/'README.md').unlink();(root/'README.md').symlink_to('native-android/session-client/app/src/main/cpp/session_renderer.c');head=commit()
        check(helper.guard(root,base,head)['eligible'] is False,'Whitelisted symlink mode changes cannot reuse')
        git('reset','--hard',base);git('clean','-fdq')
        git('update-index','--add','--cacheinfo','160000,'+base+',native-android/evidence/phases16-18/submodule')
        git('-c','user.name=Reuse guard test','-c','user.email=guard@example.invalid','commit','-m','gitlink control');head=git('rev-parse','HEAD')
        check(helper.guard(root,base,head)['eligible'] is False,'Even evidence-prefix gitlink changes cannot reuse')
        check(helper.guard(root,'0'*40,head)['eligible'] is False,'Unavailable base fails closed')
        check(helper.guard(root,base,'HEAD')['eligible'] is False,'Symbolic HEAD cannot substitute for exact provenance')
        check(helper.guard(root,head,base)['eligible'] is False,'Non-ancestor runtime baseline fails closed')
    receipt={'schema':1,'passed':True,'checks':checks,
             'scope':'Actual shipped fail-closed reuse guard over independent temporary Git histories; no artifact download or device acceptance',
             'guard_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()
