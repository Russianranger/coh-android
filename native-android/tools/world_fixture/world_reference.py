#!/usr/bin/env python3
"""Independent row-matrix reference for a bounded authored Atlas branch.

This implementation uses ordinary mathematical row matrices, explicit binary32
rounding, and independent Python trig. It never calls the native runtime. The
six cameras are controlled inputs aimed by authored-style PYR; no captured game
camera, gameplay FOV adjustment or full Atlas lighting is claimed.
"""
from pathlib import Path
import argparse,ctypes,json,math,struct
NODE_INPUTS=[
 ([511.380371,426.,-703.999756],[0.,0.,0.]),
 ([-296.317322,-417.42926,-280.957397],[0.,0.,0.]),
 ([408.936951,33.42926,-431.042847],[0.,89.999985,-0.]),
 ([0.,0.,0.],[0.,0.,0.]),
 ([24.5,32.,-40.],[0.,0.,0.]),
 ([0.,0.,0.],[0.,90.000038,0.])]
def f32(v):return ctypes.c_float(v).value
def rounded_sum(values):
 values=list(values);result=values[0]
 for v in values[1:]:result=f32(result+v)
 return result
def multiply(a,b):
 return [[rounded_sum(f32(a[r][k]*b[k][c]) for k in range(3)) if c<3 else rounded_sum([*(f32(a[r][k]*b[k][3]) for k in range(3)),a[r][3]]) for c in range(4)] for r in range(3)]
def rotation(degrees):
 p,y,r=[f32(f32(v)*math.pi*f32(1./180.)) for v in degrees]
 sp,cp,sy,cy,sr,cr=[f32(x) for x in (math.sin(p),math.cos(p),math.sin(y),math.cos(y),math.sin(r),math.cos(r))]
 t=f32(sy*sp);u=f32(-cy*sp)
 return [[f32(f32(cy*cr)+f32(t*sr)),f32(f32(cy*sr)-f32(t*cr)),f32(sy*cp)],
         [f32(-cp*sr),f32(cp*cr),sp],
         [f32(f32(-sy*cr)-f32(u*sr)),f32(f32(-sy*sr)+f32(u*cr)),f32(cy*cp)]]
def local(position,degrees):return [row+[f32(position[i])] for i,row in enumerate(rotation(degrees))]
def source_columns(m):return [m[r][c] for c in range(4) for r in range(3)]
def row_matrix(values):return [[values[c*3+r] for c in range(4)] for r in range(3)]
def transform(m,v,point=True):
 return [rounded_sum([*(f32(m[r][k]*v[k]) for k in range(3)),m[r][3]]) if point else rounded_sum(f32(m[r][k]*v[k]) for k in range(3)) for r in range(3)]
def group_matrices(nodes=NODE_INPUTS):
 locals=[local(pos,pyr) for pos,pyr in nodes];world=[]
 for i,m in enumerate(locals):world.append(multiply(world[i-1],m) if i else m)
 return locals,world
def group_eye_matrices(nodes,view):
 locals=[local(pos,pyr) for pos,pyr in nodes];eyes=[]
 for i,m in enumerate(locals):eyes.append(multiply(eyes[i-1] if i else view,m))
 return eyes
def camera_matrices(camera):
 pos,pyr,fov,aspect,near,far,fx,fy=camera
 cam=local(pos,pyr);rot=[[cam[c][r] for c in range(3)] for r in range(3)]
 # Original rdrFixMat applies X mirror on the left of the transposed rotation.
 mirrored=[[rounded_sum(f32(((-1. if r==0 else 1.) if r==k else 0.)*rot[k][c]) for k in range(3)) for c in range(3)] for r in range(3)]
 translation=[rounded_sum(f32(mirrored[r][k]*f32(-pos[k])) for k in range(3)) for r in range(3)]
 view=[mirrored[r]+[translation[r]] for r in range(3)]
 t=f32(near*math.tan(fov*math.pi/360.));b=-t;l=f32(b*aspect);right=f32(t*aspect)
 if fy:t=-t;b=-b
 if fx:l=-l;right=-right
 p=[[0.]*4 for _ in range(4)]
 p[0][0]=f32(f32(2*near)/f32(right-l));p[1][1]=f32(f32(2*near)/f32(t-b));p[0][2]=f32(f32(right+l)/f32(right-l));p[1][2]=f32(f32(t+b)/f32(t-b));p[2][2]=f32(-f32(far+near)/f32(far-near));p[3][2]=-1.;p[2][3]=f32(f32(f32(-2*far)*near)/f32(far-near))
 return view,p
