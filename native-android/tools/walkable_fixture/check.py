#!/usr/bin/env python3
"""Acquire and qualify only the new authored walkable geometry closure."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,shutil,re
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['walk/coh_walk.c','walk/source_world.c','walk/source_ctri.c','walk/source_tritri.c','motion/coh_motion.c']

def run(command):subprocess.run([str(x) for x in command],check=True)

def audit_floor(source):
    prefix='upstream/i24/data/tricks';expected='f1aab78ed5cd4e33046758f256e38e777a5ee4a3'
    tree=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD:'+prefix],text=True).strip()
    if tree!=expected:raise ValueError('Complete immutable trick tree differs')
    entries=subprocess.check_output(['git','-C',str(source),'ls-tree','-r','--format=%(objectname)\t%(path)','HEAD',prefix],text=True).splitlines()
    if len(entries)!=1585:raise ValueError('Complete trick file count differs')
    declarations={};selected={'mono_station_infloor','mono_station_infloor_sml','mono_station_floor_det'}
    for entry in entries:
        sha,name=entry.split('\t',1);raw=(source/name).read_bytes()
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=sha:raise ValueError('Original trick source blob differs: '+name)
        text=raw.removeprefix(b'\xef\xbb\xbf').decode('latin1');text=re.sub(r'/\*.*?\*/','',text,flags=re.S);text=re.sub(r'//[^\n]*','',text)
        for match in re.finditer(r'(?im)^\s*(?:Texture|InternalName)\s+("[^"\n]+"|[^\s]+)',text):
            key=match.group(1).strip('"').replace('\\','/').lstrip('/').lower();key=key.rsplit('.',1)[0] if not key.endswith('/') else key
            if key in selected:declarations.setdefault(key,[]).append(name)
    wanted={alias:[prefix+'/streets/elements/monorail.txt'] for alias in selected}
    if declarations!=wanted:raise ValueError('Selected floor lookup declarations differ: '+repr(declarations))
    return {'passed':True,'kind':'complete source floor lookup audit','git_tree_sha':tree,'source_files_verified':len(entries),'direct_aliases':declarations,'parent_directory_fallback_not_selected':True,'benchmark_audit_reused':True}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--accepted-assets',type=Path,required=True);p.add_argument('--corpus',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence-output',type=Path,required=True);p.add_argument('--skip-acquire',action='store_true');p.add_argument('--skip-complete-source-audit',action='store_true',help='Local sparse preparation only; receipt retains pending floor alias closure');a=p.parse_args();a.evidence_output.mkdir(parents=True,exist_ok=True)
    if not a.skip_acquire:run([sys.executable,Path(__file__).with_name('acquire.py'),'--output',a.corpus,'--use-verified-local'])
    core=a.evidence_output/'libwalkable-dds.so';collision=a.evidence_output/'libwalkable-source-collision.so'
    # Compile the already-qualified decoder without rerunning unrelated gates.
    run(['cc','-std=c11','-O2','-fPIC','-shared','-I'+str(ROOT/'include'),'-I'+str(ROOT/'src'),ROOT/'src/coh_dds.c','-lm','-o',core])
    run(['cc','-std=c11','-O2','-ffp-contract=off','-fPIC','-shared',*[ROOT/x for x in SOURCES],'-lm','-o',collision])
    original=a.source_root.resolve();audit_args=[]
    if not a.skip_complete_source_audit:
        audit_path=a.evidence_output/'source-floor-resolution.json';audit_path.write_text(json.dumps(audit_floor(original),indent=2)+'\n');audit_args=['--source-floor-audit',audit_path]
    run([sys.executable,Path(__file__).with_name('prepare.py'),'--accepted-assets',a.accepted_assets,'--corpus',a.corpus,'--output',a.output,'--library',core,'--collision-library',collision,'--authored-scene',original/'upstream/i24/data/maps/city_zones/city_01_01/city_01_01_layer_geometry.txt','--anim-source',original/'upstream/ouroboros/Common/seq/anim.c','--tex-source',original/'upstream/ouroboros/Game/src/render/tex.c',*audit_args])
    harness=a.evidence_output/'walkable-parser.c';harness.write_text(r'''
#include "coh_walkable_scene.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char**argv){
 if(argc!=2)return 2;
 FILE*f=fopen(argv[1],"rb");if(!f)return 3;fseek(f,0,SEEK_END);long n=ftell(f);rewind(f);if(n<128||n>16*1024*1024)return 4;unsigned char*b=malloc(n+8);if(!b||fread(b,1,(size_t)n,f)!=(size_t)n)return 5;fclose(f);CohWalkableScene s={0};if(coh_walkable_scene_parse(b,n,&s)||s.part_count!=4||s.texture_count!=6||s.triangle_count!=276)return 6;
 /* Every source material partition's actual indexed positions must equal the
  * collision record coordinates bit-for-bit, including the new authored bench. */
 unsigned t=0;for(unsigned p=0;p<s.part_count;p++){const CohMeshView*m=&s.parts[p].material.mesh;for(unsigned i=0;i<m->index_count;i+=3,t++)for(unsigned k=0;k<3;k++){uint32_t j;CohMeshVertex v;if(coh_mesh_index(m,i+k,&j)||coh_mesh_vertex(m,j,&v)||memcmp(v.position,s.triangles[t].v[k],12))return 7;}}
 if(t!=s.triangle_count)return 8;
 unsigned checks=0;CohWalkableScene before;memset(&before,0x5a,sizeof before);CohWalkableScene out=before;unsigned char original=b[0];b[0]^=0xff;if(!coh_walkable_scene_parse(b,n,&out)||memcmp(&before,&out,sizeof before))return 9;b[0]=original;checks++;
 unsigned offsets[]={16,20,24,36,44,52,60,64,108};for(unsigned i=0;i<sizeof offsets/sizeof*offsets;i++){unsigned o=offsets[i];unsigned char temp[4];memcpy(temp,b+o,4);memset(b+o,0xff,4);out=before;if(!coh_walkable_scene_parse(b,n,&out)||memcmp(&before,&out,sizeof before))return 10;memcpy(b+o,temp,4);checks++;}
 out=before;if(!coh_walkable_scene_parse(b,n-1,&out)||memcmp(&before,&out,sizeof before))return 11;checks++;
 unsigned char*unaligned=malloc(n+1);memcpy(unaligned+1,b,n);out=before;if(!coh_walkable_scene_parse(unaligned+1,n,&out)||memcmp(&before,&out,sizeof before))return 12;free(unaligned);checks++;
 printf("{\"passed\":true,\"authored_parts\":%u,\"source_triangles\":%u,\"render_collision_indexed_positions_byte_exact\":true,\"source_vertices_checked\":%u,\"malformed_inputs_checked\":%u,\"old_gates_repeated\":false}\n",s.part_count,s.triangle_count,t*3,checks);free(b);return 0;}
''')
    executable=a.evidence_output/'walkable-parser';includes=[ROOT/'walkable',ROOT/'walk',ROOT/'world-probe/app/src/main/cpp',ROOT/'world',ROOT/'material-probe/app/src/main/cpp'];run(['cc','-std=c11','-O2','-Wall','-Wextra','-fsanitize=undefined','-fno-sanitize-recover=all',*['-I'+str(x) for x in includes],ROOT/'walkable/coh_walkable_scene.c',ROOT/'material-probe/app/src/main/cpp/coh_mesh.c',harness,'-lm','-o',executable]);receipt=json.loads(subprocess.check_output([str(executable),str(a.output/'walkable.bin')],text=True));receipt['fixture']=json.loads((a.output/'walkable-fixture.json').read_text())['assets']['walkable.bin'];(a.evidence_output/'host-walkable-proof.json').write_text(json.dumps(receipt,indent=2)+'\n');shutil.copyfile(a.output/'walkable-fixture.json',a.evidence_output/'walkable-fixture.json');print(json.dumps(receipt))
if __name__=='__main__':main()
