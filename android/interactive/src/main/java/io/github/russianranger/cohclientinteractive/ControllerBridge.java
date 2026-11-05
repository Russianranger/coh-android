package io.github.russianranger.cohclientinteractive;

import java.util.*;

/**
 * COH output for ControllerInput (in place of TRASC's DisplayInput): keys use the activity's
 * shared key owners and RFB key path, mouse buttons and the cursor use ClientSurface, and the
 * wheel becomes paired RFB button 4/5 events. Controller movement keys (W, A, S, D, Space)
 * keep the earlier walking gate; other keys follow the ordinary game-input gate.
 */
public final class ControllerBridge implements ControllerInput.Sink {
    public interface Target {
        /** Ordinary game input is open (earlier controller key gate). */
        boolean keysOpen();
        /** Character movement is allowed (earlier canWalk gate for stick walking and jump). */
        boolean walkOpen();
        boolean holds(int owner);
        void press(int owner,int keysym);
        void release(int owner);
        void mouse(int button,boolean down);
        void pointer(float dx,float dy);
        void wheel(int amount);
        void command(String action);
        default void layer(int index,String name){}
    }
    /** Above keyboard key codes and the touch/stick/hat owners (100001-120005). */
    static final int OWNER_BASE=130000;
    static final Set<String> MOVEMENT=Collections.unmodifiableSet(new HashSet<>(Arrays.asList("KeyW","KeyA","KeyS","KeyD","Space")));
    private final Target target;
    // Key atoms the profile currently holds, including any a closed gate did not send.
    private final Set<String> desired=new LinkedHashSet<>();
    public ControllerBridge(Target target){this.target=target;}

    static int keysym(String action){
        if(action.matches("Key[A-Z]"))return action.charAt(3)+32;
        if(action.matches("Digit[0-9]"))return action.charAt(5);
        if(action.matches("F([1-9]|1[0-2])"))return 0xffbd+Integer.parseInt(action.substring(1));
        switch(action){
            case "NumLock":return 0xff7f;case "Space":return 32;case "Enter":return ClientInput.RETURN_KEY;case "Escape":return 0xff1b;case "Tab":return 0xff09;case "Backspace":return 0xff08;
            case "ArrowLeft":return 0xff51;case "ArrowUp":return 0xff52;case "ArrowRight":return 0xff53;case "ArrowDown":return 0xff54;
            case "ShiftLeft":return 0xffe1;case "ControlLeft":return 0xffe3;case "AltLeft":return 0xffe9;
            case "Home":return 0xff50;case "End":return 0xff57;case "PageUp":return 0xff55;case "PageDown":return 0xff56;case "Insert":return 0xff63;case "Delete":return 0xffff;
            case "Minus":return '-';case "Equal":return '=';case "BracketLeft":return '[';case "BracketRight":return ']';case "Semicolon":return ';';case "Quote":return '\'';
            case "Comma":return ',';case "Period":return '.';case "Slash":return '/';case "Backslash":return '\\';case "Backquote":return '`';default:return 0;
        }
    }
    /** RFB pointer button bits: 1 left, 2 middle, 4 right. */
    static int mouseButton(String action){
        switch(action){case "MouseLeft":return 1;case "MouseMiddle":return 2;case "MouseRight":return 4;default:return 0;}
    }
    static int owner(String action){int index=ControllerInput.ACTIONS.indexOf(action);return index<0?-1:OWNER_BASE+index;}
    private boolean allowed(String atom){return target.keysOpen()&&(!MOVEMENT.contains(atom)||target.walkOpen());}
    private void send(String atom){
        int symbol=keysym(atom);
        // A controller-held Shift sends the shifted letter, as TRASC does.
        if(symbol>='a'&&symbol<='z'&&desired.contains("ShiftLeft"))symbol-=32;
        target.press(owner(atom),symbol);
    }
    @Override public void button(String action,boolean down){
        if(ControllerInput.isCommand(action)){if(down)target.command(action);return;}
        int button=mouseButton(action);
        if(button!=0){if(!down||target.keysOpen())target.mouse(button,down);return;}
        if(keysym(action)==0||owner(action)<0)return;
        if(down){desired.add(action);if(allowed(action))send(action);}
        else{desired.remove(action);target.release(owner(action));}
    }
    @Override public void pointer(float dx,float dy){target.pointer(dx,dy);}
    @Override public void wheel(int amount){if(target.keysOpen())target.wheel(amount);}
    @Override public void layer(int index,String name){target.layer(index,name);}
    /**
     * Re-applies the gates to held controller keys: a closed gate releases them, and walking
     * keys resume when walking reopens (the earlier stick walking was level-triggered).
     * Other keys need a fresh press, as before.
     */
    public void refresh(){
        for(String atom:new ArrayList<>(desired)){
            int owner=owner(atom);boolean held=target.holds(owner);
            if(held&&!allowed(atom))target.release(owner);
            else if(!held&&MOVEMENT.contains(atom)&&allowed(atom))send(atom);
        }
    }
    Set<String> desired(){return Collections.unmodifiableSet(desired);}
}
