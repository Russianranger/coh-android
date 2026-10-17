#!/usr/bin/env python3
"""Bounded independent aggregate consistency check for source CPU sweep results."""
import argparse,hashlib,json,zlib
from pathlib import Path
COVERAGE_SHA='5df9bc58cb49c9a177a8315a841701bd300dbdf6641d27ef0b81345f1f6be197'
def inspect(receipt_path,ledger_path,coverage_path,special_path):
 for path,limit in ((receipt_path,256<<10),(ledger_path,2<<20),(coverage_path,4<<20),(special_path,32<<10)):
  if path.stat().st_size>limit:raise ValueError('bounded proof input')
 receipt=json.loads(receipt_path.read_text());raw=ledger_path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=receipt['ledger_sha256']:raise ValueError('compressed ledger digest')
 inflater=zlib.decompressobj();decoded=inflater.decompress(raw,4<<20)
 if not inflater.eof or inflater.unused_data or inflater.unconsumed_tail or len(decoded)>3<<20:raise ValueError('bounded complete ledger stream')
 if hashlib.sha256(decoded).hexdigest()!=receipt['ledger_decoded_sha256']:raise ValueError('decoded ledger digest')
 if hashlib.sha256(coverage_path.read_bytes()).hexdigest()!=COVERAGE_SHA:raise ValueError('qualified root closure')
 data=json.loads(decoded)
 if any(receipt.get(key) is not False for key in ('world_authority','client_materials_available','direct_open_observed','android_executed','original32_readModel_executed')):raise ValueError('scope flags cannot be promoted')
 scope=data['scope']
 if scope.get('world_authority') is not False or scope.get('assets_admitted') is not False or scope.get('fixture_materials_only') is not True or scope.get('not_transfer_bridge_test') is not True:raise ValueError('diagnostic fixture-only scope')
 if set(receipt['modes'])!={'release','asan','ubsan'}:raise ValueError('three qualified native modes')
 for mode in receipt['modes'].values():
  summary=mode['summary']
  if not summary['complete'] or summary['completed_pairs']!=2916 or summary['files']!=391 or summary['successes']!=2907 or summary['specials']!=9 or summary['deadline_stopped'] or summary['world_authority'] or not summary['fixture_materials_only']:raise ValueError('qualified mode closure')
 models=json.loads(coverage_path.read_text())['models'];special=json.loads(special_path.read_text());expected={r['ordinal']:r for r in special};observed={}
 if not receipt['passed'] or not receipt['complete'] or len(data['pairs'])!=2916 or len(data['files'])!=391 or len(data['cleanup'])!=391:raise ValueError('complete finite closure')
 owners=[];packets=0;scalars=0;successes=0;maximum=0
 for i,row in enumerate(data['pairs']):
  model=models[i];meta=model['metadata'];identities=model['source_ordinals'];owners+=identities
  if row['i']!=i or row['owners']!=identities or row['ordinal']!=identities[0] or row['phase']!='cpu' or row['model']!=meta['name'] or row['version']!=meta['version']:raise ValueError('exact actual pair identity')
  if row['ordinal'] in expected:
   r=expected[row['ordinal']]
   if row['status']!=2 or row['aux_status'] or row['aux_kinds']!=r['kinds'] or row['quad_count']!=r['quads'] or row['pivot_count']!=r['pivots'] or row['quad_sha256']!=r['points_sha256'] or row['pivot_sha256']!=r['pivots_sha256']:raise ValueError('special row preserved with exact supplemental data')
   observed[row['ordinal']]=True
  else:
   if row['status'] or row['aux_kinds'] or row['vertices']!=meta['vertices'] or row['triangles']!=meta['triangles'] or row['parts']!=meta['parts']:raise ValueError('actual ordinary CPU preparation')
   if row['packet_bytes']!=meta['vertices']*meta['parts']*56+meta['triangles']*12:raise ValueError('complete per-part CPU packet size')
   successes+=1;packets+=row['packet_bytes'];scalars+=meta['vertices']*8+meta['triangles']*3
  maximum=max(maximum,row['cpu_peak'],row['aux_peak'])
 if len(owners)!=3083 or len(set(owners))!=3083 or observed.keys()!=expected.keys() or successes!=2907:raise ValueError('complete source owner coverage')
 if len({f['file'] for f in data['files']})!=391 or {f['file'] for f in data['files']}!={c['file'] for c in data['cleanup']}:raise ValueError('unique paired file cleanup')
 if any(f['status'] for f in data['files']) or any(c['pinned_blobs'] for c in data['cleanup']):raise ValueError('owned-file admission or cleanup')
 if maximum>96<<20 or any(c['loader_peak']>32<<20 for c in data['cleanup']):raise ValueError('unchanged budgets')
 if receipt['original_delta']['scalars_compared']!=scalars:raise ValueError('original consumer scalar closure')
 if receipt['original_delta']['pairs_compared']!=successes or receipt['original_delta']['packet_bytes_compared']!=packets:raise ValueError('original delta packet comparison closure')
 return {'passed':True,'pairs':2916,'owners':3083,'files':391,'cpu_successes':successes,'specials_preserved':len(expected),'packet_bytes':packets,'named_peak_bytes':maximum,'no_caps_raised':True,'ordinary_world_authority':False}
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('receipt','ledger','root-coverage','special-routes'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();print(json.dumps(inspect(a.receipt,a.ledger,a.root_coverage,a.special_routes),sort_keys=True))
if __name__=='__main__':main()
