"""Recover the repository-pinned CryptoPP Adler dependency, with Git proofs."""
from pathlib import Path
import hashlib,json,zipfile

HERE=Path(__file__).resolve().parent
REVISION='b5242667a24e3db8e4600e77b2e502ef204e5280'
TREE='eed51ff8304991b27331b26a670885575ae90021'
MANIFEST='native-android/engine/body-catalog/qualification/schema-crc-20261019/cryptopp-adler-source.json'
ARCHIVE_SHA='7bb26369ae06a19836694df00dad2b4eb8e2f1046ddf3366747bdf6393b1cf15'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def git_object(kind,raw):return hashlib.sha1(kind.encode()+b' '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def prepare(root,work):
    root=Path(root).resolve();work=Path(work).resolve()
    manifest_path=root/MANIFEST;manifest_raw=manifest_path.read_bytes();m=json.loads(manifest_raw)
    if m['revision']!=REVISION or m['tree']!=TREE or len(m['files'])!=47:raise ValueError('CryptoPP revision/profile changed')
    dependency=root/m['repository_dependency']['path'];dependency_raw=dependency.read_bytes()
    if sha(dependency_raw)!=m['repository_dependency']['sha256'] or ('GIT_TAG '+REVISION) not in dependency_raw.decode():raise ValueError('Original CryptoPP dependency pin changed')
    archive=root/m['archive']['path'];packed=archive.read_bytes()
    if len(packed)!=m['archive']['bytes'] or sha(packed)!=ARCHIVE_SHA or sha(packed)!=m['archive']['sha256'] or git_object('blob',packed)!=m['archive']['git_blob_sha1']:raise ValueError('Pinned CryptoPP archive changed')
    expected={'source/'+name for name in m['files']}|{m['commit_proof']['path'],m['tree_proof']['path']}
    with zipfile.ZipFile(archive) as z:
        entries=z.infolist()
        if len(entries)!=49 or {i.filename for i in entries}!=expected or any(i.is_dir() or i.flag_bits&1 or i.file_size>524288 for i in entries) or sum(i.file_size for i in entries)>2097152:raise ValueError('CryptoPP archive extent/inventory')
        content={name:z.read(name) for name in expected}
    commit=content[m['commit_proof']['path']];tree=content[m['tree_proof']['path']]
    for key,raw in [('commit_proof',commit),('tree_proof',tree)]:
        if len(raw)!=m[key]['bytes'] or sha(raw)!=m[key]['sha256']:raise ValueError('CryptoPP proof changed')
    if git_object('commit',commit)!=REVISION or git_object('tree',tree)!=TREE or not commit.startswith(('tree '+TREE+'\n').encode()):raise ValueError('CryptoPP Git commit/tree proof refused')
    tree_entries={};at=0
    while at<len(tree):
        space=tree.index(b' ',at);mode=tree[at:space].decode('ascii');end=tree.index(b'\0',space);name=tree[space+1:end].decode('utf-8');at=end+21
        if at>len(tree) or name in tree_entries:raise ValueError('Invalid CryptoPP root tree')
        tree_entries[name]=(mode,tree[end+1:at].hex())
    for name,meta in m['files'].items():
        if '/' in name or '\\' in name or name in ('.','..'):raise ValueError('CryptoPP source path refused')
        raw=content['source/'+name]
        if len(raw)!=meta['bytes'] or sha(raw)!=meta['sha256'] or git_object('blob',raw)!=meta['git_blob_sha1'] or tree_entries.get(name)!=("100644",meta['git_blob_sha1']):raise ValueError('CryptoPP source/Git membership refused: '+name)
    destination=work/'cryptopp';destination.mkdir(parents=True,exist_ok=False)
    snapshots={}
    for name,meta in m['files'].items():
        path=destination/name;path.write_bytes(content['source/'+name]);snapshots[str(path)]=meta['sha256']
    text=content['source/integer.cpp'].decode().replace('\r\n','\n')
    start=text.index('template <> CRYPTOPP_DLL\nstd::string IntToString<word64>');at=text.index('{',start)+1;depth=1
    while depth:
        if at>=len(text):raise ValueError('Original CryptoPP auxiliary leaf incomplete')
        depth+=(text[at]=='{')-(text[at]=='}');at+=1
    leaf=text[start:at]+'\n'
    if len(leaf.encode())!=m['unchanged_auxiliary_leaf']['bytes_lf'] or sha(leaf.encode())!=m['unchanged_auxiliary_leaf']['sha256_lf']:raise ValueError('Original CryptoPP auxiliary leaf changed')
    extra=work/'cryptopp-int-to-string.cpp';extra.write_text('#include "misc.h"\nNAMESPACE_BEGIN(CryptoPP)\n'+leaf+'NAMESPACE_END\n');snapshots[str(extra)]=sha(extra.read_bytes())
    proof={'schema':'coh-pinned-cryptopp-adler-dependency-v1','revision':REVISION,'tree':TREE,'Git_commit_tree_and_selected_blob_membership_verified':True,'repository_dependency':m['repository_dependency'],'manifest_path':MANIFEST,'manifest_sha256':sha(manifest_raw),'archive':m['archive'],'source_files':m['files'],'source_files_count':47,'source_bytes':sum(f['bytes'] for f in m['files'].values()),'build_sources':m['build_sources'],'unchanged_auxiliary_leaf':m['unchanged_auxiliary_leaf'],'generated_auxiliary_source_sha256':sha(extra.read_bytes()),'compile_flags':['-std=c++11','-DCRYPTOPP_DISABLE_ASM','-ffunction-sections','-fdata-sections'],'link_flags':['-Wl,--gc-sections'],'scope':m['profile'],'original_backend_not_alternate_Adler':True,'system_cpp_runtime_allocator_or_platform_closure':False}
    (work/'cryptopp-provenance.json').write_text(json.dumps(proof,indent=2)+'\n')
    if manifest_path.read_bytes()!=manifest_raw or archive.read_bytes()!=packed or dependency.read_bytes()!=dependency_raw:raise ValueError('CryptoPP input changed during recovery')
    return {'proof':proof,'include_dir':str(destination),'source_paths':[str(destination/name) for name in m['build_sources']]+[str(extra)],'snapshot_sha256':snapshots,'repository_input_paths':[str(manifest_path),str(archive),str(dependency),str(Path(__file__).resolve())]}

def verify(dependency):
    if any(sha(Path(path).read_bytes())!=digest for path,digest in dependency['snapshot_sha256'].items()):raise ValueError('CryptoPP source changed during qualification')
