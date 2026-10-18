#!/usr/bin/env python3
"""Admit the separately qualified account-control receiver on a fresh hosted destination.

No compilation, old controls, account input or service startup. The only native
invocations are the loader's verify/list and the exact no-argument exit2 smoke.
"""
import gzip
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import selectors
import signal
import stat
import subprocess
import sys
import time

PREFIX = 'native-android/combined-client/diagnostics/'
OLD = 'native-android/combined-client/diagnostics/primary-authority-20261017/initial-receiver-account-controls-release-20261018/'
STATUS_ROOT = 'native-android/combined-client/diagnostics/primary-authority-20261017/initial-receiver-account-controls-release-20261018/'
REVIEW = 'native-android/combined-client/diagnostics/continuation-f-20261017/local-initial-account-controls-release-reuse-review-20261018/'
ELF = STATUS_ROOT + 'coh-capture-local-initial'
FOLLOWUP = 'native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/owner-predicates-followup.json'
FOLLOWUP_SHA = 'd16e9260ef07a3d64e46014037e2433d96f9a2b94905a8b7fd7e1e4970d4aa22'
FOLLOWUP_BYTES = 21528
REVIEW_SHA = 'b133df1116c5edb8426ec9a7f3b5849998e730463081fb2f15c1b7c6b46f992d'
REVIEW_BYTES = 17796
GZIP_SHA = '95fde3f9d96b5e22edda28183d320e735488a134c2b6a4971eeb9c9fe9a99108'
GZIP_BYTES = 89874
BUILD_SHA = '821ebfd2f84c60e8da23333476b9d1f8baadaf815c506933ee2b41572ef137d6'
BUILD_BYTES = 254894
ELF_SHA = '6115b96942579229d765921aee8d963f1e82ef4e7cce01a9d6d78bea6d8d419f'
MAP_SHA = '2276b07ad9f0a3b02d688fd1e168ace06641dcdc43169cd4bac0a33c30c424f8'
HISTORICAL = '1d9771c4565f9312d4e6712da95c527829c9bb41'
OBSERVER_BUILD = 'native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/compile-owner-predicates-20261018/compile-only-receipt.json'
OBSERVER_BUILD_SHA = '478bea524f7d8a5ed016ae43ea54f50401bff2c714d75275002d1f8d5b6e9034'
OBSERVER_BUILD_BYTES = 3796
PROFILE_SCHEMA = 'coh-fresh-owner-predicate-followup-v1'
REVIEW_SCHEMA = 'coh-f-retained-local-initial-account-controls-release-reuse-review-v1'
OLD_GATE = PREFIX + 'continuation-f-20261017/workflow-fresh-groups-observation-20261018/review.json'
OLD_GATE_BYTES = 43347
WORKFLOW = '.github/workflows/native-fresh-groups-observation.yml'
OLD_GATE_SHA = 'ba53d4ef8070bf7d642fe6424d0c6dce7fcc808382b66a77103407616cd0e0bb'
C_REVIEW = PREFIX + 'continuation-f-20261017/initial-editmsg-20261018/review.json'
C_REVIEW_BYTES = 17912
C_REVIEW_SHA = '8f963e9330dd9768f5586d72e1f9af2971902125d47a999c1d57b150b65c7947'
C_PROOF = 'native-android/engine/initial-capture/qualification/initial-editmsg-2f8337277.json.gz'
C_PROOF_BYTES = 6750
C_PROOF_SHA = '38285e20e89f909bdb8aa4a5eb07fa782e6f6bfd44d21cc7d25220c23ac1e88d'
C_BINDING = 'native-android/engine/initial-capture/qualification/initial-editmsg-2f8337277-binding.json'
C_BINDING_BYTES = 8576
C_BINDING_SHA = '7bda85486ab4ff6934701ee9fa9022fc6a24ddc57c8a03bc334722231bbdb9f4'
CASES = ('account-controls-captured',)
BASENAME = 'coh-capture-local-initial'
INTERPRETER = '/lib64/ld-linux-x86-64.so.2'
NEEDED = ['libz.so.1', 'libcrypto.so.3', 'libc.so.6']
VERSIONS = {'libz.so.1': ['ZLIB_1.2.0'], 'libcrypto.so.3': ['OPENSSL_3.0.0'],
            'libc.so.6': sorted(['GLIBC_2.33', 'GLIBC_2.17', 'GLIBC_2.14', 'GLIBC_2.34',
                                'GLIBC_2.4', 'GLIBC_2.2.5', 'GLIBC_2.3.4'])}
CLEAN_ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
GATE_KEYS = {'schema', 'passed', 'source_revision', 'source_sha256',
             'host_controls_reexecuted', 'historical_worker_commit_replayed_in_CI',
             'source_preflight_only', 'runtime_executed', 'accepted_observer_equivalence',
             'source_generation_admitted', 'world_authority', 'observer_compile_receipt_sha256',
             'receiver_build_receipt_sha256', 'source_profile_proof_sha256'}

