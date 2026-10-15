package org.coh.nativecombined;

import android.content.Context;
import io.github.russianranger.cohdiagnostic.AssetPackStore;
import io.github.russianranger.cohatlas.AtlasAssetImporter;
import java.io.*;
import java.nio.channels.*;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.*;

/** App-private SAF input owner. Unverified input is never selected as runtime content. */
public final class ImportStore {
    final Context context;
    final ImportContract contract;
    final File base;
    private final ImportContract.Progress progress;
    private static final long RESERVE=512L*1024*1024;
    public ImportStore(Context context,ImportContract.Progress progress)throws Exception {
        this.context=context.getApplicationContext();this.contract=new ImportContract(this.context);
        this.progress=progress==null?(phase,done,total)->{}:progress;
        base=new File(this.context.getFilesDir().getCanonicalFile(),"combined-import");directory(base.toPath());
    }
    public ImportContract contract(){return contract;}
    public String status()throws Exception {
        return "Server payload: "+(donorReady()?"verified":"import "+contract.donorName)+"\n"+assetStore(new ImportContract.Control()).status()+"\nGame files: "+(gameDataDirectory()!=null?"verified":"import all four asset parts")+"\nProfile: "+(profileDump()!=null?"disposable logical dump imported":"no logical dump imported");
    }
    public AssetPackStore assetStore(ImportContract.Control control)throws Exception {
        return new AssetPackStore(context,contract.runtimeManifest,control::check,progress::update);
    }
    public String importAssetPart(InputStream input,ImportContract.Control control)throws Exception {
        String part;AssetPackStore pack;
        try(OwnedInput selected=new OwnedInput(input)){pack=assetStore(control);part=pack.importVolume(selected);}
        control.check();
        if(pack.isAccepted()) {
            AtlasAssetImporter importer=gameImporter(pack);
            AtlasAssetImporter.Summary old=importer.inspect();
            if(old==null) {
                AtlasAssetImporter.Control token=new AtlasAssetImporter.Control();
                control.whenCancelled(token::requestCancel);
                try {importer.importArchive(pack.open("atlas/atlas-assets.zip"),(phase,files,totalFiles,bytes,totalBytes)->{
                    if(control.isCancelled()||Thread.currentThread().isInterrupted())token.requestCancel();
                    progress.update(phase,totalBytes>0?bytes:files,totalBytes>0?totalBytes:totalFiles);
                },token);} finally {control.whenCancelled(null);if(control.isCancelled())token.requestCancel();}
            }
        }
        return part;
    }
    private AtlasAssetImporter gameImporter(AssetPackStore pack)throws IOException {
        return new AtlasAssetImporter(new File(context.getFilesDir().getCanonicalFile(),"combined-game-import"),name->{
            try {return pack.contains("atlas/"+name)?pack.open("atlas/"+name):context.getAssets().open("atlas/"+name);}
            catch(IOException e){throw e;}catch(Exception e){throw new IOException("Cannot open verified game content",e);}
        });
    }
    public File gameDataDirectory()throws Exception {
        AtlasAssetImporter.Summary value=gameImporter(assetStore(new ImportContract.Control())).inspect();
        return value==null?null:value.dataDirectory;
    }
    public File runtimePayloadDirectory(){return new File(base,"donor-"+contract.donor.sha256);}
    public boolean donorReady()throws IOException {
        File dir=runtimePayloadDirectory();File receipt=new File(dir,"accepted.sha256");
        if(!regular(receipt.toPath(),65))return false;
        return new String(Files.readAllBytes(receipt.toPath()),java.nio.charset.StandardCharsets.US_ASCII).equals(contract.donor.sha256+"\n");
    }
    public void importDonorApk(InputStream input,ImportContract.Control control)throws Exception {
        Path stage=null;
        try(OwnedInput source=new OwnedInput(input);FileChannel channel=FileChannel.open(new File(base,"import.lock").toPath(),StandardOpenOption.CREATE,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS);FileLock lock=lock(channel)) {
            control.check();if(base.getUsableSpace()<2*contract.donor.bytes+RESERVE)throw new IOException("Free additional internal storage before importing the server payload");
            stage=new File(base,".donor-"+UUID.randomUUID()).toPath();Files.createDirectory(stage);
            Path apk=stage.resolve("selected.apk");copy(source,apk,contract.donor,control,progress,"Checking original server APK");
            source.close(); // No document-provider close can follow publication.
            Path out=stage.resolve("payload");Files.createDirectory(out);
            try(ZipFile zip=new ZipFile(apk.toFile())) {
                Set<String> names=new HashSet<>();int count=0;
                for(Enumeration<? extends ZipEntry> all=zip.entries();all.hasMoreElements();) {
                    ZipEntry entry=all.nextElement();if(++count>10000||!names.add(entry.getName()))throw new IOException("Duplicate or unbounded donor APK inventory");
                }
                for(Map.Entry<String,ImportContract.Pin> member:contract.donorFiles.entrySet()) {
                    control.check();ZipEntry entry=zip.getEntry(member.getKey());
                    if(entry==null||entry.isDirectory()||entry.getSize()!=member.getValue().bytes)throw new IOException("Pinned server member is missing or differs");
                    String leaf=member.getKey().substring("assets/runtime/".length());ImportContract.safeLeaf(leaf);
                    try(InputStream in=zip.getInputStream(entry)){copy(in,out.resolve(leaf),member.getValue(),control,progress,"Importing server payload");}
                }
            }
            Files.delete(apk);write(out.resolve("accepted.sha256"),(contract.donor.sha256+"\n").getBytes(java.nio.charset.StandardCharsets.US_ASCII));
            Path target=runtimePayloadDirectory().toPath();
            if(Files.exists(target,LinkOption.NOFOLLOW_LINKS)) {
                if(!donorReady())throw new IOException("An incomplete existing donor requires recovery before replacement");
                // Exact content is already accepted. Verify again, then retain its inode.
                for(Map.Entry<String,ImportContract.Pin> member:contract.donorFiles.entrySet())verify(target.resolve(member.getKey().substring(15)),member.getValue(),control,progress);
            } else {final Path published=out;control.publish(()->Files.move(published,target,StandardCopyOption.ATOMIC_MOVE));}
        } finally {if(stage!=null)quietRemove(stage);}
    }
    public File importRuntimeArchive(String kind,InputStream input,ImportContract.Control control)throws Exception {
        if(!"base".equals(kind)&&!"wine".equals(kind)){try(InputStream owned=input){throw new IOException("Choose base or wine runtime");}}
        ImportContract.Pin pin=ImportContract.pin(contract.runtimeLock.getJSONObject(kind));
        return importObject("runtime-"+kind,input,pin,control);
    }
    File runtimeArchive(String kind)throws Exception {
        ImportContract.Pin pin=ImportContract.pin(contract.runtimeLock.getJSONObject(kind));
        Path path=new File(base,"runtime-"+kind+"-"+pin.sha256).toPath();return regular(path,pin.bytes)?path.toFile():null;
    }
    File importObject(String name,InputStream input,ImportContract.Pin pin,ImportContract.Control control)throws IOException {
        Path temp=new File(base,".object-"+UUID.randomUUID()).toPath();Path target=new File(base,name+"-"+pin.sha256).toPath();
        try(OwnedInput source=new OwnedInput(input);FileChannel channel=FileChannel.open(new File(base,"import.lock").toPath(),StandardOpenOption.CREATE,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS);FileLock lock=lock(channel)) {
            if(base.getUsableSpace()<pin.bytes+RESERVE)throw new IOException("Not enough internal storage for this import");
            copy(source,temp,pin,control,progress,"Checking runtime archive");source.close();
            control.publish(()->Files.move(temp,target,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING));return target.toFile();
        } finally {Files.deleteIfExists(temp);}
    }
    /** Import user data, never raw pgdata. Restoration is explicit and occurs only in the isolated profile. */
    public File importProfileDump(InputStream input,ImportContract.Control control)throws IOException {
        Path temp=new File(base,".profile-"+UUID.randomUUID()).toPath();Path target=new File(base,"profile.pgdump").toPath();
        try(OwnedInput source=new OwnedInput(input);FileChannel channel=FileChannel.open(new File(base,"import.lock").toPath(),StandardOpenOption.CREATE,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS);FileLock lock=lock(channel)) {
            byte[] header=new byte[5];int pos=0;while(pos<header.length){control.check();int n=source.read(header,pos,header.length-pos);if(n<=0)throw new IOException("Truncated logical PostgreSQL dump");pos+=n;}
            if(!Arrays.equals(header,new byte[]{'P','G','D','M','P'}))throw new IOException("Select a PostgreSQL custom-format logical dump (PGDMP), not a database directory or report ZIP");
            try(FileOutputStream out=new FileOutputStream(temp.toFile())) {
                out.write(header);byte[] buffer=new byte[65536];long done=5;int n;
                while((n=source.read(buffer))!=-1){control.check();if(n==0)throw new IOException("Dump provider made no progress");done+=n;if(done>512L*1024*1024||base.getUsableSpace()<RESERVE)throw new IOException("Logical dump exceeds available storage or the 4 GiB bound");out.write(buffer,0,n);progress.update("Importing isolated profile dump",done,0);}out.getFD().sync();
            }
            source.close();control.publish(()->Files.move(temp,target,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING));return target.toFile();
        } finally {Files.deleteIfExists(temp);}
    }
    public File profileDump()throws IOException {Path p=new File(base,"profile.pgdump").toPath();return regular(p,-1)?p.toFile():null;}
    static void copy(InputStream input,Path output,ImportContract.Pin pin,ImportContract.Control control,ImportContract.Progress progress,String phase)throws IOException {
        noLinks(output);MessageDigest digest=ImportContract.hash();long done=0,last=0;byte[] buffer=new byte[65536];
        try(FileChannel out=FileChannel.open(output,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS)) {
            OutputStream sink=Channels.newOutputStream(out);int n;
            while((n=input.read(buffer))!=-1){control.check();if(n==0)throw new IOException("Provider made no progress");done+=n;if(done>pin.bytes)throw new IOException("Selected input exceeds its pinned size");sink.write(buffer,0,n);digest.update(buffer,0,n);if(done-last>=4L*1024*1024){progress.update(phase,done,pin.bytes);last=done;}}
            if(done!=pin.bytes||!pin.sha256.equals(ImportContract.hex(digest.digest())))throw new IOException("Selected input size or SHA-256 does not match the required version");out.force(true);
        }
    }
    static void verify(Path file,ImportContract.Pin pin,ImportContract.Control control,ImportContract.Progress progress)throws IOException {
        if(!regular(file,pin.bytes))throw new IOException("Imported runtime payload is missing");MessageDigest hash=ImportContract.hash();long done=0;byte[] buffer=new byte[65536];
        try(InputStream in=Files.newInputStream(file,LinkOption.NOFOLLOW_LINKS)){int n;while((n=in.read(buffer))!=-1){control.check();if(n==0)throw new IOException("Payload made no progress");hash.update(buffer,0,n);done+=n;}}
        if(done!=pin.bytes||!pin.sha256.equals(ImportContract.hex(hash.digest())))throw new IOException("Imported runtime payload checksum differs");
    }
    private static final class OwnedInput extends FilterInputStream {
        private boolean closed;OwnedInput(InputStream in){super(Objects.requireNonNull(in));}
        @Override public void close()throws IOException{if(!closed){closed=true;super.close();}}
    }
    private static void quietRemove(Path path){try{remove(path);}catch(IOException ignored){/* Unpublished private staging is reclaimed explicitly, never selected as ready. */}}
    static FileLock lock(FileChannel channel)throws IOException {try {FileLock lock=channel.tryLock();if(lock==null)throw new IOException("Another import is active");return lock;}catch(OverlappingFileLockException e){throw new IOException("Another import is active",e);}}
    static boolean regular(Path p,long bytes)throws IOException {noLinks(p);return Files.isRegularFile(p,LinkOption.NOFOLLOW_LINKS)&&(bytes<0||Files.size(p)==bytes);}
    static void directory(Path p)throws IOException {noLinks(p);Files.createDirectories(p);if(!Files.isDirectory(p,LinkOption.NOFOLLOW_LINKS))throw new IOException("Unsafe private directory");}
    static void noLinks(Path path)throws IOException {Path at=path.toAbsolutePath().getRoot();for(Path p:path.toAbsolutePath()){at=at.resolve(p);if(Files.isSymbolicLink(at))throw new IOException("Private import path contains a symbolic link");}}
    static void write(Path path,byte[] data)throws IOException {noLinks(path);try(FileOutputStream out=new FileOutputStream(path.toFile())){out.write(data);out.getFD().sync();}}
    static void remove(Path path)throws IOException {
        if(!Files.exists(path,LinkOption.NOFOLLOW_LINKS))return;
        Files.walkFileTree(path,new SimpleFileVisitor<Path>(){
            @Override public FileVisitResult visitFile(Path p,BasicFileAttributes a)throws IOException{Files.delete(p);return FileVisitResult.CONTINUE;}
            @Override public FileVisitResult postVisitDirectory(Path p,IOException failure)throws IOException{if(failure!=null)throw failure;Files.delete(p);return FileVisitResult.CONTINUE;}
        });
    }
}
