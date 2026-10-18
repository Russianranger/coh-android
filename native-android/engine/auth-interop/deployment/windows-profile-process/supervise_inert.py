"""Execute the admitted39106023132 inert helper once, without rebuilding it.

The only executable selector is the fixed artifact's OwnedProfileProcess.exe;
the only child mode is its fixed inert probe. No service or general command
role is exposed. Caller must use an exclusive disposable GitHub Windows host.
Private paths, exceptions, identities and raw process output never leave this
driver's fixed public projection. Watchdog termination cannot certify removal
of an account/profile created inside a synchronous Windows API call.
"""

import argparse
import ctypes as c
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time


BUILD_REVISION = '362f10cc71148c32b3b84e6c6cbe7ce59ac94480'
SOURCE_PINS = {
    'OwnedProfileProcess.cs': '6d01645e4df2db0564b6b9db3924c4cebb3ff9a590c1d73b422c5e9cce7ef474',
    'InertProfileProbe.cs': '339aa91a99fc3099e421d8a70d16d350c97d1df94728e83c2f1fab367e85a52c',
    'TestOwnedProfileProcess.cs': 'b68929efac7fa145a706524dc4d84e3b6afb6bd29258e636b9902297ca38a378',
    'as-invoker.manifest': '3a462ffbbe724bd1c520e85696599d057e3d2a8f0bb0270d5ec712be20e27331',
    'build-only.ps1': 'cb011af152d2c502b1dfe956cb2704ed0715d8ad4bf75fc3f8b77e88f8278447',
}
BOOL_FIELDS = frozenset('''passed cleanup_complete actual_windows_api_executed
native_backend_selected owned_account_created exact_sid_bound new_private_acl_verified
new_private_desktop_verified created_suspended process_thread_token_identity_verified
owned_job_assigned resume_attempted resume_previous_count_one inert_hkcu_probe_verified
owned_process_exit_observed owned_job_empty_observed owned_process_creation_not_attempted
owned_job_not_created child_observation_handles_closed new_gui_objects_closed
owned_job_handle_closed owned_hives_absent owned_profile_absent owned_account_absent
new_private_tree_absent native_credential_buffer_wiped private_journal_retained
inert_mode_requested probe_build_provenance_verified auth_db_map_or_service_authority_admitted
source_generation_admitted world_authority strict_native_api_deadline_claimed'''.split())
FALSE_ON_SUCCESS = frozenset('''owned_process_creation_not_attempted owned_job_not_created
private_journal_retained probe_build_provenance_verified
auth_db_map_or_service_authority_admitted source_generation_admitted world_authority
strict_native_api_deadline_claimed'''.split())
CAUSES = frozenset('''NONE CALLER FILES ACCOUNT PROFILE DESKTOP JOB LAUNCH IDENTITY ASSIGN
RESUME TIMEOUT PROBE CLEANUP INTERNAL ALREADY_USED'''.split())
TIMEOUT_SECONDS = 180
OUTPUT_LIMIT = 8192
FILE_PHASES = frozenset('''NONE PARENT_CHAIN PARENT_ACL PROBE_CHAIN PROBE_OPEN PROBE_LENGTH
PROBE_BYTES_HASH ROOT_NONCE ROOT_CREATE ROOT_PIN JOURNAL_CREATE JOURNAL_PIN
JOURNAL_ACL JOURNAL_WRITE'''.split())
FILE_OPERATIONS = frozenset('''NONE CHAIN_ATTRIBUTES ACL_READ ACL_PROTECTION ACL_OWNER ACL_RULE ACL_SET
DIRECTORY_ABSENCE DIRECTORY_SDDL DIRECTORY_CREATE DIRECTORY_ACL OPEN_HANDLE OPEN_INFO
SAME_HANDLE SAME_IDENTITY PATH_REOPEN PATH_IDENTITY_COMPARE SOURCE_HASH
BYTES_SIZE BYTES_STREAM BYTES_PROGRESS BYTES_END BYTES_POST
JOURNAL_IDENTITY JOURNAL_SERIALIZE JOURNAL_BYTES JOURNAL_WRITE JOURNAL_RECHECK'''.split())
DIAGNOSTIC_SOURCE_SHA256 = '3f556f65fa8a6182797c2d42bc0d1ea1c0a57aa54b5de058fe1f7a8c6cec2514'
FILE_OWNER_SOURCE_SHA256 = '53add195056ce87c445de347bd6d0fa8996ff3c5842a59a69172587b649ec933'
IDENTITY_SOURCE_SHA256 = '5420ba944a4b933d1067f0997ebd2f96b0c8581768cd885976e7042b415ff48e'
PROFILE_SOURCE_SHA256 = 'ad25eb3dc6202df2bf4b1a271770e3c6555796c32174a083f90568af4a3c5b6b'
IDENTITY_FILE_PHASES = FILE_PHASES | frozenset('''ACCOUNT_INTENT_JOURNAL ACCOUNT_CREATED_JOURNAL
ACCOUNT_SID_JOURNAL ACCOUNT_PROFILE_JOURNAL TARGET_CREATE TARGET_PIN COPY_SOURCE COPY_IMAGE_CREATE
COPY_IMAGE_PIN COPY_IMAGE_BYTES INPUT_CREATE INPUT_PIN RESULT_CREATE RESULT_PIN
IMAGE_ACL INPUT_ACL RESULT_ACL FILES_JOURNAL'''.split())
IDENTITY_FILE_OPERATIONS = FILE_OPERATIONS | frozenset('''IDENTITY_QUERY IDENTITY_VOLUME
IDENTITY_INDEX_HIGH IDENTITY_INDEX_LOW IDENTITY_CREATED IDENTITY_ATTRIBUTES IDENTITY_LINKS'''.split())

