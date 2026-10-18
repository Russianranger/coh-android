#!/usr/bin/env python3
"""Admit one genuine immutable original-source GROUPS snapshot after cleanup.

This is a point-in-time source generation, never a post-release lifetime,
CLIENT cache/material/LOD permit, actor, renderer, ACK or world permit. Private
capture/provenance inputs stay private; the receipt exposes only an opaque
binding token and fixed scope. Every input hash and counter remains private.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,platform,re,subprocess,sys
from pathlib import Path
import delivery as d
import capture_groups_transaction as capture
import admit_groups_capture as compiled_admission
import admit_graphical_fixture as fixture_admission
import inspect_groups_capture as envelope
import summarize_groups_capture as public_status
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
CHECKS=('catalog_groups_match','runtime_catalog_associations','resource_catalog_associations',
        'raw_bounds_catalog_associations','eligibility_groups_associations')
INPUT_NAMES=set(envelope.NAMES.values())|{'native/groups.bin'}
REQUIRED_VERIFIER_SOURCES={
    'native-android/engine/scenecatalog-server/verify_source_snapshot.c',
    'native-android/engine/scenecatalog-server/check_source_snapshot_verifier.py'}
COUNTS=('files','slots','definitions','children','root_slots','active_roots',
        'external_owners','resource_rows','model_rows','public_bounds_rows',
        'emitted_definitions','emitted_roots','definition_scalars_compared',
        'named_peak_reservation_bytes','named_aggregate_limit_bytes')
FLAGS=('-std=c99','-Wall','-Wextra','-Werror','-pedantic','-O2','-fstack-usage')
VERIFIER_FALSE=('source_provenance_verified','source_run_identity_verified',
    'source_generation_admitted','cache_equivalence_verified','client_materials_admitted',
    'actor_identity_verified','world_authority','current_after_quiet_release')
ADMISSION_HELPERS=('admit_source_snapshot.py','verify_source_snapshot.c',
    'check_source_snapshot_verifier.py','summarize_groups_capture.py',
    'admit_graphical_fixture.py','capture_graphical_fixture.py','graphical_fixture_backup_guest.py')
class Refused(ValueError):pass
def require(value,code):
    if not value:raise Refused(code)
def identity(path,maximum):
    size,digest=d.hash_file(path,maximum);return {'bytes':size,'sha256':digest}
def pin(value,nonempty=True):
    require(type(value) is dict and set(value)=={'bytes','sha256'} and type(value.get('bytes')) is int
            and (1 if nonempty else 0)<=value['bytes']<=12*1024**3,'BYTE_IDENTITY')
    d.sha(value.get('sha256'));return value
def pinned_json(path,digest,maximum):
    d.sha(digest);require(identity(path,maximum)['sha256']==digest,'INDEPENDENT_INPUT_PIN')
    return d.json_object(d.read(path,maximum))
def inventory(value):
    require(type(value) is dict and set(value)=={'files','bytes','ordered_inventory_sha256'}
            and type(value['files']) is int and 0<value['files']<=350000
            and type(value['bytes']) is int and 0<value['bytes']<=12*1024**3,'SOURCE_RUNTIME_INVENTORY')
    d.sha(value['ordered_inventory_sha256']);return value
def source_pins():
    paths=set((*capture.base.SOURCE_PATHS,*capture.retained.SOURCE_PATHS,*capture.native_status.ENUM_SOURCE_PATHS,
        *('native-android/engine/scenecatalog-server/'+name for name in (
        'capture_groups_transaction.py','groups_capture_stages.py','groups_native_status.py','admit_groups_capture.py',
        'inspect_groups_capture.py','stage_groups_capture.py','source_groups_capture_sink.inc'))))
    return {name:d.hash_file(ROOT/name,8*1024**2)[1] for name in sorted(paths)}
def admission_source_pins(root=ROOT):
    # Account for the complete project Python import closure as well as the
    # source producer and explicitly invoked native/fixture admission helpers.
    # Standard-library and installed compiler/library identities remain runner
    # dependencies, never project source hashes.
    paths=set(source_pins())|{
        'native-android/engine/scenecatalog-server/'+name for name in ADMISSION_HELPERS}
    for module in tuple(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename:
            path=Path(filename).resolve()
            if path.is_relative_to(root) and path.suffix=='.py':paths.add(path.relative_to(root).as_posix())
    return {name:d.hash_file(root/name,8*1024**2)[1] for name in sorted(paths)}
def committed_source_closure(root,pins,revision):
    require(type(pins) is dict and pins,'ADMISSION_SOURCE_CLOSURE')
    for name,digest in pins.items():
        d.sha(digest)
        expected=subprocess.run(['git','show',revision+':'+name],cwd=root,
                                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=30)
        require(expected.returncode==0 and len(expected.stdout)<=8*1024**2
                and hashlib.sha256(expected.stdout).hexdigest()==digest
                and d.hash_file(root/name,8*1024**2)[1]==digest,'ADMISSION_COMMITTED_BYTES')
    return pins
def verifier_source_pins():
    path=HERE/'check_source_snapshot_verifier.py'
    spec=importlib.util.spec_from_file_location('coh_pinned_snapshot_verifier',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.source_pins(require_committed=True)
def fixture_inputs(directory,receipt_sha256):
    receipt=pinned_json(directory/'fixture-capture.json',receipt_sha256,16*1024**2)
    pins=receipt.get('retained_creation_evidence')
    require(type(pins) is dict and set(pins)=={
        'original-guest-report.json','external-observer.json','backup-request.json','backup-receipt.json'},
        'FIXTURE_RETAINED_INPUT_SET')
    for item in pins.values():pin(item)
    backup=pinned_json(directory/'backup-receipt.json',pins['backup-receipt.json']['sha256'],16*1024**2)
    require(backup==receipt.get('full_backup'),'FIXTURE_BACKUP_IDENTITY')
    fixture=fixture_admission.inspect(directory,receipt_sha256)
    inputs={'fixture-capture.json':identity(directory/'fixture-capture.json',16*1024**2),
        'fixture.pgdump':identity(directory/'fixture.pgdump',capture.PRIVATE_DUMP_MAX),
        'account.txt':identity(directory/'account.txt',15)}
    for name,expected in pins.items():
        inputs[name]=identity(directory/name,16*1024**2)
        require(inputs[name]==expected,'FIXTURE_RETAINED_INPUT_BYTES')
    require(inputs['fixture-capture.json']['sha256']==receipt_sha256
            and inputs['fixture.pgdump']['sha256']==fixture['database_dump_sha256'],'FIXTURE_INPUT_BYTES')
    return fixture,backup,inputs
def emit_public_receipt(output,value):
    # Publish only a fully flushed/fsynced/closed temporary file. A late write
    # or close failure must never leave a valid positive receipt for an
    # always-upload step to collect. link() gives exclusive no-replace publish.
    temporary=output.with_name('.'+output.name+'.partial-'+os.urandom(16).hex())
    descriptor=None;stream=None;owned=False;published=False
    try:
        descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600);owned=True
        stream=os.fdopen(descriptor,'w',encoding='utf-8',newline='\n');descriptor=None
        json.dump(value,stream,sort_keys=True,indent=2,allow_nan=False);stream.write('\n')
        stream.flush();os.fsync(stream.fileno());stream.close();stream=None
        os.link(temporary,output,follow_symlinks=False);published=True
        temporary.unlink();owned=False
    except BaseException:
        # Every cleanup is independent and cannot mask the primary failure.
        if stream is not None:
            try:stream.close()
            except BaseException:pass
        if descriptor is not None:
            try:os.close(descriptor)
            except OSError:pass
        if published:
            try:output.unlink()
            except OSError:pass
        if owned:
            try:temporary.unlink()
            except OSError:pass
        raise
def verify_documents(report,run,revision,current_sources,dump,compiled,native,compile_pin,native_pin,source_inventory):
    # Pure protocol/ownership closure only. This function cannot mint authority;
    # the actual hosted, file, native-verifier and producer checks remain outside.
    status=public_status.summarize(report)
    require(status['passed'] is True,'CAPTURE_NOT_ACCEPTED')
    for name in ('existing_character_rows_seeded','new_character_created'):
        require(report.get(name) is False,'CAPTURE_INPUT_SCOPE')
    require(type(report.get('existing_character_count')) is int and report['existing_character_count']==1,'FIXTURE_MEMBERSHIP')
    require(run.get('schema')=='coh-private-original-native-groups-identity-v1'
            and type(run.get('nonce')) is str and re.fullmatch('[0-9a-f]{64}',run['nonce'])
            and run.get('source_revision')==revision,'SOURCE_RUN_IDENTITY')
    for name in ('private_fresh_wine_prefix','private_fresh_pg_cluster','restored_existing_database_only'):
        require(run.get(name) is True,'SOURCE_RUN_SCOPE')
    require(report.get('source_sha256')==run.get('source_sha256')==current_sources and current_sources,
            'SOURCE_RUN_CODE_BYTES')
    pin(report.get('existing_database_dump'));pin(run.get('database_dump'))
    require(report.get('existing_database_dump')==run.get('database_dump')==pin(dump),'SOURCE_RUN_DUMP')
    require(report.get('compile_receipt_sha256')==run.get('compile_receipt_sha256')==compile_pin
            and run.get('native_build_receipt_sha256')==native_pin,'SOURCE_RUN_BINARY_PINS')
    pin(report.get('original_map_binary'));pin(compiled['artifacts']['MapServer.exe']);pin(native.get('binary'))
    require(report.get('original_map_binary')==compiled['artifacts']['MapServer.exe']
            and report.get('native_tool')==native,'SOURCE_RUN_BINARY_BYTES')
    inventory(report.get('runtime_inventory'));inventory(run.get('runtime_inventory'))
    require(report.get('runtime_inventory')==run.get('runtime_inventory')==inventory(source_inventory),
            'SOURCE_RUN_RUNTIME_BYTES')
    return {'protocol_closure_verified':True,'source_generation_admitted':False,'world_authority':False}
def verify_native(value,inspection,source_capture,native_packet,executable,revision,expected_sources,root=ROOT):
    require(value.get('schema')=='coh-source-snapshot-native-verification-v1' and value.get('passed') is True
            and all(value.get(name) is False for name in VERIFIER_FALSE)
            and value.get('exact_native_packet_bytes_verified') is True and value.get('private_receipt') is True
            and value.get('source_revision')==revision,
            'NATIVE_VERIFIER_SCOPE')
    pin(value.get('capture'));pin(value.get('executable'))
    require(value.get('capture')==source_capture and value.get('executable')==executable,'NATIVE_VERIFIER_BYTES')
    checks=value.get('checks');require(type(checks) is dict and set(checks)==set(CHECKS)
            and all(checks[name] is True for name in CHECKS),'COMPLETE_NATIVE_ASSOCIATIONS')
    inputs=value.get('inputs');require(type(inputs) is dict and set(inputs)==INPUT_NAMES,'NATIVE_VERIFIER_INPUT_SET')
    for item in inputs.values():pin(item)
    for name in envelope.NAMES.values():
        expected=inspection['files'][name];require(inputs[name]=={'bytes':expected['bytes'],'sha256':expected['sha256']},'SAME_ENVELOPE_NATIVE_INPUTS')
    require(inputs['native/groups.bin']==native_packet and native_packet==inputs['packet.bin'],
            'SAME_NATIVE_RECEIVE_INPUT')
    hashes=value.get('source_sha256');require(type(hashes) is dict and REQUIRED_VERIFIER_SOURCES<=set(hashes)
            and hashes==expected_sources,
            'NATIVE_VERIFIER_SOURCE_SET')
    for name,digest in hashes.items():
        require(type(name) is str and name.startswith('native-android/') and Path(name).as_posix()==name
                and '..' not in Path(name).parts and '\\' not in name,'NATIVE_VERIFIER_SOURCE_PATH')
        d.sha(digest);require(d.hash_file(root/name,8*1024**2)[1]==digest,'NATIVE_VERIFIER_SOURCE_BYTES')
    build=value.get('build');require(type(build) is dict and set(build)=={
            'compiler','flags','libraries','source_sha256','current_committed_sources_verified','mode',
            'maximum_static_frame_bytes','control_digest_stack_reserve_bytes'} and build.get('source_sha256')==hashes
            and type(build.get('compiler')) is str and 0<len(build['compiler'])<=512
            and build.get('flags')==list(FLAGS) and build.get('libraries')==['crypto','z','m']
            and build.get('current_committed_sources_verified') is True and build.get('mode')=='release'
            and type(build.get('maximum_static_frame_bytes')) is int
            and 0<build['maximum_static_frame_bytes']<512*1024
            and type(build.get('control_digest_stack_reserve_bytes')) is int
            and build['control_digest_stack_reserve_bytes']==512*1024,
            'NATIVE_VERIFIER_BUILD')
    counts=value.get('counts');require(type(counts) is dict and set(counts)==set(COUNTS)
            and all(type(number) is int and 0<=number<=0xffffffff for number in counts.values())
            and counts['named_aggregate_limit_bytes']==96*1024**2
            and counts['named_peak_reservation_bytes']<=counts['named_aggregate_limit_bytes'],
            'NATIVE_VERIFIER_COUNTS')
    # Copy no names, counter values or private hashes into the public receipt.
    return {'native_associations_verified':True,'source_generation_admitted':False,'world_authority':False}
def hosted_revision():
    require(os.name=='posix' and platform.system()=='Linux' and platform.machine()=='x86_64'
            and os.geteuid()!=0 and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
            and os.environ.get('GITHUB_REPOSITORY')=='Russianranger/coh-android'
            and os.environ.get('GITHUB_REF')=='refs/heads/native-android','ACTUAL_OWNED_HOST_REQUIRED')
    require(re.fullmatch('[1-9][0-9]*',os.environ.get('GITHUB_RUN_ID','')) is not None,'ACTUAL_RUN_IDENTITY')
    revision=os.environ.get('GITHUB_SHA','');require(re.fullmatch('[0-9a-f]{40}',revision) is not None,'ACTUAL_RUN_REVISION')
    require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==revision,'ACTUAL_SOURCE_HEAD')
    # Both external admission implementations are part of the exact checked-out
    # orchestration, not untracked replacements that git diff would overlook.
    for name in ADMISSION_HELPERS:
        relative='native-android/engine/scenecatalog-server/'+name
        expected=subprocess.check_output(['git','show',revision+':'+relative],cwd=ROOT,stderr=subprocess.DEVNULL)
        require((ROOT/relative).read_bytes()==expected,'ADMISSION_COMMITTED_BYTES')
    return revision
def admit(args):
    # Tests may exercise pure protocol helpers, but cannot emit a positive
    # snapshot-generation receipt without this real execution-origin gate.
    revision=hosted_revision()
    # Load the later fixture modules before pinning all executed project imports.
    # This prevents a changed imported acceptance helper from inheriting trust
    # from the unchanged top-level admitter or producer receipt.
    fx,db,pg,pe=capture.base.fixture_modules()
    admission_pins=committed_source_closure(ROOT,admission_source_pins(),revision)
    output=d.path(args.output);require(output.parent.is_dir() and not output.exists(),'EXCLUSIVE_SOURCE_RECEIPT')
    private=d.path(args.private_output);work=d.path(args.private_work)
    report=pinned_json(private/'capture-receipt.json',args.capture_receipt_sha256,8*1024**2)
    run=pinned_json(private/'run-identity.json',args.run_identity_sha256,8*1024**2)
    require(report.get('run_identity_sha256')==args.run_identity_sha256,'RUN_IDENTITY_PIN')
    fixture,backup,fixture_pins=fixture_inputs(args.fixture_directory,args.fixture_receipt_sha256)
    created=backup['fixture_identity'];require(type(created.get('character_id')) is int and created['character_id']>0,'SOURCE_CREATED_CHARACTER')
    dump=identity(Path(fixture['database_dump']),capture.PRIVATE_DUMP_MAX)
    require(dump['sha256']==fixture['database_dump_sha256']
            and identity(work/'existing-database.dump',capture.PRIVATE_DUMP_MAX)==dump,'ACTUAL_RESTORE_COPY')
    require(capture.account_input(Path(fixture['account_file']))=='COHLOCAL','ACTUAL_FIXTURE_ACCOUNT')
    compiled,_=compiled_admission.inspect(args.compile_directory,ROOT,args.compile_receipt_sha256)
    native=capture.native_input(args.native_capture,args.native_build_receipt,args.native_build_receipt_sha256)
    require(identity(work/'map-runtime/MapServer.exe',16*1024**2)==compiled['artifacts']['MapServer.exe'],
            'ACTUAL_SOURCE_EXECUTABLE')
    control=fx.validate_control_fixture(d.json_object(d.read(args.control_fixture,8*1024**2)))
    runtime=d.path(args.runtime);require(str(runtime)==control['runtime_host_path'],'ACTUAL_CONTROL_RUNTIME')
    actual_inventory=capture.base.inventory(runtime)
    files,schema,dbdoc,donor=db.donor_inputs(args.db_donor_apk)
    require(donor==db.expected_inputs(),'ACTUAL_DB_DONOR')
    require(identity(work/'db-runtime/DbServer.exe',16*1024**2)==
            {'bytes':len(files['DbServer.exe']),'sha256':d.digest(files['DbServer.exe'])},'ACTUAL_DB_EXECUTABLE')
    current=source_pins();capture.verify_orchestration(ROOT,current,revision)
    verify_documents(report,run,revision,current,dump,compiled,native,args.compile_receipt_sha256,
                     args.native_build_receipt_sha256,actual_inventory)
    # Use the real source-created ID from the independently admitted fresh full
    # backup. This is a comparison only, never a native DBID selection argument.
    source=private/'source.cohgtx';received=private/'native'
    actual_pair=capture.pair(source,received,[{'containerid':created['character_id']}],fixture['wire_slot'])
    require(actual_pair==report.get('pair'),'ACTUAL_SOURCE_NATIVE_PAIR')
    inspection=envelope.inspect(source);source_identity=identity(source,envelope.MAXIMUM)
    packet=identity(received/'groups.bin',16*1024**2)
    verification=pinned_json(args.verification,args.verification_sha256,8*1024**2)
    executable=identity(args.verifier_executable,8*1024**2)
    native_sources=verifier_source_pins()
    verify_native(verification,inspection,source_identity,packet,executable,revision,native_sources)
    # Refuse a changing capture/verifier/producer input rather than mint a token
    # from a mixed read. Runtime ownership and socket/quiet release already had
    # to close successfully in the source-pinned supervisor/native tool.
    require(identity(source,envelope.MAXIMUM)==source_identity and identity(received/'groups.bin',16*1024**2)==packet,
            'SNAPSHOT_INPUT_CHANGED')
    require(identity(private/'capture-receipt.json',8*1024**2)['sha256']==args.capture_receipt_sha256
            and identity(private/'run-identity.json',8*1024**2)['sha256']==args.run_identity_sha256
            and identity(args.verification,8*1024**2)['sha256']==args.verification_sha256
            and identity(args.verifier_executable,8*1024**2)==executable,'PROVENANCE_INPUT_CHANGED')
    require(current==source_pins() and capture.compiled_inputs_unchanged(args,native,compiled),
            'ADMITTED_SOURCE_CHANGED')
    require(admission_pins==admission_source_pins(),'ADMISSION_IMPORT_CLOSURE_CHANGED')
    committed_source_closure(ROOT,admission_pins,revision)
    committed_source_closure(ROOT,native_sources,revision)
    require(fixture_inputs(args.fixture_directory,args.fixture_receipt_sha256)==(fixture,backup,fixture_pins)
            and identity(work/'existing-database.dump',capture.PRIVATE_DUMP_MAX)==dump,'FIXTURE_INPUT_CHANGED')
    private_binding={'capture':args.capture_receipt_sha256,'run':args.run_identity_sha256,
        'source':source_identity,'packet':packet,'verifier':args.verification_sha256,'verifier_executable':executable,
        'fixture':args.fixture_receipt_sha256,'fixture_inputs':fixture_pins,'compiled':args.compile_receipt_sha256,
        'native':args.native_build_receipt_sha256,'revision':revision,'admission_source_sha256':admission_pins,
        'verifier_source_sha256':native_sources}
    token=hashlib.sha256(b'COH-IMMUTABLE-SOURCE-SNAPSHOT-V1\0'+json.dumps(private_binding,sort_keys=True,
                            separators=(',',':')).encode()).hexdigest()
    result={'schema':'coh-immutable-source-snapshot-admission-v1','passed':True,
        'source_snapshot_token_sha256':token,'source_snapshot_generation_admitted':True,
        'source_generation_admitted':True,'original_source_provenance_verified':True,
        'exact_same_boundary_native_packet_verified':True,'same_snapshot_server_resources_bound':True,
        'complete_groups_catalog_match':True,'owned_cleanup_verified':True,'immutable_point_in_time_only':True,
        'current_after_quiet_release_validated':False,'incremental_updates_admitted':False,
        'client_materials_available':False,'client_lods_available':False,'client_cache_equivalence_verified':False,
        'actor_identity_verified':False,'renderer_publication_admitted':False,'ack_authority':False,
        'world_authority':False,'local_development_auth':True,'authserver_authenticated':False,
        'orchestration_revision':revision,'admitter_source_sha256':d.hash_file(Path(__file__),8*1024**2)[1],
        'public_receipt_contains_private_identity_or_source_bytes':False}
    emit_public_receipt(output,result);return result
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('private-output','private-work','fixture-directory','runtime','control-fixture','db-donor-apk',
                 'compile-directory','native-capture','native-build-receipt','verification','verifier-executable','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    for name in ('capture-receipt-sha256','run-identity-sha256','fixture-receipt-sha256','compile-receipt-sha256',
                 'native-build-receipt-sha256','verification-sha256'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();os.umask(0o077)
    try:
        result=admit(args);print(json.dumps({'passed':True,'source_snapshot_generation_admitted':True,
            'immutable_point_in_time_only':True,'world_authority':False}));return 0
    except Exception:
        # Never print private paths, IDs, hashes, parser text or exception text.
        print(json.dumps({'passed':False,'failure_code':'SOURCE_SNAPSHOT_REFUSED',
            'source_snapshot_generation_admitted':False,'world_authority':False}));return 2
if __name__=='__main__':raise SystemExit(main())
