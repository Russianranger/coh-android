#!/usr/bin/env python3
"""Exact binary32 source-world evaluation-order regression for Phase9.

Uses actual frozen world vertices and source matrices, not synthetic replacement
geometry. CI needs --world/--reference; --apk supports package auditing. An
optional original failed Thor report verifies the recorded observation. Without
that report, the known failure pattern is explicitly a regression input rather
than newly captured GPU output. The script neither executes a GPU nor changes
source arithmetic, references, or the established 1e-4 transform tolerance.
"""
from pathlib import Path
from fractions import Fraction
from itertools import permutations
import argparse,hashlib,json,math,struct,zipfile
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apk',type=Path,help='APK containing the frozen Phase9 world assets')
parser.add_argument('--world',type=Path,help='Alternative direct world.bin input')
parser.add_argument('--reference',type=Path,help='world-reference.bin paired with --world')
parser.add_argument('--report',type=Path,help='Optional original failed Thor report; not required by CI')
parser.add_argument('--output',required=True,type=Path)
a=parser.parse_args()
if a.apk is not None and (a.world is not None or a.reference is not None):parser.error('Choose --apk or --world with --reference')
if a.apk is None and (a.world is None or a.reference is None):parser.error('--apk or both --world and --reference are required')
OUT=a.output
RECORDED_REPORT_SHA256='d1bd54431dbfd4a3df15323c4c120349e7fad6b9d2f789c376d3ddc6cc94705d'
WORLD_SHA256='7289eb3a4478648dcefce682121ccd0448aee6a21a7c4977ffd6415dd11ece6f'
REFERENCE_SHA256='6479217ee8b78bc48cef400a94c150b03addfecd6c8a00f8ab5a2e6258fd0b13'
sha=lambda b:hashlib.sha256(b).hexdigest()
def bits(x):return struct.unpack('<I',struct.pack('<f',x))[0]
def value(b):return struct.unpack('<f',struct.pack('<I',b))[0]
def q(x):return Fraction.from_float(float(x))
def nearest32(exact):
 approx=bits(float(exact));candidates=[]
 for b in range(max(0,approx-2),min(0xffffffff,approx+2)+1):
  v=value(b)
  if math.isfinite(v):candidates.append((abs(q(v)-exact),b&1,b,v))
 return min(candidates)[3]
def mul(x,y):return nearest32(q(x)*q(y))
def add(x,y):return nearest32(q(x)+q(y))
def fma(x,y,z):return nearest32(q(x)*q(y)+q(z))
def source(v,m,c):
 a=[mul(v[j],m[j*3+c]) for j in range(3)]
 return add(add(add(a[0],a[1]),a[2]),m[9+c])
def pairwise(v,m,c):
 a=[mul(v[j],m[j*3+c]) for j in range(3)]
 return add(add(a[0],a[1]),add(a[2],m[9+c]))
def translationfirst(v,m,c):
 a=[mul(v[j],m[j*3+c]) for j in range(3)]
 return add(add(add(m[9+c],a[2]),a[1]),a[0])
def dotonce(v,m,c):return nearest32(sum([q(v[j])*q(m[j*3+c]) for j in range(3)]+[q(m[9+c])]))
def nested(v,m,c,order):
 accumulator=m[9+c]
 for j in order:accumulator=fma(v[j],m[j*3+c],accumulator)
 return accumulator
if a.apk:
 with zipfile.ZipFile(a.apk) as z:
  assert z.getinfo('assets/world.bin').file_size==102176 and z.getinfo('assets/world-reference.bin').file_size==161344
  world=z.read('assets/world.bin');reference=z.read('assets/world-reference.bin')
else:
 assert a.world.stat().st_size==102176 and a.reference.stat().st_size==161344
 world=a.world.read_bytes();reference=a.reference.read_bytes()
