#!/usr/bin/env python3
"""Bounded, pinned-Git offline scene closure. Never reads live server state.

Reuses the accepted group parser and binary32 source matrix reference. Original
assets stay external; manifest membership is NOT decoder/render qualification.
"""
import argparse, collections, hashlib, importlib.util, json, math, os, pathlib, re, subprocess
HERE = pathlib.Path(__file__).resolve().parent
NATIVE = HERE.parents[2]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

GROUPS = load('accepted_map_groups', NATIVE / 'tools/map_fixture/prepare.py')
MATH = load('accepted_source_world_math', NATIVE / 'tools/world_fixture/world_reference.py')
BASE = 'upstream/i24/data/'

class TraversalLimit(ValueError): pass

def require(ok, message):
    if not ok: raise ValueError(message)

def sha(raw): return hashlib.sha256(raw).hexdigest()

def safe(path):
    require(path and '\\' not in path and ':' not in path and not path.startswith('/') and
            all(x not in ('', '.', '..') for x in path.split('/')), 'unsafe source path')
    return path

class GitSource:
    def __init__(self, root, rev):
        self.root = root
        self.rev = self.git('rev-parse', '--verify', rev + '^{commit}').decode().strip()
        require(re.fullmatch('[a-f0-9]{40}', self.rev), 'invalid pinned revision')
        rows = self.git('ls-tree', '-r', self.rev, BASE + 'maps', BASE + 'object_library').decode().splitlines()
        self.paths = {}; self.directories = collections.defaultdict(list)
        for row in rows:
            meta, path = row.split('\t'); kind, blob = meta.split()[1:]
            if kind != 'blob' or not path.endswith('.txt'): continue
            key = path.casefold(); require(key not in self.paths, 'ambiguous source case identity')
            self.paths[key] = (path, blob)
            self.directories[path.rsplit('/', 1)[0].casefold()].append(path)
        self.raw = {}; self.pins = {}; self.bytes = 0; self.missing_blobs = {}
    def git(self, *args): return subprocess.check_output(['git', '-C', str(self.root), *args])
    def read(self, path):
        row = self.paths.get(safe(path).casefold())
        if not row: raise FileNotFoundError(path)
        path, blob = row
        if path not in self.raw:
            # Only requested blobs; never checkout whole upstream or another worker's tree.
            if path in self.missing_blobs: raise FileNotFoundError(path)
            try:
                raw = subprocess.check_output(['git', '-C', str(self.root), 'cat-file', 'blob', blob], env={**os.environ, 'GIT_NO_LAZY_FETCH':'1'}, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                self.missing_blobs[path] = blob; raise FileNotFoundError(path)
            require(len(raw) <= 8 << 20, 'individual source exceeds 8 MiB')
            self.bytes += len(raw); require(self.bytes <= 128 << 20, 'source corpus exceeds 128 MiB')
            self.raw[path] = raw
            self.pins[path] = dict(path=path, git_blob=blob, bytes=len(raw), sha256=sha(raw))
        return path, self.raw[path]

class Closure:
    def __init__(self, source, assets, max_visits=1000000, oracle=None):
        self.source, self.assets, self.max_visits = source, assets, max_visits
        self.oracle = oracle
        self.parsed = {}; self.parse_errors = {}; self.missing = collections.Counter()
        self.properties = collections.Counter(); self.endpoints = {}; self.instances = []
        self.nodes = 0; self.depth = 0; self.active = set(); self.resolved_cache = {}
    def parse(self, path):
        actual, raw = self.source.read(path)
        if actual not in self.parsed:
            try: self.parsed[actual] = GROUPS.parse_groups(raw.decode('utf-8-sig'))
            except (ValueError, KeyError) as e:
                self.parse_errors[actual] = str(e); raise
        return actual, self.parsed[actual]
    def resolve(self, name, local_path, defs):
        key = name.casefold()
        cache_key=(local_path,key)
        if cache_key in self.resolved_cache:return self.resolved_cache[cache_key]
        if key in defs: return local_path, defs[key], defs
        if '/' not in name:
            self.missing['missing_local_definition:' + local_path + ':' + name] += 1
            return None
        directory, base = name.rsplit('/', 1)
        paths = self.source.directories.get((BASE + 'object_library/' + directory).casefold(), [])
        matches = []
        for path in paths:
            try: actual, (other, _, _) = self.parse(path)
            except (ValueError, KeyError, FileNotFoundError): continue
            if base.casefold() in other: matches.append((actual, other[base.casefold()], other))
        if len(matches) != 1:
            self.missing[('ambiguous_definition:' if matches else 'missing_definition:') + name] += 1
            return None
        self.resolved_cache[cache_key]=matches[0]
        return matches[0]
    def audit_graph(self, refs, path, defs):
        graph={}; roots=[]; todo=[]; missing_before=dict(self.missing)
        def admit(edge, local_path, local_defs):
            found=self.resolve(edge['name'],local_path,local_defs)
            if not found:return None
            actual,node,local=found;key=actual+'#'+node['name']
            if key not in graph:
                require(len(graph)<65536,'definition graph budget exceeded')
                graph[key]=dict(kind=node['kind'],edges=[]);todo.append((key,actual,node,local))
            return key
        for ref in refs:
            key=admit(ref,path,defs)
            if key:roots.append(key)
        cursor=0
        while cursor<len(todo):
            key,actual,node,local=todo[cursor];cursor+=1
            for child in node['groups']:
                childkey=admit(child,actual,local)
                if childkey:graph[key]['edges'].append(childkey)
        active=set();memo={}
        def count(key,depth=0):
            require(depth<128 and key not in active,'definition graph cycle/depth')
            if key in memo:return memo[key]
            active.add(key);visits=1;models=int(graph[key]['kind']=='rootmod')
            for child in graph[key]['edges']:
                a,b=count(child,depth+1);visits+=a;models+=b
            active.remove(key);memo[key]=(visits,models);return memo[key]
        totals=[count(key) for key in roots]
        graph_missing={k:v-missing_before.get(k,0) for k,v in self.missing.items() if v>missing_before.get(k,0)}
        return dict(top_level_refs=len(refs),root_keys=roots,unique_reachable_definitions=len(graph),resolved_definition_edges=sum(len(n['edges']) for n in graph.values()),symbolic_resolved_node_occurrences=sum(x[0] for x in totals),symbolic_rootmod_occurrences=sum(x[1] for x in totals),missing_edges=graph_missing,cycles=0,all_text_definition_edges_resolved=not graph_missing)
    def visit(self, edge, path, defs, parent, depth=0, inherited_tint=None, material_overrides=()):
        if self.nodes >= self.max_visits: raise TraversalLimit('scene visit budget exceeded')
        self.nodes += 1
        require(depth < 128, 'scene depth budget exceeded'); self.depth = max(depth, self.depth)
        if self.oracle:
            matrix = MATH.row_matrix(self.oracle.compose(MATH.source_columns(parent), edge['pos'], edge['pyr'], depth == 0))
        else:
            local = MATH.local(edge['pos'], edge['pyr'])
            matrix = local if depth == 0 else MATH.multiply(parent, local)
        found = self.resolve(edge['name'], path, defs)
        if not found:
            return
        actual, node, local = found; key = (actual, node['name'].casefold())
        require(key not in self.active, 'source group cycle: ' + str(key))
        self.active.add(key)
        tint = node['tint'] if node['tint'] is not None else inherited_tint
        overrides = material_overrides + tuple(p for p in node['properties'] if p[0].casefold() in ('texswap', 'replacetex'))
        for p in node['properties']: self.properties[p[0]] += 1
        if node['kind'] == 'rootmod':
            # Exact source container mapping is a candidate; require GEO model lookup
            # before rendering. The source group name alone cannot prove a model.
            geo = 'data/' + actual[len(BASE):].rsplit('.', 1)[0] + '.geo'
            asset = self.assets.get(geo.casefold())
            endpoint = actual + '#' + node['name']
            if endpoint not in self.endpoints:
                self.endpoints[endpoint] = dict(source_file=actual, source_line=node['line'],
                    model=node['name'], geometry_candidate=geo, external_asset=asset,
                    status='external-identity-only' if asset else 'missing-external-geometry',
                    material_and_model_qualification=False,
                    geometry_version=(asset or {}).get('provenance',{}).get('geometry_header',{}).get('version'),
                    render_blockers=['GEO/model table admission required','Source trick/material/color/lighting resolution required'] + (['GEO version '+str(asset['provenance']['geometry_header']['version'])+' unsupported by accepted rigid bridge'] if (asset or {}).get('provenance',{}).get('geometry_header',{}).get('version') not in (None,0,7) else []))
            self.instances.append(dict(endpoint=endpoint, world=MATH.source_columns(matrix), tint=tint, material_overrides=overrides))
        for child in node['groups']: self.visit(child, actual, local, matrix, depth + 1, tint, overrides)
        self.active.remove(key)
    def run(self, zone):
        root = BASE + 'maps/city_zones/' + zone + '/' + zone + '.txt'
        actual, raw = self.source.read(root)
        imports = re.findall(r'^Import\s+(\S+)\s*$', raw.decode(), re.M | re.I)
        geometry = [p for p in imports if p.casefold().endswith('_layer_geometry.txt')]
        require(len(geometry) == 1, 'expected one explicit geometry layer')
        path, (defs, refs, _) = self.parse(BASE + geometry[0])
        graph=self.audit_graph(refs,path,defs)
        identity = MATH.local([0., 0., 0.], [0., 0., 0.])
        truncated=False
        try:
            for ref in refs: self.visit(ref, path, defs, identity)
        except TraversalLimit:
            truncated=True
        cells = collections.Counter((math.floor(i['world'][9] / 256.), math.floor(i['world'][11] / 256.)) for i in self.instances)
        exact_assets = {v['geometry_candidate']: v['external_asset'] for v in self.endpoints.values() if v['external_asset']}
        report = dict(schema='coh-offline-zone-closure-v1', zone=zone,
            source_revision=self.source.rev, root_source=actual, geometry_source=path,
            imports=imports, imports_not_expanded=[p for p in imports if p not in geometry],
            scope='Original geometry layer dependency expansion only; other layers and full-zone acceptance remain open.',
            traversal_truncated=truncated, limits=dict(max_visits=self.max_visits,max_depth=128,max_source_bytes=128<<20,max_single_source_bytes=8<<20),
            source_visits=self.nodes, maximum_depth=self.depth, instance_count=len(self.instances),
            top_level_geometry_refs=len(refs),map_local_definition_count=len(defs),definition_graph=graph,
            most_repeated_placed_rootmods=collections.Counter(i['endpoint'] for i in self.instances).most_common(12),
            count_semantics='Placed source RootMods include editor markers, sound emitters, invisible bounds, recursively tiled walls, and LOD content; these are NOT admitted draw instances.',
            endpoint_count=len(self.endpoints), spatial_cell_size=256, occupied_origin_cells=len(cells),
            cells=[dict(x=k[0], z=k[1], instances=v, collision_coverage='MISSING_UNQUALIFIED_GEOMETRY') for k,v in sorted(cells.items())],
            endpoints=self.endpoints, external_geometry_identities=exact_assets,
            missing_definitions=dict(sorted(self.missing.items())), parser_failures=self.parse_errors,
            retained_property_counts=dict(sorted(self.properties.items())),
            source_files=list(self.source.pins.values()), unavailable_source_blobs=self.source.missing_blobs,
            complete_zone=False, gpu_qualified=False, collision_render_geometry_qualified=False,
            renderer_integration='Use engine/assets indexed loader then engine/bridge; version 8 GEO and additional material semantics require independent admission. No fallback substitution.')
        return report, self.instances

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=pathlib.Path,required=True)
    p.add_argument('--revision',required=True);p.add_argument('--asset-manifest',type=pathlib.Path,required=True,action='append')
    p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--zone',choices=['city_01_01','city_01_02'],action='append')
    a=p.parse_args();assets={};manifest_pins=[]
    for path in a.asset_manifest:
        raw=path.read_bytes();external=json.loads(raw)
        manifest_pins.append(dict(bytes=len(raw),sha256=sha(raw),archive=external['archive']))
        for k,v in external['files'].items():
            assets[k.casefold()]=dict(path=k, **v, archive=external['archive'], provenance=external.get('provenance',{}).get('entries',{}).get(k,{}))
    a.output.mkdir(parents=True,exist_ok=True);source=GitSource(a.repo,a.revision)
    oracle_type=load('offline_source_math', HERE/'source_math.py').SourceMath
    for zone in a.zone or ['city_01_01','city_01_02']:
        oracle=oracle_type(a.repo,source.rev)
        report,instances=Closure(source,assets,oracle=oracle).run(zone)
        report['original_math_comparison']=oracle.report()
        payload=json.dumps(instances,separators=(',',':')).encode()
        (a.output/(zone+'-instances.json')).write_bytes(payload)
        report['instance_payload']=dict(file=zone+'-instances.json',bytes=len(payload),sha256=sha(payload),matrix_format='original binary32 Mat4 columns 4x3; identical render/collision placement')
        report['asset_manifest_identity']=manifest_pins
        (a.output/(zone+'-manifest.json')).write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({k:report[k] for k in ('zone','source_visits','instance_count','endpoint_count','occupied_origin_cells','complete_zone')}),flush=True)
if __name__=='__main__':main()
