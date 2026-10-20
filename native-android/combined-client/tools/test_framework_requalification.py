"""Bounded source-equivalence and immutable-artifact refusal controls; no Android/build."""
import hashlib,json,os,tempfile,textwrap,unittest,subprocess,zipfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
WORKFLOW=ROOT/'.github/workflows/native-qualification.yml'


def admission_code():
    text=WORKFLOW.read_text()
    return textwrap.dedent(text.split("python3 - <<'PYFRAMEWORK'\n",1)[1].split('        PYFRAMEWORK\n',1)[0])


def module():
    namespace={'__name__':'bounded_framework_controls'}
    exec(compile(admission_code(),str(WORKFLOW),'exec'),namespace)
    return namespace


class FrameworkRequalification(unittest.TestCase):
    def test_branch_dispatch_and_read_only_reuse_job(self):
        text=WORKFLOW.read_text();job=text.split('  combined-framework:\n',1)[1]
        bootstrap=text.split('  dispatch-fullscreen-framework:\n',1)[1].split('  body-plan:\n',1)[0]
        self.assertIn('        - combined-framework\n',text)
        for guard in ('github.repository', 'refs/heads/native-android', "github.event_name == 'push'", '[fullscreen-framework-dispatch]', "github.run_attempt == '1'"):
            self.assertIn(guard,bootstrap)
        self.assertEqual(bootstrap.count('--method POST'),1)
        self.assertIn('branches/native-android --jq .commit.sha',bootstrap)
        self.assertIn('inputs[purpose]=combined-framework',bootstrap)
        self.assertIn("!contains(github.event.head_commit.message, '[fullscreen-framework-dispatch]')",text.split('  body-catalog:',1)[0])
        self.assertIn("inputs.purpose == 'combined-framework'",job)
        for forbidden in ('gradle.py','assembleDebug','lintDebug','prepare.py --','package_check.py --','gh release','contents: write'):
            self.assertNotIn(forbidden,job)
        for required in ('artifacts/12298379427/zip','artifacts/12289656309/zip','--candidate-source-revision 81a47f8ccef15c26e02b5cbf2feb4b99ac465139','--source-admission','--exercise-debuggable-downgrade','--previous-profile capture-diagnostic','api-level: 33','emulator_check.py --adb',"if: always()",'!native-android/results/combined-framework-requalification/**/*.apk'):
            self.assertIn(required,job)

    def test_source_changes_are_limited_to_named_nonshipping_files(self):
        ns=module()
        with tempfile.TemporaryDirectory(prefix='coh-framework-source-') as tmp:
            root=Path(tmp)
            def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.DEVNULL).decode().strip()
            git('init','-q');git('config','user.name','Read-only framework controls');git('config','user.email','framework-controls@example.invalid')
            shipping=root/'native-android/combined-client/app/build.gradle';shipping.parent.mkdir(parents=True);shipping.write_text('unchanged shipping build\n')
            driver=root/'native-android/combined-client/tools/emulator_check.py';driver.parent.mkdir(parents=True);driver.write_text('original driver\n')
            git('add','.');git('commit','-qm','candidate');base=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
            with patch.dict(os.environ,{'GITHUB_SHA':base}):ns['source_equivalence'](root,base,tree)
            driver.write_text('corrected nonshipping readiness\n');git('add','.');git('commit','-qm','driver')
            with patch.dict(os.environ,{'GITHUB_SHA':git('rev-parse','HEAD')}):
                _,changes,_=ns['source_equivalence'](root,base,tree);self.assertEqual(set(changes),{str(driver.relative_to(root))})
                shipping.write_text('dirty shipping change\n')
                with self.assertRaises(ValueError):ns['source_equivalence'](root,base,tree)
                git('add','.');git('commit','-qm','shipping mutation')
            with patch.dict(os.environ,{'GITHUB_SHA':git('rev-parse','HEAD')}),self.assertRaises(ValueError):ns['source_equivalence'](root,base,tree)

    def test_missing_or_unreviewed_source_changes_are_refused(self):
        ns=module()
        self.assertNotIn('native-android/combined-client/tools/upgrade_emulator_check.py',ns['ALLOWED'])
        self.assertNotIn('native-android/combined-client/app/src/main/java/org/coh/nativecombined/NativeClientActivity.java',ns['ALLOWED'])
        self.assertEqual(ns['BASE'],'81a47f8ccef15c26e02b5cbf2feb4b99ac465139')
        self.assertEqual(ns['ARCHIVE_BYTES'],25677911)
        self.assertEqual(ns['ARCHIVE_SHA'],'794c6c45ee0bde9002d7dcc5d02956137bc427171f3a6496f879f4b3a02c7d6d')
        with tempfile.TemporaryDirectory(prefix='coh-framework-refusal-') as tmp:
            root=Path(tmp);archive=root/'bad.zip';archive.write_bytes(b'not the pinned artifact')
            with self.assertRaises(ValueError):ns['restore_candidate'](archive,root/'out')
            self.assertFalse((root/'out').exists())

    def test_verified_archive_members_are_atomic_and_unchanged(self):
        ns=module();pins=ns['PINS'];contents={}
        for abi,label in [('arm64-v8a','arm64'),('x86_64','x86_64')]:
            name='CoH-Native-Combined-0.1.17-fullscreen-diagnostic-'+label+'.apk'
            raw=b'explicit synthetic package identity control '+abi.encode();contents[name]=raw
            identity={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            receipt=dict(status='passed',package='org.coh.nativecombined',build_profile='fullscreen-diagnostic',source_commit=ns['BASE'],tracked_source_clean=True,abi=abi,version_code='18',version_name='0.1.17-fullscreen-diagnostic-test',apk=dict(name=name,**identity),signer_certificate_sha256=ns['SIGNER'])
            audit=dict(passed=True,source_revision=ns['BASE'],abi=abi,apk=identity,internal_core_and_static_archive_exports_hidden=True,world_authority=False)
            contents[label+'-package.json']=json.dumps(receipt).encode();contents[label+'-interop-dso.json']=json.dumps(audit).encode()
        fixture_pins={name:(len(raw),hashlib.sha256(raw).hexdigest()) for name,raw in contents.items()}
        with tempfile.TemporaryDirectory(prefix='coh-framework-archive-') as tmp:
            root=Path(tmp);archive=root/'fixture.zip'
            with zipfile.ZipFile(archive,'w') as z:
                for name,raw in contents.items():z.writestr(name,raw)
            ns.update(PINS=fixture_pins,ARCHIVE_BYTES=archive.stat().st_size,ARCHIVE_SHA=hashlib.sha256(archive.read_bytes()).hexdigest())
            apks=ns['restore_candidate'](archive,root/'accepted')
            self.assertEqual(set(apks),{'arm64-v8a','x86_64'})
            for name,raw in contents.items():self.assertEqual((root/'accepted'/name).read_bytes(),raw)
            bad=dict(fixture_pins);name=next(iter(bad));bad[name]=(bad[name][0],'0'*64);ns['PINS']=bad
            with self.assertRaises(ValueError):ns['restore_candidate'](archive,root/'rejected')
            self.assertFalse((root/'rejected').exists())


if __name__=='__main__':unittest.main()
