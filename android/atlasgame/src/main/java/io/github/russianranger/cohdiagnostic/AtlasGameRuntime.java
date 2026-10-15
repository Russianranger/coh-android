package io.github.russianranger.cohdiagnostic;

import android.content.Context;
import android.os.Build;
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
import java.util.zip.GZIPInputStream;

/** Installs pinned inputs and owns one bounded Android Atlas character persistence test. */
public final class AtlasGameRuntime {
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
    private final Control control;
    public static final class Control {
        private final DiagnosticOutcome outcome = new DiagnosticOutcome();
        private volatile boolean terminal;
        public boolean requestStop() { return outcome.requestStop(); }
        public boolean cancelled() { return outcome.cancelled(); }
        public boolean finished() { return terminal; }
        boolean finish() { boolean cancelled=outcome.finish(); terminal=true; return cancelled; }
    }
    private volatile File state;
    private final StringBuilder log=new StringBuilder();
    private volatile boolean cancelled;
    private volatile Process child;
    private volatile HttpURLConnection connection;
    private JSONObject manifest;
    private String manifestHash;
    private File generation;
    private String operationMode="setup";
    private File importedGeneration;
    private JSONObject importEvidence;
    private byte[] importContract;
    private String appError;
    private final JSONArray resources=new JSONArray();
    private final long started=System.currentTimeMillis();
    private JSONObject hostsEvidence;

