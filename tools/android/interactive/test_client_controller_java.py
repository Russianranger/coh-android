"""Execute the shipped overlay placement, controller model, saved profile and wheel paths.

The default controller profile is checked against the earlier fixed COH mapping, using the
retained ClientInput walking and cursor code as the oracle. Android device adapters (InputManager,
views) are outside this host; their gating is covered by test_client_sidebar_commands.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
PACKAGE = 'io.github.russianranger.cohclientinteractive'
sys.path.insert(0, str(Path(__file__).parent))
from test_storage_ui import production_method

HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
public final class ControllerHost {
 static void need(boolean value,String why){if(!value)throw new AssertionError(why);}
 static boolean near(float a,float b){return Math.abs(a-b)<=1e-3f*Math.max(1f,Math.abs(b));}
 /** Raw model output. */
 static final class Record implements ControllerInput.Sink {
  final List<String> out=new ArrayList<>();float dx,dy;Runnable onMenu;
  public void button(String action,boolean down){out.add(action+(down?"+":"-"));if(onMenu!=null&&action.equals("ClientMenu"))onMenu.run();}
  public void pointer(float x,float y){dx+=x;dy+=y;}
  public void wheel(int amount){out.add("wheel"+amount);}
  public void layer(int index,String name){out.add("layer"+index+":"+name);}
 }
 /** The activity side: shared KeyOwners like ClientActivity, edges recorded as keysym:down. */
 static final class Target implements ControllerBridge.Target {
  boolean keys=true,walk=true;final ClientInput.KeyOwners owners=new ClientInput.KeyOwners();
  final List<String> sent=new ArrayList<>();final Set<Integer> buttons=new LinkedHashSet<>();
  final List<String> commands=new ArrayList<>();float dx,dy;
  final ClientInput.KeySender sender=(key,down)->{sent.add(key+":"+(down?1:0));return true;};
  public boolean keysOpen(){return keys;}public boolean walkOpen(){return walk;}
  public boolean holds(int owner){return owners.contains(owner);}
  public void press(int owner,int keysym){owners.press(owner,keysym,sender);}
  public void release(int owner){owners.release(owner,sender);}
  public void mouse(int button,boolean down){if(down)buttons.add(button);else buttons.remove(button);int mask=0;for(int b:buttons)mask|=b;sent.add("mask:"+mask);}
  public void pointer(float x,float y){dx+=x;dy+=y;}
  public void wheel(int amount){sent.add("wheel:"+amount);}
  public void command(String action){commands.add(action);}
 }
 static ControllerInput active(ControllerInput.Sink sink){ControllerInput input=new ControllerInput(sink);input.activate(true);return input;}
 static void stick(ControllerInput input,float x,float y){input.beginFrame();try{input.axis("LeftUp","LeftDown",y);input.axis("LeftLeft","LeftRight",x);}finally{input.endFrame();}}
 @SafeVarargs static List<ControllerInput.Layer> layers(Map<String,String>... maps){
  List<ControllerInput.Layer> result=new ArrayList<>();String[] names={"Main","Powers","Third","Fourth","Fifth","Sixth","Seventh"};
  for(int i=0;i<maps.length;i++)result.add(new ControllerInput.Layer(names[i],maps[i]));return result;
 }
 static Map<String,String> with(Map<String,String> base,String... pairs){Map<String,String> m=new LinkedHashMap<>(base);for(int i=0;i<pairs.length;i+=2)m.put(pairs[i],pairs[i+1]);return m;}
 static void invalid(Runnable attempt,String why){try{attempt.run();}catch(IllegalArgumentException expected){return;}throw new AssertionError("accepted: "+why);}
 static void rejected(String json,String why){invalid(()->ControllerProfile.parse(json),why);}

 static void overlay(){
  need(ClientOverlayPosition.normalized(Float.NaN,1f)==1f&&ClientOverlayPosition.normalized(-3f,0f)==0f&&ClientOverlayPosition.normalized(7f,0f)==1f,"normalized clamp");
  need(ClientOverlayPosition.normalized(Float.POSITIVE_INFINITY,.5f)==.5f,"infinite position falls back");
  // 1000x600 window, 40 px cutout on the left, 20 px revealed bar below, 12 px margin, 48 px gear.
  ClientOverlayPosition.Area area=new ClientOverlayPosition.Area(1000,600,40,0,0,20,12,48,48);
  need(area.left==52&&area.top==12&&area.right==988&&area.bottom==568&&area.maxLeft()==940&&area.maxTop()==520,"safe area");
  ClientOverlayPosition.Placement p=area.place(1f,0f,0,12,false);need(p.gearLeft==940&&p.gearTop==12,"default upper right");
  p=area.place(0f,1f,0,12,false);need(p.gearLeft==52&&p.gearTop==520,"lower left inside insets");
  p=area.place(.5f,.5f,0,12,false);need(p.gearLeft==496&&p.gearTop==266,"center");
  p=area.place(-5f,9f,0,12,false);need(p.gearLeft==52&&p.gearTop==520,"stored values clamp into the safe area");
  ClientOverlayPosition.Point n=area.normalize(5000,-100);need(n.x==1f&&n.y==0f,"drag beyond the edge clamps");
  n=area.normalize(496,266);need(near(n.x,.5f)&&near(n.y,.5f),"normalize inverts place");
  // Persist: the saved 0..1 position restores the same relative corner on another window size.
  float savedX=area.normalize(940,520).x,savedY=area.normalize(940,520).y;
  ClientOverlayPosition.Area rotated=new ClientOverlayPosition.Area(600,1000,0,30,0,0,12,48,48);
  p=rotated.place(ClientOverlayPosition.normalized(savedX,1f),ClientOverlayPosition.normalized(savedY,0f),0,12,false);
  need(p.gearLeft==rotated.maxLeft()&&p.gearTop==rotated.maxTop(),"persisted corner survives a size change");
  // A transient window smaller than the gear keeps its origin visible.
  ClientOverlayPosition.Area tiny=new ClientOverlayPosition.Area(30,30,0,0,0,0,12,48,48);
  p=tiny.place(1f,1f,0,12,false);need(p.gearLeft==0&&p.gearTop==0,"tiny window");
  ClientOverlayPosition.Drag drag=new ClientOverlayPosition.Drag(8);
  drag.start(100,100,940,12);need(!drag.move(105,104),"movement inside slop is still a tap");need(drag.finish(),"tap toggles the menu");
  drag.start(100,100,940,12);need(drag.move(120,100)&&drag.dragging(),"drag starts past slop");
  ClientOverlayPosition.Point moved=drag.position(80,130);need(moved.x==920&&moved.y==42,"drag offset");
  need(!drag.finish()&&!drag.active(),"a drag is not a tap");
  drag.start(1,1,0,0);drag.move(50,50);drag.cancel();need(!drag.active()&&!drag.dragging()&&!drag.finish(),"cancel");
 }

 static void defaults(){
  Map<String,String> expected=new LinkedHashMap<>();for(String s:ControllerInput.SOURCES)expected.put(s,"None");
  String[] today={"A","MouseLeft","B","Escape","X","Space","L1","MouseRight","R1","MouseRight","L3","TextEntry","Start","SendEnter",
   "DpadUp","ArrowUp","DpadDown","ArrowDown","DpadLeft","ArrowLeft","DpadRight","ArrowRight",
   "LeftUp","KeyW","LeftDown","KeyS","LeftLeft","KeyA","LeftRight","KeyD",
   "RightUp","PointerUp","RightDown","PointerDown","RightLeft","PointerLeft","RightRight","PointerRight"};
  for(int i=0;i<today.length;i+=2)expected.put(today[i],today[i+1]);
  need(ControllerInput.defaults().equals(expected),"default bindings changed: "+ControllerInput.defaults());
  for(String unbound:new String[]{"Y","L2","R2","R3","Select"})need(expected.get(unbound).equals("None"),"unbound "+unbound);
  ControllerProfile profile=ControllerProfile.defaults();
  need(profile.layers.size()==1&&profile.layers.get(0).name.equals("Main")&&profile.layers.get(0).bindings.equals(expected),"single Main layer");
  need(profile.deadzone==.18f&&profile.sensitivity==550f,"earlier cursor deadzone and 0.55 px/ms");
  need(ControllerProfile.preset("original").sameBindings(profile),"original preset is the default");
  ControllerProfile powers=ControllerProfile.preset("powers");
  need(powers.layers.size()==2&&powers.layers.get(0).bindings.get("L2").equals("HoldLayer2"),"LT holds the power layer");
  Map<String,String> second=powers.layers.get(1).bindings;String digits="";
  for(String s:new String[]{"A","B","X","Y","DpadUp","DpadRight","DpadDown","DpadLeft","L1","R1"})digits+=second.get(s).substring(5);
  need(digits.equals("1234567890"),"power layer presses 1-0: "+digits);
  need(second.get("LeftUp").equals("Inherit")&&second.get("RightLeft").equals("Inherit"),"sticks keep walking and cursor");
  invalid(()->ControllerProfile.preset("takp"),"unknown preset");
  need(ControllerInput.keySource(96).equals("A")&&ControllerInput.keySource(108).equals("Start")&&ControllerInput.keySource(106).equals("L3")
   &&ControllerInput.keySource(19).equals("DpadUp")&&ControllerInput.keySource(104).equals("L2")&&ControllerInput.keySource(66)==null,"Android key codes");
  for(String action:ControllerInput.ACTIONS)need(!action.startsWith("MouseLook"),"TAKP-only action kept: "+action);
 }

 /** The retained WalkingKeys code is the oracle for default left-stick walking. */
 static void walkingOracle(){
  float[] values={-1f,-.6f,-.36f,-.35f,-.34f,-.25f,-.2f,-.19f,0f,.19f,.2f,.25f,.34f,.35f,.36f,.6f,1f,1.5f,Float.NaN,Float.POSITIVE_INFINITY};
  Random random=new Random(20261104L);
  ClientInput.KeyOwners owners=new ClientInput.KeyOwners();ClientInput.WalkingKeys walking=new ClientInput.WalkingKeys();
  List<String> before=new ArrayList<>();ClientInput.KeySender old=(key,down)->{before.add(key+":"+(down?1:0));return true;};
  Target target=new Target();ControllerInput input=active(new ControllerBridge(target));
  // The earlier test_input hysteresis sequence, then random samples near every threshold.
  float[][] script={{0,-.34f},{0,-.35f},{0,-1},{0,-.25f},{0,-.19f},{.5f,-.5f},{-.5f,.5f},{Float.NaN,Float.POSITIVE_INFINITY}};
  List<float[]> samples=new ArrayList<>(Arrays.asList(script));
  for(int i=0;i<6000;i++)samples.add(new float[]{values[random.nextInt(values.length)],values[random.nextInt(values.length)]});
  for(float[] s:samples){walking.update(s[0],s[1],true,owners,old);stick(input,s[0],s[1]);}
  walking.update(0,0,true,owners,old);stick(input,0,0);
  need(before.size()>1000,"oracle exercised");
  need(before.equals(target.sent),"default stick walking differs from the earlier COH mapping");
  List<String> first=target.sent.subList(0,10);
  need(first.equals(Arrays.asList("119:1","119:0","119:1","100:1","119:0","100:0","115:1","97:1","115:0","97:0")),"hysteresis script "+first);
 }

 /** The earlier cursor: ClientInput.axis (0.18 deadzone) * elapsed ms (max 64) * 0.55. */
 static void cursorOracle(){
  float[] values={-1f,-.7f,-.3f,-.19f,-.18f,0f,.1f,.18f,.181f,.4f,.9f,1f,1.2f,Float.NaN};
  float[] ticks={.001f,.016f,.032f,.064f,.2f};
  for(float x:values)for(float y:values)for(float dt:ticks){
   Target target=new Target();ControllerInput input=active(new ControllerBridge(target));
   input.beginFrame();input.axis("RightUp","RightDown",y);input.axis("RightLeft","RightRight",x);input.endFrame();
   input.tick(dt);
   float ms=Math.min(64f,dt*1000f);
   need(near(target.dx,ClientInput.axis(x)*ms*.55f)&&near(target.dy,ClientInput.axis(y)*ms*.55f),"cursor "+x+","+y+","+dt+" -> "+target.dx+","+target.dy);
   need(target.sent.isEmpty(),"cursor sends no keys");
  }
  // Rescale follows the configured deadzone: (|v|-dz)/(1-dz).
  Record record=new Record();ControllerInput input=active(record);
  input.configure(ControllerInput.defaultLayers(),.5f,1000f);input.activate(true);
  input.axis("RightLeft","RightRight",.5f);input.tick(.01f);need(record.dx==0,"inside a larger deadzone");
  input.axis("RightLeft","RightRight",-.75f);input.tick(.01f);need(near(record.dx,-5f),"rescaled 0.5 at 1000 px/s: "+record.dx);
  input.activate(false);input.tick(.01f);need(near(record.dx,-5f),"released model stops the cursor");
 }

 static void hysteresis(){
  Record record=new Record();ControllerInput input=active(record);
  input.configure(layers(with(ControllerInput.defaults(),"L2","KeyQ","R2","PointerRight")),.18f,550f);input.activate(true);record.out.clear();
  input.value("L2",.34f);need(record.out.isEmpty(),"below 35% does not press");
  input.value("L2",.35f);need(record.out.equals(Arrays.asList("KeyQ+")),"35% presses");
  input.value("L2",.21f);input.value("L2",.20f);need(record.out.size()==1,"held down to 20%");
  input.value("L2",.19f);need(record.out.equals(Arrays.asList("KeyQ+","KeyQ-")),"below 20% releases");
  input.value("L2",.3f);need(record.out.size()==2,"no re-press inside the band");
  input.value("L2",Float.NaN);input.value("L2",1f);input.value("L2",Float.POSITIVE_INFINITY);
  need(record.out.equals(Arrays.asList("KeyQ+","KeyQ-","KeyQ+","KeyQ-")),"non-finite trigger releases "+record.out);
  // An analog trigger bound to the pointer uses its raw value immediately.
  input.value("R2",.1f);input.tick(.01f);need(near(record.dx,.55f),"trigger pointer "+record.dx);
 }

 static void chords(){
  Record record=new Record();ControllerInput input=active(record);
  input.configure(layers(with(ControllerInput.defaults(),"A","ShiftLeft+KeyB","X","ShiftLeft","Y","ControlLeft+KeyC","B","KeyC")),.18f,550f);input.activate(true);record.out.clear();
  input.value("A",1);input.value("A",0);
  need(record.out.equals(Arrays.asList("ShiftLeft+","KeyB+","KeyB-","ShiftLeft-")),"modifier first, released last "+record.out);
  record.out.clear();input.value("X",1);input.value("A",1);input.value("X",0);input.value("A",0);
  need(record.out.equals(Arrays.asList("ShiftLeft+","KeyB+","KeyB-","ShiftLeft-")),"shared modifier is reference counted "+record.out);
  record.out.clear();input.value("Y",1);input.value("B",1);input.value("Y",0);input.value("B",0);
  need(record.out.equals(Arrays.asList("ControlLeft+","KeyC+","ControlLeft-","KeyC-")),"shared key stays held "+record.out);
  // Edges settled together still press modifiers first and release them last.
  input.configure(layers(with(ControllerInput.defaults(),"X","KeyB","Y","AltLeft")),.18f,550f);input.activate(true);record.out.clear();
  input.beginFrame();input.value("X",1);input.value("Y",1);input.endFrame();
  input.beginFrame();input.value("Y",0);input.value("X",0);input.endFrame();
  need(record.out.equals(Arrays.asList("AltLeft+","KeyB+","KeyB-","AltLeft-")),"same-frame modifier order "+record.out);
  // Through the COH bridge: Shift is pressed first and the letter is sent shifted, as TRASC does.
  Target target=new Target();input=active(new ControllerBridge(target));
  input.configure(layers(with(ControllerInput.defaults(),"A","ShiftLeft+KeyB","Y","ControlLeft+F5")),.18f,550f);input.activate(true);
  input.value("A",1);input.value("A",0);input.value("Y",1);input.value("Y",0);
  need(target.sent.equals(Arrays.asList(0xffe1+":1","66:1","66:0",0xffe1+":0",0xffe3+":1",0xffc2+":1",0xffc2+":0",0xffe3+":0")),"bridge chord "+target.sent);
 }

 static void layerInherit(){
  Record record=new Record();ControllerInput input=active(record);
  Map<String,String> main=with(ControllerInput.defaults(),"L2","HoldLayer2","Y","LayerNext","R2","Layer3");
  Map<String,String> second=with(ControllerInput.inherited(),"B","Digit2"),third=with(ControllerInput.inherited(),"B","Digit3","Y","LayerPrevious");
  input.configure(layers(main,second,third),.18f,550f);input.activate(true);
  need(record.out.equals(Arrays.asList("layer0:Main")),"configure announces the layer "+record.out);record.out.clear();
  input.value("L2",1);input.value("B",1);input.value("A",1);
  need(record.out.equals(Arrays.asList("layer1:Powers","Digit2+","MouseLeft+")),"hold layer and Inherit uses Main "+record.out);record.out.clear();
  input.value("L2",0);
  // As in TRASC, a layer change releases every output and then re-presses what the new layer holds.
  need(record.out.equals(Arrays.asList("MouseLeft-","Digit2-","MouseLeft+","Escape+","layer0:Main")),"release returns and re-maps held buttons "+record.out);
  input.value("B",0);input.value("A",0);record.out.clear();
  input.value("Y",1);input.value("Y",0);input.value("B",1);input.value("B",0);
  need(record.out.equals(Arrays.asList("layer1:Powers","Digit2+","Digit2-")),"LayerNext selects layer 2 "+record.out);record.out.clear();
  input.value("Y",1);input.value("Y",0);need(input.currentLayer()==2&&input.layerName().equals("Third"),"next again");
  input.value("Y",1);input.value("Y",0);need(input.currentLayer()==1,"Third's own binding goes back");
  input.value("R2",1);need(input.currentLayer()==2,"Layer3 selects");input.value("R2",0);need(input.currentLayer()==2,"Layer3 stays selected");
  // The held layer control is latched: releasing it ends the hold even if the new layer rebinds it.
  input.value("L2",1);need(input.currentLayer()==1,"hold from a selected layer");input.value("L2",0);need(input.currentLayer()==2,"returns to the selected layer");
  Map<String,String> inheritMain=with(ControllerInput.inherited());
  invalid(()->ControllerInput.validate(layers(inheritMain),.18f,550f),"Inherit in Main");
  invalid(()->ControllerInput.validate(layers(with(main,"Y","Layer4"),second,third),.18f,550f),"missing target layer");
  invalid(()->ControllerInput.validate(layers(main,second,third,second,second,second,second),.18f,550f),"seven layers");
  List<ControllerInput.Layer> duplicate=Arrays.asList(new ControllerInput.Layer("Main",main),new ControllerInput.Layer("main",second));
  invalid(()->ControllerInput.validate(duplicate,.18f,550f),"duplicate names");
  invalid(()->ControllerInput.validate(Arrays.asList(new ControllerInput.Layer("Tab\tName",main)),.18f,550f),"control character");
  invalid(()->ControllerInput.validate(Arrays.asList(new ControllerInput.Layer("1234567890123456789012345",main)),.18f,550f),"long name");
  invalid(()->ControllerInput.validate(layers(with(main,"A","MouseLookToggle")),.18f,550f),"TAKP-only action");
  Map<String,String> missing=new LinkedHashMap<>(main);missing.remove("R3");
  invalid(()->ControllerInput.validate(layers(missing),.18f,550f),"missing source");
  invalid(()->ControllerInput.validate(layers(main),.04f,550f),"deadzone low");invalid(()->ControllerInput.validate(layers(main),.81f,550f),"deadzone high");
  invalid(()->ControllerInput.validate(layers(main),.18f,49f),"speed low");invalid(()->ControllerInput.validate(layers(main),.18f,2501f),"speed high");
  invalid(()->ControllerInput.validate(layers(main),Float.NaN,550f),"NaN deadzone");
 }

 static void commands(){
  Record record=new Record();ControllerInput input=active(record);
  input.configure(layers(with(ControllerInput.defaults(),"Select","ClientMenu","DpadUp","WheelUp","DpadDown","WheelDown")),.18f,550f);input.activate(true);record.out.clear();
  input.value("Start",1);input.value("Start",1);input.value("Start",0);input.value("Start",1);input.value("L3",1);
  input.value("DpadUp",1);input.value("DpadUp",0);input.value("DpadDown",1);
  need(record.out.equals(Arrays.asList("SendEnter+","SendEnter+","TextEntry+","wheel1","wheel-1")),"one command per press, none held "+record.out);
  // A command may release the model (the menu opening); held outputs are released, nothing is left.
  record.out.clear();record.onMenu=()->input.activate(false);
  input.value("A",1);input.value("Select",1);
  need(record.out.equals(Arrays.asList("MouseLeft+","ClientMenu+","MouseLeft-"))&&!input.active(),"menu releases held controls "+record.out);
  input.value("A",0);input.value("Select",0);need(record.out.size()==3,"inactive model is silent");
 }

 /** Default buttons through the bridge reproduce the earlier dispatchKeyEvent mapping and gates. */
 static void bridge(){
  Target target=new Target();ControllerBridge bridge=new ControllerBridge(target);ControllerInput input=active(bridge);
  input.value("A",1);input.value("L1",1);input.value("R1",1);input.value("A",0);input.value("L1",0);input.value("R1",0);
  need(target.sent.equals(Arrays.asList("mask:1","mask:5","mask:4","mask:0")),"click and shared right button "+target.sent);target.sent.clear();
  for(String s:new String[]{"B","X","DpadLeft","DpadUp","DpadRight","DpadDown"}){input.value(s,1);input.value(s,0);}
  need(target.sent.equals(Arrays.asList("65307:1","65307:0","32:1","32:0","65361:1","65361:0","65362:1","65362:0","65363:1","65363:0","65364:1","65364:0")),"Esc, jump, arrows "+target.sent);
  target.sent.clear();for(String s:new String[]{"Y","Select","R3","L2","R2"}){input.value(s,1);input.value(s,0);}
  need(target.sent.isEmpty()&&target.commands.isEmpty(),"unbound buttons stay silent");
  input.value("L3",1);input.value("Start",1);need(target.commands.equals(Arrays.asList("TextEntry","SendEnter")),"text and Enter commands");
  input.value("L3",0);input.value("Start",0);
  // Walking gate: W/A/S/D/Space wait for canWalk; Escape only needs ordinary game input.
  target.walk=false;input.value("X",1);input.value("B",1);stick(input,0,-1);
  need(target.sent.equals(Arrays.asList("65307:1")),"walk gate holds movement "+target.sent);
  target.walk=true;bridge.refresh();
  need(target.sent.equals(Arrays.asList("65307:1","32:1","119:1")),"walking resumes like the level-triggered stick "+target.sent);
  target.walk=false;bridge.refresh();need(target.sent.subList(3,5).equals(Arrays.asList("32:0","119:0")),"closing the gate releases movement "+target.sent);
  // Escape keeps its owner while walking closes; an external release needs a fresh press.
  target.owners.clear();target.walk=true;target.sent.clear();bridge.refresh();
  need(target.sent.equals(Arrays.asList("32:1","119:1")),"only movement resumes after a release "+target.sent);
  target.keys=false;target.sent.clear();bridge.refresh();need(target.sent.equals(Arrays.asList("32:0","119:0")),"closed input releases "+target.sent);
  input.value("A",1);need(!target.sent.contains("mask:1"),"closed input does not click");input.value("A",0);
  input.value("X",0);input.value("B",0);stick(input,0,0);
  need(bridge.desired().isEmpty()&&!target.holds(ControllerBridge.owner("KeyW"))&&!target.holds(ControllerBridge.owner("Escape"))&&!target.holds(ControllerBridge.owner("Space")),"releases always pass; nothing stays held");
  // Keyboard and controller share one remote key: the second owner sends no edge.
  target.keys=true;target.sent.clear();target.owners.press(51,'w',target.sender);stick(input,0,-1);target.owners.release(51,target.sender);
  need(target.sent.equals(Arrays.asList("119:1")),"shared W "+target.sent);stick(input,0,0);need(target.sent.equals(Arrays.asList("119:1","119:0")),"last owner releases");
  need(ControllerBridge.owner("KeyW")>120005&&ControllerBridge.owner("KeyW")!=ControllerBridge.owner("KeyA"),"distinct owners above keyboard and touch owners");
 }

 static String document(String layers,String tail){return "{\"format\": 2, \"layers\": ["+layers+"]"+tail+"}";}
 static String layer(String name,Map<String,String> map){
  StringBuilder b=new StringBuilder("{\"name\": \""+name+"\", \"bindings\": {");int i=0;
  for(Map.Entry<String,String> e:map.entrySet())b.append(i++==0?"":", ").append('"').append(e.getKey()).append("\": \"").append(e.getValue()).append('"');
  return b.append("}}").toString();
 }
 static void json(){
  for(String name:ControllerProfile.PRESETS){ControllerProfile p=ControllerProfile.preset(name);need(ControllerProfile.parse(p.encode()).sameBindings(p),"round trip "+name);}
  String encoded=ControllerProfile.defaults().encode();
  need(encoded.contains("\"format\": 2")&&encoded.contains("\"deadzone\": 0.18")&&encoded.contains("\"sensitivity\": 550.0"),"format 2 fields "+encoded);
  String main=layer("Main",ControllerInput.defaults()),tail=", \"deadzone\": 0.18, \"sensitivity\": 550";
  need(ControllerProfile.parse(document(main,tail)).sameBindings(ControllerProfile.defaults()),"plain document");
  need(ControllerProfile.parse("{\"layers\": ["+main+"]"+tail+"}").layers.size()==1,"missing format means 2");
  need(ControllerProfile.parse(document(main,tail+", \"comment\": [1, true, null, {\"a\": -1.5e3}]")).layers.size()==1,"extra top-level keys are ignored");
  need(ControllerProfile.parse(document(layer("Main",ControllerInput.defaults())+", "+layer("\\u00c9tage \\\"2\\\"",ControllerInput.inherited()),tail)).layers.get(1).name.equals("Étage \"2\""),"escaped name");
  rejected("[]","array root");rejected("{}","empty object");rejected("","empty");
  rejected("{\"format\": 1, \"layers\": ["+main+"]"+tail+"}","format 1");
  rejected("{\"format\": \"2\", \"layers\": ["+main+"]"+tail+"}","string format");
  rejected(document("",tail),"no layers");rejected(document(main,""),"missing numbers");
  rejected(document(main,", \"deadzone\": \"0.18\", \"sensitivity\": 550"),"string deadzone");
  rejected(document(main,", \"deadzone\": 0.04, \"sensitivity\": 550"),"deadzone limit");
  rejected(document(main,", \"deadzone\": 0.18, \"sensitivity\": 2600"),"speed limit");
  rejected(document(main+","+layer("Main",ControllerInput.inherited()),tail),"duplicate layer name");
  StringBuilder seven=new StringBuilder(main);for(int i=2;i<=7;i++)seven.append(",").append(layer("L"+i,ControllerInput.inherited()));
  rejected(document(seven.toString(),tail),"seven layers");
  rejected(document(layer("Main",ControllerInput.inherited()),tail),"Inherit in Main");
  rejected(document(layer("Main",with(ControllerInput.defaults(),"A","MouseLookToggle")),tail),"TAKP-only action");
  rejected(document(layer("Main",with(ControllerInput.defaults(),"A","HoldLayer2")),tail),"missing target layer");
  Map<String,String> missing=new LinkedHashMap<>(ControllerInput.defaults());missing.remove("Select");
  rejected(document(layer("Main",missing),tail),"missing source");
  rejected(document(layer("Main",with(ControllerInput.defaults(),"Z","None")),tail),"extra source");
  rejected(document(main.replace("\"A\": \"MouseLeft\"","\"A\": 1"),tail),"numeric binding");
  rejected(document(main.replace("{\"name\"","{\"extra\": 1, \"name\""),tail),"extra layer key");
  rejected(document(main,tail)+" x","trailing data");
  rejected(document(main,tail+", \"deadzone\": 0.2"),"duplicate key");
  rejected(document(main,tail).replace("Main","Ma\\qin"),"bad escape");
  rejected(document(main,tail).replace("Main","Ma\tin"),"raw control character");
  rejected(document(main,", \"deadzone\": NaN, \"sensitivity\": 550"),"NaN literal");
  rejected(document(main,", \"deadzone\": 01, \"sensitivity\": 550"),"leading zero");
  rejected(document(main,", \"deadzone\": 1., \"sensitivity\": 550"),"bare point");
  rejected(document(main,", \"deadzone\": 1e999, \"sensitivity\": 550"),"overflow");
  rejected("{\"layers\": [\"unterminated","unterminated");
  String deep="1";for(int i=0;i<17;i++)deep="["+deep+"]";
  rejected(document(main,tail+", \"deep\": "+deep),"nesting limit");
  StringBuilder pad=new StringBuilder();while(pad.length()<ControllerProfile.MAX_BYTES)pad.append("xxxxxxxxxxxxxxxx");
  rejected(document(main,tail+", \"pad\": \""+pad+"\""),"over 128 KiB");
  // Six layers of 24-character names stay far below the limit.
  List<ControllerInput.Layer> six=new ArrayList<>();six.add(new ControllerInput.Layer("Main 1234567890123456789",ControllerInput.defaults()));
  for(int i=1;i<6;i++)six.add(new ControllerInput.Layer("Layer "+i+" abcdefghijklmnop",ControllerInput.inherited()));
  ControllerProfile big=new ControllerProfile(six,.18f,550f);need(big.encode().getBytes(StandardCharsets.UTF_8).length<ControllerProfile.MAX_BYTES,"six layers fit");
  need(ControllerProfile.parse(big.encode()).sameBindings(big),"six layer round trip");
 }

 static void files(String folder)throws Exception {
  File dir=new File(folder),file=new File(dir,ControllerProfile.FILE_NAME);
  need(ControllerProfile.load(file)==null,"missing file uses defaults");
  ControllerProfile powers=ControllerProfile.preset("powers");powers.save(file);
  need(ControllerProfile.load(file).sameBindings(powers),"saved profile loads");
  need(!new File(dir,ControllerProfile.FILE_NAME+".new").exists(),"no temporary file left");
  ControllerProfile.defaults().save(file);need(ControllerProfile.load(file).sameBindings(ControllerProfile.defaults()),"save replaces");
  Files.write(file.toPath(),"{\"format\": 2".getBytes(StandardCharsets.UTF_8));
  try{ControllerProfile.load(file);throw new AssertionError("corrupt profile accepted");}catch(IOException expected){}
  byte[] huge=new byte[ControllerProfile.MAX_BYTES+1];Arrays.fill(huge,(byte)' ');Files.write(file.toPath(),huge);
  try{ControllerProfile.load(file);throw new AssertionError("oversized profile accepted");}catch(IOException expected){}
  File nested=new File(new File(dir,"missing-parent"),ControllerProfile.FILE_NAME);powers.save(nested);need(ControllerProfile.load(nested).sameBindings(powers),"creates the private folder");
 }

 static byte[] fixture()throws IOException {
  ByteArrayOutputStream bytes=new ByteArrayOutputStream();DataOutputStream d=new DataOutputStream(bytes);
  d.writeBytes("RFB 003.008\n");d.writeByte(1);d.writeByte(1);d.writeInt(0);d.writeShort(2);d.writeShort(2);d.write(new byte[16]);d.writeInt(0);
  d.writeByte(0);d.writeByte(0);d.writeShort(1);d.writeShort(0);d.writeShort(0);d.writeShort(2);d.writeShort(2);d.writeInt(0);d.write(new byte[16]);
  return bytes.toByteArray();
 }
 static void wheel()throws Exception {
  ByteArrayOutputStream output=new ByteArrayOutputStream();final InteractiveRfbClient[] ref=new InteractiveRfbClient[1];final long[] waited={0};
  InteractiveRfbClient client=new InteractiveRfbClient(new ByteArrayInputStream(fixture()),output,(pixels,w,h,seq)->{
   try{
    InteractiveRfbClient c=ref[0];
    c.sendWheel(5,-3,true,c.inputEpoch());                  // clamps to (1,0); no prior position
    long before=System.nanoTime();c.sendPointer(1,0,1);waited[0]=System.nanoTime()-before; // click after the wheel moved the pointer
    c.sendWheel(1,0,false,c.inputEpoch());                  // wheel down while the left button is held
    c.sendPointer(1,0,0);
    int rejected=0;
    try{c.sendPointer(0,0,8);}catch(IOException expected){rejected++;}
    try{c.sendPointer(0,0,16);}catch(IOException expected){rejected++;}
    long stale=c.inputEpoch();c.cancelPendingInput();
    try{c.sendWheel(0,0,true,stale);}catch(InteractiveRfbClient.InputCancelledException expected){rejected++;}
    need(rejected==3,"ordinary pointer masks stay 0-7 and stale wheels write nothing");
   }catch(IOException e){throw new IllegalStateException(e);}
  });ref[0]=client;
  try{client.sendWheel(0,0,true,client.inputEpoch());throw new AssertionError("wheel before input ready");}catch(IOException expected){}
  try{client.run();}catch(EOFException expected){}
  client.close();
  byte[] wire=output.toByteArray();List<String> messages=new ArrayList<>();
  for(int at=46;at<wire.length;){
   int type=wire[at]&255,size=type==3?10:type==4?8:type==5?6:-1;need(size>0&&at+size<=wire.length,"interleaved wire");
   if(type==5)messages.add("p"+(wire[at+1]&255)+"@"+(((wire[at+2]&255)<<8)|(wire[at+3]&255))+","+(((wire[at+4]&255)<<8)|(wire[at+5]&255)));
   else messages.add("t"+type);
   at+=size;
  }
  need(messages.equals(Arrays.asList("t3","p8@1,0","p0@1,0","p1@1,0","p17@1,0","p1@1,0","p0@1,0","t3")),"wheel wire "+messages);
  need(waited[0]>=280_000_000L,"a click after a wheel move keeps the preposition settle: "+waited[0]);
 }

 public static void main(String[] args)throws Exception {
  switch(args[0]){
   case "overlay":overlay();break;
   case "defaults":defaults();break;
   case "walking":walkingOracle();break;
   case "cursor":cursorOracle();break;
   case "hysteresis":hysteresis();break;
   case "chords":chords();break;
   case "layers":layerInherit();break;
   case "commands":commands();break;
   case "bridge":bridge();break;
   case "json":json();break;
   case "files":files(args[1]);break;
   case "wheel":wheel();break;
   default:throw new AssertionError("unknown scenario");
  }
  System.out.println("PASS");
 }
}
'''

SURFACE_HOST = r'''
package io.github.russianranger.cohclientinteractive;
import android.content.*;import android.os.*;import java.util.*;
public class SurfaceWheelHost {
 static void need(boolean value,String why){if(!value)throw new AssertionError(why);}
 public static void main(String[] args){
  final List<String> wheel=new ArrayList<>();
  ClientSurface surface=new ClientSurface(new Context());
  surface.setSession("0123456789abcdef0123456789abcdef");surface.surfaceCreated(surface.getHolder());Handler.drain();
  surface.setInputListener(new ClientSurface.InputListener(){
   public void onPointer(String s,int x,int y,int b){}public void onReleaseAll(String s){}public void onCursor(float x,float y,boolean v){}
   @Override public void onWheel(String s,int x,int y,boolean up){wheel.add(s.substring(0,4)+"@"+x+","+y+(up?"+":"-"));}
  });
  surface.wheel(1);need(wheel.isEmpty(),"disabled surface sends no wheel");
  surface.setInputEnabled(true);surface.movePointer(10,-20);
  surface.wheel(2);surface.wheel(0);surface.wheel(-25);surface.wheel(Integer.MIN_VALUE);
  need(wheel.size()==12&&wheel.get(0).equals("0123@410,280+")&&wheel.get(1).equals("0123@410,280+")&&wheel.get(2).equals("0123@410,280-")&&wheel.get(11).equals("0123@410,280-"),"wheel ticks "+wheel);
  surface.setInputEnabled(false);surface.wheel(3);need(wheel.size()==12,"disabled again");
  System.out.println("PASS");
 }
}
'''


class ClientControllerJavaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='coh-controller-java-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.path = Path(cls.tmp.name)
        host = cls.path / 'ControllerHost.java'
        host.write_text(HARNESS)
        sources = [JAVA / name for name in ('ClientInput.java', 'ClientOverlayPosition.java', 'ControllerInput.java',
                                            'ControllerProfile.java', 'ControllerBridge.java', 'InteractiveRfbClient.java')]
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8', '-encoding', 'UTF-8',
                        '-d', str(cls.path), *map(str, sources), str(host)],
                       check=True, capture_output=True, text=True, timeout=120)

    def run_case(self, *args):
        result = subprocess.run(['java', '-cp', str(self.path), PACKAGE + '.ControllerHost', *args],
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), 'PASS')

    def test_overlay_position_clamps_to_safe_area_drags_and_persists_relative_corner(self): self.run_case('overlay')
    def test_default_profile_is_todays_fixed_mapping_with_triggers_unbound_and_power_preset(self): self.run_case('defaults')
    def test_default_left_stick_walking_matches_the_earlier_walking_keys_exactly(self): self.run_case('walking')
    def test_default_right_stick_cursor_matches_earlier_deadzone_rescale_and_speed(self): self.run_case('cursor')
    def test_analog_as_button_hysteresis_and_non_finite_release(self): self.run_case('hysteresis')
    def test_chords_press_modifiers_first_release_last_and_are_reference_counted(self): self.run_case('chords')
    def test_layers_inherit_main_hold_latch_cycle_and_validation(self): self.run_case('layers')
    def test_commands_fire_once_per_press_and_menu_release_is_safe(self): self.run_case('commands')
    def test_bridge_reproduces_earlier_buttons_and_keeps_walking_and_input_gates(self): self.run_case('bridge')
    def test_controller_json_format_2_validation_and_limits(self): self.run_case('json')

    def test_controller_json_atomic_save_and_bounded_load(self):
        with tempfile.TemporaryDirectory(prefix='coh-controller-files-') as folder:
            self.run_case('files', folder)
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()), ['controller.json', 'missing-parent'])

    def test_wheel_uses_paired_rfb_buttons_4_and_5_while_ordinary_masks_stay_0_to_7(self): self.run_case('wheel')

    def test_runtime_and_service_keep_pointer_mask_bound_and_route_wheel_as_gameplay_input(self):
        runtime = (JAVA / 'ClientRuntime.java').read_text()
        pointer = production_method(runtime, 'public boolean sendPointer(')
        self.assertIn('mask < 0 || mask > 7', pointer)
        wheel = production_method(runtime, 'public boolean sendWheel(')
        self.assertIn('active.sendWheel(x, y, up, epoch), true)', wheel)
        rfb = production_method((JAVA / 'InteractiveRfbClient.java').read_text(), 'public synchronized void sendPointer(int x, int y, int mask, long expectedEpoch)')
        self.assertIn('if (mask < 0 || mask > 7) throw new IOException("Invalid pointer buttons");', rfb)
        service = production_method((JAVA / 'ClientService.java').read_text(), 'public boolean sendWheel(')
        self.assertIn('busy&&uiVisible&&inputReady&&active!=null&&session.equals(selectedSession)', service)

    def test_surface_wheel_ticks_are_bounded_and_follow_input_enable(self):
        import test_client_surface_capture as surface
        with tempfile.TemporaryDirectory(prefix='coh-surface-wheel-') as folder:
            output = Path(folder)
            sources = []
            for name, content in surface.STUBS.items():
                path = output / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
                sources.append(str(path))
            host = output / 'SurfaceWheelHost.java'
            host.write_text(SURFACE_HOST)
            sources += [str(JAVA / 'ClientSurface.java'), str(JAVA / 'ClientInput.java'), str(host)]
            subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8', '-d', folder, *sources],
                           check=True, capture_output=True, text=True, timeout=120)
            result = subprocess.run(['java', '-cp', folder, PACKAGE + '.SurfaceWheelHost'],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_activity_layout_is_full_window_with_gear_menu_and_persisted_position(self):
        activity = (JAVA / 'ClientActivity.java').read_text()
        self.assertNotIn('dp(224)', activity)
        self.assertIn('FrameLayout root=new FrameLayout(this)', activity)
        self.assertIn('display=new ClientSurface(this);root.addView(display,new FrameLayout.LayoutParams(-1,-1));', activity)
        self.assertIn('getSharedPreferences("client-controls",MODE_PRIVATE)', activity)
        self.assertIn('private static final String CONTROLS_PREFIX="coh.";', activity)
        save = production_method(activity, 'private void saveControlsPosition(')
        self.assertIn('putFloat(CONTROLS_PREFIX+"x",controlsX).putFloat(CONTROLS_PREFIX+"y",controlsY).apply()', save)
        self.assertIn('ClientOverlayPosition.normalized(controlsPreferences.getFloat(CONTROLS_PREFIX+"x",1f),1f)', activity)
        menu = production_method(activity, 'private void setMenuOpen(')
        self.assertIn('if(!open&&!gameSessionRunning())open=true;', menu)
        self.assertLess(menu.index('releaseControls(false)'), menu.index('refreshControllerCapture()'))
        back = production_method(activity, '@Override public void onBackPressed(')
        self.assertLess(back.index('setMenuOpen(true)'), back.index('super.onBackPressed()'))
        captures = production_method(activity, 'private boolean controllerCaptures(')
        for gate in ('hasWindowFocus()', '!menuOpen', '!textDialogVisible', '!mappingsOpen', '!controlsDragging'):
            self.assertIn(gate, captures)
        immersive = production_method(activity, 'private void immersive(')
        self.assertIn('BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE', immersive)
        self.assertIn('SYSTEM_UI_FLAG_IMMERSIVE_STICKY', immersive)
        self.assertIn('new File(getFilesDir(),ControllerProfile.FILE_NAME)', activity)
        # Every former sidebar control is still built into the menu panel.
        for control in ('setup=button(', 'importAssets=button(', 'performanceGraphics=new CheckBox(', 'prootFastMode=new CheckBox(',
                        'prestartNextZone=new CheckBox(', 'idleResidentMaps=new CheckBox(', 'sharedServerData=new CheckBox(',
                        'clientSkipServerFolders=new CheckBox(', 'clientFolderIndex=new CheckBox(', 'clientAudio=new CheckBox(',
                        'sharedHeap=new CheckBox(', 'trustedBins=new CheckBox(', 'gameplay60=new CheckBox(', 'clientArchitecture=new Spinner(',
                        'gpuProfile=new Spinner(', 'run=button(', 'createFresh=button(', 'resumeCreation=button(', 'returnGround=button(',
                        'startTest=button(', 'stopTest=button(', 'captureContact=button(', 'openTaskContact=button(',
                        'captureAcceptedTask=button(', 'completeTask=button(', 'captureCompletedTask=button(', 'travelZone=button(',
                        'saveLogout=button(', 'finish=button(', 'typeText=button(', 'enterKey=button(', 'showFps=button(',
                        'fps10=button(', 'fps30=button(', 'fps60=button(', 'stop=button(', 'export=button(', 'recoverReports=button(',
                        'storage=button('):
            self.assertEqual(activity.count(control), 1, control)
        body = activity[activity.index('TextView title=text("COH Atlas Gameplay"'):activity.index('buildOverlay(root,scroll,panel);')]
        self.assertNotIn('root.addView(', body)
        self.assertGreater(len(re.findall(r'controls\.addView\(', body)), 40)


if __name__ == '__main__':
    unittest.main()
