from pathlib import Path
from unittest.mock import patch
import copy,json,tempfile,unittest,types,sys
import qualify_controlled_completions as q

ROOT=Path(__file__).resolve().parents[4]

class ControlledCompletionContracts(unittest.TestCase):
 def test_frozen_loader_executes_checked_bytes_not_pyc_or_source_lookup(self):
  with tempfile.TemporaryDirectory() as temporary:
   path=Path(temporary)/'sentinel.py';path.write_text('raise RuntimeError("unverified disk source")')
   path.with_suffix('.pyc').write_bytes(b'untrusted cached bytecode')
   executed={};module=types.ModuleType('checked_sentinel')
   q.FrozenSourceLoader(path,b'value=8192\n',executed).exec_module(module)
   self.assertEqual(module.value,8192);self.assertIsNone(module.__cached__)
   self.assertEqual(executed[str(path)],q.sha(b'value=8192\n'))
 def test_checked_source_freeze_refuses_wrong_commit_and_post_mutation(self):
  checked=q.ensure_helpers(ROOT)
  with self.assertRaises(ValueError):q.freeze_inputs(ROOT,'0'*40)
  self.assertTrue(q.revalidate_checked(checked)['inputs_unchanged'])
  with patch.object(Path,'read_bytes',return_value=b'changed'):
   with self.assertRaises(ValueError):q.revalidate_checked(checked)
 def test_exact_corpus_admission_and_every_field_mutation(self):
  self.assertEqual(q.admit_result(q.EXPECTED_RESULT),q.EXPECTED_RESULT)
  for name in q.EXPECTED_RESULT:
   changed=copy.deepcopy(q.EXPECTED_RESULT);changed[name]=not changed[name] if type(changed[name]) is bool else changed[name]+1
   with self.assertRaises(ValueError):q.admit_result(changed)
   changed=copy.deepcopy(q.EXPECTED_RESULT);del changed[name]
   with self.assertRaises(ValueError):q.admit_result(changed)
  changed=dict(q.EXPECTED_RESULT,passed=1)
  with self.assertRaises(ValueError):q.admit_result(changed)
 def test_ten_pinned_sources_seven_functions_only_offset_diff(self):
  values=q.source_inputs(ROOT);candidate,functions=q.generated(values);old,old_functions=q.generated(values,True)
  self.assertEqual(len(values),10);self.assertEqual(len(functions),7)
  self.assertEqual([name for name in functions if functions[name]!=old_functions[name]],['CSocketServerEx::OnRead'])
  self.assertEqual(candidate.replace(q.candidate.AFTER.decode(),q.candidate.BEFORE.decode()),old)
  self.assertIn('void CIOSocket::OnReadCallback',candidate);self.assertIn('void CPacketServerEx::OnIOCallback',candidate)
 def test_native_or_original_source_pin_mutation_refused(self):
  pins=json.loads(q.PINS.read_bytes())
  with tempfile.TemporaryDirectory(prefix='coh-controlled-pins-') as temporary:
   path=Path(temporary)/'pins.json'
   for name in q.FILES:
    changed=copy.deepcopy(pins);changed['sha256'][name]='0'*64;path.write_text(json.dumps(changed))
    with patch.object(q,'PINS',path):
     with self.assertRaises(ValueError):q.source_inputs(ROOT)
 def test_original_global_key_and_insertion_boundary_refused(self):
  values=q.source_inputs(ROOT);fixture=q.HERE/'controlled_completion_fixture.cpp';original=fixture.read_text()
  for mutation in (original.replace('0xa4,0xde','0xa5,0xde'),original.replace('#define BUFFER_SIZE 8192','#define BUFFER_SIZE 4096'),original.replace('struct WSABUF {DWORD len;','struct WSABUF {unsigned long len;'),original.replace('DWORD m_size=0;','int m_size=0;'),original.replace('/* EXACT_PACKET_CRYPTO */','/* EXACT_PACKET_CRYPTO */\n/* EXACT_PACKET_CRYPTO */')):
   with patch.object(Path,'read_text',return_value=mutation):
    with self.assertRaises(ValueError):q.generated(values)
 def test_original_buffer_size_unsigned_shape_and_opcode_domain_required(self):
  values=q.source_inputs(ROOT)
  for source,old,new in ((q.BUFFER,b'#define BUFFER_SIZE 8192',b'#define BUFFER_SIZE 4096'),(q.BUFFER,b'DWORD m_size',b'int m_size'),('upstream/ouroboros/AuthServer/src/Protocol.h',b'AQ_SERVER_LIST_EXT',b'AQ_FAKE_EXT')):
   changed=dict(values);self.assertIn(old,changed[source]);changed[source]=changed[source].replace(old,new)
   with self.assertRaises(ValueError):q.generated(changed)
 def test_real_auth_baseline_remains_capped_sends_not_controlled_receiver(self):
  baseline=q.runtime_baseline();self.assertEqual(baseline['cases'],8)
  self.assertFalse(baseline['receiver_segmentation_controlled']);self.assertFalse(baseline['general_tcp_segmentation_accepted'])
  self.assertFalse(baseline['existing_binary_or_service_reexecuted']);self.assertEqual(baseline['authserver_binary_sha256'],'9cd262dd862d14bf2d696de65cb70f155f25473503d7fd0968de9969e0ac8003')

if __name__=='__main__':unittest.main()