# Each new source proof is separate from the immutable EDITMSG proof above.
ACCOUNT_PROOF = 'native-android/engine/dbclient/qualification/account-controls-02b54d43f.json.gz'
ACCOUNT_PROOF_BYTES = 5180
ACCOUNT_PROOF_SHA = 'd04dda6ac635ced869f0a86e4f4801ec732d12e69dc8ab10575056fa9c00513f'
ACCOUNT_RAW_SHA = '8b4a16f704f53095d75c822f8f4635a707b8b965f2f1938888ff2d71c2449c1a'
ACCOUNT_BINDING = 'native-android/engine/dbclient/qualification/account-controls-02b54d43f-binding.json'
ACCOUNT_BINDING_BYTES = 6274
ACCOUNT_BINDING_SHA = '53767d18c4edd2b10964a6a2d4b8bff1ed40490789f6bb316d44c26cb3b18acb'
ACCOUNT_REVIEW = PREFIX + 'continuation-f-20261017/db-account-controls-source-review-20261018/review.json'
ACCOUNT_REVIEW_BYTES = 17692
ACCOUNT_REVIEW_SHA = '738f597ec02d40edbc55c603af265f5e82fce4f997ee1d9119f73fdad602bf98'
OWNER_REVIEW = PREFIX + 'continuation-f-20261017/fresh-owner-predicate-source-review-20261018/review.json'
OWNER_REVIEW_BYTES = 67571
OWNER_REVIEW_SHA = '8634a0c047873914faffa6b2488ba0e0be47391a682f75e5dc55dc76304e4151'
EARLIER_PROFILE = 'native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/probe-drive-alias-followup.json'
EARLIER_PROFILE_BYTES = 6860
EARLIER_PROFILE_SHA = '1ac05fa9145d63c218c389c88263ba26eb67a3a80139d587671ac79eea6591e3'
ROOT_LINKS = PREFIX + 'primary-authority-20261017/db-account-build-dependency-closure-20261018/source.json'
ROOT_LINKS_BYTES = 4188
ROOT_LINKS_SHA = '682d1e9ea6593b128c36a15f4cfbd7a2f0b2962bc039ed66c21879027610bd4a'
OWN_LINKS = 'native-android/engine/dbclient/qualification/account-control-owned-link-lists.json'
OWN_LINKS_BYTES = 1265
OWN_LINKS_SHA = '67578035a171f6f0fe0d5bf549f5658b2737d6f10c16a04090fa1b70cb43c50c'

class Refused(Exception):
    def __init__(self, code):
        self.code = code
        self.cleanup_verified = True

def need(ok, code):
    if not ok:
        raise Refused(code)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def raw(path, maximum=8 * 1024**2):
    need(path.resolve() == path, 'REGULAR_INPUT')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= maximum, 'REGULAR_INPUT')
        chunks, count = [], 0
        while True:
            block = os.read(fd, 65536)
            if not block:
                break
            count += len(block)
            need(count <= maximum, 'REGULAR_INPUT')
            chunks.append(block)
        after = os.fstat(fd)
        need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
             (after.st_dev, after.st_ino, count, after.st_mtime_ns), 'INPUT_CHANGED')
        return b''.join(chunks)
    finally:
        os.close(fd)

def child(command, cwd, limit=262144, seconds=20):
    """Bound output while reading, bound time, and reap on every failure."""
    process = subprocess.Popen(command, cwd=cwd, env=CLEAN_ENV, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    out = [bytearray(), bytearray()]
    failure, result, clean = None, None, True
    try:
        with selectors.DefaultSelector() as selector:
            for index, stream in enumerate((process.stdout, process.stderr)):
                selector.register(stream, selectors.EVENT_READ, index)
            deadline = time.monotonic() + seconds
            while selector.get_map():
                remaining = deadline - time.monotonic()
                need(remaining > 0, 'CHILD_TIMEOUT')
                for key, _ in selector.select(min(remaining, 0.1)):
                    block = os.read(key.fd, 4096)
                    if not block:
                        selector.unregister(key.fileobj)
                    else:
                        out[key.data].extend(block)
                        need(len(out[key.data]) <= limit, 'CHILD_OUTPUT')
            remaining = deadline - time.monotonic()
            need(remaining > 0, 'CHILD_TIMEOUT')
            result = process.wait(timeout=remaining)
    except BaseException as error:
        failure = error if isinstance(error, Refused) else Refused('CHILD_PROCESS')
    finally:
        # A dead leader can leave a descendant holding a pipe or group alive.
        # Never predicate group teardown on Popen.poll()/leader liveness.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError:
            clean = False
        try:
            process.wait(timeout=2)
        except (OSError, subprocess.TimeoutExpired):
            clean = False
        for stream in (process.stdout, process.stderr):
            try:
                stream.close()
            except BaseException:
                clean = False
        until = time.monotonic() + 1
        while True:
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                break
            except OSError:
                clean = False
                break
            if time.monotonic() >= until:
                clean = False
                break
            time.sleep(0.01)
    if failure is not None:
        failure.cleanup_verified = clean
        raise failure
    if not clean:
        failure = Refused('CHILD_CLEANUP')
        failure.cleanup_verified = False
        raise failure
    return result, bytes(out[0]), bytes(out[1])

def git(root, *args):
    status, value, error = child(['/usr/bin/git', *args], root)
    need(status == 0 and not error, 'GIT_SOURCE')
    return value

def committed(root, pins, revision):
    need(git(root, 'rev-parse', 'HEAD').decode().strip() == revision, 'SOURCE_HEAD')
    need(type(pins) is dict and 173 <= len(pins) <= 512, 'SOURCE_GATE')
    tree = git(root, 'ls-tree', '-r', '-z', revision, '--', *sorted(pins))
    blobs = {}
    for row in tree.split(b'\0'):
        if row:
            meta, name = row.split(b'\t', 1)
            mode, kind, blob = meta.split()
            need(kind == b'blob' and mode in (b'100644', b'100755'), 'GIT_SOURCE')
            blobs[name.decode()] = blob.decode()
    need(set(blobs) == set(pins), 'GIT_SOURCE')
    for name, pin in pins.items():
        rel = PurePosixPath(name)
        need(type(name) is str and rel.as_posix() == name and not rel.is_absolute() and
             all(p not in ('', '.', '..') for p in rel.parts) and '\\' not in name and ':' not in name and
             type(pin) is str and re.fullmatch('[0-9a-f]{64}', pin), 'SOURCE_GATE')
        value = raw(root / name)
        need(digest(value) == pin and hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest()
             == blobs[name], 'SOURCE_BYTES')
    need(git(root, 'rev-parse', 'HEAD').decode().strip() == revision, 'SOURCE_HEAD')

def fixed(root, name, size, pin):
    value = raw(root / name)
    need(len(value) == size and digest(value) == pin, 'FIXED_INPUT')
    return value

def frozen_metadata():
    """Refuse missing or malformed fixed evidence metadata before reading it."""
    need(all(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) for value in
             (FOLLOWUP_SHA, REVIEW_SHA, GZIP_SHA, BUILD_SHA, ELF_SHA, MAP_SHA, OBSERVER_BUILD_SHA))
         and all(type(value) is int and value > 0 for value in
                 (FOLLOWUP_BYTES, REVIEW_BYTES, GZIP_BYTES, BUILD_BYTES, OBSERVER_BUILD_BYTES))
         and all(type(value) is str and value.startswith((PREFIX,
                 'native-android/engine/scenecatalog-server/evidence/')) for value in
                 (FOLLOWUP, REVIEW, OBSERVER_BUILD)), 'EVIDENCE_NOT_FROZEN')

