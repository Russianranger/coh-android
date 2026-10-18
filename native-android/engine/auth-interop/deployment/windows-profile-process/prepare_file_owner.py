"""Create the narrow atomic file-security successor of the observed helper.

The accepted original helper and the observation-only generator remain exact.
Only four NEW file creations use the existing explicit runner/SYSTEM[/target]
security descriptor, rather than a token-default file owner. Existing owner,
DACL, path, identity, hashing, one-shot launch and cleanup predicates remain.
No compiler, Windows API, probe, model or service executes in this preparation.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


BASE_DIAGNOSTIC_SHA256 = '3f556f65fa8a6182797c2d42bc0d1ea1c0a57aa54b5de058fe1f7a8c6cec2514'


def replacements():
    return [
        ('  void Journal() {\n',
         '  FileStream NewFile(string path,bool withTarget,bool readable,FileShare share) {\n'
         '   // Supply owner and protected DACL atomically with CREATE_NEW.\n'
         '   // An elevated token default owner need not be the runner user.\n'
         '   FileSecurity security=new FileSecurity();\n'
         '   security.SetSecurityDescriptorSddlForm(Sddl(withTarget));\n'
         '   FileSystemRights rights=FileSystemRights.Write;\n'
         '   if(readable)rights|=FileSystemRights.Read;\n'
         '   return new FileStream(path,FileMode.CreateNew,rights,share,4096,FileOptions.None,security);\n'
         '  }\n'
         '  void Journal() {\n'),
        ('journal=new FileStream(Path.Combine(root,"owner.private"),FileMode.CreateNew,FileAccess.ReadWrite,FileShare.Read);',
         'journal=NewFile(Path.Combine(root,"owner.private"),false,true,FileShare.Read);'),
        ('using(FileStream s=new FileStream(image,FileMode.CreateNew,FileAccess.Write,FileShare.Read))',
         'using(FileStream s=NewFile(image,true,false,FileShare.Read))'),
        ('using(FileStream f=new FileStream(Path.Combine(target,"probe.input"),FileMode.CreateNew,FileAccess.Write,FileShare.Read))',
         'using(FileStream f=NewFile(Path.Combine(target,"probe.input"),true,false,FileShare.Read))'),
        ('using(FileStream f=new FileStream(Path.Combine(target,"probe.result"),FileMode.CreateNew,FileAccess.Write,FileShare.ReadWrite))',
         'using(FileStream f=NewFile(Path.Combine(target,"probe.result"),true,false,FileShare.ReadWrite))'),
    ]


def prepare(observed):
    if hashlib.sha256(observed).hexdigest() != BASE_DIAGNOSTIC_SHA256:
        raise ValueError('OBSERVED_SOURCE_REFUSED')
    source = observed.decode('utf-8')
    changes = replacements()
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('OWNER_INSERTION_REFUSED')
        source = source.replace(old, new, 1)
    reverse = source
    for old, new in reversed(changes):
        if reverse.count(new) != 1:
            raise ValueError('OWNER_REVERSE_REFUSED')
        reverse = reverse.replace(new, old, 1)
    if reverse.encode('utf-8') != observed:
        raise ValueError('OBSERVED_REVERSAL_REFUSED')
    return source.encode('utf-8')


def source_bytes():
    path = Path(__file__).with_name('prepare_file_diagnostic.py')
    spec = importlib.util.spec_from_file_location('observed_file_preparation', path)
    observation = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(observation)
    return observation.prepare(path.with_name('OwnedProfileProcess.cs').read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    observed = source_bytes()
    generated = prepare(observed)
    args.out_dir.mkdir(exist_ok=False)
    (args.out_dir/'OwnedProfileProcessFileOwner.cs').write_bytes(generated)
    receipt = dict(schema='coh-wpp-file-owner-preparation-v1', passed=True,
                   observed_source_sha256=BASE_DIAGNOSTIC_SHA256,
                   generated_source_sha256=hashlib.sha256(generated).hexdigest(),
                   generated_source_bytes=len(generated), replacements=len(replacements()),
                   exact_reverse_verified=True, explicit_file_security_at_create=True,
                   existing_owner_acl_identity_guards_preserved=True,
                   compiler_or_helper_or_model_executed=False)
    (args.out_dir/'preparation.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, separators=(',', ':')))


if __name__ == '__main__':
    main()
