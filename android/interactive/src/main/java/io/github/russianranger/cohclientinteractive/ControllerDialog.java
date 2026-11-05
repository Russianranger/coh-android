package io.github.russianranger.cohclientinteractive;

import android.app.Activity;
import android.app.AlertDialog;
import android.text.InputFilter;
import android.text.InputType;
import android.view.View;
import android.widget.*;
import java.util.*;

/** Edits the saved named-layer controller profile without closing the game (ported from TRASC). */
final class ControllerDialog {
    private static final String[] PRESET_LABELS={"Original COH bindings (default)","COH power trays: hold LT, buttons press 1–0; Select opens the menu"};
    private final Activity activity;
    private final ControllerManager controller;
    private final Runnable dismissed;
    private final List<String> names=new ArrayList<>();
    private final List<Map<String,String>> maps=new ArrayList<>();
    private float draftDeadzone,draftSpeed;
    private LinearLayout root,rows;
    private Spinner layer;
    private EditText layerName,deadzone,speed;
    private int editing;
    ControllerDialog(Activity activity,ControllerManager controller,Runnable dismissed){this.activity=activity;this.controller=controller;this.dismissed=dismissed;}
    private void label(String text){TextView v=new TextView(activity);v.setText(text);v.setPadding(8,12,8,4);root.addView(v);}
    private Spinner spinner(List<String> choices){Spinner s=new Spinner(activity);s.setAdapter(new ArrayAdapter<>(activity,android.R.layout.simple_spinner_dropdown_item,choices));root.addView(s);return s;}
    private void button(String text,Runnable action){Button b=new Button(activity);b.setText(text);b.setAllCaps(false);b.setOnClickListener(v->action.run());root.addView(b);}
    private void load(ControllerProfile profile){
        names.clear();maps.clear();
        for(ControllerInput.Layer item:profile.layers){names.add(item.name);maps.add(new LinkedHashMap<>(item.bindings));}
        draftDeadzone=profile.deadzone;draftSpeed=profile.sensitivity;editing=0;
    }
    void show(){
        load(controller.profile());
        root=new LinearLayout(activity);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(20,8,20,12);
        label("Bindings for the first controller that sends input. The original COH bindings are the default. Next/Previous or Go to layer switch layers; Hold layer switches while held. Inherit uses Main. W, A, S, D and Space keep the walking gate. Changes apply only on Save.");
        if(!controller.loadError().isEmpty())label(controller.loadError());
        Spinner preset=spinner(Arrays.asList(PRESET_LABELS));
        button("Apply preset to editor",()->{load(ControllerProfile.preset(ControllerProfile.PRESETS.get(preset.getSelectedItemPosition())));fill();});
        label("Edit layer");layer=spinner(Collections.singletonList("Main"));
        layer.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){
            @Override public void onItemSelected(AdapterView<?> p,View v,int pos,long id){if(pos<names.size()&&pos!=editing){keepName();editing=pos;render();}}
            @Override public void onNothingSelected(AdapterView<?> p){}
        });
        layerName=new EditText(activity);layerName.setSingleLine(true);layerName.setFilters(new InputFilter[]{new InputFilter.LengthFilter(24)});root.addView(layerName);
        button("Rename layer",()->{keepName();fillLayers();});
        button("Add layer (up to 6)",()->{
            if(names.size()>=ControllerInput.MAX_LAYERS){Toast.makeText(activity,"Maximum 6 layers",Toast.LENGTH_SHORT).show();return;}
            keepName();int number=names.size()+1;String name="Layer "+number;while(hasName(name))name="Layer "+(++number);
            names.add(name);maps.add(ControllerInput.inherited());editing=names.size()-1;fillLayers();
        });
        button("Remove selected layer",()->{
            if(editing==0){Toast.makeText(activity,"Main provides inherited bindings and cannot be removed",Toast.LENGTH_SHORT).show();return;}
            int removed=editing;names.remove(removed);maps.remove(removed);
            for(Map<String,String> map:maps)for(String source:ControllerInput.SOURCES){
                String action=map.get(source);int target=ControllerInput.layerTarget(action);
                if(target==removed)map.put(source,"None");
                else if(target>removed)map.put(source,(action.startsWith("Hold")?"HoldLayer":"Layer")+target);
            }
            editing=Math.min(editing,names.size()-1);fillLayers();
        });
        label("Pointer stick deadzone (0.05–0.80)");deadzone=new EditText(activity);deadzone.setInputType(InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL);root.addView(deadzone);
        label("Pointer speed (50–2500 pixels/sec)");speed=new EditText(activity);speed.setInputType(InputType.TYPE_CLASS_NUMBER|InputType.TYPE_NUMBER_FLAG_DECIMAL);root.addView(speed);
        label("Sticks and triggers bound to keys or buttons press at 35% and release below 20%.");
        rows=new LinearLayout(activity);rows.setOrientation(LinearLayout.VERTICAL);root.addView(rows);fill();
        ScrollView scroll=new ScrollView(activity);scroll.addView(root);
        AlertDialog dialog=new AlertDialog.Builder(activity).setTitle("Controller mappings").setView(scroll).setPositiveButton("Save",null).setNegativeButton("Cancel",null).create();
        dialog.setOnDismissListener(d->dismissed.run());dialog.show();
        dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v->{try{
            keepName();
            List<ControllerInput.Layer> layers=new ArrayList<>();
            for(int i=0;i<names.size();i++)layers.add(new ControllerInput.Layer(names.get(i).trim(),maps.get(i)));
            controller.save(new ControllerProfile(layers,Float.parseFloat(deadzone.getText().toString().trim()),Float.parseFloat(speed.getText().toString().trim())));
            dialog.dismiss();
        }catch(Exception e){Toast.makeText(activity,e instanceof NumberFormatException?"Enter numbers for deadzone and pointer speed":String.valueOf(e.getMessage()),Toast.LENGTH_LONG).show();}});
    }
    private void keepName(){if(layerName!=null&&editing<names.size())names.set(editing,layerName.getText().toString().trim());}
    private boolean hasName(String name){for(String existing:names)if(name.equalsIgnoreCase(existing))return true;return false;}
    private void fill(){deadzone.setText(Float.toString(draftDeadzone));speed.setText(Float.toString(draftSpeed));fillLayers();}
    private void fillLayers(){
        List<String> labels=new ArrayList<>();for(int i=0;i<names.size();i++)labels.add((i+1)+" · "+names.get(i));
        layer.setAdapter(new ArrayAdapter<>(activity,android.R.layout.simple_spinner_dropdown_item,labels));layer.setSelection(editing);render();
    }
    private String actionLabel(String action){
        int target=ControllerInput.layerTarget(action);
        if(target>=0)return (action.startsWith("Hold")?"Hold: ":"Go to: ")+names.get(target);
        switch(action){
            case "Inherit":return "Inherit (use Main)";case "LayerNext":return "Next layer";case "LayerPrevious":return "Previous layer";
            case "MouseLeft":return "Left click";case "MouseRight":return "Right click / turn view";case "MouseMiddle":return "Middle click";
            case "PointerUp":return "Cursor up";case "PointerDown":return "Cursor down";case "PointerLeft":return "Cursor left";case "PointerRight":return "Cursor right";
            case "WheelUp":return "Mouse wheel up";case "WheelDown":return "Mouse wheel down";
            case "SendEnter":return "Enter (one press, like Start)";case "TextEntry":return "Send text dialog";case "ClientMenu":return "Open options menu";
            default:return action.replace("ShiftLeft+","Shift + ").replace("ControlLeft+","Ctrl + ").replace("AltLeft+","Alt + ").replace("Digit","Number ").replace("Key","Key ");
        }
    }
    private void render(){
        if(rows==null||layerName==null||editing>=maps.size())return;
        rows.removeAllViews();layerName.setText(names.get(editing));final Map<String,String> map=maps.get(editing);
        final List<String> choices=new ArrayList<>();if(editing>0)choices.add("Inherit");
        for(String a:ControllerInput.ACTIONS)if(ControllerInput.layerTarget(a)<names.size())choices.add(a);
        List<String> labels=new ArrayList<>();for(String a:choices)labels.add(actionLabel(a));
        for(final String source:ControllerInput.SOURCES){
            TextView label=new TextView(activity);label.setText(ControllerInput.sourceLabel(source));rows.addView(label);
            Spinner s=new Spinner(activity);s.setContentDescription(source+" layer "+(editing+1)+" binding");
            s.setAdapter(new ArrayAdapter<>(activity,android.R.layout.simple_spinner_dropdown_item,labels));
            s.setSelection(Math.max(0,choices.indexOf(map.get(source))));rows.addView(s);
            s.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener(){
                @Override public void onItemSelected(AdapterView<?> p,View v,int pos,long id){map.put(source,choices.get(pos));}
                @Override public void onNothingSelected(AdapterView<?> p){}
            });
        }
    }
}