def qualified_sources(root, build, pins):
    """Only five explicit changes supersede the historical EDITMSG source map."""
    def pinned(name, size, sha):
        value = fixed(root, name, size, sha)
        pins[name] = sha
        return value
    review = json.loads(pinned(C_REVIEW, C_REVIEW_BYTES, C_REVIEW_SHA))
    pinned(C_PROOF, C_PROOF_BYTES, C_PROOF_SHA)
    pinned(C_BINDING, C_BINDING_BYTES, C_BINDING_SHA)
    need(review['passed'] is True and review['source_input_count'] == 79 and
         len(review['source_sha256']) == 79, 'QUALIFIED_SCOPE')
    previous = review['source_sha256']
    raw_account = gzip.decompress(pinned(ACCOUNT_PROOF, ACCOUNT_PROOF_BYTES, ACCOUNT_PROOF_SHA))
    need(len(raw_account) == 25073 and digest(raw_account) == ACCOUNT_RAW_SHA, 'QUALIFIED_SCOPE')
    account = json.loads(raw_account)
    binding = json.loads(pinned(ACCOUNT_BINDING, ACCOUNT_BINDING_BYTES, ACCOUNT_BINDING_SHA))
    a_review = json.loads(pinned(ACCOUNT_REVIEW, ACCOUNT_REVIEW_BYTES, ACCOUNT_REVIEW_SHA))
    current = account['source_sha256']
    need(account['schema'] == 'coh-db-account-controls-focused-tests-v1' and account['passed'] is True and
         account['all_inputs_equal_committed_HEAD'] is True and len(current) == 36 and
         account['source_revision'] == binding['qualified_source_revision'] == a_review['qualified_source_revision'] ==
         '02b54d43ffd2add91b32a5651aa31ebf6b170fdd' and
         binding['schema'] == 'coh-db-account-controls-source-proof-binding-v1' and binding['passed'] is True and
         binding['source_sha256'] == current == a_review['qualified_source_sha256'] and
         a_review['schema'] == 'coh-f-db-account-controls-source-review-v1' and a_review['passed'] is True,
         'QUALIFIED_SCOPE')
    for key in ('historical_suites_executed', 'real_auth_or_db', 'sockets_executed',
                'actual_witness_body_inferred', 'source_generation_admitted', 'world_authority'):
        need(account[key] is False, 'QUALIFIED_SCOPE')
    need(binding['owner_implementation_changed'] is False and
         binding['strict_owner_success_predicate_changed'] is False, 'QUALIFIED_SCOPE')
    core = {'native-android/engine/dbclient/coh_db_session.c',
            'native-android/engine/dbclient/coh_db_session.h'}
    need(set(binding['previous_ordinary_sha256']) == core and
         all(previous[k] == v for k, v in binding['previous_ordinary_sha256'].items()), 'QUALIFIED_SCOPE')
    central = json.loads(pinned(ROOT_LINKS, ROOT_LINKS_BYTES, ROOT_LINKS_SHA))
    owned = json.loads(pinned(OWN_LINKS, OWN_LINKS_BYTES, OWN_LINKS_SHA))
    need(central['passed'] is True and central['source_ast_equal_after_removing_new_parser_dependency'] is True and
         central['compiler_or_native_executed'] is False and central['old_qualifiers_reexecuted'] is False and
         owned['passed'] is True and owned['source_only'] is True and owned['qualifier_or_tests_executed'] is False,
         'QUALIFIED_SCOPE')
    db_tool = 'native-android/engine/dbclient/check.py'
    c_tool = 'native-android/engine/initial-capture/check_initial_editmsg.py'
    peer = 'native-android/engine/initial-capture/test_initial_peer.c'
    updates = {k: current[k] for k in core}
    row = central['files'][db_tool]
    need(row['previous_sha256'] == previous[db_tool] and
         row['only_new_parser_dependency_or_required_source_identity_added'] is True, 'QUALIFIED_SCOPE')
    updates[db_tool] = row['sha256']
    row = owned['files'][c_tool]
    need(row['before_sha256'] == previous[c_tool] and
         row['ast_equals_previous_after_removing_only_new_dependency_literal'] is True, 'QUALIFIED_SCOPE')
    updates[c_tool] = row['after_sha256']
    updates[peer] = build['source_sha256'][peer]
    need(set(updates) == core | {db_tool, c_tool, peer} and
         all(v != previous[k] for k, v in updates.items()), 'QUALIFIED_SCOPE')
    merged = {**previous, **updates}
    for name, pin in current.items():
        need(name not in merged or merged[name] == pin, 'QUALIFIED_SCOPE')
        merged[name] = pin
    new_peer = 'native-android/engine/initial-capture/test_initial_account_peer.c'
    merged[new_peer] = build['source_sha256'][new_peer]
    for name, pin in merged.items():
        need(name not in pins or pins[name] == pin, 'QUALIFIED_SCOPE')
        pins[name] = pin


