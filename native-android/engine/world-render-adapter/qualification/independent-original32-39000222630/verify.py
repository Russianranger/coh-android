#!/usr/bin/env python3
"""Read-only retained ELF32 artifact/source/scalar check; never executes binary."""
import argparse,hashlib,json,re,struct,subprocess,zipfile
from pathlib import Path
SHA='2f1a723d634f03bbcc3be08399baeb3e1ea65f43230e583ad3493ae7d3581972'
COMMIT='279650a6cda9d05c04678a98459a5ba5e1e7efcf'
def sha(b):return hashlib.sha256(b).hexdigest()
def verify(archive,repo):
 raw=archive.read_bytes();assert len(raw)==12664 and sha(raw)==SHA
 with zipfile.ZipFile(archive)as z:
  assert z.testzip()is None
  files={name:z.read(name)for name in z.namelist()}
 q=json.loads(files['qualification.json']);assert q['source_revision']==COMMIT and q['passed']is True and q['original32_required']is True
 for name,want in q['source_sha256'].items():assert sha(subprocess.check_output(['git','-C',str(repo),'show',COMMIT+':'+name]))==want
 c=files['original32/original-read-model.c'].decode();m=q['original_readModel'];assert sha(c.encode())==m['generated_oracle_sha256']
 original=subprocess.check_output(['git','-C',str(repo),'show',COMMIT+':upstream/ouroboros/Common/seq/anim.c']).decode().replace('\r\n','\n')
 start=original.index('static int readModel(');end=original.index('{',start)+1;depth=1
 while depth:depth+=(original[end]=='{')-(original[end]=='}');end+=1
 function=original[start:end];assert c.count(function)==1 and sha(function.encode())==m['unchanged_readModel_sha256_lf']
 binary=files['original32/original-read-model'];assert sha(binary)==m['binary_sha256'] and binary[:6]==b'\x7fELF\x01\x01' and struct.unpack_from('<HH',binary,16)==(2,3)
 assert m['original_consumer_executed']is m['true32bit_freestanding_linux_execution']is True and m['execution_refusal']is None
 r=bytes(map(int,re.search(r'static U8 record\[\].*?=\{([^}]*)\}',c).group(1).split(',')))
 assert len(r)==216
 word=lambda offset:struct.unpack_from('<I',r,offset)[0]
 expected=[216,216,word(0),word(4),word(12),word(28),word(32),word(20),word(84),word(40),word(80),word(36),struct.unpack_from('<h',r,16)[0]&0xffffffff,*struct.unpack_from('<9I',r,92)]
 packs=[(0,0,0)]*10
 for source,target in enumerate((0,1,2,3,5,6,7)):packs[target]=struct.unpack_from('<3I',r,132+12*source)
 expected+=sum((list(x)for x in packs),[])
 assert list(struct.unpack('<52I',files['original32/execution.stdout']))==expected
 assert not files['original32/execution.stderr']
 assert list(struct.unpack('<14I',files['original32/original-layout.bin']))==m['source_layout_offsets']==[216,0,4,12,20,28,32,36,40,80,84,88,92,132]
 assert all(row['passed']is True and row['checks']==243 for row in q['modes'].values())
 acq=json.loads(files['neon-acquisition.json']);assert acq['passed']is True and len(acq['records'])==1
 assert acq['records'][0]['sha256']=='83933b54db373bf83e0a73f128068b63b8375e00f0f288b6f6e0e0637792c9e7' and acq['records'][0]['bytes']==3684
 return {'passed':True,'source_commit':COMMIT,'source_inputs':len(q['source_sha256']),'layout_scalars':14,'metadata_pack_scalars':52,'binary_reexecuted':False,'world_authority':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.archive,a.repo)))
