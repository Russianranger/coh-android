#!/usr/bin/env python3
"""Independent power-range CRC/F32 wire event ordering and atomic refusal review."""
import argparse, hashlib, json, os, subprocess, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
PINS = {'native-android/engine/entities/coh_power_ranges.c': 'a8bb63c3ec0d5e899baab5f4d7c85f76e985b13f0fefe78d0266e21770fcf5b7', 'native-android/engine/entities/coh_power_ranges.h': '199d35f40a3eac1d8882d088006bfae7c1335bf8a88721f353f202e7af081b80', 'native-android/engine/replication/coh_replication.c': '9633724aeba77533516ea32405ea594379d95ce70a362a9023b3a57ec8f90dd4', 'native-android/engine/replication/coh_replication.h': '85817eedf8d3ce2e887037b48f16c13f8b305adae9701a717e82944e3694e84b', 'native-android/engine/character-data/coh_character_data.h': '20b88adebd62b984c12108b50a3ad0d0868cce04aaa5602d8dd2e324ba6ca5e0', 'native-android/engine/coh_contracts.h': '2a43032fc97c7aa7042224431a4b90f1ec3d27566bed7ff2fe9070e72cb37832', 'native-android/include/coh_native_core.h': '48c4e1fcbe4380778066aa1257159503883773e3b7e250fafcc61abc28818106'}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): parser.error('New receipt path required')
    before = {name: sha(args.source_root/name) for name in PINS}
    if before != PINS: raise ValueError('Reviewed production source differs')
    source = HERE/'ranges-review.c'; source_pin = sha(source)
    entities = args.source_root/'native-android/engine/entities'; outcomes = {}
    with tempfile.TemporaryDirectory(prefix='coh-ranges-independent-') as tmp:
        for mode, flags in [('release',['-O2']),('asan',['-O1','-g','-fsanitize=address','-no-pie']),('ubsan',['-O1','-g','-fsanitize=undefined','-fno-sanitize-recover=all'])]:
            binary = Path(tmp)/mode
            subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-pedantic',*flags,'-I'+str(entities),str(source),str(entities/'coh_power_ranges.c'),str(entities/'../replication/coh_replication.c'),'-lm','-o',str(binary)],check=True,timeout=60)
            run = subprocess.run([str(binary)],check=True,capture_output=True,text=True,timeout=60,env=dict(os.environ,ASAN_OPTIONS='detect_leaks=0:halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))
            outcomes[mode] = {'result':json.loads(run.stdout),'binary_sha256':sha(binary)}
    if before != {name:sha(args.source_root/name) for name in PINS} or source_pin != sha(source): raise ValueError('Reviewed source changed during checks')
    receipt = {'reviewed_commit':'aeb74ba7193f3aa4a3c438cfacfd1185d00a8fa3','source_sha256':PINS,'review_harness_sha256':source_pin,'review_driver_sha256':sha(Path(__file__)),'passed':True,'source_stable':True,'modes':outcomes,'android_executed':False,'actor_publication':False,'acknowledgments_enabled':False}
    args.output.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'passed':True,'modes':outcomes}))
if __name__ == '__main__': main()
