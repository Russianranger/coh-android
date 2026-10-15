#!/usr/bin/env python3
"""Run the actual UI controller ownership policy on host Java."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[3]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source-root',type=Path,default=ROOT)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();root=a.source_root.resolve()
paths=[root/'native-android/support-client/java/org/coh/sessionclient/SupportControllerNavigation.java',
       root/'native-android/support-client/tools/tests/ControllerNavigationTest.java']
with tempfile.TemporaryDirectory(prefix='coh-ui-controller-') as temporary:
    subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','-d',temporary,*map(str,paths)],check=True,capture_output=True)
    result=subprocess.run(['java','-cp',temporary,'org.coh.sessionclient.ControllerNavigationTest'],check=True,capture_output=True,text=True)
report=json.loads(result.stdout)
report['inputs']=[{'file':str(f.relative_to(root)),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in paths]
report['android_execution']=False
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
print(result.stdout.strip())
