#!/usr/bin/env python3
"""Stage only the separately identified fresh callback-sealed Map observer."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import stage_groups_capture as old
base=old.base
ROLE='nonshipping_fresh_callback_sealed_groups_observer'
RECEIPT='native-fresh-groups-server-build-input.json'
FOLDER='libs/UtilitiesLib/src/utils/FolderCache.c'
FOLDER_SHA='93aac8a9e1a59ca47ab5a067580c36f7ed884db51038577b0453756f55af1d4c'
API='libs/UtilitiesLib/src/utils/coh_fresh_folder_profile_api.h'
GROUP_API='libs/UtilitiesLib/src/utils/coh_fresh_source_profile_api.h'
GUARD_API='Common/seq/coh_fresh_folder_profile_api.h'
FOLDER_IMPL='libs/UtilitiesLib/src/utils/coh_fresh_folder_profile.inc'
GROUP_IMPL='MapServer/src/group/coh_fresh_source_profile.inc'
ORIGINAL_GUARD='Common/seq/coh_fresh_original_resource_quiescence.inc'
PATCHED=(*old.PATCHED,FOLDER)
CALL=b'coh_fresh_source_profile_install'
SEAL=b'    coh_fresh_source_profile_seal_after_normal_enable();\n'
SEAL_PROTO=b'void coh_fresh_source_profile_seal_after_normal_enable(void);\n'
GROUP_TAIL=b'\n/* NEW explicit fresh disposable callback-sealed diagnostic profile. */\n#include "coh_fresh_source_profile.inc"\n'
OWNER_SHA='7c485ebe5385171f22a1ad258449cb61477d8b2598952b1f2690df3c5c31c1bc'
INITIAL_OWNER_SOURCE=b'''/* Fresh disposable observer only. Original entInUse success is unchanged.
 * A loaded player remains SLEEPING through CLIENT_REQSCENE; CLIENT_READY's
 * resumeCharacter wakes it later. This alternate path observes that narrowly
 * owned pre-entry state; it never changes entity state or advances a client.
 * Called only after original nonnull/backlink/private-table-bound checks. */
static int coh_fresh_source_initial_owner(const Entity*entity,const ClientLink*client,const void*out,size_t output_bytes)
{
 if(entInUse(entity->owner))return 1;
 if(coh_fresh_source_owner_failed(entity->owner>=entities_max,COH_FRESH_OWNER_INITIAL_SLOT_OUTSIDE_TABLE))return 0;
 if(coh_fresh_source_owner_failed(entity_state[entity->owner]!=ENTITY_SLEEPING,COH_FRESH_OWNER_INITIAL_STATE))return 0;
 if(coh_fresh_source_owner_failed(!coh_source_owner_disjoint(out,output_bytes,entinfo,(size_t)MAX_ENTITIES_PRIVATE*sizeof(*entinfo)),COH_FRESH_OWNER_INITIAL_OUTPUT_ENTINFO_ALIAS))return 0;
 if(coh_fresh_source_owner_failed(ENTTYPE(entity)!=ENTTYPE_PLAYER,COH_FRESH_OWNER_INITIAL_NOT_PLAYER))return 0;
 if(coh_fresh_source_owner_failed(!entity->owned,COH_FRESH_OWNER_INITIAL_NOT_OWNED))return 0;
 if(coh_fresh_source_owner_failed(!entity->pl,COH_FRESH_OWNER_INITIAL_PLAYER_ABSENT))return 0;
 if(coh_fresh_source_owner_failed(client->ready!=CLIENTSTATE_NOT_READY,COH_FRESH_OWNER_INITIAL_CLIENT_STATE))return 0;
 if(coh_fresh_source_owner_failed(entity->ready!=0,COH_FRESH_OWNER_INITIAL_ENTITY_READY))return 0;
 if(coh_fresh_source_owner_failed(entity->demand_loaded!=0,COH_FRESH_OWNER_INITIAL_RELAY))return 0;
 if(coh_fresh_source_owner_failed(entity->is_map_xfer!=0,COH_FRESH_OWNER_INITIAL_TRANSFER_LOGIN))return 0;
 if(coh_fresh_source_owner_failed(entity->dbcomm_state.in_map_xfer!=0,COH_FRESH_OWNER_INITIAL_TRANSFER_ACTIVE))return 0;
 if(coh_fresh_source_owner_failed(entity->dbcomm_state.waiting_map_xfer!=0,COH_FRESH_OWNER_INITIAL_TRANSFER_WAITING))return 0;
 if(coh_fresh_source_owner_failed(entity->dbcomm_state.map_xfer_step!=MAPXFER_NO_XFER,COH_FRESH_OWNER_INITIAL_TRANSFER_STEP))return 0;
 return 1;
}
'''
CONTRACT={'role':ROLE,'nonshipping':True,'fresh_disposable_fixture_only':True,
 'accepted_observer_and_shipping_profile_unchanged':True,'accepted_cache_watch_policy_equivalent':False,
 'normal_startup_enable_preserved_then_explicit_original_api_disable':True,
 'configured_same_thread_sink_and_actual_folder_owner_required':True,
 'instrumented_queue_before_add_after_initialized_after_free':True,
 'recursive_reservation_lock_and_atomic_observation_close':True,
 'original_callback_update_allocator_bodies_outside_reservation_lock':True,
 'whole_public_callback_poll_reserved':True,'queue_nodes_observed':False,
 'original_boundary_predicate_and_supplier_bodies_preserved':True,
 'original_loader_guard_byte_exact_under_new_wrapper':True,
 'restore_only_when_actual_mutation_depths_idle':True,
 'failed_restore_may_remain_sealed_until_owner_retry_or_process_cleanup':True,
 'source_probe_environment':'COH_NATIVE_GROUPS_PROFILE_PROBE_OUTPUT',
 'source_probe_precreated_owned_regular_file_required':True,
 'source_probe_schema':'coh-fresh-source-profile-probe-v2',
 'first_owner_failure_atom_observed_once_in_original_order':True,
 'owner_failure_enum_only_no_original_values_or_io':True,
 'fresh_only_in_use_or_exact_owned_pre_ready_initial_player':True,
 'initial_owner_does_not_set_state_or_send_ready':True,
 'source_probe_maximum_bytes':8192,'source_probe_authority':False,
 'source_generation_admitted':False,'world_authority':False,'runtime_executed':False}
LOCAL=('source_folder_profile_api.h','source_folder_profile.inc','source_group_profile_api.h',
 'source_group_profile.inc','source_sealed_quiescence.inc','stage.py')

def checkout_closure(root):
 """Bind executed helpers and overlay suppliers to THIS exact committed tree."""
 root=base.safe_path(root);base.require(HERE==root/'native-android/engine/scenecatalog-server/fresh_callback_observer','FRESH_OWN_CHECKOUT')
 files={p for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.inc','.h')}
 files.update(p for p in HERE.parent.iterdir() if p.is_file() and p.suffix in ('.py','.inc','.json'))
 files.update((root/'tools').glob('*.py'))
 files.update((root/'native-android/engine/scenecatalog-qualification').glob('*.py'))
 expected={p.resolve():p for p in files}
 tool_names={p.stem for p in files if p.parent==root/'tools'}
 for module in tuple(sys.modules.values()):
  name=getattr(module,'__file__',None)
  if not name:continue
  path=Path(name).resolve()
  if (path.parent.name=='tools' and path.stem in tool_names) or path.parent.name in ('scenecatalog-server','fresh_callback_observer','scenecatalog-qualification'):
   base.require(path in expected,'FRESH_FOREIGN_IMPORTED_HELPER')
 paths={p.relative_to(root).as_posix():p for p in files}
 tree=subprocess.run(['git','ls-tree','-r','-z','HEAD','--',*sorted(paths)],cwd=root,check=True,capture_output=True).stdout
 blobs={}
 for row in tree.split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t',1);mode,kind,digest=meta.split();base.require(kind==b'blob' and mode in (b'100644',b'100755'),'FRESH_TRACKED_HELPER_MODE');blobs[name.decode()]=digest.decode()
 base.require(set(blobs)==set(paths),'FRESH_UNTRACKED_HELPER')
 pins={}
 for n,p in paths.items():
  raw=base.regular(p).read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
  base.require(blob==blobs[n],'FRESH_CHANGED_HELPER');pins[n]=base.sha(raw)
 return pins

def unchanged_checkout(root,pins):
 base.require(checkout_closure(root)==pins,'FRESH_HELPER_CHANGED_DURING_OPERATION')

def once(raw,before,after,code):
 base.require(raw.count(before)==1,code)
 return raw.replace(before,after,1)

def owner_predicates():
 """The one fixed C enum/name/atom table; never a caller-selected predicate."""
 raw=base.lf((HERE/'source_group_profile_api.h').read_bytes())
 rows=re.findall(rb'^ X\(([A-Z_]+),(.+)\)(?: \\)?$',raw,re.M)
 base.require(len(rows)==47 and len({n for n,_ in rows})==47,'FRESH_OWNER_ENUM_TABLE')
 return tuple((name.decode('ascii'),atom) for name,atom in rows)

def instrument_owner(raw):
 """Wrap original failed atoms once without changing their evaluation order."""
 base.require(type(raw) is bytes and base.sha(raw)==OWNER_SHA,'FRESH_OWNER_SOURCE')
 start=raw.index(b'static int coh_source_groups_prepare_owner(')
 before,body=raw[:start],raw[start:];rows=owner_predicates();at=0
 expressions=re.findall(rb'if\(([^\n;]+)\)return 0;',body)
 base.require([atom for expression in expressions for atom in expression.split(b'||')]==[atom for _,atom in rows],'FRESH_OWNER_ATOMS')
 def wrap(match):
  nonlocal at
  result=[]
  for atom in match[1].split(b'||'):
   name,expected=rows[at];at+=1;base.require(atom==expected,'FRESH_OWNER_ORDER')
   result.append(b'coh_fresh_source_owner_failed(('+atom+b'),COH_FRESH_OWNER_'+name.encode()+b')')
  return b'if('+b'||'.join(result)+b')return 0;'
 body=re.sub(rb'if\(([^\n;]+)\)return 0;',wrap,body)
 base.require(at==47,'FRESH_OWNER_COVERAGE');return before+body

def specialize_initial_owner(raw):
 """Replace only the fresh owner's active-state atom; old helper stays intact."""
 owner=base.lf((HERE.parent/'source_groups_owner.inc').read_bytes())
 base.require(raw==instrument_owner(owner),'FRESH_INITIAL_OWNER_BASE')
 entry=b'static int coh_source_groups_prepare_owner('
 result=once(raw,entry,INITIAL_OWNER_SOURCE+entry,'FRESH_INITIAL_OWNER_ENTRY')
 old_atom=b'coh_fresh_source_owner_failed((!entInUse(entity->owner)),COH_FRESH_OWNER_ENTITY_NOT_IN_USE)'
 new_atom=b'coh_fresh_source_owner_failed((!coh_fresh_source_initial_owner(entity,client,out,sizeof(*out))),COH_FRESH_OWNER_ENTITY_NOT_IN_USE)'
 return once(result,old_atom,new_atom,'FRESH_INITIAL_OWNER_ATOM')

