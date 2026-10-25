"""Explicit Finish keeps host bounds and authenticated request identity."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import interactive_host as host

class SessionContract(unittest.TestCase):
    def setUp(self):
        self.session='a'*32
        value=dict(format=1,session_id=self.session,client_pid=640,action='finish_interaction')
        payload=(json.dumps(value,sort_keys=True)+'\n').encode()
        self.finish=dict(value,bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
        self.report=dict(client_launch={'pid':640},manual_session=True,
            interaction_end_policy='explicit_finish_or_abort',minimum_observation_seconds=0,
            interaction_timeout_seconds=0,observation_seconds=399.587,startup_elapsed_seconds=117.521,
            interaction_session_completed=True,input_effect_verified=False,
            interaction_completion_reason='finish_requested',
            interaction_finish_request={k:v for k,v in self.finish.items() if k!='format'})
    def check(self,r=None,f=None):
        host.character.validate_session_bounds(r or self.report,self.session,f or self.finish)
    def test_explicit_and_original_contracts(self):
        old=copy.deepcopy(self.report);self.check();self.assertEqual(self.report,old)
        with self.assertRaises(Exception):host.character.validate_session_bounds(self.report,self.session)
        old.update(manual_session=False,interaction_timeout_seconds=1200)
        host.character.validate_session_bounds(old,self.session)
        with self.assertRaises(Exception):self.check(old)
    def test_bounds_and_policy_rejections(self):
        for key,values in {'observation_seconds':[29,1211,float('nan'),float('inf'),True],
            'startup_elapsed_seconds':[-1,901,float('nan'),True],
            'interaction_timeout_seconds':[1200,False], 'minimum_observation_seconds':[1,False],
            'manual_session':[False], 'interaction_end_policy':['timeout'],
            'interaction_completion_reason':['interaction_timeout'],
            'interaction_session_completed':[False],'input_effect_verified':[True]}.items():
            for value in values:
                with self.subTest(key=key,value=value):
                    r=copy.deepcopy(self.report);r[key]=value
                    with self.assertRaises(Exception):self.check(r)
    def test_finish_tampering_rejected_on_both_sides(self):
        for key,value in [('session_id','b'*32),('client_pid',641),('action','abort'),('bytes',1),('sha256','0'*64)]:
            for side in ('host','guest'):
                r=copy.deepcopy(self.report);f=dict(self.finish)
                (f if side=='host' else r['interaction_finish_request'])[key]=value
                with self.subTest(key=key,side=side):
                    with self.assertRaises(Exception):self.check(r,f)
        r=copy.deepcopy(self.report);r.pop('interaction_finish_request')
        with self.assertRaises(Exception):self.check(r)
if __name__=='__main__':unittest.main()