def geometry(world,modelview,projection,vertices):
 out=[]
 for vertex in vertices:
  pos,normal=vertex[:3],vertex[3:6];wp=transform(world,pos);en=transform(modelview,normal,False);ep=transform(modelview,pos);clip=[rounded_sum([*(f32(projection[r][k]*ep[k]) for k in range(3)),projection[r][3]]) for r in range(4)]
  out.extend([*wp,*en,*ep,*clip])
 return out
def make_inputs(vertices):
 if not vertices or len(vertices)!=512:raise ValueError('Expected two source partitions, 512 canonical vertices')
 _,world=group_matrices();points=[transform(world[-1],v[:3]) for v in vertices];lo=[min(p[j] for p in points) for j in range(3)];hi=[max(p[j] for p in points) for j in range(3)];center=[f32((lo[j]+hi[j])*.5) for j in range(3)];radius=math.sqrt(sum(((hi[j]-lo[j])*.5)**2 for j in range(3)));distance=f32(max(radius*4.,14.))
 cameras=[]
 for pitch,yaw,fovy,aspect in [(12.,0.,50.,1.),(18.,35.,55.,4./3.),(10.,-35.,60.,16./9.),(14.,110.,45.,1.),(20.,-110.,65.,.75),(15.,175.,50.,1.5)]:
  pyr=[pitch,yaw,0.];rot=rotation(pyr);pos=[f32(center[j]+f32(rot[j][2]*distance)) for j in range(3)];cameras.append((pos,pyr,f32(fovy),f32(aspect),1.,200.,0,0))
 out=bytearray(64);out[:8]=b'COHWRI09';struct.pack_into('<9I',out,8,1,64,6,6,64,232,520,28,48)
 for i,(pos,pyr) in enumerate(NODE_INPUTS):out.extend(struct.pack('<I6f',0xffffffff if i==0 else i-1,*pos,*pyr))
 for pos,pyr,fovy,aspect,near,far,fx,fy in cameras:out.extend(struct.pack('<10f2I',*pos,*pyr,fovy,aspect,near,far,fx,fy))
 if len(out)!=520:raise ValueError('Input block size differs')
 return bytes(out)
def decode_inputs(raw):
 if len(raw)!=520 or raw[:8]!=b'COHWRI09':raise ValueError('Input block differs')
 nodes=[];cameras=[]
 for i in range(6):v=struct.unpack_from('<I6f',raw,64+i*28);nodes.append((list(v[1:4]),list(v[4:7])))
 for i in range(6):v=struct.unpack_from('<10f2I',raw,232+i*48);cameras.append((list(v[:3]),list(v[3:6]),*v[6:]))
 return nodes,cameras
def generate(inputs,vertices):
 if len(vertices)!=512:raise ValueError('Reference requires 512 canonical vertices')
 nodes,cameras=decode_inputs(inputs);locals,world=group_matrices(nodes);stride=160+512*52;out=bytearray(64);out[:8]=b'COHWRF09';struct.pack_into('<12I',out,8,1,64,6,6,512,2,64,352,640,stride,640+6*stride,160)
 for m in [*locals,*world]:out.extend(struct.pack('<12f',*source_columns(m)))
 for camera in cameras:
  view,projection=camera_matrices(camera);eye=group_eye_matrices(nodes,view)[-1];out.extend(struct.pack('<12f',*source_columns(view)));out.extend(struct.pack('<16f',*(projection[r][c] for c in range(4) for r in range(4))));out.extend(struct.pack('<12f',*source_columns(eye)));out.extend(struct.pack('<6656f',*geometry(world[-1],eye,projection,vertices)))
 if len(out)!=161344:raise ValueError('Reference size differs')
 return bytes(out)
def self_check():
 identity=local([0,0,0],[0,0,0]);assert source_columns(identity)==[1,0,0,0,1,0,0,0,1,0,0,0]
 view,p=camera_matrices(([0,0,10],[0,0,0],60.,1.,1.,200.,0,0));assert transform(view,[2,3,0])==[-2.,3.,-10.];assert p[3][2]==-1.
 for aspect in [.5,1.,4./3.,16./9.,4.]:
  _,p=camera_matrices(([0,0,0],[0,0,0],60.,aspect,1.,200.,0,0))
  for distance,expected in [(1.,-1.),(200.,1.)]:
   v=[0.,0.,-distance,1.];clip=[sum(p[r][k]*v[k] for k in range(4)) for r in range(4)];assert abs(clip[2]/clip[3]-expected)<1e-6
 return {'passed':True,'row_matrix_reference':True,'x_mirror_witness':True,'clip_z_convention':True,'near_far_plane_witnesses':10,'aspect_witnesses':5}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--self-check',action='store_true');a=p.parse_args()
 if not a.self_check:p.error('--self-check is required for standalone invocation')
 print(json.dumps(self_check()))
if __name__=='__main__':main()
