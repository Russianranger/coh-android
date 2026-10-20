"""Replay the exact Android13 missing-policy return failure; no APK changes."""
import copy
import unittest
from unittest.mock import patch
from emulator_check import absent_policy_report_contract, returned_local_report_contract, map_report_contract

# Exact four-field projection present in all three attempt2 captures from
# run39370468578. Native report SHA25693e477592854885ae9f7f370ba949f68b5effd9725f069b374a7a6e56b754dcb.
POLICY = dict(phase='POLICY_UNAVAILABLE', live_world_rendered=False,
              authserver_authenticated=False, world_authority=False)


def reports():
    before=dict(session_id='123abc', connection_mode='LOCAL', server_protocol=copy.deepcopy(POLICY))
    returned=copy.deepcopy(before)
    service=dict(server=dict(phase='stopped',ready=False,owned_process_alive=False))
    return before,returned,service


class AbsentPolicyDriver(unittest.TestCase):
    def test_actual_minimal_projection_and_return_publish_no_invented_socket_counts(self):
        absent_policy_report_contract(POLICY)
        before,returned,service=reports()
        proof=returned_local_report_contract(before,returned,service)
        self.assertEqual(proof['native_network_phase'],'POLICY_UNAVAILABLE')
        self.assertIsNone(proof['opened_sockets']);self.assertIsNone(proof['closed_sockets'])
        self.assertIs(proof['native_owner_report_published'],False)
        self.assertEqual(returned['server_protocol'],POLICY)

    def test_full_native_validator_keeps_rejecting_minimal_projection(self):
        with self.assertRaises(AssertionError):map_report_contract(POLICY)

    def test_exact_projection_refuses_extra_missing_private_and_nonboolean_data(self):
        for key in POLICY:
            value=copy.deepcopy(POLICY);del value[key]
            with self.subTest(missing=key),self.assertRaises(AssertionError):absent_policy_report_contract(value)
        for key,bad in [('schema','coh-native-local-numeric-v1'),('opened_sockets',0),
                        ('password','private'),('world_authority',True),('world_authority',0),
                        ('live_world_rendered',None),('authserver_authenticated','false'),('phase','SUSPENDED')]:
            value=copy.deepcopy(POLICY);value[key]=bad
            with self.subTest(key=key,bad=bad),self.assertRaises(AssertionError):absent_policy_report_contract(value)
        for value in (None,[],0,'POLICY_UNAVAILABLE'):
            with self.assertRaises(AssertionError):absent_policy_report_contract(value)

    def test_absent_path_requires_matching_local_attempt_and_stopped_server(self):
        for change in ('before_full','before_mode','returned_mode','session','guest_alive','ready','phase'):
            before,returned,service=reports()
            if change=='before_full':before['server_protocol']['schema']='coh-native-local-numeric-v1'
            if change=='before_mode':before['connection_mode']='WORLD_HANDOFF'
            if change=='returned_mode':returned['connection_mode']='WORLD_HANDOFF'
            if change=='session':returned['session_id']='another'
            if change=='guest_alive':service['server']['owned_process_alive']=True
            if change=='ready':service['server']['ready']=True
            if change=='phase':service['server']['phase']='running'
            with self.subTest(change=change),self.assertRaises(AssertionError):returned_local_report_contract(before,returned,service)

    def test_full_owner_reports_cannot_bypass_full_schema_validation(self):
        before,returned,service=reports()
        returned['server_protocol']=dict(schema='coh-native-local-numeric-v1',phase='SUSPENDED',opened_sockets=2,closed_sockets=2)
        with self.assertRaises(AssertionError):returned_local_report_contract(before,returned,service)
        # Explicit collaborator isolates dispatch: actual full validation remains
        # covered by the unchanged production validator and driver_controls.
        with patch('emulator_check.map_report_contract') as validator:
            proof=returned_local_report_contract(before,returned,service)
            validator.assert_called_once_with(returned['server_protocol'])
            self.assertIs(proof['native_owner_report_published'],True)
            self.assertEqual(proof['opened_sockets'],2)
        returned['server_protocol']['closed_sockets']=1
        with patch('emulator_check.map_report_contract'),self.assertRaises(AssertionError):
            returned_local_report_contract(before,returned,service)


if __name__=='__main__':unittest.main()
