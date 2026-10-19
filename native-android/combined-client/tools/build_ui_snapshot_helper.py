#!/usr/bin/env python3
"""Build a separate disposable test helper; never rebuild the candidate APK."""
import argparse,hashlib,json,os,pathlib,shutil,subprocess,zipfile

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PACKAGE='org.coh.qualification.capture'
MANIFEST='''<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="org.coh.qualification.capture"><uses-sdk android:minSdkVersion="26" android:targetSdkVersion="35"/><application android:debuggable="true" android:label="Qualification UI snapshot"/><instrumentation android:name="org.coh.qualification.capture.UiSnapshotInstrumentation" android:targetPackage="org.coh.qualification.capture" android:functionalTest="true"/></manifest>'''
def pin(path):
 raw=path.read_bytes();return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
def run(command):
 p=subprocess.run(list(map(str,command)),capture_output=True,text=True,timeout=90)
 if p.returncode:raise RuntimeError('Helper build failed: '+repr(command)+'\n'+p.stdout[-2000:]+p.stderr[-4000:])
 return p.stdout
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
 sdk=pathlib.Path(os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT') or '/missing-android-sdk')
 tools=sdk/'build-tools/35.0.0';android=sdk/'platforms/android-35/android.jar'
 tool_inputs=[tools/'aapt2',tools/'d8',tools/'apksigner',tools/'lib/d8.jar',tools/'lib/apksigner.jar']
 for f in [android,*tool_inputs]:
  if not f.is_file():raise RuntimeError('Pinned test-helper build input missing: '+str(f))
 source=HERE/'UiSnapshotInstrumentation.java';key=ROOT/'native-android/session-client/app/test-signing/session-test.p12'
 a.output.mkdir(parents=True,exist_ok=False);classes=a.output/'classes';dex=a.output/'dex';classes.mkdir();dex.mkdir()
 manifest=a.output/'AndroidManifest.xml';manifest.write_text(MANIFEST)
 java=pathlib.Path(os.environ['JAVA_HOME'])/'bin/java' if os.environ.get('JAVA_HOME') else pathlib.Path(shutil.which('java') or '/missing-java')
 run([java,'com.sun.tools.javac.Main','-source','8','-target','8','-classpath',android,'-d',classes,source])
 jar=a.output/'snapshot-classes.jar'
 with zipfile.ZipFile(jar,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for f in sorted(classes.rglob('*.class')):z.write(f,f.relative_to(classes).as_posix())
 run([tools/'d8','--min-api','26','--lib',android,'--output',dex,jar])
 unsigned=a.output/'unsigned.apk';apk=a.output/'ui-snapshot-helper.apk'
 run([tools/'aapt2','link','-I',android,'--manifest',manifest,'--min-sdk-version','26','--target-sdk-version','35','--version-code','1','--version-name','1.0','-o',unsigned])
 with zipfile.ZipFile(unsigned,'a',compression=zipfile.ZIP_DEFLATED) as z:z.write(dex/'classes.dex','classes.dex')
 run([tools/'apksigner','sign','--ks',key,'--ks-type','PKCS12','--ks-pass','pass:coh-native-public-test','--ks-key-alias','coh-native-test','--key-pass','pass:coh-native-public-test','--out',apk,unsigned])
 signer=run([tools/'apksigner','verify','--print-certs',apk]);(a.output/'signer.txt').write_text(signer)
 expected='9aec9a8635d33dabd676748c3287e035e00d676546b4da18469dd48eecf5c522'
 if 'Signer #1 certificate SHA-256 digest: '+expected not in signer:raise RuntimeError('Unexpected separate helper signer')
 java_version=subprocess.check_output([str(java),'-version'],stderr=subprocess.STDOUT,text=True,timeout=30)
 receipt={'schema':'coh-test-only-ui-snapshot-helper-v1','passed':True,'package':PACKAGE,'target_package':PACKAGE,'source':pin(source),'builder':pin(pathlib.Path(__file__)),'manifest':pin(manifest),'public_test_key':pin(key),'apk':pin(apk),'java_version':java_version,'android_jar':pin(android),'build_tools':{str(f.relative_to(tools)):pin(f) for f in tool_inputs},'complete_tool_dependency_closure_claimed':False,'signer_certificate_sha256':expected,'limits':{'nodes':8192,'depth':64,'bytes':8*1024*1024,'root_acquisition_attempts':32,'root_acquisition_ms':3000,'host_instrumentation_timeout_seconds':45},'candidate_APK_rebuilt_or_modified':False,'app_state_changed':False,'global_idle_required':False}
 (a.output/'build.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':True,'apk':str(apk),'receipt':str(a.output/'build.json')}))
if __name__=='__main__':main()
