#!/usr/bin/env python3
"""Independent prefix byte alignment, rollback and partial-alias review."""
import argparse, hashlib, json, os, subprocess, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
PINS = {
 'native-android/engine/entities/coh_character_prefix.c': 'd0c5870795c349be967b1d79b088a47c4718fcdad4c86e24ee9837e08087d78e',
 'native-android/engine/entities/coh_character_prefix.h': '7416d5cfca7a5e8bbf6f25443b9ddc592df6fc9252c29810ec52a311c7352b3d',
 'native-android/engine/replication/coh_replication.c': '9633724aeba77533516ea32405ea594379d95ce70a362a9023b3a57ec8f90dd4',
}
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error('New receipt path required')
    before = {name: sha(args.source_root/name) for name in PINS}
    if before != PINS: raise ValueError('Reviewed production source differs')
    source = HERE/'prefix-review.c'; source_pin = sha(source)
    entities = args.source_root/'native-android/engine/entities'; outcomes = {}
    with tempfile.TemporaryDirectory(prefix='coh-prefix-independent-') as tmp:
        for mode, flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
            binary = Path(tmp)/mode
            subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(entities),str(source),str(entities/'coh_character_prefix.c'),str(entities/'../replication/coh_replication.c'),'-lm','-o',str(binary)],check=True,timeout=60)
            run = subprocess.run([str(binary)],check=True,capture_output=True,text=True,timeout=60,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
            outcomes[mode] = {'result':json.loads(run.stdout),'binary_sha256':sha(binary)}
    if before != {name:sha(args.source_root/name) for name in PINS} or source_pin != sha(source): raise ValueError('Reviewed source changed during checks')
    receipt = {'reviewed_commit':'18b84506ec4a0ae02c7617ac8116b3a77e41e9fa','source_sha256':PINS,'review_harness_sha256':source_pin,'review_driver_sha256':sha(Path(__file__)),'passed':True,'source_stable':True,'modes':outcomes,'android_executed':False,'actor_publication':False,'acknowledgments_enabled':False}
    args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'passed':True,'modes':outcomes}))
if __name__ == '__main__': main()
