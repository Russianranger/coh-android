#!/usr/bin/env python3
"""Check offline dependency ownership, JNI and exact packaged asset identities."""
import argparse,hashlib,json,re,subprocess,tempfile
from pathlib import Path

FORBIDDEN=tuple('native-android/engine/'+x+'/' for x in
                ('network','auth','dbclient','login','mapclient','live','local','session','replication'))+('native-android/combined-client/',)
def admitted_path(path):
    normalized=str(path).replace('\\','/')
    if any('/'+p in '/'+normalized for p in FORBIDDEN):raise ValueError('Protected primary dependency: '+normalized)

def source_closure(root,config):
    include_dirs=[root/x for x in config.get('include_dirs',[]) if '{' not in x]
    pending=[];seen=set();unresolved=set()
    for key in ('sources','include_dirs','java_sources'):
        for entry in config.get(key,[]):
            admitted_path(entry)
            if key=='sources' and '{' not in entry:pending.append(root/entry)
    while pending:
        path=pending.pop().resolve();admitted_path(path)
        if path in seen:continue
        seen.add(path)
        if not path.is_file():raise ValueError('Missing local source: '+str(path))
        raw=path.read_text()
        for delim,name in re.findall(r'^\s*#\s*include\s*(["<])([^">]+)[">]',raw,re.M):
            admitted_path(name)
            choices=([path.parent/name] if delim=='"' else [])+[d/name for d in include_dirs]
            found=next((p for p in choices if p.is_file()),None)
            if found is not None:pending.append(found)
            elif delim=='"':unresolved.add(name)
    return {'local_inputs_checked':len(seen),'unresolved_quoted_external_or_generated_includes':sorted(unresolved),
            'scope':'Literal local include closure; compiler-recorded closure is checked separately when a build receipt is supplied.'}

def negative_controls():
    tested=[]
    for path in FORBIDDEN:
        try:admitted_path(path+'forbidden.c')
        except ValueError:tested.append(path)
        else:raise AssertionError('Protected path admitted')
    with tempfile.TemporaryDirectory(prefix='coh-offline-boundary-') as tmp:
        root=Path(tmp);p=root/'native-android/support-client/src';p.mkdir(parents=True)
        (p/'test.c').write_text('#include "adapter.h"\n')
        (p/'adapter.h').write_text('#include "../../engine/live/forbidden.h"\n')
        forbidden=root/'native-android/engine/live/forbidden.h';forbidden.parent.mkdir(parents=True);forbidden.write_text('/* deliberately forbidden */')
        try:source_closure(root,{'sources':['native-android/support-client/src/test.c'],'include_dirs':[]})
        except ValueError:tested.append('transitive local protected header')
        else:raise AssertionError('Transitive protected dependency admitted')
    return tested

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,default=Path('.'));p.add_argument('--assets',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline',default='origin/native-android');p.add_argument('--build-receipt',type=Path)
    a=p.parse_args();root=a.source_root.resolve();client=root/'native-android/support-client';assets=a.assets or client/'assets'
    manifest=json.loads((assets/'support-asset-manifest.json').read_text())
    assert manifest['accepted_apk_sha256']=='75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639'
    for name,pin in manifest['assets'].items():
        path=Path(name);assert not path.is_absolute() and '..' not in path.parts
        raw=(assets/name).read_bytes();assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],name
    java=(client/'java/org/coh/sessionclient/MainActivity.java').read_text();audio=(client/'src/support_audio.c').read_text()
    java_names=re.findall(r'readAsset\("([^\"]+)"\)',java);audio_names=re.findall(r'asset_open\(s,"([^\"]+)"',audio)
    for name in java_names+audio_names:assert (assets/name).is_file(),name
    config=json.loads((client/'build-sources.json').read_text());closure=source_closure(root,config)
    compiled_count=0
    if a.build_receipt:
        receipt=json.loads(a.build_receipt.read_text())
        for artifact in receipt['artifacts']:
            for item in artifact['native']['compiled_inputs']:admitted_path(item['file']);compiled_count+=1
    assert 'org.coh.nativesupport' in (client/'AndroidManifest.xml').read_text()
    assert 'native boolean destroy' in (client/'java/org/coh/sessionclient/SessionNative.java').read_text()
    assert 'JNIEXPORT jboolean JNICALL Java_org_coh_sessionclient_SessionNative_destroy' in (client/'src/offline_scene.c').read_text()
    protected=['native-android/session-client','native-android/walk','native-android/locomotion','native-android/character','native-android/engine/coh_contracts.h','native-android/engine/ui/coh_ui.c','native-android/engine/ui/coh_ui.h',*FORBIDDEN]
    changed=subprocess.check_output(['git','diff','--name-only',a.baseline,'--',*protected],cwd=root,text=True).splitlines();assert not changed,changed
    tests=negative_controls()
    result={'schema':2,'passed':True,'asset_identities':len(manifest['assets']),'java_asset_paths':java_names,'audio_asset_paths':audio_names,
        'forbidden_dependency_negative_cases':tests,'closure':closure,'compiler_inputs_checked':compiled_count,'protected_source_changes':changed,
        'network_protocol_linked':False,'native_source_count':len(config['sources']),'android_execution':False,'physical_acceptance':False}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
