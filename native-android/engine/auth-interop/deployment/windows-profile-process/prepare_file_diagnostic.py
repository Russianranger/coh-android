"""Generate a fixed observation-only helper successor from exact admitted source.

The original helper/probe/model/build files remain unchanged. All replacements
are exact one-occurrence insertions or the explicit diagnostic schema suffix.
Reversing every replacement must reproduce the admitted original bytes exactly.
No Windows API, compiler, model or helper is executed by this preparation.
"""

import argparse
import hashlib
import json
from pathlib import Path


BASE_SHA256 = '6d01645e4df2db0564b6b9db3924c4cebb3ff9a590c1d73b422c5e9cce7ef474'
PHASES = '''NONE PARENT_CHAIN PARENT_ACL PROBE_CHAIN PROBE_OPEN PROBE_LENGTH
PROBE_BYTES_HASH ROOT_NONCE ROOT_CREATE ROOT_PIN JOURNAL_CREATE JOURNAL_PIN
JOURNAL_ACL JOURNAL_WRITE'''.split()
OPERATIONS = '''NONE CHAIN_ATTRIBUTES ACL_READ ACL_PROTECTION ACL_OWNER ACL_RULE ACL_SET
DIRECTORY_ABSENCE DIRECTORY_SDDL DIRECTORY_CREATE DIRECTORY_ACL OPEN_HANDLE OPEN_INFO
SAME_HANDLE SAME_IDENTITY PATH_REOPEN PATH_IDENTITY_COMPARE SOURCE_HASH
BYTES_SIZE BYTES_STREAM BYTES_PROGRESS BYTES_END BYTES_POST
JOURNAL_IDENTITY JOURNAL_SERIALIZE JOURNAL_BYTES JOURNAL_WRITE JOURNAL_RECHECK'''.split()


