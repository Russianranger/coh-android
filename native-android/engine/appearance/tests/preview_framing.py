"""Raster bounds, long-clock and inherited-GL-state regression for neutral preview."""
import argparse,ctypes as C,hashlib,importlib.util,json
from pathlib import Path
from PIL import Image,ImageChops
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('framing_gpu',HERE/'preview_gpu.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
a=p.a;U=a.U
def run(library,package,output):
 lib=C.CDLL(str(library));lib.coh_appearance_preview_create.argtypes=[a.api.asset.Bytes,C.POINTER(C.c_void_p)];lib.coh_appearance_preview_draw.argtypes=[C.c_void_p,U,U,U,C.c_double];lib.coh_appearance_preview_destroy.argtypes=[C.c_void_p,C.c_int]
 raw=package.read_bytes();blob=C.create_string_buffer(raw);owner=C.c_void_p();assert lib.coh_appearance_preview_create(a.api.asset.Bytes(C.addressof(blob),len(raw)),C.byref(owner))==0
 e=a.bridge.gpu.EGL();g=e.g;output.mkdir(parents=True,exist_ok=True);rows=[]
 for name,ret,args in [('glGenRenderbuffers',None,[C.c_int,C.POINTER(U)]),('glBindRenderbuffer',None,[U,U]),('glRenderbufferStorage',None,[U,U,C.c_int,C.c_int]),('glFramebufferRenderbuffer',None,[U,U,U,U]),('glDeleteRenderbuffers',None,[C.c_int,C.POINTER(U)]),('glScissor',None,[C.c_int]*4),('glColorMask',None,[C.c_ubyte]*4),('glDepthMask',None,[C.c_ubyte])]:e.gf(name,ret,args)
 try:
  for width,height in [(1920,790),(1080,959),(640,1280),(1280,480)]:
   target=e.texture(width,height);fbo=U();g.glGenFramebuffers(1,C.byref(fbo));g.glBindFramebuffer(0x8d40,fbo);g.glFramebufferTexture2D(0x8d40,0x8ce0,0xde1,target,0)
   depth=U();g.glGenRenderbuffers(1,C.byref(depth));g.glBindRenderbuffer(0x8d41,depth);g.glRenderbufferStorage(0x8d41,0x81a6,width,height);g.glFramebufferRenderbuffer(0x8d40,0x8d00,0x8d41,depth);assert g.glCheckFramebufferStatus(0x8d40)==0x8cd5
   frames=[]
   for seconds in [0.,.8,1.2,2.,3.,4.,10.,3600.,86400.]:
    # Model the nonzero viewport/scissor and disabled depth state left by a HUD.
    g.glViewport(13,17,width//2,height//3);g.glEnable(0xc11);g.glScissor(7,11,19,23);g.glDisable(0xb71);g.glDepthMask(0);g.glColorMask(0,0,0,0)
    assert lib.coh_appearance_preview_draw(owner,width,height,1,seconds)==0
    pixels=C.create_string_buffer(width*height*4);g.glReadPixels(0,0,width,height,0x1908,0x1401,pixels);assert g.glGetError()==0
    im=Image.frombytes('RGBA',(width,height),pixels.raw).transpose(Image.Transpose.FLIP_TOP_BOTTOM).convert('RGB');bbox=ImageChops.difference(im,Image.new('RGB',im.size,im.getpixel((0,0)))).getbbox()
    bounded=bool(bbox and bbox[0]>=width*.12 and bbox[1]>=height*.12 and bbox[2]<=width*.88 and bbox[3]<=height*.88)
    item={'seconds':seconds,'bbox':bbox,'normalized_bbox':[round(v/d,5) for v,d in zip(bbox,(width,height,width,height))] if bbox else None,'fully_framed':bounded,'sha256':hashlib.sha256(pixels.raw).hexdigest()};frames.append(item)
    if seconds==0 or not bounded:im.save(output/f'framing-{width}x{height}-{seconds:g}.png')
   rows.append({'width':width,'height':height,'frames':frames,'same_pose_at_all_clocks':len({x['sha256'] for x in frames})==1})
   g.glDeleteFramebuffers(1,C.byref(fbo));g.glDeleteTextures(1,C.byref(target));g.glDeleteRenderbuffers(1,C.byref(depth))
  result={'passed':all(row['same_pose_at_all_clocks'] and all(x['fully_framed'] for x in row['frames']) for row in rows),'identity':e.identity,'source_pose':'first source frame, neutral morphology','package_sha256':hashlib.sha256(raw).hexdigest(),'inherited_gl_state_reset':True,'frames':sum(len(row['frames']) for row in rows),'aspects':rows,'android':False,'physical_thor':False};(output/'framing.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:lib.coh_appearance_preview_destroy(owner,1);e.close()
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--library',type=Path,required=True);parser.add_argument('--package',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);x=parser.parse_args();result=run(x.library,x.package,x.output);print(json.dumps({'passed':result['passed'],'frames':result['frames'],'aspects':len(result['aspects'])}));raise SystemExit(0 if result['passed'] else 1)
