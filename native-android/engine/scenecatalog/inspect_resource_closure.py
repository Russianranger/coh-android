#!/usr/bin/env python3
"""Read-only native graph/resource closure using separately authenticated source inputs."""
from pathlib import Path
import hashlib,json,subprocess,sys,importlib.util,collections,os,argparse,tempfile
parser=argparse.ArgumentParser(description="Read-only actual source resource/root closure; no assets admitted")
parser.add_argument("--source-root",type=Path,required=True)
parser.add_argument("--capture-directory",type=Path,required=True)
parser.add_argument("--binding-sha256",required=True)
parser.add_argument("--output",type=Path,required=True)
a=parser.parse_args()
if a.output.exists():raise ValueError("New output required")
work=tempfile.TemporaryDirectory(prefix="coh-source-resource-closure-");temporary=Path(work.name)
root=a.source_root.resolve();eng=root/'native-android/engine';here=eng/'scenecatalog';cap=a.capture_directory.resolve()
sys.path.insert(0,str(eng/'scenecatalog-server'));import capture_resources
binding=json.loads((cap/'resource-binding.json').read_text());receipt=json.loads((cap/'capture-receipt.json').read_text())
if hashlib.sha256((cap/'resource-binding.json').read_bytes()).hexdigest()!=a.binding_sha256:raise ValueError('Trusted binding digest differs')
if capture_resources.build_binding(cap,receipt,binding['asset_generation'])!=binding:raise ValueError('Capture binding validation differs')
source=(here/'validate_resource_join.c').read_text();needle=' done:\n';assert source.count(needle)==1
emit='''
    if(status==COH_OK){const CohResourceSource *sources=NULL;size_t count=0;CohResourceBinding rb; if(coh_resource_join_sources(join,&sources,&count,&rb)!=COH_OK)return 3;
      for(uint32_t k=0;k<count;k++){uint32_t index;CohRuntimeGraphNode n;CohResourceView v;if(coh_resource_join_node(join,k,&index)!=COH_OK||coh_runtime_graph_node(graph,index,&n)!=COH_OK||coh_resource_source_view(sources[k].record,rb.asset_generation,&v)!=COH_OK)return 3;
        printf("ROW\\t%u\\t%u\\t%u\\t%u\\t%u\\t%u\\t%u\\t%u\\t%u\\t%u\\n",k,index,n.reachable,n.child_count,n.source_model_present,n.empty_owned_future,v.model_present,v.geo_version,v.gld_loadstate,v.model_loadstate);
      }
    }
'''
path=temporary/'closure.c';path.write_text(source.replace(needle,emit+needle))
sources=[path,here/'coh_resource_join.c',here/'coh_resource_index.c',here/'coh_catalog_snapshot.c',here/'coh_catalog_owner.c',here/'coh_scenecatalog.c',eng/'scenegraph/runtime_snapshot.c',eng/'scenegraph/tests/runtime_matrix_bridge.c',eng/'replication/coh_replication.c',eng/'replication/coh_groups.c',eng/'assets/coh_asset_loader.c',eng/'assets/coh_asset_geo.c',root/'native-android/src/coh_assets.c',root/'native-android/src/coh_dds.c']
dependency_paths=sources[1:]+[here/'validate_resource_join.c',eng/'scenecatalog-server/resource_oracle.py',eng/'scenecatalog-server/capture_resources.py',root/'upstream/ouroboros/Common/seq/anim.h']
dependency_paths+=list(here.glob('*.h'))+list((eng/'scenegraph').glob('*.h'))+[eng/'scenegraph/coh_scenegraph.c',eng/'assets/coh_asset_geo.h',eng/'assets/coh_asset_loader.h',eng/'replication/coh_replication.h',eng/'replication/coh_groups.h',eng/'coh_contracts.h',root/'native-android/include/coh_native_core.h']
pins={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dependency_paths}
subprocess.run(['cc','-O2','-std=c99','-Wall','-Wextra','-Werror','-pedantic','-I'+str(root/'native-android/include'),'-I'+str(here),*map(str,sources),'-lcrypto','-lz','-lm','-o',str(temporary/'closure')],check=True)
binding=json.loads((cap/'resource-binding.json').read_text());identity=json.loads((cap/'source-identity.json').read_text())
args=[cap/'catalog.cohcat',cap/'runtime.cohrts',cap/'resources.cohres',binding['source_identity']['sha256'],binding['run_identity']['sha256'],identity['runtime_inventory']['ordered_inventory_sha256'],binding['snapshot']['sha256'],binding['resources']['sha256'],hashlib.sha256((cap/'resource-binding.json').read_bytes()).hexdigest()]
p=subprocess.run([str(temporary/'closure'),*map(str,args)],check=True,capture_output=True,text=True);lines=p.stdout.splitlines(); native=json.loads(lines[-1]);rows=[list(map(int,line.split('\t')[1:])) for line in lines[:-1]];assert len(rows)==40232
spec=importlib.util.spec_from_file_location('oracle',eng/'scenecatalog-server/resource_oracle.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);resources=m.decode((cap/'resources.cohres').read_bytes());assert len(resources)==len(rows)
result={'schema':1,'passed':True,'scope':'Independent actual captured source graph closure; no GEO assets decoded or admitted','native_join':native,'capture_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in cap.glob('*') if p.name in ['catalog.cohcat','runtime.cohrts','resources.cohres','resource-binding.json','source-identity.json','run-identity.json']},'generated_native_source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source_sha256':pins,'partitions':{},'future_objects':[],'missing_original_geometry_observations':[]}
for label,select in [('all',lambda n:True),('reachable',lambda n:bool(n[2])),('unreachable',lambda n:not n[2])]:
 pairs=[(n,r) for n,r in zip(rows,resources) if select(n)];fmt=collections.Counter();no=collections.Counter();geos=set();models=set();textures=set();partitions=0;tricks=set();states=collections.Counter()
 for n,r in pairs:
  if n[4]!=n[6]:result['missing_original_geometry_observations'].append(r)
  if r['model_present']:
   fmt[str(r['format'])]+=1;geos.add(r['strings'][2]);models.add((r['strings'][2],r['strings'][1]));partitions+=len(r['textures']);textures.update(t[2] for t in r['textures']);states[str((n[8],n[9]))]+=1
   if r['strings'][3]:tricks.add(r['strings'][3])
  else:no['empty_owned_future' if n[5] else 'group_with_children' if n[3] else 'regular_leaf_no_geometry']+=1
 result['partitions'][label]={'rows':len(pairs),'model_references':sum(r['model_present'] for n,r in pairs),'no_model_classification':dict(no),'unique_exact_geo_names':len(geos),'unique_geo_model_pairs':len(models),'observed_texture_partitions':partitions,'unique_observed_texture_names':len(textures),'unique_observed_trick_names':len(tricks),'geo_format_model_counts':dict(fmt),'gld_model_loadstate_pairs':dict(states)}
for n,r in zip(rows,resources):
 if r['owner_kind']==2:result['future_objects'].append({'ordinal':r['slot'],'original_id':r['original_id'],'name':r['strings'][0],'reachable':bool(n[2]),'empty_owned_future':bool(n[5]),'model_present':r['model_present'],'library_observation':r['strings'][5]})
result['reachable_model_ordinals']=[n[0] for n,r in zip(rows,resources) if n[2] and r['model_present']]
result['reachable_exact_geo_names']=sorted({r['strings'][2] for n,r in zip(rows,resources) if n[2] and r['model_present']})
result['remaining_dependencies']=['Exact source GEO-name to authenticated manifest loader identity mapping and authentic GEO bytes for each required reachable model','Original sorted runtime model row to unique raw disk row admission with GEO/material partition checks','Effective CLIENT TexBind/BasicTexture trick/swap/capability/material and LOD closure (SERVER capture cannot supply)','Matching live GROUPS generation plus authoritative selected-character transaction before world publication']
if capture_resources.build_binding(cap,receipt,binding['asset_generation'])!=binding:raise ValueError('Capture changed during native inspection')
if pins!={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in dependency_paths}:raise ValueError('Native sources changed during inspection')
result['inspector_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
result['source_loadstate_semantics']={'gld_1':'original NOT_LOADED flag (header stubs)','model_0':'no model LOADED flag observed','source':'upstream/ouroboros/Common/seq/anim.h'}
result['interpretation']='No-model regular rows are original group containers, not missing geometry observations. Header model/GEO identities do not imply decoded assets, effective CLIENT materials or LOD.'
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
work.cleanup()
print(json.dumps(result['partitions'],indent=2));print(json.dumps(result['future_objects'],indent=2))
