package io.github.russianranger.cohdiagnostic;

import android.app.ActivityManager;
import android.content.Context;
import android.os.SystemClock;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.security.MessageDigest;
import java.util.*;

/** Android adapter for the independently versioned, APK-pinned asset release. */
public final class AssetPackStore {
    private final AssetPackArchive archive;
    private final SetupMemoryGuard guard;
    public final String version;
    public AssetPackStore(Context context,JSONObject runtime,AssetPackArchive.Check check,
            AssetPackArchive.Progress progress) throws Exception {
        JSONObject expected=runtime.getJSONObject("external_asset_pack");
        byte[] raw;
        try(InputStream input=context.getAssets().open("runtime/asset-pack-manifest.json")){raw=bounded(input,1024*1024);}
        JSONObject descriptor=new JSONObject(new String(raw,StandardCharsets.UTF_8));
        version=descriptor.getString("version");
        if(descriptor.getInt("format")!=1||!"coh-assets".equals(descriptor.getString("id"))
                ||!version.matches("[0-9]+\\.[0-9]+\\.[0-9]+")||expected.getInt("format")!=1
                ||!expected.getString("id").equals(descriptor.getString("id"))
                ||!expected.getString("version").equals(version)||expected.getLong("manifest_bytes")!=raw.length
                ||!expected.getString("manifest_sha256").equals(hex(MessageDigest.getInstance("SHA-256").digest(raw))))
            throw new IOException("The APK asset pack descriptor is inconsistent");
        Map<String,AssetPackArchive.Pin> files=new TreeMap<>();JSONObject manifestFiles=descriptor.getJSONObject("files");
        for(Iterator<String> names=manifestFiles.keys();names.hasNext();) {
            String name=names.next();JSONObject pin=manifestFiles.getJSONObject(name);
            files.put(name,new AssetPackArchive.Pin(pin.getLong("bytes"),pin.getString("sha256")));
            if(name.startsWith("runtime/")) {
                JSONObject runtimeFiles=runtime.getJSONObject("files");String runtimeName=name.substring(8);
                if(!runtimeFiles.has(runtimeName))throw new IOException("Asset is absent from runtime inventory: "+name);
                JSONObject runtimePin=runtimeFiles.getJSONObject(runtimeName);
                if(runtimePin.getLong("bytes")!=pin.getLong("bytes")||!runtimePin.getString("sha256").equals(pin.getString("sha256")))
                    throw new IOException("Asset and runtime pins differ: "+name);
            }
        }
        Map<String,Set<String>> volumes=new TreeMap<>();JSONObject entries=descriptor.getJSONObject("volumes");
        for(Iterator<String> names=entries.keys();names.hasNext();) {
            String name=names.next();JSONArray array=entries.getJSONArray(name);Set<String> members=new TreeSet<>();
            for(int i=0;i<array.length();i++)if(!members.add(array.getString(i)))throw new IOException("Duplicate asset volume member");
            volumes.put(name,members);
        }
        ActivityManager manager=(ActivityManager)context.getSystemService(Context.ACTIVITY_SERVICE);
        ActivityManager.MemoryInfo memory=new ActivityManager.MemoryInfo();Runtime vm=Runtime.getRuntime();
        guard=new SetupMemoryGuard(()->{
            if(manager==null)throw new IOException("Android memory service is unavailable");
            manager.getMemoryInfo(memory);
            return new SetupMemoryGuard.Sample(memory.availMem,memory.totalMem,memory.threshold,memory.lowMemory,vm.totalMemory()-vm.freeMemory(),vm.maxMemory());
        },SystemClock::uptimeMillis,Thread::sleep,check::check,paused->{if(paused)progress.update("Waiting for memory; previous assets are preserved",0,0);});
        archive=new AssetPackArchive(new File(context.getFilesDir().getCanonicalFile(),"asset-packs"),raw,files,volumes,check,
                new AssetPackArchive.Io(){
                    public void before()throws IOException{guard.beforeIo();}
                    public void read(long bytes)throws IOException{guard.read(bytes);}
                    public void written(long bytes,AssetPackArchive.Sync sync)throws IOException{guard.written(bytes,sync::sync);}
                    public void synced(){guard.synced();}
                },progress);
    }
    public boolean contains(String path){return archive.contains(path);}
    public boolean isAccepted()throws IOException{return archive.isAccepted();}
    public List<String> missingVolumes()throws IOException{return archive.missingVolumes();}
    public File resolve(String path)throws IOException{return archive.resolve(path);}
    public InputStream open(String path)throws IOException{return archive.open(path);}
    public String importVolume(InputStream input)throws IOException{guard.admit();String volume=archive.importVolume(input);guard.finishWrites();return volume;}
    public JSONObject receipt()throws Exception {
        return new JSONObject().put("format",1).put("version",version).put("manifest_sha256",archive.descriptorHash())
                .put("complete",archive.isAccepted()).put("missing_parts",new JSONArray(archive.missingVolumes()))
                .put("memory_control",new JSONObject(guard.receipt()));
    }
    public String status()throws IOException {
        return "Assets "+version+(isAccepted()?" verified; reusable with this APK":" — import "+String.join(", ",missingVolumes())+" part(s)");
    }
    /** Small receipt and size checks only; callers keep this off the UI thread. */
    public static String status(Context context) {
        try {
            byte[] raw;
            try(InputStream in=context.getAssets().open("runtime/asset-pack-manifest.json")){raw=bounded(in,1024*1024);}
            JSONObject descriptor=new JSONObject(new String(raw,StandardCharsets.UTF_8));
            String version=descriptor.getString("version"),hash=hex(MessageDigest.getInstance("SHA-256").digest(raw));
            File base=new File(context.getFilesDir().getCanonicalFile(),"asset-packs");
            if(!base.getCanonicalFile().equals(base.getAbsoluteFile()))throw new IOException("Unsafe asset storage path");
            File receipt=new File(base,"accepted/"+hash+".json");
            JSONObject files=descriptor.getJSONObject("files"),volumes=descriptor.getJSONObject("volumes");
            List<String> missing=new ArrayList<>();
            for(Iterator<String> names=volumes.keys();names.hasNext();) {
                String name=names.next();JSONArray members=volumes.getJSONArray(name);
                for(int i=0;i<members.length();i++) {
                    JSONObject pin=files.getJSONObject(members.getString(i));String digest=pin.getString("sha256");
                    if(!digest.matches("[0-9a-f]{64}"))throw new IOException("Invalid asset identity");
                    File object=new File(base,"objects/"+digest);
                    if(!object.getCanonicalFile().equals(object.getAbsoluteFile())||!Files.isRegularFile(object.toPath(),LinkOption.NOFOLLOW_LINKS)||object.length()!=pin.getLong("bytes")){missing.add(name);break;}
                }
            }
            boolean accepted=false;
            if(missing.isEmpty()&&receipt.getCanonicalFile().equals(receipt.getAbsoluteFile())&&Files.isRegularFile(receipt.toPath(),LinkOption.NOFOLLOW_LINKS)&&receipt.length()==raw.length)
                try(InputStream in=Files.newInputStream(receipt.toPath(),LinkOption.NOFOLLOW_LINKS)){accepted=Arrays.equals(raw,bounded(in,1024*1024));}
            return "Assets "+version+(accepted?" · verified; reusable with this APK":missing.isEmpty()?" · import a compatible part to finish verification":" · import "+String.join(", ",missing)+" part(s)");
        } catch(FileNotFoundException absent){return "Assets are bundled in this APK";}
        catch(Exception failure){return "Asset pack status unavailable: "+failure.getMessage();}
    }
    private static byte[] bounded(InputStream in,int limit)throws IOException {
        ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int n;
        while((n=in.read(buffer))!=-1){if(out.size()+n>limit)throw new IOException("Asset metadata exceeds its bound");out.write(buffer,0,n);}return out.toByteArray();
    }
    private static String hex(byte[] bytes){StringBuilder out=new StringBuilder();for(byte b:bytes){out.append(Character.forDigit((b>>>4)&15,16));out.append(Character.forDigit(b&15,16));}return out.toString();}
}