PROFILE_FILE_PHASES = IDENTITY_FILE_PHASES | frozenset('''PROFILE_ROOT_QUERY PROFILE_ROOT_PATH
PROFILE_ROOT_CHAIN PROFILE_FRESH_ABSENCE'''.split())
PROFILE_FILE_OPERATIONS = IDENTITY_FILE_OPERATIONS | frozenset('''PATH_FORM PATH_CHARACTER
PATH_CANONICAL CHAIN_ROOT CHAIN_DRIVE MISSING_ATTRIBUTES MISSING_ERROR'''.split())

class Refusal(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise Refusal(code)


def unique_object(pairs):
    result = {}
    for name, value in pairs:
        need(name not in result, 'JSON_DUPLICATE')
        result[name] = value
    return result


def decode_json(raw):
    need(type(raw) is bytes and 0 < len(raw) <= 65536, 'JSON_SIZE')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_object,
                      parse_constant=lambda _: need(False, 'JSON_CONSTANT'))


def parse_receipt(raw, *, file_diagnostic=False, identity_diagnostic=False, profile_diagnostic=False):
    """Strict fixed field/type projection; never promote a failed native receipt."""
    need(type(raw) is bytes and 0 < len(raw) <= OUTPUT_LIMIT, 'RECEIPT_SIZE')
    need(re.fullmatch(rb'[\x20-\x7e]+\r?\n', raw) is not None, 'RECEIPT_ENCODING')
    value = decode_json(raw)
    diagnostic_fields = {'file_phase', 'file_operation'} if file_diagnostic or identity_diagnostic or profile_diagnostic else set()
    need(type(value) is dict and set(value) == BOOL_FIELDS | {
        'schema', 'first_failure', 'first_cleanup_failure'} | diagnostic_fields, 'RECEIPT_FIELDS')
    expected_schema = ('coh-owned-profile-inert-process-profile-path-diagnostic-v1' if profile_diagnostic
                       else 'coh-owned-profile-inert-process-file-identity-diagnostic-v1' if identity_diagnostic
                       else 'coh-owned-profile-inert-process-file-diagnostic-v1' if file_diagnostic
                       else 'coh-owned-profile-inert-process-v1')
    need(value['schema'] == expected_schema, 'RECEIPT_SCHEMA')
    if file_diagnostic or identity_diagnostic or profile_diagnostic:
        phases = PROFILE_FILE_PHASES if profile_diagnostic else IDENTITY_FILE_PHASES if identity_diagnostic else FILE_PHASES
        operations = PROFILE_FILE_OPERATIONS if profile_diagnostic else IDENTITY_FILE_OPERATIONS if identity_diagnostic else FILE_OPERATIONS
        need(value['file_phase'] in phases and value['file_operation'] in operations,
             'RECEIPT_OPERATION')
    need(all(type(value[key]) is bool for key in BOOL_FIELDS), 'RECEIPT_TYPE')
    need(value['first_failure'] in CAUSES and value['first_cleanup_failure'] in CAUSES,
         'RECEIPT_CAUSE')
    need(not value['probe_build_provenance_verified'] and
         not value['auth_db_map_or_service_authority_admitted'] and
         not value['source_generation_admitted'] and not value['world_authority'] and
         not value['strict_native_api_deadline_claimed'], 'RECEIPT_SCOPE')
    if value['passed']:
        need(all(value[name] is (name not in FALSE_ON_SUCCESS) for name in BOOL_FIELDS)
             and value['first_failure'] == value['first_cleanup_failure'] == 'NONE',
             'RECEIPT_CONJUNCTION')
        if file_diagnostic or identity_diagnostic or profile_diagnostic:
            need(value['file_phase'] == value['file_operation'] == 'NONE', 'RECEIPT_SUCCESS_OPERATION')
    # Reconstruct with fixed known keys, including on a native failure.
    return {'schema': value['schema'], **{key: value[key] for key in sorted(BOOL_FIELDS)},
            **{key: value[key] for key in sorted(diagnostic_fields)},
            'first_failure': value['first_failure'],
            'first_cleanup_failure': value['first_cleanup_failure']}