def evidence(root):
    frozen_metadata()
    review = json.loads(fixed(root, REVIEW + 'review.json', REVIEW_BYTES, REVIEW_SHA))
    gz = fixed(root, OLD + 'build.json.gz', GZIP_BYTES, GZIP_SHA)
    original = gzip.decompress(gz)
    need(len(original) == BUILD_BYTES and digest(original) == BUILD_SHA, 'FIXED_INPUT')
    build = json.loads(original)
    binary = fixed(root, ELF, 180616, ELF_SHA)
    need(review['schema'] == REVIEW_SCHEMA and review['passed'] is True and
         review['historical_build_source_revision'] == build['source_revision'] == HISTORICAL,
         'QUALIFIED_SCOPE')
    need(build['passed'] is True and build['new_account_controls_only'] is True and
         build['new_editmsg_controls_only'] is False and build['old123_controls_reexecuted'] is False and
         build['old151_controls_reexecuted'] is False and build['real_server_capture'] is False and
         build['sends_ready'] is False and build['sends_received_character'] is False and
         build['sends_full_update_ack'] is False, 'QUALIFIED_SCOPE')
    mapping = review['current_project_consumer_dependencies']['sha256']
    need(len(mapping) == 45 and digest(json.dumps(mapping, sort_keys=True, separators=(',', ':')).encode()) == MAP_SHA,
         'CURRENT_45_MAP')
    need(all(build['source_sha256'].get(k) == v for k, v in mapping.items()), 'CURRENT_45_MAP')
    static = review['static_ELF']
    need(static['interpreter'] == INTERPRETER and static['needed'] == NEEDED and
         static['required_versions'] == VERSIONS and static['RPATH'] is False and static['RUNPATH'] is False,
         'ELF_METADATA')
    pins = {ELF: ELF_SHA, OLD + 'build.json.gz': GZIP_SHA, REVIEW + 'review.json': REVIEW_SHA,
            FOLLOWUP: FOLLOWUP_SHA, OBSERVER_BUILD: OBSERVER_BUILD_SHA, OLD_GATE: OLD_GATE_SHA}
    qualified_sources(root, build, pins)
    original_sources = build['original_account_control_fixtures']['whole_source_sha256_lf']
    need(set(original_sources) == {
        'libs/UtilitiesLib/src/components/BitStream.c', 'libs/UtilitiesLib/src/network/net_packet.c',
        'libs/UtilitiesLib/src/network/net_packetutil.c', 'DBServer/src/accountservercomm.c',
        'QueueServer/src/QueueServer_Passthrough.c', 'Game/src/clientcomm/dbclient.c', 'Common/comm_backend.h',
        'AccountServer/src/AccountServer.cpp', 'Game/src/UI/uiServerTransfer.c', 'DBServer/src/clientcomm.c'},
        'ORIGINAL_SOURCE_MAP')
    for relative, lf_sha in original_sources.items():
        name = 'upstream/ouroboros/' + relative
        value = raw(root / name)
        need(digest(value) == build['source_sha256'].get(name) and
             digest(value.replace(b'\r\n', b'\n')) == lf_sha and
             (name not in pins or pins[name] == build['source_sha256'][name]), 'ORIGINAL_SOURCE_MAP')
        pins[name] = build['source_sha256'][name]
    statuses = review['historical_controls']['safe_status_files_verified']
    expected = {f'status-{mode}/{case}.json' for mode in ('release', 'address', 'undefined') for case in CASES}
    need(set(statuses) == expected, 'QUALIFIED_SCOPE')
    for mode in ('release', 'address', 'undefined'):
        tests = build['modes'][mode]['tests']
        need(tests['passed'] is True and tests['checks'] == 28 and tests['scripted_peers_only'] is True and
             tests['new_account_controls_only'] is True and tests['old123_controls_reexecuted'] is False and
             tests['old151_controls_reexecuted'] is False and tests['cases'] == list(CASES) and
             build['modes'][mode]['built'] is True, 'QUALIFIED_SCOPE')
        if mode == 'release':need(build['modes'][mode]['sha256'] == ELF_SHA, 'QUALIFIED_SCOPE')
        for case in CASES:
            name = f'status-{mode}/{case}.json'
            item = statuses[name]
            need(set(item) == {'file', 'bytes', 'sha256', 'repository_path'} and
                 {k: item[k] for k in ('file', 'bytes', 'sha256')} == tests['fixed_status_stdout'][case] and
                 item['file'] == name and item['repository_path'] == STATUS_ROOT + name, 'QUALIFIED_SCOPE')
            fixed(root, STATUS_ROOT + name, item['bytes'], item['sha256'])
            pins[STATUS_ROOT + name] = item['sha256']
    for item in static['readelf_outputs'].values():
        fixed(root, REVIEW + item['file'], item['bytes'], item['sha256'])
        pins[REVIEW + item['file']] = item['sha256']
    # New owner-reason instrumentation requires an actually rebuilt Map PE.
    # Its exact receipt pin remains PENDING until root independently admits it.
    observer = json.loads(fixed(root, OBSERVER_BUILD, OBSERVER_BUILD_BYTES, OBSERVER_BUILD_SHA))
    need(observer['schema'] == 'coh-fresh-groups-observer-compile-v1' and observer['passed'] is True and
         observer['compile_only'] is True and observer['runtime_executed'] is False and
         observer['source_stage_verified'] is True and observer['inherited_source_closure_reverified'] is True and
         observer['accepted_observer_equivalence'] is False and observer['pe_machine'] == 'i386', 'QUALIFIED_SCOPE')
    focused = json.loads(fixed(root, FOLLOWUP, FOLLOWUP_BYTES, FOLLOWUP_SHA))
    fingerprint = focused['compiled_source_fingerprint']['current']
    need(set(fingerprint) == {'source_folder_profile.inc', 'source_folder_profile_api.h',
         'source_group_profile.inc', 'source_group_profile_api.h', 'source_sealed_quiescence.inc', 'stage.py'} and
         fingerprint['stage.py'] == focused['source_sha256'][
             'native-android/engine/scenecatalog-server/fresh_callback_observer/stage.py'], 'OBSERVER_SOURCE')
    # Five compiled members occupy six artifact slots (the folder API appears
    # twice). The staging script is qualified/current source above; the fixed
    # complete compile receipt is separately admitted by the root workflow.
    compiled = {
        'source/Common/seq/coh_fresh_folder_profile_api.h': 'source_folder_profile_api.h',
        'source/libs/UtilitiesLib/src/utils/coh_fresh_folder_profile_api.h': 'source_folder_profile_api.h',
        'source/libs/UtilitiesLib/src/utils/coh_fresh_folder_profile.inc': 'source_folder_profile.inc',
        'source/MapServer/src/group/coh_fresh_source_profile.inc': 'source_group_profile.inc',
        'source/libs/UtilitiesLib/src/utils/coh_fresh_source_profile_api.h': 'source_group_profile_api.h',
        'source/Common/seq/coh_resource_quiescence.inc': 'source_sealed_quiescence.inc'}
    need(all(observer['artifacts'][path]['sha256'] == fingerprint[key] for path, key in compiled.items()),
         'OBSERVER_SOURCE')
    return binary, original, mapping, pins


