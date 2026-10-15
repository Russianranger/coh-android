package org.coh.nativecombined;

import android.content.Context;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.util.*;

/** Trust roots shipped in this small APK. An imported archive never supplies its own pins. */
public final class ImportContract {
    public interface Progress { void update(String phase, long done, long total); }
    public static final class Control {
        private volatile boolean cancelled;
        private Runnable cancelHook;
        public synchronized void cancel() { cancelled=true;if(cancelHook!=null)cancelHook.run(); }
        synchronized void whenCancelled(Runnable hook) { cancelHook=hook;if(cancelled&&hook!=null)hook.run(); }
        public boolean isCancelled() { return cancelled; }
        public void check() throws InterruptedIOException {
            if(cancelled||Thread.currentThread().isInterrupted())throw new InterruptedIOException("Operation stopped; previously verified imports are preserved");
        }
        synchronized void publish(RunnableCommit commit) throws IOException { check();commit.run(); }
    }
    interface RunnableCommit { void run() throws IOException; }
    public static final class Pin {
        public final long bytes;
        public final String sha256;
        public Pin(long bytes,String sha256)throws IOException {
            if(bytes<0||bytes>8L*1024*1024*1024||sha256==null||!sha256.matches("[0-9a-f]{64}"))throw new IOException("Invalid pinned input");
            this.bytes=bytes;this.sha256=sha256;
        }
    }
    public final String digest, donorName;
    public final Pin donor;
    public final SortedMap<String,Pin> donorFiles, bundledFiles;
    public final JSONObject runtimeManifest, runtimeLock;
    public final byte[] runtimeManifestBytes;
    public ImportContract(Context context)throws Exception {
        byte[] raw=asset(context,"combined/import-contract.json",1024*1024);
        JSONObject value=new JSONObject(new String(raw,StandardCharsets.UTF_8));
        if(value.getInt("format")!=1)throw new IOException("Unsupported import contract");
        JSONObject apk=value.getJSONObject("donor_apk");
        donorName=apk.getString("name");donor=pin(apk);
        if(donor.bytes<1||!donorName.matches("[A-Za-z0-9_.-]+\\.apk")||donor.bytes>128L*1024*1024)throw new IOException("Unsupported donor APK");
        donorFiles=inventory(value.getJSONObject("donor_files"),"assets/runtime/");
        bundledFiles=inventory(value.has("bundled_files")?value.getJSONObject("bundled_files"):new JSONObject(),"runtime/");
        if(donorFiles.isEmpty())throw new IOException("Donor runtime inventory is absent");
        runtimeManifestBytes=asset(context,"runtime/runtime-manifest.json",2*1024*1024);
        runtimeManifest=new JSONObject(new String(runtimeManifestBytes,StandardCharsets.UTF_8));
        if(runtimeManifest.getInt("format")!=1)throw new IOException("Unsupported runtime manifest");
        runtimeLock=new JSONObject(new String(asset(context,"runtime/runtime-lock.json",65536),StandardCharsets.UTF_8));
        pin(runtimeLock.getJSONObject("base"));pin(runtimeLock.getJSONObject("wine"));
        digest=hex(hash().digest(raw));
    }
    private static SortedMap<String,Pin> inventory(JSONObject value,String prefix)throws Exception {
        SortedMap<String,Pin> result=new TreeMap<>();
        for(Iterator<String> i=value.keys();i.hasNext();) {
            String name=i.next();String leaf=name.startsWith(prefix)?name.substring(prefix.length()):"";
            safeLeaf(leaf);if(result.size()>=512)throw new IOException("Unbounded import inventory");
            result.put(name,pin(value.getJSONObject(name)));
        }
        return Collections.unmodifiableSortedMap(result);
    }
    static Pin pin(JSONObject value)throws Exception { return new Pin(value.getLong("bytes"),value.getString("sha256")); }
    static void safeLeaf(String name)throws IOException {
        if(name==null||!name.matches("[A-Za-z0-9_][A-Za-z0-9_.-]{0,159}")||name.equals(".")||name.equals(".."))throw new IOException("Unsafe runtime member");
    }
    static byte[] asset(Context context,String name,int limit)throws IOException {
        try(InputStream in=context.getAssets().open(name)){return bounded(in,limit);}
    }
    static byte[] bounded(InputStream in,int limit)throws IOException {
        ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int count;
        while((count=in.read(buffer))!=-1){if(count==0)throw new IOException("Input made no progress");if(out.size()+count>limit)throw new IOException("Metadata exceeds its size limit");out.write(buffer,0,count);}return out.toByteArray();
    }
    static MessageDigest hash(){try{return MessageDigest.getInstance("SHA-256");}catch(NoSuchAlgorithmException e){throw new AssertionError(e);}}
    static String hex(byte[] bytes){StringBuilder out=new StringBuilder();for(byte b:bytes){out.append(Character.forDigit((b>>>4)&15,16));out.append(Character.forDigit(b&15,16));}return out.toString();}
}