    public AtlasGameRuntime(Context context, Listener listener) {
        this(context,listener,new Control());
    }
    public AtlasGameRuntime(Context context, Listener listener, Control control) {
        this.context=context.getApplicationContext(); this.listener=listener;
        this.control=control;
        File files;
        try {files=this.context.getFilesDir().getCanonicalFile();} catch(IOException e){throw new IllegalStateException("Cannot resolve app storage",e);}
        home=new File(files,"atlas-runtime"); state=new File(home,"state");
        reports=new DiagnosticReports(home);
    }
    public File getLatestReport() { return reports.target; }
    public static boolean cleanupBlocked() { return CleanupGuard.isBlocked(); }
    public static void markCleanupUncertain() { CleanupGuard.block(()->{}); }
    private String appVersion() {
        try{return context.getPackageManager().getPackageInfo(context.getPackageName(),0).versionName;}
        catch(Exception ignored){return "unknown";}
    }
    private void check() throws InterruptedIOException {
        if(cancelled||control.cancelled()||Thread.currentThread().isInterrupted()) throw new InterruptedIOException("Diagnostic stopped");
    }
    public boolean requestStop() {
        if(!control.requestStop())return false;
        cancelled=true; signalStop(); return true;
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
    private void stage(String name,String detail) { listener.onStage(name,detail); line(name+": "+detail); }
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
        try(InputStream in=new FileInputStream(file)){byte[] buffer=new byte[1024*1024];int n;while((n=in.read(buffer))!=-1){check();digest.update(buffer,0,n);}}
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
                c.setRequestProperty("User-Agent","COH-Atlas-Test/"+appVersion());
                int code=c.getResponseCode();
                if(code>=300&&code<400){String location=c.getHeaderField("Location");c.disconnect();if(location==null)throw new IOException("Missing download redirect");url=new URL(url,location);continue;}
                if(code!=200)throw new IOException("Runtime download failed (HTTP "+code+")");
                long total=0,last=0;
                try(InputStream in=c.getInputStream();OutputStream out=new FileOutputStream(part)) {
                    byte[] buffer=new byte[1024*1024];int n;
                    while((n=in.read(buffer))!=-1){check();total+=n;if(total>expected)throw new IOException("Runtime download too large");out.write(buffer,0,n);
                        if(total-last>=4*1024*1024){listener.onStage("Downloading "+name,total/1048576+" / "+expected/1048576+" MiB");last=total;}}
                } finally {c.disconnect();connection=null;}
                verify(part,pin);Files.move(part.toPath(),dest.toPath(),StandardCopyOption.REPLACE_EXISTING);return dest;
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
        try {
            loadManifest();check();
            if(!Arrays.asList(Build.SUPPORTED_ABIS).contains("arm64-v8a"))throw new IOException("This diagnostic requires an ARM64 device");
            File ready=new File(generation,"ready.json");
            if(ready.isFile()&&new JSONObject(new String(read(ready,16384),StandardCharsets.UTF_8)).getString("manifest_sha256").equals(manifestHash)) {
                validateInstalled();stage("Runtime ready","The pinned runtime is already installed");
            } else {
                if(home.getUsableSpace()<8L*1024*1024*1024)throw new IOException("Keep at least 8 GiB free for runtime setup");
                JSONObject lock;
                try(InputStream in=context.getAssets().open("runtime/runtime-lock.json")){lock=new JSONObject(new String(read(in,65536),StandardCharsets.UTF_8));}
                File base=download(lock.getJSONObject("base"),"database environment");
                File wine=download(lock.getJSONObject("wine"),"Windows runtime");
                File staging=new File(home,generation.getName()+".staging");
                if(staging.exists())TarExtractor.remove(staging);staging.mkdirs();
                try {
                    File root=new File(staging,"rootfs"), win=new File(staging,"wine"), pg=new File(staging,"pg"), assets=new File(staging,"assets");
                    root.mkdirs();win.mkdirs();pg.mkdirs();assets.mkdirs();
                    stage("Unpacking runtime","Preparing the private database environment");
                    TarExtractor.extract(base,root,n->listener.onStage("Unpacking environment",n+" files"));check();
                    TarExtractor.extract(wine,win,n->listener.onStage("Unpacking Windows runtime",n+" files"));check();
                    JSONObject files=manifest.getJSONObject("files");
                    for(Iterator<String> it=files.keys();it.hasNext();) {
                        String name=it.next(); if(!name.matches("[A-Za-z0-9_.-]+"))throw new IOException("Unsafe package member");
                        File dest=new File(assets,name);
                        try(InputStream in=context.getAssets().open("runtime/"+name);OutputStream out=new FileOutputStream(dest)) {
                            TarExtractor.transfer(in,out,files.getJSONObject(name).getLong("bytes"));if(in.read()!=-1)throw new IOException("Package member grew");
                        }
                        verify(dest,files.getJSONObject(name));check();
                    }
                    try(InputStream in=context.getAssets().open("runtime/runtime-manifest.json")){write(new File(assets,"runtime-manifest.json"),read(in,MAX_REPORT));}
                    TarExtractor.extract(new File(assets,"postgresql-runtime.tar.gz"),pg,n->listener.onStage("Unpacking PostgreSQL",n+" files"));
                    stage("Unpacking Atlas services","Preparing the qualified local server inputs");
                    TarExtractor.extract(new File(assets,"game-package.tar.gz"),new File(staging,"game-package"),n->listener.onStage("Unpacking game services",n+" files"));
                    TarExtractor.extract(new File(assets,"dbserver-schema.tar.gz"),new File(staging,"schema"),n->listener.onStage("Unpacking server schema",n+" files"));
                    unpackDataManifest(new File(assets,"game-data-manifest.json.gz"),new File(staging,"game-data-manifest.json"));
                    required(root,"usr/bin/python3");required(root,"usr/bin/Xtigervnc");required(win,"bin/wine");required(win,"bin/wineserver");
                    required(pg,"opt/coh/pgsql/bin/postgres");required(pg,"opt/coh/pgsql/bin/initdb");
                    if(!sha(new File(win,"lsb-fex.json")).equals(lock.getJSONObject("wine").getString("manifest_sha256")))throw new IOException("Windows runtime manifest mismatch");
                    write(new File(staging,"passwd"),"root:x:0:0:root:/root:/bin/sh\ncoh:x:1000:1000:COH:/state:/bin/sh\nnobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n".getBytes(StandardCharsets.UTF_8));
                    write(new File(staging,"group"),"root:x:0:\ncoh:x:1000:\nnogroup:x:65534:\n".getBytes(StandardCharsets.UTF_8));
                    for(String dir:new String[]{"opt/coh","opt/coh-m3","opt/coh/pgsql","opt/coh-game-package","opt/coh-game-data","opt/coh-schema","opt/wine","state","tmp"})new File(root,dir).mkdirs();
                    new File(root,"opt/coh-game-data-manifest.json").createNewFile();
                    new File(root,"opt/coh-import-contract.properties").createNewFile();
                    write(new File(staging,"ready.json"),new JSONObject().put("manifest_sha256",manifestHash).toString().getBytes(StandardCharsets.UTF_8));
                    check();if(generation.exists())TarExtractor.remove(generation);
                    if(!staging.renameTo(generation))throw new IOException("Cannot activate runtime");
                } finally {if(staging.exists())TarExtractor.remove(staging);}
                validateInstalled();stage("Runtime ready","Setup complete. Import the game assets, then run the Atlas Park test.");
            }
            report.put("status","setup_complete").put("passed",false).put("scope","Runtime installation only; run the diagnostic before claiming execution");
        } catch(Exception e) {report.put("status",control.cancelled()?"cancelled":"failed").put("error",clean(String.valueOf(e.getMessage())));throw e;}
        finally { boolean interrupted=Thread.interrupted(); try {support(report,false);} finally {if(interrupted)Thread.currentThread().interrupt();} }
    }
    private void validateInstalled() throws Exception {
        required(generation,"rootfs/usr/bin/python3");required(generation,"wine/bin/wine");required(generation,"pg/opt/coh/pgsql/bin/postgres");
        JSONObject files=manifest.getJSONObject("files");
        for(Iterator<String> it=files.keys();it.hasNext();){String name=it.next();verify(new File(generation,"assets/"+name),files.getJSONObject(name));}
        required(generation,"game-package/game-package.json"); required(generation,"schema/schema-manifest.json");
        verifyDataManifest(new File(generation,"game-data-manifest.json"));
    }
    private static final long DATA_MANIFEST_BYTES=32184737L;
    private static final String DATA_MANIFEST_SHA="b367cc35d3f3826d9988ffa5dadb0a240ffc0967f0d248586e54d8ac545615f4";
    private static final long GAME_FREE=6L*1024*1024*1024;
    private void verifyDataManifest(File file) throws Exception {
        if(!file.isFile()||Files.isSymbolicLink(file.toPath())||file.length()!=DATA_MANIFEST_BYTES
                ||!sha(file).equals(DATA_MANIFEST_SHA))throw new IOException("Reviewed game inventory differs");
    }
    private void unpackDataManifest(File archive,File target) throws Exception {
        try(InputStream in=new GZIPInputStream(new FileInputStream(archive));OutputStream out=new FileOutputStream(target)) {
            TarExtractor.transfer(in,out,DATA_MANIFEST_BYTES);
            if(in.read()!=-1)throw new IOException("Reviewed game inventory exceeds its bound");
        }
        verifyDataManifest(target);
    }
    private JSONObject json(File file,long maximum) throws Exception {
        return new JSONObject(new String(read(file,maximum),StandardCharsets.UTF_8));
    }
    private void validateImport(File selected) throws Exception {
        File privateFiles=context.getFilesDir().getCanonicalFile();
        if(selected==null)throw new IOException("Import the game assets first");
        File canonical=selected.getCanonicalFile();
        if(!canonical.equals(selected.getAbsoluteFile())||!canonical.toPath().startsWith(privateFiles.toPath())
                ||!canonical.getName().matches("generation-[0-9a-f]{32}"))throw new IOException("Invalid imported game generation");
        File current=canonical;
        while(!current.equals(privateFiles)) {
            if(Files.isSymbolicLink(current.toPath())||!current.isDirectory())throw new IOException("Unsafe imported content path");
            current=current.getParentFile();
        }
        File data=new File(canonical,"data"),receipt=new File(canonical,"complete.properties");
        if(!data.isDirectory()||Files.isSymbolicLink(data.toPath())||!receipt.isFile()
                ||Files.isSymbolicLink(receipt.toPath()))throw new IOException("Completed import is unavailable");
        byte[] raw=read(receipt,4096),contract;
        try(InputStream in=context.getAssets().open("atlas/atlas-import.properties")){contract=read(in,16384);}
        importContract=contract;
        Properties value=new Properties();value.load(new ByteArrayInputStream(raw));
        String contractSha=hex(MessageDigest.getInstance("SHA-256").digest(contract));
        if(!canonical.getName().equals(value.getProperty("generation"))||!contractSha.equals(value.getProperty("contract.sha256"))
                ||!"173011".equals(value.getProperty("count"))||!"2977730517".equals(value.getProperty("bytes")))
            throw new IOException("Completed content does not match this test package");
        importedGeneration=canonical;
        importEvidence=new JSONObject().put("generation",canonical.getName()).put("contract_sha256",contractSha)
                .put("receipt_sha256",hex(MessageDigest.getInstance("SHA-256").digest(raw)))
                .put("file_count",173011).put("total_bytes",2977730517L);
    }