def regular(path, limit):
    path = Path(path).absolute()
    need(path.is_file() and not path.is_symlink(), 'INPUT_FILE')
    for at in (path, *path.parents):
        need(not at.is_symlink() and
             not getattr(at.stat(), 'st_file_attributes', 0) & 0x400, 'REPARSE')
    size = path.stat().st_size
    need(0 < size <= limit, 'INPUT_SIZE')
    return path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def helper_environment(source, *, system_drive=False):
    environment = {name: source[name] for name in
                   ('SystemRoot', 'WINDIR', 'TEMP', 'TMP') if name in source}
    if system_drive:
        drive = source.get('SystemDrive')
        need(type(drive) is str and re.fullmatch('[A-Za-z]:', drive) is not None,
             'SYSTEM_DRIVE_ENVIRONMENT')
        for name in ('SystemRoot', 'WINDIR'):
            directory = source.get(name)
            need(type(directory) is str and len(directory) > 3 and
                 re.match(r'^[A-Za-z]:\\', directory) is not None and
                 directory[:2].casefold() == drive.casefold(), 'SYSTEM_DRIVE_AGREEMENT')
        environment['SystemDrive'] = drive
    return environment


def admit_artifact(directory, source=None):
    """Artifact provenance is additionally bound by root's exact run download."""
    directory = Path(directory).absolute()
    source = Path(source) if source else Path(__file__).resolve().parent
    docs = {name: decode_json(regular(directory / name, 65536).read_bytes()) for name in
            ('source-admission.json', 'build.json', 'summary.json', 'model-status.json')}
    admission, build, summary, model = (docs[name] for name in
        ('source-admission.json', 'build.json', 'summary.json', 'model-status.json'))
    need(admission.get('schema') == 'coh-owned-profile-model-source-admission-v1' and
         admission.get('passed') is True and admission.get('source_revision') == BUILD_REVISION,
         'ARTIFACT_SOURCE')
    need(build.get('schema') == 'coh-owned-profile-inert-build-v1' and
         build.get('passed') is True and build.get('compiler_invocations') == 3 and
         build.get('target') == 'x64' and
         build.get('output_executable_or_model_tests_executed') is False and
         build.get('account_or_profile_or_gui_api_executed') is False, 'ARTIFACT_BUILD')
    need(summary.get('schema') == 'coh-owned-profile-build-model-public-summary-v1' and
         all(summary.get(key) is True for key in
             ('source_admission_passed', 'compile_passed', 'new_model_passed')) and
         summary.get('actual_profile_helper_executed') is False, 'ARTIFACT_SUMMARY')
    need(model.get('schema') == 'coh-owned-profile-process-model-controls-v1' and
         model.get('passed') is True and model.get('model_result_valid') is True and
         model.get('scenarios') == 36 and model.get('actual_windows_api_executed') is False,
         'ARTIFACT_MODEL')
    for name, expected in SOURCE_PINS.items():
        entry = build.get('inputs', {}).get(name, {})
        path = regular(source / name, 1048576)
        need(entry.get('sha256') == expected and entry.get('bytes') == path.stat().st_size
             and sha(path) == expected, 'ARTIFACT_INPUT')
        relative = 'native-android/engine/auth-interop/deployment/windows-profile-process/' + name
        need(admission.get('source_sha256', {}).get(relative) == expected, 'ARTIFACT_SOURCE_PIN')
    images = {}
    for name in ('OwnedProfileProcess.exe', 'InertProfileProbe.exe'):
        path = regular(directory / name, 16 * 1024 * 1024)
        expected = build.get('outputs', {}).get(name, {})
        need(type(expected.get('bytes')) is int and expected['bytes'] == path.stat().st_size
             and re.fullmatch('[0-9a-f]{64}', expected.get('sha256', '')) is not None and
             sha(path) == expected['sha256'], 'ARTIFACT_IMAGE')
        images[name] = (path, expected['sha256'])
    return images


