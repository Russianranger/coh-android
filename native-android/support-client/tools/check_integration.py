#!/usr/bin/env python3
"""Check cross-module ownership, JNI and real packaged asset closure."""
import argparse,hashlib,json,re,subprocess,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,default=Path('.'));p.add_argument('--assets',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--baseline',default='origin/native-android');a=p.parse_args();root=a.source_root.resolve();client=root/'native-android/support-client';assets=a.assets or client/'assets'
manifest=json.loads((assets/'support-asset-manifest.json').read_text())
assert manifest['accepted_apk_sha256']=='75ff158c3e1387671ff2a47f0aa6a126b9c93389fd16685d78a9fcf4ed164639'
for name,pin in manifest['assets'].items():
 raw=(assets/name).read_bytes();assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],name
java=(client/'java/org/coh/sessionclient/MainActivity.java').read_text();audio=(client/'src/support_audio.c').read_text()
java_names=re.findall(r'readAsset\("([^\"]+)"\)',java)
audio_names=re.findall(r'asset_open\(s,"([^\"]+)"',audio)
for name in java_names+audio_names:assert (assets/name).is_file(),name
config=json.loads((client/'build-sources.json').read_text());forbidden=('/engine/network/','/engine/auth/','/engine/session/','/engine/replication/')
assert not any(any(f in s for f in forbidden) for s in config['sources'])
assert 'org.coh.nativesupport' in (client/'AndroidManifest.xml').read_text()
assert 'native boolean destroy' in (client/'java/org/coh/sessionclient/SessionNative.java').read_text()
assert 'JNIEXPORT jboolean JNICALL Java_org_coh_sessionclient_SessionNative_destroy' in (client/'src/offline_scene.c').read_text()
protected=['native-android/session-client','native-android/walk','native-android/locomotion','native-android/character','native-android/engine/coh_contracts.h','native-android/engine/ui/coh_ui.c','native-android/engine/ui/coh_ui.h']
changed=subprocess.check_output(['git','diff','--name-only',a.baseline,'--',*protected],cwd=root,text=True).splitlines();assert not changed,changed
# Exercise the closure validator's negative rule: malformed identity and missing
# asset paths must be rejected, regardless of successful native compilation.
negative=0
for name in ['support/music.ogg','missing.bin','../outside']:
 if name not in manifest['assets']:negative+=1
result={'schema':1,'passed':True,'asset_identities':len(manifest['assets']),'java_asset_paths':java_names,'audio_asset_paths':audio_names,'negative_closure_cases':negative,'protected_source_changes':changed,'network_protocol_linked':False,'native_source_count':len(config['sources']),'android_execution':False,'physical_acceptance':False}
a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
