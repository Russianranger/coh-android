#!/usr/bin/env python3
"""Inspect an exact public donor client; never approve a login profile or alias."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import zipfile

from source_audit import decoded, digest, extract

HERE = Path(__file__).resolve().parent


def identity(data, expected):
    if len(data) != expected['bytes'] or digest(data) != expected['sha256']:
        raise ValueError('reference_input_identity_mismatch')


def inspect(root, apk):
    pins = json.loads((HERE / 'client-reference-pins.json').read_text())
    if not apk.is_file() or apk.stat().st_size != pins['donor_apk']['bytes']:
        raise ValueError('reference_donor_size_mismatch')
    apk_data = apk.read_bytes()
    identity(apk_data, pins['donor_apk'])
    with zipfile.ZipFile(io.BytesIO(apk_data)) as outer:
        info = outer.getinfo('assets/runtime/client-runtime.zip')
        if info.file_size != pins['client_runtime_zip']['bytes']:
            raise ValueError('reference_nested_size_mismatch')
        runtime = outer.read(info)
    identity(runtime, pins['client_runtime_zip'])
    with zipfile.ZipFile(io.BytesIO(runtime)) as inner:
        client_info = inner.getinfo('CityOfHeroes.exe')
        package_info = inner.getinfo('client-package.json')
        if client_info.file_size != pins['client_executable']['bytes'] or package_info.file_size > 1024**2:
            raise ValueError('reference_nested_member_size_mismatch')
        client, package_bytes = inner.read(client_info), inner.read(package_info)
        original_alias_present = any(Path(name).name.casefold() == 'ouroboros.exe' for name in inner.namelist())
        version_ini_present = any(Path(name).name.casefold() == 'version.ini' for name in inner.namelist())
    identity(client, pins['client_executable'])
    if digest(package_bytes) != pins['client_package_json_sha256']:
        raise ValueError('reference_package_manifest_mismatch')
    package = json.loads(package_bytes)
    build = package['client_render_queue']['manifest']
    manifest_hash = digest((json.dumps(build, indent=2, sort_keys=True) + '\n').encode())
    if (package['source_commit'] != pins['source_commit'] or build['source_commit'] != pins['source_commit']
            or build['repository_commit'] != pins['reference_build_commit']
            or package['client_render_queue']['manifest_sha256'] != manifest_hash
            or manifest_hash != pins['reference_build_manifest_sha256']):
        raise ValueError('reference_build_source_manifest_mismatch')
    for files in (package['files'], build['files']):
        file = files['CityOfHeroes.exe']
        if file['size'] != len(client) or file['sha256'] != digest(client) or file['pe_machine'] != 332:
            raise ValueError('reference_build_executable_mismatch')
    offset = struct.unpack_from('<I', client, 60)[0]
    if (client[:2] != b'MZ' or offset > len(client) - 96 or client[offset:offset+4] != b'PE\0\0'
            or struct.unpack_from('<H', client, offset+4)[0] != 332
            or struct.unpack_from('<H', client, offset+24)[0] != 0x10b):
        raise ValueError('reference_pe_identity_mismatch')
    original = {}
    for name, expected in pins['original_source_sha256_utf8_lf'].items():
        path = root / name
        data = path.read_bytes() if path.exists() else subprocess.run(['git', '-C', root, 'show', 'HEAD:' + name],
               check=True, capture_output=True, timeout=30).stdout
        value = decoded(data)
        if digest(value.encode()) != expected:
            raise ValueError('reference_original_source_mismatch')
        original[name] = value
    names = {'initGameChecksum': 'Common/ClientLogin/clientcommLogin.c',
             'checksumFile': 'libs/UtilitiesLib/src/version/AppVersion.c',
             'getExecutablePatchVersionInternal': 'libs/UtilitiesLib/src/version/AppVersion.c',
             'getCompatibleGameVersion': 'libs/UtilitiesLib/src/version/AppVersion.c',
             'cryptMD5Update': 'libs/UtilitiesLib/src/network/crypt.cpp',
             'cryptMD5Final': 'libs/UtilitiesLib/src/network/crypt.cpp',
             'dbConnect': 'Game/src/clientcomm/dbclient.c'}
    functions = {name: digest(extract(original['upstream/ouroboros/' + path], name).encode())
                 for name, path in names.items()}
    checksum = hashlib.md5(client).digest()
    return {'schema': 'coh-auth-client-reference-inspection-v1', 'inspection_passed': True,
            'inspection_tool_sha256': digest(Path(__file__).read_bytes()),
            'extraction_helper_sha256': digest((HERE.parent / 'source_oracle.py').read_bytes()),
            'source_audit_helper_sha256': digest((HERE / 'source_audit.py').read_bytes()),
            'pins_file_sha256': digest((HERE / 'client-reference-pins.json').read_bytes()),
            'input_pins': pins, 'original_function_sha256': functions,
            'reference_build_role': build['role'], 'reference_build_manifest_sha256': manifest_hash,
            'reference_client_filename': 'CityOfHeroes.exe', 'whole_file_md5_hex': checksum.hex(),
            'wire_checksum_u32_le': list(struct.unpack('<4I', checksum)),
            'checksum_implementation_executed': 'Python hashlib MD5; original functions audited, not executed here',
            'original_checksum_functions_executed': False,
            'original_alias_present': original_alias_present, 'client_version_ini_present': version_ini_present,
            'proposed_server_reference_filename': 'Ouroboros.exe', 'alias_created': False,
            'native_reference_compatibility_approved': False, 'deployment_profile_admitted': False,
            'nondev_compatible_version_observed': False, 'db_checksum_candidate_built': False,
            'original_client_checksum_rule': 'dbConnect hashes its executing client file; DB init hashes sibling Ouroboros.exe.',
            'blocked_requirements': ['Explicit source-bound native/reference compatibility profile',
                'Verified non-dev getCompatibleGameVersion from the isolated DbServer profile',
                'Separately built fail-closed DbServer candidate and binary negative controls',
                'Actual encrypted AuthServer account exchange and authenticated DB/Map binding'],
            'real_account_login_verified': False, 'physical_thor_accepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--apk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    proof = inspect(args.source_root.resolve(), args.apk)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'inspection_passed': True, 'deployment_profile_admitted': False,
                      'real_account_login_verified': False}))


if __name__ == '__main__':
    main()