def replacements():
    changes = []

    def add(old, new):
        changes.append((old, new))

    declarations = (' public enum FilePhase { ' + ','.join(PHASES) + ' }\n' +
                    ' public enum FileOperation { ' + ','.join(OPERATIONS) + ' }\n' +
                    ' internal static class FileDiagnostic {\n' +
                    '  internal static FilePhase Phase=FilePhase.NONE;\n' +
                    '  internal static FileOperation Operation=FileOperation.NONE;\n' +
                    '  internal static void At(FilePhase phase){Phase=phase;Operation=FileOperation.NONE;}\n' +
                    '  internal static void Op(FileOperation operation){Operation=operation;}\n' +
                    '  internal static bool Result(bool value,FileOperation operation){Operation=operation;return value;}\n' +
                    '  internal static void Latch(Receipt r){r.filePhase=Phase;r.fileOperation=Operation;}\n' +
                    ' }\n')
    add(' public sealed class Receipt {\n', declarations + ' public sealed class Receipt {\n' +
        '  public FilePhase filePhase=FilePhase.NONE;public FileOperation fileOperation=FileOperation.NONE;\n')
    add('coh-owned-profile-inert-process-v1', 'coh-owned-profile-inert-process-file-diagnostic-v1')
    add('   return "{\\"schema\\":',
        '   return "{\\"file_phase\\":\\""+filePhase+"\\",\\"file_operation\\":\\""+fileOperation+"\\",\\"schema\\":')
    add('   } catch(Refusal e) { r.first=e.Code; }\n   catch { r.first=Cause.INTERNAL; }',
        '   } catch(Refusal e) { FileDiagnostic.Latch(r);r.first=e.Code; }\n   catch { FileDiagnostic.Latch(r);r.first=Cause.INTERNAL; }')
    add('   Chain(parent);Acl(parent,false,false);Chain(probePath);\n   sourcePin=Pin.Open(probePath,false,false);Need(sourcePin.Info.Length>0&&sourcePin.Info.Length<=16*1024*1024,Cause.FILES);\n   Need(Hash(sourcePin.Bytes(16*1024*1024))==expectedHash,Cause.FILES);',
        '   FileDiagnostic.At(FilePhase.PARENT_CHAIN);Chain(parent);\n   FileDiagnostic.At(FilePhase.PARENT_ACL);Acl(parent,false,false);\n   FileDiagnostic.At(FilePhase.PROBE_CHAIN);Chain(probePath);\n   FileDiagnostic.At(FilePhase.PROBE_OPEN);sourcePin=Pin.Open(probePath,false,false);\n   FileDiagnostic.At(FilePhase.PROBE_LENGTH);Need(sourcePin.Info.Length>0&&sourcePin.Info.Length<=16*1024*1024,Cause.FILES);\n   FileDiagnostic.At(FilePhase.PROBE_BYTES_HASH);Need(Hash(sourcePin.Bytes(16*1024*1024))==expectedHash,Cause.FILES);\n   FileDiagnostic.At(FilePhase.NONE);')
    add('   nonce=new byte[16];using(RandomNumberGenerator g=RandomNumberGenerator.Create())g.GetBytes(nonce);',
        '   FileDiagnostic.At(FilePhase.ROOT_NONCE);nonce=new byte[16];using(RandomNumberGenerator g=RandomNumberGenerator.Create())g.GetBytes(nonce);')
    add('Need(Hash(sourcePin.Bytes(16*1024*1024))==expectedHash,Cause.FILES);',
        'Need(FileDiagnostic.Result(Hash(sourcePin.Bytes(16*1024*1024))==expectedHash,FileOperation.SOURCE_HASH),Cause.FILES);')
    add('   MakeDir(root,false,delegate{rootOwned=true;});rootPin=Pin.Open(root,true,false);',
        '   FileDiagnostic.At(FilePhase.ROOT_CREATE);MakeDir(root,false,delegate{rootOwned=true;});\n   FileDiagnostic.At(FilePhase.ROOT_PIN);rootPin=Pin.Open(root,true,false);')
    add('   journal=new FileStream(Path.Combine(root,"owner.private"),FileMode.CreateNew,FileAccess.ReadWrite,FileShare.Read);\n   journalPin=Pin.Open(Path.Combine(root,"owner.private"),false,true);\n   Acl(journalPin.Path,false,true);\n   Journal();',
        '   FileDiagnostic.At(FilePhase.JOURNAL_CREATE);journal=new FileStream(Path.Combine(root,"owner.private"),FileMode.CreateNew,FileAccess.ReadWrite,FileShare.Read);\n   FileDiagnostic.At(FilePhase.JOURNAL_PIN);journalPin=Pin.Open(Path.Combine(root,"owner.private"),false,true);\n   FileDiagnostic.At(FilePhase.JOURNAL_ACL);Acl(journalPin.Path,false,true);\n   FileDiagnostic.At(FilePhase.JOURNAL_WRITE);Journal();\n   FileDiagnostic.At(FilePhase.NONE);')
    add('    Need(a!=UInt32.MaxValue&&(a&0x400)==0,Cause.FILES);',
        '    FileDiagnostic.Op(FileOperation.CHAIN_ATTRIBUTES);Need(a!=UInt32.MaxValue&&(a&0x400)==0,Cause.FILES);')
    add('   FileSystemSecurity ds=file?', '   FileDiagnostic.Op(FileOperation.ACL_READ);FileSystemSecurity ds=file?')
    add('   Need(file||ds.AreAccessRulesProtected,Cause.FILES);',
        '   FileDiagnostic.Op(FileOperation.ACL_PROTECTION);Need(file||ds.AreAccessRulesProtected,Cause.FILES);')
    add('   Need(owner==runner||owner=="S-1-5-18",Cause.FILES);',
        '   FileDiagnostic.Op(FileOperation.ACL_OWNER);Need(owner==runner||owner=="S-1-5-18",Cause.FILES);')
    add('    Need(a.AccessControlType==AccessControlType.Allow&&allowed.Contains(who)&&',
        '    FileDiagnostic.Op(FileOperation.ACL_RULE);Need(a.AccessControlType==AccessControlType.Allow&&allowed.Contains(who)&&')
    add('   Need(seen.SetEquals(allowed),Cause.FILES);',
        '   FileDiagnostic.Op(FileOperation.ACL_SET);Need(seen.SetEquals(allowed),Cause.FILES);')
    add('   Need(Missing(path),Cause.FILES);IntPtr sd=IntPtr.Zero;uint bytes;',
        '   FileDiagnostic.Op(FileOperation.DIRECTORY_ABSENCE);Need(Missing(path),Cause.FILES);IntPtr sd=IntPtr.Zero;uint bytes;')
    add('   Need(N.ConvertStringSecurityDescriptorToSecurityDescriptorW(Sddl(withTarget),1,out sd,out bytes),Cause.FILES);',
        '   FileDiagnostic.Op(FileOperation.DIRECTORY_SDDL);Need(N.ConvertStringSecurityDescriptorToSecurityDescriptorW(Sddl(withTarget),1,out sd,out bytes),Cause.FILES);')
    add('    Need(N.CreateDirectoryW(path,ref sa),Cause.FILES);acquired();',
        '    FileDiagnostic.Op(FileOperation.DIRECTORY_CREATE);Need(N.CreateDirectoryW(path,ref sa),Cause.FILES);acquired();')
    add('   Acl(path,withTarget,false);', '   FileDiagnostic.Op(FileOperation.DIRECTORY_ACL);Acl(path,withTarget,false);')
    add('    IntPtr h=N.CreateFileW(path,0x80000000|0x20000,writable?3u:1u,IntPtr.Zero,3,',
        '    FileDiagnostic.Op(FileOperation.OPEN_HANDLE);IntPtr h=N.CreateFileW(path,0x80000000|0x20000,writable?3u:1u,IntPtr.Zero,3,')
    add('    try{N.FileInfo i;Need(N.GetFileInformationByHandle(h,out i)',
        '    try{FileDiagnostic.Op(FileOperation.OPEN_INFO);N.FileInfo i;Need(N.GetFileInformationByHandle(h,out i)')
    add('   public void Same() {Need(h!=IntPtr.Zero,Cause.FILES);',
        '   public void Same() {FileDiagnostic.Op(FileOperation.SAME_HANDLE);Need(h!=IntPtr.Zero,Cause.FILES);')
    add('Need(N.GetFileInformationByHandle(h,out b)&&Equal(b)&&PathIdentitySame(),Cause.FILES);',
        'Need(FileDiagnostic.Result(N.GetFileInformationByHandle(h,out b)&&Equal(b)&&PathIdentitySame(),FileOperation.SAME_IDENTITY),Cause.FILES);')
    add('    Pin p=Open(Path,(Info.attrs&0x10)!=0,true);',
        '    FileDiagnostic.Op(FileOperation.PATH_REOPEN);Pin p=Open(Path,(Info.attrs&0x10)!=0,true);')
    add('    bool equal=Equal(p.Info);',
        '    FileDiagnostic.Op(FileOperation.PATH_IDENTITY_COMPARE);bool equal=Equal(p.Info);')
    add('    Same();N.FileInfo now;Need(N.GetFileInformationByHandle(h,out now)',
        '    Same();FileDiagnostic.Op(FileOperation.BYTES_SIZE);N.FileInfo now;Need(N.GetFileInformationByHandle(h,out now)')
    add('    using(SafeFileHandle safe=new SafeFileHandle(h,false))',
        '    FileDiagnostic.Op(FileOperation.BYTES_STREAM);using(SafeFileHandle safe=new SafeFileHandle(h,false))')
    add('     f.Position=0;int at=0;while(at<b.Length){int n=f.Read(b,at,b.Length-at);Need(n>0,Cause.FILES);at+=n;}\n     Need(f.ReadByte()==-1,Cause.FILES);',
        '     f.Position=0;int at=0;while(at<b.Length){int n=f.Read(b,at,b.Length-at);FileDiagnostic.Op(FileOperation.BYTES_PROGRESS);Need(n>0,Cause.FILES);at+=n;}\n     FileDiagnostic.Op(FileOperation.BYTES_END);Need(f.ReadByte()==-1,Cause.FILES);')
    add('    Same();N.FileInfo after;Need(N.GetFileInformationByHandle(h,out after)',
        '    Same();FileDiagnostic.Op(FileOperation.BYTES_POST);N.FileInfo after;Need(N.GetFileInformationByHandle(h,out after)')
    add('   Need(journalPin!=null,Cause.FILES);journalPin.Same();',
        '   FileDiagnostic.Op(FileOperation.JOURNAL_IDENTITY);Need(journalPin!=null,Cause.FILES);journalPin.Same();')
    add('   byte[] b=Encoding.UTF8.GetBytes("coh-owned-profile-private-v1',
        '   FileDiagnostic.Op(FileOperation.JOURNAL_SERIALIZE);byte[] b=Encoding.UTF8.GetBytes("coh-owned-profile-private-v1')
    add('   Need(b.Length<4096,Cause.FILES);journal.Position=0;journal.Write(b,0,b.Length);\n   journal.SetLength(b.Length);journal.Flush(true);Array.Clear(b,0,b.Length);journalPin.Same();',
        '   FileDiagnostic.Op(FileOperation.JOURNAL_BYTES);Need(b.Length<4096,Cause.FILES);\n   FileDiagnostic.Op(FileOperation.JOURNAL_WRITE);journal.Position=0;journal.Write(b,0,b.Length);\n   journal.SetLength(b.Length);journal.Flush(true);Array.Clear(b,0,b.Length);\n   FileDiagnostic.Op(FileOperation.JOURNAL_RECHECK);journalPin.Same();')
    return changes


