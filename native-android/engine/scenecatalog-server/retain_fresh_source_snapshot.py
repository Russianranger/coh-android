#!/usr/bin/env python3
"""Retain four exact source bodies only for an admitted fresh graphical fixture.

Generic private captures/backups never qualify. The complete live source
admission is repeated against the same cleaned inputs before any public copy.
No packet, owner, envelope header, eligibility, private receipt or log is exported.
"""
from __future__ import annotations
import argparse,json,os,subprocess,sys,time
from pathlib import Path
import admit_source_snapshot as admit

d=admit.d;HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
PAYLOADS={'catalog.cohcat':32*1024**2,'runtime.cohrts':16*1024**2,
          'resources.cohres':32*1024**2,'public-bounds.cohrbw':32*1024**2}
PATH_ARGUMENTS=('private-output','private-work','fixture-directory','runtime','control-fixture',
    'db-donor-apk','compile-directory','native-capture','native-build-receipt','verification','verifier-executable')
PIN_ARGUMENTS=('capture-receipt-sha256','run-identity-sha256','fixture-receipt-sha256',
    'compile-receipt-sha256','native-build-receipt-sha256','verification-sha256')
class Refused(ValueError):pass
def require(value,code):
    if not value:raise Refused(code)
def scope(receipt):
    require(type(receipt) is dict and receipt.get('schema')=='coh-immutable-source-snapshot-admission-v1'
            and receipt.get('passed') is True and receipt.get('source_snapshot_generation_admitted') is True
            and receipt.get('immutable_point_in_time_only') is True
            and receipt.get('owned_cleanup_verified') is True,'SOURCE_ADMISSION_SCOPE')
    for name in ('current_after_quiet_release_validated','incremental_updates_admitted',
        'client_materials_available','client_lods_available','client_cache_equivalence_verified',
        'actor_identity_verified','renderer_publication_admitted','ack_authority','world_authority',
        'authserver_authenticated','public_receipt_contains_private_identity_or_source_bytes'):
        require(receipt.get(name) is False,'SOURCE_ADMISSION_SCOPE')
    d.sha(receipt.get('source_snapshot_token_sha256'));return receipt

def readmit(args,workspace):
    # A separate interpreter gives the original source admitter exactly its own
    # project import closure; importing this retention helper into it would alter
    # the token's dependency binding. No runtime/service/capture is launched.
    output=workspace/'readmitted-source-snapshot.json'
    command=[sys.executable,str(HERE/'admit_source_snapshot.py')]
    for name in (*PATH_ARGUMENTS,*PIN_ARGUMENTS):command+=['--'+name,str(getattr(args,name.replace('-','_')))]
    command+=['--output',str(output)]
    child=None
    try:
        child=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        stdout,stderr=child.communicate(timeout=900)
        require(child.returncode==0 and len(stdout)+len(stderr)<=1024**2,'SOURCE_READMISSION_REFUSED')
        require(admit.capture.base.stop_owned(child),'READMISSION_CHILD_CLEANUP')
        end=time.monotonic()+2
        while not admit.capture.base.process_group_absent(child) and time.monotonic()<end:time.sleep(.05)
        require(admit.capture.base.process_group_absent(child),'READMISSION_GROUP_REMAINS')
        return d.json_object(d.read(output,64*1024))
    finally:
        if child is not None:
            # A failed/timeout admission is not permission to leave its owned
            # compiler-dependency child group running. Never emit child output.
            primary=sys.exc_info()[0] is not None;cleanup=[]
            try:
                require(admit.capture.base.stop_owned(child),'READMISSION_CHILD_CLEANUP')
                require(admit.capture.base.process_group_absent(child),'READMISSION_GROUP_REMAINS')
            except Exception as error:cleanup.append(error)
            for stream in (child.stdout,child.stderr):
                if stream is not None:
                    try:stream.close()
                    except Exception as error:cleanup.append(error)
            if cleanup and not primary:raise Refused('READMISSION_CHILD_CLEANUP')

