import hashlib,json,os,pathlib,subprocess,tarfile,tempfile
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[4];NET=ROOT/'native-android/engine/network';OUT=HERE/'reproduced';SRC=NET/'diagnostics/worker-c-fragment-20261019'
def sha(v):return hashlib.sha256(v).hexdigest()
def run(args):return subprocess.run(list(map(str,args)),capture_output=True)
def rec(p):d=p.read_bytes();return {'bytes':len(d),'sha256':sha(d)}
def main():
 OUT.mkdir(parents=True,exist_ok=False)
 proof=json.loads((SRC/'qualification.json').read_bytes());assert proof['passed']
 pin_fail=[]
 for p,v in proof['source_sha256'].items():
  if sha((ROOT/p).read_bytes())!=v:pin_fail.append(p)
 assert not pin_fail
 archive=SRC/'executed-proof.tar.gz';assert rec(archive)==proof['executed_proof']
 header={'upstream/ouroboros/libs/UtilitiesLib/src/components/MemoryPool.c':'initMemoryPoolOffset sets Default, mpAlloc_dbg zeroes pool->structSize when zeroMemory set','upstream/ouroboros/libs/UtilitiesLib/include/utilitieslib/components/MemoryPool.h':'Default = ZERO_MEMORY_BIT','upstream/ouroboros/libs/UtilitiesLib/src/network/net_packet.c':'PacketMemoryPool keeps Default; pktCreateImp uses mpAlloc(PacketMemoryPool); pktMakeCompatible copies flags, not ordered_id','upstream/ouroboros/libs/UtilitiesLib/src/network/netio_send.c':'pktSendDbg splits stream.size >= maxPacketDataSize and passes i!=0 into lnkAddToSendQueue','upstream/ouroboros/libs/UtilitiesLib/src/network/netio_core.c':'lnkAddToSendQueue assigns ordered_id only !sibling_packet; pktWrap writes zero when ordered; mergeSibs sorts and copies part0 ordered_id'}
 original={p:{**rec(ROOT/p),'facts':text} for p,text in header.items()}
 net=(NET/'coh_net.c').read_bytes();frame=(NET/'coh_net_frame.c').read_bytes();mutants=[('reject-single-sibling',None,(b'p->sibling_count>COH_NET_FRAGMENT_MAX||',b'p->sibling_count<2||p->sibling_count>COH_NET_FRAGMENT_MAX||')),('reject-zero-continuation',None,(b'(!p->ordered_id&&(!p->sibling_count||!p->sibling_part))',b'!p->ordered_id')),('require-identical-fragment-order', (b'(g->parts[i].ordered_id&&p->ordered_id&&g->parts[i].ordered_id!=p->ordered_id)',b'g->parts[i].ordered_id!=p->ordered_id'),None),('use-last-arriving-order', (b';m.ordered_id=g->parts[0].ordered_id',b''),None)]
 results={}
 with tempfile.TemporaryDirectory(prefix='coh-f-fragments-') as t:
  work=pathlib.Path(t)
  with tarfile.open(archive,'r:gz') as tar:
   item=tar.getmember('fragment_goldens.h');(work/'fragment_goldens.h').write_bytes(tar.extractfile(item).read())
  includes=['-I'+str(NET),'-I'+str(ROOT/'native-android/protocol'),'-I'+str(ROOT/'native-android/include'),'-I'+str(work)]
  base=[NET/'coh_net_zip.c',ROOT/'native-android/protocol/coh_protocol.c',ROOT/'native-android/src/coh_blowfish.c',NET/'tests/test_fragment_compat.c']
  objs=[]
  for i,p in enumerate(base):
   obj=work/('base'+str(i)+'.o');build=run(['cc','-std=c99','-O0','-g',*includes,'-c',p,'-o',obj]);assert build.returncode==0,build.stderr;objs.append(obj)
  for name,nm,fm in mutants:
   n=net;f=frame
   if nm:assert n.count(nm[0])==1;n=n.replace(*nm)
   if fm:assert f.count(fm[0])==1;f=f.replace(*fm)
   np=work/(name+'-net.c');fp=work/(name+'-frame.c');np.write_bytes(n);fp.write_bytes(f)
   binary=work/name;build=run(['cc','-std=c99','-O0','-g',*includes,np,fp,*objs,'-lz','-o',binary]);assert build.returncode==0,build.stderr
   test=run([binary]);assert test.returncode!=0 and b'FAIL ' in test.stderr
   (OUT/(name+'.stderr')).write_bytes(test.stderr)
   results[name]={'runtime_returncode':test.returncode,'expected_assertion_refusal':True,'stderr_sha256':sha(test.stderr),'binary':rec(binary),'mutated_net_sha256':sha(n),'mutated_frame_sha256':sha(f)}
 result={'schema':'coh-independent-fragment-review-v1','passed':True,'reviewed_proof':rec(SRC/'qualification.json'),'source_pins_verified':len(proof['source_sha256']),'archive_hash_verified':True,'original_source_facts':original,'mutation_refusals':results,'review':'All three edits match exact original source behavior: one-sibling exact-size split, later ordered siblings zero ID, complete message metadata from part zero. Existing repeated same nonzero IDs remain valid; mismatched nonzero IDs still refuse. Existing bounded fragments, reassembly, timeout, owned-message release and authority policies remain.','bounds_unchanged':proof['unchanged_limits'],'allocation_owner_changes':False,'original_server_transaction_executed':False,'android_execution_or_Thor_qualification':False,'whole_process_memory_measured':False,'transport_ACK_is_application_ACK':False,'gates25_27':'OPEN'}
 (OUT/'review.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps({'passed':True,'mutation_refusals':len(results),'source_pins':len(proof['source_sha256'])}))
if __name__=='__main__':main()
