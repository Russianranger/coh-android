#!/usr/bin/env python3
"""Bounded native replay envelope validation and atomic private Java storage."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'native-android/combined-client/app/src/main/java/org/coh/nativecombined/InitialReplayStore.java'
TEST = Path(__file__).with_name('TestInitialReplayStore.java')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    activity=JAVA.with_name('NativeClientActivity.java');launcher=JAVA.with_name('MainActivity.java')
    inputs = [Path(__file__).resolve(), JAVA, TEST, activity, launcher]
    pins = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    # These are wiring assertions, separate from the executable Java storage
    # controls below; no Android JNI or device lifecycle execution is claimed.
    text=activity.read_text();main=launcher.read_text()
    for method,operation in [('disconnectNetwork','disconnect'),('suspendNetwork','suspend')]:
        begin=text.index('    private void '+method+'()');end=text.index('\n    private ',begin+10)
        body=text[begin:end]
        assert body.index('saveInitialReplay();')<body.index('InteropNative.'+operation+'(')
    assert 'retireNetworkOwner();networkMode=mode;charactersPublished=false;' in text
    assert text.index('InitialReplayStore.clear(getFilesDir())')<text.index('networkHandle=mode==NetworkMode.WORLD_HANDOFF')
    assert text.count('InteropNative.exportInitialReplay(')==1
    save=text[text.index('    private void saveInitialReplay(){'):text.index('    private void publishNetwork()')]
    assert 'BuildConfig.FRAME_CAPTURE_DIAGNOSTIC' in save and 'initialReplayStorageReady' in save
    assert save.index('handoffState.initialObserved()')<save.index('InteropNative.exportInitialReplay(')
    assert 'finally{if(raw!=null)java.util.Arrays.fill(raw,(byte)0);}' in save
    assert 'InitialReplayStore.append(getFilesDir(),zip,replaySha)' in main
    assert 'replay.optString("activity_session").equals(report.optString("session_id"))' in main
    assert 'replay.optLong("app_version",-1)==app.optLong("version_code",-2)' in main
    assert 'replaySha=replay.optString("sha256")' in main
    compile_result = subprocess.run(['java', '-Xmx128m', 'com.sun.tools.javac.Main', '--release', '8', '-Xlint:all', '-Werror', '-d', str(work), str(JAVA), str(TEST)], capture_output=True, text=True)
    (work / 'compile.log').write_text(compile_result.stdout + compile_result.stderr)
    if compile_result.returncode:
        raise RuntimeError('Java replay store compile failed; see ' + str(work / 'compile.log'))
    execution = subprocess.run(['java', '-Xmx64m', '-cp', str(work), 'org.coh.nativecombined.TestInitialReplayStore', str(work)], capture_output=True, text=True, timeout=30)
    (work / 'run.log').write_text(execution.stdout + execution.stderr)
    if execution.returncode:
        raise RuntimeError('Java replay store test failed; see ' + str(work / 'run.log'))
    result = {'passed': True, 'inputs_sha256': pins, 'host': json.loads(execution.stdout), 'scope': 'Java framing/hash/bounds/atomic replacement/symlink/report-bound ZIP controls plus source assertions for serialized Activity wiring; no device execution or physical packet replay.'}
    assert pins == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'passed': True, 'host': result['host']}))


if __name__ == '__main__':
    main()