def admit_gate(root, runner, revision, own_name, artifact_pins):
    frozen_metadata()
    path = runner / 'fresh-groups-source-admission.json'
    gate_raw = raw(path, 256 * 1024)
    gate = json.loads(gate_raw)
    need(type(gate) is dict and set(gate) == GATE_KEYS and gate['schema'] ==
         'coh-account-controls-fresh-groups-live-source-admission-v1' and gate['passed'] is True and
         gate['source_preflight_only'] is True and gate['source_revision'] == revision, 'SOURCE_GATE')
    for key in ('host_controls_reexecuted', 'historical_worker_commit_replayed_in_CI', 'runtime_executed',
                'accepted_observer_equivalence', 'source_generation_admitted', 'world_authority'):
        need(gate[key] is False, 'SOURCE_GATE')
    need(gate['observer_compile_receipt_sha256'] == OBSERVER_BUILD_SHA and
         gate['receiver_build_receipt_sha256'] == BUILD_SHA and
         gate['source_profile_proof_sha256'] == FOLLOWUP_SHA, 'SOURCE_GATE')
    focused = json.loads(fixed(root, FOLLOWUP, FOLLOWUP_BYTES, FOLLOWUP_SHA))
    need(focused['schema'] == PROFILE_SCHEMA and focused['passed'] is True and
         focused['runtime_executed_for_qualification'] is False and
         focused['actual_windows_pe_compiled_for_refinement'] is False and
         focused['native_receiver_reexecuted'] is False and focused['predicate_relaxed'] is False and
         focused['owner_candidate_or_outputs_changed'] is False and focused['source_generation_admitted'] is False and
         focused['world_authority'] is False, 'SOURCE_GATE')
    old = json.loads(fixed(root, OLD_GATE, OLD_GATE_BYTES, OLD_GATE_SHA))['current_278_pin_map']
    need(type(old) is dict and len(old) == 278 and WORKFLOW in old, 'SOURCE_GATE')
    earlier = json.loads(fixed(root, EARLIER_PROFILE, EARLIER_PROFILE_BYTES, EARLIER_PROFILE_SHA))
    need(earlier['passed'] is True and len(earlier['source_sha256']) == 4 and
         set(earlier['previous_source_sha256']) == set(earlier['source_sha256']) and
         all(old[k] == v for k, v in earlier['previous_source_sha256'].items()), 'SOURCE_GATE')
    base = {k: v for k, v in old.items() if k != WORKFLOW}
    base.update(earlier['source_sha256'])
    updates = focused['source_sha256']
    changed = focused['superseded_source_pins']
    need(type(updates) is dict and len(updates) == 40 and len(changed) == 9 and
         all(base.get(k) == row['previous_sha256'] and updates[k] == row['sha256'] for k, row in changed.items()) and
         {k for k, v in updates.items() if k in base and base[k] != v} == set(changed) and
         set(updates).difference(base) == set(focused['added_source_paths']) |
         {'native-android/engine/scenecatalog-server/groups_owner_oracle_shim.h'}, 'SOURCE_GATE')
    owner_review = json.loads(fixed(root, OWNER_REVIEW, OWNER_REVIEW_BYTES, OWNER_REVIEW_SHA))
    need(owner_review['schema'] == 'coh-f-fresh-owner-predicate-source-review-v1' and
         owner_review['passed'] is True and owner_review['followup']['sha256'] == FOLLOWUP_SHA and
         all(owner_review['source_inputs_sha256'].get(k) == v for k, v in updates.items()), 'SOURCE_GATE')
    base.update(updates)
    review = json.loads(fixed(root, REVIEW + 'review.json', REVIEW_BYTES, REVIEW_SHA))
    mapping = review['current_project_consumer_dependencies']['sha256']
    need(len(mapping) == 45 and digest(json.dumps(mapping, sort_keys=True, separators=(',', ':')).encode()) == MAP_SHA,
         'CURRENT_45_MAP')
    allowed = {'native-android/combined-client/tools/check_local_initial_capture.py',
        'native-android/engine/initial-capture/coh_initial_capture.h',
        'native-android/engine/initial-capture/coh_initial_map.c',
        'native-android/engine/dbclient/coh_db_session.c', 'native-android/engine/dbclient/coh_db_session.h',
        'native-android/engine/dbclient/coh_db_account_controls.c', 'native-android/engine/dbclient/coh_db_account_controls.h'}
    need({k for k, v in mapping.items() if base.get(k) != v} == allowed, 'SOURCE_GATE')
    base.update(mapping)
    # The current workflow itself is always checked against the current Git.
    pins = gate['source_sha256']
    extra = {EARLIER_PROFILE: EARLIER_PROFILE_SHA, OWNER_REVIEW: OWNER_REVIEW_SHA}
    need(type(pins) is dict and all(pins.get(k) == v for k, v in base.items()) and
         all(pins.get(k) == v for k, v in {**artifact_pins, **extra}.items()) and
         own_name in pins and WORKFLOW in pins, 'SOURCE_GATE')
    committed(root, pins, revision)
    return path, digest(gate_raw), pins

