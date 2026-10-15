#!/usr/bin/env python3
"""Compile a bounded authored map subset into a runtime semantic index/raw bundle.

The allowlist consists of explicit source RootMod/GEO endpoint identities and
material dependencies, never renderer object IDs. Omitted leaves are reported.
"""
from pathlib import Path
import argparse, collections, hashlib, importlib.util, json, math, shlex, struct
HERE=Path(__file__).resolve().parent;NATIVE=HERE.parents[1]
NO=0xffffffff

def module(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def sha(b):return hashlib.sha256(b).hexdigest()
def require(v,msg):
 if not v:raise ValueError(msg)

def parse_groups(text):
 defs={};refs=[];stack=[];property_count=0
 for lineno,line in enumerate(text.splitlines(),1):
  words=shlex.split(line,comments=True,posix=True)
  if not words:continue
  if words[0].startswith('//'):continue
  tag=words[0].casefold();v=words[1:]
  if tag in ('def','rootmod','ref','group'):
   require(len(v)==1,f'bad declaration line {lineno}')
   node={'kind':tag,'name':v[0],'line':lineno,'pos':[0.,0.,0.],'pyr':[0.,0.,0.],'groups':[],'properties':[],'tint':None}
   if tag in ('def','rootmod'):
    require(not stack,'nested Def');require(v[0].casefold() not in defs,'duplicate Def');defs[v[0].casefold()]=node
   elif tag=='ref':require(not stack,'nested Ref');refs.append(node)
   else:require(stack and stack[-1]['kind'] in ('def','rootmod'),'Group outside Def');stack[-1]['groups'].append(node)
   stack.append(node)
  elif tag=='lod' and not v:
   require(stack and stack[-1]['kind'] in ('def','rootmod'),'Lod outside Def');block={'kind':'lod','properties':[]};stack[-1]['properties'].append(['LodBlock',block]);stack.append(block)
  elif tag=='end':require(len(words)==1 and stack,f'unmatched End line {lineno}: {words}');stack.pop()
  elif stack:
   n=stack[-1]
   if tag in ('pos','pyr','rot'):
    require(len(v)==3,'vector arity');f=[float(x) for x in v];require(all(math.isfinite(x) and abs(x)<=1e6 for x in f),'vector bound');n['pos' if tag=='pos' else 'pyr']=[x*(180/math.pi) for x in f] if tag=='rot' else f
   elif tag=='tintcolor':require(len(v)==6 and n['kind'] in ('def','rootmod'),'bad tint');n['tint']=[int(x) for x in v];require(all(0<=x<=255 for x in n['tint']),'tint range')
   else:n['properties'].append(words);property_count+=1
  else:require(tag in ('version','scenefile','loadscreen','loadscreenpages','includes','include'),'unhandled top-level token '+tag)
 require(not stack,'unterminated declaration')
 return defs,refs,property_count

def index_bytes(nodes,endpoints,assets):
 strings=bytearray();lookup={}
 def string(s):
  require(s and '\0' not in s,'bad string')
  if s not in lookup:lookup[s]=len(strings);strings.extend(s.encode()+b'\0')
  return lookup[s]
 ns=bytearray();es=bytearray();aa=bytearray();deps=[]
 for n in nodes:ns.extend(struct.pack('<4I6f6I',n['parent'],n['endpoint'],string(n['name']),int(n['tint'] is not None),*n['pos'],*n['pyr'],*(n['tint'] or [0]*6)))
 for e in endpoints:
  first=len(deps);deps.extend(e['dependencies']);es.extend(struct.pack('<4I4f2I',e['geometry'],string(e['model']),first,len(e['dependencies']),*e['center'],e['radius'],0,0))
 for a in assets:aa.extend(struct.pack('<2I',string(a['path']),a['generation']))
 no=64;eo=no+len(ns);ao=eo+len(es);dd=ao+len(aa);so=dd+4*len(deps);total=so+len(strings)
 h=struct.pack('<8s14I',b'COHMAP01',1,64,total,len(nodes),len(endpoints),len(assets),len(deps),len(strings),no,eo,ao,dd,so,0)
 require(len(nodes)<=512 and len(endpoints)<=16 and len(assets)<=64 and len(deps)<=256 and len(strings)<=32768,'native index capacity exceeded')
 return h+ns+es+aa+struct.pack('<'+'I'*len(deps),*deps)+strings

def bundle_bytes(index,assets,materials):
 strings=bytearray();lookup={}
 def string(text):
  if text not in lookup:lookup[text]=len(strings);strings.extend(text.encode()+b'\0')
  return lookup[text]
 rows=[];mr=[];so=64+24*len(assets)
 for asset in assets:rows.append([string(asset['path']),asset['generation'],0,len(asset['raw']),0,0])
 for material in materials:
  r=bytearray(128);struct.pack_into('<8I',r,0,string(material['name']),string(material['textures'][0]),string(material['textures'][1]),1,material['family'],material['wrap'][0],material['wrap'][1],material['cull_back']);struct.pack_into('<21f',r,32,*material['uv_scale'][0],*material['uv_scale'][1],*material['const0'],*material['const1'],material['alpha_ref'],*material['diffuse'],*material['ambient']);mr.append(bytes(r))
 ix=so+len(strings);mo=ix+len(index);po=mo+len(mr)*128;offset=po
 for row in rows:row[2]=offset;offset+=row[3]
 return struct.pack('<8s14I',b'COHWB001',1,64,offset,ix,len(index),len(assets),64,so,len(strings),po,len(mr),mo,len(mr)*128,0)+b''.join(struct.pack('<6I',*r) for r in rows)+strings+index+b''.join(mr)+b''.join(asset['raw'] for asset in assets)

def source_materials(source_root,assets,byfile):
 import re
 paths=['upstream/i24/data/tricks/streets/elements/streets_misc.txt','upstream/i24/data/tricks/streets/elements/monorail.txt'];texts=[(source_root/p).read_text() for p in paths]
 pins=[]
 for path in paths:
  raw=(source_root/path).read_bytes();pins.append({'path':path,'bytes':len(raw),'sha256':sha(raw)})
 def block(text,name):
  match=re.search(r'(?ims)^Texture '+re.escape(name)+r'\.tga\s*\n(.*?)^End\s*$',text);require(match is not None,'source material missing '+name);return [x.strip().split() for x in match.group(1).splitlines() if x.strip() and not x.strip().startswith('//')]
 bench=block(texts[0],'modern_bench');require(bench==[['Surface','METAL'],['Blend','white.tga'],['BlendType','ColorBlendDual']],'source bench material differs')
 texpath=lambda file:assets[byfile[file]]['path']
 materials=[]
 for name,base,dual,family,scale in [('modern_bench','bench.texture','white.texture',1,1),('signmetal','sign.texture','grey.texture',0,1),('mono_station_infloor','mono_station_infloor.texture','grey.texture',0,14),('mono_station_infloor_sml','mono_station_infloor_sml.texture','grey.texture',0,8)]:
  if name.startswith('mono_station_infloor'):require(block(texts[1],name)==[['Blend','mono_station_floor_det.tga'],['BlendType','Multiply'],['ScaleST0',str(scale),str(scale)]],'source floor material differs')
  materials.append({'name':name+'.tga','textures':[texpath(base),texpath(dual)],'family':family,'uv_scale':[[scale,scale],[1,1]],'const0':[1,1,1,1],'const1':[0,0,0,1],'wrap':[0,0],'cull_back':1,'alpha_ref':0.,'diffuse':[0.,0.,0.,1.],'ambient':[.125,.125,.125,1.],'lighting_scope':'controlled neutral diffuse=0 ambient=.125; authored Atlas light grids/ambient zones not evaluated'})
 # Reuse previously successful complete source alias and original grey fallback
 # receipts instead of rerunning every original trick/source qualifier.
 receipt_paths=[NATIVE/'evidence/phase9/source-trick-resolution.json',NATIVE/'evidence/phases19-21/source-build-qualified/source-floor-resolution.json']
 receipts=[]
 for path in receipt_paths:
  raw=path.read_bytes();report=json.loads(raw);require(report.get('passed') is True,'prior source material receipt failed');receipts.append({'path':str(path.relative_to(NATIVE)),'bytes':len(raw),'sha256':sha(raw)})
 return materials,pins,receipts

def prepare(source_root,corpus,output):
 output.mkdir(parents=True,exist_ok=True)
 source_path='upstream/i24/data/maps/city_zones/city_01_01/city_01_01_layer_geometry.txt'
 raw=(source_root/source_path).read_bytes();accepted=json.loads((NATIVE/'evidence/phase9/scene-recovery.json').read_text());pin=next(x for x in accepted['source_pins'] if x['path']==source_path);require(len(raw)==pin['bytes'] and sha(raw)==pin['sha256'],'authored map pin differs')
 defs,refs,propcount=parse_groups(raw.decode('utf8'))
 geo=module('map_original_geo_prepare',NATIVE/'tools/world_fixture/geo_prepare.py');floor=module('map_floor_geo_prepare',NATIVE/'tools/walkable_fixture/prepare.py')
 asset_pins=[]
 for p in [NATIVE/'tools/world_fixture/pins.json',NATIVE/'tools/walkable_fixture/pins.json']:asset_pins.extend(json.loads(p.read_text())['records'])
 want=['misc.geo','trainstation.geo','bench.texture','sign.texture','white.texture','grey.texture','mono_station_infloor.texture','mono_station_infloor_sml.texture']
 assets=[];byfile={}
 for file in want:
  p=next(x for x in asset_pins if x['file_name']==file);path=next((r/file for r in corpus if (r/file).exists()),None);require(path is not None,'missing pinned asset '+file);b=path.read_bytes();require(len(b)==p['size'] and sha(b)==p['sha256'],'asset pin differs '+file)
  virtual=p['name'];virtual=virtual.removeprefix('assets/');virtual='data/'+virtual if not virtual.startswith('data/') else virtual
  byfile[file]=len(assets);assets.append({'path':virtual,'generation':1,'raw':b,'source_file':file,'sha256':sha(b),'bytes':len(b)})
 require(len({a['path'].casefold() for a in assets})==len(assets),'asset identity duplicate')
 _,miscdata,miscmodels,_=geo.records(assets[byfile['misc.geo']]['raw']);floordata,floormodels=floor.legacy_records(assets[byfile['trainstation.geo']]['raw'])
 bindings=[];sourcepins=[{'path':source_path,'bytes':len(raw),'sha256':sha(raw)}]
 specs=[('Streets/Elements/misc_sm/modern_bench_2wide','misc.geo','modern_bench_2wide',['bench.texture','sign.texture','white.texture','grey.texture']),('Streets/Elements/misc_sm/modern_bench_4wide','misc.geo','modern_bench_4wide',['bench.texture','sign.texture','white.texture','grey.texture']),('Special_Buildings/trainstation/_trnstation_infloor','trainstation.geo','_trnstation_infloor',['mono_station_infloor.texture','mono_station_infloor_sml.texture','grey.texture'])]
 for group,file,base,dependencies in specs:
  models=miscmodels if file=='misc.geo' else floormodels;data=miscdata if file=='misc.geo' else floordata
  matches=[m for m in models if m['name'].split('__',1)[0].casefold()==base.casefold()];require(len(matches)==1,'ambiguous RootMod/GEO binding '+base);m=matches[0]
  original_group='upstream/i24/data/object_library/'+group.rsplit('/',1)[0]+'/'+('misc_sm' if file=='misc.geo' else 'trainstation')+'.txt';original_group=original_group.replace('Streets/Elements/','Streets/elements/');original=(source_root/original_group).read_bytes();rootdefs,rootrefs,_=parse_groups(original.decode());require(base.casefold() in rootdefs and rootdefs[base.casefold()]['kind']=='rootmod','actual RootMod missing');sourcepins.append({'path':original_group,'bytes':len(original),'sha256':sha(original)})
  encoded=(geo.stream if file=='misc.geo' else floor.stream)(data,m,1);positions=geo.accepted.decode_delta(encoded,m['vertex_count'],3,True);lo=[min(positions[j::3]) for j in range(3)];hi=[max(positions[j::3]) for j in range(3)];center=[geo.f32((a+b)*.5) for a,b in zip(lo,hi)];radius=geo.f32(math.sqrt(sum(max(abs(a-c),abs(b-c))**2 for a,b,c in zip(lo,hi,center))))
  bindings.append({'group':group,'geometry':byfile[file],'model':m['name'],'dependencies':[byfile[x] for x in [file,*dependencies]],'center':center,'radius':radius,'source_model_materials':m['materials'],'source_rootmod':original_group,'source_scale':m['scale']})
 bindingmap={b['group'].casefold():i for i,b in enumerate(bindings)};omitted=collections.Counter();nodes=[];source_visits=0;maxdepth=0;retainedprops=[]
 def walk(edge,parent,chain):
  nonlocal source_visits,maxdepth
  source_visits+=1;require(source_visits<=1000000,'source expansion bound');key=edge['name'].casefold();require(key not in chain,'source group cycle');require(len(chain)<512,'source hierarchy depth');maxdepth=max(maxdepth,len(chain))
  target=defs.get(key);endpoint=bindingmap.get(key,NO)
  n={'name':edge['name'],'parent':parent,'endpoint':endpoint,'pos':edge['pos'],'pyr':edge['pyr'],'tint':target['tint'] if target else None,'line':edge['line'],'properties':target['properties'] if target else []};start=len(nodes);nodes.append(n)
  if target:
   for child in target['groups']:walk(child,start,[*chain,key])
  elif endpoint==NO:omitted[edge['name']]+=1
  if len(nodes)==start+1 and endpoint==NO:nodes.pop();return
  if n['properties']:retainedprops.append({'node':start,'name':n['name'],'properties':n['properties']})
 for ref in refs:walk(ref,NO,[])
 require(nodes and all(n['parent']==NO or n['parent']<i for i,n in enumerate(nodes)),'parent order invalid')
 # Retained source TexSwap rows must not affect any selected material. Other
 # source properties are retained diagnostically; this subset does not claim
 # portals/sounds/cubemaps/lightgrids/LOD or editor metadata execution.
 material_names={m['name'].casefold() for b in bindings for m in b['source_model_materials']}
 for row in retainedprops:
  for tokens in row['properties']:
   if tokens[0].casefold() in ('texswap','replacetex'):require(tokens[1].casefold() not in material_names,'selected active texture override needs qualification')
 materials,materialpins,reused_material_receipts=source_materials(source_root,assets,byfile);sourcepins+=materialpins
 index=index_bytes(nodes,bindings,assets);bundle=bundle_bytes(index,assets,materials);(output/'map.bin').write_bytes(bundle);(output/'map-index.bin').write_bytes(index)
 rr=module('map_independent_reference',NATIVE/'tools/world_fixture/world_reference.py');worlds=[]
 for n in nodes:
  m=rr.local(n['pos'],n['pyr']);worlds.append(rr.multiply(worlds[n['parent']],m) if n['parent']!=NO else m)
 instances=[]
 for i,n in enumerate(nodes):
  if n['endpoint']==NO:continue
  e=bindings[n['endpoint']];instances.append({'node':i,'endpoint':n['endpoint'],'name':n['name'],'world':rr.source_columns(worlds[i]),'world_center':rr.transform(worlds[i],e['center']),'radius':e['radius']})
 spawn=[582.5,74.,-1380.];queries={}
 for radius in [24.,96.]:queries[str(int(radius))]=[r['node'] for r in instances if sum((x-y)**2 for x,y in zip(r['world_center'],spawn))<=(radius+r['radius'])**2]
 receipt={'schema':'coh-gate23-map-fixture-v1','passed':True,'map_source':sourcepins[0],'source_files':list({r['path']:r for r in sourcepins}.values()),'bundle':{'bytes':len(bundle),'sha256':sha(bundle),'format':'COHWB001 app envelope; not original PIGG'},'index':{'bytes':len(index),'sha256':sha(index)},'materials':materials,'reused_material_receipts':reused_material_receipts,'catalog':{'nodes':len(nodes),'endpoints':len(bindings),'assets':len(assets),'instances':len(instances)},'source_definitions':len(defs),'source_refs':len(refs),'source_traversal_visits':source_visits,'source_max_depth':maxdepth,'source_property_rows':propcount,'retained_properties':retainedprops,'omitted_unbound_leaf_instances':sum(omitted.values()),'omitted_unique_names':len(omitted),'unsupported_leaf_frontier':dict(sorted(omitted.items())),'nodes':nodes,'endpoints':bindings,'assets':[{k:v for k,v in a.items() if k!='raw'} for a in assets],'instances':instances,'spawn':spawn,'radius_queries':queries,'scope':'All source-authored placements reachable from Atlas geometry references for three explicitly admitted RootMod endpoints. Full Atlas dependency closure/streaming, source light grids, portals, sounds and other endpoint materials remain unsupported. Accepted WALK kernels remain unchanged; new bounded collision closure covers all eleven admitted source instances.'}
 walkable=module('map_walkable_builder',HERE/'walkable.py');receipt['expanded_walkable']=walkable.build(receipt,assets,source_root,output)
 (output/'map-fixture.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--corpus',type=Path,action='append',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=prepare(a.source_root,a.corpus,a.output);print(json.dumps({k:r[k] for k in ('passed','catalog','radius_queries','bundle')}))
if __name__=='__main__':main()