    /** Consumes a completed importer generation; the guest copies and rehashes it before any game writes. */
    public Result runGameProbe(File selectedGeneration) throws Exception {
        CleanupGuard.requireClear();
        operationMode="atlas_character_persistence";
        File runRoot=new File(home,"runs/"+reports.runId);
        state=new File(runRoot,"state");
        JSONObject report=new JSONObject();
        Thread reader=null; boolean passed=false; int processExit=-1;
        Exception failure=null;
        try {
            loadManifest();check();
            if(!new File(generation,"ready.json").isFile())throw new IOException("Set up the runtime first");
            validateInstalled();validateImport(selectedGeneration);
            if(home.getUsableSpace()<GAME_FREE)throw new IOException("Keep at least 6 GiB free after setup and import for the Atlas Park test");
            Files.createDirectories(state.toPath());
            File tmp=new File(runRoot,"tmp");if(!tmp.mkdir())throw new IOException("Cannot create private temporary storage");
            String hostname=android.system.Os.uname().nodename;
            byte[] contents=DeviceHosts.contents(hostname).getBytes(StandardCharsets.US_ASCII);
            File hosts=new File(runRoot,"hosts");write(hosts,contents);
            hostsEvidence=new JSONObject().put("kernel_hostname",hostname)
                .put("guest_hosts_sha256",hex(MessageDigest.getInstance("SHA-256").digest(contents)))
                .put("contents",new String(contents,StandardCharsets.US_ASCII));
            JSONObject metadata=new JSONObject().put("format",1).put("app_id",context.getPackageName())
                .put("app_version",appVersion()).put("android_uid",android.os.Process.myUid())
                .put("android_sdk",Build.VERSION.SDK_INT).put("run_id",reports.runId)
                .put("imported_content",importEvidence).put("free_storage_bytes",home.getUsableSpace());
            write(new File(state,"android-context.json"),metadata.toString().getBytes(StandardCharsets.UTF_8));
            File contractFile=new File(runRoot,"import-contract.properties");write(contractFile,importContract);
            String guestData="/opt/coh-game-data/"+importedGeneration.getName();
            File dataMount=new File(generation,"rootfs"+guestData);Files.createDirectories(dataMount.toPath());
            File prootTmp=new File(home.getParentFile(),"p");prootTmp.mkdirs();prootTmp=prootTmp.getCanonicalFile();
            if(prootTmp.getPath().getBytes(StandardCharsets.UTF_8).length+27>107)
                throw new IOException("App storage path is too long for the process runtime's local sockets");
            String nativeDir=context.getApplicationInfo().nativeLibraryDir;
            File proot=new File(nativeDir,"libproot.so"),loader=new File(nativeDir,"libproot-loader.so");
            if(!proot.canExecute()||!loader.canExecute())throw new IOException("The APK's ARM64 process runtime is missing");
            List<String> command=new ArrayList<>(Arrays.asList(proot.getPath(),"--link2symlink","--kill-on-exit","--sysvipc",
                "-i","1000:1000","-r",new File(generation,"rootfs").getPath(),"-b","/dev","-b","/proc","-b","/sys",
                "-b",state.getPath()+":/state","-b",tmp.getPath()+":/tmp",
                "-b",new File(generation,"assets").getPath()+":/opt/coh",
                "-b",new File(generation,"assets").getPath()+":/opt/coh-m3",
                "-b",new File(generation,"pg/opt/coh/pgsql").getPath()+":/opt/coh/pgsql",
                "-b",new File(generation,"wine").getPath()+":/opt/wine",
                "-b",new File(generation,"passwd").getPath()+":/etc/passwd",
                "-b",new File(generation,"group").getPath()+":/etc/group",
                "-b",hosts.getPath()+":/etc/hosts",
                "-b",new File(generation,"game-package").getPath()+":/opt/coh-game-package",
                "-b",new File(generation,"schema").getPath()+":/opt/coh-schema",
                "-b",importedGeneration.getPath()+":"+guestData,
                "-b",contractFile.getPath()+":/opt/coh-import-contract.properties",
                "-b",new File(generation,"game-data-manifest.json").getPath()+":/opt/coh-game-data-manifest.json",
                "-w","/state","/usr/bin/env","-i","HOME=/state","USER=coh","LOGNAME=coh",
                "PATH=/opt/coh/pgsql/bin:/usr/local/bin:/usr/bin:/bin","LANG=C.UTF-8","TZ=UTC","TMPDIR=/tmp","PYTHONUNBUFFERED=1","PYTHONDONTWRITEBYTECODE=1",
                "/usr/bin/python3","/opt/coh/game_device_diagnostic.py","--state","/state","--assets","/opt/coh",
                "--pg-bin","/opt/coh/pgsql/bin","--wine","/opt/wine/bin/wine","--wineserver","/opt/wine/bin/wineserver",
                "--game-package","/opt/coh-game-package","--schema","/opt/coh-schema","--game-data",guestData,
                "--import-contract","/opt/coh-import-contract.properties",
                "--game-data-manifest","/opt/coh-game-data-manifest.json","--execution-platform","android",
                "--listener-policy","device","--android-metadata","/state/android-context.json","--timeout-seconds","5400"));
            ProcessBuilder builder=new ProcessBuilder(command);builder.redirectErrorStream(true);
            builder.environment().put("PROOT_LOADER",loader.getPath());
            builder.environment().put("PROOT_TMP_DIR",prootTmp.getPath());builder.environment().put("PROOT_NO_SECCOMP","1");
            stage("Starting Atlas Park test","Automatic character creation, save, restart and resume; allow up to 90 minutes.");
            check();child=builder.start();final Process process=child;
            reader=new Thread(()->captureOutput(process),"coh-atlas-output");reader.start();
            long deadline=System.nanoTime()+TimeUnit.MINUTES.toNanos(92),nextSample=0;
            while(!process.waitFor(200,TimeUnit.MILLISECONDS)) {
                check();long now=System.nanoTime();
                if(now>deadline)throw new IOException("Atlas Park test exceeded the 92 minute runtime limit");
                if(now>=nextSample) {
                    sampleResources();nextSample=now+TimeUnit.SECONDS.toNanos(10);
                    if(home.getUsableSpace()<512L*1024*1024)throw new IOException("Storage reserve reached; stopping owned game services");
                }
            }
            processExit=process.exitValue();reader.join(2000);check();
            report=json(new File(state,"latest-report.json"),MAX_REPORT);
            passed=processExit==0&&AtlasGameAcceptance.accepts(jsonValue(report),manifestHash,jsonValue(importEvidence),jsonValue(manifest.getJSONObject("atlas_device_bundle")));
            if(!passed)throw new IOException("An Atlas Park check failed. Export the latest report for review.");
        } catch(Exception e) {
            failure=e;appError=clean(e.getMessage()==null?e.getClass().getSimpleName():e.getMessage());
            if(cancelled||control.cancelled()||e instanceof InterruptedException||Thread.currentThread().isInterrupted()) {
                cancelled=true;control.requestStop();
            }
        } finally {
            boolean interrupted=Thread.interrupted();
            Process process=child;
            if(process!=null&&process.isAlive()) {
                signalStop();
                try {
                    if(!process.waitFor(60,TimeUnit.SECONDS)) {
                        process.destroy();if(!process.waitFor(5,TimeUnit.SECONDS))process.destroyForcibly();
                    }
                    process.waitFor(5,TimeUnit.SECONDS);
                } catch(InterruptedException ignored) {process.destroyForcibly();}
            }
            if(reader!=null)try{reader.join(2000);}catch(InterruptedException ignored){}
            boolean forcedOutputClose=reader!=null&&reader.isAlive();
            if(forcedOutputClose&&process!=null) {
                try{process.getInputStream().close();}catch(IOException ignored){}
                try{reader.join(2000);}catch(InterruptedException ignored){}
            }
            boolean alive=process!=null&&process.isAlive();
            if(!alive)child=null;
            File guest=new File(state,"latest-report.json");
            if(guest.isFile())try{report=json(guest,MAX_REPORT);}catch(Exception bad){appError="Guest report could not be read: "+bad.getClass().getSimpleName();passed=false;}
            if(report.length()==0)report.put("format",1).put("passed",false)
                .put("status",control.cancelled()?"cancelled":"failed").put("failures",new JSONArray().put("No complete guest report"));
            if(alive||forcedOutputClose||(process!=null&&!ownedCleanup(report))) {
                final JSONObject failedReport=report;
                throw CleanupGuard.block(()->{appError="Owned process cleanup could not be proved";support(failedReport,false);});
            }
            if(process!=null&&processExit<0)processExit=process.exitValue();
            sampleResources();
            try {
                passed=support(report,passed);
                if(!passed&&failure==null&&!control.cancelled())failure=new IOException(appError==null?"Atlas Park report verification failed":appError);
            } finally {if(interrupted)Thread.currentThread().interrupt();}
            // A run's writable copy is disposable. Its selected captures are already
            // immutable in the report; never remove the separate imported generation.
            if(process==null||!process.isAlive()) {
                boolean wasInterrupted=Thread.interrupted();
                try {if(runRoot.exists())TarExtractor.remove(runRoot);}
                catch(Exception cleanupFailure){line("Temporary test files need cleanup before another run");}
                finally {if(wasInterrupted)Thread.currentThread().interrupt();}
            }
        }
        if(control.cancelled())throw new InterruptedIOException("Atlas Park test stopped; imported content is preserved");
        if(failure!=null)throw failure;
        stage("Atlas Park test passed","Character creation, committed saves and restart/resume passed on this device.");
        return new Result(true,getLatestReport(),"Atlas Park server and character persistence checks passed. Interactive gameplay remains untested.");
    }

