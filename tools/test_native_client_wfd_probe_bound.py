"""Source/package guards only; synthetic SDK receipts are not native execution."""
from __future__ import annotations
import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import native_client_wfd_probe_bound as bound
import test_native_client_wfd_probe as original


def fake_probe(path):
    path.write_bytes(b'SYNTHETIC_SOURCE_CONTROL_NOT_A_PE COH_NATIVE_WFD_PROBE_V1')
    return {'size': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'pe_machine': 332, 'imports': ['KERNEL32.dll'], 'delay_imports': []}


def sdk_fixture(contract, exe, source_pin):
    """Exercise the real strict Python validator with explicitly synthetic bytes."""
    good, failed = contract.fixture(), contract.fixture(failed=True)
    labels = ['complete_readonly_named_dot_empty_branches', 'existing_output_refused',
              'sharing_denial_explicit_incomplete', 'output_inside_readonly_inputs_refused']
    cases = []
    for index, label in enumerate(labels):
        packet = (good, good, failed, b'')[index]
        observation = contract.parse(packet, contract.GENERATION, contract.OPERATION, 'C:/controlled/data') if index in (0, 2) else None
        receipt = {'format': 1,
            'status': ('complete_observation', 'exclusive_output_refused', 'incomplete_observation', 'arguments_or_abi_refused')[index],
            'operation': contract.OPERATION, 'generation': contract.GENERATION, 'windows_pid': 312,
            'rows': observation['footer']['rows'] if observation else 0,
            'directories': len(observation['directories']) if observation else 0,
            'bytes': len(packet) if observation else 0, 'issues': observation['footer']['issues'] if observation else 0,
            'output_created': index in (0, 2), 'exact_handle_cleanup_marked': False,
            'output_handle_closed': index in (0, 2), 'provider_authority': False, 'publication_allowed': False}
        stdout = (contract.MARKER + json.dumps(receipt) + '\n').encode()
        cases.append({'label': label, 'returncode': (0, 2, 2, 64)[index], 'receipt': receipt,
            'status': observation['status'] if observation else None,
            'stdout_base64': base64.b64encode(stdout).decode(), 'stderr_base64': '',
            'packet_base64': base64.b64encode(packet).decode(), 'packet_bytes': len(packet),
            'packet_sha256': hashlib.sha256(packet).hexdigest() if packet else None})
    return {'format': 1, 'role': 'Windows_SDK_readonly_ANSI_metadata_probe_fixture', 'status': 'passed',
        'source_sha256': source_pin['sha256'], 'probe': bound.pin(exe),
        'observed_ABI': {'pointer_bits': 32, 'WFD_bytes': 320, 'by_handle_bytes': 52, 'header_bytes': 160},
        'actual_windows_sdk_executed': True, 'native_Wine_executed': False, 'native_Game_executed': False,
        'physical_device_executed': False, 'current_provider_generation_qualified': False,
        'provider_authority': False, 'publication_allowed': False, 'cases': cases, 'observed_rows': 20}


