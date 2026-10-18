#!/usr/bin/env python3
"""New Inventory/A13 receiver metadata mocks only; never execute native or loader."""
import argparse
import ast
from contextlib import ExitStack, contextmanager
import copy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = MODULE = FROZEN = HELPER = None
CASES = []
READS = {}
CORE = ['Refused','need','digest','raw','child','git','committed','fixed','static_elf',
        'system_files','loader_checks','imported_sources','write_new','unlink_owned','export_env','main']
FROZEN_SHA = '99f47dd7d3e6e9a0475a83d498a7c3318bcfc1e40c9140d89948c28942e4c553'
BASE_SHA = 'c5a49d446423ac76ab2977a75a5e8bcb3a817daeb55c1d2dd30092933238c01e'
OWN = 'native-android/combined-client/tools/admit_initial_inventory_receiver.py'
MODES = ('release','address','undefined')

def sha(raw): return hashlib.sha256(raw).hexdigest()
def js(raw): return json.loads(raw)
def at(name): return (ROOT / name).read_bytes()
def encoded(value): return (json.dumps(value, indent=2) + '\n').encode()
def objects(raw):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body
            if isinstance(n,(ast.FunctionDef,ast.ClassDef))}

class Controls(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(MODULE.subprocess,'Popen',side_effect=AssertionError('process prohibited')))
        self.stack.enter_context(patch.object(MODULE.subprocess,'run',side_effect=AssertionError('subprocess prohibited')))
        self.stack.enter_context(patch.object(MODULE.subprocess,'check_output',side_effect=AssertionError('subprocess prohibited')))
        self.stack.enter_context(patch.object(MODULE.importlib,'import_module',side_effect=AssertionError('project import prohibited')))
        original = MODULE.raw
        def recorded(path, maximum=8*1024**2):
            raw = original(path, maximum)
            if ROOT in path.parents:
                READS[path.relative_to(ROOT).as_posix()] = sha(raw)
            return raw
        self.stack.enter_context(patch.object(MODULE,'raw',side_effect=recorded))
    def check(self, condition, name):
        self.assertTrue(condition, name); CASES.append(name)
    def refused(self, function, name, code=None):
        with self.assertRaises(MODULE.Refused) as result: function()
        if code is not None:self.assertEqual(result.exception.code,code,name)
        CASES.append(name)
    def observer(self, mutate=None):
        old = js(at('native-android/engine/scenecatalog-server/evidence/fresh-callback-profile-20261018/compile-owner-predicates-20261018/compile-only-receipt.json'))
        focused = js(at(MODULE.FOLLOWUP))
        names = {'source/Common/seq/coh_fresh_folder_profile_api.h':'source_folder_profile_api.h',
         'source/libs/UtilitiesLib/src/utils/coh_fresh_folder_profile_api.h':'source_folder_profile_api.h',
         'source/libs/UtilitiesLib/src/utils/coh_fresh_folder_profile.inc':'source_folder_profile.inc',
         'source/MapServer/src/group/coh_fresh_source_profile.inc':'source_group_profile.inc',
         'source/libs/UtilitiesLib/src/utils/coh_fresh_source_profile_api.h':'source_group_profile_api.h',
         'source/Common/seq/coh_resource_quiescence.inc':'source_sealed_quiescence.inc'}
        for name,key in names.items():old['artifacts'][name]['sha256']=focused['compiled_source_fingerprint']['current'][key]
        if mutate:mutate(old)
        return encoded(old)
    @contextmanager
    def inputs(self, *, overrides=None, observer=None, raw_pin=None, build_pin=None):
        fake = self.observer() if observer is None else observer
        fixed = MODULE.fixed
        overrides = {} if overrides is None else overrides
        def selected(root,name,size,pin):
            if name == MODULE.OBSERVER_BUILD:return fake
            if name in overrides:return overrides[name]
            return fixed(root,name,size,pin)
        with ExitStack() as stack:
            stack.enter_context(patch.object(MODULE,'OBSERVER_BUILD_SHA',sha(fake)))
            stack.enter_context(patch.object(MODULE,'OBSERVER_BUILD_BYTES',len(fake)))
            stack.enter_context(patch.object(MODULE,'fixed',side_effect=selected))
            if raw_pin is not None:stack.enter_context(patch.object(MODULE,'INVENTORY_RAW_SHA',raw_pin))
            if build_pin is not None:stack.enter_context(patch.object(MODULE,'BUILD_SHA',build_pin))
            yield
    def canonical_build(self):return js(gzip.decompress(at(MODULE.OLD+'build.json.gz')))
    def composition(self, build=None):
        pins={};MODULE.qualified_sources(ROOT,self.canonical_build() if build is None else build,pins);return pins
    def gate(self, artifacts):
        old=js(at(MODULE.OLD_GATE))['current_278_pin_map']
        pins={k:v for k,v in old.items() if k!=MODULE.WORKFLOW}
        for name in (MODULE.EARLIER_PROFILE,MODULE.PREVIOUS_FOLLOWUP,MODULE.FOLLOWUP):
            pins.update(js(at(name))['source_sha256'])
        focused=js(at(MODULE.FOLLOWUP))
        pins.update({'upstream/ouroboros/'+k:v for k,v in focused['original_sha256_raw'].items()})
        pins.update(js(at(MODULE.INITIAL_OWNER_REVIEW))['source_inputs_sha256'])
        pins.update(js(at(MODULE.REVIEW+'review.json'))['current_project_consumer_dependencies']['sha256'])
        pins.update(artifacts)
        for name,pin in ((MODULE.EARLIER_PROFILE,MODULE.EARLIER_PROFILE_SHA),(MODULE.OWNER_REVIEW,MODULE.OWNER_REVIEW_SHA),
            (MODULE.PREVIOUS_FOLLOWUP,MODULE.PREVIOUS_FOLLOWUP_SHA),(MODULE.INITIAL_OWNER_REVIEW,MODULE.INITIAL_OWNER_REVIEW_SHA),
            (MODULE.INITIAL_OWNER_QUALIFICATION,MODULE.INITIAL_OWNER_QUALIFICATION_SHA)):
            pins[name]=pin
        pins[OWN]=sha(FROZEN);pins[MODULE.WORKFLOW]=sha(at(MODULE.WORKFLOW))
        gate={key:False for key in MODULE.GATE_KEYS}
        gate.update(schema='coh-inventory-initial-owner-fresh-groups-live-source-admission-v1',passed=True,
            source_preflight_only=True,source_revision='a'*40,source_sha256=pins,
            observer_compile_receipt_sha256=MODULE.OBSERVER_BUILD_SHA,
            receiver_build_receipt_sha256=MODULE.BUILD_SHA,source_profile_proof_sha256=MODULE.FOLLOWUP_SHA)
        return gate

    def test_frozen_core_and_pending_before_evidence_or_copy(self):
        old=at('native-android/combined-client/tools/admit_account_controls_initial_receiver.py')
        self.check(sha(old)==BASE_SHA and sha(FROZEN)==FROZEN_SHA,'exact-base-and-new-source-freeze')
        a,b=objects(old),objects(FROZEN)
        for name in CORE:self.check(a[name]==b[name],'unchanged-core-'+name)
        self.check(len(MODULE.GATE_KEYS)==14,'exact-new-fourteen-key-gate')
        self.check(MODULE.OBSERVER_BUILD_SHA=='PENDING_ACTUAL_MAP_RECEIPT' and MODULE.OBSERVER_BUILD_BYTES==0,
            'actual-new-map-stays-pending')
        with patch.object(MODULE,'fixed',side_effect=AssertionError('evidence read before pending refusal')):
            self.refused(lambda:MODULE.evidence(ROOT),'pending-before-first-evidence-read','EVIDENCE_NOT_FROZEN')
        with tempfile.TemporaryDirectory(prefix='inventory-pending-mocks-') as td:
            runner=Path(td).resolve();output=runner/'new-output';real_stat=Path.stat
            def stat_owned(path,*args,**kwargs):
                if path==runner:return types.SimpleNamespace(st_uid=1000,st_mode=0o700)
                return real_stat(path,*args,**kwargs)
            environment={'GITHUB_SHA':'a'*40,'GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted',
                'RUNNER_OS':'Linux','RUNNER_ARCH':'X64','GITHUB_REPOSITORY':'Russianranger/coh-android',
                'GITHUB_REF':'refs/heads/native-android','RUNNER_TEMP':str(runner)}
            with patch.dict(MODULE.os.environ,environment,clear=True),patch.object(MODULE.os,'geteuid',return_value=1000),\
                 patch.object(MODULE,'__file__',str(ROOT/OWN)),patch.object(Path,'stat',new=stat_owned),\
                 patch.object(MODULE,'write_new',side_effect=AssertionError('copy prohibited')):
                self.refused(lambda:MODULE.admit(ROOT,output),'pending-before-output-directory-and-copy','EVIDENCE_NOT_FROZEN')
            self.check(not output.exists(),'pending-leaves-no-output')

    def test_current_c50_three_supersessions_and_c79_history(self):
        c36=js(gzip.decompress(at(MODULE.ACCOUNT_PROOF)))['source_sha256']
        c50=js(gzip.decompress(at(MODULE.INVENTORY_PROOF)))['source_sha256']
        binding=js(at(MODULE.INVENTORY_BINDING));changed=binding['previous_changed_source_sha256']
        with self.inputs():pins=self.composition()
        self.check(len(c36)==36 and len(c50)==50 and len(c50)-len(c36)==14,'c50-net-plus-fourteen')
        self.check(len(set(c50)-set(c36))==16 and len(set(c36)-set(c50))==2,'exact-sixteen-added-two-absent')
        self.check(len(changed)==3 and all(c36[k]==v and c50[k]!=v and pins[k]==c50[k] for k,v in changed.items()),
            'exact-three-historical-c36-to-current-c50')
        self.check(sum(k not in changed for k in c36)==33 and all(pins[k]==v and sha(at(k))==v for k,v in c36.items() if k not in changed),
            'other-thirty-three-c36-stay-current-including-two-absent-from-c50')
        self.check(all(pins[k]==v and sha(at(k))==v for k,v in c50.items()),'all-fifty-current-source-bytes')
        c79=js(at(MODULE.C_REVIEW))['source_sha256']
        expected={'native-android/engine/dbclient/coh_db_session.c','native-android/engine/dbclient/coh_db_session.h',
            'native-android/engine/dbclient/check.py','native-android/engine/initial-capture/check_initial_editmsg.py',
            'native-android/engine/initial-capture/test_initial_peer.c'}
        self.check(len(c79)==79 and {k for k,v in c79.items() if pins[k]!=v}==expected,'c79-only-five-explicit-final-transitions')
        bad=copy.deepcopy(binding);bad['previous_changed_source_sha256']['native-android/engine/dbclient/coh_db_session.c']='0'*64
        with self.inputs(overrides={MODULE.INVENTORY_BINDING:encoded(bad)}):
            self.refused(self.composition,'wrong-c36-precursor-refuses','QUALIFIED_SCOPE')
        name='native-android/engine/auth/coh_auth.c'
        original_raw=gzip.decompress(at(MODULE.INVENTORY_PROOF))
        needle=('"'+name+'": "'+c50[name]+'"').encode()
        self.assertEqual(original_raw.count(needle),1)
        bad_raw=original_raw.replace(needle,('"'+name+'": "'+'0'*64+'"').encode())
        bad_binding=copy.deepcopy(binding);bad_binding['source_sha256'][name]='0'*64
        bad_review=js(at(MODULE.INVENTORY_REVIEW));bad_review['source_inputs_sha256'][name]='0'*64
        with self.inputs(overrides={MODULE.INVENTORY_PROOF:gzip.compress(bad_raw),
            MODULE.INVENTORY_BINDING:encoded(bad_binding),MODULE.INVENTORY_REVIEW:encoded(bad_review)},raw_pin=sha(bad_raw)):
            self.refused(self.composition,'coherent-fourth-c36-source-change-refuses','QUALIFIED_SCOPE')
        old=js(at(MODULE.C_REVIEW));old['source_sha256']['native-android/engine/dbclient/coh_db_session.h']='0'*64
        with self.inputs(overrides={MODULE.C_REVIEW:encoded(old)}):
            self.refused(self.composition,'wrong-c79-history-refuses','QUALIFIED_SCOPE')
        bad=copy.deepcopy(binding);bad['owner_implementation_changed']=True
        with self.inputs(overrides={MODULE.INVENTORY_BINDING:encoded(bad)}):
            self.refused(self.composition,'changed-secure-owner-refuses','QUALIFIED_SCOPE')

    def test_peer_checker_and_all_current46_values(self):
        review=js(at(MODULE.REVIEW+'review.json'));mapping=review['current_project_consumer_dependencies']['sha256']
        with self.inputs():pins=self.composition()
        self.check(len(mapping)==46 and all(pins[k]==v and sha(at(k))==v for k,v in mapping.items()),'exact-current-forty-six-values')
        self.check(sha(json.dumps(mapping,sort_keys=True,separators=(',',':')).encode())==MODULE.MAP_SHA,'current46-map-identity')
        self.check(pins['native-android/combined-client/tools/check_local_initial_capture.py']==
            '722199b76f206fcd1c2fcfe925d99f105a69ffba6215e94d5d3dba8b8cdace4b','exact-722-checker')
        peer=js(at(MODULE.PEER_PROOF))
        self.check(all(pins[k]==v for k,v in peer['source_sha256'].items()),'exact-six-peer-oracle-source-pins')
        bad=copy.deepcopy(peer);bad['all_old_bytes_equal_after_removing_new_guard_blocks']=False
        with self.inputs(overrides={MODULE.PEER_PROOF:encoded(bad)}):
            self.refused(self.composition,'unproved-peer-derivation-refuses','QUALIFIED_SCOPE')
        bad=copy.deepcopy(review);bad['current_project_consumer_dependencies']['previous_account_controls45_transition']['added']['native-android/engine/dbclient/coh_db_account_inventory.h']='0'*64
        with self.inputs(overrides={MODULE.REVIEW+'review.json':encoded(bad)}):
            self.refused(self.composition,'wrong-added-value-even-with-correct-key-refuses','QUALIFIED_SCOPE')
        bad=copy.deepcopy(review);bad['current_project_consumer_dependencies']['previous_account_controls45_transition']['changed']['native-android/combined-client/tools/check_local_initial_capture.py']['previous_sha256']='0'*64
        with self.inputs(overrides={MODULE.REVIEW+'review.json':encoded(bad)}):
            self.refused(self.composition,'wrong-checker-precursor-refuses','QUALIFIED_SCOPE')

    def test_current29_status_binding_and_compiled_map_mock(self):
        with self.inputs():binary,raw,mapping,pins=MODULE.evidence(ROOT)
        self.check(len(binary)==180688 and sha(binary)==MODULE.ELF_SHA,'canonical66f-read-only-binary')
        self.check(len(raw)==266672 and sha(raw)==MODULE.BUILD_SHA,'exact-canonical-immutable-receiver-receipt')
        build=js(raw)
        self.check(len(build['source_sha256'])==1860 and len(mapping)==46,'historical1860-is-not-current46')
        for mode in MODES:
            tests=build['modes'][mode]['tests'];name=MODULE.STATUS_ROOT+'status-'+mode+'/account-inventory-captured.json'
            self.check(tests['checks']==29 and tests['new_account_inventory_only'] is True and
                tests['old28_controls_reexecuted'] is tests['old123_controls_reexecuted'] is tests['old151_controls_reexecuted'] is False,
                'new29-only-'+mode)
            self.check(len(at(name))==507 and sha(at(name))==pins[name]==
                'ba705db4b44c0445f82b4c3998a84127d2fbfbf41be996a438fe23c46f0e3677','fixed507-status-'+mode)
        mutated=raw.replace(b'"checks": 29',b'"checks": 28',1)
        self.assertNotEqual(mutated,raw);self.assertEqual(len(mutated),266672)
        with self.inputs(overrides={MODULE.OLD+'build.json.gz':gzip.compress(mutated)},build_pin=sha(mutated)):
            self.refused(lambda:MODULE.evidence(ROOT),'old28-cannot-substitute-new29','QUALIFIED_SCOPE')
        bad=js(at(MODULE.INVENTORY_BINDING));bad['source_sha256']['native-android/engine/dbclient/coh_db_session.c']='0'*64
        with self.inputs(overrides={MODULE.INVENTORY_BINDING:encoded(bad)}):
            self.refused(self.composition,'c50-binding-current-map-mismatch-refuses','QUALIFIED_SCOPE')
        name=MODULE.STATUS_ROOT+'status-release/account-inventory-captured.json';original=MODULE.raw
        def changed_status(path,maximum=8*1024**2):
            value=original(path,maximum)
            return (bytes([value[0]^1])+value[1:]) if path==ROOT/name else value
        with self.inputs(),patch.object(MODULE,'raw',side_effect=changed_status):
            self.refused(lambda:MODULE.evidence(ROOT),'changed-status-bytes-refuse','FIXED_INPUT')
        fake=self.observer(lambda d:d['artifacts']['source/MapServer/src/group/coh_fresh_source_profile.inc'].__setitem__('sha256','0'*64))
        with self.inputs(observer=fake):
            self.refused(lambda:MODULE.evidence(ROOT),'old-map-member-cannot-admit-a13','OBSERVER_SOURCE')

    def test_a13_original15_gate_and_eight_exact_native_overrides(self):
        with self.inputs():
            _,_,mapping,artifacts=MODULE.evidence(ROOT);gate=self.gate(artifacts)
            original=js(at(MODULE.OLD_GATE))['current_278_pin_map'];base={k:v for k,v in original.items() if k!=MODULE.WORKFLOW}
            for name in (MODULE.EARLIER_PROFILE,MODULE.PREVIOUS_FOLLOWUP,MODULE.FOLLOWUP):base.update(js(at(name))['source_sha256'])
            focused=js(at(MODULE.FOLLOWUP));base.update({'upstream/ouroboros/'+k:v for k,v in focused['original_sha256_raw'].items()})
            base.update(js(at(MODULE.INITIAL_OWNER_REVIEW))['source_inputs_sha256'])
            changes={k for k,v in mapping.items() if base.get(k)!=v}
            self.check(len(changes)==8,'exact-eight-native-source-overrides')
            self.check(len(focused['source_sha256'])==13 and len(focused['original_sha256_raw'])==15 and
                len(focused['superseded_source_pins'])==6 and len(focused['added_source_paths'])==3,'a13-original15-six-three-composition')
            self.check(len(gate)==14 and gate['source_profile_proof_sha256']==MODULE.FOLLOWUP_SHA,'new-fourteen-key-a13-gate')
            calls=[]
            def committed(root,pins,revision):
                self.assertEqual((root,revision),(ROOT,'a'*40));calls.append(copy.deepcopy(pins))
            with tempfile.TemporaryDirectory(prefix='inventory-gate-mocks-') as td,patch.object(MODULE,'committed',side_effect=committed):
                runner=Path(td).resolve();path=runner/'fresh-groups-source-admission.json';path.write_bytes(encoded(gate))
                result=MODULE.admit_gate(ROOT,runner,'a'*40,OWN,artifacts)
                self.check(result[2]==gate['source_sha256'] and len(calls)==1,'composed-gate-admitted-before-project-imports')
                mutations=[('old-schema',lambda d:d.__setitem__('schema','coh-account-controls-fresh-groups-live-source-admission-v1')),
                    ('stale-build',lambda d:d.__setitem__('receiver_build_receipt_sha256','0'*64)),
                    ('old-a40-proof',lambda d:d.__setitem__('source_profile_proof_sha256',MODULE.PREVIOUS_FOLLOWUP_SHA)),
                    ('runtime-authority',lambda d:d.__setitem__('runtime_executed',True)),
                    ('extra-key',lambda d:d.__setitem__('unknown',False)),
                    ('missing-self',lambda d:d['source_sha256'].pop(OWN))]
                for name in sorted(changes):
                    mutations.append(('wrong-native-value-'+name,lambda d,n=name:d['source_sha256'].__setitem__(n,'0'*64)))
                one=next(iter(focused['original_sha256_raw']));name='upstream/ouroboros/'+one
                mutations.append(('missing-original15-member',lambda d,n=name:d['source_sha256'].pop(n)))
                for label,mutate in mutations:
                    candidate=copy.deepcopy(gate);mutate(candidate);path.write_bytes(encoded(candidate));calls.clear()
                    self.refused(lambda:MODULE.admit_gate(ROOT,runner,'a'*40,OWN,artifacts),label,'SOURCE_GATE')
                    self.assertEqual(calls,[])
                path.write_bytes(encoded(gate))
                bad=copy.deepcopy(focused);key=next(iter(bad['superseded_source_pins']));bad['superseded_source_pins'][key]['previous_sha256']='0'*64
                with self.inputs(overrides={MODULE.FOLLOWUP:encoded(bad)}):
                    self.refused(lambda:MODULE.admit_gate(ROOT,runner,'a'*40,OWN,artifacts),'a13-conflicting-six-supersessions-refuse','SOURCE_GATE')
                bad=js(at(MODULE.INITIAL_OWNER_QUALIFICATION));key=next(iter(bad['original_sha256_raw']));bad['original_sha256_raw'][key]='0'*64
                with self.inputs(overrides={MODULE.INITIAL_OWNER_QUALIFICATION:encoded(bad)}):
                    self.refused(lambda:MODULE.admit_gate(ROOT,runner,'a'*40,OWN,artifacts),'a13-original15-binding-conflict-refuses','SOURCE_GATE')


