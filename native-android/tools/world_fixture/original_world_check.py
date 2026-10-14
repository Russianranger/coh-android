#!/usr/bin/env python3
"""Execute unchanged degree, YPR, group, view and frustum source kernels.

Only standalone scalar kernels execute. Token storage uses a single supplied
float token, invert output is disabled, and gfx projection state is a local
Mat44. These documented adapters do not claim original whole-client execution.
"""
from pathlib import Path
import argparse,ctypes as C,hashlib,importlib.util,json,os,re,shlex,struct,subprocess,tempfile
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
types=module('world_native_types',HERE/'_types.py');reference=module('world_independent_reference',HERE/'world_reference.py')
PATHS={'mathutil.c':'libs/UtilitiesLib/src/utils/mathutil.c','mathutil.h':'libs/UtilitiesLib/include/utilitieslib/utils/mathutil.h','gfx.c':'Game/src/graphics/gfx.c','renderUtil.c':'Game/src/render/renderUtil.c','textparser.c':'libs/UtilitiesLib/src/utils/textparser.c'}
FUNCTIONS=[('textparser.c','degrees_parse'),('mathutil.h','mathutil_sincosf'),('mathutil.c','createMat3YPR'),('mathutil.h','mulMat3Inline'),('mathutil.h','mulMat4Inline'),('mathutil.c','mulMat3'),('mathutil.c','transposeMat3'),('mathutil.h','copyMat4'),('mathutil.h','mulVecMat3'),('mathutil.h','mulVecMat4'),('mathutil.h','mulVecMat44'),('renderUtil.c','rdrFixMat'),('gfx.c','gfxSetViewMat'),('renderUtil.c','rdrSetupFrustum'),('renderUtil.c','rdrSetupPerspectiveProjection')]
def require(v,s):
 if not v:raise ValueError(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def extract(text,name):
 matches=list(re.finditer(r'(?m)^[^\n;]*\b'+re.escape(name)+r'\s*\([^;]*?\)\s*\{',text))
 require(matches,'Source function missing: '+name);m=matches[0];start=m.start();brace=text.find('{',m.start());depth=1;i=brace+1
 while depth:
  require(i<len(text),'Unbalanced source '+name)
  if text[i]=='{':depth+=1
  elif text[i]=='}':depth-=1
  i+=1
 return text[start:i]
PREAMBLE=r'''
#include <assert.h>
#include <stdbool.h>
#include <math.h>
#include <string.h>
typedef float F32;typedef float Vec3[3],Vec4[4],Mat3[3][3],Mat4[4][3],Mat44[4][4];
#define INLINEDBG
#define PI 3.14159265358979323846
#define RAD(a) (((a)*PI)*(1.0f/180.0f))
#define copyVec3(s,d) memcpy((d),(s),12)
#define copyMat3(s,d) memcpy((d),(s),36)
#define subVec3(a,b,d) do{for(int i=0;i<3;i++)(d)[i]=(a)[i]-(b)[i];}while(0)
static const Vec3 zerovec3={0,0,0};
static struct{Mat44 projection_matrix;}gfx_state;
typedef const float *TokenizerHandle;typedef int ParseTable;typedef void *ParserTextCallback;
static const char *GetNextParameter(TokenizerHandle tok){return tok?"supplied_float_token":0;}
static float GetFloat(TokenizerHandle tok,const char *text){(void)text;return *tok;}
static void TokenStoreSetF32(ParseTable *t,int column,void *out,int index,float v){(void)t;(void)column;((float*)out)[index]=v;}
static void invertMat4Copy(const Mat4 m,Mat4 inv){(void)m;(void)inv;assert(!"Inverse camera output is outside this bounded oracle");}
'''
WRAPPER=r'''
void original_local(const float pos[3],const float degrees[3],float out[12]){
 Vec3 pyr;ParseTable table=0;for(int i=0;i<3;i++)degrees_parse(degrees+i,&table,0,pyr,i,0);Mat4 matrix;createMat3YPR(matrix,pyr);copyVec3(pos,matrix[3]);memcpy(out,matrix,48);
}
void original_group(const float nodes[36],float locals[72],float worlds[72]){
 Mat4 l[6],w[6];for(int i=0;i<6;i++){original_local(nodes+i*6,nodes+i*6+3,(float*)l[i]);if(i)mulMat4Inline(w[i-1],l[i],w[i]);else copyMat4(l[i],w[i]);}memcpy(locals,l,sizeof l);memcpy(worlds,w,sizeof w);
}
void original_camera(const float parameters[10],unsigned fx,unsigned fy,float view[12],float projection[16]){
 Mat4 cam,v;original_local(parameters,parameters+3,(float*)cam);gfxSetViewMat(cam,v,0);rdrSetupPerspectiveProjection(parameters[6],parameters[7],parameters[8],parameters[9],fx,fy);memcpy(view,v,48);memcpy(projection,gfx_state.projection_matrix,64);
}
void original_group_eye(const float nodes[36],const float view[12],float eyes[72]){
 Mat4 l,e[6];for(int i=0;i<6;i++){original_local(nodes+i*6,nodes+i*6+3,(float*)l);mulMat4Inline(i?e[i-1]:(const float(*)[3])view,l,e[i]);}memcpy(eyes,e,sizeof e);
}
void original_vertex(const float world[12],const float view[12],const float projection[16],const float pos[3],const float normal[3],float out[13]){
 mulVecMat4(pos,(const float(*)[3])world,out);mulVecMat3(normal,(const float(*)[3])view,out+3);mulVecMat4(pos,(const float(*)[3])view,out+6);mulVecMat44(out+6,(const float(*)[4])projection,out+9);
}
'''
def source_code(directory=None,initialize=False):
 texts={};pins={};snippets=[]
 for name,path in PATHS.items():
  raw=((directory/name) if directory else ROOT.parent/'upstream/ouroboros'/path).read_bytes().replace(b'\r\n',b'\n');texts[name]=raw.decode('latin1');pins[name]={'sha256_lf':sha(raw),'functions':{}}
 for name,func in FUNCTIONS:
  snippet=extract(texts[name],func);pins[name]['functions'][func]=sha(snippet.encode());snippets.append(snippet)
 # Pin RAD's exact double-PI / binary32 reciprocal expression separately.
 rad=re.search(r'(?m)^#define RAD\(a\).*$',texts['mathutil.h']).group(0);pins['mathutil.h']['RAD_macro_sha256']=sha(rad.encode())
 expected_path=HERE/'source-pins.json'
 if initialize:expected_path.write_text(json.dumps({'sources':pins,'scope':'15 unchanged scalar source functions plus RAD; mathutil_sincosf selects original _WIN64 float-libm branch'},indent=2)+'\n')
 require(pins==json.loads(expected_path.read_text())['sources'],'Source or function pins differ')
 return PREAMBLE+'\n'+'\n'.join(snippets)+WRAPPER,pins
def input_block(world):
 if len(world)==520 and world[:8]==b'COHWRI09':return world
 require(world[:8]==b'COHWOR09','World magic differs');off,n=struct.unpack_from('<2I',world,48);require(n==520 and off<=len(world)-n,'World raw math span differs');return world[off:off+n]
def compare(actual,expected,name,stats,tolerance=0.):
 require(len(actual)==len(expected),name+' count differs')
 for x,y in zip(actual,expected):
  error=abs(x-y);stats['components']+=1;stats['maximum_absolute_error']=max(stats['maximum_absolute_error'],error);require(error<=tolerance,f'{name}: {x} vs {y}, error{error}')
def stat():return {'components':0,'maximum_absolute_error':0.}
def qualify(inputs,vertices=None,source_directory=None,compiler='cc'):
 code,pins=source_code(source_directory);nodes,cameras=reference.decode_inputs(inputs);fp=C.POINTER(C.c_float);stats={k:stat() for k in ('local','group_world','view','projection','eye_hierarchy','geometry','independent_reference')};samples={'local':[],'world':[],'cameras':[]}
 with tempfile.TemporaryDirectory(prefix='coh-original-world-') as directory:
  t=Path(directory);p=t/'original.c';p.write_text(code);so=t/'original.so';subprocess.run([*shlex.split(compiler),'-std=c11','-O0','-ffp-contract=off','-fno-strict-aliasing','-shared','-fPIC',str(p),'-lm','-o',str(so)],check=True)
  lib=C.CDLL(str(so));lib.original_group.argtypes=[fp,fp,fp];lib.original_group_eye.argtypes=[fp,fp,fp];lib.original_camera.argtypes=[fp,C.c_uint,C.c_uint,fp,fp];lib.original_vertex.argtypes=[fp,fp,fp,fp,fp,fp]
  nso=t/'native.so';subprocess.run([*shlex.split(compiler),'-std=c11','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-shared','-fPIC',str(ROOT/'world/coh_world.c'),'-lm','-o',str(nso)],check=True);native=types.configure(C.CDLL(str(nso)));mem=(C.c_uint8*520).from_buffer_copy(inputs);parsed=types.Inputs();require(native.coh_world_parse_inputs(mem,520,C.byref(parsed))==0,'Native input rejected')
  raw=(C.c_float*36)(*(v for pos,pyr in nodes for v in [*pos,*pyr]));local=(C.c_float*72)();world=(C.c_float*72)();lib.original_group(raw,local,world);nl=(C.c_float*72)();nw=(C.c_float*72)();require(native.coh_world_group_matrices(C.byref(parsed),nl,nw)==0,'Native group failed');compare(nl,local,'Original local',stats['local']);compare(nw,world,'Original group',stats['group_world']);samples['local']=list(local);samples['world']=list(world)
  pl,pw=reference.group_matrices(nodes);compare([v for m in pl for v in reference.source_columns(m)],local,'Independent local',stats['independent_reference'],1e-4);compare([v for m in pw for v in reference.source_columns(m)],world,'Independent group',stats['independent_reference'],1e-4)
  for i,camera in enumerate(cameras):
   pos,pyr,fovy,aspect,near,far,fx,fy=camera;params=(C.c_float*10)(*pos,*pyr,fovy,aspect,near,far);view=(C.c_float*12)();proj=(C.c_float*16)();lib.original_camera(params,fx,fy,view,proj);nv=(C.c_float*12)();np=(C.c_float*16)();require(native.coh_world_camera(C.byref(parsed),i,0,nv,np)==0,'Native camera failed');compare(nv,view,'Original view',stats['view']);compare(np,proj,'Original projection',stats['projection']);pv,pp=reference.camera_matrices(camera);compare(reference.source_columns(pv),view,'Independent view',stats['independent_reference'],1e-4);compare([pp[r][c] for c in range(4) for r in range(4)],proj,'Independent projection',stats['independent_reference'],1e-4)
   eyes=(C.c_float*72)();ne=(C.c_float*72)();lib.original_group_eye(raw,view,eyes);require(native.coh_world_group_eye_matrices(C.byref(parsed),nv,ne)==0,'Native source eye hierarchy failed');compare(ne,eyes,'Original eye hierarchy',stats['eye_hierarchy']);pe=reference.group_eye_matrices(nodes,pv);compare([v for m in pe for v in reference.source_columns(m)],eyes,'Independent source eye hierarchy',stats['independent_reference'],1e-4);eye=(C.c_float*12)(*eyes[-12:]);n_eye=(C.c_float*12)(*ne[-12:]);sample={'index':i,'view':list(view),'projection':list(proj),'eye_hierarchy':list(eyes),'modelview':list(eye)}
   if vertices:
    actual=[];native_values=[];wm=(C.c_float*12)(*world[-12:]);
    for vertex in vertices:
     p=(C.c_float*3)(*vertex[:3]);n=(C.c_float*3)(*vertex[3:6]);o=(C.c_float*13)();no=(C.c_float*13)();lib.original_vertex(wm,eye,proj,p,n,o);require(native.coh_world_vertex(wm,n_eye,np,p,n,no)==0,'Native vertex failed');compare(no,o,'Original geometry',stats['geometry']);actual.extend(o);native_values.extend(no)
    compare(reference.geometry(pw[-1],pe[-1],pp,vertices),actual,'Independent transformed geometry',stats['independent_reference'],1e-4);sample['geometry']=actual
   samples['cameras'].append(sample)
  # Explicit original perspective flip/aspect/depth witnesses beyond the six scenes.
  witnesses=[]
  for fx,fy,aspect in [(0,0,.5),(1,0,1.),(0,1,2.),(1,1,4.)]:
   pos,pyr,fovy,_,near,far,_,_=cameras[0];params=(C.c_float*10)(*pos,*pyr,fovy,aspect,near,far);v=(C.c_float*12)();p=(C.c_float*16)();lib.original_camera(params,fx,fy,v,p);test=types.Inputs();C.memmove(C.byref(test),C.byref(parsed),C.sizeof(test));test.cameras[0].flip_x=fx;test.cameras[0].flip_y=fy;nv=(C.c_float*12)();np=(C.c_float*16)();require(native.coh_world_camera(C.byref(test),0,aspect,nv,np)==0,'Native projection witness failed');compare(np,p,'Projection flip/aspect witness',stats['projection']);witnesses.append({'flip_x':fx,'flip_y':fy,'aspect':aspect})
 report={'passed':True,'input_sha256':sha(inputs),'nodes':6,'cameras':6,'source_functions':len(FUNCTIONS),'unchanged_source_pins':pins,'stages':stats,'projection_witnesses':witnesses,'source_parity_tolerance':0.,'independent_float_tolerance':1e-4,'limits':['Single-token degree storage compatibility helper','Original _WIN64 sinf/cosf branch selected; original 32-bit x87 fsincos is not executed','No inverse view requested','Controlled camera inputs; no gameplay camera or above-4:3 FOV adjustment','No full Win32 client or original GPU execution']}
 return samples,report
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--world',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--report',required=True,type=Path);p.add_argument('--source-directory',type=Path);p.add_argument('--geometry-input',type=Path);p.add_argument('--compiler',default=os.environ.get('CC','cc'));a=p.parse_args();vertices=None
 if a.geometry_input:vertices=[v for part in json.loads(a.geometry_input.read_text())['vertices'] for v in part]
 samples,report=qualify(input_block(a.world.read_bytes()),vertices,a.source_directory,a.compiler)
 for path,value in [(a.output,samples),(a.report,report)]:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps({'passed':True,'stages':report['stages']}))
if __name__=='__main__':main()
