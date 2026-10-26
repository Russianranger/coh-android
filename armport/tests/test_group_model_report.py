import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import group_model_report
import zone_report


def record(kind=2,sample=1,tid=36):
    text=f'outcome={kind} sample={sample} name="Model_name" geo="'+('object_library/test.geo' if kind else '')+f'" model={int(kind==2)} loadstate={4 if kind==2 else 0} verts={24 if kind==2 else 0} tris={12 if kind==2 else 0}'
    return json.dumps(dict(stage='group.model',text=text,tid=tid))+'\n'


class LookupReport(unittest.TestCase):
    def test_three_outcomes_with_reordered_atomic_reservations(self):
        data=[record(k,i) for k in range(3) for i in [2,1]]
        result=group_model_report.summarize(data)
        self.assertTrue(result['observations_valid']);self.assertEqual(result['sample_count'],6)
        self.assertEqual(result['sampled_outcome_counts'],dict(library_entry_missing=2,model_lookup_missing=2,model_found=2))
        self.assertFalse(result['complete_model_census']);self.assertFalse(result['cause_established']);self.assertFalse(result['rendering_acceptance_changed'])
        self.assertEqual([s['sample'] for s in result['samples']],[2,1,2,1,2,1])

    def test_independent_budgets_and_sparse_outcomes(self):
        self.assertTrue(group_model_report.summarize([record(2)])['observations_valid'])
        data=[record(k,i) for k in range(3) for i in range(1,17)]
        result=group_model_report.summarize(data);self.assertTrue(result['observations_valid'])
        self.assertEqual(len(result['saturated_outcomes']),3)
        self.assertFalse(group_model_report.summarize(data+[record(2,17)])['observations_valid'])

    def test_invalid_records_never_qualify_observation(self):
        cases=[[],[record(2,2)],[record(),record()],[record()[:-1]],['[]\n'],['broken\n'],[record(tid=True)],[record().replace('sample=1','sample=0')],[record().replace('loadstate=4','loadstate=4294967296')],[record(0).replace('verts=0','verts=1')],[record(1).replace('model=0','model=1')],[record().replace('tris=12','tris=-2147483649')]]
        for case in cases:self.assertFalse(group_model_report.summarize(case)['observations_valid'],case)

    def test_report_caller_retains_complete_isolated_lookup_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'zone-trace.jsonl').write_text(record(0)+record(1)+record(2))
            sections=dict(zone_report.sections(root,root))
            self.assertTrue(json.loads(sections['ArmPort M3 model traversal'])['lookup_observations']['observations_valid'])
            saved=json.loads((root/'group-model-summary.json').read_text())
            self.assertEqual(saved['sample_count'],3);self.assertEqual(saved['samples'][1]['geo'],'object_library/test.geo')