def main():
    global ROOT,MODULE,FROZEN,HELPER
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True);parser.add_argument('--helper',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    ROOT=args.source_root.resolve(strict=True);HELPER=args.helper.resolve(strict=True);FROZEN=HELPER.read_bytes()
    if sha(FROZEN)!=FROZEN_SHA:raise ValueError('exact frozen helper required')
    if args.output.exists():raise ValueError('fresh output required')
    test_source=Path(__file__).read_bytes();sys.dont_write_bytecode=True
    spec=importlib.util.spec_from_file_location('inventory_initial_receiver_mocks',HELPER)
    MODULE=importlib.util.module_from_spec(spec);spec.loader.exec_module(MODULE)
    args.output.mkdir(mode=0o700);stream=io.StringIO()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    stderr=stream.getvalue().encode();stdout=(json.dumps({'passed':result.wasSuccessful(),'methods':result.testsRun,'cases':len(CASES)},sort_keys=True)+'\n').encode()
    (args.output/'stderr.txt').write_bytes(stderr);(args.output/'stdout.json').write_bytes(stdout)
    unchanged=HELPER.read_bytes()==FROZEN and Path(__file__).read_bytes()==test_source
    record={'schema':'coh-inventory-initial-owner-receiver-focused-mocks-v1','passed':result.wasSuccessful() and unchanged,
      'helper_sha256':sha(FROZEN),'test_sha256':sha(test_source),'base_helper_sha256':BASE_SHA,
      'methods':result.testsRun,'cases':len(CASES),'case_names':CASES,'errors':len(result.errors),'failures':len(result.failures),
      'skipped':len(result.skipped),'source_inputs_unchanged':unchanged,'fixed_read_inputs_sha256':READS,
      'stdout':{'file':'stdout.json','bytes':len(stdout),'sha256':sha(stdout)},
      'stderr':{'file':'stderr.txt','bytes':len(stderr),'sha256':sha(stderr)},
      'new_inventory_a13_metadata_controls_only':True,'old49_or54_mock_suites_reexecuted':False,
      'retained_elf_read_for_hash_only':True,'observer_receipt_is_explicit_mock':True,
      'actual_new_map_receipt_admitted':False,'actual_destination_preflight_executed':False,
      'project_imports_compiler_loader_native_registry_services_or_network_executed':False,
      'source_generation_admitted':False,'actor_publication':False,'world_authority':False}
    (args.output/'proof.json').write_bytes(encoded(record));sys.stdout.buffer.write(stdout);sys.stderr.buffer.write(stderr)
    return 0 if record['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