class BoundProbeTests(unittest.TestCase):
    def stage(self, base):
        out = base/'prepared'; bound.prepare(out)
        return out/'tools'

    def package_fixture(self, base):
        sources = self.stage(base)
        contract = bound.load_contract(sources)
        exe = base/'synthetic.exe'; record = fake_probe(exe)
        checks = base/'synthetic-sdk.json'
        checks.write_text(json.dumps(sdk_fixture(contract, exe, bound.generated()['pins'][bound.C_SOURCE])))
        output = base/'package'
        with mock.patch.object(bound.native, 'validate_probe', return_value=record):
            value = bound.package(sources, exe, checks, output, 'a'*40,
                                  'https://github.com/Russianranger/coh-android/actions/runs/123')
        return output, record, value

    def test_exact_one_constant_each_and_original64_unchanged(self):
        source = bound.generated()
        self.assertEqual(bound.pin(bound.ROOT/'tools'/bound.C_SOURCE)['sha256'], bound.ORIGINAL_C_SHA)
        self.assertEqual(bound.pin(bound.ROOT/'tools'/bound.PARSER)['sha256'], bound.ORIGINAL_PARSER_SHA)
        self.assertEqual(source['bytes'][bound.C_SOURCE].replace(b'(96u * 1024u * 1024u)', b'(64u * 1024u * 1024u)'),
                         (bound.ROOT/'tools'/bound.C_SOURCE).read_bytes())
        self.assertEqual(source['bytes'][bound.PARSER].replace(b'= 96*1024**2,', b'= 64*1024**2,'),
                         (bound.ROOT/'tools'/bound.PARSER).read_bytes())
        self.assertEqual(original.MAX_BYTES, 64*1024**2)
        self.assertEqual(bound.FINITE_WIRE_MAX_BYTES, 91_403_315)
        self.assertLess(bound.FINITE_WIRE_MAX_BYTES, bound.MAX_BYTES)

    def test_generated96_parser_smoke_original_rejects_new_header(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = self.stage(Path(temporary)); contract = bound.load_contract(directory)
            raw = contract.fixture()
            self.assertEqual(contract.parse(raw, contract.GENERATION, contract.OPERATION, 'C:/controlled/data')['status'], 'complete_observation')
            with self.assertRaises(ValueError): original.parse(raw, original.GENERATION, original.OPERATION, 'C:/controlled/data')
            self.assertEqual(original.parse(original.fixture(), original.GENERATION, original.OPERATION, 'C:/controlled/data')['status'], 'complete_observation')
            self.assertEqual(contract.root_path(r'C:\controlled\data'), 'C:/controlled/data')
            self.assertEqual({p.name for p in directory.iterdir()}, {bound.C_SOURCE, bound.PARSER})
            self.assertFalse((directory/'__pycache__').exists())

    def test_missing_changed_doubled_original_pin_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary); tools = repository/'tools'; tools.mkdir()
            for name in (bound.C_SOURCE, bound.PARSER): (tools/name).write_bytes((bound.ROOT/'tools'/name).read_bytes())
            for mutation in ('double_constant', 'changed', 'missing'):
                source = tools/bound.C_SOURCE
                original_bytes = (bound.ROOT/'tools'/bound.C_SOURCE).read_bytes()
                if mutation == 'double_constant': source.write_bytes(original_bytes + b'\n#define PROBE_MAX_BYTES (64u * 1024u * 1024u)\n')
                elif mutation == 'changed': source.write_bytes(original_bytes.replace(b'PROBE_MAX_ROWS 200000u', b'PROBE_MAX_ROWS 300000u'))
                else: source.unlink()
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): bound.generated(repository)
                source.write_bytes(original_bytes)

    def test_generated_source_tamper_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = self.stage(Path(temporary))
            (directory/bound.PARSER).write_bytes((directory/bound.PARSER).read_bytes() + b'\nraise RuntimeError("UNTRUSTED")\n')
            with self.assertRaisesRegex(ValueError, 'generated source'): bound.load_contract(directory)

    def test_fresh_outputs_never_overwrite_existing_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); directory = self.stage(root)
            before = {name: bound.pin(directory/name) for name in (bound.C_SOURCE, bound.PARSER)}
            with self.assertRaises(ValueError): bound.prepare(directory.parent)
            self.assertEqual(before, {name: bound.pin(directory/name) for name in before})

    def test_synthetic_four_sdk_receipts_use_exact_generated_contract_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); sources = self.stage(root); contract = bound.load_contract(sources)
            exe = root/'synthetic.exe'; fake_probe(exe)
            proof = sdk_fixture(contract, exe, bound.generated()['pins'][bound.C_SOURCE])
            path = root/'sdk.json'; path.write_text(json.dumps(proof))
            self.assertEqual(bound.sdk_checks(path, exe, contract, bound.generated()['pins'][bound.C_SOURCE]), proof)
            for key, value in [('actual_windows_sdk_executed', 1), ('provider_authority', True),
                               ('source_sha256', bound.ORIGINAL_C_SHA), ('native_Game_executed', True)]:
                changed = copy.deepcopy(proof); changed[key] = value; path.write_text(json.dumps(changed))
                with self.subTest(key=key), self.assertRaises(ValueError): bound.sdk_checks(path, exe, contract, bound.generated()['pins'][bound.C_SOURCE])

    def test_source_only_package_mock_keeps_five_members_no_Game_or_pycache(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, record, value = self.package_fixture(Path(temporary))
            self.assertEqual({p.name for p in output.iterdir()}, bound.MEMBERS)
            self.assertEqual(len(bound.MEMBERS), 5)
            self.assertFalse(value['scope']['Game_recompiled'])
            self.assertEqual(value['retained_Game_artifact'], bound.RETAINED_GAME_ARTIFACT)
            self.assertEqual(value['packet_bound_bytes'], 96*1024**2)
            with mock.patch.object(bound.native, 'validate_probe', return_value=record):
                self.assertEqual(bound.validate(output, 'a'*40), value)
            self.assertFalse((output/'__pycache__').exists())

    def test_probe_PE32_Kernel32_only_no_delay_imports(self):
        with tempfile.TemporaryDirectory() as temporary:
            exe = Path(temporary)/'synthetic.exe'; record = fake_probe(exe)
            for field, value in [('pe_machine', 34404), ('imports', ['KERNEL32.dll', 'USER32.dll']),
                                  ('imports', []), ('delay_imports', ['KERNEL32.dll'])]:
                changed = copy.deepcopy(record); changed[field] = value
                with self.subTest(field=field), mock.patch.object(bound.native, 'validate_probe', return_value=changed), self.assertRaises(ValueError): bound.probe(exe)

    def test_manifest_authority_limit_original_Game_pin_and_producer_mutations_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            output, record, manifest = self.package_fixture(Path(temporary))
            for change in ('authority', 'cap', 'row_cap', 'Game_pin', 'commit', 'format'):
                value = copy.deepcopy(manifest)
                if change == 'authority': value['scope']['provider_authority'] = True
                elif change == 'cap': value['packet_bound_bytes'] = 128*1024**2
                elif change == 'row_cap': value['row_bound'] += 1
                elif change == 'Game_pin': value['retained_Game_artifact']['Game_sha256'] = '0'*64
                elif change == 'commit': value['producer_commit'] = 'b'*40
                else: value['format'] = True
                (output/bound.MANIFEST).write_text(json.dumps(value))
                with self.subTest(change=change), mock.patch.object(bound.native, 'validate_probe', return_value=record), self.assertRaises(ValueError): bound.validate(output, 'a'*40)

    def test_missing_extra_or_aliased_artifact_members_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); output, record, _ = self.package_fixture(root)
            (output/'CityOfHeroes.exe').write_bytes(b'forbidden')
            with self.assertRaises(ValueError): bound.validate(output, 'a'*40)
            (output/'CityOfHeroes.exe').unlink(); (output/bound.SDK).unlink()
            with self.assertRaises(ValueError): bound.validate(output, 'a'*40)

    def test_owned_regular_symlink_and_duplicate_JSON_guards(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); target = root/'input'; target.write_bytes(b'x'); link = root/'linked'; link.symlink_to(target)
            with self.assertRaises(ValueError): bound.regular(link)
            path = root/'duplicate.json'; path.write_text('{"a":1,"a":2}')
            with self.assertRaises(ValueError): bound.read(path)

    def test_strict_producer_identity_and_CLI_prepare_no_unexpected_outputs(self):
        for commit, url in [('a'*39, 'https://github.com/Russianranger/coh-android/actions/runs/1'),
            ('a'*40, 'https://github.com/other/repo/actions/runs/1'), ('a'*40, 'https://github.com/Russianranger/coh-android/actions/runs/0')]:
            with self.assertRaises(ValueError): bound.identity(commit, url)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)/'cli-prepared'
            result = subprocess.run([sys.executable, str(Path(bound.__file__)), 'prepare', '--output', str(output)], capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            row = json.loads(result.stdout)
            self.assertEqual(row['packet_bound_bytes'], bound.MAX_BYTES)
            self.assertFalse(row['Game_recompiled'])
            self.assertEqual({p.name for p in output.iterdir()}, {'tools'})
            self.assertEqual({p.name for p in (output/'tools').iterdir()}, {bound.C_SOURCE, bound.PARSER})


if __name__ == '__main__': unittest.main()