def overlays(root):
 return {GUARD_API:base.lf((HERE/'source_folder_profile_api.h').read_bytes()),
 API:base.lf((HERE/'source_folder_profile_api.h').read_bytes()),
 FOLDER_IMPL:base.lf((HERE/'source_folder_profile.inc').read_bytes()),
 GROUP_API:base.lf((HERE/'source_group_profile_api.h').read_bytes()),
 GROUP_IMPL:base.lf((HERE/'source_group_profile.inc').read_bytes()),
 ORIGINAL_GUARD:base.lf((HERE.parent/'source_resource_quiescence.inc').read_bytes()),
 old.GUARD_IMPL:base.lf((HERE/'source_sealed_quiescence.inc').read_bytes())}

def transform(original):
 result={}
 f=base.lf(original[FOLDER]);base.require(base.sha(f)==FOLDER_SHA,'FRESH_FOLDER_SOURCE')
 anchor=b'#include "utilitieslib/utils/DirMonitor.h"\n'
 f=once(f,anchor,anchor+b'#define COH_FRESH_FOLDER_IMPLEMENTATION\n#include "coh_fresh_folder_profile_api.h"\n','FRESH_FOLDER_HEADER')
 for before,after in ((b'static int FolderCacheUpdate(DirChangeInfo** bufferOverrunOut)',b'static int coh_fresh_original_FolderCacheUpdate(DirChangeInfo** bufferOverrunOut)'),
 (b'static void doAllCallbacks(void) {',b'static void coh_fresh_original_doAllCallbacks(void) {'),
 (b'void FolderCacheDoCallbacks(void)\n',b'void coh_fresh_original_FolderCacheDoCallbacks(void)\n'),
 (b'void FolderCacheEnableCallbacks(int enable) {',b'void coh_fresh_original_FolderCacheEnableCallbacks(int enable) {'),
 (b'void FolderCacheSetManualCallbackMode(int on)',b'void coh_fresh_original_FolderCacheSetManualCallbackMode(int on)')):
  f=once(f,before,after,'FRESH_FOLDER_DEFINITION')
 for before,after in ((b'            newitem = listAddNewMember(&queued_callbacks, sizeof(FolderCacheCallbackInfo));',b'            coh_fresh_folder_queue_added();\n            newitem = listAddNewMember(&queued_callbacks, sizeof(FolderCacheCallbackInfo));'),
 (b'            newitem->when = whathappened;',b'            newitem->when = whathappened;\n            coh_fresh_folder_queue_add_finished();'),
 (b'        listFreeMember(walk, &queued_callbacks);',b'        listFreeMember(walk, &queued_callbacks);\n        coh_fresh_folder_queue_removed();')):
  f=once(f,before,after,'FRESH_QUEUE_SITE')
 result[FOLDER]=base.restore_newlines(f+b'\n#include "coh_fresh_folder_profile.inc"\n',original[FOLDER])
 init=base.lf(original[base.INIT]);base.require(init.count(old.CALL)==2,'FRESH_INSTALL')
 init=init.replace(old.CALL,CALL)
 init=once(init,b'void '+CALL+b'(void);\n',b'void '+CALL+b'(void);\n'+SEAL_PROTO,'FRESH_PROTOTYPE')
 init=once(init,b'    FolderCacheEnableCallbacks(1);\n',b'    FolderCacheEnableCallbacks(1);\n'+SEAL,'FRESH_NORMAL_ENABLE')
 result[base.INIT]=base.restore_newlines(init,original[base.INIT])
 group=base.lf(original[base.GROUP])
 owner=base.lf((HERE.parent/'source_groups_owner.inc').read_bytes())
 group=once(group,owner,specialize_initial_owner(instrument_owner(owner)),'FRESH_OWNER_OBSERVATION')
 prefix=b'#include "../../../libs/UtilitiesLib/src/utils/coh_fresh_source_profile_api.h"\n'
 # Observational calls only: each exact original predicate/call remains intact.
 for token,stage in ((b' status=coh_resource_quiescence_begin();','QUIET'),
 (b' if(!coh_source_groups_prepare_owner(link,&s->owner))','OWNER'),
 (b' s->opened=1;if(s->sink.open','OPEN'),
 (b' status=coh_source_catalog_export(','CATALOG'),
 (b' status=coh_source_runtime_snapshot_export(','RUNTIME'),
 (b' status=coh_source_resources_export(','RESOURCES'),
 (b' status=coh_source_public_bounds_export(','BOUNDS'),
 (b' s->kind=5;s->kind_bytes=0;s->phase=2;return s->id;','ELIGIBILITY'),
 (b' if(s->sink.packet(','PACKET'),
 (b' if(coh_resource_quiescence_end()!=1)','QUIET_RELEASE'),
 (b' if(s->sink.commit(','COMMIT')):
  group=once(group,token,b' coh_fresh_source_probe_step(COH_FRESH_STAGE_'+stage.encode()+b');\n'+token,'FRESH_BOUNDARY_STEP')
 result[base.GROUP]=base.restore_newlines(prefix+group+GROUP_TAIL,original[base.GROUP])
 # anim.c body and include site are unchanged. Only the overlay at that include
 # becomes a wrapper around a byte-exact copy of the accepted old guard.
 result[old.GUARD]=original[old.GUARD]
 return result

