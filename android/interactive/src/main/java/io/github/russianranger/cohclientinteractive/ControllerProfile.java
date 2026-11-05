package io.github.russianranger.cohclientinteractive;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.*;

/**
 * The saved controller profile: TRASC's controller.json format 2
 * ({format:2, layers:[{name, bindings}], deadzone, sensitivity}), at most 128 KiB,
 * validated completely before it replaces the active bindings and written atomically.
 * A small strict JSON reader keeps this testable without Android's org.json.
 */
final class ControllerProfile {
    static final int FORMAT=2,MAX_BYTES=128*1024;
    static final String FILE_NAME="controller.json";
    static final List<String> PRESETS=Collections.unmodifiableList(Arrays.asList("original","powers"));
    final List<ControllerInput.Layer> layers;
    final float deadzone,sensitivity;
    ControllerProfile(List<ControllerInput.Layer> layers,float deadzone,float sensitivity){
        ControllerInput.validate(layers,deadzone,sensitivity);
        this.layers=Collections.unmodifiableList(new ArrayList<>(layers));this.deadzone=deadzone;this.sensitivity=sensitivity;
    }
    static ControllerProfile defaults(){return new ControllerProfile(ControllerInput.defaultLayers(),ControllerInput.DEFAULT_DEADZONE,ControllerInput.DEFAULT_SENSITIVITY);}
    static ControllerProfile preset(String name){
        if("original".equals(name))return defaults();
        if("powers".equals(name))return new ControllerProfile(ControllerInput.powerTrayLayers(),ControllerInput.DEFAULT_DEADZONE,ControllerInput.DEFAULT_SENSITIVITY);
        throw new IllegalArgumentException("Unknown controller preset");
    }
    boolean sameBindings(ControllerProfile other){
        if(other==null||other.layers.size()!=layers.size()||Float.compare(other.deadzone,deadzone)!=0||Float.compare(other.sensitivity,sensitivity)!=0)return false;
        for(int i=0;i<layers.size();i++)if(!layers.get(i).name.equals(other.layers.get(i).name)||!layers.get(i).bindings.equals(other.layers.get(i).bindings))return false;
        return true;
    }

