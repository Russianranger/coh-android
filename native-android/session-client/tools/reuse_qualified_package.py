#!/usr/bin/env python3
"""Reuse exact packaged bytes only when all intervening changes are non-runtime.

The pinned original run passed packaging/source proofs but stopped at an
accessibility selector. Reuse does not qualify that failed emulator run: the
workflow executes the current driver against the exact installed APK again.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile

SOURCE_COMMIT='e88a02b284de16ed6f7caf1e6b689f2e85d0b6e8'
WORKFLOW_RUN=38631384218
ARTIFACT_ID=11926935368
ARCHIVE_SHA256='f38d8de127b50e249bf3a5b0d9273b5190ada9ee42848890a86886d23ca255b4'
REPOSITORY='Russianranger/coh-android'
MAX_ARCHIVE=256<<20
ALLOWED_FILES=frozenset({
    'native-android/session-client/tools/emulator_check.py',
    'native-android/session-client/tools/tap_host_check.py',
    'native-android/session-client/tools/reuse_qualified_package.py',
    'native-android/session-client/tools/reuse_host_check.py',
    '.github/workflows/native-session-client.yml',
    'README.md','native-android/README.md','native-android/PHASES16-18.md',
    'native-android/session-client/THOR-TEST.md',
})
EVIDENCE_PREFIX='native-android/evidence/phases16-18/'


def git(root,*arguments):
    return subprocess.run(['git',*arguments],cwd=root,capture_output=True,check=True,timeout=30).stdout


def allowed_path(name):
    return (name in ALLOWED_FILES or (name.startswith(EVIDENCE_PREFIX)
            and '..' not in PurePosixPath(name).parts and '\\' not in name))


def guard(root,base,head):
    try:
        if git(root,'rev-parse',head).decode().strip()!=head:
            return {'eligible':False,'reason':'Validation head must be an exact commit SHA','changes':[]}
        git(root,'merge-base','--is-ancestor',base,head)
        raw=git(root,'diff','--raw','-z','--no-renames',base,head).split(b'\0')
        if raw[-1]!=b'' or (len(raw)-1)%2:
            raise ValueError('Malformed NUL-delimited Git raw diff')
        changes=[]
        for i in range(0,len(raw)-1,2):
            fields=raw[i].decode('ascii').split();name=raw[i+1].decode('utf8')
            if len(fields)!=5 or not fields[0].startswith(':'):
                raise ValueError('Unexpected Git raw diff record')
            before,after=fields[0][1:],fields[1]
            change={'path':name,'old_mode':before,'new_mode':after,'status':fields[4]}
            changes.append(change)
            if before not in {'000000','100644','100755'} or after not in {'000000','100644','100755'}:
                return {'eligible':False,'reason':'Gitlink, symlink or non-regular mode changed','changes':changes}
            if fields[4] not in {'A','M','D'} or not allowed_path(name):
                return {'eligible':False,'reason':'A runtime, build, asset, oracle or unapproved path changed','changes':changes}
        return {'eligible':True,'reason':'Every committed change is in the explicit non-runtime allowlist','changes':changes}
    except (subprocess.CalledProcessError,UnicodeDecodeError,ValueError) as error:
        return {'eligible':False,'reason':'Git ancestry/diff inspection failed closed','error_type':type(error).__name__,'changes':[]}


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,message,headers,newurl):
        redirected=super().redirect_request(request,fp,code,message,headers,newurl)
        if redirected is not None and urllib.parse.urlsplit(request.full_url).hostname!=urllib.parse.urlsplit(newurl).hostname:
            redirected.remove_header('Authorization')
        return redirected


def request(url,token):
    return urllib.request.build_opener(SafeRedirect()).open(urllib.request.Request(url,headers={
        'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
        'X-GitHub-Api-Version':'2022-11-28','User-Agent':'coh-native-package-requalification'}),timeout=60)


def extract(archive,output):
    with zipfile.ZipFile(archive) as bundle:
        if bundle.testzip() is not None:
            raise ValueError('Pinned artifact ZIP integrity differs')
        entries=bundle.infolist()
        if len(entries)>20000 or sum(item.file_size for item in entries)>MAX_ARCHIVE:
            raise ValueError('Artifact extraction exceeds bounds')
        names=set()
        for item in entries:
            path=PurePosixPath(item.filename);kind=stat.S_IFMT(item.external_attr>>16)
            if (path.is_absolute() or '..' in path.parts or '\\' in item.filename
                    or kind not in {0,stat.S_IFREG,stat.S_IFDIR} or item.filename in names):
                raise ValueError('Unsafe artifact ZIP entry')
            names.add(item.filename)
        for item in entries:
            path=output.joinpath(*PurePosixPath(item.filename).parts)
            if item.is_dir():
                path.mkdir(parents=True,exist_ok=True);continue
            path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():
                raise ValueError('Pinned extraction would overwrite current evidence')
            with bundle.open(item) as source,path.open('wb') as target:
                shutil.copyfileobj(source,target,1<<20)


def github_output(value):
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as output:
            output.write('reused='+('true' if value else 'false')+'\n')


def unavailable(output,decision,reason):
    decision.update(reuse_selected=False,fallback_reason=reason)
    (output/'reuse-guard.json').write_text(json.dumps(decision,indent=2)+'\n')
    print(json.dumps({'reused':False,'reason':reason,'fallback':'complete source build'}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root',type=Path,default=Path('.'))
    parser.add_argument('--output',type=Path,default=Path('native-android/results/session-client'))
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True);github_output(False)
    head=git(args.repo_root,'rev-parse','HEAD').decode().strip()
    decision=guard(args.repo_root,SOURCE_COMMIT,head)
    decision.update(schema=1,pinned_runtime_source_commit=SOURCE_COMMIT,validation_head=head)
    (args.output/'reuse-guard.json').write_text(json.dumps(decision,indent=2)+'\n')
    if not decision['eligible']:
        print(json.dumps({'reused':False,'reason':decision['reason']}));return
    if os.environ.get('GITHUB_REPOSITORY')!=REPOSITORY:
        raise ValueError('Pinned reuse belongs to a different repository')
    token=os.environ.get('GH_TOKEN')
    if not token:
        raise ValueError('Artifact read token missing')
    api='https://api.github.com/repos/'+REPOSITORY+'/actions/artifacts/'+str(ARTIFACT_ID)
    try:
        with request(api,token) as response:
            raw=response.read((1<<20)+1)
    except urllib.error.HTTPError as error:
        if error.code in (404,410):
            unavailable(args.output,decision,'Pinned original artifact is unavailable (HTTP '+str(error.code)+')');return
        raise
    if len(raw)>1<<20:
        raise ValueError('Artifact metadata exceeds bound')
    metadata=json.loads(raw)
    if (metadata['id']!=ARTIFACT_ID
            or metadata['workflow_run']['id']!=WORKFLOW_RUN
            or metadata['workflow_run']['head_sha']!=SOURCE_COMMIT
            or metadata['workflow_run']['head_branch']!='native-android'):
        raise ValueError('Original artifact identity differs')
    if metadata['expired'] is True:
        unavailable(args.output,decision,'Pinned original artifact expired; source rebuild required');return
    if metadata['expired'] is not False:
        raise ValueError('Original artifact expiry metadata is invalid')
    with tempfile.TemporaryDirectory(prefix='coh-pinned-package-') as temp:
        archive=Path(temp)/'artifact.zip';digest=hashlib.sha256();size=0
        try:
            with request(api+'/zip',token) as source,archive.open('wb') as target:
                while True:
                    chunk=source.read(1<<20)
                    if not chunk:break
                    size+=len(chunk)
                    if size>MAX_ARCHIVE:raise ValueError('Artifact download exceeds bound')
                    digest.update(chunk);target.write(chunk)
        except urllib.error.HTTPError as error:
            if error.code in (404,410):
                unavailable(args.output,decision,'Pinned archive became unavailable (HTTP '+str(error.code)+')');return
            raise
        if digest.hexdigest()!=ARCHIVE_SHA256:
            raise ValueError('Pinned original artifact archive SHA256 differs')
        extract(archive,args.output)
    receipt_bytes=(args.output/'build-receipt.json').read_bytes();original=json.loads(receipt_bytes)
    if original['source_commit']!=SOURCE_COMMIT or str(original['workflow_run_id'])!=str(WORKFLOW_RUN):
        raise ValueError('Original package receipt source/run differs')
    artifacts=[]
    for item in original['artifacts']:
        path=args.output/item['file'];payload=path.read_bytes()
        if len(payload)!=item['bytes'] or hashlib.sha256(payload).hexdigest()!=item['sha256']:
            raise ValueError('Original APK bytes differ from retained receipt')
        artifacts.append({'file':item['file'],'bytes':item['bytes'],'sha256':item['sha256'],'abi':item['abi']})
    if {item['abi'] for item in artifacts}!={'arm64-v8a','x86_64'}:
        raise ValueError('Original package ABI set differs')
    # Keep the unsuccessful original driver outputs intact and distinguish them
    # from the fresh Android run that follows this step.
    previous=args.output/'reuse-original-emulator';previous.mkdir()
    for path in args.output.glob('emulator-*'):
        shutil.move(str(path),previous/path.name)
    driver=args.repo_root/'native-android/session-client/tools/emulator_check.py'
    reuse={'schema':1,'package_bytes_reused':True,'original_runtime_source_commit':SOURCE_COMMIT,
           'validation_head':head,'validation_workflow_run_id':os.environ.get('GITHUB_RUN_ID'),
           'validation_driver_sha256':hashlib.sha256(driver.read_bytes()).hexdigest(),
           'original_artifact_id':ARTIFACT_ID,'original_workflow_run_id':WORKFLOW_RUN,
           'original_archive_bytes':size,'original_archive_sha256':ARCHIVE_SHA256,
           'original_build_receipt_sha256':hashlib.sha256(receipt_bytes).hexdigest(),'artifacts':artifacts,
           'original_source_host_proofs_retained_unchanged':True,'source_host_tests_rerun':False,
           'new_emulator_acceptance':False,'thor_device_execution_verified':False,
           'scope':'Exact previously packaged APKs; fresh driver/lifecycle/selector qualification follows separately'}
    (args.output/'package-reuse-receipt.json').write_text(json.dumps(reuse,indent=2)+'\n')
    github_output(True);print(json.dumps({'reused':True,'runtime_source_commit':SOURCE_COMMIT,'artifacts':artifacts}))


if __name__=='__main__':
    main()
