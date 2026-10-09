"""Execute shipped staging reuse and copy methods with real files and Java I/O.

Tiny pinned assets and Android descriptor/stat adapters qualify the recovery
boundaries without allocating device-sized archives. Abrupt process termination
is a fixture for retry behavior, not evidence that Android LMK is prevented.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_runtime_setup_reuse import CLASS, HOST, compile_runtime_setup_host


COPY_HOST = HOST.split('    public static void main(String[] args)throws Exception {', 1)[0]
COPY_HOST = COPY_HOST.replace('    static boolean cancelling;', '    static boolean cancelling,stopAtRetainedRoot,stopAtStagingUnlink;')
COPY_HOST = COPY_HOST.replace(
    'static void remove(File root,SetupMemoryGuard control)throws IOException {control.beforeIo();remove(root);}',
    '''static void remove(File root,SetupMemoryGuard control)throws IOException {
        if(stopAtRetainedRoot&&root.getName().equals("rootfs")) {
            stopAtRetainedRoot=false;owner.cancelled=true;owner.outcome.cancelled=true;
        }
        if(stopAtStagingUnlink&&root.getName().endsWith(".staging")) {
            stopAtStagingUnlink=false;owner.cancelled=true;owner.outcome.cancelled=true;
        }
        control.beforeIo();remove(root);
    }''')
COPY_HOST = COPY_HOST.replace('    int opens;', '''    int opens;
    final Map<String,Integer> rawOpens=new HashMap<>(),fdOpens=new HashMap<>();
    boolean compressed,wrongDeclaredLength;
    String stopAsset;
    File raceTarget;
    InputStream input(String name,byte[] raw) {
        if(!name.equals(stopAsset))return new ByteArrayInputStream(raw);
        return new ByteArrayInputStream(raw) {
            boolean stopped;
            public synchronized int read(byte[] target,int offset,int length) {
                if(stopped){TarExtractor.owner.cancelled=true;TarExtractor.owner.outcome.cancelled=true;return -1;}
                stopped=true;return super.read(target,offset,Math.min(length,5));
            }
        };
    }
''')
COPY_HOST = COPY_HOST.replace(
    'opens++;byte[] raw=assets.get(name);',
    'opens++;rawOpens.put(name,rawOpens.getOrDefault(name,0)+1);byte[] raw=assets.get(name);')
COPY_HOST = COPY_HOST.replace(
    'return new ByteArrayInputStream(raw);}\n        InputStream open(String name,int mode)',
    'return input(name,raw);}\n        InputStream open(String name,int mode)')
COPY_HOST = COPY_HOST.replace(
    'byte[] raw=assets.get(name);if(raw==null)throw new IOException("missing asset");\n            return new android.content.res.AssetFileDescriptor(raw,raw.length);',
    '''fdOpens.put(name,fdOpens.getOrDefault(name,0)+1);
            if(compressed)throw new FileNotFoundException("compressed host fixture");
            byte[] raw=assets.get(name);if(raw==null)throw new IOException("missing asset");
            if(raceTarget!=null) {
                File stage=new File(TarExtractor.owner.home,TarExtractor.owner.generation.getName()+".staging");
                Files.createSymbolicLink(new File(stage,"assets/"+name.substring("runtime/".length())).toPath(),raceTarget.toPath());
                raceTarget=null;
            }
            return new android.content.res.AssetFileDescriptor(raw,wrongDeclaredLength?raw.length+1:raw.length){
                InputStream createInputStream()throws IOException{return input(name,raw);}
                public void close(){
                    if(wrongDeclaredLength) {
                        File stage=new File(TarExtractor.owner.home,TarExtractor.owner.generation.getName()+".staging");
                        RuntimeSetupHost.need(!Files.exists(new File(stage,"assets/"+name.substring("runtime/".length())).toPath(),LinkOption.NOFOLLOW_LINKS),"invalid descriptor created output before length validation");
                    }
                }
            };''')
COPY_HOST = COPY_HOST.replace(
    'boolean setupCleanupDeferred;', '''boolean setupCleanupDeferred,haltAfterVerified;
    int firstHashReports;long hashExpected,hashProcessed;''')
COPY_HOST = COPY_HOST.replace('    PRODUCTION_METHODS', '''    void fixtureCopy(File destination,String name,JSONObject pin)throws Exception {
        loadManifest();setupReceipt=new JSONObject();setupControl=setupMemoryControl();setupControl.admit();
        copySetupAsset(destination,name,pin);
    }
    boolean fixtureReusable(File candidate,JSONObject pin)throws Exception {
        loadManifest();setupReceipt=new JSONObject();setupControl=setupMemoryControl();setupControl.admit();
        return reusableSetupAsset(candidate,pin);
    }
    PRODUCTION_METHODS''')
COPY_HOST = COPY_HOST.replace(
    '        stages.add(text);',
    '''        stages.add(text);
        if(text.startsWith("Verifying postgresql-runtime.tar.gz: ")) {
            RuntimeSetupHost.need(setupReceipt.getString("current_input_file").equals("postgresql-runtime.tar.gz")&&setupReceipt.getString("current_input_operation").equals("sha256"),"hash checkpoint misattributed");
            firstHashReports++;hashExpected=setupReceipt.getLong("current_input_expected_bytes");hashProcessed=setupReceipt.getLong("current_input_processed_bytes");
        }
        if(haltAfterVerified&&name.equals("Copying runtime assets")&&text.endsWith("MiB verified"))
            Runtime.getRuntime().halt(73);''')
COPY_HOST += r'''
    static final String FIRST="postgresql-runtime.tar.gz",SECOND="dbserver-package.tar.gz";
    static int opens(Map<String,Integer> counts,String name){return counts.getOrDefault("runtime/"+name,0);}
    static void preservedFile(File file,Map<String,String> before)throws Exception {
        need(before.equals(snapshot(file)),"verified asset was rewritten or replaced");
    }
    static File staging(HostInstaller installer)throws Exception {
        byte[] manifest=installer.context.assets.get("runtime/runtime-manifest.json");
        return new File(installer.home,"runtime-"+digest(manifest).substring(0,16)+".staging");
    }
    static void seed(File root,HostContext context,boolean all)throws Exception {
        for(String name:new String[]{FIRST,SECOND,"dbserver-schema.tar.gz","fixture.txt"}) {
            if(!all&&!name.equals(FIRST))continue;
            HostInstaller.write(new File(root,"assets/"+name),context.assets.get("runtime/"+name));
        }
        TarExtractor.file(root,"rootfs/obsolete","unfinished extraction");
        TarExtractor.file(root,"wine/obsolete","unfinished extraction");
        TarExtractor.file(root,"ready.json","interrupted marker");
    }
    static void assertCopied(HostInstaller installer,int reused,int copied,long reusedBytes)throws Exception {
        JSONObject receipt=installer.getSetupReceipt();
        need(receipt.getString("mode").equals("installed")&&Boolean.TRUE.equals(receipt.get("runtime_activated")),"verified setup did not activate");
        need(receipt.getInt("runtime_payload_files_reused")==reused,"wrong reused payload count");
        need(receipt.getLong("runtime_payload_bytes_reused")==reusedBytes,"wrong verified reused byte count");
        need(receipt.getInt("runtime_payload_files_copied")==copied,"wrong copied payload count");
        long bytes=0;
        for(String name:new String[]{FIRST,SECOND,"dbserver-schema.tar.gz","fixture.txt"}) {
            byte[] expected=installer.context.assets.get("runtime/"+name);
            Path path=new File(installer.generation,"assets/"+name).toPath();
            need(Files.isRegularFile(path,LinkOption.NOFOLLOW_LINKS)&&((Number)Files.getAttribute(path,"unix:nlink",LinkOption.NOFOLLOW_LINKS)).longValue()==1,"activated payload is linked or nonregular");
            need(Arrays.equals(expected,Files.readAllBytes(path)),"copied asset differs from package pin");
            bytes+=expected.length;
        }
        need(receipt.getLong("runtime_payload_bytes_copied")==bytes-reusedBytes,"wrong copied byte count");
        need(!new File(installer.generation,"rootfs/obsolete").exists()&&!new File(installer.generation,"wine/obsolete").exists(),"interrupted extracted trees were trusted");
    }
    public static void main(String[] args)throws Exception {
        boolean temporary=args.length==1;
        File files=temporary?Files.createTempDirectory("setup-copy-").toFile():new File(args[1]);files.mkdirs();
        try {
            String scenario=args[0];HostContext context=assets();
            if(scenario.equals("stale_pin")) {
                JSONObject manifest=new JSONObject(new String(context.assets.get("runtime/runtime-manifest.json"),StandardCharsets.UTF_8));
                byte[] current=context.assets.get("runtime/"+FIRST).clone();current[0]^=1;
                context.assets.put("runtime/"+FIRST,current);manifest.getJSONObject("files").put(FIRST,pin(current));
                context.assets.put("runtime/runtime-manifest.json",manifest.toString().getBytes(StandardCharsets.UTF_8));
            }
            if(scenario.equals("large_reuse_hash")) {
                JSONObject manifest=new JSONObject(new String(context.assets.get("runtime/runtime-manifest.json"),StandardCharsets.UTF_8));
                byte[] current=new byte[5*1048576];Arrays.fill(current,(byte)41);
                context.assets.put("runtime/"+FIRST,current);manifest.getJSONObject("files").put(FIRST,pin(current));
                context.assets.put("runtime/runtime-manifest.json",manifest.toString().getBytes(StandardCharsets.UTF_8));
            }
            HostInstaller installer=new HostInstaller(files,context);downloads(installer);
            File profile=new File(files,"client/state/diagnostic/android-local-login");
            File imported=new File(files,"client-import/generation-00000000000000000000000000000000/data");
            File old=new File(installer.home,"runtime-0000000000000000");
            if(!new File(profile,"pgdata/keep").exists())TarExtractor.file(profile,"pgdata/keep","character database");
            if(!new File(imported,"keep").exists())TarExtractor.file(imported,"keep","accepted import");
            if(!new File(old,"ready.json").exists())TarExtractor.file(old,"ready.json","previous generation");
            Map<String,String> profileBefore=snapshot(profile),importBefore=snapshot(imported),oldBefore=snapshot(old);
            File stage=staging(installer),candidate=new File(stage,"assets/"+FIRST);
            long firstBytes=context.assets.get("runtime/"+FIRST).length,totalBytes=0;
            for(String name:new String[]{FIRST,SECOND,"dbserver-schema.tar.gz","fixture.txt"})totalBytes+=context.assets.get("runtime/"+name).length;
            Map<String,String> retained=null,protectedBefore=null,neighborBefore=null;
            Map<String,Map<String,String>> retainedAll=new HashMap<>();
            File protectedRoot=new File(files,"protected-external"),neighbor=new File(installer.home,"runtime-1111111111111111.staging");
            boolean all=scenario.equals("verified_all")||scenario.equals("cancel_resume")||scenario.equals("pressure_resume");
            if(!scenario.equals("after_kill")&&!scenario.equals("fd_uncompressed")&&!scenario.equals("fd_compressed")&&!scenario.equals("fd_wrong_length")&&!scenario.equals("kill_after_payload"))seed(stage,context,all);
            if(scenario.equals("verified_all")||scenario.equals("verified_one")||scenario.equals("owned_neighbor")||scenario.equals("cancel_resume")||scenario.equals("pressure_resume")||scenario.equals("copy_interrupt")||scenario.equals("large_reuse_hash")||scenario.equals("prepare_stop"))retained=snapshot(candidate);
            if(scenario.equals("verified_all"))for(String name:new String[]{FIRST,SECOND,"dbserver-schema.tar.gz","fixture.txt"})retainedAll.put(name,snapshot(new File(stage,"assets/"+name)));
            if(scenario.equals("corrupt")){byte[] raw=Files.readAllBytes(candidate.toPath());raw[0]^=1;Files.write(candidate.toPath(),raw);}
            if(scenario.equals("truncated"))Files.write(candidate.toPath(),new byte[]{1});
            if(scenario.equals("stale_pin")){byte[] oldBytes=context.assets.get("runtime/"+FIRST).clone();oldBytes[0]^=1;Files.write(candidate.toPath(),oldBytes);}
            if(scenario.equals("candidate_directory")){Files.delete(candidate.toPath());TarExtractor.file(candidate,"nested","untrusted directory");}
            if(scenario.equals("asset_symlink")||scenario.equals("asset_hardlink")||scenario.equals("create_race")) {
                HostInstaller.write(new File(protectedRoot,"keep"),context.assets.get("runtime/"+FIRST));Files.delete(candidate.toPath());
                Path target=new File(protectedRoot,"keep").toPath();
                if(scenario.equals("asset_symlink"))Files.createSymbolicLink(candidate.toPath(),target);
                else if(scenario.equals("asset_hardlink"))Files.createLink(candidate.toPath(),target);
                else context.raceTarget=target.toFile();
                protectedBefore=snapshot(protectedRoot);
            }
            if(scenario.equals("assets_symlink")) {
                TarExtractor.remove(new File(stage,"assets"));
                for(String name:new String[]{FIRST,SECOND,"dbserver-schema.tar.gz","fixture.txt"})HostInstaller.write(new File(protectedRoot,name),context.assets.get("runtime/"+name));
                Files.createSymbolicLink(new File(stage,"assets").toPath(),protectedRoot.toPath());protectedBefore=snapshot(protectedRoot);
            }
            if(scenario.equals("staging_symlink")||scenario.equals("staging_symlink_stop")) {
                TarExtractor.remove(stage);seed(protectedRoot,context,true);
                Files.createSymbolicLink(stage.toPath(),protectedRoot.toPath());protectedBefore=snapshot(protectedRoot);
                if(scenario.equals("staging_symlink_stop"))TarExtractor.stopAtStagingUnlink=true;
            }
            if(scenario.equals("unknown_asset"))TarExtractor.file(stage,"assets/not-in-current-manifest","unknown bytes");
            if(scenario.equals("unknown_staging"))TarExtractor.file(stage,"not-owned-by-installer","unknown bytes");
            if(scenario.equals("owned_neighbor")) {
                seed(neighbor,context,true);neighborBefore=snapshot(neighbor);
            }
            if(scenario.startsWith("metadata_")) {
                HostInstaller.write(new File(protectedRoot,"keep"),"linked metadata target must stay exact".getBytes(StandardCharsets.UTF_8));
                String metadata=scenario.contains("partial")?"runtime-manifest.json.part":"runtime-manifest.json";
                Path path=new File(stage,"assets/"+metadata).toPath(),target=new File(protectedRoot,"keep").toPath();
                if(scenario.endsWith("symlink"))Files.createSymbolicLink(path,target);else Files.createLink(path,target);
                protectedBefore=snapshot(protectedRoot);retained=snapshot(candidate);
            }
            if(scenario.equals("fd_compressed"))context.compressed=true;
            if(scenario.equals("fd_wrong_length"))context.wrongDeclaredLength=true;
            if(scenario.equals("kill_after_payload"))installer.haltAfterVerified=true;
            if(scenario.equals("prepare_stop")) {
                Files.write(new File(stage,"ready.json.part").toPath(),"stale ready output".getBytes(StandardCharsets.UTF_8));
                TarExtractor.stopAtRetainedRoot=true;
            }
            if(scenario.equals("after_kill")) {
                need(candidate.isFile()&&!new File(stage,"ready.json").exists(),"abrupt copy fixture lost incomplete owned staging");
                retained=snapshot(candidate);
            }
            if(scenario.equals("staging_symlink_stop")) {
                reject(installer::setupRuntime,"Diagnostic stopped");
                need(!installer.generation.exists()&&Files.isSymbolicLink(stage.toPath()),"Stop at staging unlink activated runtime or touched external link");
                need(Boolean.TRUE.equals(installer.getSetupReceipt().get("staging_cleanup_deferred")),"Stop at unsafe staging unlink lost guarded deferral");
                unchanged(protectedRoot,protectedBefore);
                installer=new HostInstaller(files,context);installer.setupRuntime();assertCopied(installer,0,4,0);
                unchanged(protectedRoot,protectedBefore);
            } else if(scenario.equals("prepare_stop")) {
                reject(installer::setupRuntime,"Diagnostic stopped");
                need(!installer.generation.exists()&&stage.isDirectory()&&!new File(stage,"ready.json").exists()&&!new File(stage,"ready.json.part").exists(),"Stop during retained staging cleanup left a success marker or activated runtime");
                need(Boolean.TRUE.equals(installer.getSetupReceipt().get("staging_cleanup_deferred")),"Stop during staging preparation lost retry state");
                preservedFile(candidate,retained);
                installer=new HostInstaller(files,context);installer.setupRuntime();assertCopied(installer,1,3,firstBytes);
                preservedFile(new File(installer.generation,"assets/"+FIRST),retained);
            } else if(scenario.equals("dot")||scenario.equals("dotdot")||scenario.equals("wrong_copy_parent")||scenario.equals("wrong_reuse_parent")) {
                HostInstaller.write(new File(protectedRoot,FIRST),context.assets.get("runtime/"+FIRST));
                protectedBefore=snapshot(protectedRoot);Map<String,String> stagingBefore=snapshot(stage);
                if(scenario.equals("wrong_reuse_parent")) {
                    need(!installer.fixtureReusable(new File(protectedRoot,FIRST),pin(context.assets.get("runtime/"+FIRST))),"foreign exact-pinned asset was reusable");
                } else {
                    String unsafeName=scenario.equals("dot")?".":scenario.equals("dotdot")?"..":FIRST;
                    File destination=scenario.equals("wrong_copy_parent")?new File(protectedRoot,FIRST):new File(stage,"assets/"+unsafeName);
                    HostInstaller tested=installer;
                    reject(()->tested.fixtureCopy(destination,unsafeName,pin(context.assets.get("runtime/"+FIRST))),"Unsafe package destination");
                }
                unchanged(stage,stagingBefore);unchanged(protectedRoot,protectedBefore);
                need(opens(context.rawOpens,FIRST)==0&&opens(context.fdOpens,FIRST)==0,"unsafe destination opened package before rejection");
            } else if(scenario.equals("create_race")) {
                reject(installer::setupRuntime,"");
                need(!installer.generation.exists()&&!stage.exists(),"raced destination was activated or left verified");
                unchanged(protectedRoot,protectedBefore);
            } else if(scenario.equals("fd_wrong_length")) {
                reject(installer::setupRuntime,"Package member length mismatch");
                need(!installer.generation.exists()&&!stage.exists(),"wrong descriptor length was activated or retained as verified");
                need(opens(context.fdOpens,FIRST)==1&&opens(context.rawOpens,FIRST)==0,"wrong descriptor length silently fell back");
            } else if(scenario.equals("copy_interrupt")) {
                context.stopAsset="runtime/"+SECOND;
                reject(installer::setupRuntime,"");
                need(!installer.generation.exists()&&stage.isDirectory()&&!new File(stage,"ready.json").exists(),"mid-copy interruption activated or removed retry staging");
                need(Boolean.TRUE.equals(installer.getSetupReceipt().get("staging_cleanup_deferred")),"mid-copy interruption did not retain retry state");
                preservedFile(candidate,retained);
                context.stopAsset=null;installer=new HostInstaller(files,context);installer.setupRuntime();assertCopied(installer,1,3,firstBytes);
                need(opens(context.rawOpens,FIRST)==0&&opens(context.fdOpens,FIRST)==0,"mid-copy retry reopened already verified asset");
                preservedFile(new File(installer.generation,"assets/"+FIRST),retained);
            } else if(scenario.equals("cancel_resume")||scenario.equals("pressure_resume")) {
                installer.cancelOnAssets=scenario.equals("cancel_resume");installer.pressureOnAssets=scenario.equals("pressure_resume");
                reject(installer::setupRuntime,scenario.equals("cancel_resume")?"Diagnostic stopped":"memory remained low");
                need(!installer.generation.exists()&&stage.isDirectory()&&!new File(stage,"ready.json").exists(),"stopped copy staging was activated or marked ready");
                need(Boolean.TRUE.equals(installer.getSetupReceipt().get("staging_cleanup_deferred")),"stopped copy retry state was discarded");
                need(opens(context.rawOpens,FIRST)==0&&opens(context.fdOpens,FIRST)==0,"stopped reuse reopened the package payload");
                preservedFile(candidate,retained);
                installer=new HostInstaller(files,context);installer.setupRuntime();assertCopied(installer,4,0,totalBytes);
                need(opens(context.rawOpens,FIRST)==0&&opens(context.fdOpens,FIRST)==0,"retry reopened verified package payload");
                preservedFile(new File(installer.generation,"assets/"+FIRST),retained);
            } else {
                installer.setupRuntime();
                int reused=scenario.equals("verified_all")?4:
                    scenario.equals("verified_one")||scenario.equals("owned_neighbor")||scenario.equals("after_kill")||scenario.equals("large_reuse_hash")||scenario.startsWith("metadata_")?1:0;
                assertCopied(installer,reused,4-reused,reused==4?totalBytes:reused==1?firstBytes:0);
                if(reused>0) {
                    need(opens(context.rawOpens,FIRST)==0&&opens(context.fdOpens,FIRST)==0,"verified asset reopened packaged bytes");
                    preservedFile(new File(installer.generation,"assets/"+FIRST),retained);
                }
                if(scenario.equals("verified_all")) {
                    for(String name:new String[]{FIRST,SECOND,"dbserver-schema.tar.gz","fixture.txt"}) {
                        need(opens(context.rawOpens,name)==0&&opens(context.fdOpens,name)==0,"retained asset reopened package");
                        preservedFile(new File(installer.generation,"assets/"+name),retainedAll.get(name));
                    }
                    need(installer.getSetupReceipt().getJSONObject("setup_memory_control").getLong("written_bytes")==0,"retained payload streamed new output bytes");
                }
                if(scenario.equals("fd_uncompressed"))need(opens(context.fdOpens,FIRST)==1&&opens(context.rawOpens,FIRST)==0,"uncompressed payload did not use descriptor path");
                if(scenario.equals("large_reuse_hash"))need(installer.firstHashReports==2&&installer.hashExpected==5L*1048576&&installer.hashProcessed==4L*1048576,"large retained hash did not report bounded actual progress during reuse and installed verification");
                if(scenario.equals("fd_compressed"))need(opens(context.fdOpens,FIRST)==1&&opens(context.rawOpens,FIRST)==1,"compressed/unavailable descriptor did not use pinned stream fallback");
                if(protectedBefore!=null)unchanged(protectedRoot,protectedBefore);
                if(neighborBefore!=null)unchanged(neighbor,neighborBefore);
            }
            unchanged(profile,profileBefore);unchanged(imported,importBefore);unchanged(old,oldBefore);
            System.out.println("PASS "+scenario);
        } finally {if(temporary)TarExtractor.remove(files);}
    }
}
'''


class SetupCopyMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-setup-copy-host-')
        cls.classes = Path(cls.temporary.name)
        compile_runtime_setup_host(cls.classes, COPY_HOST)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_host(self, scenario, root=None):
        args = ['java', '-Xmx64m', '-cp', str(self.classes), CLASS, scenario]
        if root is not None:
            args.append(str(root))
        return subprocess.run(args, capture_output=True, text=True, timeout=20)

    def check(self, *scenarios):
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                result = self.run_host(scenario)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual('PASS ' + scenario, result.stdout.strip())

    def test_all_verified_current_staging_assets_reuse_without_package_open_or_write(self):
        self.check('verified_all')

    def test_verified_one_asset_reuses_exact_bytes_and_copies_only_missing_payloads(self):
        self.check('verified_one')

    def test_large_retained_hash_reports_actual_progress_during_reuse_and_validation(self):
        self.check('large_reuse_hash')

    def test_corrupt_truncated_and_stale_pins_require_verified_replacement(self):
        self.check('corrupt', 'truncated', 'stale_pin')

    def test_symlink_and_hardlink_candidates_never_mutate_their_targets(self):
        self.check('asset_symlink', 'asset_hardlink')

    def test_directory_candidate_is_replaced_with_a_pinned_regular_file(self):
        self.check('candidate_directory')

    def test_destination_link_race_is_rejected_without_target_write(self):
        self.check('create_race')

    def test_dot_and_dotdot_are_rejected_before_any_unlink_or_package_open(self):
        self.check('dot', 'dotdot')

    def test_copy_and_reuse_require_the_exact_owned_current_assets_parent(self):
        self.check('wrong_copy_parent', 'wrong_reuse_parent')

    def test_linked_metadata_and_partial_outputs_are_unlinked_without_target_mutation(self):
        self.check('metadata_symlink', 'metadata_hardlink', 'metadata_partial_symlink', 'metadata_partial_hardlink')

    def test_linked_assets_or_staging_never_reuse_or_modify_external_trees(self):
        self.check('assets_symlink', 'staging_symlink')

    def test_stop_before_staging_symlink_unlink_preserves_external_ready_and_retry(self):
        self.check('staging_symlink_stop')

    def test_unknown_members_force_fresh_owned_staging(self):
        self.check('unknown_asset', 'unknown_staging')

    def test_only_the_exact_current_manifest_generation_staging_is_touched(self):
        self.check('owned_neighbor')

    def test_uncompressed_payload_uses_descriptor_input(self):
        self.check('fd_uncompressed')

    def test_compressed_payload_falls_back_to_verified_stream_input(self):
        self.check('fd_compressed')

    def test_mismatched_descriptor_length_fails_before_opening_or_creating_payload(self):
        self.check('fd_wrong_length')

    def test_stop_or_persistent_pressure_preserves_verified_assets_and_retry(self):
        self.check('cancel_resume', 'pressure_resume')

    def test_stop_during_retained_extraction_cleanup_clears_inherited_success_markers(self):
        self.check('prepare_stop')

    def test_interruption_inside_streaming_copy_retains_good_asset_and_recopies_partial(self):
        self.check('copy_interrupt')

    def test_abrupt_process_exit_never_activates_partial_and_retry_reuses_verified_payload(self):
        with tempfile.TemporaryDirectory(prefix='coh-setup-copy-kill-') as root:
            result = self.run_host('kill_after_payload', root)
            self.assertEqual(73, result.returncode, result.stderr)
            root = Path(root)
            staging = list((root / 'm2').glob('runtime-*.staging'))
            self.assertEqual(1, len(staging))
            self.assertFalse((staging[0] / 'ready.json').exists())
            self.assertFalse(staging[0].with_name(staging[0].name.removesuffix('.staging')).exists())
            reused = staging[0] / 'assets/postgresql-runtime.tar.gz'
            before = (reused.read_bytes(), reused.stat().st_ino, reused.stat().st_mtime_ns)
            protected = [root / name for name in (
                'client/state/diagnostic/android-local-login/pgdata/keep',
                'client-import/generation-00000000000000000000000000000000/data/keep',
                'm2/runtime-0000000000000000/ready.json')]
            prior = [(path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns) for path in protected]
            result = self.run_host('after_kill', root)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual('PASS after_kill', result.stdout.strip())
            final = reused.parent.parent.with_name(reused.parent.parent.name.removesuffix('.staging')) / reused.relative_to(reused.parent.parent)
            self.assertEqual(before, (final.read_bytes(), final.stat().st_ino, final.stat().st_mtime_ns))
            self.assertEqual(prior, [(path.read_bytes(), path.stat().st_ino, path.stat().st_mtime_ns) for path in protected])


if __name__ == '__main__':
    unittest.main()
