#!/usr/bin/env python3
"""Numeric report controls for asynchronous fullscreen resize readiness only."""
import copy,unittest
from emulator_check import ResizedPreview,viewport_contract

def report(epoch=3,frames=58,width=1080,height=718,fullscreen=False,contexts=1,time=5122):
 return {'session_id':'retained-activity','updated_at':str(time),'assets_verified':True,'resumed':True,'failure':None,'report_write_failed':False,'preview_is_server_world':False,
  'viewport_policy':{'schema':'coh-native-viewport-v1','maximum_controls_percent':60,'minimum_aspect':.25,'maximum_aspect':8,'maximum_dimension':16384,'host_width':width,'host_height':height,'fullscreen':fullscreen},
  'input_area':{'left':0,'top':0,'width':width,'height':height,'shown':True,'surface_ready':True},
  'native':{'valid':True,'failed':False,'running':True,'foreground':True,'objects_released':False,'frames':frames,'epoch':epoch,'total_ms':time,'contexts_started':contexts,'contexts_completed':contexts-1,'width':width,'height':height,'gl_errors':0,'tf_mismatches':0,
   'world_visible_pixels':1,'actor_visible_pixels':1,'world_occludes_actor_pixels':1,'actor_occludes_world_pixels':1,'actor_changed_pixels':1,'static_renderer':{'gpu_bytes':100,'tf_mismatches':0,'visible_pixels':1}}}

def full(frames=400,epoch=6,contexts=3,time=21000):return report(epoch,frames,1920,1080,True,contexts,time)

class ReadinessControls(unittest.TestCase):
 def test_actual_failure_shape_cannot_pass_old_frame_threshold(self):
  before=report();wait=ResizedPreview(before,True);stale=full(387,time=20292)
  stale['native'].update(width=1080,height=718)
  self.assertGreater(stale['native']['frames'],before['native']['frames']+12)
  with self.assertRaisesRegex(AssertionError,'stale EGL viewport'):viewport_contract(stale)
  self.assertFalse(wait(stale));self.assertIsNone(wait.anchor)
  self.assertFalse(wait(full()));self.assertFalse(wait(full(412,time=22000)))
  self.assertTrue(wait(full(413,time=22000)))
 def test_epoch_context_session_and_report_time_must_be_fresh(self):
  before=report()
  for changed in ('epoch','contexts','session','phase','foreground'):
   bad=full()
   if changed=='epoch':bad['native']['epoch']=3
   if changed=='contexts':bad['native'].update(contexts_started=1,contexts_completed=0)
   if changed=='session':bad['session_id']='replacement'
   if changed=='phase':bad['viewport_policy']['fullscreen']=False
   if changed=='foreground':bad['native']['foreground']=False
   with self.subTest(changed=changed):self.assertFalse(ResizedPreview(before,True)(bad))
  wait=ResizedPreview(before,True);anchor=full();self.assertFalse(wait(anchor))
  value=full(413);self.assertFalse(wait(value))
  value['native']['total_ms']+=100;self.assertFalse(wait(value))
  value['updated_at']='newer';self.assertTrue(wait(value))
 def test_intermediate_resize_resets_new_frame_anchor(self):
  wait=ResizedPreview(report(),True);self.assertFalse(wait(full()))
  self.assertFalse(wait(full(440,epoch=7,contexts=4,time=23000)))
  self.assertFalse(wait(full(452,epoch=7,contexts=4,time=24000)))
  self.assertTrue(wait(full(453,epoch=7,contexts=4,time=24000)))
 def test_portrait_or_undersized_fullscreen_never_satisfies_landscape(self):
  for width,height in ((1080,1920),(639,360)):
   wait=ResizedPreview(report(),True);value=report(6,400,width,height,True,3,21000)
   self.assertFalse(wait(value));self.assertIsNone(wait.anchor)
 def test_return_requires_coherent_new_context_and_new_frames(self):
  before=full();wait=ResizedPreview(before,False)
  restored=report(8,500,1080,718,False,4,100);self.assertFalse(wait(restored))
  current=report(8,513,1080,718,False,4,200);self.assertTrue(wait(current))
  invalid=copy.deepcopy(current);invalid['native']['width']=1920
  self.assertFalse(wait(invalid));self.assertIsNone(wait.anchor)
if __name__=='__main__':unittest.main()
