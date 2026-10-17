from pathlib import Path
import tempfile
import unittest
import pg_wine_checksum_recipe as r

ROOT=Path(__file__).resolve().parents[4]

class RecipeTests(unittest.TestCase):
 def test_exact_composition_single_additional_change_and_no_permit(self):
  with tempfile.TemporaryDirectory() as temp:
   output=Path(temp)/'recipe';proof=r.prepare(ROOT,output)
   changed=[name for name in proof['baseline_closure_sha256'] if proof['baseline_closure_sha256'][name]!=proof['candidate_closure_sha256'][name]]
   self.assertEqual(changed,[r.CHECKSUM]);self.assertTrue(proof['version_checksum_caller_unchanged'])
   for key in ('buildable_tree','new_binary_built','shipping_runtime_replacement_permit','manual_atlas_layers_composed','runtime_profile_admitted','native_reference_alias_created','live_authenticated_db_login_verified'):self.assertFalse(proof[key])
   self.assertEqual(proof['accepted_normal_binary']['sha256'],'535bfd6df77ce09bc3d1048accd95d7910552f8861c3a9c4e356d522786d585c')
   with self.assertRaises(ValueError):r.prepare(ROOT,output)
 def test_critical_source_mutation_and_link_refusal(self):
  with tempfile.TemporaryDirectory() as temp:
   output=Path(temp)/'recipe';proof=r.prepare(ROOT,output)
   for name in ('DBServer/src/sql_fifo.c','DBServer/src/clientcomm.c','DBServer/src/authcomm.c','libs/UtilitiesLib/src/version/AppVersion.c'):
    path=output/name;data=path.read_bytes();path.write_bytes(data+b'changed')
    with self.assertRaises(ValueError):r.verify(output,proof['candidate_closure_sha256'])
    path.write_bytes(data)
   path=output/r.CHECKSUM;data=path.read_bytes();path.unlink();target=Path(temp)/'external';target.write_bytes(data);path.symlink_to(target)
   with self.assertRaises(ValueError):r.verify(output,proof['candidate_closure_sha256'])
 def test_no_repository_destination_or_mismatched_patch(self):
  with self.assertRaises(ValueError):r.prepare(ROOT,ROOT/'unsafe-new-recipe')
  with tempfile.TemporaryDirectory() as temp:
   with self.assertRaises(ValueError):r.apply_patch(Path(temp),b'invalid patch')

if __name__=='__main__':unittest.main()
