package io.github.russianranger.cohdiagnostic;

import android.content.Context;
import android.app.ActivityManager;
import android.os.Build;
import android.os.SystemClock;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/** Owns only this diagnostic app's downloads, runtime generation and child process. */
public final class DiagnosticRuntime {
    public interface Listener {
        void onStage(String stage, String detail);
        void onLog(String line);
    }
    public static final class Result {
        public final boolean passed;
        public final File report;
        public final String summary;
        Result(boolean passed, File report, String summary) { this.passed=passed; this.report=report; this.summary=summary; }
    }
    private static final long MAX_REPORT=2L*1024*1024, MAX_LOG=1024*1024;
    private final Context context;
    private final Listener listener;
    private final File home;
    private final DiagnosticReports reports;
    private final DiagnosticOutcome outcome;
    private volatile File state;
    private final StringBuilder log=new StringBuilder();
    private volatile boolean cancelled;
    private volatile Process child;
    private volatile HttpURLConnection connection;
    private JSONObject manifest;
    private String manifestHash;
    private File generation;
    private boolean clientProbeRequested;
    private boolean dbServerRequested;
    private String operationMode="setup";
    private JSONObject hostsEvidence;
    private JSONObject setupReceipt;
    private SetupMemoryGuard setupControl;
    private boolean setupCleanupDeferred;
    private String setupPhase="Checking runtime",setupDetail="Checking the installed runtime and available memory";

