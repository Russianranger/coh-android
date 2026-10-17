import copy
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace
import admit_resources as admit
import capture_resources as capture
import stage_resources as stage
import delivery as d
ROOT=Path(__file__).resolve().parents[3]
FIELDS=('status','catalog_status','snapshot_status','resource_status','catalog_bytes','snapshot_bytes','resource_bytes','files','slots','definitions','children','root_slots','active_roots','external_count','external_children','resource_records','resource_models','resource_missing_models','resource_textures','model_row_comparisons','client_materials_available','client_lods_available','source_quiescence_status','source_quiescence_held','source_quiescence_released','defs_crc','refs_crc','partial_remaining','failed_final_remaining')
VALUES=(1,0,0,0,12179670,1000,1579,508,40225,40225,130314,33,33,7,0,40232,10000,30232,20000,200000,0,0,1,1,1,3173822562,3649375123,0,0)
def line(values=VALUES):return b'COH_RESOURCE_SNAPSHOT_V1 '+b' '.join(k.encode()+b'='+str(v).encode() for k,v in zip(FIELDS,values))+b'\n'
class ResourceCaptureTests(unittest.TestCase):
 def test_exact_sink_and_independent_scope_counters(self):
  self.assertEqual(capture.sink_observation(line())['resource_records'],40232)
  with self.assertRaises(d.Refused):capture.sink_observation(line()+line())
  for name in ('status','catalog_status','snapshot_status','resource_status','partial_remaining','failed_final_remaining','client_materials_available','client_lods_available'):
   v=list(VALUES);index=FIELDS.index(name);v[index]=2 if name=='status' else 1
   with self.assertRaises(d.Refused):capture.sink_observation(line(v))
  for name,n in (('resource_bytes',64*1024**2+1),('resource_records',40231),('resource_textures',2560001),('model_row_comparisons',64*1024**2+1),('external_count',65)):
   v=list(VALUES);v[FIELDS.index(name)]=n
   with self.assertRaises(d.Refused):capture.sink_observation(line(v))
  self.assertIsNone(capture.sink_observation(b'not the new observer'))
 def triple(self,work):
  fixture=ROOT/'native-android/engine/scenecatalog-server/evidence/resource-observer/resources.cohres'
  raw=fixture.read_bytes();records=capture.resource_wire.decode(raw);external=[r for r in records if r['owner_kind']==2]
  side=bytearray(80);side[:8]=b'COHRTS01';struct.pack_into('<I',side,44,0)
  for i,r in enumerate(external):
   name=r['strings'][0].encode()+b'\0';side.extend(struct.pack('<9I',i,r['original_id'],15,r['model_present'],len(name),8,1,0,0)+bytes(120)+name+b'x')
  (work/'catalog').write_bytes(b'synthetic catalog');(work/'snapshot').write_bytes(side);(work/'resources').write_bytes(raw)
  sink={'source_quiescence_status':1,'source_quiescence_held':1,'source_quiescence_released':1,'resource_bytes':len(raw),'resource_records':len(records),'resource_models':1,'resource_missing_models':len(records)-1,'resource_textures':2,'files':508,'external_count':len(external)}
  return raw,sink
 def test_source_stream_exact_pair_generation_order_and_futures(self):
  with tempfile.TemporaryDirectory() as t:
   work=Path(t);raw,sink=self.triple(work)
   with mock.patch.object(capture.snapshot_base,'validate_pair',return_value=True):
    r=capture.validate_triple(work/'catalog',work/'snapshot',work/'resources',sink,20261016)
    self.assertEqual(r['records'],6);self.assertFalse(r['native_decode_completed']);self.assertFalse(r['assets_admitted'])
    for key in ('resource_records','resource_models','resource_missing_models','resource_textures','external_count','resource_bytes'):
     changed=dict(sink);changed[key]+=1
     with self.assertRaises((d.Refused,ValueError)):capture.validate_triple(work/'catalog',work/'snapshot',work/'resources',changed,20261016)
    for offset in (20,24,28,32,36,44):
     bad=bytearray(raw);bad[offset]^=1;(work/'resources').write_bytes(bad)
     with self.assertRaises((d.Refused,ValueError)):capture.validate_triple(work/'catalog',work/'snapshot',work/'resources',sink,20261016)
    (work/'resources').write_bytes(raw)
    bad=bytearray((work/'snapshot').read_bytes());bad[80+156]^=1;(work/'snapshot').write_bytes(bad)
    with self.assertRaises(d.Refused):capture.validate_triple(work/'catalog',work/'snapshot',work/'resources',sink,20261016)
 def test_new_role_admission_and_hash_drift(self):
  prior={'schema_version':1,'build_role':'map_startup_certified_animation','build_targets':['MapServer'],'animation_certificate':{},'monorail_build_input':{},'patched_sha256':{},'overlay_sha256':{},'retained_sources_sha256':{}}
  revision='a'*40;original={n:(ROOT/'upstream/ouroboros'/n).read_bytes() for n in stage.PATCHED};output=stage.transform(original[stage.base.GROUP],original[stage.base.INIT],original[stage.GUARD])
  with tempfile.TemporaryDirectory() as t,mock.patch.object(stage.base,'expected_prior',return_value=prior):
   work=Path(t);compile=work/'compile';compile.mkdir();declared=stage.expected(ROOT,prior,original,output)
   files={'MapServer.exe':b'fixture-not-PE','CMakeCache.txt':b'fixture',stage.RECEIPT:json.dumps(declared).encode(),stage.PRIOR:json.dumps(prior).encode(),'map-startup-inputs.json':b'{}'}
   files.update({'source/'+n:raw for n,raw in {**output,**stage.overlays(ROOT)}.items()})
   for n,raw in files.items():p=compile/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
   receipt={'schema':'coh-resource-snapshot-compile-v1','passed':True,'source_revision':revision,'source_git_status_porcelain':[],'build_role':stage.ROLE,'compile_only':True,'runtime_executed':False,'source_stage_verified':True,'published_inputs_reverified':True,'artifacts':{n:{'bytes':len(raw),'sha256':d.digest(raw)} for n,raw in files.items()}}
   path=compile/'compile-only-receipt.json';path.write_text(json.dumps(receipt));self.assertEqual(admit.inspect(compile,ROOT,revision)[0],receipt)
   for schema in ('coh-runtime-snapshot-compile-v1','wrong'):
    changed=copy.deepcopy(receipt);changed['schema']=schema;path.write_text(json.dumps(changed))
    with self.assertRaises(d.Refused):admit.inspect(compile,ROOT,revision)
   path.write_text(json.dumps(receipt));candidate=work/'candidate';plan=admit.admit(compile,ROOT,revision,candidate)
   self.assertEqual(capture.verify_candidate(candidate,revision),plan)
   modified=dict(plan);modified['resource_producer_sha256']='0'*64;(candidate/'deployment-plan.json').write_text(json.dumps(modified))
   with self.assertRaises(d.Refused):capture.verify_candidate(candidate,revision)
   (candidate/'deployment-plan.json').write_text(json.dumps(plan));(candidate/'MapServer.exe').write_bytes(b'changed')
   with self.assertRaises(d.Refused):capture.verify_candidate(candidate,revision)
 def test_isolated_host_guard_never_starts_service(self):
  with mock.patch.object(capture.os,'geteuid',return_value=0),mock.patch.object(capture.subprocess,'Popen') as start:
   with self.assertRaises(d.Refused):capture.capture(SimpleNamespace())
   start.assert_not_called()
 def test_binding_cleanup_provenance_and_copied_bytes_fail_closed(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t);raw,sink=self.triple(out)
   (out/'catalog').rename(out/'catalog.cohcat');(out/'snapshot').rename(out/'runtime.cohrts');(out/'resources').rename(out/'resources.cohres')
   report={'schema':'coh-disposable-resource-snapshot-v1','generation':20261016}
   truekeys=('passed','runtime_executed','catalog_captured','runtime_snapshot_captured','resource_snapshot_captured','catalog_exact_equality','cleanup_verified','owned_process_groups_absent','source_runtime_unchanged','source_snapshot_only')
   falsekeys=('player_profile_opened','accepted_runtime_modified','physical_thor_generation_verified','matching_groups_transaction_captured','renderer_authorized','native_decode_completed','live_groups_transaction','assets_admitted','client_materials_available','client_lods_available')
   report.update(dict.fromkeys(truekeys,True));report.update(dict.fromkeys(falsekeys,False))
   revision='a'*40;tree='b'*40;producer='c'*64;exporter='d'*64
   report.update(db_schema={'fixture_only':True},compile_receipt_sha256='f'*64,stage_receipt_sha256='a'*64,exporter_source_revision=revision,orchestration_source_revision=revision,orchestration_source_tree=tree,exporter_sha256=exporter,source_runtime_inventory={'files':10},source_sha256={'native-android/engine/scenecatalog-server/source_resources.inc':producer},sink=sink)
   source={'source_quiescence_guard':'original_geo_lod_trylock_zero_pending','source_snapshot_only':True,'client_materials_available':False,'client_lods_available':False,'map_id':1,'map_name':'maps/City_Zones/City_01_01/City_01_01.txt','compile_receipt_sha256':report['compile_receipt_sha256'],'stage_receipt_sha256':report['stage_receipt_sha256'],'schema':'coh-resource-snapshot-source-v1','exporter_source_revision':revision,'exporter':{'sha256':exporter},'runtime_inventory':report['source_runtime_inventory'],'orchestration_source_sha256':report['source_sha256'],'resource_producer_sha256':producer,'asset_generation':20261016,'retained_catalog_sha256':capture.CATALOG_SHA256,'owner_callback':'coh_source_resource_snapshot_startup'}
   sourcepin=capture.emit_identity(out/'source-identity.json',source)
   run={'db_schema_sha256':d.digest(capture.canonical(report['db_schema'])),'schema':'coh-resource-snapshot-run-v1','source_identity_sha256':sourcepin,'owner_callback':'coh_source_resource_snapshot_startup','orchestration_source_revision':revision,'orchestration_source_tree':tree,'private_fresh_wine_prefix':True,'private_fresh_postgresql':True,'player_profile_opened':False,'resource_capture_requested':True,'nonce':'e'*64}
   runpin=capture.emit_identity(out/'run-identity.json',run);report.update(source_identity_sha256=sourcepin,run_identity_sha256=runpin)
   original=d.hash_file
   def hashes(path,maximum):
    return (12179670,capture.CATALOG_SHA256) if Path(path).name=='catalog.cohcat' else original(path,maximum)
   for key,name in (('catalog','catalog.cohcat'),('snapshot','runtime.cohrts'),('resources','resources.cohres')):
    n,digest=hashes(out/name,64*1024**2);report[key]={'bytes':n,'sha256':digest}
   with mock.patch.object(d,'hash_file',side_effect=hashes),mock.patch.object(capture.snapshot_base,'validate_pair',return_value=True):
    binding=capture.build_binding(out,report,20261016);self.assertFalse(binding['assets_admitted']);self.assertEqual(binding['resources'],report['resources'])
    for key in truekeys+falsekeys:
     changed=copy.deepcopy(report);changed[key]=not changed[key]
     with self.assertRaises(d.Refused):capture.build_binding(out,changed,20261016)
    changed=copy.deepcopy(report);changed['resources']['sha256']='0'*64
    with self.assertRaises(d.Refused):capture.build_binding(out,changed,20261016)
    changed=copy.deepcopy(report);changed['run_identity_sha256']='0'*64
    with self.assertRaises(d.Refused):capture.build_binding(out,changed,20261016)
    for key,value in (('source_quiescence_guard','unheld'),('source_snapshot_only',False),('client_materials_available',True),('client_lods_available',True),('map_id',2),('map_name','maps/elsewhere.txt'),('compile_receipt_sha256','0'*64)):
     wrong=dict(source);wrong[key]=value;wrongraw=capture.canonical(wrong);(out/'source-identity.json').write_bytes(wrongraw)
     wrongrun=dict(run);wrongrun['source_identity_sha256']=d.digest(wrongraw);wrongrunraw=capture.canonical(wrongrun);(out/'run-identity.json').write_bytes(wrongrunraw)
     changed=copy.deepcopy(report);changed['source_identity_sha256']=d.digest(wrongraw);changed['run_identity_sha256']=d.digest(wrongrunraw)
     with self.assertRaises(d.Refused):capture.build_binding(out,changed,20261016)
    (out/'source-identity.json').write_bytes(capture.canonical(source));wrongrun=dict(run);wrongrun['db_schema_sha256']='0'*64;wrongraw=capture.canonical(wrongrun);(out/'run-identity.json').write_bytes(wrongraw)
    changed=copy.deepcopy(report);changed['run_identity_sha256']=d.digest(wrongraw)
    with self.assertRaises(d.Refused):capture.build_binding(out,changed,20261016)

 def test_texture_work_and_printable_name_bounds(self):
  raw=(ROOT/'native-android/engine/scenecatalog-server/evidence/resource-observer/resources.cohres').read_bytes();bad=bytearray(raw)
  struct.pack_into('<I',bad,96,257)
  with self.assertRaises(ValueError):capture.resource_wire.decode(bad)
if __name__=='__main__':unittest.main()