def static_elf(binary, directory):
    outputs = []
    for flag in ('-h', '-l', '-d', '-V'):
        status, out, error = child(['/usr/bin/readelf', flag, str(binary)], directory, 16384)
        need(status == 0 and not error, 'ELF_METADATA')
        outputs.append(out.decode('ascii'))
    header, segments, dynamic, versions = outputs
    need(re.search(r'Class:\s+ELF64\b', header) and re.search(r'Data:\s+2.s complement, little endian', header)
         and re.search(r'Type:\s+DYN\b', header) and 'Advanced Micro Devices X86-64' in header, 'ELF_METADATA')
    need(re.findall(r'Requesting program interpreter: ([^\]]+)', segments) == [INTERPRETER] and
         re.findall(r'\(NEEDED\).*Shared library: \[([^\]]+)\]', dynamic) == NEEDED and
         not re.search(r'\((?:RPATH|RUNPATH)\)', dynamic) and '(FLAGS)' in dynamic and
         'BIND_NOW' in dynamic and re.search(r'\(FLAGS_1\).*NOW PIE', dynamic), 'ELF_METADATA')
    required, current = {}, None
    need("Version needs section '.gnu.version_r' contains 3 entries:" in versions, 'ELF_METADATA')
    for line in versions.split("Version needs section", 1)[1].splitlines():
        match = re.search(r'File: (\S+)\s+Cnt:', line)
        if match:
            current = match[1]
            need(current not in required, 'ELF_METADATA')
            required[current] = []
        match = re.search(r'Name: (\S+)\s+Flags:', line)
        if match:
            need(current is not None, 'ELF_METADATA')
            required[current].append(match[1])
    need({k: sorted(v) for k, v in required.items()} == VERSIONS, 'ELF_METADATA')

def system_files():
    declared = {name: Path('/lib/x86_64-linux-gnu') / name for name in NEEDED}
    declared['loader'] = Path(INTERPRETER)
    result = {}
    for name, path in declared.items():
        resolved = path.resolve(strict=True)
        info = resolved.stat()
        need(info.st_uid == 0 and not info.st_mode & 0o022 and stat.S_ISREG(info.st_mode), 'SYSTEM_FILES')
        value = raw(resolved, 32 * 1024**2)
        result[name] = {'declared': str(path), 'resolved': str(resolved), 'bytes': len(value),
                        'sha256': digest(value), 'device': info.st_dev, 'inode': info.st_ino}
    return result

