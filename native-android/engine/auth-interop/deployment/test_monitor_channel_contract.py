from dataclasses import replace,FrozenInstanceError
import unittest
import monitor_channel_contract as c


class ChannelTests(unittest.TestCase):
    def inputs(self):
        before=c.ProcessMetadata('a'*64,42,'b'*64,'c'*64,100,True)
        after=replace(before,observed_ms=200)
        channel=c.ChannelMetadata('a'*64,42,'b'*64,'127.0.0.1',6996,'127.0.0.1',6996,'127.0.0.1',49152,'TCP')
        events=tuple(c.HandshakeMetadata('a'*64,direction,command,110+i*10) for i,(direction,command) in enumerate((('outbound',1),('inbound',2),('outbound',3),('inbound',4))))
        return before,after,channel,events
    def match(self,inputs=None,**kwargs):
        options=dict(requested_network_version=5,negotiated_network_version=5,required_encryption=True,server_ack_encryption=True);options.update(kwargs)
        return c.match_metadata(*(inputs or self.inputs()),**options)
    def test_labels_never_make_permit(self):
        result=self.match();self.assertTrue(result.handshake_sequence_matches)
        for field in ('actual_process_ownership_verified','actual_socket_ownership_verified','actual_netlink_handshake_verified','live_request_permit','sends_monitor_connect'):self.assertFalse(getattr(result,field))
        with self.assertRaises(FrozenInstanceError):result.live_request_permit=True
    def test_process_lifetime_and_channel_mismatches(self):
        before,after,channel,events=self.inputs()
        for changes in (dict(pid=43),dict(pid=True),dict(start_identity_sha256='d'*64),dict(binary_sha256='d'*64),dict(owner_generation='d'*64),dict(alive=False),dict(observed_ms=139),dict(observed_ms=20000)):
            with self.assertRaises(ValueError):self.match((before,replace(after,**changes),channel,events))
        for changes in (dict(owner_pid=43),dict(owner_start_identity_sha256='d'*64),dict(transport='UDP'),dict(listener_ip='0.0.0.0'),dict(local_ip='127.0.0.2'),dict(peer_ip='192.168.1.1'),dict(peer_port=0),dict(local_port=7002)):
            with self.assertRaises(ValueError):self.match((before,after,replace(channel,**changes),events))
    def test_control_sequence_downgrade_and_no_implicit_ready(self):
        before,after,channel,events=self.inputs()
        for altered in (events[:3],events[::-1],events+(events[-1],),events[:2]+(replace(events[2],owner_generation='d'*64),)+events[3:],events[:1]+(replace(events[1],observed_ms=109),)+events[2:]):
            with self.assertRaises(ValueError):self.match((before,after,channel,altered))
        for changes in (dict(negotiated_network_version=4),dict(requested_network_version=0),dict(server_ack_encryption=False),dict(required_encryption=0)):
            with self.assertRaises(ValueError):self.match(**changes)
        self.assertFalse(self.match(required_encryption=False,server_ack_encryption=False).live_request_permit)

if __name__=='__main__':unittest.main()