assert len(world)==102176 and sha(world)==WORLD_SHA256
assert len(reference)==161344 and sha(reference)==REFERENCE_SHA256
assert world[:8]==b'COHWOR09' and reference[:8]==b'COHWRF09'
assert list(struct.unpack_from('<12I',reference,8))==[1,64,6,6,512,2,64,352,640,26784,161344,160]
model=list(struct.unpack_from('<12f',reference,352+5*48));mesh=struct.unpack_from('<I',world,128)[0];vo=struct.unpack_from('<I',world,mesh+32)[0];vertices=[struct.unpack_from('<3f',world,mesh+vo+i*48) for i in range(256)]
expected=[struct.unpack_from('<3f',reference,640+160+i*52) for i in range(256)]
for i,v in enumerate(vertices):assert [source(v,model,c) for c in range(3)]==list(expected[i])
runs=[]
witness={'camera':0,'part':0,'vertex':8,'component':2,'expected':-1439.9266357421875,'actual':-1439.9267578125}
if a.report:
 report=json.loads(a.report.read_text());assert report['schema']=='coh-native-world-probe-v1'
 for name,digest in [('world.bin',WORLD_SHA256),('world-reference.bin',REFERENCE_SHA256)]:assert report['fixture']['assets'][name]['sha256']==digest
 runs=[r for r in report['native_runs'] if not r['obsolete']]
 assert runs
 for run in runs:
  assert not run['passed'];cycle=run['native']['cycles'][0]
  assert cycle['transform_vertices']==256 and cycle['transform_components']==3328
  assert cycle['world_position_mismatches']==88 and cycle['transform_mismatches']==88
  assert cycle['eye_position_mismatches']==cycle['normal_mismatches']==cycle['clip_mismatches']==0
  current=cycle['first_transform_mismatch'];assert current['observed']
  assert all(current[k]==witness[k] for k in ['camera','part','vertex','component'])
  assert bits(current['expected'])==bits(witness['expected']) and bits(current['actual'])==bits(witness['actual'])
observed=value(bits(witness['actual']));recorded_expected=value(bits(witness['expected']));assert recorded_expected==expected[8][2]
models={'strict_source_separate_mul_left_associative_add':source,'rounded_products_pairwise_addition':pairwise,'rounded_products_translation_then_z_then_y_then_x':translationfirst,'exact_dot_single_rounding':dotonce}
for order in permutations(range(3)):models['FMA_translation_then_'+'_'.join('xyz'[j] for j in order)]=lambda v,m,c,order=order:nested(v,m,c,order)
results={}
for name,fn in models.items():
 mismatches=[];changed=[];errors=[]
 for i,v in enumerate(vertices):
  for c in range(3):
   actual=fn(v,model,c);error=abs(actual-expected[i][c]);errors.append(error)
   if error:changed.append((i,c))
   if error>1e-4:mismatches.append((i,c))
 results[name]={'first_witness_value':fn(vertices[8],model,2),'first_witness_hex_bits':f'0x{bits(fn(vertices[8],model,2)):08x}','matches_first_observed':fn(vertices[8],model,2)==observed,'mismatches_above_existing_1e_4':len(mismatches),'mismatch_components':sorted(set(c for _,c in mismatches)),'first_mismatch':list(mismatches[0]) if mismatches else None,'maximum_absolute_error':max(errors),'changed_components_below_or_above_tolerance':len(changed),'matches_recorded_aggregate_pattern':len(mismatches)==88 and set(c for _,c in mismatches)=={2} and max(errors)==0.0001220703125 and fn(vertices[8],model,2)==observed}