def admit_file_diagnostic(directory):
    directory = Path(directory)/'file-diagnostic'
    receipt = decode_json(regular(directory/'diagnostic-build.json', 65536).read_bytes())
    need(receipt.get('schema') == 'coh-wpp-file-diagnostic-build-v1' and
         receipt.get('passed') is True and receipt.get('compiler_invocations') == 1 and
         receipt.get('original_source_sha256') == SOURCE_PINS['OwnedProfileProcess.cs'] and
         receipt.get('generated_source_sha256') == DIAGNOSTIC_SOURCE_SHA256 and
         receipt.get('generated_source_bytes') == 47405 and
         all(receipt.get(name) is True for name in ('exact_reverse_verified',
             'selected_compiler_files_match_accepted_build')) and
         all(receipt.get(name) is False for name in ('accepted_inert_probe_recompiled',
             'accepted_model_recompiled_or_executed', 'helper_executed',
             'source_generation_admitted', 'world_authority')), 'DIAGNOSTIC_BUILD')
    image = regular(directory/'OwnedProfileProcess.exe', 16*1024*1024)
    expected = receipt.get('helper_image', {})
    need(type(expected.get('bytes')) is int and image.stat().st_size == expected['bytes'] and
         re.fullmatch('[0-9a-f]{64}', expected.get('sha256', '')) is not None and
         sha(image) == expected['sha256'], 'DIAGNOSTIC_IMAGE')
    return image, expected['sha256']


def admit_file_owner(directory):
    directory = Path(directory)/'file-owner'
    receipt = decode_json(regular(directory/'owner-build.json', 65536).read_bytes())
    need(receipt.get('schema') == 'coh-wpp-file-owner-build-v1' and
         receipt.get('passed') is True and receipt.get('compiler_invocations') == 1 and
         receipt.get('original_source_sha256') == SOURCE_PINS['OwnedProfileProcess.cs'] and
         receipt.get('observed_source_sha256') == DIAGNOSTIC_SOURCE_SHA256 and
         receipt.get('generated_source_sha256') == FILE_OWNER_SOURCE_SHA256 and
         receipt.get('generated_source_bytes') == 47790 and
         all(receipt.get(name) is True for name in ('exact_reverse_verified',
             'selected_compiler_files_match_accepted_build', 'explicit_file_security_at_create',
             'existing_owner_acl_identity_guards_preserved')) and
         all(receipt.get(name) is False for name in ('accepted_inert_probe_recompiled',
             'accepted_model_recompiled_or_executed', 'helper_executed',
             'source_generation_admitted', 'world_authority')), 'FILE_OWNER_BUILD')
    image = regular(directory/'OwnedProfileProcess.exe', 16*1024*1024)
    expected = receipt.get('helper_image', {})
    need(type(expected.get('bytes')) is int and image.stat().st_size == expected['bytes'] and
         re.fullmatch('[0-9a-f]{64}', expected.get('sha256', '')) is not None and
         sha(image) == expected['sha256'], 'FILE_OWNER_IMAGE')
    return image, expected['sha256']


def admit_file_identity(directory):
    directory = Path(directory)/'file-identity'
    receipt = decode_json(regular(directory/'identity-build.json', 65536).read_bytes())
    need(receipt.get('schema') == 'coh-wpp-file-identity-build-v1' and
         receipt.get('passed') is True and receipt.get('compiler_invocations') == 1 and
         receipt.get('original_source_sha256') == SOURCE_PINS['OwnedProfileProcess.cs'] and
         receipt.get('observed_source_sha256') == DIAGNOSTIC_SOURCE_SHA256 and
         receipt.get('owner_source_sha256') == FILE_OWNER_SOURCE_SHA256 and
         receipt.get('generated_source_sha256') == IDENTITY_SOURCE_SHA256 and
         receipt.get('generated_source_bytes') == 49689 and
         all(receipt.get(name) is True for name in ('exact_reverse_verified',
             'selected_compiler_files_match_accepted_build', 'explicit_file_security_at_create',
             'existing_owner_acl_identity_guards_preserved', 'identity_observation_only')) and
         all(receipt.get(name) is False for name in ('accepted_inert_probe_recompiled',
             'accepted_model_recompiled_or_executed', 'helper_executed',
             'source_generation_admitted', 'world_authority')), 'FILE_IDENTITY_BUILD')
    image = regular(directory/'OwnedProfileProcess.exe', 16*1024*1024)
    expected = receipt.get('helper_image', {})
    need(type(expected.get('bytes')) is int and image.stat().st_size == expected['bytes'] and
         re.fullmatch('[0-9a-f]{64}', expected.get('sha256', '')) is not None and
         sha(image) == expected['sha256'], 'FILE_IDENTITY_IMAGE')
    return image, expected['sha256']