    private void captureOutput(Process process) {
        try(Reader in=new InputStreamReader(process.getInputStream(),StandardCharsets.UTF_8)) {
            char[] block=new char[4096];StringBuilder pending=new StringBuilder();boolean omitted=false;int count;
            while((count=in.read(block))!=-1)for(int i=0;i<count;i++) {
                char c=block[i];
                if(c=='\n') {
                    String text=pending.toString();pending.setLength(0);
                    if(!omitted)try {JSONObject event=new JSONObject(text);if("stage".equals(event.optString("type")))
                        listener.onStage(event.optString("stage","Checking"),clean(event.optString("message",event.optString("detail",""))));
                    }catch(Exception ignored){}
                    line(text+(omitted?" [line truncated]":""));omitted=false;
                } else if(pending.length()<8192)pending.append(c);else omitted=true;
            }
            if(pending.length()>0)line(pending.toString());
        }catch(Exception e){line("Output capture ended: "+e.getClass().getSimpleName());}
    }
    private void sampleResources() {
        if(resources.length()>=560)return;
        try {
            android.app.ActivityManager.MemoryInfo memory=new android.app.ActivityManager.MemoryInfo();
            ((android.app.ActivityManager)context.getSystemService(Context.ACTIVITY_SERVICE)).getMemoryInfo(memory);
            JSONObject sample=new JSONObject().put("elapsed_ms",System.currentTimeMillis()-started)
                .put("free_storage_bytes",home.getUsableSpace()).put("available_memory_bytes",memory.availMem)
                .put("total_memory_bytes",memory.totalMem).put("low_memory",memory.lowMemory);
            if(Build.VERSION.SDK_INT>=29)sample.put("thermal_status",((android.os.PowerManager)context.getSystemService(Context.POWER_SERVICE)).getCurrentThermalStatus());
            resources.put(sample);
        }catch(Exception ignored){}
    }
    private static Object jsonValue(Object value) throws Exception {
        if(value instanceof JSONObject){JSONObject src=(JSONObject)value;Map<String,Object> out=new HashMap<>();
            for(Iterator<String> it=src.keys();it.hasNext();){String key=it.next();out.put(key,jsonValue(src.get(key)));}return out;}
        if(value instanceof JSONArray){JSONArray src=(JSONArray)value;List<Object> out=new ArrayList<>();for(int i=0;i<src.length();i++)out.add(jsonValue(src.get(i)));return out;}
        return value;
    }
    private static boolean ownedCleanup(JSONObject report) {
        try{return AtlasGameAcceptance.cleanupSafe(jsonValue(report));}catch(Exception invalid){return false;}
    }
    private static Object sanitized(Object value) throws Exception {
        if(value instanceof JSONObject){JSONObject src=(JSONObject)value,out=new JSONObject();for(Iterator<String> it=src.keys();it.hasNext();){String key=it.next();out.put(key,sanitized(src.get(key)));}return out;}
        if(value instanceof JSONArray){JSONArray src=(JSONArray)value,out=new JSONArray();for(int i=0;i<src.length();i++)out.put(sanitized(src.get(i)));return out;}
        return value instanceof String?clean((String)value):value;
    }
    private static void zipText(ZipOutputStream out,String name,String value) throws IOException {
        out.putNextEntry(new ZipEntry(name));out.write(value.getBytes(StandardCharsets.UTF_8));out.closeEntry();
    }
    private boolean support(JSONObject report,boolean passed) throws IOException {
        try {
            if(control.finish())passed=false;
            JSONObject captures=new JSONObject();List<File> paths=new ArrayList<>();List<String> names=new ArrayList<>();
            try {collectCaptures(report,captures,paths,names);}
            catch(Exception invalid){passed=false;appError="Capture verification failed: "+invalid.getMessage();captures=new JSONObject();paths.clear();names.clear();}
            JSONObject wrapper=new JSONObject().put("format",1)
                .put("recorded_utc",new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ssXXX",Locale.ROOT).format(new Date()))
                .put("app_id",context.getPackageName()).put("app_version",appVersion()).put("android_uid",android.os.Process.myUid())
                .put("android_sdk",Build.VERSION.SDK_INT).put("device",Build.MANUFACTURER+" "+Build.MODEL)
                .put("abis",new JSONArray(Arrays.asList(Build.SUPPORTED_ABIS))).put("runtime_manifest_sha256",manifestHash)
                .put("run_id",reports.runId).put("operation",operationMode)
                .put("status",cleanupBlocked()?"cleanup_failed":control.cancelled()?"cancelled":passed?"passed":"setup".equals(operationMode)?report.optString("status","failed"):"failed")
                .put("cleanup_blocked",cleanupBlocked())
                .put("android_atlas_test_passed",passed).put("generated_character_persistence_validated",passed)
                .put("android_listener_binding_validated",passed).put("gameplay_validated",false)
                .put("android_surface_validated",false).put("interactive_rendering_validated",false)
                .put("hardware_acceleration_validated",false).put("guest",report)
                .put("resource_samples",resources).put("capture_files",captures);
            if(appError!=null)wrapper.put("app_error",appError);
            if(importEvidence!=null)wrapper.put("imported_content",importEvidence);
            if(hostsEvidence!=null)wrapper.put("guest_hosts",hostsEvidence);
            File part=reports.prepare();
            try(ZipOutputStream out=new ZipOutputStream(new FileOutputStream(part))) {
                zipText(out,"android-atlas-report.json",((JSONObject)sanitized(wrapper)).toString(2));
                synchronized(this){zipText(out,"diagnostic.log",clean(log.toString()));}
                if(manifest!=null)zipText(out,"runtime-manifest.json",manifest.toString(2));
                byte[] buffer=new byte[1024*1024];
                for(int i=0;i<paths.size();i++) {
                    File source=paths.get(i);String name=names.get(i);JSONObject pin=captures.getJSONObject(name);
                    out.putNextEntry(new ZipEntry(name));MessageDigest digest=MessageDigest.getInstance("SHA-256");long count=0;
                    try(InputStream in=new FileInputStream(source)){int n;while((n=in.read(buffer))!=-1){count+=n;if(count>pin.getLong("bytes"))throw new IOException("Capture grew during export");digest.update(buffer,0,n);out.write(buffer,0,n);}}
                    if(count!=pin.getLong("bytes")||!hex(digest.digest()).equals(pin.getString("sha256")))throw new IOException("Capture changed during export");
                    out.closeEntry();
                }
            }
            reports.publish();
            if(!passed&&"atlas_character_persistence".equals(operationMode)&&!control.cancelled()&&appError!=null)
                line(appError);
            return passed;
        }catch(Exception e){reports.discardPartial();throw new IOException("Could not save a fresh Atlas Park report",e);}
    }
    private void collectCaptures(JSONObject report,JSONObject pins,List<File> paths,List<String> names) throws Exception {
        JSONObject game=report.optJSONObject("game");if(game==null)return;long total=0;
        for(String[] group:new String[][]{{"capture_files","game-captures"},{"service_capture_files","game-service-captures"},{"hang_capture_files","game-hang-captures"}}) {
            JSONObject inventory=game.optJSONObject(group[0]);if(inventory==null)continue;
            List<String> members=new ArrayList<>();for(Iterator<String> it=inventory.keys();it.hasNext();)members.add(it.next());Collections.sort(members);
            for(String member:members) {
                long maximum=AtlasGameCapturePolicy.captureLimit(group[1],member);JSONObject pin=inventory.getJSONObject(member);
                long size=pin.getLong("bytes");String hash=pin.getString("sha256");
                if(size<0||size>maximum||!hash.matches("[0-9a-f]{64}")||paths.size()>=80||(total+=size)>192L*1024*1024)
                    throw new IOException("Capture inventory exceeds export bounds");
                File folder=new File(state,group[1]),source=new File(folder,member);
                if(Files.isSymbolicLink(folder.toPath())||Files.isSymbolicLink(source.toPath())||!source.isFile()||source.length()!=size)
                    throw new IOException("Capture file is missing or unsafe");
                MessageDigest digest=MessageDigest.getInstance("SHA-256");long actual=0;byte[] block=new byte[1024*1024];
                try(InputStream in=new FileInputStream(source)){int n;while((n=in.read(block))!=-1){actual+=n;if(actual>size)throw new IOException("Capture exceeds declared size");digest.update(block,0,n);}}
                if(actual!=size||!hex(digest.digest()).equals(hash))throw new IOException("Capture hash differs");
                if("game-captures".equals(group[1])&&"mapserver-progress.json".equals(member)
                        &&!jsonValue(json(source,maximum)).equals(jsonValue(game.getJSONObject("mapserver_progress"))))
                    throw new IOException("MapServer progress capture differs from report");
                String name=group[1]+"/"+member;pins.put(name,new JSONObject().put("bytes",size).put("sha256",hash));paths.add(source);names.add(name);
            }
        }
    }

}
