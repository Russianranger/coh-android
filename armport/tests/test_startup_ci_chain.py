"""A failed, duplicate or moved-head run must never advance the signed chain."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('startup_ci_chain', ROOT / 'armport/scripts/startup_ci_chain.py')
chain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chain)
SHA = 'a' * 40
BUILD, RUNTIME, APK = 'armport-build.yml', 'armport-app-runtime.yml', 'armport-thor-apk.yml'
ARTIFACTS = {BUILD: ['armport-server-metrics-native', 'armport-client-Release'],
             RUNTIME: ['armport-app-client-package', 'armport-app-server-metrics'],
             APK: ['coh-atlas-gameplay-0.13.52-apk']}


class FakeGithub:
    def __init__(self):
        self.head, self.calls, self.created = SHA, [], {}
        self.failure, self.duplicate, self.missing, self.delayed = None, False, False, False
        self.empty_discovery = set()

    def run(self, workflow):
        return {'id': self.created[workflow], 'head_sha': SHA, 'head_branch': chain.BRANCH,
                'event': 'workflow_dispatch', 'status': 'completed',
                'conclusion': 'failure' if self.failure == workflow else 'success'}

    def api(self, endpoint, payload=None):
        self.calls.append((endpoint, payload))
        if endpoint.startswith('git/ref/'):
            return {'object': {'sha': self.head}}
        if endpoint.startswith('actions/workflows/'):
            workflow = endpoint.split('/')[2]
            if payload is not None:
                assert payload['ref'] == chain.BRANCH
                assert workflow not in self.created
                if workflow == RUNTIME:
                    assert payload['inputs'] == {'client_run_id': '1', 'data_run_id': '1', 'server_run_id': '1'}
                if workflow == APK:
                    assert payload['inputs'] == {'m4_run_id': '2', 'server_metrics': True}
                self.created[workflow] = len(self.created) + 1
                return None
            if workflow not in self.created:
                runs = []
            elif self.delayed and workflow not in self.empty_discovery:
                self.empty_discovery.add(workflow)
                runs = []
            else:
                runs = [self.run(workflow)] * (2 if self.duplicate else 1)
            return {'total_count': len(runs), 'workflow_runs': runs}
        identifier = int(endpoint.split('/')[2])
        workflow = next(k for k, v in self.created.items() if v == identifier)
        if '/artifacts?' in endpoint:
            names = [] if self.missing else ARTIFACTS[workflow]
            return {'total_count': len(names), 'artifacts': [{'name': n, 'expired': False} for n in names]}
        return self.run(workflow)


class ChainTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict('os.environ', {'GITHUB_STEP_SUMMARY': ''}))
        self.enterContext(patch('builtins.print'))
        self.github = FakeGithub()
        self.chain = chain.Chain(SHA, api=self.github.api, sleep=lambda _: None)

    def test_exact_serial_inputs_and_all_artifacts(self):
        self.github.delayed = True
        self.assertEqual(self.chain.execute(), (1, 2, 3))
        posted = [c for c in self.github.calls if c[1] is not None]
        self.assertEqual([x[0].split('/')[2] for x in posted], [BUILD, RUNTIME, APK])
        self.assertEqual(posted[0][1]['inputs'], {'build_server_metrics': True})

    def test_moved_head_does_not_dispatch(self):
        self.github.head = 'b' * 40
        with self.assertRaisesRegex(RuntimeError, 'branch moved'):
            self.chain.execute()
        self.assertEqual(self.github.created, {})

    def test_failed_build_cannot_dispatch_runtime_or_apk(self):
        self.github.failure = BUILD
        with self.assertRaisesRegex(RuntimeError, 'Stage failed'):
            self.chain.execute()
        self.assertEqual(list(self.github.created), [BUILD])

    def test_missing_native_artifact_cannot_advance(self):
        self.github.missing = True
        with self.assertRaisesRegex(RuntimeError, 'artifacts absent'):
            self.chain.execute()
        self.assertEqual(list(self.github.created), [BUILD])

    def test_existing_stage_is_reused_and_never_redispatched(self):
        self.github.created[BUILD] = 1
        self.chain.stage(BUILD, {'build_server_metrics': True}, ARTIFACTS[BUILD])
        self.assertFalse(any(payload is not None for _, payload in self.github.calls))

    def test_duplicate_runs_fail_without_another_dispatch(self):
        self.github.created[BUILD], self.github.duplicate = 1, True
        with self.assertRaisesRegex(RuntimeError, 'Duplicate'):
            self.chain.execute()
        self.assertFalse(any(payload is not None for _, payload in self.github.calls))


if __name__ == '__main__':
    unittest.main()
