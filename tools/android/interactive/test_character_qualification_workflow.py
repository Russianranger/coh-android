"""Exercise immutable donor checks from the actual qualification workflow."""
import copy
from pathlib import Path
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT/'.github/workflows/android-character-qualification.yml'


class ImmutableQualificationDonorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = WORKFLOW.read_text()
        begin = text.index('          # BEGIN DONOR_VALIDATION\n')
        end = text.index('          # END DONOR_VALIDATION\n', begin)
        namespace = {}
        exec(compile(textwrap.dedent(text[begin:end]), str(WORKFLOW), 'exec'), namespace)
        cls.donor = namespace['DONOR']
        cls.validate = staticmethod(namespace['validate_donor'])

    def setUp(self):
        self.repository = 'Russianranger/coh-android'
        repo = {'id': 1368730125, 'full_name': self.repository}
        self.run = {'id': self.donor['run_id'], 'status': 'completed', 'conclusion': 'failure',
                    'repository': dict(repo), 'head_repository': dict(repo),
                    'head_sha': self.donor['repository_commit'], 'path': self.donor['workflow_path']}
        self.jobs = {'jobs': [{'name': 'apk', 'run_id': self.donor['run_id'],
                              'status': 'completed', 'conclusion': 'success'}]}
        self.artifact = {'id': self.donor['artifact_id'], 'name': self.donor['artifact_name'],
                         'expired': False, 'size_in_bytes': self.donor['artifact_bytes'],
                         'digest': self.donor['artifact_digest'],
                         'workflow_run': {'id': self.donor['run_id'],
                                          'head_sha': self.donor['repository_commit'],
                                          'repository_id': repo['id'], 'head_repository_id': repo['id']}}

    def test_successful_apk_remains_reusable_after_external_runtime_failure(self):
        self.validate(self.repository, self.run, self.jobs, self.artifact)

    def test_foreign_repository_source_workflow_or_unfinished_run_rejected(self):
        cases = [('id', 1), ('head_sha', '0'*40), ('path', '.github/workflows/resume-client.yml'),
                 ('status', 'in_progress'), ('repository', {'id': 9, 'full_name': 'other/repo'}),
                 ('head_repository', {'id': 9, 'full_name': 'other/repo'})]
        for key, value in cases:
            with self.subTest(key=key):
                run = copy.deepcopy(self.run)
                run[key] = value
                with self.assertRaises(ValueError):
                    self.validate(self.repository, run, self.jobs, self.artifact)

    def test_failed_pending_missing_duplicate_or_foreign_apk_job_rejected(self):
        cases = [{'jobs': []}, {'jobs': self.jobs['jobs']*2}]
        for key, value in [('conclusion', 'failure'), ('status', 'in_progress'), ('run_id', 1)]:
            jobs = copy.deepcopy(self.jobs)
            jobs['jobs'][0][key] = value
            cases.append(jobs)
        for jobs in cases:
            with self.subTest(jobs=jobs), self.assertRaises(ValueError):
                self.validate(self.repository, self.run, jobs, self.artifact)

    def test_artifact_identity_digest_size_expiry_or_source_mismatch_rejected(self):
        cases = [('id', 1), ('name', 'another-apk'), ('expired', True), ('size_in_bytes', 1),
                 ('digest', 'sha256:'+'0'*64)]
        for key, value in cases:
            with self.subTest(key=key):
                artifact = copy.deepcopy(self.artifact)
                artifact[key] = value
                with self.assertRaises(ValueError):
                    self.validate(self.repository, self.run, self.jobs, artifact)
        for key, value in [('id', 1), ('head_sha', '0'*40), ('repository_id', 1), ('head_repository_id', 1)]:
            with self.subTest(workflow_key=key):
                artifact = copy.deepcopy(self.artifact)
                artifact['workflow_run'][key] = value
                with self.assertRaises(ValueError):
                    self.validate(self.repository, self.run, self.jobs, artifact)


if __name__ == '__main__':
    unittest.main()
