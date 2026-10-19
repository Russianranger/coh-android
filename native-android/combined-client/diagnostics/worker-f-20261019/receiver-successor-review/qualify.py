#!/usr/bin/env python3
"""Read-only successor ELF/source admission; no protocol/server invocation."""
import gzip,hashlib,importlib.util,json,pathlib,subprocess,sys,tempfile
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[4]
SRC=ROOT/'native-android/combined-client/diagnostics/gates25-27-thor-20261018/server-initial-investigation-worker-c'
def sha(v):return hashlib.sha256(v).hexdigest()
def read(p):return p.read_bytes()
def record(p):v=read(p);return {'bytes':len(v),'sha256':sha(v)}
def main():
 new=SRC/'qualified03-fragment-20261019';old=SRC/'qualified02';proof=json.loads(read(new/'qualification.json'));previous=json.loads(read(old/'qualification.json'));scope=json.loads(read(new/'successor-scope.json'));retained=json.loads(read(new/'retention-binding.json'))
 assert proof['passed'] and not proof['world_authority'];assert retained['passed']
 for p,v in retained['files'].items():assert record(new/p)==v
 for p,v in proof['source_sha256'].items():assert sha(read(ROOT/p))==v
 diff={p:{'before':previous['source_sha256'].get(p),'after':v} for p,v in proof['source_sha256'].items() if previous['source_sha256'].get(p)!=v}
 assert diff==scope['changed_compiler_inputs'] and len(diff)==2
 assert sha(read(old/'qualification.json'))==scope['predecessor_receipt_sha256']
 assert sha(read(new/'qualification.json'))==scope['successor_receipt_sha256']
 assert scope['legacy_field_context']['whole_source_unchanged_claim']is False
 assert scope['source_revision_is_not_a_claim_that_uncommitted_inputs_equal_revision']is True
 mismatch=[]
 for p,v in proof['source_sha256'].items():
  blob=subprocess.check_output(['git','show',proof['source_revision']+':'+p],cwd=ROOT)
  if sha(blob)!=v:mismatch.append(p)
 assert set(mismatch)==set(diff)
 elves={}
 for mode,detail in proof['modes'].items():
  for role,name in [('unit','receive-unit-'+mode),('jni','receive-jni-'+mode),('production_role',mode+'-coh-capture-initial-receive')]:
   raw=gzip.decompress(read(new/(name+'.gz')));actual={'bytes':len(raw),'sha256':sha(raw)}
   assert actual==detail['executables'][role];assert raw[:6]==b'\x7fELF\x02\x01' and raw[18:20]==b'>\x00'
   elves[name]=actual
  assert detail['focused_unit']['checks']==30 and detail['focused_JNI']['checks']==86
  assert detail['Python_projection_controls']['positive']==3 and detail['Python_projection_controls']['negative']==99
 sys.path.insert(0,str(ROOT/'native-android/engine/scenecatalog-server'))
 spec=importlib.util.spec_from_file_location('f_receive_admission',SRC/'receive_admission.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 refusals={}
 with tempfile.TemporaryDirectory(prefix='coh-f-receiver-admit-')as t:
  binary=pathlib.Path(t)/mod.BASENAME;binary.write_bytes(gzip.decompress(read(new/(mod.BASENAME+'.gz'))));binary.chmod(0o700)
  admitted=mod.native_input(binary,new/'qualification.json',sha(read(new/'qualification.json')),ROOT)
  assert admitted==scope['successor_current_source_actual_elf_admission']
  for label,receipt,pin in [('prior-receipt',old/'qualification.json',sha(read(old/'qualification.json'))),('wrong-receipt-hash',new/'qualification.json','0'*64)]:
   try:mod.native_input(binary,receipt,pin,ROOT)
   except Exception as error:refusals[label]=str(error)
   else:raise AssertionError('false successor admission')
 result={'schema':'coh-independent-receiver-successor-review-v1','passed':True,'successor_receipt':record(new/'qualification.json'),'successor_scope_receipt':record(new/'successor-scope.json'),'retention_binding':record(new/'retention-binding.json'),'retained_files_verified':len(retained['files']),'source_pins_current_raw_verified':len(proof['source_sha256']),'source_pins_equal_checkout_base':len(proof['source_sha256'])-len(mismatch),'checkout_base_differences':mismatch,'explicit_changed_compiler_inputs':diff,'nine_retained_ELFs_decompressed_and_bound':elves,'current_source_actual_ELF_admission_passed':True,'expected_receipt_refusals':refusals,'scope_note':'Qualified03 is a fresh three-mode compile with two changed underlying transport TUs, not equivalence/reuse of unchanged qualified02. Historical false checker field is explicitly superseded by scope receipt. Noargs, numeric projection doubles, JNI doubles and source-generated fragment tests remain distinct from real source-service or Android runtime execution.','actual_server_protocol_executed':False,'actual_Android_or_Thor_executed':False,'original_compiler_receipt_rewritten':False,'whole_process_memory_fit':False,'world_authority':False,'gates25_27':'OPEN'}
 (HERE/'review.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({'passed':True,'retained_files':len(retained['files']),'raw_pins':len(proof['source_sha256']),'changed_source_pins':len(diff),'ELFs':len(elves),'expected_refusals':len(refusals)}))
if __name__=='__main__':main()
