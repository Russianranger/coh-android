"""Observe profile path/chain preconditions without changing environment/guards."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

BASE_IDENTITY_SHA256 = '5420ba944a4b933d1067f0997ebd2f96b0c8581768cd885976e7042b415ff48e'
EXTRA_PHASES = ['PROFILE_ROOT_QUERY', 'PROFILE_ROOT_PATH', 'PROFILE_ROOT_CHAIN', 'PROFILE_FRESH_ABSENCE']
EXTRA_OPERATIONS = ['PATH_FORM', 'PATH_CHARACTER', 'PATH_CANONICAL', 'CHAIN_ROOT', 'CHAIN_DRIVE', 'MISSING_ATTRIBUTES', 'MISSING_ERROR']


def load():
    path = Path(__file__).with_name('prepare_identity_diagnostic.py')
    spec = importlib.util.spec_from_file_location('profile_identity_predecessor', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replacements():
    identity = load()
    observation = identity.load('profile_observation_predecessor', 'prepare_file_diagnostic.py')
    phases = ','.join(observation.PHASES+identity.EXTRA_PHASES)
    operations = ','.join(observation.OPERATIONS+identity.EXTRA_OPERATIONS)
    return [
        (' public enum FilePhase { '+phases+' }', ' public enum FilePhase { '+phases+','+','.join(EXTRA_PHASES)+' }'),
        (' public enum FileOperation { '+operations+' }', ' public enum FileOperation { '+operations+','+','.join(EXTRA_OPERATIONS)+' }'),
        ('coh-owned-profile-inert-process-file-identity-diagnostic-v1', 'coh-owned-profile-inert-process-profile-path-diagnostic-v1'),
        ('   Need(p!=null&&p.Length>3', '   FileDiagnostic.Op(FileOperation.PATH_FORM);Need(p!=null&&p.Length>3'),
        ('   foreach(char c in p)Need(c>31', '   foreach(char c in p){FileDiagnostic.Op(FileOperation.PATH_CHARACTER);Need(c>31'),
        ('c!=\'|\',Cause.FILES);\n   Need(p.IndexOf', 'c!=\'|\',Cause.FILES);}\n   FileDiagnostic.Op(FileOperation.PATH_CANONICAL);Need(p.IndexOf'),
        ('   string at=Path.GetPathRoot(p);Need(at.Length==3&&N.GetDriveTypeW(at)==3,Cause.FILES);',
         '   string at=Path.GetPathRoot(p);Need(FileDiagnostic.Match(at.Length==3,FileOperation.CHAIN_ROOT)&&FileDiagnostic.Match(N.GetDriveTypeW(at)==3,FileOperation.CHAIN_DRIVE),Cause.FILES);'),
        ('   uint a=N.GetFileAttributesW(p);if(a!=UInt32.MaxValue)return false;',
         '   FileDiagnostic.Op(FileOperation.MISSING_ATTRIBUTES);uint a=N.GetFileAttributesW(p);if(a!=UInt32.MaxValue)return false;'),
        ('   int e=Marshal.GetLastWin32Error();Need(e==2||e==3,Cause.FILES);return true;',
         '   int e=Marshal.GetLastWin32Error();FileDiagnostic.Op(FileOperation.MISSING_ERROR);Need(e==2||e==3,Cause.FILES);return true;'),
        ('   uint cap=260;StringBuilder p=new StringBuilder(260);\n   Need(N.GetProfilesDirectoryW(p,ref cap),Cause.PROFILE);',
         '   FileDiagnostic.At(FilePhase.PROFILE_ROOT_QUERY);uint cap=260;StringBuilder p=new StringBuilder(260);\n   Need(N.GetProfilesDirectoryW(p,ref cap),Cause.PROFILE);'),
        ('   string profiles=PathLocal(p.ToString());Chain(profiles);profile=Path.Combine(profiles,user);',
         '   FileDiagnostic.At(FilePhase.PROFILE_ROOT_PATH);string profiles=PathLocal(p.ToString());\n   FileDiagnostic.At(FilePhase.PROFILE_ROOT_CHAIN);Chain(profiles);profile=Path.Combine(profiles,user);'),
        ('   Need(Missing(profile)&&ProfileRegistrationAbsent()&&HiveAbsent(),Cause.PROFILE);',
         '   FileDiagnostic.At(FilePhase.PROFILE_FRESH_ABSENCE);Need(Missing(profile)&&ProfileRegistrationAbsent()&&HiveAbsent(),Cause.PROFILE);'),
    ]


def prepare(original):
    if hashlib.sha256(original).hexdigest() != BASE_IDENTITY_SHA256:
        raise ValueError('IDENTITY_SOURCE_REFUSED')
    source = original.decode('utf-8')
    changes = replacements()
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('PROFILE_INSERTION_REFUSED')
        source = source.replace(old, new, 1)
    reverse = source
    for old, new in reversed(changes):
        if reverse.count(new) != 1:
            raise ValueError('PROFILE_REVERSE_REFUSED')
        reverse = reverse.replace(new, old, 1)
    if reverse.encode('utf-8') != original:
        raise ValueError('IDENTITY_REVERSAL_REFUSED')
    return source.encode('utf-8')


def source_bytes():
    identity = load()
    return identity.prepare(identity.source_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    generated = prepare(source_bytes())
    args.out_dir.mkdir(exist_ok=False)
    (args.out_dir/'OwnedProfileProcessProfileDiagnostic.cs').write_bytes(generated)
    receipt = dict(schema='coh-wpp-profile-path-preparation-v1', passed=True,
                   identity_source_sha256=BASE_IDENTITY_SHA256,
                   generated_source_sha256=hashlib.sha256(generated).hexdigest(),
                   generated_source_bytes=len(generated), replacements=len(replacements()),
                   exact_reverse_verified=True, profile_path_observation_only=True,
                   existing_owner_acl_identity_guards_preserved=True,
                   compiler_or_helper_or_model_executed=False)
    (args.out_dir/'preparation.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, separators=(',', ':')))


if __name__ == '__main__':
    main()
