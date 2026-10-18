#!/usr/bin/env python3
"""Retain one raw initial packet only from the genuine fresh graphical fixture.

Existing/private profiles never qualify. Repeats complete source admission and
the owned native initial/GROUPS binding after cleanup. Raw packet bytes include
only this newly created disposable test character's data. No entity/character
tail, actor, READY, received-character, ACK, renderer or world is admitted.
"""
from __future__ import annotations
import argparse,hashlib,json,os,stat,sys
from pathlib import Path
import retain_fresh_source_snapshot as source_retention
admit=source_retention.admit;capture=admit.capture;d=admit.d
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
PATH_ARGUMENTS=source_retention.PATH_ARGUMENTS;PIN_ARGUMENTS=source_retention.PIN_ARGUMENTS
class Refused(ValueError):pass
def require(value,code):
    if not value:raise Refused(code)
def observed(private,work,report):
    require(report.get('passed') is True and report.get('cleanup_verified') is True
        and report.get('matching_groups_transaction_captured') is True
        and report.get('native_tool',{}).get('build_schema')==capture.INITIAL_BUILD_SCHEMA,
        'INITIAL_CLEANED_RUN_SCOPE')
    require(admit.public_status.summarize(report)['passed'] is True,'INITIAL_GROUPS_RUN_SCOPE')
    binding=capture.initial_input(private/'native',report['pair'])
    require(binding['status']=='OBSERVED' and binding['bounded_raw_allents_observed'] is True
        and binding['same_groups_owner_verified'] is True
        and report.get('initial_observation')==dict(binding,retained_after_owned_cleanup=True),
        'INITIAL_POST_CLEANUP_BINDING')
    require(capture.initial_input(work/'native-received',report['pair'])==binding,'INITIAL_ORIGINAL_LOAN_BYTES')
    receipt=d.json_object(d.read(capture.private_file(private/'native/initial-observation.json',64*1024),64*1024))
    require(capture.identity(private/'native/initial-observation.json',64*1024)==binding['receipt'],
        'INITIAL_RECEIPT_READ_CHANGED')
    return binding,receipt
def manifest_for(source,source_pin,fixture,fixture_pin,binding,receipt,revision,helper_pin):
    # Fixed constructor: never serialize private receipts/owners/arbitrary keys.
    # Protocol shortcut IDs and full-update counter are parser metadata, not
    # selected-character, connection, message or session identity exports.
    return {'schema':'coh-fresh-initial-observation-retention-v1','passed':True,
        'fixture_only':True,'input_scope':'new_disposable_original_graphical_COHLOCAL_THORHERO',
        'source_snapshot_token_sha256':source['source_snapshot_token_sha256'],
        'source_admission_receipt_sha256':source_pin,'fixture_capture_receipt_sha256':fixture_pin,
        'fresh_fixture_dump_sha256':fixture['database_dump_sha256'],
        'payload':{'name':'initial-update.bin','bytes':binding['packet']['bytes'],'sha256':binding['packet']['sha256']},
        'profile':{'payload_bits':receipt['payload_bits'],'post_command_cursor':receipt['post_command_cursor'],
            'byte_aligned':receipt['byte_aligned'],'ordered':receipt['ordered'],
            'transport_version':receipt['transport_version']},
        'accessible_commands':receipt['accessible_commands'],
        'shortcuts':[[row[0],row[1]] for row in receipt['shortcuts']],
        'update_prefix':{name:receipt['update_prefix'][name] for name in capture.INITIAL_PREFIX},
        'fresh_source_creation_reverified':True,'same_fully_admitted_source_snapshot_reverified':True,
        'same_owned_groups_initial_loan_reverified':True,'owned_cleanup_verified':True,
        'public_fresh_initial_packet_retention_permitted':True,'raw_packet_contains_disposable_test_character_data':True,
        'private_user_input_accepted':False,'raw_private_receipt_or_owner_exported':False,
        'raw_initial_packet_observation_only':True,'immutable_point_in_time_only':True,
        'entity_or_character_tail_semantics_admitted':False,'source_generation_admitted':False,
        'complete_initial_character':False,'actor_publication':False,'renderer_publication_admitted':False,
        'sends_ready':False,'sends_received_character':False,'sends_full_update_ack':False,
        'ack_permitted':False,'world_authority':False,'current_after_release_validated':False,
        'orchestration_revision':revision,'retainer_source_sha256':helper_pin}
def owned_key(info):return info.st_dev,info.st_ino,info.st_uid
def open_owned(path,created):
    descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    created.append((path,None))
    try:created[-1]=(path,owned_key(os.fstat(descriptor)))
    except BaseException:
        try:os.close(descriptor)
        except OSError:pass
        raise
    return descriptor
def close_stream(stream,descriptor):
    if stream is not None:
        try:stream.close()
        except BaseException:pass
    if descriptor is not None:
        try:os.close(descriptor)
        except OSError:pass
