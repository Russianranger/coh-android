"""Stock station requests prepare real map 5; exact arrival/save guards persist."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'android/guest'))
import character_zoning as zoning
import character_reopen_diagnostic as reopen
import test_character_zoning as old

class StationTests(unittest.TestCase):
    def instance(self):
        value=old.ZoningServerTests.instance(self)
        value.monorail_qualified=True;value.native_station_seen={}
        value.runtime=value.owner.args.state
        value.map_native_events=Mock(return_value=[])
        return value
    def native(self,kind='station_request',sequence=1,**kw):
        v=dict(kind=kind,sequence=sequence,request=1,target=5,pid=55,tid=56,session_id=old.SESSION,
            map_id=1,db_id=1,auth_id=17,utc_ms=old.NOW,line_sha256=str(sequence)*64)
        v.update(kw);return v
    def test_kings_world_and_logger_routes_cannot_be_atlas_alias(self):
        text='5 maps/City_Zones/City_01_02/City_01_02.txt S: 1 / 2 Ip: 127.0.0.1:7003 Mem: 100\n'
        self.assertTrue(zoning.ready(zoning.parse_map_status(text,5),5))
        for bad in (text.replace('City_01_02','City_01_01'),text.replace(':7003',':7001')):
            with self.assertRaises(old.ERROR):zoning.parse_map_status(bad,5)
        ready=old.resume(1).replace('City_01_01_1','City_01_02_1')
        self.assertIsNotNone(zoning.stock_ready(old.logs(ready),5,old.NOW,old.NOW))
        self.assertIsNone(zoning.stock_ready(old.logs(ready),1,old.NOW,old.NOW))
    def test_native_choice_starts_preparation_with_verified_android_event_and_no_input(self):
        v=self.instance();native=self.native();v.map_native_events.return_value=[native]
        v._observe_station(old.NOW)
        self.assertEqual(v.pending['to_map_id'],5);self.assertEqual(v.epoch,1)
        e=v.zoning_report['events'][-1]
        self.assertTrue(e['native_station_request_verified']);self.assertEqual(e['travel_method'],'stock_monorail')
        self.assertEqual(e['native_request_sequence'],1);self.assertEqual(e['native_station_pid'],55)
        v._query_start.assert_called_once_with(['-getstatus','1','5'],'baseline')
        v._observe_station(old.NOW+100)
        self.assertEqual(v.epoch,1)
    def test_ready_authorization_is_exact_and_departure_bound_to_native_selection(self):
        v=self.instance();req=self.native();v.map_native_events.return_value=[req];v._observe_station(old.NOW)
        v.pending.update(phase='ready',ready_utc_ms=old.NOW,departure_deadline_utc_ms=old.NOW+10000)
        v._authorize_station(req)
        self.assertTrue(v.pending['native_authorization_issued'])
        self.assertEqual((v.runtime/'monorail-1-reply.txt').read_text(),zoning.monorail_events.reply(req))
        departure=self.native('station_departure',2,utc_ms=old.NOW+50)
        v.map_native_events.return_value=[req,departure];v._observe_station(old.NOW+100)
        self.assertEqual(v.pending['phase'],'arrival');self.assertTrue(v.pending['transfer_requested'])
        self.assertTrue(v.zoning_report['events'][-1]['native_station_departure_verified'])
        self.assertEqual(v.zoning_report['events'][-1]['sent_utc_ms'],old.NOW+50)
    def test_save_before_authorization_cancels_without_publishing(self):
        v=self.instance();v.pending={'phase':'ready'}
        (v.owner.args.state/'character-logout.json').write_text('{}')
        with self.assertRaises(old.ERROR):v._authorize_station(self.native())
        self.assertFalse((v.runtime/'monorail-1-reply.txt').exists())
    def test_authorization_failure_is_uncertain_and_cannot_continue_gameplay(self):
        v=self.instance();v.pending=dict(to_map_id=5,phase='ready',deadline=0,native_authorization_issued=True)
        with patch.object(zoning.time,'time',return_value=old.NOW/1000),self.assertRaises(old.ERROR):v.tick_zoning()
        self.assertTrue(v.zoning_report['failure']['transfer_requested'])
    def test_immediate_arrival_wait_avoids_translated_helpers_then_checks_endpoint_and_identity(self):
        v=self.instance();v.epoch=1
        v.pending=dict(to_map_id=5,phase='arrival',delivery=old.request('mapmove',to_map_id=5),next_query=0,
            transfer_requested=True,native_station_request_verified=True)
        v._activate=Mock(side_effect=lambda map_id:setattr(v,'active_map_id',map_id))
        v._observe_arrival(None,old.NOW+100)
        v._query_start.assert_not_called()
        ready=dict(kind='ready',utc_ms=old.NOW+200,line_sha256='f'*64,map_id=5)
        v.map_native_events.return_value=[ready]
        v._observe_arrival(None,old.NOW+250)
        v._query_start.assert_called_once_with(['-getstatus','1','5'],'arrival_map')
        maptext='5 maps/City_Zones/City_01_02/City_01_02.txt S: 1 / 2 Ip: 127.0.0.1:7003 Mem: 100\n'
        v._observe_arrival(('arrival_map',maptext),old.NOW+300)
        v._query_start.assert_called_with(['-getstatus','3','1'],'arrival_final_character')
        char='1 Name THORHERO Auth COHLOCAL Ip 127.0.0.1 MapId 5 SmapId 5\n'
        v._observe_arrival(('arrival_final_character',char),old.NOW+400)
        self.assertEqual(v.active_map_id,5);self.assertTrue(v.creation_report['monorail_enabled'])
        self.assertEqual(v.zoning_report['transfers'][0]['native_timestamp_precision_ms'],1)
        self.assertEqual(v.zoning_report['transfers'][0]['native_ready_after_send_lower_bound_ms'],200)
        v.current_logs.assert_not_called()
    def test_saved_kings_map_needs_opt_in_before_readonly_activation(self):
        row=dict(containerid=1,mapid=None,staticmapid=5,posx=12,posy=-20,posz=40)
        v=self.instance();v.sql_rows=Mock(return_value=[row]);v.monorail_qualified=False
        with self.assertRaises(old.ERROR):v.character_position(allow_unassigned_active_map=True)
        v.monorail_qualified=True
        self.assertEqual(v.character_position(allow_unassigned_active_map=True),row)
        self.assertEqual(v.active_map_id,5)


class MonorailEventAdapterTests(unittest.TestCase):
    def test_actual_reopen_event_adapters_carry_kings_row_opt_in_to_android(self):
        diagnostic=object.__new__(reopen.ZoningCharacterReopenDiagnostic)
        for map_id in (1,5,101):
            with self.subTest(map_id=map_id):
                proof={'map_id':map_id,'baseline_character_id':1,'monorail_enabled':True,
                       'recovery_requested':False,'recovery_verified':False}
                connected=diagnostic.connected_event_data(proof)
                saved=diagnostic.saved_event_data(proof)
                for event in (connected,saved):
                    self.assertIs(event['monorail_enabled'],True)
                    self.assertIs(event['zoning_enabled'],True)
                    self.assertIs(event['connected_on_supported_map'],True)
                self.assertEqual(saved['map_id'],map_id)
                self.assertEqual(connected['baseline_character_id'],1)

    def test_legacy_event_adapters_do_not_invent_monorail_qualification(self):
        diagnostic=object.__new__(reopen.ZoningCharacterReopenDiagnostic)
        for opt_in in (None,False,1,'true'):
            with self.subTest(opt_in=opt_in):
                proof={'map_id':1,'baseline_character_id':1,'monorail_enabled':opt_in,
                       'recovery_requested':False,'recovery_verified':False}
                self.assertIs(diagnostic.connected_event_data(proof)['monorail_enabled'],False)
                self.assertIs(diagnostic.saved_event_data(proof)['monorail_enabled'],False)

if __name__=='__main__':unittest.main()
