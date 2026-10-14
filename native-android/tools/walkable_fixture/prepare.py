#!/usr/bin/env python3
"""Prepare real authored floor and second bench; old benchmark stays unchanged."""
from pathlib import Path
import argparse,ctypes as C,hashlib,json,math,struct,sys,zlib,subprocess,tempfile,re
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/world_fixture'))
import geo_prepare as geo
import world_reference as reference
sys.path.insert(0,str(ROOT/'tools/collision_fixture'))
from polycell import decode as decode_grid
f32,require,span,u32=geo.f32,geo.require,geo.span,geo.u32

def identity(raw):return {'bytes':len(raw),'sha256':geo.sha(raw)}

def legacy_records(raw):
    require(16<=len(raw)<=2<<20,'legacy GEO byte bound')
    biased,unpacked=struct.unpack_from('<2I',raw)
    require(unpacked and 4<biased<len(raw)-8,'legacy GEO envelope differs')
    header=geo.inflate(span(raw,8,biased-4),unpacked)
    ds,ns,os,ts=struct.unpack_from('<4I',header);data=span(raw,biased+8,ds)
    require(biased+8+ds==len(raw),'legacy GEO suffix differs')
    pos=16;names=span(header,pos,ns);pos+=ns;objects=span(header,pos,os);pos+=os;texids=span(header,pos,ts);pos+=ts
    nt=u32(names,0);require(0<nt<=128,'legacy texture count bound');nb=4+nt*4
    textures=[geo.name_at(names,nb+u32(names,4+i*4)) for i in range(nt)]
    count=u32(header,pos+136);pos+=140;require(0<count<=128,'legacy model count bound');models=[]
    for index in range(count):
        r=span(header,pos,216);pos+=216
        vc,tc=struct.unpack_from('<2I',r,28);np=u32(r,12)
        require(0<vc<=10000 and 0<tc<=10000 and 0<np<=32,'legacy model count bound')
        require(u32(r,24)==0 and u32(r,40)==0 and u32(r,72)==0 and u32(r,76)==0,'legacy disk pointer slot differs')
        materials=[];first=0
        for tid,n in struct.iter_unpack('<2H',span(texids,u32(r,36),np*4)):
            require(tid<nt and n>0,'legacy material partition invalid')
            materials.append({'name':textures[tid],'triangle_count':n,'first_triangle':first});first+=n
        require(first==tc,'legacy triangle partition mismatch')
        packs=[struct.unpack_from('<3I',r,132+i*12) for i in range(7)]
        for packed,decoded,off in packs:
            require(decoded<=4<<20 and (not packed or decoded),'legacy stream bounds');span(data,off,packed or decoded)
        models.append({'index':index,'name':geo.name_at(objects,u32(r,80)),'vertex_count':vc,'triangle_count':tc,'materials':materials,'packs':packs,'scale':list(struct.unpack_from('<3f',r,92)),'bone_info_offset':u32(r,20)})
    require(pos==len(header),'legacy model record layout suffix differs')
    return data,models

def stream(data,model,index):
    packed,decoded,off=model['packs'][index];b=span(data,off,packed or decoded)
    return geo.inflate(b,decoded) if packed else b

def mesh(vertices,indices):
    vc=len(vertices);vo=64;io=vo+vc*48;bo=io+len(indices)*4;total=bo+4
    h=struct.pack('<8s14I',b'COHMESH1',1,64,vc,len(indices),1,48,vo,io,bo,total,0,0,0,0)
    return h+b''.join(struct.pack('<10f2I',*v) for v in vertices)+struct.pack('<'+'I'*len(indices),*indices)+struct.pack('<I',0)

class CTri(C.Structure):
    _fields_=[('V1',C.c_float*3),('v2',C.c_float*2),('v3',C.c_float*2),('midpt',C.c_float*2),('extents',C.c_float*2),('norm',C.c_float*3),('scale',C.c_float),('flags',C.c_uint32),('surfTex',C.c_void_p)]

