#!/usr/bin/env python3
"""Report and driver controls for fullscreen resize and first-immersive education."""
import copy,unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
from emulator_check import ResizedPreview,viewport_contract,Check,PACKAGE

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

EDUCATION='''<hierarchy><node package="android" class="android.widget.TextView" resource-id="android:id/immersive_cling_title" text="Viewing full screen"/><node package="android" class="android.widget.TextView" resource-id="android:id/immersive_cling_description" text="To exit, swipe down from the top."/><node package="android" class="android.widget.Button" resource-id="android:id/ok" text="Got it" enabled="true" clickable="true" bounds="[1123,464][1354,590]"/></hierarchy>'''
APP='''<hierarchy><node package="org.coh.nativecombined" class="android.widget.Button" text="RETURN TO CONTROLS" content-desc="Return to native client controls" enabled="true" clickable="true" bounds="[1480,24][1896,168]"/></hierarchy>'''

class FullscreenDriver(Check):
 def __init__(self,frames=()):self.frames=list(frames);self.commands=[];self.records=[];self.dumps=0
 def adb(self,*args,**kwargs):self.commands.append(args)
 def dump(self):self.dumps+=1;return ET.fromstring(self.frames.pop(0))
 def record(self,*args,**kwargs):self.records.append((args,kwargs))

class ImmersiveEducationControls(unittest.TestCase):
 def test_specific_system_education_is_clicked_once_then_app_corner_is_proved(self):
  driver=FullscreenDriver([APP]);root=driver.dismiss_immersive_education(ET.fromstring(EDUCATION))
  self.assertEqual(driver.commands,[('shell','input','tap',1238,527)])
  self.assertEqual(driver.dumps,1)
  self.assertEqual(driver.fullscreen_corner(root,full()),[1480,24,1896,168])
  with self.assertRaises(AssertionError):driver.dismiss_immersive_education(ET.fromstring(EDUCATION))
  self.assertEqual(len(driver.commands),1)
 def test_no_blanket_got_it_dismissal_or_invented_corner(self):
  for xml in (EDUCATION.replace('android:id/immersive_cling_title','android:id/other_title'),EDUCATION.replace('Viewing full screen','Unrelated dialog')):
   driver=FullscreenDriver();root=ET.fromstring(xml)
   self.assertIs(driver.dismiss_immersive_education(root),root)
   self.assertEqual(driver.commands,[])
   with self.assertRaises(AssertionError):driver.fullscreen_corner(root,full())
 def test_wrong_package_class_label_disabled_and_unbounded_targets_refuse_without_click(self):
  for old,new in [('package="android" class="android.widget.Button"','package="'+PACKAGE+'" class="android.widget.Button"'),('text="Got it"','text="Allow"'),('class="android.widget.Button"','class="android.widget.TextView"'),('enabled="true"','enabled="false"'),('clickable="true"','clickable="false"'),('[1123,464][1354,590]','[0,0][0,0]')]:
   driver=FullscreenDriver()
   with self.subTest(change=new),self.assertRaises(AssertionError):driver.dismiss_immersive_education(ET.fromstring(EDUCATION.replace(old,new)))
   self.assertEqual(driver.commands,[])
 def test_corner_requires_app_identity_clickability_real_bounds_and_hidden_controls(self):
  for old,new in [('package="'+PACKAGE+'"','package="android"'),('class="android.widget.Button"','class="android.widget.TextView"'),('enabled="true"','enabled="false"'),('clickable="true"','clickable="false"'),('Return to native client controls','Unrelated'),('[1480,24][1896,168]','[0,800][100,900]')]:
   with self.subTest(change=new),self.assertRaises(AssertionError):FullscreenDriver().fullscreen_corner(ET.fromstring(APP.replace(old,new)),full())
  visible=APP.replace('</hierarchy>','<node content-desc="Native client controls"/></hierarchy>')
  with self.assertRaises(AssertionError):FullscreenDriver().fullscreen_corner(ET.fromstring(visible),full())
 def test_reacquisition_is_bounded_and_does_not_bypass_unknown_overlay(self):
  driver=FullscreenDriver(['<hierarchy/>' for _ in range(3)])
  with patch('emulator_check.time.sleep'),self.assertRaisesRegex(AssertionError,'App hierarchy'):
   driver.dismiss_immersive_education(ET.fromstring(EDUCATION))
  self.assertEqual(driver.dumps,3);self.assertEqual(len(driver.commands),1)
  driver=FullscreenDriver();app=ET.fromstring(APP)
  self.assertIs(driver.dismiss_immersive_education(app),app);self.assertEqual(driver.commands,[])
if __name__=='__main__':unittest.main()