def expected(root,prior,original,output):
 return {'schema_version':1,'build_role':ROLE,'build_targets':['MapServer'],
 'prior_groups_build_input':prior,'prior_groups_build_input_canonical_sha256':base.canonical(prior),
 'source_sha256':{n:base.sha(v) for n,v in original.items()},
 'patched_sha256':{n:base.sha(v) for n,v in output.items()},
 'overlay_sha256':{n:base.sha(v) for n,v in overlays(root).items()},
 'new_profile_source_sha256':{n:base.sha((HERE/n).read_bytes()) for n in LOCAL},
 'contract':dict(CONTRACT),'runtime_validation':'not_executed_compile_only'}

def prepare(root,stage):
 root,stage=base.private_stage(root,stage);closure=checkout_closure(root);prior=old.verify_staged(root,stage)
 originals={n:base.regular(stage/n).read_bytes() for n in PATCHED}
 base.require(base.sha(base.lf(originals[FOLDER]))==FOLDER_SHA,'FRESH_FOLDER_SOURCE')
 output=transform(originals);extra=overlays(root)
 base.require(not(stage/RECEIPT).exists(),'FRESH_RECEIPT_EXISTS')
 for n in extra:
  if n!=old.GUARD_IMPL:base.require(not(stage/n).exists(),'FRESH_OVERLAY_EXISTS')
 originals_guard=base.regular(stage/old.GUARD_IMPL).read_bytes()
 receipt=expected(root,prior,originals,output);created=[];changed=[]
 try:
  for n,raw in extra.items():
   if n==old.GUARD_IMPL:continue
   with (stage/n).open('xb') as stream:created.append(stage/n);stream.write(raw)
  for n,raw in output.items():changed.append(n);(stage/n).write_bytes(raw)
  changed.append(old.GUARD_IMPL);(stage/old.GUARD_IMPL).write_bytes(extra[old.GUARD_IMPL])
  unchanged_checkout(root,closure)
  with (stage/RECEIPT).open('xb') as stream:created.append(stage/RECEIPT);stream.write((json.dumps(receipt,indent=2,sort_keys=True)+'\n').encode('utf-8'))
  unchanged_checkout(root,closure)
 except BaseException:
  for n in changed:
   try:(stage/n).write_bytes(originals_guard if n==old.GUARD_IMPL else originals[n])
   except OSError:pass
  for p in reversed(created):
   try:p.unlink()
   except OSError:pass
  raise
 return receipt

