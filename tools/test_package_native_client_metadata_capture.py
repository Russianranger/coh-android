"""Capture package guards; synthetic changed PE/receipts are not native execution."""
from __future__ import annotations
import copy
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
import zipfile
import package_native_client_metadata_capture as package

DONOR_APK = Path(os.environ.get('COH_PUBLIC036_DONOR_APK', '/workspace/scratch/5d16603ca7ff/publication-037-evidence/COH-Atlas-Gameplay-0.13.36.apk'))

class CapturePackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not DONOR_APK.is_file():raise ValueError('Exact public .36 donor required via COH_PUBLIC036_DONOR_APK')
        cls.donor=package.donor(DONOR_APK)
        with zipfile.ZipFile(DONOR_APK) as apk:
            with zipfile.ZipFile(io.BytesIO(apk.read('assets/runtime/client-runtime.zip'))) as native:
                cls.game=native.read('CityOfHeroes.exe')
        cls.controls={'format':1,'role':'portable_source_controls_for_native_capture','status':'passed',
            'repository_commit':'a'*40,'source_recipe':package.source.expected_receipt(),'host_tests':50,
            'host_modules':list(package.HOST_MODULES),
            'host_control_sources':{name:package.pin(package.ROOT/'tools'/(name+'.py')) for name in package.HOST_MODULES},
            'native_windows_executed':False,'native_game_executed':False,'publication_allowed':False}

    def image(self, root, marker=True):
        path=Path(root)/'CityOfHeroes.exe'
        path.write_bytes(self.game+(b'\nSYNTHETIC_UNIT_IMAGE\nCOH_NATIVE_PIG_INDEX_CAPTURE_V1' if marker else b'unit-change'))
        return path

    def test_public_donor_full_original_closure(self):
        self.assertEqual(self.donor['native_game']['sha256'],package.GAME_SHA)
        self.assertEqual(len(self.donor['native_member_closure']),21)
        self.assertFalse(self.donor['native_donor_rebuilt'])
        self.assertFalse(self.donor['original_archive_or_receipts_rewritten'])

    def test_changed_donor_refused_before_zip(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'wrong.apk';path.write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError,'independently audited'):package.donor(path)

    def test_original_game_cannot_claim_capture_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'CityOfHeroes.exe';path.write_bytes(self.game)
            with self.assertRaisesRegex(ValueError,'Fresh changed Win32'):package.validate_game(path,self.donor)

    def test_changed_image_retains_actual_pe_import_parser(self):
        with tempfile.TemporaryDirectory() as temporary:
            actual=package.validate_game(self.image(temporary),self.donor)
            self.assertEqual(actual['imports'],self.donor['native_game']['imports'])

    def test_changed_dll_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=self.image(temporary);path.write_bytes(path.read_bytes().replace(b'cg.dll\0',b'xx.dll\0',1))
            with self.assertRaisesRegex(ValueError,'DLL/ABI closure'):package.validate_game(path,self.donor)

    def test_wrong_machine_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=self.image(temporary);raw=bytearray(path.read_bytes());offset=struct.unpack_from('<I',raw,60)[0]
            struct.pack_into('<H',raw,offset+4,0x8664);path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'Win32'):package.validate_game(path,self.donor)

    def test_marker_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError,'marker'):package.validate_game(self.image(temporary,False),self.donor)

    def test_source_controls_scope_is_portable_only(self):
        self.assertFalse(package.validate_fixture(copy.deepcopy(self.controls))['native_windows_executed'])
        for field in ('native_windows_executed','native_game_executed','publication_allowed'):
            with self.subTest(field=field):
                value=copy.deepcopy(self.controls);value[field]=True
                with self.assertRaisesRegex(ValueError,'source-only'):package.validate_fixture(value)

    def test_control_schema_types_exact(self):
        for field,value in [('format',True),('host_tests',50.0),('host_tests',True),('host_tests',49)]:
            with self.subTest(field=field,value=value):
                controls=copy.deepcopy(self.controls);controls[field]=value
                with self.assertRaises(ValueError):package.validate_fixture(controls)

    def test_control_source_changes_refused(self):
        controls=copy.deepcopy(self.controls);controls['source_recipe']['patched_sha256'][package.source.STAT_SOURCE]='0'*64
        with self.assertRaisesRegex(ValueError,'source recipe'):package.validate_fixture(controls)

    def test_control_unknown_fields_refused(self):
        controls=copy.deepcopy(self.controls);controls['provider_authority']=True
        with self.assertRaises(ValueError):package.validate_fixture(controls)

    def test_cmake_requires_exact_capture_injection_and_game_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'CMakeCache.txt'
            base='COH_PG_PERSISTENCE_TESTS:BOOL=OFF\nCMAKE_GENERATOR_PLATFORM:INTERNAL=Win32\n'
            capture='CMAKE_PROJECT_INCLUDE:FILEPATH=C:/source/'+package.source.CMAKE_INJECTION+'\nCOX_BUILD_MAPSERVER:BOOL=OFF\nCOX_BUILD_BEACONSERVER:BOOL=OFF\n'
            path.write_text(base+capture);self.assertEqual(package.validate_cache(path)['bytes'],path.stat().st_size)
            for changed in (base,base+capture.replace('MAPSERVER:BOOL=OFF','MAPSERVER:BOOL=ON'),base+capture.replace(package.source.CMAKE_INJECTION,'other.cmake')):
                path.write_text(changed)
                with self.assertRaises(ValueError):package.validate_cache(path)

    def test_probe_metadata_guard_is_readonly_win32(self):
        # Mocked PE records here test structure only; the build gate parses a real PE.
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'probe.exe';path.write_bytes(b'COH_NATIVE_WFD_PROBE_V1')
            record={'size':path.stat().st_size,'sha256':'1'*64,'pe_machine':332,'imports':['KERNEL32.dll'],'delay_imports':[]}
            with mock.patch.object(package,'file_record',return_value=record):self.assertEqual(package.validate_probe(path),record)
            for field,value in [('pe_machine',34404),('imports',['OPENGL32.dll']),('delay_imports',['user32.dll'])]:
                changed=copy.deepcopy(record);changed[field]=value
                with mock.patch.object(package,'file_record',return_value=changed),self.assertRaises(ValueError):package.validate_probe(path)
            path.write_bytes(b'other')
            with mock.patch.object(package,'file_record',return_value=record),self.assertRaisesRegex(ValueError,'marker'):package.validate_probe(path)

    def test_extra_native_members_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name in package.MEMBERS|{package.MANIFEST,'MapServer.exe'}:(root/name).write_text('{}')
            with self.assertRaisesRegex(ValueError,'member closure'):package.validate_package(root,'a'*40,DONOR_APK)

    def test_missing_probe_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name in (package.MEMBERS|{package.MANIFEST})-{package.FIXTURE}:(root/name).write_text('{}')
            with self.assertRaisesRegex(ValueError,'member closure'):package.validate_package(root,'a'*40,DONOR_APK)

    def test_symlink_inputs_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);target=root/'input';target.write_bytes(b'a');link=root/'link';link.symlink_to(target)
            with self.assertRaises(ValueError):package.regular(link)

    def test_source_actions_identity_strict(self):
        for commit,run in [('a'*39,'https://github.com/Russianranger/coh-android/actions/runs/1'),('a'*40,'https://github.com/other/coh-android/actions/runs/1'),('a'*40,'https://github.com/Russianranger/coh-android/actions/runs/0')]:
            with self.assertRaises(ValueError):package.identity(commit,run)

    def test_scope_closes_all_runtime_authority(self):
        for field in ('native_game_runtime_qualified','native_wine_executed','physical_device_executed','publication_allowed','provider_authority_granted'):
            self.assertIs(package.SCOPE[field],False)
        self.assertIs(package.SCOPE['probe_is_qualification_only'],True)

    def sdk_fixture(self,probe):
        import test_native_client_wfd_probe as contract
        good,failed=contract.fixture(),contract.fixture(failed=True)
        cases=[]
        labels=['complete_readonly_named_dot_empty_branches','existing_output_refused','sharing_denial_explicit_incomplete','output_inside_readonly_inputs_refused']
        for i,label in enumerate(labels):
            packet=(good,good,failed,b'')[i]
            observation=contract.parse(packet,contract.GENERATION,contract.OPERATION,'C:/controlled/data') if i in (0,2) else None
            receipt={'format':1,'status':('complete_observation','exclusive_output_refused','incomplete_observation','arguments_or_abi_refused')[i],
                'operation':contract.OPERATION,'generation':contract.GENERATION,'windows_pid':312,
                'rows':observation['footer']['rows'] if observation else 0,'directories':len(observation['directories']) if observation else 0,
                'bytes':len(packet) if observation else 0,'issues':1 if i==2 else 0,
                'output_created':i in (0,2),'exact_handle_cleanup_marked':False,'output_handle_closed':i in (0,2),
                'provider_authority':False,'publication_allowed':False}
            stdout=(contract.MARKER+json.dumps(receipt)+'\n').encode()
            cases.append({'label':label,'returncode':(0,2,2,64)[i],'receipt':receipt,
                'status':observation['status'] if observation else None,
                'stdout_base64':base64.b64encode(stdout).decode(),'stderr_base64':'',
                'packet_base64':base64.b64encode(packet).decode(),'packet_bytes':len(packet),
                'packet_sha256':hashlib.sha256(packet).hexdigest() if packet else None})
        return {'format':1,'role':'Windows_SDK_readonly_ANSI_metadata_probe_fixture','status':'passed',
            'source_sha256':package.pin(package.ROOT/'tools/native_client_wfd_probe.c')['sha256'],'probe':package.pin(probe),
            'observed_ABI':{'pointer_bits':32,'WFD_bytes':320,'by_handle_bytes':52,'header_bytes':160},
            'actual_windows_sdk_executed':True,'native_Wine_executed':False,'native_Game_executed':False,
            'physical_device_executed':False,'current_provider_generation_qualified':False,
            'provider_authority':False,'publication_allowed':False,'cases':cases,'observed_rows':20}

    def test_synthetic_sdk_material_roundtrip_structure_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            probe=Path(temporary)/'probe.exe';probe.write_bytes(b'synthetic unit probe bytes')
            value=self.sdk_fixture(probe)
            self.assertEqual(package.validate_probe_checks(value,probe),value)

    def test_sdk_raw_packet_and_stdout_mutation_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            probe=Path(temporary)/'probe.exe';probe.write_bytes(b'synthetic unit probe bytes')
            for field,value in [('packet_sha256','0'*64),('packet_bytes',0),('stdout_base64','')]:
                proof=self.sdk_fixture(probe);proof['cases'][0][field]=value
                with self.subTest(field=field),self.assertRaises(ValueError):package.validate_probe_checks(proof,probe)

    def test_sdk_scope_and_native_source_mutations_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            probe=Path(temporary)/'probe.exe';probe.write_bytes(b'synthetic unit probe bytes')
            for field,value in [('provider_authority',True),('native_Wine_executed',True),('source_sha256','0'*64),('actual_windows_sdk_executed',1)]:
                proof=self.sdk_fixture(probe);proof[field]=value
                with self.subTest(field=field),self.assertRaises(ValueError):package.validate_probe_checks(proof,probe)

    def test_sdk_console_status_code_and_cleanup_must_match_exact_outcomes(self):
        import test_native_client_wfd_probe as contract
        with tempfile.TemporaryDirectory() as temporary:
            probe=Path(temporary)/'probe.exe';probe.write_bytes(b'synthetic unit probe bytes')
            for field,value in [('status','failed'),('exact_handle_cleanup_marked',True),('issues',4)]:
                proof=self.sdk_fixture(probe);proof['cases'][0]['receipt'][field]=value
                proof['cases'][0]['stdout_base64']=base64.b64encode((contract.MARKER+json.dumps(proof['cases'][0]['receipt'])+'\n').encode()).decode()
                with self.subTest(field=field),self.assertRaises(ValueError):package.validate_probe_checks(proof,probe)
            proof=self.sdk_fixture(probe);proof['cases'][1]['returncode']=64
            with self.assertRaises(ValueError):package.validate_probe_checks(proof,probe)

    def test_sdk_existing_output_and_denied_readability_evidence_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            probe=Path(temporary)/'probe.exe';probe.write_bytes(b'synthetic unit probe bytes')
            proof=self.sdk_fixture(probe);proof['cases'][1]['packet_base64']='';proof['cases'][1]['packet_bytes']=0;proof['cases'][1]['packet_sha256']=None
            with self.assertRaises(ValueError):package.validate_probe_checks(proof,probe)
            proof=self.sdk_fixture(probe);proof['cases'][2]['returncode']=0
            with self.assertRaises(ValueError):package.validate_probe_checks(proof,probe)

    def test_duplicate_receipt_keys_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'receipt.json';path.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(ValueError,'Duplicate'):package.read(path)

    def test_one_fresh_compile_and_explicit_no_replay_workflow(self):
        text=(package.ROOT/'.github/workflows/android-native-client-metadata-capture.yml').read_text()
        self.assertEqual(text.count('cmake --build '),1)
        self.assertEqual(text.count('cl /nologo /O2 /MT /TC tools/native_client_wfd_probe.c'),1)
        self.assertIn('needs: portable-controls',text)
        self.assertIn('--windows-qualify --probe',text)
        self.assertIn('-DCOX_BUILD_MAPSERVER=OFF -DCOX_BUILD_BEACONSERVER=OFF',text)
        self.assertIn('-DCMAKE_PROJECT_INCLUDE=',text)
        self.assertNotIn('-DCOH_CLIENT_METADATA_CENSUS_PROTOTYPE',text)

if __name__=='__main__':unittest.main()