def native_matrices(lib,nodes):
    raw=bytearray(520);raw[:8]=b'COHWRI09';struct.pack_into('<9I',raw,8,1,64,6,6,64,232,520,28,48)
    for i,(p,y) in enumerate(nodes):struct.pack_into('<I6f',raw,64+28*i,0xffffffff if i==0 else i-1,*p,*y)
    for i in range(6):struct.pack_into('<10f2I',raw,232+i*48,0,0,10,0,0,0,50,1,1,200,0,0)
    # Opaque input ABI consists exactly of 6*28+6*48 bytes on supported hosts.
    inputs=(C.c_uint8*456)();buf=(C.c_uint8*520).from_buffer_copy(raw)
    lib.coh_world_parse_inputs.argtypes=[C.c_void_p,C.c_size_t,C.c_void_p]
    require(lib.coh_world_parse_inputs(buf,520,inputs)==0,'native raw matrix inputs rejected')
    local=(C.c_float*72)();world=(C.c_float*72)();lib.coh_world_group_matrices.argtypes=[C.c_void_p,C.c_void_p,C.c_void_p]
    require(lib.coh_world_group_matrices(inputs,local,world)==0,'native source matrices rejected')
    expected=reference.group_matrices(nodes)[1][-1];actual=reference.row_matrix(list(world)[60:72])
    error=max(abs(actual[r][c]-expected[r][c]) for r in range(3) for c in range(4))
    require(error<1e-4,'independent authored hierarchy transform differs')
    return actual,error

def original_delta(data,model,source):
    original=geo.module('walkable_original_delta',ROOT/'tools/material_fixture/original_delta_check.py');code=original.original_c(source);checks=[]
    with tempfile.TemporaryDirectory(prefix='coh-walkable-delta-') as directory:
        t=Path(directory);(t/'original.c').write_bytes(code);subprocess.run(['cc','-std=c11','-O0','-fno-strict-aliasing','-shared','-fPIC','-o',str(t/'oracle.so'),str(t/'original.c')],check=True)
        lib=C.CDLL(str(t/'oracle.so'));lib.uncompressDeltas.argtypes=[C.c_void_p,C.POINTER(C.c_uint8),C.c_int,C.c_int,C.c_int]
        for label,j,count,stride,kind in [('indices',0,model['triangle_count'],3,1),('positions',1,model['vertex_count'],3,0),('normals',2,model['vertex_count'],3,0),('uvs',3,model['vertex_count'],2,0)]:
            raw=stream(data,model,j);values=geo.accepted.decode_delta(raw,count,stride,kind==0);expected=struct.pack('<'+('f' if kind==0 else 'I')*len(values),*values);src=(C.c_uint8*(len(raw)+16))();C.memmove(src,raw,len(raw));output=(C.c_uint8*len(expected))()
            require(lib.uncompressDeltas(output,src,stride,count,kind)==len(raw) and bytes(output)==expected,'original floor delta differs:'+label)
            checks.append({'channel':label,'elements':len(values),'byte_exact':True,'source_sha256':geo.sha(raw),'decoded_sha256':geo.sha(expected)})
    return {'passed':True,'original_unchanged_uncompressDeltas':True,'source_sha256_lf':original.SOURCE_SHA,'checks':checks}