def prepare(raw):
    if hashlib.sha256(raw).hexdigest() != BASE_SHA256:
        raise ValueError('BASE_SOURCE_REFUSED')
    source = raw.decode('utf-8')
    changes = replacements()
    for old, new in changes:
        if source.count(old) != 1:
            raise ValueError('DIAGNOSTIC_INSERTION_REFUSED')
        source = source.replace(old, new, 1)
    reverse = source
    for old, new in reversed(changes):
        if reverse.count(new) != 1:
            raise ValueError('DIAGNOSTIC_REVERSE_REFUSED')
        reverse = reverse.replace(new, old, 1)
    if reverse.encode('utf-8') != raw:
        raise ValueError('BASE_REVERSAL_REFUSED')
    return source.encode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    raw = Path(__file__).with_name('OwnedProfileProcess.cs').read_bytes()
    generated = prepare(raw)
    args.out_dir.mkdir(exist_ok=False)
    (args.out_dir/'OwnedProfileProcessFileDiagnostic.cs').write_bytes(generated)
    receipt = dict(schema='coh-wpp-file-diagnostic-preparation-v1', passed=True,
                   original_source_sha256=BASE_SHA256,
                   generated_source_sha256=hashlib.sha256(generated).hexdigest(),
                   generated_source_bytes=len(generated),
                   replacements=len(replacements()), exact_reverse_verified=True,
                   original_predicates_and_order_preserved=True,
                   compiler_or_helper_or_model_executed=False)
    (args.out_dir/'preparation.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, separators=(',', ':')))


if __name__ == '__main__':
    main()
