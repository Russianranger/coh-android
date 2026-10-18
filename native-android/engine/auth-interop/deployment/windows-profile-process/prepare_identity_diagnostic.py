"""Add only fixed Account/Files phases and first identity-mismatch observation.

The explicit CreateNew owner/DACL repair, predicates, API order and cleanup are
unchanged. Exact reversal yields the actual39152328268 owner successor. No raw
path, SID, file metadata, credential, error number or exception text is added.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


BASE_OWNER_SHA256 = '53add195056ce87c445de347bd6d0fa8996ff3c5842a59a69172587b649ec933'
EXTRA_PHASES = '''ACCOUNT_INTENT_JOURNAL ACCOUNT_CREATED_JOURNAL ACCOUNT_SID_JOURNAL
ACCOUNT_PROFILE_JOURNAL TARGET_CREATE TARGET_PIN COPY_SOURCE COPY_IMAGE_CREATE
COPY_IMAGE_PIN COPY_IMAGE_BYTES INPUT_CREATE INPUT_PIN RESULT_CREATE RESULT_PIN
IMAGE_ACL INPUT_ACL RESULT_ACL FILES_JOURNAL'''.split()
EXTRA_OPERATIONS = '''IDENTITY_QUERY IDENTITY_VOLUME IDENTITY_INDEX_HIGH
IDENTITY_INDEX_LOW IDENTITY_CREATED IDENTITY_ATTRIBUTES IDENTITY_LINKS'''.split()


def load(name, filename):
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replacements():
    observation = load('identity_observation_predecessor', 'prepare_file_diagnostic.py')
    phases = ','.join(observation.PHASES)
    operations = ','.join(observation.OPERATIONS)
    changes = [
        (' public enum FilePhase { '+phases+' }',
         ' public enum FilePhase { '+phases+','+','.join(EXTRA_PHASES)+' }'),
        (' public enum FileOperation { '+operations+' }',
         ' public enum FileOperation { '+operations+','+','.join(EXTRA_OPERATIONS)+' }'),
        ('coh-owned-profile-inert-process-file-diagnostic-v1',
         'coh-owned-profile-inert-process-file-identity-diagnostic-v1'),
        ('  internal static void Latch(Receipt r){r.filePhase=Phase;r.fileOperation=Operation;}',
         '  internal static FileOperation Mismatch=FileOperation.NONE;\n'
         '  internal static bool Match(bool value,FileOperation operation){if(!value&&Mismatch==FileOperation.NONE)Mismatch=operation;return value;}\n'
         '  internal static void Latch(Receipt r){r.filePhase=Phase;r.fileOperation=Mismatch==FileOperation.NONE?Operation:Mismatch;}'),
        ('Need(FileDiagnostic.Result(N.GetFileInformationByHandle(h,out b)&&Equal(b)&&PathIdentitySame(),FileOperation.SAME_IDENTITY),Cause.FILES);',
         'Need(FileDiagnostic.Result(FileDiagnostic.Match(N.GetFileInformationByHandle(h,out b),FileOperation.IDENTITY_QUERY)&&Equal(b)&&PathIdentitySame(),FileOperation.SAME_IDENTITY),Cause.FILES);'),
    ]
    for expression, operation in (
        ('b.volume==Info.volume', 'IDENTITY_VOLUME'),
        ('b.indexHi==Info.indexHi', 'IDENTITY_INDEX_HIGH'),
        ('b.indexLo==Info.indexLo', 'IDENTITY_INDEX_LOW'),
        ('b.created.Value==Info.created.Value', 'IDENTITY_CREATED'),
        ('b.attrs==Info.attrs', 'IDENTITY_ATTRIBUTES'),
        ('b.links==Info.links', 'IDENTITY_LINKS'),
    ):
        changes.append((expression, 'FileDiagnostic.Match('+expression+',FileOperation.'+operation+')'))
    for old, new in (
        ('accountAddAttempted=true;Journal();',
         'accountAddAttempted=true;FileDiagnostic.At(FilePhase.ACCOUNT_INTENT_JOURNAL);Journal();'),
        ('accountOwned=true;r.accountCreated=true;Journal();',
         'accountOwned=true;r.accountCreated=true;FileDiagnostic.At(FilePhase.ACCOUNT_CREATED_JOURNAL);Journal();'),
        ('r.sidBound=true;Journal();',
         'r.sidBound=true;FileDiagnostic.At(FilePhase.ACCOUNT_SID_JOURNAL);Journal();'),
        ('Need(Missing(profile)&&ProfileRegistrationAbsent()&&HiveAbsent(),Cause.PROFILE);Journal();',
         'Need(Missing(profile)&&ProfileRegistrationAbsent()&&HiveAbsent(),Cause.PROFILE);FileDiagnostic.At(FilePhase.ACCOUNT_PROFILE_JOURNAL);Journal();\n   FileDiagnostic.At(FilePhase.NONE);'),
        ('MakeDir(target,true,delegate{targetOwned=true;});targetPin=Pin.Open(target,true,false);',
         'FileDiagnostic.At(FilePhase.TARGET_CREATE);MakeDir(target,true,delegate{targetOwned=true;});\n   FileDiagnostic.At(FilePhase.TARGET_PIN);targetPin=Pin.Open(target,true,false);'),
        ('byte[] imageBytes=sourcePin.Bytes(16*1024*1024);',
         'FileDiagnostic.At(FilePhase.COPY_SOURCE);byte[] imageBytes=sourcePin.Bytes(16*1024*1024);'),
        ('using(FileStream s=NewFile(image,true,false,FileShare.Read))',
         'FileDiagnostic.At(FilePhase.COPY_IMAGE_CREATE);using(FileStream s=NewFile(image,true,false,FileShare.Read))'),
        ('imagePin=Pin.Open(image,false,false);Need(Hash(imagePin.Bytes(16*1024*1024))==expectedHash,Cause.FILES);',
         'FileDiagnostic.At(FilePhase.COPY_IMAGE_PIN);imagePin=Pin.Open(image,false,false);\n   FileDiagnostic.At(FilePhase.COPY_IMAGE_BYTES);Need(Hash(imagePin.Bytes(16*1024*1024))==expectedHash,Cause.FILES);'),
        ('using(FileStream f=NewFile(Path.Combine(target,"probe.input"),true,false,FileShare.Read))',
         'FileDiagnostic.At(FilePhase.INPUT_CREATE);using(FileStream f=NewFile(Path.Combine(target,"probe.input"),true,false,FileShare.Read))'),
        ('inputPin=Pin.Open(Path.Combine(target,"probe.input"),false,false);',
         'FileDiagnostic.At(FilePhase.INPUT_PIN);inputPin=Pin.Open(Path.Combine(target,"probe.input"),false,false);'),
        ('using(FileStream f=NewFile(Path.Combine(target,"probe.result"),true,false,FileShare.ReadWrite))',
         'FileDiagnostic.At(FilePhase.RESULT_CREATE);using(FileStream f=NewFile(Path.Combine(target,"probe.result"),true,false,FileShare.ReadWrite))'),
        ('resultPin=Pin.Open(Path.Combine(target,"probe.result"),false,true);',
         'FileDiagnostic.At(FilePhase.RESULT_PIN);resultPin=Pin.Open(Path.Combine(target,"probe.result"),false,true);'),
        ('Acl(image,true,true);Acl(inputPin.Path,true,true);Acl(resultPin.Path,true,true);',
         'FileDiagnostic.At(FilePhase.IMAGE_ACL);Acl(image,true,true);\n   FileDiagnostic.At(FilePhase.INPUT_ACL);Acl(inputPin.Path,true,true);\n   FileDiagnostic.At(FilePhase.RESULT_ACL);Acl(resultPin.Path,true,true);'),
        ('r.privateAcl=true;Journal();',
         'r.privateAcl=true;FileDiagnostic.At(FilePhase.FILES_JOURNAL);Journal();\n   FileDiagnostic.At(FilePhase.NONE);'),
    ):
        changes.append((old, new))
    return changes


def prepare(owner):
    if hashlib.sha256(owner).hexdigest() != BASE_OWNER_SHA256:
        raise ValueError('OWNER_SOURCE_REFUSED')
    source = owner.decode('utf-8')
    changes = replacements()
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('IDENTITY_INSERTION_REFUSED')
        source = source.replace(old, new, 1)
    reverse = source
    for old, new in reversed(changes):
        if reverse.count(new) != 1:
            raise ValueError('IDENTITY_REVERSE_REFUSED')
        reverse = reverse.replace(new, old, 1)
    if reverse.encode('utf-8') != owner:
        raise ValueError('OWNER_REVERSAL_REFUSED')
    return source.encode('utf-8')


def source_bytes():
    owner = load('identity_owner_predecessor', 'prepare_file_owner.py')
    return owner.prepare(owner.source_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    owner = source_bytes()
    generated = prepare(owner)
    args.out_dir.mkdir(exist_ok=False)
    (args.out_dir/'OwnedProfileProcessIdentityDiagnostic.cs').write_bytes(generated)
    receipt = dict(schema='coh-wpp-file-identity-preparation-v1', passed=True,
                   owner_source_sha256=BASE_OWNER_SHA256,
                   generated_source_sha256=hashlib.sha256(generated).hexdigest(),
                   generated_source_bytes=len(generated), replacements=len(replacements()),
                   exact_reverse_verified=True, identity_observation_only=True,
                   existing_owner_acl_identity_guards_preserved=True,
                   compiler_or_helper_or_model_executed=False)
    (args.out_dir/'preparation.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, separators=(',', ':')))


if __name__ == '__main__':
    main()
