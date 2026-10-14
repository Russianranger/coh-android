"""Source-only projection/custody/lifecycle tests; no new native process claim."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import tempfile
import textwrap
from types import SimpleNamespace
import unittest
from unittest import mock
import qualify_native_client_metadata_capture_wine as lane

class LaneTests(unittest.TestCase):
    def provider(self,base):
        root=base/'work'/'data';root.mkdir(parents=True)
        imported=base/'imported';imported.mkdir()
        for branch in ('texture_library','object_library','fx','scripts','scripts.loc'):
            directory=root/branch;directory.mkdir();(directory/'empty').mkdir()
            (directory/'.named-dir').mkdir()
            for filename in ('ordinary.txt','.named-file','asset.texture'):
                path=directory/filename;path.write_bytes(b'current immutable source facts');path.chmod(0o444)
        return root,imported

    def test_fresh_scan_encode_keeps_all_authority_false(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);root,imported=self.provider(base)
            packet,report=lane.projection(root,imported,'1'*32,{'runtime_source_equivalence':False},base/'projection')
            self.assertEqual(packet[:8],b'COHCNS1\0')
            self.assertEqual(report['fresh_metadata_passes'],2)
            self.assertEqual(report['complete_selected_branches'][-1],'scripts.loc')
            self.assertFalse(report['producer_capture_recipe_validation_executed'])
            self.assertFalse(report['fixed_Android_Wine_source_commit_asserted_for_host'])
            for field in lane.FALSE_AUTHORITY:self.assertIs(report[field],False)
            self.assertFalse(report['root_anchor_complete'])
            self.assertGreater(report['rows'],15)
            self.assertTrue(lane.recheck_projection(root,imported,report,base/'post.json')['matched'])

    def test_same_bytes_permission_change_between_passes_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);root,imported=self.provider(base)
            with self.assertRaises(ValueError):
                lane.projection(root,imported,'1'*32,{},base/'projection',between=lambda:(root/'fx/ordinary.txt').chmod(0o644))
            self.assertFalse((base/'projection').exists())

    def test_source_derived_projection_cannot_reuse_operation_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);root,imported=self.provider(base)
            packet,_=lane.projection(root,imported,'1'*32,{},base/'projection')
            with self.assertRaises(ValueError):lane.projection(root,imported,'2'*32,{},base/'projection')
            self.assertEqual((base/'projection/source-projection.bin').read_bytes(),packet)

    def test_post_native_metadata_change_retains_failed_recheck(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);root,imported=self.provider(base)
            _,report=lane.projection(root,imported,'1'*32,{},base/'projection')
            path=root/'fx/ordinary.txt';path.chmod(0o644);path.write_bytes(b'different content');path.chmod(0o444)
            with self.assertRaises(ValueError):lane.recheck_projection(root,imported,report,base/'post.json')
            self.assertFalse(json.loads((base/'post.json').read_text())['matched'])

    def test_guest_producer_pin_is_exact_and_no_recipe_success_claim(self):
        module=lane.producer_module()
        self.assertIsNone(module.PRODUCTION_AUTHORITY)
        self.assertIs(module.ACTIVATION_IMPLEMENTED,False)
        with mock.patch.object(lane,'PRODUCER_SOURCE','0'*64),self.assertRaises(ValueError):lane.producer_module()

    def test_only_authenticated_z_or_relative_provider_mappings(self):
        work=Path('/controlled/work')
        self.assertEqual(lane.mapped_native_path('Z:\\controlled\\work\\data',work),work/'data')
        self.assertEqual(lane.mapped_native_path('./piggs/server-animations.pigg',work),work/'piggs/server-animations.pigg')
        for path in ('C:/unknown/data','../unknown/data','bad\0data'):
            with self.assertRaises(ValueError):lane.mapped_native_path(path,work)
        with self.assertRaises(ValueError):lane.windows_path('/controlled/../unknown')

    def test_closed_prefix_rejects_identity_change_and_live_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            prefix=Path(temporary)/'prefix';prefix.mkdir(mode=0o700);info=prefix.lstat()
            identity=[info.st_dev,info.st_ino,info.st_uid]
            with mock.patch.object(lane.startup,'process_census',return_value=[]):lane.closed_prefix(prefix,identity)
            with mock.patch.object(lane.startup,'process_census',return_value=[{'pid':5}]),self.assertRaises(ValueError):lane.closed_prefix(prefix,identity)
            with mock.patch.object(lane.startup,'process_census',return_value=[]),self.assertRaises(ValueError):lane.closed_prefix(prefix,[0,0,os.geteuid()])

    def test_actual_pig_custody_requires_exact_archive_not_supplied_nonoverlap(self):
        work=Path('/controlled/work');fixture={'supplements':{'client_animation_package':{'pigg':{'sha256':'1'*64}}}}
        aux={'stable_inputs':{'piggs/server-animations.pigg':{'sha256':'1'*64}}}
        capture={'begin':{'gdd_root':'Z:/controlled/work/data'},'providers':[{'archive':'piggs/server-animations.pigg','virtual_location':-1,'folder_cache_mount':'piggs/server-animations.pigg:'}],'end':{'rows':2}}
        proof=lane.pig_custody(capture,work,fixture,aux)
        self.assertFalse(proof['branch_nonoverlap_qualified'])
        capture['providers'][0]['archive']='piggs/unknown.pigg'
        with self.assertRaises(ValueError):lane.pig_custody(capture,work,fixture,aux)

    def test_pre_native_failure_still_retains_current_outer_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);args=SimpleNamespace(output=base/'out',package=base/'package',package_commit='1'*40,donor_apk=base/'donor')
            with (mock.patch.dict('sys.modules',{'native_client_census_observed_bridge':SimpleNamespace()}),
                mock.patch.object(lane.native,'validate_package',side_effect=ValueError('injected admission failure')),
                mock.patch.object(lane.startup,'stop_prefix') as stop):
                with self.assertRaises(ValueError):lane.qualify(args)
                stop.assert_not_called()
            report=json.loads((base/'out/native-client-metadata-capture-Wine-qualification.json').read_text())
            self.assertEqual(report['status'],'failed')
            self.assertEqual(report['failure']['message'],'injected admission failure')
            self.assertFalse(report['provider_authority'])

    def test_prefix_custody_callback_precedes_any_wine_process(self):
        text=(lane.ROOT/'tools/qualify_native_client_startup.py').read_text()
        self.assertLess(text.index('prefix_created(args.prefix)'),text.index("boot = subprocess.run([tools['wine']['invocation']"))
        outer=Path(lane.__file__).read_text()
        self.assertIn('startup.check_held_prefix(args.prefix.absolute(),prefix_descriptor,prefix_info)',outer)
        self.assertIn('native_Game_timing_includes_preparation=False',outer)
        self.assertNotIn("capture(root, recipe",outer)

    def test_owned_prefix_outer_cleanup_runs_when_inner_report_finalizer_raises(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);root,imported=self.provider(base);assets=base/'assets';assets.mkdir()
            fixture=base/'fixture.json';fixture.write_text(json.dumps({'work':str(root.parent),'assets':str(assets),
                'actual_client_worktree':{'source_data':str(imported)},'texture_header_environment':{}}))
            args=SimpleNamespace(output=base/'out',package=base/'package',package_commit='1'*40,
                donor_apk=base/'donor',fixture=fixture,prefix=base/'prefix',timeout_seconds=900)
            provider={'files':0,'bytes':0,'directories':1};aux={'stable_inputs':{}}
            def interrupted_retained(arguments):
                arguments.prefix.mkdir(mode=0o700)
                arguments.prefix_created(arguments.prefix)
                raise RuntimeError('injected optional inner finalizer failure')
            with (mock.patch.dict('sys.modules',{'native_client_census_observed_bridge':SimpleNamespace()}),
                mock.patch.object(lane.native,'validate_package',return_value={'retained_public_client':{'native_member_closure':{}}}),
                mock.patch.object(lane.retained_helpers,'provider_snapshot',return_value=provider),
                mock.patch.object(lane.retained_helpers,'auxiliary_snapshot',return_value=aux),
                mock.patch.object(lane.retained_helpers,'native_closure'),
                mock.patch.object(lane.startup,'binary_tool',return_value={'resolved':'unit-system-runtime'}),
                mock.patch.object(lane.startup,'qualify',side_effect=interrupted_retained),
                mock.patch.object(lane.startup,'stop_prefix',return_value={'passed':True}) as stop):
                with self.assertRaises(ValueError):lane.qualify(args)
                stop.assert_called_once()
                self.assertEqual(stop.call_args.args[0],args.prefix)
            report=json.loads((args.output/'native-client-metadata-capture-Wine-qualification.json').read_text())
            self.assertEqual(report['status'],'failed');self.assertTrue(report['final_cleanup']['passed'])
            self.assertEqual(report['failure']['message'],'injected optional inner finalizer failure')
            self.assertTrue(json.loads((args.output/'owned-prefix-created.json').read_text())['held_before_any_native_Wine_process'])

    def test_native_probe_timeout_still_attempts_exact_owned_stop_and_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);root,imported=self.provider(base);prefix=base/'prefix';prefix.mkdir(mode=0o700)
            info=prefix.lstat();identity=[info.st_dev,info.st_ino,info.st_uid]
            executable=base/'probe.exe';executable.write_bytes(b'explicit synthetic fixture')
            tools={'wine':{'invocation':'unit-Wine','resolved':str(executable),'resolved_pin':lane.pin(executable)},'wineserver':{}}
            process=mock.Mock();process.poll.return_value=None
            with (mock.patch.object(lane.startup,'process_census',return_value=[]),
                mock.patch.object(lane.subprocess,'Popen',return_value=process),
                mock.patch.object(lane.time,'monotonic',side_effect=[0,40,45]),
                mock.patch.object(lane.startup,'stop_prefix',return_value={'passed':True}) as stop):
                with self.assertRaises(ValueError):lane.run_probe(executable,root.parent,prefix,identity,{'WINEPREFIX':str(prefix)},tools,base/'probe-out','1'*64,'2'*32,1)
                self.assertIs(stop.call_args.kwargs['owned_process'],process)
            report=json.loads((base/'probe-out/native-probe-phase.json').read_text())
            self.assertEqual(report['status'],'failed');self.assertTrue(report['cleanup']['passed'])
            self.assertFalse(report['provider_authority'])

    def test_capture_workflow_reuses_native_bytes_and_prepares_one_provider(self):
        workflow=(lane.ROOT/'.github/workflows/android-native-client-metadata-capture-wine.yml').read_text()
        jobs=workflow.split('\njobs:\n',1)[1]
        self.assertEqual(re.findall(r'^  ([A-Za-z0-9_-]+):\s*$',jobs,re.M),['actual-client-capture'])
        self.assertNotIn('cmake --build',workflow)
        self.assertNotIn('cl /nologo',workflow)
        self.assertEqual(workflow.count('inputs.ensure_assets('),1)
        self.assertEqual(workflow.count('tools/prepare_native_client_profile_fixture.py --donor-apk'),1)
        self.assertIn('libgl1-mesa-dri:i386',workflow)
        self.assertIn('11866594540',workflow)
        self.assertIn('4e3188d7dffd2790bbc73e49f9e3fa55df90f016',workflow)
        programs=re.findall(r"(?ms)^([ ]*)python3 - <<'PYTHON'\n(.*?)^\1PYTHON\s*$",workflow)
        self.assertEqual(len(programs),3)
        for _,body in programs:compile(textwrap.dedent(body),'<capture-workflow>','exec')

    def test_unknown_probe_packet_limit_refused_before_operation(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            with self.assertRaises(ValueError):
                lane.run_probe(base/'probe',base/'work',base/'prefix',[],{}, {},base/'output',
                    '1'*64,'2'*32,contract=SimpleNamespace(MAX_BYTES=128*1024**2))
            self.assertFalse((base/'output').exists())

    def test_external_probe_must_be_authenticated_after_original_package(self):
        source=Path(lane.__file__).read_text()
        self.assertLess(source.index('build=native.validate_package('),source.index('extension_value=bound.validate('))
        self.assertIn('probe_contract=bound.load_contract(extension)',source)
        self.assertIn('contract=probe_contract',source)
        self.assertIn('sidecar.stat().st_size<=contract.MAX_BYTES',source)
        self.assertIn("'native_probe_RSS_measured':False",source)

    def test_probe_only_repair_workflow_builds_once_without_Game_recompile(self):
        workflow=(lane.ROOT/'.github/workflows/android-native-client-metadata-probe-bound.yml').read_text()
        jobs=workflow.split('\njobs:\n',1)[1]
        self.assertEqual(re.findall(r'^  ([A-Za-z0-9_-]+):\s*$',jobs,re.M),['probe-windows','actual-client-capture'])
        self.assertEqual(workflow.count('cl /nologo'),1)
        self.assertNotIn('cmake --build',workflow)
        self.assertNotIn('package_native_client_metadata_capture.py stage',workflow)
        self.assertIn('needs: probe-windows',workflow)
        self.assertEqual(workflow.count('inputs.ensure_assets('),1)
        self.assertEqual(workflow.count('tools/prepare_native_client_profile_fixture.py --donor-apk'),1)
        self.assertIn('--probe-extension out/probe-bound',workflow)
        self.assertIn("producer[0]['conclusion']=='success'",workflow)
        programs=re.findall(r"(?ms)^([ ]*)python3 - <<'PYTHON'\n(.*?)^\1PYTHON\s*$",workflow)
        self.assertEqual(len(programs),5)
        for _,body in programs:compile(textwrap.dedent(body),'<bound-workflow>','exec')

    def test_Windows_exact_byte_preservation_precedes_checkout_and_pin_controls(self):
        workflow=(lane.ROOT/'.github/workflows/android-native-client-metadata-probe-bound.yml').read_text()
        windows=workflow.split('  probe-windows:',1)[1].split('  actual-client-capture:',1)[0]
        preserve=windows.index('git config --global core.autocrlf false')
        checkout=windows.index('actions/checkout@')
        guards=windows.index('python -m unittest test_native_client_wfd_probe_bound')
        self.assertLess(preserve,checkout)
        self.assertLess(checkout,guards)
        self.assertEqual(windows.count('git config --global core.autocrlf false'),1)
        self.assertNotIn('replace(',windows)

    def test_enabled_current_Game_evidence_precedes_final_strict_probe_gate(self):
        source=Path(lane.__file__).read_text()
        enabled=source.index("value['capture_enabled']=phase")
        pig=source.index("value['actual_native_PIG_index']=capture")
        stats=source.index("value['actual_native_stat_snapshots']=")
        persist=source.index("write(args.output/'enabled-Game-observations-before-probe.json'")
        probe=source.index('probe=run_probe(probe_executable,')
        gate=source.index("require(value['consumed_field_mapping_gate_passed']")
        self.assertLess(enabled,pig);self.assertLess(pig,stats)
        self.assertLess(stats,persist);self.assertLess(persist,probe);self.assertLess(probe,gate)
        self.assertIn("COH_CLIENT_BIN_PROFILE='1'",source)
        self.assertIn('enabled Game before WFD probe',source)

    def test_fixed_namespace_enters_generation_before_native_and_final_cleanup(self):
        source=Path(lane.__file__).read_text()
        admitted=source.index('mapping.admit()')
        provenance=source.index("provenance['probe_namespace']=mapping.report()")
        encoded=source.index('packet,report=projection(')
        bound=source.index('mapping.bind_census(packet)')
        enabled=source.index("phase=startup.launch_case(SimpleNamespace(native_role='metadata-capture-enabled'")
        self.assertLess(admitted,provenance);self.assertLess(provenance,encoded)
        self.assertLess(encoded,bound);self.assertLess(bound,enabled)
        self.assertIn("mapping.report()['path_census_admitted'] is True",source)
        self.assertIn("mapping.native_root=='X:/data'",source)
        self.assertIn('_close_capture_handles(value,mapping,prefix_descriptor)',source)
        self.assertIn('native_Game_absolute_root_or_volume_or_shortname_equivalence_claimed',source)

    def test_reuse_only_workflow_requires_real_successful_jobs_not_whole_failed_run(self):
        workflow=(lane.ROOT/'.github/workflows/android-native-client-metadata-capture-reuse-wine.yml').read_text()
        jobs=workflow.split('\njobs:\n',1)[1]
        self.assertEqual(re.findall(r'^  ([A-Za-z0-9_-]+):\s*$',jobs,re.M),['actual-client-capture'])
        for command in ('cl /nologo','cmake --build','native_client_wfd_probe_bound.py prepare','native_client_wfd_probe_bound.py package'):
            self.assertNotIn(command,workflow)
        for pin in ('11866594540','11869483251','115678115609','10f3ac8853b270088456db8116275108615b0e87','9edfad23f057ebbc678a52274f95707a2c04e4ea6942275f35de705ac0a1c4d2'):
            self.assertIn(pin,workflow)
        self.assertIn("run['conclusion']=='failure'",workflow)
        self.assertIn("producer[0]['conclusion']=='success'",workflow)
        self.assertIn('--short-probe-namespace',workflow)
        self.assertEqual(workflow.count('inputs.ensure_assets('),1)
        programs=re.findall(r"(?ms)^([ ]*)python3 - <<'PYTHON'\n(.*?)^\1PYTHON\s*$",workflow)
        self.assertEqual(len(programs),5)
        for _,body in programs:compile(textwrap.dedent(body),'<reuse-workflow>','exec')

    def test_mapping_FD_close_error_cannot_skip_prefix_release_or_durable_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);descriptor=os.open(base,os.O_RDONLY|os.O_DIRECTORY)
            mapping=mock.Mock();mapping.close.side_effect=OSError('injected mapping FD close failure')
            value={'status':'passed','failure':None}
            lane._close_capture_handles(value,mapping,descriptor)
            mapping.close.assert_called_once()
            with self.assertRaises(OSError):os.fstat(descriptor)
            lane.write(base/'qualification.json',value)
            saved=json.loads((base/'qualification.json').read_text())
            self.assertEqual(saved['status'],'failed')
            self.assertFalse(saved['descriptor_finalization'][0]['closed'])
            self.assertTrue(saved['descriptor_finalization'][1]['closed'])
            self.assertEqual(saved['descriptor_finalization'][0]['message'],'injected mapping FD close failure')
        source=Path(lane.__file__).read_text()
        self.assertLess(source.index('_close_capture_handles(value,mapping,prefix_descriptor)',source.index('    finally:',source.index('def qualify('))),
            source.index("write(args.output/'native-client-metadata-capture-Wine-qualification.json'"))

if __name__=='__main__':unittest.main()