def portable(value):
 result=dict(value);inline=value.get('inline_producer_sha256');base.require(type(inline) is dict,'FRESH_INLINE')
 normalized={}
 for n,digest in inline.items():
  base.require(type(n) is str and ('\\' not in n or '/' not in n),'FRESH_INLINE_PATH');name=n.replace('\\','/')
  base.require(name not in normalized,'FRESH_INLINE_DUPLICATE');normalized[name]=digest
 result['inline_producer_sha256']=normalized;return result

def decode(raw):
 base.require(type(raw) is bytes and len(raw)<=8*1024**2,'FRESH_JSON_SIZE')
 def pairs(items):
  result={}
  for k,v in items:
   base.require(k not in result,'FRESH_JSON_DUPLICATE');result[k]=v
  return result
 result=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:base.require(False,'FRESH_JSON_FINITE'))
 base.require(type(result) is dict,'FRESH_JSON_OBJECT');return result

def verify_bytes(root,read,all_inherited=False):
 """Reconstruct both roles from pinned original bytes, without executing either."""
 prior=decode(read(old.RECEIPT))
 startup=decode(read(old.PRIOR));base.require(base.json_equal(startup,base.expected_prior(root,startup)),'FRESH_PRIOR')
 init=base.lf(read(base.INIT));base.require(init.count(CALL)==2,'FRESH_INSTALL_VERIFY')
 init=once(init,SEAL,b'','FRESH_SEAL_VERIFY');init=once(init,SEAL_PROTO,b'','FRESH_SEAL_PROTO_VERIFY');init=init.replace(CALL,b'coh_source_catalog_export_startup')
 init=once(init,base.HOOK,b'','FRESH_INIT_HOOK_VERIFY');init=once(init,base.PROTOTYPE,b'','FRESH_INIT_PROTO_VERIFY')
 anim=read(old.GUARD);tail=base.restore_newlines(old.resources.GUARD_TAIL,anim);base.require(anim.endswith(tail),'FRESH_GUARD_TAIL')
 group=read(base.GROUP)
 originals={base.GROUP:base.restore_newlines(base.lf(base.regular(root/'upstream/ouroboros'/base.GROUP).read_bytes()),group),
 base.INIT:base.restore_newlines(init,read(base.INIT)),old.GUARD:anim[:-len(tail)]}
 old_output=old.transform(originals[base.GROUP],originals[base.INIT],originals[old.GUARD])
 base.require(base.json_equal(portable(prior),portable(old.expected(root,startup,originals,old_output))),'FRESH_OLD_RECEIPT')
 # Portable metadata emitted by Path on Windows uses backslashes in inline map.
 inherited_originals={**originals,FOLDER:base.restore_newlines(base.lf(base.regular(root/'upstream/ouroboros'/FOLDER).read_bytes()),read(FOLDER))}
 for n,digest in base.inherited_hashes(startup).items():
  if n in inherited_originals or all_inherited:base.require(base.sha(inherited_originals[n] if n in inherited_originals else read(n))==digest,'FRESH_INHERITED')
 original={**old_output,FOLDER:inherited_originals[FOLDER]}
 output=transform(original);receipt=expected(root,prior,original,output)
 base.require(all(read(n)==raw for n,raw in output.items()),'FRESH_PATCHED')
 base.require(base.json_equal(decode(read(RECEIPT)),receipt),'FRESH_RECEIPT')
 extra=overlays(root)
 for n,raw in {**old.overlays(root),**extra}.items():base.require(read(n)==raw,'FRESH_OVERLAY')
 return receipt

def verify_staged(root,stage):
 root,stage=base.private_stage(root,stage);closure=checkout_closure(root)
 result=verify_bytes(root,lambda n:base.regular(stage/n).read_bytes(),all_inherited=True)
 unchanged_checkout(root,closure);return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--already-staged',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args()
 r=(verify_staged if a.verify else prepare)(a.source_root,a.already_staged)
 print(json.dumps({'passed':True,'build_role':r['build_role'],'runtime_executed':False,'receipt':RECEIPT}))
if __name__=='__main__':main()
