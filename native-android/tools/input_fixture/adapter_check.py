#!/usr/bin/env python3
"""Execute the actual InputAdapter with bounded host Android/JSON transport stubs.

This verifies adapter accounting and calls, not Android framework behavior.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'native-android/systems-probe/app/src/main/java/org/coh/systemsprobe/InputAdapter.java'
STUBS = {
    'android/hardware/input/InputManager.java': '''package android.hardware.input;
public class InputManager { public interface InputDeviceListener {
void onInputDeviceAdded(int id);void onInputDeviceChanged(int id);void onInputDeviceRemoved(int id);}}
''',
    'android/view/InputDevice.java': '''package android.view;
import java.util.HashSet;import java.util.Set;
public class InputDevice {
public static final int SOURCE_GAMEPAD=0x401,SOURCE_JOYSTICK=0x1000010,SOURCE_DPAD=0x201,SOURCE_KEYBOARD=0x101,SOURCE_TOUCHSCREEN=0x1002;
private final Set<Integer> axes=new HashSet<Integer>();
public InputDevice(int... declaredAxes){for(int axis:declaredAxes)axes.add(axis);}
public MotionRange getMotionRange(int axis,int source){return axes.contains(axis)?new MotionRange():null;}
public static class MotionRange {public float getFlat(){return 0;}}
}
''',
    'android/view/KeyEvent.java': '''package android.view;
public class KeyEvent {
public static final int ACTION_DOWN=0,ACTION_UP=1;
public static final int KEYCODE_BUTTON_A=96,KEYCODE_BUTTON_B=97,KEYCODE_BUTTON_X=99,KEYCODE_BUTTON_Y=100,
KEYCODE_BUTTON_L1=102,KEYCODE_BUTTON_R1=103,KEYCODE_BUTTON_L2=104,KEYCODE_BUTTON_R2=105,
KEYCODE_BUTTON_SELECT=109,KEYCODE_BUTTON_START=108,KEYCODE_BUTTON_THUMBL=106,KEYCODE_BUTTON_THUMBR=107,
KEYCODE_DPAD_UP=19,KEYCODE_DPAD_DOWN=20,KEYCODE_DPAD_LEFT=21,KEYCODE_DPAD_RIGHT=22,
KEYCODE_SPACE=62,KEYCODE_ENTER=66,KEYCODE_W=51,KEYCODE_S=47,KEYCODE_A=29,KEYCODE_D=32;
public int getKeyCode(){return 0;} public int getSource(){return 0;}public int getDeviceId(){return -1;}
public int getAction(){return 0;}public int getRepeatCount(){return 0;}
}
''',
    'android/view/MotionEvent.java': '''package android.view;
import java.util.HashMap;import java.util.Map;
public class MotionEvent {
public static final int ACTION_DOWN=0,ACTION_UP=1,ACTION_MOVE=2,ACTION_CANCEL=3,ACTION_POINTER_DOWN=5,ACTION_POINTER_UP=6;
public static final int AXIS_X=0,AXIS_Y=1,AXIS_Z=11,AXIS_RX=12,AXIS_RY=13,AXIS_RZ=14,AXIS_HAT_X=15,AXIS_HAT_Y=16;
private final int action,id,source;private final float x,y;private float[][] history=new float[0][];
private final Map<Integer,Float> axes=new HashMap<Integer,Float>();private InputDevice device;private int deviceId=-1;
public MotionEvent(int a,int i,float xx,float yy,int s){action=a;id=i;x=xx;y=yy;source=s;}
public MotionEvent history(float[][] h){history=h;return this;}
public MotionEvent device(int id,InputDevice d){deviceId=id;device=d;return this;}
public MotionEvent axis(int axis,float value){axes.put(axis,value);return this;}
public int getSource(){return source;}public int getActionMasked(){return action;}public int getActionIndex(){return 0;}
public int getDeviceId(){return deviceId;}public InputDevice getDevice(){return device;}
public float getAxisValue(int axis){Float value=axes.get(axis);return value==null?0:value;}public int getPointerId(int index){return id;}
public float getX(int index){return x;}public float getY(int index){return y;}
public int findPointerIndex(int pointer){return pointer==id?0:-1;}public int getHistorySize(){return history.length;}
public float getHistoricalX(int index,int h){return history[h][0];}public float getHistoricalY(int index,int h){return history[h][1];}
}
''',
    'org/json/JSONException.java': '''package org.json;
public class JSONException extends Exception {private static final long serialVersionUID=1L;public JSONException(String s){super(s);}}
''',
    'org/json/JSONObject.java': '''package org.json;
import java.util.HashMap;import java.util.Map;
public class JSONObject {
private final Map<String,Object> data=new HashMap<String,Object>();
public JSONObject put(String key,Object value)throws JSONException{data.put(key,value);return this;}
public JSONObject getJSONObject(String key){return (JSONObject)data.get(key);}
public int getInt(String key){return ((Number)data.get(key)).intValue();}
public long getLong(String key){return ((Number)data.get(key)).longValue();}
}
''',
    'org/coh/systemsprobe/AdapterHostCheck.java': '''package org.coh.systemsprobe;
import android.view.InputDevice;import android.view.MotionEvent;import org.json.JSONObject;
import java.util.ArrayList;import java.util.List;
public class AdapterHostCheck {
static int checks;static void check(boolean good){checks++;if(!good)throw new AssertionError("check "+checks);}
static class Sink implements InputAdapter.Sink {
 final List<Integer> actions=new ArrayList<Integer>();int lastId;float lastX,lastY;
 float[] lastAxes;int axisCalls;
 public void focus(boolean focus){}public void key(int key,boolean down){}
 public void axes(float x,float y,float z,float rz){lastAxes=new float[]{x,y,z,rz};axisCalls++;}
 public void touch(int action,int id,float x,float y){actions.add(action);lastId=id;lastX=x;lastY=y;}
}
static MotionEvent e(int a,int id,float x,float y){return new MotionEvent(a,id,x,y,InputDevice.SOURCE_TOUCHSCREEN);}
static JSONObject external(InputAdapter a)throws Exception{return a.report().getJSONObject("external_android");}
static void endpoint(int sx,int sy,int ex,int ey,int expected)throws Exception{
 Sink sink=new Sink();InputAdapter a=new InputAdapter(sink);
 check(a.dispatchTouchEvent(e(0,7,sx,sy),100,100));check(a.dispatchTouchEvent(e(1,7,ex,ey),100,100));
 JSONObject c=external(a);check(c.getInt("touch_motion_directions")==expected);
 check(c.getLong("touch_begin")==1&&c.getLong("touch_end")==1&&c.getLong("touch_move")==0);
 check(sink.actions.size()==2&&sink.actions.get(0)==0&&sink.actions.get(1)==2);
 check(sink.lastId==7&&sink.lastX==ex*2f/100-1&&sink.lastY==ey*2f/100-1);
}
public static void main(String[] args)throws Exception{
 // Endpoint-only callbacks still carry actual motion into native END processing.
 endpoint(25,50,75,50,2);endpoint(75,50,25,50,1);
 endpoint(50,25,50,75,8);endpoint(50,75,50,25,4);endpoint(50,50,50,50,0);
 Sink sink=new Sink();InputAdapter a=new InputAdapter(sink);
 a.dispatchTouchEvent(e(0,5,25,50),100,100);
 a.dispatchTouchEvent(e(6,9,75,50),100,100);
 check(external(a).getInt("touch_motion_directions")==0&&external(a).getLong("touch_end")==0);
 check(sink.actions.size()==1); // Other pointer's UP cannot invent END or movement.
 a.dispatchTouchEvent(e(1,5,75,50),100,100);
 check(external(a).getInt("touch_motion_directions")==2&&external(a).getLong("touch_end")==1);
 check(external(a).getLong("touch_move")==0&&sink.actions.size()==2);
 sink=new Sink();a=new InputAdapter(sink);a.dispatchTouchEvent(e(0,3,25,25),100,100);
 a.dispatchTouchEvent(e(2,3,50,50).history(new float[][]{{35,35},{40,40}}),100,100);
 a.dispatchTouchEvent(e(1,3,75,75),100,100);
 check(external(a).getLong("touch_move")==3); // Actual two history samples plus current MOVE only.
 check(external(a).getLong("touch_end")==1&&external(a).getInt("touch_motion_directions")==10);
 check(sink.actions.size()==5&&sink.actions.get(4)==2);
 sink=new Sink();a=new InputAdapter(sink);
 check(!a.dispatchTouchEvent(new MotionEvent(0,1,25,25,InputDevice.SOURCE_JOYSTICK),100,100));
 check(external(a).getLong("touch_begin")==0&&sink.actions.isEmpty());
 a.setSynthetic(true);a.dispatchTouchEvent(e(0,4,25,50),100,100);a.dispatchTouchEvent(e(1,4,75,50),100,100);a.setSynthetic(false);
 check(external(a).getInt("touch_motion_directions")==0&&external(a).getLong("touch_end")==0);
 JSONObject synthetic=a.report().getJSONObject("in_app_synthetic");
 check(synthetic.getInt("touch_motion_directions")==2&&synthetic.getLong("touch_move")==0&&synthetic.getLong("touch_end")==1);
 sink=new Sink();a=new InputAdapter(sink);a.dispatchTouchEvent(e(0,8,25,50),100,100);a.dispatchTouchEvent(e(3,8,75,50),100,100);
 check(external(a).getInt("touch_motion_directions")==0&&external(a).getLong("touch_cancel")==1);
 check(external(a).getLong("touch_move")==0&&external(a).getLong("touch_end")==0&&sink.actions.get(1)==3);
 // Device declarations, not nonzero samples, choose the physical right-stick layout.
 sink=new Sink();a=new InputAdapter(sink);
 MotionEvent primary=new MotionEvent(2,0,0,0,InputDevice.SOURCE_JOYSTICK)
     .device(17,new InputDevice(MotionEvent.AXIS_Z,MotionEvent.AXIS_RZ,MotionEvent.AXIS_RX,MotionEvent.AXIS_RY))
     .axis(MotionEvent.AXIS_RX,1).axis(MotionEvent.AXIS_RY,-1);
 check(a.dispatchGenericMotionEvent(primary));
 check(sink.axisCalls==1&&sink.lastAxes[2]==0&&sink.lastAxes[3]==0);
 check(external(a).getInt("right_axis_directions")==0);
 primary.axis(MotionEvent.AXIS_Z,-1).axis(MotionEvent.AXIS_RZ,1);
 check(a.dispatchGenericMotionEvent(primary));
 check(sink.lastAxes[2]==-1&&sink.lastAxes[3]==1);
 check(external(a).getInt("right_axis_directions")==9);
 sink=new Sink();a=new InputAdapter(sink);
 MotionEvent alternate=new MotionEvent(2,0,0,0,InputDevice.SOURCE_JOYSTICK)
     .device(18,new InputDevice(MotionEvent.AXIS_RX,MotionEvent.AXIS_RY))
     .axis(MotionEvent.AXIS_Z,-1).axis(MotionEvent.AXIS_RZ,1)
     .axis(MotionEvent.AXIS_RX,1).axis(MotionEvent.AXIS_RY,-1);
 check(a.dispatchGenericMotionEvent(alternate));
 check(sink.axisCalls==1&&sink.lastAxes[2]==1&&sink.lastAxes[3]==-1);
 check(external(a).getInt("right_axis_directions")==6&&external(a).getLong("controller_events")==1);
 sink=new Sink();a=new InputAdapter(sink);
 MotionEvent mixed=new MotionEvent(2,0,0,0,InputDevice.SOURCE_JOYSTICK)
     .device(19,new InputDevice(MotionEvent.AXIS_Z,MotionEvent.AXIS_RY))
     .axis(MotionEvent.AXIS_RX,1).axis(MotionEvent.AXIS_RY,1).axis(MotionEvent.AXIS_RZ,-1);
 check(a.dispatchGenericMotionEvent(mixed));
 check(sink.lastAxes[2]==0&&sink.lastAxes[3]==1);
 check(external(a).getInt("right_axis_directions")==8);
 sink=new Sink();a=new InputAdapter(sink);a.setSynthetic(true);
 MotionEvent noDevice=new MotionEvent(2,0,0,0,InputDevice.SOURCE_JOYSTICK)
     .axis(MotionEvent.AXIS_Z,-1).axis(MotionEvent.AXIS_RZ,1)
     .axis(MotionEvent.AXIS_RX,1).axis(MotionEvent.AXIS_RY,-1);
 check(a.dispatchGenericMotionEvent(noDevice));
 check(sink.lastAxes[2]==-1&&sink.lastAxes[3]==1);
 check(a.report().getJSONObject("in_app_synthetic").getInt("right_axis_directions")==9);
 check(external(a).getInt("right_axis_directions")==0&&external(a).getLong("controller_events")==0);
 System.out.println(checks);
}}
''',
}

def run(command):
    result=subprocess.run(command,text=True,capture_output=True,timeout=60)
    if result.returncode: raise RuntimeError(result.stderr or result.stdout)
    return result.stdout

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--jdk-bin',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    javac=str(args.jdk_bin/'javac') if args.jdk_bin else 'javac'
    java=str(args.jdk_bin/'java') if args.jdk_bin else 'java'
    with tempfile.TemporaryDirectory(prefix='coh-input-adapter-') as temporary:
        temp=Path(temporary);files=[]
        for name,text in STUBS.items():
            path=temp/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);files.append(str(path))
        classes=temp/'classes';classes.mkdir()
        run([javac,'--release','8','-Xlint:all','-Xlint:-options','-Werror','-d',str(classes),str(SOURCE),*files])
        checks=int(run([java,'-cp',str(classes),'org.coh.systemsprobe.AdapterHostCheck']).strip())
        # Removing only final-UP accounting must reproduce the directional failure.
        original=SOURCE.read_text()
        witness='                recordTouchDirection(c, x, y);\n'
        assert original.count(witness)==1
        mutated=temp/'negative/org/coh/systemsprobe/InputAdapter.java'
        mutated.parent.mkdir(parents=True);mutated.write_text(original.replace(witness,''))
        negative_classes=temp/'negative-classes';negative_classes.mkdir()
        run([javac,'--release','8','-Xlint:all','-Xlint:-options','-Werror','-d',str(negative_classes),str(mutated),*files])
        negative=subprocess.run([java,'-cp',str(negative_classes),'org.coh.systemsprobe.AdapterHostCheck'],capture_output=True,text=True,timeout=60)
        assert negative.returncode!=0 and 'AssertionError: check 3' in negative.stderr, 'END-only negative control failed to reproduce the missing +X direction'
        # The previous fixed Z/RZ reads must fail the alternate-layout witness.
        primary_reads='''        float z = centered(event, rightStickAxis(event, MotionEvent.AXIS_Z, MotionEvent.AXIS_RX));
        float rz = centered(event, rightStickAxis(event, MotionEvent.AXIS_RZ, MotionEvent.AXIS_RY));'''
        assert original.count(primary_reads)==1
        axis_mutated=temp/'axis-negative/org/coh/systemsprobe/InputAdapter.java'
        axis_mutated.parent.mkdir(parents=True)
        axis_mutated.write_text(original.replace(primary_reads,
            '        float z = centered(event, MotionEvent.AXIS_Z), rz = centered(event, MotionEvent.AXIS_RZ);'))
        axis_negative_classes=temp/'axis-negative-classes';axis_negative_classes.mkdir()
        run([javac,'--release','8','-Xlint:all','-Xlint:-options','-Werror','-d',str(axis_negative_classes),str(axis_mutated),*files])
        axis_negative=subprocess.run([java,'-cp',str(axis_negative_classes),'org.coh.systemsprobe.AdapterHostCheck'],capture_output=True,text=True,timeout=60)
        assert axis_negative.returncode!=0 and 'AssertionError: check 51' in axis_negative.stderr, 'Fixed Z/RZ negative control failed to reproduce alternate stick loss'
    report={'schema':'coh-input-adapter-host-proof-v1','passed':True,'checks':checks,
            'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'scope':'Actual InputAdapter class under host Android/JSON transport stubs; not Android framework execution',
            'cases':['four END-only direction signs','zero movement END','unowned pointer UP','historical MOVE samples','wrong source flags','external/synthetic separation','CANCEL no invented movement',
                     'declared Z/RZ preferred even while centered','RX/RY fallback by declared axis ranges','independent mixed axis fallback','device-less synthetic Z/RZ retained'],
            'invariants':['END contributes measured final movement directions','touch_move counts genuine MOVE samples only','native sink receives END rather than fabricated MOVE'],
            'negative_control':{'passed':True,'mutation':'Remove only final-UP direction accounting from actual InputAdapter','expected_failure':'END-only +X direction assertion check 3'},
            'right_stick_negative_control':{'passed':True,'mutation':'Restore fixed Z/RZ reads without declared-range fallback','expected_failure':'RX/RY sink assertion check 51'}}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'passed':True,'checks':checks,'source_sha256':report['source_sha256']}))

if __name__=='__main__':main()
