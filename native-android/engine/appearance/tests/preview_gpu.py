"""Exercise the production preview owner, real GL contexts and failure recovery."""
import argparse,ctypes as C,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('preview_actor_gpu',HERE/'actor_gpu.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
U,Z,Q=a.U,a.Z,C.c_uint64
class Stats(C.Structure):_fields_=[('frames',Q),('draws',Q),('surface_uploads',Q),('failures',Q),('owned_cpu_bytes',Z),('borrowed_package_bytes',Z),('gpu_buffer_bytes',Z),('texture_bytes',Z),('surface_generation',U),('parts',U),('vertices',U),('indices',U)]
def run(library,package,output):
 lib=C.CDLL(str(library));lib.coh_appearance_preview_create.argtypes=[a.api.asset.Bytes,C.POINTER(C.c_void_p)];lib.coh_appearance_preview_draw.argtypes=[C.c_void_p,U,U,U,C.c_double];lib.coh_appearance_preview_surface_lost.argtypes=[C.c_void_p,C.c_int];lib.coh_appearance_preview_destroy.argtypes=[C.c_void_p,C.c_int];lib.coh_appearance_preview_stats.argtypes=[C.c_void_p];lib.coh_appearance_preview_stats.restype=Stats
 raw=package.read_bytes();blob=C.create_string_buffer(raw);owner=C.c_void_p();assert lib.coh_appearance_preview_create(a.api.asset.Bytes(C.addressof(blob),len(raw)),C.byref(owner))==0
 original=owner.value;assert lib.coh_appearance_preview_create(a.api.asset.Bytes(C.addressof(blob),len(raw)),C.byref(owner))==1 and owner.value==original
 e=a.bridge.gpu.EGL();g=e.g;output.mkdir(parents=True,exist_ok=True);contexts=[];recovery=[]
 try:
  for cycle in range(2):
   if cycle:lib.coh_appearance_preview_surface_lost(owner,0);e.recreate_context()
   target=e.texture(512,640);fbo=U();g.glGenFramebuffers(1,C.byref(fbo));g.glBindFramebuffer(0x8d40,fbo);g.glFramebufferTexture2D(0x8d40,0x8ce0,0xde1,target,0)
   e.gf('glGenRenderbuffers',None,[C.c_int,C.POINTER(U)]);e.gf('glBindRenderbuffer',None,[U,U]);e.gf('glRenderbufferStorage',None,[U,U,C.c_int,C.c_int]);e.gf('glFramebufferRenderbuffer',None,[U,U,U,U]);e.gf('glDeleteRenderbuffers',None,[C.c_int,C.POINTER(U)])
   depth=U();g.glGenRenderbuffers(1,C.byref(depth));g.glBindRenderbuffer(0x8d41,depth);g.glRenderbufferStorage(0x8d41,0x81a6,512,640);g.glFramebufferRenderbuffer(0x8d40,0x8d00,0x8d41,depth);assert g.glCheckFramebufferStatus(0x8d40)==0x8cd5
   frames=[]
   for step,seconds in enumerate([0.,2.05,4.0]):
    assert lib.coh_appearance_preview_draw(owner,512,640,cycle+1,seconds)==0
    pixels=C.create_string_buffer(512*640*4);g.glReadPixels(0,0,512,640,0x1908,0x1401,pixels);assert g.glGetError()==0
    from PIL import Image
    data=pixels.raw;image=output/f'preview-context{cycle+1}-pose{step+1}.png';Image.frombytes('RGBA',(512,640),data).transpose(Image.Transpose.FLIP_TOP_BOTTOM).save(image)
    count=sum(data[i:i+4]!=data[:4] for i in range(0,len(data),4));assert count>3000
    frames.append({'seconds':seconds,'visible_pixels':count,'sha256':hashlib.sha256(data).hexdigest(),'image':image.name})
   stable=lib.coh_appearance_preview_stats(owner)
   for step in range(50):assert lib.coh_appearance_preview_draw(owner,512,640,cycle+1,step/30)==0
   after=lib.coh_appearance_preview_stats(owner);assert after.surface_uploads==stable.surface_uploads and after.owned_cpu_bytes==stable.owned_cpu_bytes and after.gpu_buffer_bytes==stable.gpu_buffer_bytes
   if hasattr(lib,'coh_preview_test_submit_failure'):
    lib.coh_preview_test_submit_failure(4);assert lib.coh_appearance_preview_draw(owner,512,640,cycle+1,0)==1
    assert lib.coh_appearance_preview_draw(owner,512,640,cycle+1,0)==0;recovery.append('partial batch submission discarded; next frame succeeds')
    lib.coh_appearance_preview_surface_lost(owner,1);lib.coh_preview_test_upload_failure(1);assert lib.coh_appearance_preview_draw(owner,512,640,cycle+1,0)==6
    assert lib.coh_appearance_preview_draw(owner,512,640,cycle+1,0)==0;recovery.append('texture upload error releases staged GL objects; next frame succeeds')
   contexts.append({'generation':cycle+1,'frames':frames,'gl_errors':0,'steady_frame_allocated_bytes_unchanged':True,'steady_frame_upload_counter_unchanged':True})
   # Leave first-context names to context destruction, exercise alive=0 path.
   if cycle:g.glDeleteFramebuffers(1,C.byref(fbo));g.glDeleteTextures(1,C.byref(target));g.glDeleteRenderbuffers(1,C.byref(depth))
  assert [x['sha256'] for x in contexts[0]['frames']]==[x['sha256'] for x in contexts[1]['frames']]
  stats=lib.coh_appearance_preview_stats(owner);result={'passed':True,'identity':e.identity,'package_sha256':hashlib.sha256(raw).hexdigest(),'contexts':contexts,'recovery':recovery,'stats':{k:getattr(stats,k) for k,_ in Stats._fields_},'android':False,'physical_thor':False,'scope':'Complete source-menu neutral Male preview through production owner; not original full-client image equivalence, custom morphology, Female/Huge, or full Gate31'}
  (output/'preview-gpu.json').write_text(json.dumps(result,indent=2)+'\n');return result
 finally:lib.coh_appearance_preview_destroy(owner,1);e.close()
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--library',type=Path,required=True);p.add_argument('--package',type=Path,required=True);p.add_argument('--output',type=Path,required=True);x=p.parse_args();print(json.dumps(run(x.library,x.package,x.output)))
