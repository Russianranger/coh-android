from pathlib import Path
import gzip,json
import tempfile
import unittest
import manual_atlas_full_recipe as r

ROOT=Path(__file__).resolve().parents[4]

class FullRecipeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.owned=tempfile.TemporaryDirectory(prefix='coh-full-manual-recipe-test-');cls.output=Path(cls.owned.name)/'source'
  cls.proof=r.prepare(ROOT,cls.output)
 @classmethod
 def tearDownClass(cls):cls.owned.cleanup()
 def test_all_original_and_manual_layers_only_checksum_delta(self):
  p=self.proof;maps=p['maps']
  retained=json.loads(gzip.decompress((r.MANIFEST.parent/'source-recipe.source-maps.json.gz').read_bytes()))
  self.assertEqual(maps,retained)
  self.assertEqual(len(maps['original']),5995);self.assertEqual(len(maps['accepted_manual_lineage']),6007)
  self.assertEqual([n for n in maps['checksum_candidate'] if maps['checksum_candidate'][n]!=maps['accepted_manual_lineage'][n]],[r.base.CHECKSUM])
  self.assertEqual(len(p['layers']),5);self.assertTrue(r.verify_complete_source(self.output,maps['checksum_candidate'])['full_first_party_source_verified'])
  for key in ('build_executed','new_binary_built','runtime_profile_admitted','shipping_runtime_replacement_permit','manual_wait_skip_permitted_for_real_auth','native_reference_alias_created'):self.assertIs(p[key],False)
 def test_saved_persistence_version_auth_and_guard_mutations_refused(self):
  expected=self.proof['maps']['checksum_candidate']
  for name in ('DBServer/src/sql_fifo.c','DBServer/src/container_merge.c','DBServer/src/container_sql.c','DBServer/src/clientcomm.c','DBServer/src/authcomm.c','DBServer/src/wine_manual_atlas.c','libs/UtilitiesLib/src/version/AppVersion.c'):
   path=self.output/name;data=path.read_bytes();path.write_bytes(data+b'changed')
   try:
    with self.assertRaises(ValueError):r.verify_complete_source(self.output,expected)
   finally:path.write_bytes(data)
 def test_extra_linked_missing_and_existing_destination_refused(self):
  expected=self.proof['maps']['checksum_candidate'];path=self.output/'unexpected.c';path.write_bytes(b'unqualified')
  try:
   with self.assertRaises(ValueError):r.verify_complete_source(self.output,expected)
  finally:path.unlink()
  path=self.output/r.base.CHECKSUM;data=path.read_bytes();path.unlink();target=Path(self.owned.name)/'outside';target.write_bytes(data);path.symlink_to(target)
  try:
   with self.assertRaises(ValueError):r.verify_complete_source(self.output,expected)
  finally:path.unlink();path.write_bytes(data)
  with self.assertRaises(ValueError):r.prepare(ROOT,self.output)
  with self.assertRaises(ValueError):r.prepare(ROOT,ROOT/'unsafe-full-manual-source')
 def test_build_inputs_and_dependency_mutations_refused(self):
  for name in ('DBServer/src/dbinit.c','cmake/dependencies/Zlib.cmake','cmake/StructParser.cmake','libs/crashrpt/src/CrashRpt.rc','CMakeLists.txt'):
   path=self.output/name;data=path.read_bytes();path.write_bytes(data+b'changed')
   try:
    with self.assertRaises(ValueError):r.build_plan(self.output,'build','patch.exe',self.proof['maps']['checksum_candidate'])
   finally:path.write_bytes(data)
 def test_compile_profile_keeps_normal_flags_and_only_dbserver(self):
  plan=r.build_plan(self.output,'build','patch.exe',self.proof['maps']['checksum_candidate']);configure,build=plan['commands']
  self.assertTrue(plan['static_plan_only']);self.assertFalse(plan['compiler_executed'])
  self.assertEqual(plan['enabled_registered_projects'],['Common','DbServer'])
  self.assertEqual(len(plan['external_dependencies']),3)
  for name in plan['disabled_registered_projects']:self.assertIn('-DCOX_BUILD_'+name.upper()+'=OFF',configure)
  for flag in ('-DCOH_PG_PERSISTENCE_TESTS=OFF','-DCOX_BUILD_MAPSERVER=OFF','-DCOX_BUILD_BEACONSERVER=OFF'):self.assertIn(flag,configure)
  self.assertEqual(build,['cmake','--build','build','--config','OptDebug','--parallel','2','--target','DbServer'])
  self.assertIn('Win32',configure)

if __name__=='__main__':unittest.main()