def loader_checks(binary, directory, systems):
    need(not os.path.lexists('/etc/ld.so.preload'), 'LOADER_PRELOAD')
    status, out, error = child([INTERPRETER, '--verify', str(binary)], directory, 16384, 10)
    need(status == 0 and not out and not error, 'LOADER_VERIFY')
    status, out, error = child([INTERPRETER, '--list', str(binary)], directory, 16384, 10)
    need(status == 0 and not error, 'LOADER_LIST')
    seen = set()
    for line in out.decode('ascii').splitlines():
        line = line.strip()
        if re.fullmatch(r'linux-vdso\.so\.1 \(0x[0-9a-f]+\)', line):
            name = 'vDSO'
        elif re.fullmatch(re.escape(INTERPRETER) + r' \(0x[0-9a-f]+\)', line):
            name = 'loader'
        else:
            match = re.fullmatch(r'(libz\.so\.1|libcrypto\.so\.3|libc\.so\.6) => (/[^\s]+) \(0x[0-9a-f]+\)', line)
            need(match is not None, 'LOADER_LIST')
            name = match[1]
            need(str(Path(match[2]).resolve(strict=True)) == systems[name]['resolved'], 'LOADER_LIST')
        need(name not in seen, 'LOADER_LIST')
        seen.add(name)
    need(seen == {*NEEDED, 'loader', 'vDSO'}, 'LOADER_LIST')
    status, out, error = child([str(binary)], directory, 16384, 10)
    need(status == 2 and not out and not error, 'NOARGS_SMOKE')

