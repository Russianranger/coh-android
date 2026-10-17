from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest
import version_observation_contract as c

ROOT=Path(__file__).resolve().parents[4]
GEN='a'*64


def encode(body,offset):
    output=bytearray((offset+len(body)*8+7)//8)
    for index,byte in enumerate(body):
        for bit in range(8):
            if byte&(1<<bit):position=offset+index*8+bit;output[position//8]|=1<<(position%8)
    return bytes(output)


class VersionTests(unittest.TestCase):
    def decode(self,body,offset=0,**changes):
        args=dict(start_bit=offset,bit_count=len(body)*8,command=10,has_debug_info=False,owner_generation=GEN)
        args.update(changes);return c.decode_body(encode(body,offset),**args)

    def test_exact_source_audit(self):
        proof=c.source_audit(ROOT)
        self.assertEqual(proof['request_command'],10);self.assertEqual(proof['server_monitor_port'],6996)
        self.assertEqual(len(proof['source_sha256']),6)
        self.assertFalse(proof['original_functions_executed']);self.assertFalse(proof['actual_process_version_verified'])

    def test_all_offsets_and_bounded_lengths_metadata_only(self):
        for offset in range(8):
            for size in range(1,100):
                value=self.decode(b'v'*size+b'\0server-version\0',offset)
                self.assertEqual(value.compatible_version,'v'*size)
                self.assertEqual(value.server_patch_version,'server-version')
                self.assertFalse(value.actual_process_version_verified)
                self.assertFalse(value.live_deployment_admitted)
                with self.assertRaises(FrozenInstanceError):value.actual_process_version_verified=True

    def test_truncation_extra_mode_and_bounds_refused(self):
        body=b'normal-version\0normal-server\0'
        for offset in range(8):
            for cut in range(len(body)):
                with self.assertRaises(ValueError):self.decode(body[:cut],offset)
        for body in (b'\0x\0',b'x\0\0',b'x\0y\0z',b'x\0y\xff\0',b'x'*100+b'\0y\0'):
            with self.assertRaises(ValueError):self.decode(body)
        for changes in (dict(command=12),dict(command=True),dict(has_debug_info=True),dict(has_debug_info=0),
                        dict(start_bit=8),dict(bit_count=17),dict(owner_generation='unowned')):
            with self.assertRaises(ValueError):self.decode(b'game\0server\0',**changes)

    def test_only_version_request_metadata(self):
        args=dict(owner_generation=GEN,peer_ip='127.0.0.1',port=6996)
        result=c.declare_request(**args)
        self.assertFalse(result.sends_monitor_connect);self.assertEqual(result.application_body_bits,0)
        self.assertFalse(result.transport_qualified);self.assertFalse(result.live_channel_ownership_verified)
        for changes in (dict(command=12),dict(command=2),dict(port=7002),dict(peer_ip='0.0.0.0'),dict(peer_ip=2130706433),dict(peer_ip='::1')):
            with self.assertRaises(ValueError):c.declare_request(**(args|changes))

if __name__=='__main__':unittest.main()
