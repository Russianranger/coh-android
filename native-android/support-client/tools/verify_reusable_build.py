#!/usr/bin/env python3
"""Admit an exact prior APK for new driver-only qualification, without rebuilding.

This does not convert a failed scenario into a pass. Runtime inputs must match
the original source commit, current HEAD and current working tree byte for byte.
"""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,re,subprocess,zipfile

def require(ok,message):
 if not ok:raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def git(root,*args,check=True):return subprocess.run(['git',*args],cwd=root,capture_output=True,check=check).stdout
def tracked(root,commit,name):
 return subprocess.run(['git','cat-file','-e',commit+':'+name],cwd=root,capture_output=True).returncode==0
def safe_relative(name):
 p=PurePosixPath(name);require(not p.is_absolute() and '..' not in p.parts and '\\' not in name,'Unsafe receipt path');return name
def verify(root,directory,archive,archive_sha,source):
 root=root.resolve();require(re.fullmatch('[0-9a-f]{40}',source) and re.fullmatch('[0-9a-f]{64}',archive_sha),'Missing exact source/archive identity')
 require(digest(archive.read_bytes())==archive_sha,'Artifact ZIP SHA256 differs')
 build=json.loads((directory/'build-receipt.json').read_text());head=git(root,'rev-parse','HEAD').decode().strip()
 require(build['passed'] and build['source_tree_clean'] and build['source_commit']==source,'Original build source receipt differs')
 require(build['package']=='org.coh.nativesupport' and build['version_code']==201 and build['version_name']=='0.2.0-gameplay','Original package identity differs')
 with zipfile.ZipFile(archive) as bundle:
  require(bundle.testzip() is None and len(bundle.namelist())==len(set(bundle.namelist())),'Artifact ZIP integrity differs')
  require(bundle.read('build-receipt.json')==(directory/'build-receipt.json').read_bytes(),'Extracted receipt differs from pinned ZIP')
  for artifact in build['artifacts']:
   name=safe_relative(artifact['file']);raw=(directory/name).read_bytes()
   require(raw==bundle.read(name) and len(raw)==artifact['bytes'] and digest(raw)==artifact['sha256'],'Exact APK identity differs: '+name)
   require(artifact['signature_verified'] and artifact['manifest_verified'] and artifact['packaged_assets_verified'],'Original build verification incomplete')
   with zipfile.ZipFile(directory/name) as apk:
    require(apk.testzip() is None and len(apk.namelist())==len(set(apk.namelist())),'APK ZIP integrity differs')
    native=artifact['native'];libraries=[n for n in apk.namelist() if n.startswith('lib/') and n.endswith('.so')]
    require(len(libraries)==1 and libraries[0].startswith('lib/'+native['abi']+'/'),'APK ABI closure differs')
    require(digest(apk.read(libraries[0]))==native['sha256'],'Packaged native library differs')
    actual={n[7:] for n in apk.namelist() if n.startswith('assets/') and not n.endswith('/')}
    require(actual=={x['file'] for x in build['assets']},'APK asset set differs')
    for item in build['assets']:
     data=apk.read('assets/'+safe_relative(item['file']));require(len(data)==item['bytes'] and digest(data)==item['sha256'],'Packaged asset differs: '+item['file'])
 inputs=[build['source_manifest'],*build['sources'],*build['java_sources']]
 for artifact in build['artifacts']:inputs+=artifact['native']['compiled_inputs']
 checked={};external={}
 for item in inputs:
  name=item['file']
  if Path(name).is_absolute():external[name]=item['sha256'];continue
  safe_relative(name)
  if not tracked(root,source,name):external[name]=item['sha256'];continue
  expected=item['sha256'];require(digest(git(root,'show',source+':'+name))==expected,'Receipt is not bound to original Git input: '+name)
  require(digest(git(root,'show',head+':'+name))==expected and (root/name).is_file() and digest((root/name).read_bytes())==expected,'Current runtime/header/Java input differs: '+name)
  checked[name]=expected
 app='native-android/support-client/'
 def build_input(name):
  suffix=name[len(app):];return suffix.startswith(('src/','java/','res/')) or suffix in ('AndroidManifest.xml','build-sources.json','tools/build_apk.py','tools/prepare_assets.py')
 names=set(git(root,'ls-tree','-r','--name-only',source,'--',app).decode().splitlines()+git(root,'ls-tree','-r','--name-only',head,'--',app).decode().splitlines())
 for name in sorted(filter(build_input,names)):
  require(tracked(root,source,name) and tracked(root,head,name),'Runtime build input added or removed: '+name)
  expected=digest(git(root,'show',source+':'+name));require(digest(git(root,'show',head+':'+name))==expected and digest((root/name).read_bytes())==expected,'Android packaging/runtime input differs: '+name);checked[name]=expected
 # Generated headers are external in -MMD, so also bind their tracked shader,
 # tray/font, codec and canonical-asset preparation inputs explicitly.
 def generation_input(name):
  if name.startswith(('native-android/world-probe/shaders/','native-android/engine/ui/gameplay/tray/')):return True
  if name in ('native-android/engine/ui/gameplay/make_atlas.py','native-android/engine/ui/gameplay/docs/font-provenance.json','native-android/engine/sequencer/showcase/base-pins.json','native-android/engine/sequencer/continuation/extra-asset-pins.json','native-android/engine/audio/android-integration/acquire.py'):return True
  if name.startswith(tuple('native-android/tools/'+x+'/' for x in ('animation_fixture','material_fixture','decode_fixture','audio_fixture'))):return Path(name).suffix in ('.py','.json','.c','.h')
  if name.startswith('native-android/engine/appearance/') and '/qualification/' not in name:return Path(name).suffix in ('.py','.json')
  return name.startswith(tuple('native-android/engine/'+x+'/' for x in ('assets','renderer','bridge'))) and Path(name).suffix=='.py'
 native_names=set(git(root,'ls-tree','-r','--name-only',source,'--','native-android').decode().splitlines()+git(root,'ls-tree','-r','--name-only',head,'--','native-android').decode().splitlines())
 generator_count=0
 for name in sorted(filter(generation_input,native_names)):
  require(tracked(root,source,name) and tracked(root,head,name),'Tracked generator input added or removed: '+name)
  expected=digest(git(root,'show',source+':'+name));require(digest(git(root,'show',head+':'+name))==expected and digest((root/name).read_bytes())==expected,'Tracked generator input differs: '+name);checked[name]=expected;generator_count+=1
 allowed=[]
 qualification={'emulator-scenario.json','tools/emulator_check.py','tools/emulator_relay.py','tools/preview_image.py','tools/verify_reusable_build.py','README.md'}
 for name in git(root,'diff','--name-only',source,head,'--',app).decode().splitlines():
  suffix=name[len(app):]
  require(suffix in qualification or suffix.startswith('qualification-next/'),'Non-qualification support change disallows APK reuse: '+name);allowed.append(name)
 return {'schema':'coh-support-exact-apk-reuse-v1','passed':True,'apk_source_commit':source,'qualification_source_commit':head,'archive_sha256':archive_sha,'package':build['package'],'version_name':build['version_name'],'version_code':build['version_code'],'tracked_inputs_verified':len(checked),'tracked_generation_inputs_verified':generator_count,'tracked_input_hashes':checked,'external_generated_inputs_bound_by_original_artifact':len(external),'allowed_qualification_changes':allowed,'artifacts':[{'file':a['file'],'sha256':a['sha256'],'bytes':a['bytes']} for a in build['artifacts']],'scope':'Exact retained signed APK, packaged native library and assets verified against pinned artifact; tracked source/header/Java/Android packaging inputs equal original Git source, current HEAD and working bytes. No rebuild, emulator pass or physical acceptance is inferred. External/generated build inputs are retained artifact identities, not reacquired source.','signature_scope':'Original verified signature receipt preserved and exact signed APK bytes rehashed; signature verification is not rerun by this source-reuse checker.','android_emulator_qualified':False,'physical_thor_accepted':False}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,default=Path('.'));p.add_argument('--artifact-dir',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--expected-archive-sha256',required=True);p.add_argument('--expected-source-commit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 result=verify(a.source_root,a.artifact_dir,a.archive,a.expected_archive_sha256,a.expected_source_commit);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('passed','apk_source_commit','qualification_source_commit','tracked_inputs_verified')}))
if __name__=='__main__':main()