v=vertices[8];products=[mul(v[j],model[j*3+2]) for j in range(3)];z_plus_translation=q(products[2])+q(model[11]);source_partial=add(add(products[0],products[1]),products[2]);exact_affine=sum([q(v[j])*q(model[j*3+2]) for j in range(3)]+[q(model[11])]);
receipt={'schema':'coh-phase9-adreno-world-rounding-diagnostic-v1','passed':True,'diagnostic_only':True,'input_sha256':{'thor_report':sha(a.report.read_bytes()) if a.report else None,'apk':sha(a.apk.read_bytes()) if a.apk else None,'world.bin':sha(world),'world-reference.bin':sha(reference)},'scope':'First source part, first controlled camera; exact IEEE binary32 arithmetic models reproduce recorded first witness plus aggregate threshold count. GPU instruction ordering is inferred, not captured.','arithmetic':'All modeled product/add/fma roundings use exact rational arithmetic and binary32 round-to-nearest ties-to-even; no epsilon or tolerance change.','observed':{'current_failed_runs':len(runs) if a.report else None,'observation_source':'supplied failed Thor report' if a.report else 'fixed regression pattern from prior validated Thor report','recorded_report_sha256':RECORDED_REPORT_SHA256,'gpu_executed_by_this_script':False,'first_camera':0,'first_part':0,'vertices_compared':256,'tf_components_compared':3328,'world_position_mismatches':88,'eye_normal_clip_mismatches':0,'maximum_error_binary32_exact':0.0001220703125,'first_vertex':8,'component':2,'expected':recorded_expected,'actual':observed,'expected_bits':f'0x{bits(recorded_expected):08x}','actual_bits':f'0x{bits(observed):08x}','existing_absolute_tolerance':1e-4},'world_matrix_source_columns':model,'first_source_vertex':list(v),'first_witness_detail':{'z_products':products,'translation_z':model[11],'source_partial_before_translation':source_partial,'z_product_plus_translation_exact':float(z_plus_translation),'z_product_plus_translation_is_midpoint':z_plus_translation==(q(recorded_expected)+q(observed))/2,'exact_affine_value':float(exact_affine),'tiny_x_contribution':products[0],'strict_source_result':source(v,model,2),'pairwise_result':pairwise(v,model,2),'fully_fused_result':dotonce(v,model,2),'ulp_at_coordinate':0.0001220703125},'models':results,'conclusions':['Strict source product/add order reproduces every frozen first-part world reference exactly.','The large translation plus z product lies exactly halfway between adjacent binary32 world coordinates for the first witness.','Adding the tiny x-rotation contribution before translation selects the expected neighbor; rounding translation+z first loses that contribution and reproduces the observed neighbor.','Several reassociated/FMA instruction-order models reproduce the recorded aggregate count of 88 threshold mismatches, world-z-only classification, first vertex 8 and exact one-ULP maximum. This identifies a numeric-order mechanism without asserting captured Adreno instructions or complete measured GPU vertex values.','A single fully fused dot returns the source result for the first witness; the issue is evaluation grouping and intermediate rounding, not all FMA use.'],'recommended_remedy':'Keep source input coordinates, source CPU matrix order, references and 1e-4 tolerance unchanged. Use explicitly staged binary32 component products and left-associative additions under an ESSL precise/no-contraction contract supported by the selected device/shader profile, then rerun independent GPU transform/pixel/lifecycle qualification. Mere temporaries without precision/optimization constraints do not establish evaluation order.','device_qualification':'failed until corrected shader reruns on Thor; source host and prior emulator evidence remain separate'}
assert results['strict_source_separate_mul_left_associative_add']['mismatches_above_existing_1e_4']==0
assert results['rounded_products_pairwise_addition']['matches_recorded_aggregate_pattern']
assert results['rounded_products_translation_then_z_then_y_then_x']['matches_recorded_aggregate_pattern']
assert all(results['FMA_translation_then_'+'_'.join('xyz'[j] for j in order)]['matches_recorded_aggregate_pattern'] for order in permutations(range(3)))
assert results['exact_dot_single_rounding']['mismatches_above_existing_1e_4']==3
assert z_plus_translation==(q(recorded_expected)+q(observed))/2
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({'receipt':str(OUT),'first_witness':receipt['first_witness_detail'],'models_matching_observed_aggregate':[n for n,v in results.items() if v['matches_recorded_aggregate_pattern']],'all_models_summary':{n:{k:v[k] for k in ['first_witness_value','mismatches_above_existing_1e_4','maximum_absolute_error']} for n,v in results.items()}}))
