package io.github.russianranger.cohclientinteractive;

import android.content.Context;
import android.hardware.input.InputManager;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.view.InputDevice;
import android.view.InputEvent;
import android.view.KeyEvent;
import android.view.MotionEvent;
import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/**
 * Android gamepad adapter, ported from TRASC: the first controller to send input while capture
 * is on owns it, key repeats are dropped, sticks/hat/triggers become ControllerInput sources and
 * a 16 ms tick moves the cursor. It captures only while the game view is in front.
 */
final class ControllerManager implements InputManager.InputDeviceListener {
    private final File profileFile;
    private final InputManager manager;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final ControllerInput input;
    private ControllerProfile profile=ControllerProfile.defaults();
    private long lastTick;
    private String loadError="";
    private int device=-1;
    private final Map<String,Float> digital=new HashMap<>(),analog=new HashMap<>();
    private final Runnable tick=new Runnable(){@Override public void run(){long now=SystemClock.uptimeMillis();input.tick((now-lastTick)/1000f);lastTick=now;handler.postDelayed(this,16);}};
    ControllerManager(Context context,File profileFile,ControllerInput.Sink sink){
        this.profileFile=profileFile;input=new ControllerInput(sink);
        reload();
        manager=(InputManager)context.getSystemService(Context.INPUT_SERVICE);
        if(manager!=null)manager.registerInputDeviceListener(this,handler);
    }
    /** A saved profile that does not validate leaves the defaults active and reports why. */
    void reload(){
        ControllerProfile next=ControllerProfile.defaults();loadError="";
        try{ControllerProfile saved=ControllerProfile.load(profileFile);if(saved!=null)next=saved;}
        catch(IOException|RuntimeException failure){loadError="Saved controller profile could not be loaded: "+failure.getMessage();}
        apply(next);
    }
    /** Validated before disk or the active bindings change. */
    void save(ControllerProfile next)throws IOException {next.save(profileFile);apply(next);loadError="";}
    private void apply(ControllerProfile next){
        boolean capturing=input.active();
        capture(false);input.configure(next.layers,next.deadzone,next.sensitivity);profile=next;
        if(capturing)capture(true);
    }
    ControllerProfile profile(){return profile;}
    String loadError(){return loadError;}
    String layerLabel(){return (input.currentLayer()+1)+"/"+input.layerCount()+" · "+input.layerName();}
    int layerCount(){return input.layerCount();}
    void capture(boolean active){
        input.activate(false);digital.clear();analog.clear();device=-1;handler.removeCallbacks(tick);
        input.activate(active);
        if(active){lastTick=SystemClock.uptimeMillis();handler.post(tick);}
    }
    boolean active(){return input.active();}
    private boolean accepts(InputEvent event){
        if(!input.active())return false;
        boolean pad=event.isFromSource(InputDevice.SOURCE_GAMEPAD)||event.isFromSource(InputDevice.SOURCE_JOYSTICK);
        // A hardware keyboard's arrow keys also carry SOURCE_DPAD; only a controller's D-pad is captured.
        if(!pad&&event.isFromSource(InputDevice.SOURCE_DPAD)){
            InputDevice source=event.getDevice();
            pad=source!=null&&(source.supportsSource(InputDevice.SOURCE_GAMEPAD)||source.supportsSource(InputDevice.SOURCE_JOYSTICK));
        }
        if(!pad)return false;
        if(device<0)device=event.getDeviceId();
        return device==event.getDeviceId();
    }
    boolean key(KeyEvent event){
        String source=ControllerInput.keySource(event.getKeyCode());
        if(source==null||!accepts(event))return false;
        if(event.getAction()==KeyEvent.ACTION_DOWN&&event.getRepeatCount()>0)return true;
        if(event.getAction()==KeyEvent.ACTION_DOWN||event.getAction()==KeyEvent.ACTION_UP){
            digital.put(source,event.getAction()==KeyEvent.ACTION_DOWN?1f:0f);
            input.value(source,Math.max(digital.get(source),analog.getOrDefault(source,0f)));
        }
        return true;
    }
    boolean motion(MotionEvent event){
        if(event.getAction()!=MotionEvent.ACTION_MOVE||!event.isFromSource(InputDevice.SOURCE_JOYSTICK)||!accepts(event))return false;
        InputDevice pad=event.getDevice();
        // Right stick on Z/RZ, falling back to RX/RY per axis (the earlier COH selection).
        int xAxis=pad!=null&&pad.getMotionRange(MotionEvent.AXIS_Z,event.getSource())!=null?MotionEvent.AXIS_Z:MotionEvent.AXIS_RX;
        int yAxis=pad!=null&&pad.getMotionRange(MotionEvent.AXIS_RZ,event.getSource())!=null?MotionEvent.AXIS_RZ:MotionEvent.AXIS_RY;
        input.beginFrame();
        try{
            input.axis("LeftUp","LeftDown",event.getAxisValue(MotionEvent.AXIS_Y));
            input.axis("LeftLeft","LeftRight",event.getAxisValue(MotionEvent.AXIS_X));
            input.axis("RightUp","RightDown",event.getAxisValue(yAxis));
            input.axis("RightLeft","RightRight",event.getAxisValue(xAxis));
            float hatX=event.getAxisValue(MotionEvent.AXIS_HAT_X),hatY=event.getAxisValue(MotionEvent.AXIS_HAT_Y);
            analogValue("DpadLeft",Math.max(0,-hatX));analogValue("DpadRight",Math.max(0,hatX));
            analogValue("DpadUp",Math.max(0,-hatY));analogValue("DpadDown",Math.max(0,hatY));
            analogValue("L2",Math.max(event.getAxisValue(MotionEvent.AXIS_LTRIGGER),event.getAxisValue(MotionEvent.AXIS_BRAKE)));
            analogValue("R2",Math.max(event.getAxisValue(MotionEvent.AXIS_RTRIGGER),event.getAxisValue(MotionEvent.AXIS_GAS)));
        }finally{input.endFrame();}
        return true;
    }
    private void analogValue(String source,float value){
        if(!Float.isFinite(value))value=0;
        analog.put(source,value);input.value(source,Math.max(value,digital.getOrDefault(source,0f)));
    }
    /** A lost or reconfigured controller releases everything; the next controller may take over. */
    private void restart(){if(input.active()){capture(false);capture(true);}}
    @Override public void onInputDeviceAdded(int id){}
    @Override public void onInputDeviceChanged(int id){if(device==id)restart();}
    @Override public void onInputDeviceRemoved(int id){if(device==id)restart();}
    void close(){capture(false);if(manager!=null)manager.unregisterInputDeviceListener(this);}
}