def copy_packet(source,target,expected,created):
    descriptor=stream=None
    try:
        source=capture.private_file(source,capture.INITIAL_PACKET_MAX)
        require(admit.identity(source,capture.INITIAL_PACKET_MAX)==expected,'INITIAL_EXPORT_SOURCE_BYTES')
        descriptor=open_owned(target,created);stream=os.fdopen(descriptor,'wb');descriptor=None;total=0
        with source.open('rb') as incoming:
            while block:=incoming.read(65536):
                total+=len(block);require(total<=expected['bytes'],'INITIAL_EXPORT_COPY_LIMIT');stream.write(block)
        require(total==expected['bytes'],'INITIAL_EXPORT_COPY_LENGTH')
        stream.flush();os.fsync(stream.fileno());stream.close();stream=None
        require(admit.identity(capture.private_file(target,capture.INITIAL_PACKET_MAX),capture.INITIAL_PACKET_MAX)==expected
            and admit.identity(source,capture.INITIAL_PACKET_MAX)==expected,'INITIAL_EXPORT_COPY_CHANGED')
    except BaseException:
        close_stream(stream,descriptor);raise
def commit_manifest(output,manifest,created):
    temporary=output/'.manifest.partial';final=output/'manifest.json';descriptor=stream=None
    raw=(json.dumps(manifest,sort_keys=True,indent=2,allow_nan=False)+'\n').encode('utf-8')
    require(len(raw)<=64*1024,'INITIAL_MANIFEST_LIMIT')
    try:
        descriptor=open_owned(temporary,created);key=created[-1][1]
        stream=os.fdopen(descriptor,'wb');descriptor=None;stream.write(raw)
        stream.flush();os.fsync(stream.fileno());stream.close();stream=None
        require(admit.identity(capture.private_file(temporary,64*1024),64*1024)==
            {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},'INITIAL_MANIFEST_BYTES')
        os.link(temporary,final,follow_symlinks=False);created.append((final,key))
        temporary.unlink()
        expected={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        require(admit.identity(capture.private_file(final,64*1024),64*1024)==expected,'INITIAL_MANIFEST_FINAL_BYTES')
        return expected
    except BaseException:
        close_stream(stream,descriptor);raise
def export_owned(source,output,expected,manifest,before_publish):
    admit.pin(expected);require(expected['bytes']<=capture.INITIAL_PACKET_MAX,'INITIAL_EXPORT_LIMIT')
    require(output.name=='fresh-initial-observation' and output.parent.is_dir()
        and not output.exists() and not output.is_symlink(),'NEW_FIXED_INITIAL_EXPORT')
    created=[];directory_key=None
    try:
        output.mkdir(mode=0o700);directory_key=owned_key(output.stat())
        copy_packet(source,output/'initial-update.bin',expected,created)
        before_publish()
        require(admit.identity(capture.private_file(output/'initial-update.bin',capture.INITIAL_PACKET_MAX),
            capture.INITIAL_PACKET_MAX)==expected,'INITIAL_EXPORT_FINAL_PACKET_BYTES')
        manifest_identity=commit_manifest(output,manifest,created)
        # The manifest is still private until the command returns successfully.
        # Rebind both source provenance and packet after its final I/O as well.
        before_publish()
        require(admit.identity(capture.private_file(output/'initial-update.bin',capture.INITIAL_PACKET_MAX),
            capture.INITIAL_PACKET_MAX)==expected,'INITIAL_EXPORT_COMMITTED_PACKET_BYTES')
        require(admit.identity(capture.private_file(output/'manifest.json',64*1024),64*1024)==manifest_identity
            and set(path.name for path in output.iterdir())=={'initial-update.bin','manifest.json'},
            'INITIAL_EXPORT_COMMITTED_MANIFEST_BYTES')
        return manifest
    except BaseException:
        # Preserve primary failure and replaced files. Each cleanup is separate;
        # no valid manifest remains accepted after a failure in owned I/O.
        if directory_key is not None:
            for path,key in reversed(created):
                try:
                    info=path.lstat()
                    if key is not None and stat.S_ISREG(info.st_mode) and owned_key(info)==key:path.unlink()
                except OSError:pass
            try:
                if owned_key(output.lstat())==directory_key:output.rmdir()
            except OSError:pass
        raise
def readmit(args,work):
    workspace=d.absent_directory(work/'fresh-initial-retention-readmission');workspace.mkdir(mode=0o700)
    try:return source_retention.scope(source_retention.readmit(args,workspace))
    finally:
        primary=sys.exc_info()[0] is not None;cleanup=[]
        try:(workspace/'readmitted-source-snapshot.json').unlink(missing_ok=True)
        except OSError as error:cleanup.append(error)
        try:workspace.rmdir()
        except OSError as error:cleanup.append(error)
        if cleanup and not primary:raise Refused('INITIAL_READMISSION_PRIVATE_CLEANUP')
def retain(args):
    revision=admit.hosted_revision();capture.base.fixture_modules()
    compiled,_=admit.compiled_admission.inspect(args.compile_directory,ROOT,args.compile_receipt_sha256)
    admit.capture.orchestration_source_paths(compiled)
    pins=admit.committed_source_closure(ROOT,admit.admission_source_pins(compiled=compiled),revision)
    own=Path(__file__).resolve().relative_to(ROOT).as_posix();require(own in pins,'INITIAL_RETENTION_COMMITTED_HELPER')
    source=source_retention.scope(admit.pinned_json(args.source_admission,args.source_admission_sha256,64*1024))
    fixture,backup,fixture_pins=admit.fixture_inputs(args.fixture_directory,args.fixture_receipt_sha256)
    private=d.path(args.private_output);work=d.path(args.private_work);output=d.path(args.output)
    require(output.name=='fresh-initial-observation','FIXED_INITIAL_EXPORT')
    for path in (private,work,args.fixture_directory,args.runtime,args.verification.parent):
        path=d.path(path);require(output!=path and path not in output.parents and output not in path.parents,
            'INITIAL_PUBLIC_PRIVATE_ISOLATION')
    report=admit.pinned_json(private/'capture-receipt.json',args.capture_receipt_sha256,8*1024**2)
    binding,receipt=observed(private,work,report)
    native=capture.native_input(args.native_capture,args.native_build_receipt,args.native_build_receipt_sha256)
    require(native.get('build_schema')==capture.INITIAL_BUILD_SCHEMA and native==report.get('native_tool'),
        'INITIAL_ADMITTED_NATIVE_ROLE')
    require(readmit(args,work)==source,'INITIAL_SAME_FULL_SOURCE_ADMISSION')
    source_identity=admit.identity(private/'source.cohgtx',admit.envelope.MAXIMUM)
    require(source_identity==report['pair']['source_envelope'],'INITIAL_SAME_SOURCE_ENVELOPE')
    verification=admit.pinned_json(args.verification,args.verification_sha256,8*1024**2)
    verifier=admit.identity(args.verifier_executable,8*1024**2)
    require(verifier==verification.get('executable'),'INITIAL_SAME_NATIVE_VERIFIER')
    manifest=manifest_for(source,args.source_admission_sha256,fixture,args.fixture_receipt_sha256,
        binding,receipt,revision,pins[own])
    def unchanged():
        require(admit.pinned_json(args.source_admission,args.source_admission_sha256,64*1024)==source
            and admit.pinned_json(private/'capture-receipt.json',args.capture_receipt_sha256,8*1024**2)==report,
            'INITIAL_SOURCE_RECEIPTS_CHANGED')
        require(admit.fixture_inputs(args.fixture_directory,args.fixture_receipt_sha256)==(fixture,backup,fixture_pins),
            'INITIAL_FRESH_FIXTURE_CHANGED')
        require(observed(private,work,report)==(binding,receipt),'INITIAL_OBSERVATION_CHANGED')
        require(capture.native_input(args.native_capture,args.native_build_receipt,args.native_build_receipt_sha256)==native,
            'INITIAL_NATIVE_INPUT_CHANGED')
        require(admit.identity(private/'source.cohgtx',admit.envelope.MAXIMUM)==source_identity
            and admit.pinned_json(args.verification,args.verification_sha256,8*1024**2)==verification
            and admit.identity(args.verifier_executable,8*1024**2)==verifier
            and admit.identity(private/'run-identity.json',8*1024**2)['sha256']==args.run_identity_sha256
            and admit.identity(work/'existing-database.dump',capture.PRIVATE_DUMP_MAX)==fixture_pins['fixture.pgdump']
            and capture.compiled_inputs_unchanged(args,native,compiled),'INITIAL_PROVENANCE_CHANGED')
        require(admit.admission_source_pins(compiled=compiled)==pins,'INITIAL_RETENTION_IMPORT_CLOSURE_CHANGED')
        admit.committed_source_closure(ROOT,pins,revision)
    return export_owned(private/'native/initial-update.bin',output,binding['packet'],manifest,unchanged)
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in (*PATH_ARGUMENTS,'source-admission','output'):parser.add_argument('--'+name,type=Path,required=True)
    for name in (*PIN_ARGUMENTS,'source-admission-sha256'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();os.umask(0o077)
    try:retain(args)
    except Exception:
        print(json.dumps({'passed':False,'failure_code':'FRESH_INITIAL_RETENTION_REFUSED',
            'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}));return 2
    print(json.dumps({'passed':True,'fresh_initial_packet_retained':True,
        'complete_initial_character':False,'actor_publication':False,'ack_permitted':False,'world_authority':False}));return 0
if __name__=='__main__':raise SystemExit(main())