def imported_sources(root, pins):
    for module in tuple(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name:
            path = Path(name).resolve()
            if root in path.parents:
                relative = path.relative_to(root).as_posix()
                need(relative in pins and digest(raw(path)) == pins[relative], 'IMPORTED_SOURCE')

def write_new(path, value, mode):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    owned, failure = None, None
    try:
        identity = os.fstat(fd)
        owned = (identity.st_dev, identity.st_ino)
        os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(value)
            stream.flush()
            os.fsync(fd)
    except BaseException as error:
        failure = error if isinstance(error, Refused) else Refused('OUTPUT_WRITE')
    try:
        os.close(fd)
    except OSError:
        if failure is None:
            failure = Refused('OUTPUT_CLOSE')
    if failure is not None:
        failure.cleanup_verified = owned is not None and unlink_owned(path, owned)
        raise failure
    return owned

def unlink_owned(path, identity):
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or (info.st_dev, info.st_ino) != identity:
            return False
        path.unlink()
        return True
    except FileNotFoundError:
        return True
    except OSError:
        return False

def export_env(path, runner):
    need(path.resolve(strict=True) == path and runner in path.parents, 'ENV_EXPORT')
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
    info, written, failure = None, 0, None
    try:
        info = os.fstat(fd)
        need(stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid() and not info.st_mode & 0o022, 'ENV_EXPORT')
        line = ('INITIAL_BUILD_SHA256=' + BUILD_SHA + '\n').encode()
        written = os.write(fd, line)
        need(written == len(line), 'ENV_EXPORT')
        os.fsync(fd)
    except BaseException:
        failure = Refused('ENV_EXPORT')
    try:
        os.close(fd)
    except BaseException:
        failure = failure or Refused('ENV_EXPORT')
    if failure is not None:
        # Roll back only our exact append; never truncate another writer's data.
        failure.cleanup_verified = False
        if info is not None:
            rollback = None
            try:
                rollback = os.open(path, os.O_WRONLY | os.O_NOFOLLOW)
                current = os.fstat(rollback)
                need((current.st_dev, current.st_ino, current.st_size) ==
                     (info.st_dev, info.st_ino, info.st_size + written), 'ENV_EXPORT')
                os.ftruncate(rollback, info.st_size)
                os.fsync(rollback)
                failure.cleanup_verified = True
            except BaseException:
                pass
            finally:
                if rollback is not None:
                    try:
                        os.close(rollback)
                    except BaseException:
                        failure.cleanup_verified = False
        raise failure

def admit(root, output):
    need(__debug__ and not os.environ.get('PYTHONOPTIMIZE') and sys.platform == 'linux' and
         platform.machine() == 'x86_64' and os.geteuid() != 0 and os.environ.get('GITHUB_ACTIONS') == 'true' and
         os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted' and os.environ.get('RUNNER_OS') == 'Linux' and
         os.environ.get('RUNNER_ARCH') == 'X64' and os.environ.get('GITHUB_REPOSITORY') == 'Russianranger/coh-android'
         and os.environ.get('GITHUB_REF') == 'refs/heads/native-android', 'HOSTED_DESTINATION')
    revision = os.environ.get('GITHUB_SHA', '')
    need(re.fullmatch('[0-9a-f]{40}', revision), 'SOURCE_HEAD')
    need('INITIAL_BUILD_SHA256' not in os.environ, 'ENV_EXPORT')
    root = root.resolve(strict=True)
    own_name = Path(__file__).resolve().relative_to(root).as_posix()
    runner = Path(os.environ['RUNNER_TEMP']).resolve(strict=True)
    need(output.is_absolute() and output.parent.resolve(strict=True) == output.parent and
         runner in output.parents and root not in output.parents and output not in root.parents and
         not os.path.lexists(output), 'PRIVATE_OUTPUT')
    parent = output.parent.stat()
    need(parent.st_uid == os.geteuid() and not parent.st_mode & 0o077, 'PRIVATE_OUTPUT')
    binary_raw, build_raw, mapping, artifact_pins = evidence(root)
    gate_path, gate_sha, pins = admit_gate(root, runner, revision, own_name, artifact_pins)
    need(all(k not in pins or pins[k] == v for k, v in mapping.items()), 'CURRENT_45_MAP')
    pins = {**pins, **mapping}
    committed(root, pins, revision)
    need(not any(getattr(m, '__file__', None) and root in Path(m.__file__).resolve().parents
                 for key, m in sys.modules.items() if key != '__main__'), 'IMPORTED_SOURCE')
    output.mkdir(mode=0o700)
    created = []
    try:
        os.chmod(output, 0o700)
        binary, build = output / BASENAME, output / 'build.json'
        for path, value, mode in ((binary, binary_raw, 0o700), (build, build_raw, 0o600)):
            created.append((path, write_new(path, value, mode)))
        sys.dont_write_bytecode = True
        sys.pycache_prefix = str(output / 'unused-bytecode')
        sys.path.insert(0, str(root / 'native-android/engine/scenecatalog-server'))
        capture = importlib.import_module('capture_groups_transaction')
        need(Path(capture.__file__).resolve() == root / 'native-android/engine/scenecatalog-server/capture_groups_transaction.py',
             'IMPORTED_SOURCE')
        imported_sources(root, pins)
        saved_environment = dict(os.environ)
        try:
            os.environ.clear()
            os.environ.update(CLEAN_ENV)
            native = capture.native_input(binary, build, BUILD_SHA, root)
        except Exception:
            raise Refused('NATIVE_INPUT') from None
        finally:
            os.environ.clear()
            os.environ.update(saved_environment)
        need(native['dependencies_sha256'] == mapping and native['project_dependencies'] == 45 and
             native['source_revision'] == HISTORICAL, 'CURRENT_45_MAP')
        imported_sources(root, pins)
        committed(root, pins, revision)
        static_elf(binary, output)
        systems = system_files()
        loader_checks(binary, output, systems)
        def recheck():
            need(system_files() == systems, 'SYSTEM_FILES_CHANGED')
            need(raw(binary) == binary_raw and raw(build) == build_raw, 'COPY_CHANGED')
            need(evidence(root)[:2] == (binary_raw, build_raw) and digest(raw(gate_path)) == gate_sha, 'LATE_INPUT')
            committed(root, pins, revision)
            imported_sources(root, pins)
        recheck()
        result = {'schema': 'coh-account-controls-initial-receiver-reuse-v1', 'passed': True,
                  'source_revision': revision, 'historical_build_source_revision': HISTORICAL,
                  'original_build_receipt_sha256': BUILD_SHA, 'binary_sha256': ELF_SHA,
                  'project_dependencies': 45, 'dependencies_sha256': mapping,
                  'source_gate_sha256': gate_sha, 'helper_sha256': pins[own_name],
                  'historical_checks_each_mode': 28, 'historical_status_files': 3,
                  'historical_controls_reexecuted': False, 'binary_recompiled': False,
                  'static_elf_interpreter': INTERPRETER, 'static_elf_needed': NEEDED,
                  'static_elf_required_versions': VERSIONS, 'destination_system_files': systems,
                  'loader_verify_passed': True, 'loader_list_passed': True,
                  'noargs_exit_status': 2, 'noargs_stdout_bytes': 0, 'noargs_stderr_bytes': 0,
                  'cleanup_verified': True, 'services_started_by_helper': False,
                  'actual_loaded_mappings_verified': False, 'full_system_or_toolchain_closure_verified': False,
                  'crypto_RNG_or_protocol_functionality_verified': False,
                  'source_generation_admitted': False, 'actor_publication': False,
                  'world_authority': False, 'application_ACK_permitted': False}
        receipt = output / 'receiver-reuse.json'
        receipt_bytes = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode()
        created.append((receipt, write_new(receipt, receipt_bytes, 0o600)))
        recheck()
        need(raw(receipt) == receipt_bytes and {p.name for p in output.iterdir()} ==
             {BASENAME, 'build.json', 'receiver-reuse.json'}, 'REUSE_RECEIPT_CHANGED')
        for path, identity in created:
            info = path.lstat()
            need(stat.S_ISREG(info.st_mode) and (info.st_dev, info.st_ino) == identity and
                 stat.S_IMODE(info.st_mode) == (0o700 if path.name == BASENAME else 0o600), 'COPY_CHANGED')
        export_env(Path(os.environ['GITHUB_ENV']), runner)
        return result
    except BaseException as failure:
        cleanup = getattr(failure, 'cleanup_verified', True)
        for path, identity in reversed(created):
            cleanup = unlink_owned(path, identity) and cleanup
        code = failure.code if isinstance(failure, Refused) else 'RECEIVER_REUSE_REFUSED'
        try:
            write_new(output / 'receiver-reuse.json', (json.dumps({'schema': 'coh-account-controls-initial-receiver-reuse-v1',
                      'passed': False, 'code': code, 'cleanup_verified': cleanup,
                      'services_started_by_helper': False, 'source_generation_admitted': False,
                      'world_authority': False}, sort_keys=True) + '\n').encode(), 0o600)
        except BaseException:
            pass
        raise

def main():
    try:
        values = sys.argv[1:]
        need(len(values) == 4 and set(values[::2]) == {'--source-root', '--output'}, 'ARGUMENTS')
        args = dict(zip(values[::2], values[1::2]))
        admit(Path(args['--source-root']), Path(args['--output']))
        print(json.dumps({'passed': True, 'receiver_reused': True, 'historical_controls_reexecuted': False,
                          'source_generation_admitted': False, 'world_authority': False}, sort_keys=True))
        return 0
    except BaseException as failure:
        code = failure.code if isinstance(failure, Refused) else 'RECEIVER_REUSE_REFUSED'
        print(json.dumps({'passed': False, 'code': code}, sort_keys=True))
        return 1

if __name__ == '__main__':
    sys.exit(main())