def fallback_oracle(source):
    raw=source.read_bytes();require(geo.sha(raw)=='4507ee6fa752ed9452e78c4c989a9de0bdf93d81dd3597f1b1db063d73f1ca5c','original tex.c source pin differs')
    text=raw.decode('utf8');start=text.index('static BasicTexture *texFindVerify(');end=text.index('\n}\n',start)+3;function=text[start:end]
    statement='bind->tex_layers[TEXLAYER_GENERIC] = texFindVerify(texopt->blend_names[BLEND_OLD_TEX_GENERIC_BLEND], grey_tex, "DualColor1", trickFileName, trickName);'
    require(statement in text,'original missing generic binding assignment differs')
    code='#include <string.h>\n#define stricmp strcasecmp\n#include <strings.h>\ntypedef struct {int id;} BasicTexture;\nstatic int quickload=1;\nstatic BasicTexture grey={128},present={7},*grey_tex=&grey;\nstatic BasicTexture *texFind(const char*n){return strcmp(n,"present")==0?&present:0;}\n#define ErrorFilenamef(...) ((void)0)\n'+function+'\n#define TEXLAYER_GENERIC 0\n#define BLEND_OLD_TEX_GENERIC_BLEND 0\nint main(void){struct {BasicTexture*tex_layers[1];} b,*bind=&b;struct{char*blend_names[1];}t,*texopt=&t;char*trickFileName="monorail.txt",*trickName="mono_station_infloor";t.blend_names[0]="mono_station_floor_det";'+statement+'return bind->tex_layers[0]!=grey_tex;}\n'
    with tempfile.TemporaryDirectory(prefix='coh-source-floor-fallback-') as directory:
        p=Path(directory);(p/'oracle.c').write_text(code);subprocess.run(['cc','-std=c11','-O0','-o',str(p/'oracle'),str(p/'oracle.c')],check=True);subprocess.run([str(p/'oracle')],check=True)
    return {'passed':True,'source_path':'upstream/ouroboros/Game/src/render/tex.c','source_sha256':geo.sha(raw),'unchanged_function_sha256':geo.sha(function.encode()),'unchanged_binding_statement_sha256':geo.sha(statement.encode()),'missing_alias':'mono_station_floor_det','original_selected_fallback':'grey','original_client_executed':False,'texture_detail_fidelity_complete':False}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--accepted-assets',type=Path,required=True);p.add_argument('--corpus',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--collision-library',type=Path,required=True);p.add_argument('--authored-scene',type=Path,required=True);p.add_argument('--anim-source',type=Path,required=True);p.add_argument('--tex-source',type=Path,required=True);p.add_argument('--source-floor-audit',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    pins=json.loads(Path(__file__).with_name('pins.json').read_text());floor_audit=json.loads(a.source_floor_audit.read_text()) if a.source_floor_audit else None
    if floor_audit:require(floor_audit.get('passed') and floor_audit.get('kind')=='complete source floor lookup audit' and floor_audit.get('git_tree_sha')=='f1aab78ed5cd4e33046758f256e38e777a5ee4a3' and floor_audit.get('source_files_verified')==1585,'complete source floor lookup receipt differs')
    for pin in pins['records']:
        raw=(a.corpus/pin['file_name']).read_bytes();require(identity(raw)=={'bytes':pin['size'],'sha256':pin['sha256']} and f'{zlib.crc32(raw):08x}'==pin['crc32'],'ground corpus identity differs')
    authored=a.authored_scene.read_bytes();recovery=json.loads((ROOT/'evidence/phase9/scene-recovery.json').read_text());sourcepin=next(x for x in recovery['source_pins'] if x['path'].endswith('city_01_01_layer_geometry.txt'));require(identity(authored)=={k:sourcepin[k] for k in ('bytes','sha256')},'authored Atlas map differs')
    require(b'\tGroup Special_Buildings/trainstation/_trnstation_infloor\n\t\tPos 0 32 0\n\tEnd\n' in authored and b'\tGroup grp141259\n\t\tPos -29.5 32 -41.5\n\tEnd\n' in authored,'actual selected authored sibling placements differ')
    decl=Path(__file__).with_name('source').joinpath('monorail.txt').read_bytes();require(identity(decl)=={k:pins['source_declarations'][k] for k in ('bytes','sha256')},'floor source declaration differs')
    for name,scale in [('mono_station_infloor_sml',8),('mono_station_infloor',14)]:
        block=re.search(r'(?ms)^Texture '+name+r'\.tga\n(.*?)^End',decl.decode()).group(1);tokens=[x.strip() for x in block.splitlines() if x.strip()];require(tokens==['Blend mono_station_floor_det.tga','BlendType Multiply',f'ScaleST0 {scale} {scale}'],'floor material flags or timing differ')
    accepted=json.loads((a.accepted_assets/'world-fixture.json').read_text());old=(a.accepted_assets/'world.bin').read_bytes();require(identity(old)=={k:accepted['assets']['world.bin'][k] for k in ('bytes','sha256')},'accepted world input differs');require(accepted['source_trick_resolution_qualified'],'accepted bench declaration audit missing')
    lib=C.CDLL(str(a.library.resolve()));matrix_path=a.output/'source-world-matrices.so';subprocess.run(['cc','-std=c11','-O2','-fPIC','-shared',str(ROOT/'world/coh_world.c'),'-lm','-o',str(matrix_path)],check=True);matrix_lib=C.CDLL(str(matrix_path.resolve()));base=reference.NODE_INPUTS[:4];floor_nodes=base+[([0,32,0],[0,0,0]),([0,0,0],[0,0,0])];bench_nodes=base+[([-29.5,32,-41.5],[0,0,0]),reference.NODE_INPUTS[-1]];floor_matrix,floorerr=native_matrices(matrix_lib,floor_nodes);bench_matrix,bencherr=native_matrices(matrix_lib,bench_nodes)
    data,models=legacy_records((a.corpus/'trainstation.geo').read_bytes());m=models[5];require(m['name']=='_trnstation_infloor' and m['vertex_count']==71 and m['triangle_count']==88 and m['scale']==[1,1,1] and not m['bone_info_offset'],'authentic floor model differs');require(not stream(data,m,4) and not stream(data,m,5),'floor unexpectedly skinned')
    decoded={j:geo.accepted.decode_delta(stream(data,m,j),m['triangle_count'] if j==0 else m['vertex_count'],3 if j<3 else 2,j!=0) for j in range(4)};fv=[]
    for i in range(71):fv.append(reference.transform(floor_matrix,decoded[1][i*3:i*3+3])+reference.transform(floor_matrix,decoded[2][i*3:i*3+3],False)+[decoded[3][i*2],f32(1-decoded[3][i*2+1])]+[1.,0.,0,0])
    meshes=[];parts=[];triangles=[]
    for i,material in enumerate(m['materials']):
        ix=decoded[0][material['first_triangle']*3:(material['first_triangle']+material['triangle_count'])*3];meshes.append(mesh(fv,ix));parts.append({'model':m['name'],'base_texture':i,'dual_texture':3,'flags':0,'mode':0,'color1':[1]*4,'color2':[0,0,0,1],'diffuse_scale':1.,'ambient_scale':1.,'alpha_ref':0.,'uv_scale0':[8.,8.] if i==0 else [14.,14.],'uv_scale1':[1.,1.]});triangles.extend([[fv[j][:3] for j in ix[t:t+3]] for t in range(0,len(ix),3)])
    # Old source mesh bytes retain all normals/UVs/material partitions. Only the
    # additional actual authored instance gets the different hierarchy matrix.
    bench_tris=[]
    for i in range(2):
        rec=old[128+i*96:128+(i+1)*96];raw=old[u32(rec,0):u32(rec,0)+u32(rec,4)];vc=u32(raw,16);ic=u32(raw,20);v=[]
        for j in range(vc):
            values=list(struct.unpack_from('<10f2I',raw,64+j*48));v.append(reference.transform(bench_matrix,values[:3])+reference.transform(bench_matrix,values[3:6],False)+values[6:])
        ix=list(struct.unpack_from('<'+'I'*ic,raw,u32(raw,36)));meshes.append(mesh(v,ix));parts.append({'model':'modern_bench_2wide__mbench','base_texture':u32(rec,12)+2,'dual_texture':u32(rec,16)+2,'flags':u32(rec,20),'mode':u32(rec,68),'color1':list(struct.unpack_from('<4f',rec,24)),'color2':list(struct.unpack_from('<4f',rec,40)),'diffuse_scale':struct.unpack_from('<f',rec,56)[0],'ambient_scale':struct.unpack_from('<f',rec,60)[0],'alpha_ref':struct.unpack_from('<f',rec,64)[0],'uv_scale0':[1,1],'uv_scale1':[1,1]});bench_tris.extend([[v[j][:3] for j in ix[t:t+3]] for t in range(0,len(ix),3)])
    triangles+=bench_tris;require(len(triangles)==276,'selected triangle closure differs');collision=C.CDLL(str(a.collision_library.resolve()));collision.createCTri.argtypes=[C.POINTER(CTri),C.POINTER(C.c_float),C.POINTER(C.c_float),C.POINTER(C.c_float)];records=[]
    for points in triangles:
        tri=CTri();vs=[(C.c_float*3)(*v) for v in points];valid=collision.createCTri(C.byref(tri),*vs);flags=2048 if valid and tri.scale else 0;records.append(struct.pack('<9fI',*(x for v in points for x in v),flags))
    # Source packed PolyCell offsets and memberships are audited, never cast or
    # relocated. Runtime uses compact CTri cache over the selected exact closure.
    grid=decode_grid(stream(data,m,6),88);grid['source_grid_sha256']=geo.sha(stream(data,m,6));grid['collision_flags_reconstructed']=True
    textures=[];lib.coh_dds_rgba.argtypes=[C.c_void_p,C.c_size_t,C.c_uint32,C.c_void_p,C.c_size_t]
    for name in ['mono_station_infloor_sml.texture','mono_station_infloor.texture']:
        rgba,w,h,metadata=geo.accepted.decode_texture((a.corpus/name).read_bytes(),lib.coh_dds_rgba);textures.append({'name':name,'rgba':rgba,'width':w,'height':h})
    for i in range(4):
        tr=old[u32(old,40)+i*32:u32(old,40)+(i+1)*32];off,size,w,h=struct.unpack_from('<4I',tr);textures.append({'name':accepted['textures'][i]['name'],'rgba':old[off:off+size],'width':w,'height':h,'accepted_reused':True})
    require(textures[3]['name']=='grey','original missing detail grey fallback mapping differs')
    po=128;to=po+len(parts)*96;co=to+len(textures)*32;dataoff=co+len(records)*40;cursor=dataoff;pr=[]
    for raw,part in zip(meshes,parts):
        r=bytearray(96);struct.pack_into('<6I',r,0,cursor,len(raw),0,part['base_texture'],part['dual_texture'],part['flags']);struct.pack_into('<4f',r,24,*part['color1']);struct.pack_into('<4f',r,40,*part['color2']);struct.pack_into('<3fI4f',r,56,part['diffuse_scale'],part['ambient_scale'],part['alpha_ref'],part['mode'],*part['uv_scale0'],*part['uv_scale1']);pr.append(bytes(r));cursor+=len(raw)
    tr=[]
    for t in textures:tr.append(struct.pack('<4I',cursor,len(t['rgba']),t['width'],t['height'])+bytes(16));cursor+=len(t['rgba'])
    points=[v for tri in triangles for v in tri];lo=[min(p[k] for p in points) for k in range(3)];hi=[max(p[k] for p in points) for k in range(3)];spawn=reference.transform(floor_matrix,[-36,0,-41.5]);yaw=f32(math.atan2(floor_matrix[0][0],floor_matrix[2][0]));head=bytearray(128);head[:8]=b'COHWALK1';struct.pack_into('<15I',head,8,1,128,len(parts),len(textures),len(records),sum(u32(b,16) for b in meshes),sum(u32(b,20) for b in meshes),po,96,to,32,co,40,dataoff,cursor);struct.pack_into('<10f',head,68,*lo,*hi,*spawn,yaw)
    raw=bytes(head)+b''.join(pr)+b''.join(tr)+b''.join(records)+b''.join(meshes)+b''.join(t['rgba'] for t in textures);require(len(raw)==cursor and cursor<=16<<20,'walkable byte bound differs');(a.output/'walkable.bin').write_bytes(raw)
    parity=original_delta(data,m,a.anim_source);fallback=fallback_oracle(a.tex_source);receipt={'schema':1,'passed':True,'gates':[19,20],'name':'Actual Atlas trainstation infloor plus authored second modern bench','assets':{'walkable.bin':identity(raw)},'scene':{'part_count':4,'texture_count':6,'triangle_count':276,'bytes':len(raw),'bounds_min':lo,'bounds_max':hi,'spawn':spawn,'spawn_yaw':yaw,'obstacle_bounds_min':[min(v[k] for tri in bench_tris for v in tri) for k in range(3)],'obstacle_bounds_max':[max(v[k] for tri in bench_tris for v in tri) for k in range(3)]},'authored_source':sourcepin,'authored_nodes':{'floor':floor_nodes,'additional_bench':bench_nodes},'source_matrices':{'floor':reference.source_columns(floor_matrix),'bench':reference.source_columns(bench_matrix),'max_independent_error':max(floorerr,bencherr)},'render_collision_vertices_byte_identical':True,'source_delta_parity':parity,'source_createCTri_flags':{'triangle_count':276,'normal_triangles':sum(struct.unpack_from('<I',x,36)[0]==2048 for x in records),'degenerate_triangles':sum(struct.unpack_from('<I',x,36)[0]==0 for x in records),'source_texopt_flags':0,'source_trick_mbench_coll_flags':0,'runtime_original_CTtri_cache':True},'source_grid':grid,'materials':parts,'original_missing_detail_fallback':fallback,'missing_detail_texture':'mono_station_floor_det','floor_material_fidelity_complete':False,'complete_floor_material_resolution_qualified':floor_audit is not None,'source_floor_declaration_audit':floor_audit,'synthetic_geometry':False,'source_geometry_version':0,'source_record_bytes':216,'full_atlas_loaded':False,'physical_gates19_21_accepted':False,'accepted_world_assets_changed':False,'runtime_references_drive_rendering':False,'memory_bounds':{'container_max_bytes':16<<20,'source_grid_max_bytes':4<<20,'triangle_max_count':8192,'vertices_max_count':65536,'textures_max_count':16}}
    (a.output/'walkable-fixture.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'passed':True,'scene':receipt['scene'],'assets':receipt['assets']}))
if __name__=='__main__':main()
