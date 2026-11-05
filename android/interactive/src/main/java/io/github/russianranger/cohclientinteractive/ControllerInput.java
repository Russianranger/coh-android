package io.github.russianranger.cohclientinteractive;

import java.util.*;

/**
 * Platform-independent controller state, ported from the TRASC launcher's ControllerInput.
 * Named layers bind 24 controller sources to actions; key and mouse-button actions are
 * reference-counted atoms (chords press modifiers first and release them last). COH keeps
 * its accepted stick feel: pointer actions use the deadzone-rescaled stick, while analog
 * sources bound to keys or buttons engage at 35% raw deflection and hold until below 20%.
 */
public final class ControllerInput {
    public interface Sink {void button(String action,boolean down);void pointer(float dx,float dy);void wheel(int amount);default void layer(int index,String name){}}
    static final int MAX_LAYERS=6;
    /** Analog-as-button hysteresis on raw deflection (the accepted COH walking thresholds). */
    static final float PRESS=.35f,RELEASE=.20f;
    /** The accepted COH right-stick cursor: 0.18 deadzone, 0.55 px/ms. */
    static final float DEFAULT_DEADZONE=.18f,DEFAULT_SENSITIVITY=550f;
    static final float MIN_DEADZONE=.05f,MAX_DEADZONE=.8f,MIN_SENSITIVITY=50f,MAX_SENSITIVITY=2500f;
    /** Longest frame one pointer tick may cover, matching the earlier 64 ms cursor cap. */
    static final float MAX_TICK_SECONDS=.064f;
    static final class Layer {
        final String name;final Map<String,String> bindings;
        Layer(String name,Map<String,String> bindings){this.name=name;this.bindings=Collections.unmodifiableMap(new LinkedHashMap<>(bindings));}
    }
    static final List<String> SOURCES=Collections.unmodifiableList(Arrays.asList(
        "A","B","X","Y","L1","R1","L2","R2","L3","R3","Start","Select",
        "DpadUp","DpadDown","DpadLeft","DpadRight","LeftUp","LeftDown","LeftLeft","LeftRight",
        "RightUp","RightDown","RightLeft","RightRight"));
    /** COH one-shot commands: they fire on press and hold nothing. */
    static final List<String> COMMANDS=Collections.unmodifiableList(Arrays.asList("ClientMenu","SendEnter","TextEntry"));
    static final List<String> ACTIONS;
    static {
        List<String> list=new ArrayList<>(Arrays.asList("None","MouseLeft","MouseRight","MouseMiddle","PointerUp","PointerDown","PointerLeft","PointerRight","WheelUp","WheelDown"));
        for(char c='A';c<='Z';c++)list.add("Key"+c);
        for(int i=0;i<=9;i++)list.add("Digit"+i);
        for(int i=1;i<=12;i++)list.add("F"+i);
        list.addAll(Arrays.asList("Space","Enter","Escape","Tab","Backspace","ArrowUp","ArrowDown","ArrowLeft","ArrowRight","ShiftLeft","ControlLeft","AltLeft","Home","End","PageUp","PageDown","Insert","Delete","Minus","Equal","BracketLeft","BracketRight","Semicolon","Quote","Comma","Period","Slash","Backslash","Backquote","NumLock"));
        list.addAll(COMMANDS);
        List<String> keys=new ArrayList<>(list);
        for(String mod:Arrays.asList("ShiftLeft","ControlLeft","AltLeft"))
            for(String key:keys)if(key.startsWith("Key")||key.startsWith("Digit")||key.matches("F[0-9]+")||key.equals("Tab"))list.add(mod+"+"+key);
        list.addAll(Arrays.asList("LayerNext","LayerPrevious"));
        for(int i=1;i<=MAX_LAYERS;i++){list.add("Layer"+i);list.add("HoldLayer"+i);}
        ACTIONS=Collections.unmodifiableList(list);
    }
    /** Today's COH controller: the defaults reproduce the earlier hard-coded mapping. Triggers are unbound. */
    static Map<String,String> defaults(){
        Map<String,String> m=new LinkedHashMap<>();for(String s:SOURCES)m.put(s,"None");
        m.put("A","MouseLeft");m.put("B","Escape");m.put("X","Space");
        m.put("L1","MouseRight");m.put("R1","MouseRight");m.put("L3","TextEntry");m.put("Start","SendEnter");
        for(String dir:Arrays.asList("Up","Down","Left","Right")){m.put("Dpad"+dir,"Arrow"+dir);m.put("Right"+dir,"Pointer"+dir);}
        m.put("LeftUp","KeyW");m.put("LeftDown","KeyS");m.put("LeftLeft","KeyA");m.put("LeftRight","KeyD");
        return m;
    }
    static Map<String,String> inherited(){Map<String,String> m=new LinkedHashMap<>();for(String s:SOURCES)m.put(s,"Inherit");return m;}
    static List<Layer> defaultLayers(){return Collections.singletonList(new Layer("Main",defaults()));}
    /** "COH power trays": the defaults plus hold LT for a layer whose face, D-pad and shoulder buttons press 1-0. */
    static List<Layer> powerTrayLayers(){
        Map<String,String> main=defaults(),powers=inherited();
        main.put("L2","HoldLayer2");main.put("Select","ClientMenu");
        String[] sources={"A","B","X","Y","DpadUp","DpadRight","DpadDown","DpadLeft","L1","R1"};
        for(int i=0;i<sources.length;i++)powers.put(sources[i],"Digit"+((i+1)%10));
        return Arrays.asList(new Layer("Main",main),new Layer("Powers",powers));
    }
    static boolean isLayerAction(String action){return action.startsWith("Layer")||action.startsWith("HoldLayer");}
    static boolean isCommand(String action){return COMMANDS.contains(action);}
    static int layerTarget(String action){
        if(action.matches("(?:HoldLayer|Layer)[1-6]"))return Integer.parseInt(action.substring(action.length()-1))-1;
        return -1;
    }
    static String sourceLabel(String source){
        switch(source){case "L1":return "LB";case "R1":return "RB";case "L2":return "LT";case "R2":return "RT";case "L3":return "Left stick press";case "R3":return "Right stick press";default:return source.replaceAll("([a-z])([A-Z])","$1 $2");}
    }
    /** Android KeyEvent codes (stable platform constants) for the digital sources. */
    public static String keySource(int keyCode){
        switch(keyCode){
            case 96:return "A";case 97:return "B";case 99:return "X";case 100:return "Y";          // KEYCODE_BUTTON_A/B/X/Y
            case 102:return "L1";case 103:return "R1";case 104:return "L2";case 105:return "R2";    // KEYCODE_BUTTON_L1/R1/L2/R2
            case 106:return "L3";case 107:return "R3";case 108:return "Start";case 109:return "Select"; // THUMBL/THUMBR/START/SELECT
            case 19:return "DpadUp";case 20:return "DpadDown";case 21:return "DpadLeft";case 22:return "DpadRight"; // KEYCODE_DPAD_*
            default:return null;
        }
    }
    /** Shared by the model and saved-profile loading; nothing changes unless every rule holds. */
    static void validate(List<Layer> next,float deadzone,float sensitivity){
        if(!Float.isFinite(deadzone)||deadzone<MIN_DEADZONE||deadzone>MAX_DEADZONE)throw new IllegalArgumentException("Controller deadzone must be between 0.05 and 0.8");
        if(!Float.isFinite(sensitivity)||sensitivity<MIN_SENSITIVITY||sensitivity>MAX_SENSITIVITY)throw new IllegalArgumentException("Pointer speed must be between 50 and 2500");
        if(next==null||next.isEmpty()||next.size()>MAX_LAYERS)throw new IllegalArgumentException("Choose between 1 and 6 layers");
        Set<String> names=new HashSet<>();
        for(int i=0;i<next.size();i++){
            Layer layer=next.get(i);
            if(layer==null||layer.name==null||layer.name.isEmpty()||layer.name.length()>24||layer.name.chars().anyMatch(Character::isISOControl)||!names.add(layer.name.toLowerCase(Locale.ROOT)))throw new IllegalArgumentException("Layer names must be unique and contain 1–24 printable characters");
            if(!layer.bindings.keySet().equals(new HashSet<>(SOURCES)))throw new IllegalArgumentException("Every layer must contain all controller sources");
            for(String value:layer.bindings.values()){
                if(value==null||!(i>0&&value.equals("Inherit"))&&!ACTIONS.contains(value))throw new IllegalArgumentException("Unknown controller action: "+value);
                if(layerTarget(value)>=next.size())throw new IllegalArgumentException("Binding targets a layer that does not exist");
            }
        }
    }
    private final Sink sink;
    private List<Layer> layers=defaultLayers();
    private final Map<String,Float> held=new LinkedHashMap<>();
    // Latch layer controls on press, so their release is independent of the new layer's bindings.
    private final Map<String,String> controls=new LinkedHashMap<>();
    private final Map<String,Integer> temporary=new LinkedHashMap<>(),counts=new LinkedHashMap<>();
    // One Android motion event updates many axes; settle them together so releases precede presses.
    private int frameDepth,frameLayer;
    private boolean frameDirty;
    private final List<Runnable> frameCommands=new ArrayList<>();
    private int selected;
    private boolean active;
    float deadzone=DEFAULT_DEADZONE,sensitivity=DEFAULT_SENSITIVITY;
    public ControllerInput(Sink sink){this.sink=sink;}
    void configure(List<Layer> next,float deadzone,float sensitivity){
        validate(next,deadzone,sensitivity);
        releaseAll();layers=new ArrayList<>(next);selected=0;this.deadzone=deadzone;this.sensitivity=sensitivity;sink.layer(currentLayer(),layerName());
    }
    List<Layer> layers(){return Collections.unmodifiableList(layers);}
    int currentLayer(){int result=selected;for(int target:temporary.values())result=target;return result;}
    String layerName(){return layers.get(currentLayer()).name;}
    public int layerCount(){return layers.size();}
    public void activate(boolean enabled){if(!enabled)releaseAll();active=enabled;}
    public boolean active(){return active;}
    private String action(String source){String value=layers.get(currentLayer()).bindings.get(source);return value.equals("Inherit")?layers.get(0).bindings.get(source):value;}
    private static boolean isModifier(String action){return action.equals("ShiftLeft")||action.equals("ControlLeft")||action.equals("AltLeft");}
    private static boolean holdsOutput(String action){
        return !(action.equals("None")||action.startsWith("Pointer")||action.startsWith("Wheel")||isCommand(action)||isLayerAction(action));
    }
    private void releaseOutputs(){
        List<String> old=new ArrayList<>(counts.keySet());old.sort(Comparator.comparing(ControllerInput::isModifier));
        counts.clear();for(String a:old)sink.button(a,false);
    }
    private void reconcile(){
        Map<String,Integer> next=new LinkedHashMap<>();
        // Source order fixes the order of simultaneous edges (left stick: W, S, A, D as before).
        for(String source:SOURCES){
            if(!held.containsKey(source)||controls.containsKey(source))continue;
            String action=action(source);
            if(!holdsOutput(action))continue;
            for(String atom:action.split("\\+"))next.put(atom,next.getOrDefault(atom,0)+1);
        }
        List<String> old=new ArrayList<>(counts.keySet());old.sort(Comparator.comparing(ControllerInput::isModifier));
        for(String a:old)if(!next.containsKey(a))sink.button(a,false);
        List<String> fresh=new ArrayList<>(next.keySet());fresh.sort(Comparator.comparing(ControllerInput::isModifier).reversed());
        Set<String> before=new HashSet<>(counts.keySet());
        counts.clear();counts.putAll(next);
        for(String a:fresh)if(!before.contains(a))sink.button(a,true);
    }
    private void changedLayer(int before){
        if(before!=currentLayer()){releaseOutputs();reconcile();sink.layer(currentLayer(),layerName());}
        else reconcile();
    }
    private void settle(int previous){if(frameDepth>0)frameDirty=true;else changedLayer(previous);}
    private void fire(Runnable command){if(frameDepth>0)frameCommands.add(command);else command.run();}
    void beginFrame(){if(frameDepth++==0){frameLayer=currentLayer();frameDirty=false;}}
    void endFrame(){
        if(frameDepth==0||--frameDepth>0)return;
        if(frameDirty){frameDirty=false;changedLayer(frameLayer);}
        List<Runnable> commands=new ArrayList<>(frameCommands);frameCommands.clear();
        for(Runnable command:commands){if(!active)break;command.run();}
    }
    public void value(String source,float magnitude){value(source,magnitude,magnitude);}
    private void value(String source,float raw,float scaled){
        if(!SOURCES.contains(source))return;
        // A non-finite sample releases, like the earlier COH stick handling.
        if(!Float.isFinite(raw))raw=0;
        if(!Float.isFinite(scaled))scaled=0;
        if(!active)return;
        raw=Math.max(0,Math.min(1,raw));scaled=Math.max(0,Math.min(1,scaled));boolean before=held.containsKey(source);
        String command=controls.containsKey(source)?controls.get(source):action(source);
        boolean pointer=command.startsWith("Pointer");
        boolean down=pointer?scaled>0:raw>=(before?RELEASE:PRESS);
        if(down)held.put(source,pointer?scaled:raw);else held.remove(source);
        if(down==before)return;
        int previous=currentLayer();
        if(!down){controls.remove(source);temporary.remove(source);settle(previous);return;}
        if(isLayerAction(command)){
            controls.put(source,command);
            if(command.equals("LayerNext"))selected=(selected+1)%layers.size();
            else if(command.equals("LayerPrevious"))selected=(selected+layers.size()-1)%layers.size();
            else if(command.startsWith("HoldLayer"))temporary.put(source,layerTarget(command));
            else selected=layerTarget(command);
            settle(previous);return;
        }
        settle(previous);
        // Commands run last: one may release this model (for example by opening the menu).
        if(command.startsWith("Wheel"))fire(()->sink.wheel(command.equals("WheelUp")?1:-1));
        else if(isCommand(command))fire(()->sink.button(command,true));
    }
    /** A stick axis: raw deflection drives button bindings, the deadzone-rescaled value drives the pointer. */
    void axis(String negative,String positive,float value){
        if(!Float.isFinite(value))value=0;
        float raw=Math.min(1,Math.abs(value));
        float scaled=raw<=deadzone?0:(raw-deadzone)/(1-deadzone);
        beginFrame();
        try{value(negative,value<0?raw:0,value<0?scaled:0);value(positive,value>0?raw:0,value>0?scaled:0);}
        finally{endFrame();}
    }
    void tick(float seconds){
        if(!active||!(seconds>0))return;float dt=Math.min(seconds,MAX_TICK_SECONDS),dx=0,dy=0;
        for(Map.Entry<String,Float> e:held.entrySet())switch(controls.containsKey(e.getKey())?"None":action(e.getKey())){
            case "PointerLeft":dx-=e.getValue();break;case "PointerRight":dx+=e.getValue();break;case "PointerUp":dy-=e.getValue();break;case "PointerDown":dy+=e.getValue();break;
            default:break;
        }
        if(dx!=0||dy!=0)sink.pointer(dx*sensitivity*dt,dy*sensitivity*dt);
    }
    void releaseAll(){
        int before=currentLayer();releaseOutputs();held.clear();controls.clear();temporary.clear();frameCommands.clear();frameDirty=false;
        if(before!=currentLayer())sink.layer(currentLayer(),layerName());
    }
}
