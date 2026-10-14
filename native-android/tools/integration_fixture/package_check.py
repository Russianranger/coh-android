"""Bind both isolated APKs to their source, assets, ELF and signing receipts."""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import zipfile

root=Path('native-android/results/integration-probe')
assets=Path('native-android/integration-probe/app/src/main/assets')
expected={'world.bin','world-reference.bin','material-reference.bin','world-fixture.json','audio.bin','audio-fixture.json','headset.ogg','codec-licenses.txt'}
assert {p.name for p in assets.iterdir() if p.is_file()}==expected
audio=json.loads((assets/'audio-fixture.json').read_text())
world=json.loads((assets/'world-fixture.json').read_text())
assert hashlib.sha256((assets/'headset.ogg').read_bytes()).hexdigest()=='82bec697f9e824d192cac90f32a01421e4a3875aada64fc709862bc4d3ae9198'
assert (assets/'headset.ogg').stat().st_size==12930
for name,pin in dict(world['assets'],**{'audio.bin':audio['audio']}).items():
    raw=(assets/name).read_bytes()
    assert len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
signer=Path(os.environ['ANDROID_HOME'])/'build-tools/35.0.0/apksigner'
artifacts=[]
for label,abi,machine in [('arm64','arm64-v8a',183),('emulator-x86_64','x86_64',62)]:
    apk=root/('CoH-Native-Integration-Probe-0.1.0-'+label+'.apk')
    with zipfile.ZipFile(apk) as z:
        native=[n for n in z.namelist() if n.startswith('lib/') and n.endswith('.so')]
        assert native==['lib/'+abi+'/libcoh_integration_probe.so']
        elf=z.read(native[0])
        assert elf[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',elf,18)[0]==machine
        assert {n.removeprefix('assets/') for n in z.namelist() if n.startswith('assets/') and not n.endswith('/')}==expected
        for name in expected:assert z.read('assets/'+name)==(assets/name).read_bytes(),name
    signature=subprocess.check_output([str(signer),'verify','--verbose','--print-certs',str(apk)],text=True)
    badging=subprocess.check_output([str(signer.with_name('aapt')),'dump','badging',str(apk)],text=True)
    package=re.search(r"^package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'",badging,re.M)
    assert package and package.groups()==('org.coh.integrationprobe','1','0.1.0-phases13-15')
    assert "sdkVersion:'26'" in badging and "targetSdkVersion:'35'" in badging
    permissions=re.findall(r"^uses-permission: name='([^']+)'",badging,re.M)
    assert permissions==['android.permission.INTERNET'],permissions
    assert "native-code: '"+abi+"'" in badging
    cert=re.search(r'^Signer #1 certificate SHA-256 digest: ([0-9a-f]+)$',signature,re.M)
    assert cert
    (root/('apk-signature-'+label+'.txt')).write_text(signature)
    (root/('apk-badging-'+label+'.txt')).write_text(badging)
    artifacts.append({'file':apk.name,'bytes':apk.stat().st_size,'sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),
        'abi':abi,'elf_machine':machine,'native_library':{'file':native[0],'bytes':len(elf),'sha256':hashlib.sha256(elf).hexdigest()},
        'signature_verified':True,'manifest_verified':True,'packaged_fixtures_verified':True,'signer_certificate_sha256':cert.group(1)})
assert len({a['signer_certificate_sha256'] for a in artifacts})==1
receipt={'schema':1,'phases':[13,14,15],'source_commit':os.environ['GITHUB_SHA'],'workflow_run_id':os.environ['GITHUB_RUN_ID'],
    'application_id':'org.coh.integrationprobe','probe_version':'0.1.0-phases13-15','version_code':1,'min_sdk':26,'target_sdk':35,
    'gradle':'8.9','android_gradle_plugin':'8.7.3','ndk':'28.2.13676358','cmake':'3.22.1',
    'signing':'Isolated CI debug key; separate from production launcher',
    'artifacts':artifacts,'assets':[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(assets.iterdir()) if p.is_file()],
    'accepted_input_adapter_sha256':hashlib.sha256(Path('native-android/systems-probe/app/src/main/java/org/coh/systemsprobe/InputAdapter.java').read_bytes()).hexdigest(),
    'original_game_execution':False,'full_atlas_loaded':False,'character_movement_or_collision':False,'server_interoperability_verified':False,
    'network_scope':'IPv4 UDP to127.0.0.1 only; ephemeral ports; worker-owned descriptors',
    'thor_device_execution_verified':False,'physical_controller_verified':False,'physical_audibility_verified':False}
(root/'build-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(root/'SHA256SUMS').write_text(''.join(a['sha256']+'  '+a['file']+'\n' for a in artifacts))
print(json.dumps({'passed':True,'artifacts':artifacts}))