    public DiagnosticRuntime(Context context, Listener listener) {
        this(context,listener,new DiagnosticOutcome());
    }
    DiagnosticRuntime(Context context, Listener listener, DiagnosticOutcome outcome) {
        this.context=context.getApplicationContext(); this.listener=listener;
        this.outcome=outcome;
        File files;
        try {files=this.context.getFilesDir().getCanonicalFile();} catch(IOException e){throw new IllegalStateException("Cannot resolve app storage",e);}
        home=new File(files,"m2"); state=new File(home,"state");
        reports=new DiagnosticReports(home);
    }
    public File getLatestReport() { return reports.target; }
    /** Compact setup evidence; never inventories, prunes or launches the runtime. */
    public JSONObject getSetupReceipt() throws Exception {
        return setupReceipt==null?null:new JSONObject(setupReceipt.toString());
    }
    private String appVersion() {
        try{return context.getPackageManager().getPackageInfo(context.getPackageName(),0).versionName;}
        catch(Exception ignored){return "unknown";}
    }
    private void check() throws InterruptedIOException {
        if(cancelled||outcome.cancelled()||Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Diagnostic stopped");
    }
    public void requestStop() {
        if(!outcome.requestStop())return;
        cancelled=true;
        signalStop();
    }
    private void signalStop() {
        try { state.mkdirs(); write(new File(state,"stop-request"),"stop\n".getBytes(StandardCharsets.UTF_8)); } catch(Exception ignored) {}
        HttpURLConnection c=connection; if(c!=null)c.disconnect();
    }
    private static String clean(String line) {
        return line.replaceAll("(?i)(password|pwd|token|secret)(\\s*[=:]\\s*)([^;\\s]+)","$1$2[redacted]");
    }
    private synchronized void line(String text) {
        text=clean(text); if(text.length()>2048)text=text.substring(0,2048)+"…";
        log.append(text).append('\n');
        if(log.length()>MAX_LOG)log.delete(0, log.length()-(int)MAX_LOG);
        listener.onLog(text);
    }
    private void stage(String name,String detail) {
        if(setupControl!=null){setupPhase=name;setupDetail=detail;}
        listener.onStage(name,detail); line(name+": "+detail);
    }
    private void setupProgress(String name,String detail) {
        setupPhase=name;setupDetail=detail;listener.onStage(name,detail);
    }
    private SetupMemoryGuard setupMemoryControl() {
        ActivityManager manager=(ActivityManager)context.getSystemService(Context.ACTIVITY_SERVICE);
        ActivityManager.MemoryInfo memory=new ActivityManager.MemoryInfo();
        Runtime vm=Runtime.getRuntime();
        return new SetupMemoryGuard(()->{
            if(manager==null)throw new IOException("Android memory service is unavailable");
            manager.getMemoryInfo(memory);
            return new SetupMemoryGuard.Sample(memory.availMem,memory.totalMem,memory.threshold,memory.lowMemory,
                    vm.totalMemory()-vm.freeMemory(),vm.maxMemory());
        },SystemClock::uptimeMillis,Thread::sleep,this::check,paused->{
            if(paused)listener.onStage("Waiting for memory","Runtime setup is paused while Android memory is low. Stop remains available; the previous runtime and saved profile are preserved.");
            else listener.onStage(setupPhase,setupDetail);
        });
    }
    private static byte[] read(File file,long limit) throws IOException {
        try(InputStream in=new FileInputStream(file)){return read(in,limit);}
    }
    private static byte[] read(InputStream in,long limit) throws IOException {
        ByteArrayOutputStream out=new ByteArrayOutputStream(); byte[] buffer=new byte[8192]; int n;
        while((n=in.read(buffer))!=-1){if(out.size()+n>limit)throw new IOException("Report exceeds size limit");out.write(buffer,0,n);}
        return out.toByteArray();
    }
    private static void write(File file,byte[] bytes) throws IOException {
        file.getParentFile().mkdirs(); File part=new File(file.getParentFile(),file.getName()+".part");
        try(FileOutputStream out=new FileOutputStream(part)){out.write(bytes);out.getFD().sync();}
        Files.move(part.toPath(),file.toPath(),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
    }
    private static String hex(byte[] bytes) {StringBuilder b=new StringBuilder();for(byte v:bytes)b.append(String.format(Locale.ROOT,"%02x",v&255));return b.toString();}
    private String sha(File file) throws Exception {
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        try(InputStream in=new FileInputStream(file)) {
            byte[] buffer=new byte[65536];int n;
            while(true) {
                check();if(setupControl!=null)setupControl.beforeIo();n=in.read(buffer);if(n<0)break;
                if(setupControl!=null)setupControl.read(n);digest.update(buffer,0,n);
            }
        }
        return hex(digest.digest());
    }
    private void loadManifest() throws Exception {
        home.mkdirs(); state.mkdirs();
        byte[] bytes;
        try(InputStream in=context.getAssets().open("runtime/runtime-manifest.json")){bytes=read(in,MAX_REPORT);}
        manifestHash=hex(MessageDigest.getInstance("SHA-256").digest(bytes));
        manifest=new JSONObject(new String(bytes,StandardCharsets.UTF_8));
        if(manifest.getInt("format")!=1)throw new IOException("Unsupported diagnostic package");
        generation=new File(home,"runtime-"+manifestHash.substring(0,16));
    }
    private void verify(File file,JSONObject pin) throws Exception {
        if(!file.isFile()||file.length()!=pin.getLong("bytes")||!sha(file).equals(pin.getString("sha256")))
            throw new IOException("Runtime integrity check failed: "+file.getName());
    }
    private File download(JSONObject pin,String name) throws Exception {
        File cache=new File(home,"downloads");cache.mkdirs(); File dest=new File(cache,name+"-"+pin.getString("sha256")+".tar.gz");
        if(dest.isFile()){verify(dest,pin);return dest;}
        File part=new File(cache,dest.getName()+".part");
        URL url=new URL(pin.getString("url")); long expected=pin.getLong("bytes");
        if(expected<1||expected>1024L*1024*1024)throw new IOException("Invalid runtime size");
        try {
            for(int redirect=0;redirect<6;redirect++) {
                check(); if(!url.getProtocol().equals("https"))throw new IOException("Runtime requires HTTPS");
                HttpURLConnection c=(HttpURLConnection)url.openConnection();connection=c;
                c.setConnectTimeout(15000);c.setReadTimeout(15000);c.setInstanceFollowRedirects(false);
                c.setRequestProperty("User-Agent","COH-Diagnostic/"+appVersion());
                int code=c.getResponseCode();
                if(code>=300&&code<400){String location=c.getHeaderField("Location");c.disconnect();if(location==null)throw new IOException("Missing download redirect");url=new URL(url,location);continue;}
                if(code!=200)throw new IOException("Runtime download failed (HTTP "+code+")");
                long total=0,last=0;
                if(setupReceipt!=null)setupReceipt.put("download_started",true);
                try(InputStream in=c.getInputStream();FileOutputStream out=new FileOutputStream(part)) {
                    byte[] buffer=new byte[65536];int n;
                    try {
                        while(true){check();if(setupControl!=null)setupControl.beforeIo();n=in.read(buffer);if(n<0)break;
                            if(setupControl!=null)setupControl.read(n);total+=n;if(total>expected)throw new IOException("Runtime download too large");out.write(buffer,0,n);
                            if(setupControl!=null)setupControl.written(n,()->out.getFD().sync());
                            if(total-last>=4*1024*1024){setupProgress("Downloading "+name,total/1048576+" / "+expected/1048576+" MiB");last=total;}}
                    } finally {if(setupControl!=null){out.getFD().sync();setupControl.synced();}}
                } finally {c.disconnect();connection=null;}
                verify(part,pin);Files.move(part.toPath(),dest.toPath(),StandardCopyOption.REPLACE_EXISTING);
                if(setupReceipt!=null)setupReceipt.put("downloaded_archive_bytes",Math.addExact(setupReceipt.getLong("downloaded_archive_bytes"),total));
                return dest;
            }
            throw new IOException("Too many runtime redirects");
        } finally {if(part.exists())part.delete();HttpURLConnection c=connection;if(c!=null)c.disconnect();connection=null;}
    }
    private static void required(File root,String name) throws IOException {
        if(!new File(root,name).isFile())throw new IOException("Incomplete runtime: "+name);
    }
    public void setupRuntime() throws Exception {
        CleanupGuard.requireClear();
        JSONObject report=new JSONObject();
        long usableBefore=home.getParentFile().getUsableSpace();
        setupReceipt=new JSONObject().put("format",1).put("mode","checking").put("reused",false)
                .put("installation_started",false).put("runtime_activated",false)
                .put("download_started",false).put("downloaded_archive_bytes",0L)
                .put("extraction_started",false).put("archives_extracted",0)
                .put("runtime_payload_files_copied",0).put("runtime_contents_inventory_performed",false)
                .put("automatic_cleanup_performed",false).put("staging_cleanup_deferred",false);
        setupCleanupDeferred=false;
        try {
            loadManifest();check();
            setupControl=setupMemoryControl();setupControl.admit();
            long assetBytes=0;
            JSONObject pinnedFiles=manifest.getJSONObject("files");
            for(Iterator<String> names=pinnedFiles.keys();names.hasNext();)assetBytes=Math.addExact(assetBytes,pinnedFiles.getJSONObject(names.next()).getLong("bytes"));
            setupReceipt.put("generation",generation.getName()).put("runtime_manifest_sha256",manifestHash)
                    .put("packaged_runtime_asset_logical_bytes",assetBytes);
            if(!Arrays.asList(Build.SUPPORTED_ABIS).contains("arm64-v8a"))throw new IOException("This diagnostic requires an ARM64 device");
            File ready=new File(generation,"ready.json");
            if(ready.isFile()&&new JSONObject(new String(read(ready,16384),StandardCharsets.UTF_8)).getString("manifest_sha256").equals(manifestHash)) {
                stage("Verifying installed runtime","Checking pinned runtime assets without adding runtime files");
                validateInstalled();setupReceipt.put("mode","reused").put("reused",true);
            } else {
                if(home.getUsableSpace()<5L*1024*1024*1024)throw new IOException("Keep at least 5 GiB free for runtime setup");
                JSONObject lock;
                try(InputStream in=context.getAssets().open("runtime/runtime-lock.json")){lock=new JSONObject(new String(read(in,65536),StandardCharsets.UTF_8));}
                stage("Checking runtime archives","Checking or downloading the pinned database and Windows runtime archives");
                File base=download(lock.getJSONObject("base"),"database environment");
                File wine=download(lock.getJSONObject("wine"),"Windows runtime");
                File staging=new File(home,generation.getName()+".staging");
                setupReceipt.put("installation_started",true);
                if(staging.exists())TarExtractor.remove(staging,setupControl);staging.mkdirs();
                try {
                    File root=new File(staging,"rootfs"), win=new File(staging,"wine"), pg=new File(staging,"pg"), assets=new File(staging,"assets");
                    root.mkdirs();win.mkdirs();pg.mkdirs();assets.mkdirs();
                    stage("Unpacking runtime","Preparing the private database environment");
                    setupReceipt.put("extraction_started",true);
                    TarExtractor.extract(base,root,n->setupProgress("Unpacking environment",n+" files"),setupControl);
                    setupReceipt.put("archives_extracted",1);check();
                    stage("Unpacking Windows runtime","Preparing the pinned Windows environment");
                    TarExtractor.extract(wine,win,n->setupProgress("Unpacking Windows runtime",n+" files"),setupControl);
                    setupReceipt.put("archives_extracted",2);check();
                    JSONObject files=manifest.getJSONObject("files");
                    stage("Copying runtime assets","Copying and verifying the packaged runtime assets");
                    long copied=0;
                    for(Iterator<String> it=files.keys();it.hasNext();) {
                        String name=it.next(); if(!name.matches("[A-Za-z0-9_.-]+"))throw new IOException("Unsafe package member");
                        File dest=new File(assets,name);
                        setupControl.beforeIo();
                        try(InputStream in=context.getAssets().open("runtime/"+name);FileOutputStream out=new FileOutputStream(dest)) {
                            TarExtractor.transfer(in,out,files.getJSONObject(name).getLong("bytes"),setupControl);if(in.read()!=-1)throw new IOException("Package member grew");
                        }
                        stage("Verifying runtime asset",name);
                        verify(dest,files.getJSONObject(name));check();
                        setupReceipt.put("runtime_payload_files_copied",setupReceipt.getInt("runtime_payload_files_copied")+1);
                        copied=Math.addExact(copied,files.getJSONObject(name).getLong("bytes"));
                        stage("Copying runtime assets",copied/1048576+" / "+assetBytes/1048576+" MiB verified");
                    }
                    try(InputStream in=context.getAssets().open("runtime/runtime-manifest.json")){write(new File(assets,"runtime-manifest.json"),read(in,MAX_REPORT));}
                    stage("Unpacking PostgreSQL","Preparing the pinned PostgreSQL environment");
                    TarExtractor.extract(new File(assets,"postgresql-runtime.tar.gz"),pg,n->setupProgress("Unpacking PostgreSQL",n+" files"),setupControl);
                    setupReceipt.put("archives_extracted",3);
                    if(files.has("dbserver-package.tar.gz")&&files.has("dbserver-schema.tar.gz")) {
                        stage("Unpacking real DbServer","Preparing the isolated server test inputs");
                        TarExtractor.extract(new File(assets,"dbserver-package.tar.gz"),new File(staging,"dbserver"),n->setupProgress("Unpacking DbServer",n+" files"),setupControl);
                        setupReceipt.put("archives_extracted",4);
                        stage("Unpacking server schema","Preparing the pinned server schema");
                        TarExtractor.extract(new File(assets,"dbserver-schema.tar.gz"),new File(staging,"schema"),n->setupProgress("Unpacking server schema",n+" files"),setupControl);
                        setupReceipt.put("archives_extracted",5);
                    }
                    required(root,"usr/bin/python3");required(root,"usr/bin/Xtigervnc");required(win,"bin/wine");required(win,"bin/wineserver");
                    required(pg,"opt/coh/pgsql/bin/postgres");required(pg,"opt/coh/pgsql/bin/initdb");
                    if(!sha(new File(win,"lsb-fex.json")).equals(lock.getJSONObject("wine").getString("manifest_sha256")))throw new IOException("Windows runtime manifest mismatch");
                    write(new File(staging,"passwd"),"root:x:0:0:root:/root:/bin/sh\ncoh:x:1000:1000:COH:/state:/bin/sh\nnobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n".getBytes(StandardCharsets.UTF_8));
                    write(new File(staging,"group"),"root:x:0:\ncoh:x:1000:\nnogroup:x:65534:\n".getBytes(StandardCharsets.UTF_8));
                    for(String dir:new String[]{"opt/coh","opt/coh/pgsql","opt/coh-dbserver","opt/coh-schema","opt/wine","state","tmp"})new File(root,dir).mkdirs();
                    stage("Activating runtime","Finishing the verified runtime generation");
                    setupControl.checkpoint();
                    write(new File(staging,"ready.json"),new JSONObject().put("manifest_sha256",manifestHash).toString().getBytes(StandardCharsets.UTF_8));
                    check();setupControl.checkpoint();if(generation.exists())TarExtractor.remove(generation,setupControl);
                    if(!staging.renameTo(generation))throw new IOException("Cannot activate runtime");
                    setupReceipt.put("runtime_activated",true);
                } catch(OutOfMemoryError failure) {setupCleanupDeferred=true;throw failure;}
                finally {
                    if(staging.exists()) {
                        if(setupCleanupDeferred||setupControl.cleanupShouldDefer()||outcome.cancelled()||Thread.currentThread().isInterrupted()) {
                            setupCleanupDeferred=true;
                            // A deferred private staging tree never carries a
                            // success marker, including a Stop at publication.
                            Files.deleteIfExists(new File(staging,"ready.json").toPath());
                        }
                        else TarExtractor.remove(staging);
                    }
                }
                stage("Verifying installed runtime","Checking the activated runtime assets");
                validateInstalled();setupReceipt.put("mode","installed");
            }
            setupControl.finishWrites();
            stage("Runtime ready",setupReceipt.optBoolean("reused")?"The pinned runtime is already installed; no runtime files were added":"Setup complete. Run diagnostics next.");
            report.put("status","setup_complete").put("passed",false).put("scope","Runtime installation only; run the diagnostic before claiming execution");
        } catch(Exception e) {setupReceipt.put("mode",outcome.cancelled()?"cancelled":"failed");report.put("status",outcome.cancelled()?"cancelled":"failed").put("error",clean(String.valueOf(e.getMessage())));throw e;}
        finally {
            if(generation!=null&&new File(home,generation.getName()+".staging").exists()
                    &&(setupCleanupDeferred||outcome.cancelled()||Thread.currentThread().isInterrupted()
                    ||setupControl!=null&&setupControl.cleanupShouldDefer()))setupCleanupDeferred=true;
            setupReceipt.put("staging_cleanup_deferred",setupCleanupDeferred);
            if(setupControl!=null)setupReceipt.put("setup_memory_control",new JSONObject(setupControl.receipt()));
            setupControl=null;
            int generations=0,entries=0;boolean complete=true;
            try(java.nio.file.DirectoryStream<java.nio.file.Path> names=Files.newDirectoryStream(home.toPath())) {
                for(java.nio.file.Path name:names) {
                    if(++entries>512){complete=false;break;}
                    if(name.getFileName().toString().matches("runtime-[0-9a-f]{16}")
                            &&Files.isDirectory(name,java.nio.file.LinkOption.NOFOLLOW_LINKS))generations++;
                }
            } catch(IOException|SecurityException ignored){complete=false;}
            long usableAfter=home.getParentFile().getUsableSpace();
            setupReceipt.put("storage_observation",new JSONObject()
                    .put("scope","shared_filesystem_available_space_only; not app allocated usage")
                    .put("shared_filesystem_usable_bytes_before",usableBefore)
                    .put("shared_filesystem_usable_bytes_after",usableAfter)
                    .put("shared_filesystem_usable_bytes_change",usableAfter-usableBefore)
                    .put("runtime_generation_directories",generations).put("generation_count_complete",complete)
                    .put("directory_entry_limit",512));
            report.put("runtime_setup",setupReceipt);support(report,false);
        }
    }
    private void validateInstalled() throws Exception {
        required(generation,"rootfs/usr/bin/python3");required(generation,"wine/bin/wine");required(generation,"pg/opt/coh/pgsql/bin/postgres");
        JSONObject files=manifest.getJSONObject("files");
        for(Iterator<String> it=files.keys();it.hasNext();){String name=it.next();verify(new File(generation,"assets/"+name),files.getJSONObject(name));}
    }
    public Result runDiagnostics() throws Exception {
        return runDiagnostics(false,false);
    }
    public Result runClientProbe() throws Exception {
        return runDiagnostics(true,false);
    }
    public Result runDbServerProbe() throws Exception {
        return runDiagnostics(false,true);
    }
    private Result runDiagnostics(boolean clientProbe,boolean dbServer) throws Exception {
        CleanupGuard.requireClear();
        clientProbeRequested=clientProbe;
        dbServerRequested=dbServer;
        operationMode=dbServer?"dbserver":clientProbe?"database_and_client":"database";
        File runRoot=dbServer?new File(home,"dbserver-runs/"+reports.runId):home;
        if(dbServer)state=new File(runRoot,"state");
        JSONObject report=new JSONObject();boolean passed=false;
        String successSummary=null;
        Thread reader=null;
        try {
            loadManifest();check();
            if(!new File(generation,"ready.json").isFile())throw new IOException("Set up the runtime first");
            validateInstalled();
            JSONObject listenerContract=null;
            File guestHosts=null;
            if(dbServer) {
                required(generation,"assets/dbserver_diagnostic.py");
                required(generation,"dbserver/package-manifest.json");
                required(generation,"schema/schema-manifest.json");
                if(home.getUsableSpace()<2L*1024*1024*1024)throw new IOException("Keep at least 2 GiB free for the real DbServer test");
                listenerContract=new JSONObject(new String(read(new File(generation,"dbserver/package-manifest.json"),MAX_REPORT),StandardCharsets.UTF_8))
                    .getJSONObject("wine_build_input").getJSONObject("normal_schema_listeners");
                String hostname=android.system.Os.uname().nodename;
                byte[] contents=DeviceHosts.contents(hostname).getBytes(StandardCharsets.US_ASCII);
                guestHosts=new File(runRoot,"hosts");write(guestHosts,contents);
                hostsEvidence=new JSONObject().put("kernel_hostname",hostname).put("guest_hosts_sha256",hex(MessageDigest.getInstance("SHA-256").digest(contents)))
                    .put("contents",new String(contents,StandardCharsets.US_ASCII));
            }
            File stop=new File(state,"stop-request");if(stop.exists()&&!stop.delete())throw new IOException("Cannot clear previous stop request");
            File old=new File(state,"latest-report.json");if(old.exists()&&!old.delete())throw new IOException("Cannot clear previous report");
            File tmp=new File(runRoot,"tmp");tmp.mkdirs();
            // PRoot also needs a short native path when it translates AF_UNIX
            // sockets. Keep this separate from the fresh guest /tmp binding.
            File prootTmp=new File(home.getParentFile(),"p");prootTmp.mkdirs();
            prootTmp=prootTmp.getCanonicalFile();
            if(prootTmp.getPath().getBytes(StandardCharsets.UTF_8).length+27>107)
                throw new IOException("App storage path is too long for the process runtime's local sockets");
            String nativeDir=context.getApplicationInfo().nativeLibraryDir;
            File proot=new File(nativeDir,"libproot.so"),loader=new File(nativeDir,"libproot-loader.so");
            if(!proot.canExecute()||!loader.canExecute())throw new IOException("The APK's ARM64 process runtime is missing");
            List<String> command=new ArrayList<>(Arrays.asList(proot.getPath(),"--link2symlink","--kill-on-exit","--sysvipc","-i","1000:1000","-r",new File(generation,"rootfs").getPath(),
                "-b","/dev","-b","/proc","-b","/sys","-b",state.getPath()+":/state","-b",tmp.getPath()+":/tmp",
                "-b",new File(generation,"assets").getPath()+":/opt/coh","-b",new File(generation,"pg/opt/coh/pgsql").getPath()+":/opt/coh/pgsql",
                "-b",new File(generation,"wine").getPath()+":/opt/wine","-b",new File(generation,"passwd").getPath()+":/etc/passwd","-b",new File(generation,"group").getPath()+":/etc/group"));
            if(dbServer)command.addAll(Arrays.asList("-b",new File(generation,"dbserver").getPath()+":/opt/coh-dbserver",
                "-b",new File(generation,"schema").getPath()+":/opt/coh-schema","-b",guestHosts.getPath()+":/etc/hosts"));
            command.addAll(Arrays.asList(
                "-w","/state","/usr/bin/env","-i","HOME=/state","USER=coh","LOGNAME=coh","PATH=/opt/coh/pgsql/bin:/usr/local/bin:/usr/bin:/bin","LANG=C.UTF-8","TZ=UTC","TMPDIR=/tmp","PYTHONUNBUFFERED=1",
                "/usr/bin/python3",dbServer?"/opt/coh/dbserver_diagnostic.py":"/opt/coh/diagnostic.py","--state","/state","--assets","/opt/coh","--pg-bin","/opt/coh/pgsql/bin","--wine","/opt/wine/bin/wine","--wineserver","/opt/wine/bin/wineserver","--execution-platform","android"));
            if(clientProbe)command.add("--client-probe");
            if(dbServer)command.addAll(Arrays.asList("--package","/opt/coh-dbserver","--schema","/opt/coh-schema","--listener-policy","device","--timeout-seconds","1800"));
            ProcessBuilder builder=new ProcessBuilder(command);builder.redirectErrorStream(true);
            builder.environment().put("PROOT_LOADER",loader.getPath());builder.environment().put("PROOT_TMP_DIR",prootTmp.getPath());builder.environment().put("PROOT_NO_SECCOMP","1");
            stage(dbServer?"Starting real DbServer test":clientProbe?"Starting client probe":"Starting diagnostics",dbServer
                ?"Real server persistence and schema checks; this may take up to 30 minutes"
                :clientProbe
                ?"Database, synthetic Windows graphics and input checks run in the private virtual display"
                :"Database and Windows checks run in this app's private environment");
            check();child=builder.start();final Process process=child;
            reader=new Thread(()->{
                try(BufferedReader in=new BufferedReader(new InputStreamReader(process.getInputStream(),StandardCharsets.UTF_8))) {
                    String text;while((text=in.readLine())!=null){
                        if(text.length()>8192)text=text.substring(0,8192);
                        try{JSONObject event=new JSONObject(text);if(event.optString("type").equals("stage"))listener.onStage(event.optString("stage","Checking"),clean(event.optString("message",event.optString("detail",""))));}catch(Exception ignored){}
                        line(text);
                    }
                } catch(Exception e){line("Output capture ended: "+e.getClass().getSimpleName());}
            },"coh-diagnostic-output");reader.start();
            long limitMinutes=dbServer?32:20;
            long deadline=System.nanoTime()+TimeUnit.MINUTES.toNanos(limitMinutes);
            while(!process.waitFor(200,TimeUnit.MILLISECONDS)) {
                check();if(System.nanoTime()>deadline)throw new IOException("Diagnostics exceeded the "+limitMinutes+" minute limit");
            }
            reader.join(2000);check();
            report=new JSONObject(new String(read(new File(state,"latest-report.json"),MAX_REPORT),StandardCharsets.UTF_8));
            JSONObject cleanup=report.optJSONObject("cleanup");
            JSONObject probe=report.optJSONObject("client_probe");
            boolean modeMatches=dbServer?DbServerAcceptance.accepts(jsonValue(report),jsonValue(listenerContract))
                :report.optString("diagnostic_mode").equals(clientProbe?"database_and_client":"database");
            boolean probePassed=!clientProbe||(probe!=null&&probe.optString("status").equals("passed")
                &&probe.optString("scope").equals("headless_wgl_client_capabilities")
                &&Boolean.FALSE.equals(probe.opt("game_rendering_validated"))
                &&Boolean.FALSE.equals(probe.opt("android_surface_validated"))
                &&Boolean.FALSE.equals(probe.opt("hardware_acceleration_validated")));
            passed=process.exitValue()==0&&report.optBoolean("passed",false)&&report.optJSONArray("failures")!=null&&report.getJSONArray("failures").length()==0
                &&modeMatches&&probePassed
                &&cleanup!=null&&cleanup.optBoolean("postgres_graceful")&&cleanup.optBoolean("wine_prefix_stopped")&&cleanup.optBoolean("owned_processes_reaped");
            if(!passed)throw new IOException("A diagnostic check failed. Export the report for review.");
            stage(dbServer?"Real DbServer test passed":clientProbe?"Client probe passed":"Diagnostics passed",dbServer
                ?"Real server persistence, schema reload and cleanup passed on this device"
                :clientProbe
                ?"Database and synthetic graphics/input checks passed in the virtual display"
                :"Database, restart, Win32 and shutdown checks passed on this device");
            successSummary=dbServer
                ?"Real DbServer checks passed on this Android device. Atlas Park gameplay and character saves on this device remain untested."
                :clientProbe
                ?"Client probe checks passed. Game rendering, hardware acceleration and controller input remain untested."
                :"Diagnostic checks passed. Game execution remains untested.";
        } catch(Exception e) {
            if(cancelled||outcome.cancelled()||e instanceof InterruptedException||Thread.currentThread().isInterrupted()){cancelled=true;outcome.requestStop();}
            report.put("passed",false).put("status",cancelled?"cancelled":"failed").put("app_error",clean(String.valueOf(e.getMessage())));throw e;
        } finally {
            boolean interrupted=Thread.interrupted();
            Process process=child;
            if(process!=null&&process.isAlive()) {
                signalStop();
                try {if(!process.waitFor(30,TimeUnit.SECONDS)){process.destroy();if(!process.waitFor(5,TimeUnit.SECONDS))process.destroyForcibly();}}catch(InterruptedException ignored){process.destroyForcibly();}
            }
            if(process!=null && process.isAlive()) {
                try {process.waitFor(5,TimeUnit.SECONDS);} catch(InterruptedException ignored) {}
                if(process.isAlive()) {
                    final JSONObject failedReport=report;
                    throw CleanupGuard.block(()->{
                        failedReport.put("passed",false).put("status","cleanup_failed");
                        support(failedReport,false);
                    });
                }
            }
            if(reader!=null)try{reader.join(2000);}catch(InterruptedException ignored){}
            child=null;
            if(!passed&&process!=null)try{File guest=new File(state,"latest-report.json");if(guest.isFile())report.put("guest_report",new JSONObject(new String(read(guest,MAX_REPORT),StandardCharsets.UTF_8)));}catch(Exception ignored){}
            support(report,passed);if(interrupted)Thread.currentThread().interrupt();
        }
        if(outcome.cancelled())throw new InterruptedIOException("Diagnostic stopped");
        return new Result(passed,getLatestReport(),successSummary);
    }
    private static Object jsonValue(Object value) throws Exception {
        if(value instanceof JSONObject){JSONObject src=(JSONObject)value;Map<String,Object> out=new HashMap<>();for(Iterator<String> it=src.keys();it.hasNext();){String key=it.next();out.put(key,jsonValue(src.get(key)));}return out;}
        if(value instanceof JSONArray){JSONArray src=(JSONArray)value;List<Object> out=new ArrayList<>();for(int i=0;i<src.length();i++)out.add(jsonValue(src.get(i)));return out;}
        return value;
    }
    private static Object sanitized(Object value) throws Exception {
        if(value instanceof JSONObject){JSONObject src=(JSONObject)value,out=new JSONObject();for(Iterator<String> it=src.keys();it.hasNext();){String key=it.next();out.put(key,sanitized(src.get(key)));}return out;}
        if(value instanceof JSONArray){JSONArray src=(JSONArray)value,out=new JSONArray();for(int i=0;i<src.length();i++)out.put(sanitized(src.get(i)));return out;}
        return value instanceof String?clean((String)value):value;
    }
    private void support(JSONObject report,boolean passed) throws IOException {
        try {
            // Resolve the terminal outcome before report publication; later
            // Stop requests are ignored by the shared gate.
            boolean wasCancelled=outcome.finish();
            if(wasCancelled) {
                passed=false;
                report.put("passed",false);
                if(!report.optString("status").equals("cleanup_failed"))report.put("status","cancelled");
            }
            home.mkdirs();
            JSONObject wrapper=new JSONObject().put("format",1).put("recorded_utc",new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX",Locale.ROOT).format(new Date()))
                .put("app_id",context.getPackageName()).put("app_version",appVersion()).put("android_uid",android.os.Process.myUid()).put("android_sdk",Build.VERSION.SDK_INT)
                .put("device",Build.MANUFACTURER+" "+Build.MODEL).put("abis",new JSONArray(Arrays.asList(Build.SUPPORTED_ABIS))).put("runtime_manifest_sha256",manifestHash)
                .put("run_id",reports.runId).put("operation",operationMode)
                .put("android_diagnostic_passed",passed).put("client_probe_requested",clientProbeRequested)
                .put("real_dbserver_requested",dbServerRequested).put("real_dbserver_android_validated",dbServerRequested&&passed)
                .put("gameplay_validated",false).put("generated_character_persistence_validated",false).put("guest",report);
            if(hostsEvidence!=null)wrapper.put("guest_hosts",hostsEvidence);
            File part=reports.prepare();
            try(ZipOutputStream out=new ZipOutputStream(new FileOutputStream(part))) {
                out.putNextEntry(new ZipEntry("android-diagnostic-report.json"));out.write(((JSONObject)sanitized(wrapper)).toString(2).getBytes(StandardCharsets.UTF_8));out.closeEntry();
                out.putNextEntry(new ZipEntry("diagnostic.log"));synchronized(this){out.write(clean(log.toString()).getBytes(StandardCharsets.UTF_8));}out.closeEntry();
                if(manifest!=null){out.putNextEntry(new ZipEntry("runtime-manifest.json"));out.write(manifest.toString(2).getBytes(StandardCharsets.UTF_8));out.closeEntry();}
            }
            reports.publish();
        } catch(Exception e){reports.discardPartial();line("Could not write support report: "+e.getClass().getSimpleName());throw new IOException("Could not save a fresh diagnostic report",e);}
    }
}
