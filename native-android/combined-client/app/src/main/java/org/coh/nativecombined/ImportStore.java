package org.coh.nativecombined;

import android.content.Context;
import android.system.Os;
import android.system.OsConstants;
import android.system.StructStat;
import android.system.ErrnoException;
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
    // Linux UAPI asm-generic/fcntl.h: O_CLOEXEC = 02000000 on Android arm64/x86_64.
    // Use the kernel flag directly: the public SDK constant starts after minSdk 26.
    private static final int LINUX_O_CLOEXEC=0x80000;
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
                    sealVerified(out.resolve(leaf),member.getValue(),control,progress);
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
    /** One verified immutable inode; aliases are checked again before publication. */
    static final class SealRecord {
        final Path path;final ImportContract.Pin pin;final StructStat observed;final List<Path> aliases=new ArrayList<>();
        SealRecord(Path path,ImportContract.Pin pin,StructStat observed){this.path=path;this.pin=pin;this.observed=observed;aliases.add(path);}
    }
    static StructStat immutableStat(Path path,ImportContract.Pin pin)throws IOException {
        noLinks(path);
        try {
            StructStat value=Os.lstat(path.toString());
            if(!OsConstants.S_ISREG(value.st_mode)||value.st_uid!=android.os.Process.myUid()||value.st_size!=pin.bytes)
                throw new IOException("Immutable input has an unexpected type, owner or size");
            return value;
        } catch(ErrnoException e){throw new IOException("Cannot inspect an immutable input",e);}
    }
    static boolean sameFile(StructStat a,StructStat b){return a.st_dev==b.st_dev&&a.st_ino==b.st_ino&&a.st_uid==b.st_uid&&a.st_size==b.st_size;}
    static boolean sameState(StructStat a,StructStat b){return sameFile(a,b)&&a.st_mode==b.st_mode&&a.st_nlink==b.st_nlink&&a.st_mtime==b.st_mtime&&a.st_ctime==b.st_ctime;}
    static boolean readonly(Path path,ImportContract.Pin pin)throws IOException{return (immutableStat(path,pin).st_mode&0222)==0;}
    static SealRecord verifyForSeal(Path path,ImportContract.Pin pin,ImportContract.Control control,ImportContract.Progress progress)throws IOException {
        StructStat before=immutableStat(path,pin);MessageDigest hash=ImportContract.hash();long done=0,last=0;byte[] buffer=new byte[65536];
        try {
            FileDescriptor fd=Os.open(path.toString(),OsConstants.O_RDONLY|OsConstants.O_NOFOLLOW|LINUX_O_CLOEXEC,0);
            try {
                if(!sameState(before,Os.fstat(fd)))throw new IOException("Immutable input changed before verification");
                int n;while((n=Os.read(fd,buffer,0,buffer.length))!=0){control.check();if(n<0)throw new IOException("Invalid immutable input read result");done+=n;if(done>pin.bytes)throw new IOException("Immutable input exceeds its pin");hash.update(buffer,0,n);if(done-last>=4L*1024*1024){progress.update("Verifying immutable server inputs",done,pin.bytes);last=done;}}
                if(done!=pin.bytes||!pin.sha256.equals(ImportContract.hex(hash.digest()))||!sameState(before,Os.fstat(fd))||!sameState(before,immutableStat(path,pin)))
                    throw new IOException("Immutable input SHA-256 or identity differs");
            } finally {Os.close(fd);}
        } catch(ErrnoException e){throw new IOException("Cannot verify an immutable input",e);}
        return new SealRecord(path,pin,before);
    }
    static void requireSealAliases(SealRecord record,boolean sealed)throws IOException {
        for(Path path:record.aliases){StructStat current=immutableStat(path,record.pin);
            if(!(sealed?sameFile(record.observed,current)&&(current.st_mode&0222)==0:sameState(record.observed,current)))
                throw new IOException("Immutable input alias changed during preparation");}
    }
    static void setSealMode(SealRecord record,int mode,boolean requireOriginal)throws IOException {
        noLinks(record.path);
        try {
            FileDescriptor fd=Os.open(record.path.toString(),OsConstants.O_RDONLY|OsConstants.O_NOFOLLOW|LINUX_O_CLOEXEC,0);
            try {
                StructStat current=Os.fstat(fd);
                if(!(requireOriginal?sameState(record.observed,current):sameFile(record.observed,current)))throw new IOException("Immutable inode changed before permission update");
                Os.fchmod(fd,mode);current=Os.fstat(fd);
                if(!sameFile(record.observed,current)||(current.st_mode&0777)!=mode)throw new IOException("Immutable input permission update was not retained");
            } finally {Os.close(fd);}
        }catch(ErrnoException e){throw new IOException("Cannot protect an immutable input",e);}
    }
    static void sealVerified(Path path,ImportContract.Pin pin,ImportContract.Control control,ImportContract.Progress progress)throws IOException {
        SealRecord record=verifyForSeal(path,pin,control,progress);
        control.publish(()->{requireSealAliases(record,false);if((record.observed.st_mode&0222)!=0)setSealMode(record,record.observed.st_mode&0555,true);requireSealAliases(record,true);});
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
