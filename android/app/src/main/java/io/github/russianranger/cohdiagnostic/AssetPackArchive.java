package io.github.russianranger.cohdiagnostic;

import java.io.*;
import java.nio.channels.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.*;
import java.util.*;
import java.util.zip.*;

/** Bounded, transactional import of APK-pinned asset volumes. No Android or JSON dependency. */
public final class AssetPackArchive {
    public interface Check { void check() throws IOException; }
    public interface Sync { void sync() throws IOException; }
    public interface Io {
        void before() throws IOException;
        void read(long bytes) throws IOException;
        void written(long bytes, Sync sync) throws IOException;
        void synced();
    }
    public interface Progress { void update(String phase, long done, long total); }
    public interface Space { long usable(File directory); }
    public static final class Pin {
        public final long bytes;
        public final String sha256;
        public Pin(long bytes, String sha256) throws IOException {
            if(bytes<0||bytes>8L*1024*1024*1024||sha256==null||!sha256.matches("[0-9a-f]{64}"))throw new IOException("Invalid asset pin");
            this.bytes=bytes;this.sha256=sha256;
        }
    }
    private static final long RESERVE=512L*1024*1024, MAX_ARCHIVE=2L*1024*1024*1024;
    private final Path base,objects,accepted;
    private final byte[] descriptor;
    private final String descriptorHash;
    private final SortedMap<String,Pin> pins;
    private final SortedMap<String,Set<String>> volumes;
    private final Check check;
    private final Io io;
    private final Progress progress;
    private final Space space;
    public AssetPackArchive(File directory, byte[] descriptor, Map<String,Pin> pins,
            Map<String,Set<String>> volumes, Check check, Io io, Progress progress) throws IOException {
        this(directory,descriptor,pins,volumes,check,io,progress,File::getUsableSpace);
    }
    public AssetPackArchive(File directory, byte[] descriptor, Map<String,Pin> pins,
            Map<String,Set<String>> volumes, Check check, Io io, Progress progress, Space space) throws IOException {
        if(descriptor.length<1||descriptor.length>1024*1024||pins.isEmpty()||pins.size()>256||volumes.isEmpty()||volumes.size()>16)
            throw new IOException("Invalid asset pack inventory");
        this.base=directory.toPath().toAbsolutePath();this.objects=base.resolve("objects");this.accepted=base.resolve("accepted");
        this.descriptor=descriptor.clone();this.descriptorHash=hex(digest().digest(descriptor));
        this.pins=new TreeMap<>(pins);this.volumes=new TreeMap<>();this.check=check;this.io=io;this.progress=progress;this.space=space;
        Set<String> assigned=new HashSet<>();
        for(String name:pins.keySet())safeName(name);
        for(Map.Entry<String,Set<String>> volume:volumes.entrySet()) {
            if(!volume.getKey().matches("[a-z0-9][a-z0-9-]{0,63}")||volume.getValue().isEmpty())throw new IOException("Invalid asset volume");
            for(String name:volume.getValue())if(!pins.containsKey(name)||!assigned.add(name))throw new IOException("Overlapping asset volume inventory");
            this.volumes.put(volume.getKey(),new TreeSet<>(volume.getValue()));
        }
        if(!assigned.equals(pins.keySet()))throw new IOException("Incomplete asset volume inventory");
        directory(base);directory(objects);directory(accepted);
    }
    public boolean contains(String name) { return pins.containsKey(name); }
    public String descriptorHash() { return descriptorHash; }
    public List<String> missingVolumes() throws IOException {
        List<String> missing=new ArrayList<>();
        for(Map.Entry<String,Set<String>> volume:volumes.entrySet())for(String name:volume.getValue()) {
            if(!regular(objects.resolve(pins.get(name).sha256),pins.get(name).bytes)){missing.add(volume.getKey());break;}
        }
        return missing;
    }
    public boolean isAccepted() throws IOException {
        Path receipt=accepted.resolve(descriptorHash+".json");
        if(!regular(receipt,descriptor.length))return false;
        return Arrays.equals(descriptor,Files.readAllBytes(receipt))&&missingVolumes().isEmpty();
    }
    public File resolve(String name) throws IOException {
        Pin pin=pins.get(name);
        if(pin==null)throw new IOException("Asset is not part of this pack: "+name);
        if(!isAccepted())throw new IOException("Import all required asset pack parts first: "+String.join(", ",missingVolumes()));
        Path file=objects.resolve(pin.sha256);noLinks(file);
        if(!regular(file,pin.bytes))throw new IOException("Imported asset is missing: "+name);
        return file.toFile();
    }
    public InputStream open(String name) throws IOException {return Files.newInputStream(resolve(name).toPath(),LinkOption.NOFOLLOW_LINKS);}
    public void verify(String name) throws IOException {
        File file=resolve(name);Pin pin=pins.get(name);verifyFile(file.toPath(),pin);
    }
    /** One exact volume is accepted at a time; a previous full receipt is never replaced. */
    public String importVolume(InputStream selected) throws IOException {
        return importVolume(selected,()->{});
    }
    /** Own the provider before admission, so memory pressure or cancellation cannot leak its fd. */
    public String importVolume(InputStream selected,Check admission) throws IOException {
        Path staging=null;
        try(OwnedInput source=new OwnedInput(selected);FileChannel channel=FileChannel.open(base.resolve("import.lock"),StandardOpenOption.CREATE,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS)) {
            FileLock lock;
            try {lock=channel.tryLock();}catch(OverlappingFileLockException e){throw new IOException("An asset import is already running",e);}
            if(lock==null)throw new IOException("An asset import is already running");
            try(FileLock owned=lock) {
                admission.check();check.check();recoverStaging();
                long largest=0;
                for(Set<String> names:volumes.values()){long total=0;for(String name:names)total=Math.addExact(total,pins.get(name).bytes);largest=Math.max(largest,total);}
                long limit=Math.min(MAX_ARCHIVE,Math.addExact(largest,2L*1024*1024));
                if(space.usable(base.toFile())<Math.addExact(Math.multiplyExact(largest,2),RESERVE))
                    throw new IOException("Not enough internal storage for safe asset import; free at least "+(2*largest+RESERVE)/1048576+" MiB");
                staging=base.resolve(".import-"+UUID.randomUUID().toString());Files.createDirectory(staging);
                Path archive=staging.resolve("selected.zip");
                copyArchive(source,archive,limit);
                source.close(); // Release the document provider before verifying private files or publishing receipts.
                SortedMap<String,Pin> members=validateCentral(archive);
                Set<String> memberNames=new TreeSet<>();for(String name:members.keySet())if(name.startsWith("payloads/"))memberNames.add(name.substring(9));
                String volume=null;
                for(Map.Entry<String,Set<String>> entry:volumes.entrySet())if(entry.getValue().equals(memberNames)){volume=entry.getKey();break;}
                if(volume==null)throw new IOException("This ZIP does not contain one complete asset pack part");
                BasicFileAttributes objectDirectory=directoryIdentity(objects);
                Map<String,BasicFileAttributes> previousObjects=new HashMap<>(),verifiedStaging=new HashMap<>();
                long total=0;for(String name:memberNames)total+=pins.get(name).bytes;
                long done=0;Set<String> seen=new HashSet<>();
                try(ZipInputStream zip=new ZipInputStream(Files.newInputStream(archive))) {
                    ZipEntry entry;
                    while((entry=zip.getNextEntry())!=null) {
                        check.check();String name=entry.getName();Pin pin=members.get(name);
                        if(pin==null||!seen.add(name)||entry.isDirectory())throw new IOException("Unexpected or duplicate asset ZIP member");
                        if(name.equals("asset-pack-manifest.json")) {
                            ByteArrayOutputStream data=new ByteArrayOutputStream();copyPayload(zip,data,pin,null,0,pin.bytes);
                            if(!Arrays.equals(descriptor,data.toByteArray()))throw new IOException("This asset pack version does not match the installed APK");
                        } else {
                            Path object=objects.resolve(pin.sha256),output=staging.resolve(pin.sha256);
                            if(!previousObjects.containsKey(pin.sha256))previousObjects.put(pin.sha256,objectIdentity(object));
                            boolean reuse=verifiedStaging.containsKey(pin.sha256);
                            if(reuse)requireIdentity(output,verifiedStaging.get(pin.sha256));
                            else if(regular(object,pin.bytes)) {
                                try{verifyFile(object,pin);reuse=true;}catch(IOException damaged){check.check();}
                                requireIdentity(object,previousObjects.get(pin.sha256));
                            }
                            if(reuse)copyPayload(zip,null,pin,null,done,total);
                            else {
                                try(FileChannel file=FileChannel.open(output,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS)) {
                                    copyPayload(zip,Channels.newOutputStream(file),pin,()->file.force(true),done,total);file.force(true);io.synced();
                                }
                                verifiedStaging.put(pin.sha256,objectIdentity(output));
                            }
                            done+=pin.bytes;
                        }
                        zip.closeEntry();
                    }
                }
                if(!seen.equals(members.keySet()))throw new IOException("Asset ZIP local and central inventories differ");
                requireDirectoryIdentity(objects,objectDirectory);
                for(Map.Entry<String,BasicFileAttributes> prior:previousObjects.entrySet())
                    requireIdentity(objects.resolve(prior.getKey()),prior.getValue());
                // Every member has passed its own digest before any shared object is published.
                for(String name:memberNames) {
                    check.check();Pin pin=pins.get(name);Path staged=staging.resolve(pin.sha256),object=objects.resolve(pin.sha256);
                    if(Files.exists(staged,LinkOption.NOFOLLOW_LINKS)) {
                        requireDirectoryIdentity(objects,objectDirectory);
                        requireIdentity(staged,verifiedStaging.get(pin.sha256));
                        if(!staged.toFile().setReadOnly())throw new IOException("Cannot protect an imported asset");
                        requireIdentity(object,previousObjects.get(pin.sha256));
                        // Replace only the directory entry. A damaged previous inode is
                        // never written or truncated; existing runtime links retain it.
                        Files.move(staged,object,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
                    }
                }
                if(missingVolumes().isEmpty()) {
                    for(String name:pins.keySet())verifyFile(objects.resolve(pins.get(name).sha256),pins.get(name));
                    check.check();Path receipt=staging.resolve("complete.json");
                    try(FileOutputStream out=new FileOutputStream(receipt.toFile())){out.write(descriptor);out.getFD().sync();}
                    Files.move(receipt,accepted.resolve(descriptorHash+".json"),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
                }
                return volume;
            }
        } finally {if(staging!=null)try{remove(staging);}catch(IOException ignored){/* recover only this store's interrupted staging on next import */}}
    }
    private static final class OwnedInput extends FilterInputStream {
        private boolean closed;
        OwnedInput(InputStream input){super(Objects.requireNonNull(input));}
        @Override public void close()throws IOException{if(!closed){closed=true;super.close();}}
    }
    private void copyArchive(InputStream source,Path dest,long limit) throws IOException {
        try(FileChannel out=FileChannel.open(dest,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS)) {
            OutputStream sink=Channels.newOutputStream(out);byte[] buffer=new byte[65536];long done=0,last=0;int count;
            while(true){check.check();io.before();count=source.read(buffer);if(count<0)break;if(count==0)throw new IOException("Asset provider made no progress");
                io.read(count);done+=count;if(done>limit)throw new IOException("Selected asset ZIP exceeds its pinned size bound");sink.write(buffer,0,count);io.written(count,()->out.force(true));
                if(done-last>=4L*1024*1024){progress.update("Reading asset pack",done,0);last=done;}}
            out.force(true);io.synced();
        }
    }
    private void copyPayload(InputStream in,OutputStream out,Pin pin,Sync sync,long previous,long total) throws IOException {
        MessageDigest hash=digest();byte[] buffer=new byte[65536];long done=0,last=0;int count;
        while(true){check.check();io.before();count=in.read(buffer);if(count<0)break;if(count==0)throw new IOException("Asset member made no progress");
            done+=count;if(done>pin.bytes)throw new IOException("Asset member exceeds pinned size");io.read(count);hash.update(buffer,0,count);
            if(out!=null){out.write(buffer,0,count);if(sync!=null)io.written(count,sync);}
            if(done-last>=4L*1024*1024){progress.update("Verifying asset pack",previous+done,total);last=done;}}
        if(done!=pin.bytes||!pin.sha256.equals(hex(hash.digest())))throw new IOException("Asset member checksum or size mismatch");
    }
    private void verifyFile(Path file,Pin pin) throws IOException {
        noLinks(file);if(!regular(file,pin.bytes))throw new IOException("Imported asset is missing or unsafe");
        try(InputStream in=Files.newInputStream(file,LinkOption.NOFOLLOW_LINKS)){copyPayload(in,null,pin,null,0,pin.bytes);}
    }
    private SortedMap<String,Pin> validateCentral(Path archive) throws IOException {
        SortedMap<String,Pin> result=new TreeMap<>();
        try(RandomAccessFile in=new RandomAccessFile(archive.toFile(),"r")) {
            long length=in.length(),end=-1;
            for(long at=length-22,first=Math.max(0,length-65557);at>=first;at--){in.seek(at);if(u32(in)==0x06054b50L){in.seek(at+20);if(at+22+u16(in)==length){end=at;break;}}}
            if(end<0)throw new IOException("Missing or truncated asset ZIP central directory");
            in.seek(end+4);if(u16(in)!=0||u16(in)!=0)throw new IOException("Multi-disk asset ZIP is unsupported");
            long disk=u16(in),count=u16(in),size=u32(in),offset=u32(in);
            // Release volumes are deliberately bounded below 2 GiB and 257 members.
            if(count!=disk||count<2||count>pins.size()+1||offset+size!=end)throw new IOException("Invalid asset ZIP central directory");
            in.seek(offset);byte[] header=new byte[46];Set<Long> localOffsets=new HashSet<>();
            for(long i=0;i<count;i++) {
                check.check();in.readFully(header);
                if(le32(header,0)!=0x02014b50L)throw new IOException("Invalid asset ZIP entry");
                int made=le16(header,4),flags=le16(header,8),method=le16(header,10),nameLength=le16(header,28),extraLength=le16(header,30),comment=le16(header,32);
                long compressed=le32(header,20),bytes=le32(header,24),attributes=le32(header,38),local=le32(header,42);
                if((made>>8)!=3||((attributes>>16)&0170000)!=0100000||(attributes&0x10)!=0
                        ||(flags&1)!=0||(method!=0&&method!=8)||le16(header,34)!=0||nameLength==0||nameLength>512||local>=offset||!localOffsets.add(local))
                    throw new IOException("Asset ZIP contains a link, unsafe entry or unsupported metadata");
                byte[] encoded=new byte[nameLength];in.readFully(encoded);for(byte b:encoded)if((b&255)<32||(b&255)>126)throw new IOException("Non-ASCII asset path");
                String name=new String(encoded,StandardCharsets.US_ASCII);Pin pin;
                if(name.equals("asset-pack-manifest.json"))pin=new Pin(descriptor.length,descriptorHash);
                else {if(!name.startsWith("payloads/"))throw new IOException("Unknown asset ZIP path");safeName(name.substring(9));pin=pins.get(name.substring(9));}
                if(pin==null||bytes!=pin.bytes||compressed>length||result.put(name,pin)!=null)throw new IOException("Asset ZIP inventory or size mismatch");
                long next=in.getFilePointer()+extraLength+comment;if(next>end)throw new IOException("Truncated asset ZIP metadata");
                // Validate the local entry against its central identity before streaming it.
                in.seek(local);if(u32(in)!=0x04034b50L)throw new IOException("Invalid asset ZIP local header");
                in.seek(local+6);if(u16(in)!=flags||u16(in)!=method)throw new IOException("Asset ZIP local metadata differs");
                in.seek(local+26);int localName=u16(in),localExtra=u16(in);
                if(localName!=nameLength||local+30+localName+localExtra+compressed>offset)throw new IOException("Asset ZIP local range differs");
                byte[] localEncoded=new byte[localName];in.readFully(localEncoded);if(!Arrays.equals(encoded,localEncoded))throw new IOException("Asset ZIP local name differs");
                in.seek(next);
            }
            if(in.getFilePointer()!=end||!result.containsKey("asset-pack-manifest.json"))throw new IOException("Unexpected asset ZIP central data");
        }
        return result;
    }
    private void recoverStaging() throws IOException {
        try(DirectoryStream<Path> entries=Files.newDirectoryStream(base)) {for(Path entry:entries){check.check();if(entry.getFileName().toString().matches("\\.import-[0-9a-f-]{36}"))remove(entry);}}
    }
    private static void remove(Path path) throws IOException {
        Files.walkFileTree(path,new SimpleFileVisitor<Path>() {
            @Override public FileVisitResult visitFile(Path file,BasicFileAttributes attrs)throws IOException{Files.delete(file);return FileVisitResult.CONTINUE;}
            @Override public FileVisitResult postVisitDirectory(Path dir,IOException failure)throws IOException{if(failure!=null)throw failure;Files.delete(dir);return FileVisitResult.CONTINUE;}
        });
    }
    private static boolean regular(Path file,long bytes) throws IOException {noLinks(file);return Files.isRegularFile(file,LinkOption.NOFOLLOW_LINKS)&&Files.size(file)==bytes;}
    private static BasicFileAttributes objectIdentity(Path file) throws IOException {
        noLinks(file);
        try {
            BasicFileAttributes value=Files.readAttributes(file,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
            if(!value.isRegularFile()||value.fileKey()==null)throw new IOException("Asset object is not an identifiable regular file");
            return value;
        } catch(NoSuchFileException missing){return null;}
    }
    private static void requireIdentity(Path file,BasicFileAttributes expected) throws IOException {
        BasicFileAttributes actual=objectIdentity(file);
        if(expected==null?actual!=null:actual==null||!expected.fileKey().equals(actual.fileKey())
                ||expected.size()!=actual.size()||!expected.lastModifiedTime().equals(actual.lastModifiedTime())
                ||!expected.creationTime().equals(actual.creationTime()))throw new IOException("Asset object changed during import");
    }
    private static BasicFileAttributes directoryIdentity(Path path) throws IOException {
        noLinks(path);BasicFileAttributes value=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(!value.isDirectory()||value.fileKey()==null)throw new IOException("Asset directory is not identifiable");
        return value;
    }
    private static void requireDirectoryIdentity(Path path,BasicFileAttributes expected) throws IOException {
        if(!expected.fileKey().equals(directoryIdentity(path).fileKey()))throw new IOException("Asset directory changed during import");
    }
    private static void directory(Path path) throws IOException {noLinks(path);Files.createDirectories(path);if(!Files.isDirectory(path,LinkOption.NOFOLLOW_LINKS))throw new IOException("Unsafe asset directory");}
    private static void noLinks(Path path) throws IOException {Path current=path.toAbsolutePath().getRoot();for(Path part:path.toAbsolutePath()){current=current.resolve(part);if(Files.isSymbolicLink(current))throw new IOException("Asset storage path contains a symbolic link");}}
    private static void safeName(String name) throws IOException {
        if(name==null||name.length()>480||!name.matches("(?:runtime|atlas)/[A-Za-z0-9_.-]+")||name.endsWith("/.")||name.endsWith("/.."))throw new IOException("Unsafe asset pack path");
    }
    private static MessageDigest digest(){try{return MessageDigest.getInstance("SHA-256");}catch(NoSuchAlgorithmException e){throw new AssertionError(e);}}
    private static String hex(byte[] bytes){StringBuilder out=new StringBuilder();for(byte b:bytes){out.append(Character.forDigit((b>>>4)&15,16));out.append(Character.forDigit(b&15,16));}return out.toString();}
    private static int u16(RandomAccessFile in)throws IOException{return in.readUnsignedByte()|in.readUnsignedByte()<<8;}
    private static long u32(RandomAccessFile in)throws IOException{return (long)u16(in)|(long)u16(in)<<16;}
    private static int le16(byte[] bytes,int at){return(bytes[at]&255)|(bytes[at+1]&255)<<8;}
    private static long le32(byte[] bytes,int at){return(long)le16(bytes,at)|(long)le16(bytes,at+2)<<16;}
}