def admit_profile_path(directory):
    directory = Path(directory)/'profile-path'
    receipt = decode_json(regular(directory/'profile-build.json', 65536).read_bytes())
    need(receipt.get('schema') == 'coh-wpp-profile-path-build-v1' and
         receipt.get('passed') is True and receipt.get('compiler_invocations') == 1 and
         receipt.get('original_source_sha256') == SOURCE_PINS['OwnedProfileProcess.cs'] and
         receipt.get('observed_source_sha256') == DIAGNOSTIC_SOURCE_SHA256 and
         receipt.get('owner_source_sha256') == FILE_OWNER_SOURCE_SHA256 and
         receipt.get('identity_source_sha256') == IDENTITY_SOURCE_SHA256 and
         receipt.get('generated_source_sha256') == PROFILE_SOURCE_SHA256 and
         receipt.get('generated_source_bytes') == 50395 and
         all(receipt.get(name) is True for name in ('exact_reverse_verified',
             'selected_compiler_files_match_accepted_build', 'explicit_file_security_at_create',
             'existing_owner_acl_identity_guards_preserved', 'profile_path_observation_only')) and
         all(receipt.get(name) is False for name in ('accepted_inert_probe_recompiled',
             'accepted_model_recompiled_or_executed', 'helper_executed',
             'source_generation_admitted', 'world_authority')), 'PROFILE_PATH_BUILD')
    image = regular(directory/'OwnedProfileProcess.exe', 16*1024*1024)
    expected = receipt.get('helper_image', {})
    need(type(expected.get('bytes')) is int and image.stat().st_size == expected['bytes'] and
         re.fullmatch('[0-9a-f]{64}', expected.get('sha256', '')) is not None and
         sha(image) == expected['sha256'], 'PROFILE_PATH_IMAGE')
    return image, expected['sha256']


class Native:
    """New outer supervisor, System32 APIs only; no account/profile operations."""
    def __init__(self):
        need(os.name == 'nt' and c.sizeof(c.c_void_p) == 8, 'PLATFORM')
        self.k = c.WinDLL('kernel32.dll', use_last_error=True, winmode=0x0800)
        self.a = c.WinDLL('advapi32.dll', use_last_error=True, winmode=0x0800)
        h, d, b, p = c.c_void_p, c.c_uint32, c.c_int32, c.c_void_p
        signatures = {
            'CreateJobObjectW': ([p, c.c_wchar_p], h),
            'SetInformationJobObject': ([h, c.c_int, p, d], b),
            'AssignProcessToJobObject': ([h, h], b),
            'IsProcessInJob': ([h, h, c.POINTER(b)], b),
            'QueryInformationJobObject': ([h, c.c_int, p, d, c.POINTER(d)], b),
            'TerminateJobObject': ([h, d], b), 'CloseHandle': ([h], b),
            'GetCurrentProcess': ([], h), 'GetDriveTypeW': ([c.c_wchar_p], d),
            'CreateFileW': ([c.c_wchar_p, d, d, p, d, d, h], h),
            'CreateDirectoryW': ([c.c_wchar_p, p], b),
            'LocalFree': ([p], p),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.k, name)
            function.argtypes, function.restype = args, result
        for name, args, result in (
            ('OpenProcessToken', [h, d, c.POINTER(h)], b),
            ('GetTokenInformation', [h, c.c_int, p, d, c.POINTER(d)], b),
            ('ConvertSidToStringSidW', [p, c.POINTER(p)], b),
            ('ConvertStringSecurityDescriptorToSecurityDescriptorW',
             [c.c_wchar_p, d, c.POINTER(p), c.POINTER(d)], b),
        ):
            function = getattr(self.a, name)
            function.argtypes, function.restype = args, result

    def close(self, handle):
        need(bool(self.k.CloseHandle(handle)), 'HANDLE_CLOSE')

    def pin(self, path):
        handle = self.k.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x08000000, None)
        need(handle not in (None, 0, (1 << 64)-1), 'IMAGE_PIN')
        return handle

    def create_parent(self, path):
        path = Path(path).absolute()
        need(not path.exists() and not path.is_symlink() and path.parent.is_dir(), 'PARENT_EXISTS')
        need(path.drive and self.k.GetDriveTypeW(path.anchor) == 3, 'PARENT_DRIVE')
        for at in (path.parent, *path.parent.parents):
            need(not at.is_symlink() and
                 not getattr(at.stat(), 'st_file_attributes', 0) & 0x400, 'PARENT_REPARSE')
        token, text, sd = c.c_void_p(), c.c_void_p(), c.c_void_p()
        try:
            need(self.a.OpenProcessToken(self.k.GetCurrentProcess(), 8, c.byref(token)), 'PARENT_TOKEN')
            buffer, needed = c.create_string_buffer(1024), c.c_uint32()
            need(self.a.GetTokenInformation(token, 1, buffer, len(buffer), c.byref(needed))
                 and 0 < needed.value <= len(buffer), 'PARENT_TOKEN')
            sid = c.cast(buffer, c.POINTER(c.c_void_p))[0]
            need(self.a.ConvertSidToStringSidW(sid, c.byref(text)), 'PARENT_SID')
            value = c.wstring_at(text)
            need(re.fullmatch(r'S-1-5-21-[0-9-]+', value) is not None, 'PARENT_SID')
            sddl = 'O:' + value + 'D:P(A;OICI;FA;;;' + value + ')(A;OICI;FA;;;SY)'
            need(self.a.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                sddl, 1, c.byref(sd), c.byref(needed)), 'PARENT_SD')
            class SA(c.Structure):
                _fields_ = [('length', c.c_uint32), ('sd', c.c_void_p), ('inherit', c.c_int32)]
            security = SA(c.sizeof(SA), sd, 0)
            need(self.k.CreateDirectoryW(str(path), c.byref(security)), 'PARENT_CREATE')
            # The admitted helper independently checks the exact protected DACL.
        finally:
            for value in (sd, text):
                if value.value:
                    need(not self.k.LocalFree(value), 'PARENT_FREE')
            if token.value:
                self.close(token)

    def job(self):
        handle = self.k.CreateJobObjectW(None, None)
        need(bool(handle), 'JOB_CREATE')
        try:
            # Fixed x64 JOBOBJECT_EXTENDED_LIMIT_INFORMATION layout; all other
            # fields zero. No breakaway/process-limit manipulation is enabled.
            data = c.create_string_buffer(144)
            c.c_uint32.from_buffer(data, 16).value = 0x2000
            need(self.k.SetInformationJobObject(handle, 9, data, 144), 'JOB_LIMIT')
            need(self.empty(handle), 'JOB_INITIAL_NOT_EMPTY')
            return handle
        except BaseException:
            self.close(handle)
            raise

    def empty(self, job):
        # Query process IDs AND accounting. A truncated list is never empty.
        data, returned = c.create_string_buffer(72), c.c_uint32()
        need(self.k.QueryInformationJobObject(job, 3, data, len(data), c.byref(returned))
             and 8 <= returned.value <= len(data), 'JOB_LIST')
        assigned = c.c_uint32.from_buffer(data, 0).value
        listed = c.c_uint32.from_buffer(data, 4).value
        need(assigned == listed and listed <= 8, 'JOB_LIST')
        accounting = c.create_string_buffer(48)
        need(self.k.QueryInformationJobObject(job, 1, accounting, 48, c.byref(returned))
             and returned.value == 48, 'JOB_ACCOUNTING')
        active = c.c_uint32.from_buffer(accounting, 40).value
        return assigned == 0 and active == 0

    def assign(self, job, process):
        need(self.empty(job), 'JOB_NOT_EMPTY')
        need(self.k.AssignProcessToJobObject(job, int(process._handle)), 'JOB_ASSIGN')
        inside = c.c_int32()
        need(self.k.IsProcessInJob(int(process._handle), job, c.byref(inside))
             and inside.value, 'JOB_ASSIGN_VERIFY')


