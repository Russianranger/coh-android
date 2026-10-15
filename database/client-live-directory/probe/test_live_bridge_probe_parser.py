import struct
import unittest
import parse_live_bridge_probe as probe


def row(name='fixture.fx',next_offset=0):
    encoded=name.encode('utf-16le')
    data=bytearray(94+len(encoded))
    struct.pack_into('<I',data,0,next_offset)
    struct.pack_into('<Q',data,24,123456789)
    struct.pack_into('<Q',data,40,100)
    struct.pack_into('<I',data,56,0x27)
    struct.pack_into('<I',data,60,len(encoded))
    data[94:]=encoded
    return bytes(data)


def packet(payload=None,complete=1,mode=1,opened=0,info=0,inode=99):
    path=b'Z:\\state\\fixture\\fx'
    final=b'\\\\?\\Z:\\state\\fixture\\fx'
    data=bytearray(96)
    data[:8]=b'COHNTB1\0'
    struct.pack_into('<IIII',data,8,1,mode,12,13)
    struct.pack_into('<Q',data,32,inode)
    struct.pack_into('<IIIIIIII',data,40,opened,info,len(path),len(final),8192,256,32,512*1024)
    data+=path+final
    count=0
    if payload is not None:
        count=len(probe.rows(payload))
        data+=b'NTBATCH1'+struct.pack('<IIII',0,0,len(payload),count)+payload
    footer=b'NTEND1\0\0'+struct.pack('<IIIIIIII',1,complete,int(payload is not None),count,
                                   0x80000006 if mode==1 else 0xc0000001,0,len(data)+40,0)
    return bytes(data+footer)


class PacketParser(unittest.TestCase):
    def test_current_native_record_fields_and_scope(self):
        value=probe.parse(packet(row()))
        self.assertEqual(value['native_inode'],99)
        self.assertEqual(value['rows'][0]['attributes_consumed'],7)
        self.assertEqual(value['rows'][0]['write_FILETIME'],123456789)
        self.assertEqual(value['rows'][0]['size_low'],100)
        self.assertFalse(value['provider_authority'])
        self.assertTrue(value['outer_native_exit_console_and_custody_required'])

    def test_aligned_chain_preserves_names_and_offsets(self):
        first=row('a')
        space=(len(first)+7)&~7
        first=row('a',space)+b'\0'*(space-len(first))
        value=probe.parse(packet(first+row('B')))
        self.assertEqual([r['name'] for r in value['rows']],['a','B'])
        self.assertEqual(value['rows'][1]['record_offset'],space)

    def test_truncated_or_nonadvancing_record_refuses(self):
        for data in (row()[:93],row()[:-1],row('a',1),row('a',0xffffffff)):
            with self.assertRaises(ValueError):
                probe.rows(data)

    def test_unknown_non_ascii_and_separator_refuses(self):
        for name in ('é','x/y','x\\y','x\0y'):
            with self.assertRaises(ValueError):
                probe.rows(row(name))

    def test_partial_native_refusal_is_preserved_not_success(self):
        value=probe.parse(packet(complete=0,opened=0xc0000043,info=0xc0000001,inode=0))
        self.assertFalse(value['packet_complete'])
        self.assertEqual(value['native_open_status'],0xc0000043)

    def test_complete_positive_native_status_is_refused(self):
        for key in ('opened','info'):
            with self.assertRaises(ValueError):
                probe.parse(packet(row(),**{key:1}))

    def test_footer_inconsistency_and_trailing_bytes_refuse(self):
        original=packet(row())
        for data in (original[:-1],original+b'x',original[:-16]+b'\x00'*16):
            with self.assertRaises(ValueError):
                probe.parse(data)

    def test_sharing_observer_scope_does_not_claim_enumeration(self):
        value=probe.parse(packet(mode=2))
        self.assertTrue(value['packet_complete'])
        self.assertEqual(value['rows'],[])
        with self.assertRaises(ValueError):
            probe.parse(packet(row(),mode=2))


if __name__=='__main__':
    unittest.main()
