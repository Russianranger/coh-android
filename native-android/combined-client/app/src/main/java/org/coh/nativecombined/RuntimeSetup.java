package org.coh.nativecombined;

import android.app.ActivityManager;
import android.content.Context;
import android.os.Build;
import android.os.SystemClock;
import io.github.russianranger.cohdiagnostic.AssetPackStore;
import org.json.JSONObject;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.channels.*;
import java.nio.file.*;
import java.util.*;

/** Installs only a verified disposable runtime. Existing launcher storage is never opened. */
public final class RuntimeSetup {
    private final Context context;
    private final ImportStore imports;
    private final ImportContract contract;
    private final File home,generation;
    private final String identity;
    public RuntimeSetup(Context context,ImportStore imports)throws Exception {
        this.context=context.getApplicationContext();this.imports=imports;contract=imports.contract();
        home=new File(this.context.getFilesDir().getCanonicalFile(),"combined-runtime");ImportStore.directory(home.toPath());
        identity=ImportContract.hex(ImportContract.hash().digest((contract.digest+ImportContract.hex(ImportContract.hash().digest(contract.runtimeManifestBytes))).getBytes(StandardCharsets.US_ASCII)));
        generation=new File(home,"runtime-"+identity.substring(0,16));
    }
    public File generationDirectory(){return generation;}
    public boolean ready()throws IOException {
        File receipt=new File(generation,"ready.sha256");
        return ImportStore.regular(receipt.toPath(),65)&&new String(Files.readAllBytes(receipt.toPath()),StandardCharsets.US_ASCII).equals(identity+"\n");
    }
    /** Run off the UI thread; setup never starts PostgreSQL, Wine or a game process. */
    public File setup(ImportContract.Control control,ImportContract.Progress listener)throws Exception {
        final ImportContract.Progress progress=listener==null?(phase,done,total)->{}:listener;
        if(!Arrays.asList(Build.SUPPORTED_ABIS).contains("arm64-v8a"))throw new IOException("The server runtime requires an ARM64 Android device");
        AssetPackStore pack=imports.assetStore(control);
        if(!pack.isAccepted()||imports.gameDataDirectory()==null)throw new IOException("Import all four verified asset pack parts before setup");
        if(!imports.donorReady())throw new IOException("Import the pinned "+contract.donorName+" before setup");
        try(FileChannel channel=FileChannel.open(new File(home,"setup.lock").toPath(),StandardOpenOption.CREATE,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS);FileLock lock=ImportStore.lock(channel)) {
            control.check();
            if(ready()){verifyInstalled(control,progress);progress.update("Verified runtime ready",1,1);return generation;}
            if(home.getUsableSpace()<5L*1024*1024*1024)throw new IOException("Keep at least 5 GiB of internal storage free for safe runtime setup");
            File base=archive("base",control,progress),wine=archive("wine",control,progress);
            Path staging=new File(home,".setup-"+UUID.randomUUID()).toPath();Files.createDirectory(staging);
            RuntimeMemoryGuard guard=memoryGuard(control,progress);guard.admit();
            boolean published=false;
            try {
                File stage=staging.toFile(),root=new File(stage,"rootfs"),win=new File(stage,"wine"),pg=new File(stage,"pg"),assets=new File(stage,"assets");
                ImportStore.directory(assets.toPath());
                progress.update("Unpacking Linux environment",0,0);RuntimeTarExtractor.extract(base,root,n->progress.update("Unpacking Linux environment",n,0),guard);
                progress.update("Unpacking Windows environment",0,0);RuntimeTarExtractor.extract(wine,win,n->progress.update("Unpacking Windows environment",n,0),guard);
                JSONObject files=contract.runtimeManifest.getJSONObject("files");
                for(Iterator<String> names=files.keys();names.hasNext();) {
                    control.check();String name=names.next();ImportContract.safeLeaf(name);ImportContract.Pin pin=ImportContract.pin(files.getJSONObject(name));
                    File target=new File(assets,name);String bundled="runtime/"+name;
                    if(contract.bundledFiles.containsKey(bundled)) {
                        ImportContract.Pin expected=contract.bundledFiles.get(bundled);same(pin,expected);
                        try(InputStream in=context.getAssets().open(bundled)){ImportStore.copy(in,target.toPath(),pin,control,progress,"Copying small launcher helpers");}
                    } else {
                        File source;
                        if(pack.contains("runtime/"+name))source=pack.resolve("runtime/"+name);
                        else {
                            ImportContract.Pin donor=contract.donorFiles.get("assets/runtime/"+name);
                            if(donor==null)throw new IOException("Runtime member is absent from every pinned input");same(pin,donor);
                            source=new File(imports.runtimePayloadDirectory(),name);
                        }
                        ImportStore.verify(source.toPath(),pin,control,progress);
                        // Immutable app-private payloads share bytes across setup generations.
                        Files.createLink(target.toPath(),source.toPath());
                    }
                    progress.update("Verified runtime payload: "+name,pin.bytes,pin.bytes);
                }
                ImportStore.write(new File(assets,"runtime-manifest.json").toPath(),contract.runtimeManifestBytes);
                RuntimeTarExtractor.extract(new File(assets,"postgresql-runtime.tar.gz"),pg,n->progress.update("Unpacking PostgreSQL",n,0),guard);
                if(files.has("dbserver-package.tar.gz"))RuntimeTarExtractor.extract(new File(assets,"dbserver-package.tar.gz"),new File(stage,"dbserver"),n->progress.update("Unpacking DbServer",n,0),guard);
                if(files.has("dbserver-schema.tar.gz"))RuntimeTarExtractor.extract(new File(assets,"dbserver-schema.tar.gz"),new File(stage,"schema"),n->progress.update("Unpacking schema",n,0),guard);
                required(root,"usr/bin/python3");required(win,"bin/wine");required(win,"bin/wineserver");required(pg,"opt/coh/pgsql/bin/postgres");required(pg,"opt/coh/pgsql/bin/initdb");
                ImportContract.Pin wineManifest=new ImportContract.Pin(new File(win,"lsb-fex.json").length(),contract.runtimeLock.getJSONObject("wine").getString("manifest_sha256"));
                ImportStore.verify(new File(win,"lsb-fex.json").toPath(),wineManifest,control,progress);
                ImportStore.write(new File(stage,"passwd").toPath(),"root:x:0:0:root:/root:/bin/sh\ncoh:x:1000:1000:COH:/state:/bin/sh\nnobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n".getBytes(StandardCharsets.US_ASCII));
                ImportStore.write(new File(stage,"group").toPath(),"root:x:0:\ncoh:x:1000:\nnogroup:x:65534:\n".getBytes(StandardCharsets.US_ASCII));
                for(String name:new String[]{"opt/coh","opt/coh/pgsql","opt/wine","opt/combined","state","tmp","game","imports"})new File(root,name).mkdirs();
                control.check();guard.finishWrites();ImportStore.write(new File(stage,"ready.sha256").toPath(),(identity+"\n").getBytes(StandardCharsets.US_ASCII));
                if(Files.exists(generation.toPath(),LinkOption.NOFOLLOW_LINKS))throw new IOException("An incomplete runtime generation exists; export diagnostics before retrying");
                control.publish(()->Files.move(staging,generation.toPath(),StandardCopyOption.ATOMIC_MOVE));published=true;
                progress.update("Runtime ready; start the server manually",1,1);return generation;
            } finally {
                // Never follow extracted guest symlinks during cancellation cleanup.
                if(!published)try{RuntimeTarExtractor.remove(staging.toFile());}catch(IOException ignored){/* Unpublished setup remains unselectable and may be removed on explicit retry. */}
            }
        }
    }
    private RuntimeMemoryGuard memoryGuard(ImportContract.Control control,ImportContract.Progress progress) {
        ActivityManager manager=(ActivityManager)context.getSystemService(Context.ACTIVITY_SERVICE);ActivityManager.MemoryInfo memory=new ActivityManager.MemoryInfo();Runtime vm=Runtime.getRuntime();
        return new RuntimeMemoryGuard(()->{if(manager==null)throw new IOException("Android memory service is unavailable");manager.getMemoryInfo(memory);return new RuntimeMemoryGuard.Sample(memory.availMem,memory.totalMem,memory.threshold,memory.lowMemory,vm.totalMemory()-vm.freeMemory(),vm.maxMemory());},SystemClock::uptimeMillis,Thread::sleep,control::check,paused->{if(paused)progress.update("Waiting for memory; previous imports are preserved",0,0);});
    }
    private File archive(String kind,ImportContract.Control control,ImportContract.Progress progress)throws Exception {
        File existing=imports.runtimeArchive(kind);ImportContract.Pin pin=ImportContract.pin(contract.runtimeLock.getJSONObject(kind));
        if(existing!=null){ImportStore.verify(existing.toPath(),pin,control,progress);return existing;}
        JSONObject record=contract.runtimeLock.getJSONObject(kind);URL url=new URL(record.getString("url"));
        for(int redirects=0;redirects<6;redirects++) {
            control.check();if(!url.getProtocol().equals("https"))throw new IOException("Runtime download requires HTTPS");
            HttpURLConnection connection=(HttpURLConnection)url.openConnection();connection.setConnectTimeout(15000);connection.setReadTimeout(15000);connection.setInstanceFollowRedirects(false);connection.setRequestProperty("User-Agent","COH-Native-Combined/0.1");
            try {
                int status=connection.getResponseCode();
                if(status>=300&&status<400){String location=connection.getHeaderField("Location");if(location==null)throw new IOException("Runtime download redirect is missing");url=new URL(url,location);continue;}
                if(status!=200)throw new IOException("Runtime download returned HTTP "+status);
                progress.update("Downloading pinned "+kind+" runtime",0,pin.bytes);
                return imports.importObject("runtime-"+kind,connection.getInputStream(),pin,control);
            } finally {connection.disconnect();}
        }
        throw new IOException("Too many runtime download redirects");
    }
    private void verifyInstalled(ImportContract.Control control,ImportContract.Progress progress)throws Exception {
        required(generation,"rootfs/usr/bin/python3");required(generation,"wine/bin/wine");required(generation,"wine/bin/wineserver");required(generation,"pg/opt/coh/pgsql/bin/postgres");required(generation,"pg/opt/coh/pgsql/bin/initdb");
        JSONObject files=contract.runtimeManifest.getJSONObject("files");
        for(Iterator<String> names=files.keys();names.hasNext();){String name=names.next();ImportContract.safeLeaf(name);ImportStore.verify(new File(generation,"assets/"+name).toPath(),ImportContract.pin(files.getJSONObject(name)),control,progress);}
    }
    private static void required(File root,String name)throws IOException {if(!new File(root,name).isFile())throw new IOException("Runtime is incomplete: "+name);}
    private static void same(ImportContract.Pin a,ImportContract.Pin b)throws IOException {if(a.bytes!=b.bytes||!a.sha256.equals(b.sha256))throw new IOException("Pinned runtime inventories disagree");}
}
