"""Fresh inherited source staging and exact closure refusal; no compiler."""
from pathlib import Path
from types import SimpleNamespace
import argparse
import hashlib
import json
import sys
import tempfile
import time
import prepare_live_native_source as live


def qualify(repository,output):
    root=Path(repository).resolve()
    output=Path(output)
    live.require(not output.exists() and not output.is_symlink(),'Existing source-stage evidence preserved')
    retained,_=live._retained(root)
    begin=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='coh-live-source-stage-') as temporary:
        staging=Path(temporary)/'source'
        retained.stage(SimpleNamespace(output=staging))
        old={str(p.relative_to(staging)):p.read_bytes() for p in staging.glob('*build-input*.json')}
        result=live.stage(staging,root)
        live.require(all((staging/name).read_bytes()==raw for name,raw in old.items()),'Old native source receipt changed')
        live.require(result==live.validate_staged_source(staging,root),'Fresh source closure differs')
        target=staging/'Game/src/game.c'
        target.write_bytes(target.read_bytes()+b'\n/* unexpected source mutation */\n')
        try:
            live.validate_staged_source(staging,root)
        except ValueError as error:
            refusal=str(error)
        else:
            raise ValueError('Mutated effective source accepted')
    value={'format':1,'role':'fresh_retained_live_source_staging_control','status':'passed',
           'seconds':time.monotonic()-begin,'exact_validated_source':result,
           'old_raw_receipts_sha256':{n:hashlib.sha256(v).hexdigest() for n,v in old.items()},
           'mutation_refusal':refusal,'native_SDK_executed':False,'native_Game_executed':False,
           'Android_runtime_executed':False,'publication_allowed':False}
    with output.open('x') as stream:
        json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n')
    return value


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    value=qualify(args.repository,args.output)
    print(json.dumps({'status':value['status'],'seconds':value['seconds'],
                      'effective_source_pins':len(value['exact_validated_source']['validated_sources_sha256']),
                      'old_raw_receipts':len(value['old_raw_receipts_sha256']),'mutation_refusal':value['mutation_refusal']}))