def payload_plan(extracted,inspection,verification):
    require(verification.get('capture')==inspection.get('envelope'),'SAME_SOURCE_ENVELOPE')
    inputs=verification.get('inputs');require(type(inputs) is dict,'VERIFIED_PAYLOAD_INPUTS')
    result={}
    for name,maximum in PAYLOADS.items():
        expected=inputs.get(name);admit.pin(expected)
        item=inspection['files'][name]
        require(expected=={'bytes':item['bytes'],'sha256':item['sha256']}
                and expected['bytes']<=maximum
                and admit.identity(extracted/name,maximum)==expected,'EXACT_VERIFIED_PAYLOAD')
        result[name]=dict(expected)
    return result

def copy_payload(source,target,expected,maximum,created):
    descriptor=None;stream=None
    try:
        descriptor=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
        created.append(target)
        stream=os.fdopen(descriptor,'wb');descriptor=None
        # Only the exact verified native-format body is copied. Its own format
        # header remains intact; the private COHGTX envelope is never copied.
        source=d.regular(source);before=admit.identity(source,maximum)
        require(before==expected,'PAYLOAD_CHANGED_BEFORE_COPY')
        total=0
        with source.open('rb') as incoming:
            while block:=incoming.read(65536):
                total+=len(block);require(total<=expected['bytes'],'PAYLOAD_COPY_LIMIT');stream.write(block)
        require(total==expected['bytes'],'PAYLOAD_COPY_LENGTH')
        stream.flush();os.fsync(stream.fileno());stream.close();stream=None
        require(admit.identity(target,maximum)==expected and admit.identity(source,maximum)==expected,
                'PAYLOAD_CHANGED_DURING_COPY')
    except BaseException:
        if stream is not None:
            try:stream.close()
            except BaseException:pass
        if descriptor is not None:
            try:os.close(descriptor)
            except OSError:pass
        raise

def export_owned(extracted,output,plan,manifest,before_publish):
    require(output.name=='fresh-source-snapshot' and set(plan)==set(PAYLOADS),'FIXED_FRESH_EXPORT')
    require(output.parent.is_dir() and not output.exists(),'NEW_FRESH_EXPORT')
    created=[];owned=False
    try:
        output.mkdir(mode=0o700);owned=True
        for name,maximum in PAYLOADS.items():copy_payload(extracted/name,output/name,plan[name],maximum,created)
        before_publish()
        require(all(admit.identity(output/name,PAYLOADS[name])==plan[name] for name in PAYLOADS),
                'FINAL_PAYLOAD_BYTES')
        manifest_path=output/'manifest.json';created.append(manifest_path)
        admit.emit_public_receipt(manifest_path,manifest)
        return manifest
    except BaseException:
        if owned:
            # Close errors inside copy/publication cannot skip any later unlink.
            for target in reversed(created):
                try:target.unlink()
                except OSError:pass
            try:output.rmdir()
            except OSError:pass
        raise

def manifest_for(source,source_pin,fixture,fixture_pin,plan,revision,helper_pin):
    # Fixed public constructor. Never serialize private objects, selected-owner
    # IDs, arbitrary keys/paths, errors, private capture hashes or child output.
    return {'schema':'coh-fresh-source-snapshot-retention-v1','passed':True,
        'fixture_only':True,'input_scope':'new_disposable_original_graphical_COHLOCAL_THORHERO',
        'source_snapshot_token_sha256':source['source_snapshot_token_sha256'],
        'source_admission_receipt_sha256':source_pin,'fixture_capture_receipt_sha256':fixture_pin,
        'fresh_fixture_dump_sha256':fixture['database_dump_sha256'],
        'payloads':{name:{'bytes':plan[name]['bytes'],'sha256':plan[name]['sha256']} for name in PAYLOADS},
        'same_fully_admitted_source_snapshot_reverified':True,'fresh_source_creation_reverified':True,
        'public_source_payload_retention_permitted':True,'immutable_point_in_time_only':True,
        'private_user_input_accepted':False,'raw_private_transaction_exported':False,
        'source_generation_admitted':False,'current_after_quiet_release_validated':False,
        'client_materials_available':False,'client_lods_available':False,'client_cache_equivalence_verified':False,
        'actor_identity_verified':False,'renderer_publication_admitted':False,'world_authority':False,
        'orchestration_revision':revision,'retainer_source_sha256':helper_pin}

