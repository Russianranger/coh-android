"""Bounded post-exit job observation; strict query guards remain immediate."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

BASE_PROFILE_SHA256='ad25eb3dc6202df2bf4b1a271770e3c6555796c32174a083f90568af4a3c5b6b'
OLD='   Need(JobIsEmpty(),Cause.JOB);resultPin.Same();'
NEW=('   Stopwatch drain=Stopwatch.StartNew();bool drained=false;\n'
     '   do {drained=JobIsEmpty();if(drained)break;Thread.Sleep(20);}\n'
     '   while(drain.ElapsedMilliseconds<10000);\n'
     '   Need(drained,Cause.JOB);\n'
     '   resultPin.Same();')


def source_bytes():
    path=Path(__file__).with_name('prepare_profile_diagnostic.py')
    spec=importlib.util.spec_from_file_location('job_drain_profile_predecessor',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.prepare(module.source_bytes())


def prepare(original):
    if hashlib.sha256(original).hexdigest()!=BASE_PROFILE_SHA256:
        raise ValueError('PROFILE_SOURCE_REFUSED')
    source=original.decode('utf-8')
    if source.count(OLD)!=1:raise ValueError('DRAIN_INSERTION_REFUSED')
    source=source.replace(OLD,NEW,1)
    if source.count(NEW)!=1 or source.replace(NEW,OLD,1).encode()!=original:
        raise ValueError('PROFILE_REVERSAL_REFUSED')
    return source.encode('utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir',type=Path,required=True);args=parser.parse_args()
    generated=prepare(source_bytes());args.out_dir.mkdir(exist_ok=False)
    (args.out_dir/'OwnedProfileProcessJobDrain.cs').write_bytes(generated)
    receipt=dict(schema='coh-wpp-job-drain-preparation-v1',passed=True,
                 profile_source_sha256=BASE_PROFILE_SHA256,
                 generated_source_sha256=hashlib.sha256(generated).hexdigest(),
                 generated_source_bytes=len(generated),replacements=1,
                 exact_reverse_verified=True,bounded_job_drain_repair=True,
                 existing_owner_acl_identity_guards_preserved=True,
                 compiler_or_helper_or_model_executed=False)
    (args.out_dir/'preparation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,separators=(',',':')))


if __name__=='__main__':main()