    /** Missing file: null (use the defaults). Anything else must validate in full. */
    static ControllerProfile load(File file)throws IOException {
        if(!file.exists())return null;
        if(!file.isFile())throw new IOException("Controller profile is not a file");
        if(file.length()>MAX_BYTES)throw new IOException("Controller profile exceeds limits");
        byte[] raw=Files.readAllBytes(file.toPath());
        if(raw.length>MAX_BYTES)throw new IOException("Controller profile exceeds limits");
        try{return parse(new String(raw,StandardCharsets.UTF_8));}
        catch(IllegalArgumentException invalid){throw new IOException(invalid.getMessage(),invalid);}
    }
    /** Encodes and bounds the profile first, then replaces the file in one rename. */
    void save(File file)throws IOException {
        byte[] encoded=encode().getBytes(StandardCharsets.UTF_8);
        if(encoded.length>MAX_BYTES)throw new IOException("Controller profile exceeds limits");
        File parent=file.getAbsoluteFile().getParentFile();
        if(parent==null||!parent.isDirectory()&&!parent.mkdirs())throw new IOException("Controller profile folder unavailable");
        File temp=new File(parent,file.getName()+".new");
        try{
            try(FileOutputStream out=new FileOutputStream(temp)){out.write(encoded);out.getFD().sync();}
            Files.move(temp.toPath(),file.toPath(),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
        }finally{if(temp.exists()&&!temp.delete())temp.deleteOnExit();}
    }

    static ControllerProfile parse(String text){
        if(text==null||text.length()>MAX_BYTES||text.getBytes(StandardCharsets.UTF_8).length>MAX_BYTES)throw new IllegalArgumentException("Controller profile exceeds limits");
        Object root=new Reader(text).document();
        if(!(root instanceof Map))throw new IllegalArgumentException("Controller profile must be a JSON object");
        Map<?,?> data=(Map<?,?>)root;
        Object format=data.containsKey("format")?data.get("format"):Double.valueOf(FORMAT);
        if(!(format instanceof Double)||((Double)format)!=FORMAT)throw new IllegalArgumentException("Unsupported controller profile version");
        Object rawLayers=data.get("layers");
        if(!(rawLayers instanceof List))throw new IllegalArgumentException("Controller profile needs a layers list");
        List<?> list=(List<?>)rawLayers;
        if(list.isEmpty()||list.size()>ControllerInput.MAX_LAYERS)throw new IllegalArgumentException("Choose between 1 and 6 layers");
        List<ControllerInput.Layer> layers=new ArrayList<>();
        for(Object item:list){
            if(!(item instanceof Map))throw new IllegalArgumentException("Each controller layer must be an object");
            Map<?,?> layer=(Map<?,?>)item;
            if(!new HashSet<>(Arrays.asList("name","bindings")).equals(layer.keySet()))throw new IllegalArgumentException("Each controller layer needs exactly a name and bindings");
            Object name=layer.get("name"),bindings=layer.get("bindings");
            if(!(name instanceof String)||!(bindings instanceof Map))throw new IllegalArgumentException("Invalid controller layer");
            Map<String,String> map=new LinkedHashMap<>();
            Map<?,?> source=(Map<?,?>)bindings;
            if(!source.keySet().equals(new HashSet<>(ControllerInput.SOURCES)))throw new IllegalArgumentException("Every layer must contain all controller sources");
            for(String key:ControllerInput.SOURCES){
                Object value=source.get(key);
                if(!(value instanceof String))throw new IllegalArgumentException("Controller bindings must be action names");
                map.put(key,(String)value);
            }
            layers.add(new ControllerInput.Layer(((String)name).trim(),map));
        }
        return new ControllerProfile(layers,number(data.get("deadzone"),"deadzone"),number(data.get("sensitivity"),"sensitivity"));
    }
    private static float number(Object value,String name){
        if(!(value instanceof Double))throw new IllegalArgumentException("Controller profile needs a numeric "+name);
        return (float)(double)(Double)value;
    }
    String encode(){
        StringBuilder out=new StringBuilder("{\n  \"format\": ").append(FORMAT).append(",\n  \"layers\": [");
        for(int i=0;i<layers.size();i++){
            ControllerInput.Layer layer=layers.get(i);
            out.append(i==0?"\n":",\n").append("    {\"name\": ");quote(out,layer.name);out.append(", \"bindings\": {");
            int n=0;for(String source:ControllerInput.SOURCES){out.append(n++==0?"":", ");quote(out,source);out.append(": ");quote(out,layer.bindings.get(source));}
            out.append("}}");
        }
        return out.append("\n  ],\n  \"deadzone\": ").append(Float.toString(deadzone)).append(",\n  \"sensitivity\": ").append(Float.toString(sensitivity)).append("\n}\n").toString();
    }
    private static void quote(StringBuilder out,String value){
        out.append('"');
        for(int i=0;i<value.length();i++){
            char c=value.charAt(i);
            if(c=='"'||c=='\\')out.append('\\').append(c);
            else if(c<0x20)out.append(String.format(Locale.ROOT,"\\u%04x",(int)c));
            else out.append(c);
        }
        out.append('"');
    }

    /** RFC 8259 subset reader: objects, arrays, strings, numbers, literals; duplicate keys and deep nesting rejected. */
    static final class Reader {
        private static final int MAX_DEPTH=16;
        private final String text;private int at,depth;
        Reader(String text){this.text=text;}
        Object document(){Object value=value();space();if(at!=text.length())fail("trailing data");return value;}
        private void fail(String what){throw new IllegalArgumentException("Controller profile is not valid JSON: "+what+" at "+at);}
        private void space(){while(at<text.length()&&" \t\r\n".indexOf(text.charAt(at))>=0)at++;}
        private char peek(){if(at>=text.length())fail("unexpected end");return text.charAt(at);}
        private void expect(char c){if(peek()!=c)fail("expected '"+c+"'");at++;}
        private Object value(){
            space();char c=peek();
            if(c=='{')return object();if(c=='[')return array();if(c=='"')return string();
            if(text.startsWith("true",at)){at+=4;return Boolean.TRUE;}
            if(text.startsWith("false",at)){at+=5;return Boolean.FALSE;}
            if(text.startsWith("null",at)){at+=4;return null;}
            return number();
        }
        private Map<String,Object> object(){
            if(++depth>MAX_DEPTH)fail("nesting too deep");
            expect('{');Map<String,Object> result=new LinkedHashMap<>();space();
            if(peek()=='}'){at++;depth--;return result;}
            while(true){
                space();String key=string();space();expect(':');
                if(result.containsKey(key))fail("duplicate key");
                result.put(key,value());space();
                if(peek()==','){at++;continue;}
                expect('}');depth--;return result;
            }
        }
        private List<Object> array(){
            if(++depth>MAX_DEPTH)fail("nesting too deep");
            expect('[');List<Object> result=new ArrayList<>();space();
            if(peek()==']'){at++;depth--;return result;}
            while(true){
                result.add(value());space();
                if(peek()==','){at++;continue;}
                expect(']');depth--;return result;
            }
        }
        private String string(){
            expect('"');StringBuilder out=new StringBuilder();
            while(true){
                char c=peek();at++;
                if(c=='"')return out.toString();
                if(c<0x20)fail("control character in string");
                if(c!='\\'){out.append(c);continue;}
                char e=peek();at++;
                switch(e){
                    case '"':case '\\':case '/':out.append(e);break;
                    case 'b':out.append('\b');break;case 'f':out.append('\f');break;
                    case 'n':out.append('\n');break;case 'r':out.append('\r');break;case 't':out.append('\t');break;
                    case 'u':
                        if(at+4>text.length())fail("short unicode escape");
                        try{out.append((char)Integer.parseInt(text.substring(at,at+4),16));}catch(NumberFormatException bad){fail("bad unicode escape");}
                        at+=4;break;
                    default:fail("bad escape");
                }
            }
        }
        private boolean digit(int index){return index<text.length()&&text.charAt(index)>='0'&&text.charAt(index)<='9';}
        private Double number(){
            int start=at;
            if(at<text.length()&&text.charAt(at)=='-')at++;
            if(at<text.length()&&text.charAt(at)=='0')at++;
            else{if(!digit(at))fail("unexpected character");while(digit(at))at++;}
            if(at<text.length()&&text.charAt(at)=='.'){at++;if(!digit(at))fail("bad number");while(digit(at))at++;}
            if(at<text.length()&&(text.charAt(at)=='e'||text.charAt(at)=='E')){
                at++;if(at<text.length()&&(text.charAt(at)=='+'||text.charAt(at)=='-'))at++;
                if(!digit(at))fail("bad number");while(digit(at))at++;
            }
            double value=Double.parseDouble(text.substring(start,at));
            if(!Double.isFinite(value))fail("number out of range");
            return value;
        }
    }
}