def retain(args):
    revision=admit.hosted_revision()
    admit.capture.base.fixture_modules()
    pins=admit.committed_source_closure(ROOT,admit.admission_source_pins(),revision)
    own=Path(__file__).resolve().relative_to(ROOT).as_posix();require(own in pins,'RETENTION_COMMITTED_HELPER')
    source=scope(admit.pinned_json(args.source_admission,args.source_admission_sha256,64*1024))
    fixture,backup,fixture_pins=admit.fixture_inputs(args.fixture_directory,args.fixture_receipt_sha256)
    output=d.path(args.output);require(output.name=='fresh-source-snapshot','FIXED_FRESH_EXPORT')
    for private in (args.private_output,args.private_work,args.fixture_directory,args.runtime,args.verification.parent):
        private=d.path(private);require(output!=private and private not in output.parents
            and output not in private.parents,'PUBLIC_PRIVATE_OUTPUT_ISOLATION')
    workspace=d.absent_directory(d.path(args.private_work)/'fresh-source-retention-readmission')
    workspace.mkdir(mode=0o700)
    try:
        reverified=scope(readmit(args,workspace))
        require(reverified==source,'SAME_FULL_SOURCE_ADMISSION')
    finally:
        primary=sys.exc_info()[0] is not None;cleanup=[]
        for name in ('readmitted-source-snapshot.json',):
            try:(workspace/name).unlink(missing_ok=True)
            except OSError as error:cleanup.append(error)
        try:workspace.rmdir()
        except OSError as error:cleanup.append(error)
        if cleanup and not primary:raise Refused('READMISSION_PRIVATE_CLEANUP')
    verification=admit.pinned_json(args.verification,args.verification_sha256,8*1024**2)
    inspection=admit.envelope.inspect(args.private_output/'source.cohgtx')
    extracted=d.path(args.verification.parent/'source')
    plan=payload_plan(extracted,inspection,verification)
    manifest=manifest_for(source,args.source_admission_sha256,fixture,args.fixture_receipt_sha256,
                          plan,revision,pins[own])
    def unchanged():
        require(admit.pinned_json(args.source_admission,args.source_admission_sha256,64*1024)==source,
                'SOURCE_ADMISSION_CHANGED')
        require(admit.fixture_inputs(args.fixture_directory,args.fixture_receipt_sha256)==(fixture,backup,fixture_pins),
                'FRESH_FIXTURE_CHANGED')
        require(admit.pinned_json(args.verification,args.verification_sha256,8*1024**2)==verification
                and admit.envelope.inspect(args.private_output/'source.cohgtx')==inspection,'VERIFIED_SOURCE_CHANGED')
        require(payload_plan(extracted,inspection,verification)==plan,'VERIFIED_PAYLOAD_CHANGED')
        require(admit.admission_source_pins()==pins,'RETENTION_IMPORT_CLOSURE_CHANGED')
        admit.committed_source_closure(ROOT,pins,revision)
    return export_owned(extracted,output,plan,manifest,unchanged)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in (*PATH_ARGUMENTS,'source-admission','output'):parser.add_argument('--'+name,type=Path,required=True)
    for name in (*PIN_ARGUMENTS,'source-admission-sha256'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();os.umask(0o077)
    try:retain(args)
    except Exception:
        print(json.dumps({'passed':False,'failure_code':'FRESH_SOURCE_RETENTION_REFUSED',
            'source_generation_admitted':False,'world_authority':False}));return 2
    print(json.dumps({'passed':True,'four_fresh_source_payloads_retained':True,
        'source_generation_admitted':False,'world_authority':False}));return 0
if __name__=='__main__':raise SystemExit(main())