class BoundedPipe:
    def __init__(self, stream, limit):
        self.stream, self.limit = stream, limit
        self.data = bytearray()
        self.eof = self.failed = self.overflow = False
        self.thread = threading.Thread(target=self.read, daemon=True)
        self.thread.start()

    def read(self):
        try:
            while True:
                chunk = self.stream.read(1024)
                if not chunk:
                    self.eof = True
                    return
                if len(chunk) > self.limit-len(self.data):
                    self.overflow = True
                    return
                self.data.extend(chunk)
        except BaseException:
            self.failed = True


def execute(artifact, parent, *, file_diagnostic=False, file_owner=False, identity_diagnostic=False, profile_diagnostic=False, profile_system_drive=False):
    status = dict(schema='coh-owned-profile-inert-supervision-v1', passed=False,
                  first_failure='NONE', first_cleanup_failure='NONE',
                  accepted_build_reused=False, compiler_or_model_reexecuted=False,
                  actual_helper_started=False, helper_receipt_valid=False,
                  probe_build_provenance_verified=False, suspended_outer_launch=False,
                  outer_job_assigned=False, outer_resume_observed=False,
                  outer_process_exit_observed=False, outer_job_empty_observed=False,
                  outer_job_handle_closed=False, outer_process_handle_closed=False,
                  image_pins_closed=False, parent_absent=False, timeout=False,
                  inner_cleanup_observed=False, private_journal_may_remain=True,
                  raw_output_exported=False, service_readiness_qualified=False,
                  source_generation_admitted=False, world_authority=False,
                  file_diagnostic_requested=file_diagnostic,
                  explicit_file_owner_requested=file_owner,
                  identity_diagnostic_requested=identity_diagnostic,
                  profile_path_diagnostic_requested=profile_diagnostic,
                  system_drive_environment_requested=profile_system_drive,
                  retained_profile_helper_reused=False,
                  changed_helper_compiled_only=False,
                  accepted_probe_or_model_reexecuted=False,
                  new_helper_compiler_invocations=0)
    native_receipt = None
    native = None
    images = {}
    pins = []
    job = process = None
    pipes = []
    parent_created = False
    stage = 'ARTIFACT_ADMISSION'
    try:
        need(sum(bool(mode) for mode in (file_diagnostic, file_owner, identity_diagnostic, profile_diagnostic, profile_system_drive)) <= 1, 'HELPER_MODE')
        images = admit_artifact(artifact)
        status['accepted_build_reused'] = True
        if profile_system_drive:
            stage = 'RETAINED_PROFILE_ADMISSION'
            images['OwnedProfileProcess.exe'] = admit_profile_path(artifact)
            status['retained_profile_helper_reused'] = True
        if profile_diagnostic:
            stage = 'PROFILE_PATH_ADMISSION'
            images['OwnedProfileProcess.exe'] = admit_profile_path(artifact)
            status['changed_helper_compiled_only'] = True
            status['compiler_or_model_reexecuted'] = True
            status['new_helper_compiler_invocations'] = 1
        if identity_diagnostic:
            stage = 'FILE_IDENTITY_ADMISSION'
            images['OwnedProfileProcess.exe'] = admit_file_identity(artifact)
            status['changed_helper_compiled_only'] = True
            status['compiler_or_model_reexecuted'] = True
            status['new_helper_compiler_invocations'] = 1
        if file_owner:
            stage = 'FILE_OWNER_ADMISSION'
            images['OwnedProfileProcess.exe'] = admit_file_owner(artifact)
            status['changed_helper_compiled_only'] = True
            status['compiler_or_model_reexecuted'] = True
            status['new_helper_compiler_invocations'] = 1
        if file_diagnostic:
            stage = 'DIAGNOSTIC_ADMISSION'
            images['OwnedProfileProcess.exe'] = admit_file_diagnostic(artifact)
            status['changed_helper_compiled_only'] = True
            status['compiler_or_model_reexecuted'] = True
            status['new_helper_compiler_invocations'] = 1
        stage = 'PLATFORM'
        native = Native()
        stage = 'IMAGE_PIN'
        for path, expected in images.values():
            pins.append(native.pin(path))
            need(sha(path) == expected, 'IMAGE_CHANGED')
        stage = 'PRIVATE_PARENT'
        native.create_parent(parent)
        parent_created = True
        stage = 'OUTER_JOB'
        job = native.job()
        stage = 'HELPER_LAUNCH'
        helper, _ = images['OwnedProfileProcess.exe']
        probe, probe_hash = images['InertProfileProbe.exe']
        environment = helper_environment(os.environ, system_drive=profile_system_drive)
        process = subprocess.Popen([str(helper), '--qualify-inert', str(probe), probe_hash,
                                    str(Path(parent).absolute())], cwd=str(helper.parent),
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=environment, close_fds=True,
                                   creationflags=0x00000004 | 0x08000000)
        status['actual_helper_started'] = status['suspended_outer_launch'] = True
        stage = 'OUTER_ASSIGN'
        native.assign(job, process)
        status['outer_job_assigned'] = True
        # Imported only after artifact/host/job admission; root pins this small
        # module in the workflow before executing any project source.
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from windows_suspended_thread import resume_primary
        stage = 'OUTER_RESUME'
        resumed = resume_primary(process)
        status['outer_resume_observed'] = resumed['resume_observed'] is True
        need(resumed['passed'] is True, 'OUTER_RESUME')
        pipes = [BoundedPipe(process.stdout, OUTPUT_LIMIT), BoundedPipe(process.stderr, 0)]
        stage = 'HELPER_WAIT'
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while process.poll() is None or not all(pipe.eof for pipe in pipes):
            need(not any(pipe.failed or pipe.overflow for pipe in pipes), 'HELPER_OUTPUT')
            if time.monotonic() >= deadline:
                status['timeout'] = True
                raise Refusal('HELPER_TIMEOUT')
            time.sleep(0.02)
        status['outer_process_exit_observed'] = True
        stage = 'HELPER_RECEIPT'
        native_receipt = parse_receipt(bytes(pipes[0].data), file_diagnostic=file_diagnostic or file_owner,
                                       identity_diagnostic=identity_diagnostic,
                                       profile_diagnostic=profile_diagnostic or profile_system_drive)
        status['helper_receipt_valid'] = True
        status['inner_cleanup_observed'] = native_receipt['cleanup_complete']
        status['private_journal_may_remain'] = not native_receipt['cleanup_complete']
        need(process.returncode == (0 if native_receipt['passed'] else 1), 'HELPER_EXIT')
        stage = 'HELPER_RESULT'
        need(native_receipt['passed'], 'HELPER_REFUSED')
        stage = 'IMAGE_BRACKET'
        need(all(sha(path) == expected for path, expected in images.values()), 'IMAGE_CHANGED')
        status['probe_build_provenance_verified'] = True
        status['passed'] = True
    except BaseException:
        status['first_failure'] = stage
    finally:
        def cleanup(code, action):
            try:
                action()
            except BaseException:
                status['passed'] = False
                if status['first_cleanup_failure'] == 'NONE':
                    status['first_cleanup_failure'] = code

        def stop_job():
            if not native.empty(job):
                need(native.k.TerminateJobObject(job, 0xC000013A), 'JOB_TERMINATE')
        if job:
            cleanup('OUTER_STOP', stop_job)
        if process:
            def stop_direct():
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=10)
                status['outer_process_exit_observed'] = True
            cleanup('DIRECT_STOP', stop_direct)
        if job:
            def observe_empty():
                deadline = time.monotonic()+10
                while not native.empty(job):
                    need(time.monotonic() < deadline, 'JOB_NOT_EMPTY')
                    time.sleep(0.02)
                status['outer_job_empty_observed'] = True
            cleanup('OUTER_EMPTY', observe_empty)
        for pipe in pipes:
            cleanup('PIPE_JOIN', lambda pipe=pipe: pipe.thread.join(timeout=2))
            if pipe.thread.is_alive():
                status['passed'] = False
                if status['first_cleanup_failure'] == 'NONE':
                    status['first_cleanup_failure'] = 'PIPE_EOF_UNOBSERVED'
        if process:
            def close_process():
                # A reader that did not observe EOF can still own a blocking
                # buffered-read lock. Never block this cleanup on stream.close.
                readers_done = all(not pipe.thread.is_alive() for pipe in pipes)
                for stream in (process.stdout, process.stderr):
                    if stream is not None and readers_done:
                        stream.close()
                need(status['outer_process_exit_observed'], 'PROCESS_LIVE')
                process._handle.Close()
                status['outer_process_handle_closed'] = True
            cleanup('PROCESS_CLOSE', close_process)
        if job:
            def close_job():
                native.close(job)
                status['outer_job_handle_closed'] = True
            cleanup('JOB_CLOSE', close_job)
        for handle in pins:
            cleanup('IMAGE_CLOSE', lambda handle=handle: native.close(handle))
        status['image_pins_closed'] = bool(pins) and status['first_cleanup_failure'] == 'NONE'
        if parent_created and status['inner_cleanup_observed'] and status['outer_process_exit_observed'] and status['outer_job_empty_observed']:
            def retire_parent():
                # Never recurse, enumerate private identities, or delete a journal.
                Path(parent).rmdir()
                status['parent_absent'] = not Path(parent).exists()
            cleanup('PARENT_RETIRE', retire_parent)
        if status['passed']:
            status['passed'] = all(status[key] is True for key in (
                'helper_receipt_valid', 'probe_build_provenance_verified',
                'outer_process_exit_observed', 'outer_job_empty_observed',
                'outer_job_handle_closed', 'outer_process_handle_closed',
                'image_pins_closed', 'parent_absent', 'inner_cleanup_observed'))
    return status, native_receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact-dir', type=Path, required=True)
    parser.add_argument('--private-parent', type=Path, required=True)
    parser.add_argument('--public-out', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--file-diagnostic', action='store_true')
    mode.add_argument('--file-owner', action='store_true')
    mode.add_argument('--file-identity-diagnostic', action='store_true')
    mode.add_argument('--profile-path-diagnostic', action='store_true')
    mode.add_argument('--profile-system-drive', action='store_true')
    args = parser.parse_args()
    # Before mutation, require the explicit disposable CI host and a fresh
    # public directory. No username/SID/profile/packet/log selector is accepted.
    need(os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted' and
         os.environ.get('RUNNER_OS') == 'Windows' and os.environ.get('RUNNER_ARCH') == 'X64' and
         os.environ.get('GITHUB_REPOSITORY') == 'Russianranger/coh-android' and
         os.environ.get('GITHUB_REF') == 'refs/heads/native-android', 'HOST')
    args.public_out.mkdir(parents=False, exist_ok=False)
    status, native_receipt = execute(args.artifact_dir, args.private_parent,
                                     file_diagnostic=args.file_diagnostic, file_owner=args.file_owner,
                                     identity_diagnostic=args.file_identity_diagnostic,
                                     profile_diagnostic=args.profile_path_diagnostic,
                                     profile_system_drive=args.profile_system_drive)
    (args.public_out/'supervision.json').write_text(json.dumps(status, indent=2)+'\n', encoding='utf-8')
    if native_receipt is not None:
        (args.public_out/'inert-result.json').write_text(json.dumps(native_receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'inert_helper_passed': status['passed'],
                      'first_failure': status['first_failure'],
                      'first_cleanup_failure': status['first_cleanup_failure'],
                      'service_readiness_qualified': False}, separators=(',', ':')))
    return 0 if status['passed'] else 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        # Even orchestration/input errors cannot echo private arguments/errors.
        print('{"inert_helper_passed":false,"first_failure":"DRIVER_INPUT","raw_output_exported":false}')
        sys.exit(2)
