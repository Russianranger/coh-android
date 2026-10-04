package io.github.russianranger.cohclientinteractive;

import android.system.ErrnoException;
import android.system.Os;
import android.system.OsConstants;
import android.system.StructStat;
import android.os.ParcelFileDescriptor;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/** Android lstat adapter. Paths remain below the app's own files directory. */
public final class StorageFiles implements StorageAudit.Fs {
    private final File root;
    private final StorageAudit.Stat rootIdentity;
    private final List<String> rootAliases;
    private final File cache;
    private final StorageAudit.Stat cacheIdentity;
    public StorageFiles(File filesDirectory) throws IOException {
        this(filesDirectory,new File(filesDirectory.getParentFile(),"cache"));
    }
    public StorageFiles(File filesDirectory,File cacheDirectory) throws IOException {
        // Android's trusted Context.getFilesDir() may contain /data/user/0 aliases.
        // Canonicalize that API-provided root once; individual inventory paths never resolve links.
        root=filesDirectory.getCanonicalFile();
        rootAliases=Collections.unmodifiableList(new ArrayList<>(new LinkedHashSet<>(Arrays.asList(root.getPath(),filesDirectory.getAbsolutePath()))));
        rootIdentity=lstat(root);if(rootIdentity==null||rootIdentity.kind!=StorageAudit.Kind.DIRECTORY)throw new IOException("App files directory is unavailable");
        cache=cacheDirectory.getCanonicalFile();
        if(!cache.getParentFile().equals(root.getParentFile())||!cache.getName().equals("cache"))throw new IOException("Storage scratch cache is outside the application");
        cacheIdentity=lstat(cache);if(cacheIdentity==null||cacheIdentity.kind!=StorageAudit.Kind.DIRECTORY)throw new IOException("App cache directory is unavailable");
        discardOwnedJournals();
    }
    private File file(String relative) throws IOException {
        if(relative==null||relative.startsWith("/")||relative.indexOf('\0')>=0)throw new IOException("Unsafe storage path");
        if(relative.isEmpty())return root;
        String[] parts=relative.split("/",-1);
        File current=root;
        if(!rootIdentity.sameDirectory(lstat(root)))throw new IOException("App files root changed");
        for(int i=0;i<parts.length;i++) {
            String part=parts[i];if(part.isEmpty()||part.equals(".")||part.equals(".."))throw new IOException("Unsafe storage component");
            current=new File(current,part);
            if(i<parts.length-1) {
                StorageAudit.Stat stat=lstat(current);
                if(stat==null)return currentPath(parts);
                if(stat.kind!=StorageAudit.Kind.DIRECTORY)throw new IOException("Storage parent is linked or not a directory");
            }
        }
        return current;
    }
    private File currentPath(String[] parts){File result=root;for(String part:parts)result=new File(result,part);return result;}
    private static StorageAudit.Stat lstat(File file) throws IOException {
        try {
            return stat(Os.lstat(file.getPath()));
        } catch(ErrnoException e){if(e.errno==OsConstants.ENOENT)return null;throw new IOException("Cannot inspect private storage",e);}
    }
    private static StorageAudit.Stat stat(StructStat s) {
        StorageAudit.Kind kind;
        if(OsConstants.S_ISREG(s.st_mode))kind=StorageAudit.Kind.FILE;
        else if(OsConstants.S_ISDIR(s.st_mode))kind=StorageAudit.Kind.DIRECTORY;
        else if(OsConstants.S_ISLNK(s.st_mode))kind=StorageAudit.Kind.SYMLINK;else kind=StorageAudit.Kind.OTHER;
        return new StorageAudit.Stat(kind,s.st_dev,s.st_ino,s.st_nlink,s.st_size,s.st_blocks,s.st_mtime,s.st_ctime);
    }
    @Override public StorageAudit.Stat stat(String relative) throws IOException {return lstat(file(relative));}
    @Override public String rootPath(){return root.getPath();}
    @Override public List<String> rootAliases(){return rootAliases;}
    @Override public String readLink(String relative) throws IOException {
        File target=file(relative);StorageAudit.Stat before=lstat(target);
        if(before==null||before.kind!=StorageAudit.Kind.SYMLINK)throw new IOException("Storage link is unavailable");
        try {
            String value=Os.readlink(target.getPath());
            if(!before.same(lstat(file(relative))))throw new IOException("Storage link changed while reading");
            return value;
        } catch(ErrnoException e){throw new IOException("Cannot inspect private storage link",e);}
    }
    @Override public List<String> list(String relative) throws IOException {
        List<String> names=new ArrayList<>();
        visitDirectory(relative,name->{
            // Policy identification needs only small top-level lists. Full inventory uses the iterator directly.
            if(names.size()>=50000)throw new IOException("Storage identity directory entry limit reached");
            names.add(name);
        });
        return names;
    }
    @Override public void visitDirectory(String relative,StorageAudit.NameVisitor visitor) throws IOException {
        File directory=file(relative);StorageAudit.Stat before=lstat(directory);
        if(before==null||before.kind!=StorageAudit.Kind.DIRECTORY)throw new IOException("Cannot list a linked storage directory");
        FileDescriptor descriptor=null;int count=0;
        try {
            descriptor=Os.open(directory.getPath(),OsConstants.O_RDONLY|OsConstants.O_NOFOLLOW|OsConstants.O_CLOEXEC|OsConstants.O_NONBLOCK,0);
            if(!before.same(stat(Os.fstat(descriptor))))throw new IOException("Opened inventory directory changed");
            try(ParcelFileDescriptor held=ParcelFileDescriptor.dup(descriptor);
                    DirectoryStream<Path> stream=Files.newDirectoryStream(Paths.get("/proc/self/fd/"+held.getFd()))) {
                for(Path member:stream) {
                    if(++count>2000000)throw new IOException("Directory entry limit reached");
                    if((count&1023)==0) {
                        Runtime vm=Runtime.getRuntime();
                        if(vm.maxMemory()-(vm.totalMemory()-vm.freeMemory())<8L*1024*1024) {
                            vm.gc();if(vm.maxMemory()-(vm.totalMemory()-vm.freeMemory())<8L*1024*1024)
                                throw new IOException("Directory iteration reached its memory budget");
                        }
                    }
                    visitor.visit(member.getFileName().toString());
                }
            }
            if(!before.same(lstat(file(relative))))throw new IOException("Storage directory changed while listing");
        } catch(ErrnoException e){throw new IOException("Cannot open inventory directory without following links",e);}
        finally{if(descriptor!=null)try{Os.close(descriptor);}catch(ErrnoException ignored){}}
    }
    private File journals(boolean create) throws IOException {
        if(!cacheIdentity.sameDirectory(lstat(cache)))throw new IOException("App storage scratch cache changed");
        File tools=new File(cache,"storage-tools"),directory=new File(tools,"journals");
        if(create) {
            if(lstat(tools)==null&&!tools.mkdir())throw new IOException("Cannot create storage scratch directory");
            if(lstat(tools)==null||lstat(tools).kind!=StorageAudit.Kind.DIRECTORY)throw new IOException("Storage scratch parent is linked");
            if(lstat(directory)==null&&!directory.mkdir())throw new IOException("Cannot create cleanup journal directory");
        }
        StorageAudit.Stat parent=lstat(tools);if(parent==null)return null;
        if(parent.kind!=StorageAudit.Kind.DIRECTORY)throw new IOException("Storage scratch parent is linked");
        StorageAudit.Stat identity=lstat(directory);if(identity==null)return null;
        if(identity.kind!=StorageAudit.Kind.DIRECTORY)throw new IOException("Storage journal directory is linked");
        return directory;
    }
    /** The caller holds the idle storage lock; only abandoned files owned by this tool are removed. */
    private void discardOwnedJournals() throws IOException {
        File directory=journals(false);if(directory==null)return;
        StorageAudit.Stat before=lstat(directory);int count=0;FileDescriptor descriptor=null;
        try {
            descriptor=Os.open(directory.getPath(),OsConstants.O_RDONLY|OsConstants.O_NOFOLLOW|OsConstants.O_CLOEXEC|OsConstants.O_NONBLOCK,0);
            if(!before.sameDirectory(stat(Os.fstat(descriptor))))throw new IOException("Opened journal recovery directory changed");
            try(ParcelFileDescriptor held=ParcelFileDescriptor.dup(descriptor);
                    DirectoryStream<Path> stream=Files.newDirectoryStream(Paths.get("/proc/self/fd/"+held.getFd()))) {
                for(Path entry:stream) {
                    if(++count>1024)throw new IOException("Storage journal recovery entry limit reached");
                    String name=entry.getFileName().toString();
                    if(!name.matches("coh-storage-[0-9a-f-]{36}\\.journal"))continue;
                    StorageAudit.Stat stat=lstat(entry.toFile());
                    if(stat==null||stat.kind!=StorageAudit.Kind.FILE||stat.links!=1)continue;
                    if(!before.sameDirectory(lstat(journals(false))))throw new IOException("Storage journal directory changed during recovery");
                    Files.delete(entry);
                }
            }
        } catch(ErrnoException failure){throw new IOException("Cannot anchor private journal recovery",failure);}
        finally{if(descriptor!=null)try{Os.close(descriptor);}catch(ErrnoException ignored){}}
    }
    @Override public File cleanupJournal() throws IOException {
        File directory=journals(true),target=new File(directory,"coh-storage-"+UUID.randomUUID()+".journal");FileDescriptor descriptor=null;
        try {
            descriptor=Os.open(target.getPath(),OsConstants.O_WRONLY|OsConstants.O_CREAT|OsConstants.O_EXCL|OsConstants.O_NOFOLLOW|OsConstants.O_CLOEXEC,0600);
            StorageAudit.Stat stat=stat(Os.fstat(descriptor));
            if(stat.kind!=StorageAudit.Kind.FILE||stat.links!=1)throw new IOException("Cleanup journal is not a private file");
            return target;
        } catch(ErrnoException e){throw new IOException("Cannot create bounded private cleanup journal",e);}
        finally{if(descriptor!=null)try{Os.close(descriptor);}catch(ErrnoException ignored){}}
    }
    @Override public byte[] read(String relative,int limit) throws IOException {
        File target=file(relative);StorageAudit.Stat before=lstat(target);
        if(before==null||before.kind!=StorageAudit.Kind.FILE||before.links!=1||before.size>limit)throw new IOException("Storage identity file is linked, missing or too large");
        FileDescriptor fd;
        try{fd=Os.open(target.getPath(),OsConstants.O_RDONLY|OsConstants.O_NOFOLLOW|OsConstants.O_CLOEXEC|OsConstants.O_NONBLOCK,0);}
        catch(ErrnoException e){throw new IOException("Cannot read private storage identity",e);}
        try(InputStream in=new FileInputStream(fd)) {
            try{if(!before.same(stat(Os.fstat(fd))))throw new IOException("Opened storage identity changed");}
            catch(ErrnoException e){throw new IOException("Cannot verify opened identity",e);}
            byte[] value=bounded(in,limit);
            if(!before.same(lstat(file(relative))))throw new IOException("Storage identity changed while reading");
            if(relative.equals("client/latest-report.txt")) {
                String path=new String(value,StandardCharsets.UTF_8).trim();
                if(path.startsWith("/")) {
                    boolean owned=false;for(String alias:rootAliases)if(path.startsWith(alias+"/client/reports/"))owned=true;
                    if(!owned)throw new IOException("Latest report pointer is outside app storage");
                }
            }
            return value;
        }
    }
    @Override public Map<String,Object> json(byte[] bytes) throws IOException {
        try{return object(new JSONObject(new String(bytes,StandardCharsets.UTF_8)));}
        catch(Exception e){throw new IOException("Storage identity JSON is unreadable",e);}
    }
    private static Map<String,Object> object(JSONObject value) throws Exception {
        Map<String,Object> result=new LinkedHashMap<>();Iterator<String> keys=value.keys();
        while(keys.hasNext()){String key=keys.next();result.put(key,convert(value.get(key)));}return result;
    }
    private static Object convert(Object value) throws Exception {
        if(value==JSONObject.NULL)return null;if(value instanceof JSONObject)return object((JSONObject)value);
        if(value instanceof JSONArray){List<Object> list=new ArrayList<>();for(int i=0;i<((JSONArray)value).length();i++)list.add(convert(((JSONArray)value).get(i)));return list;}return value;
    }
    @Override public Map<String,Object> reportIdentity(String relative,int limit) throws IOException {
        File target=file(relative);StorageAudit.Stat before=lstat(target);
        if(before==null||before.kind!=StorageAudit.Kind.FILE||before.links!=1)throw new IOException("Report is not an owned regular archive");
        FileDescriptor descriptor;
        try{descriptor=Os.open(target.getPath(),OsConstants.O_RDONLY|OsConstants.O_NOFOLLOW|OsConstants.O_CLOEXEC|OsConstants.O_NONBLOCK,0);}
        catch(ErrnoException e){throw new IOException("Cannot open completed report without following links",e);}
        try(InputStream input=new FileInputStream(descriptor);ZipInputStream archive=new ZipInputStream(input)) {
            try{if(!before.same(stat(Os.fstat(descriptor))))throw new IOException("Opened report changed");}
            catch(ErrnoException e){throw new IOException("Cannot verify opened report",e);}
            // All interactive report publishers put this identity first. Other archives are protected.
            ZipEntry report=archive.getNextEntry();
            if(report==null||!report.getName().equals("android-client-report.json")||report.isDirectory()||report.getSize()>limit)throw new IOException("Completed client report identity is unavailable");
            Map<String,Object> result=json(bounded(archive,limit));
            if(!before.same(lstat(file(relative))))throw new IOException("Completed report changed while inspecting");
            return result;
        }
    }
    private static byte[] bounded(InputStream in,int limit) throws IOException {
        ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int count;
        while((count=in.read(buffer))!=-1){if(out.size()+count>limit)throw new IOException("Storage metadata exceeded its bound");out.write(buffer,0,count);}return out.toByteArray();
    }
    @Override public void unlink(String relative) throws IOException {
        if(relative.isEmpty())throw new IOException("Cannot remove app storage root");File target=file(relative);
        StorageAudit.Stat stat=lstat(target);if(stat==null||(stat.kind!=StorageAudit.Kind.FILE&&stat.kind!=StorageAudit.Kind.SYMLINK))throw new IOException("Cleanup member is not a regular file or link");
        Files.delete(target.toPath());
    }
    @Override public void rmdir(String relative) throws IOException {
        if(relative.isEmpty())throw new IOException("Cannot remove app storage root");File target=file(relative);
        StorageAudit.Stat stat=lstat(target);if(stat==null||stat.kind!=StorageAudit.Kind.DIRECTORY)throw new IOException("Cleanup member is not a directory");
        Files.delete(target.toPath());
    }
    @Override public void remove(String relative,StorageAudit.Stat expected,StorageAudit.Stat expectedParent) throws IOException {
        if(relative.isEmpty())throw new IOException("Cannot remove app storage root");
        File target=file(relative),parent=target.getParentFile();FileDescriptor descriptor=null;
        try {
            descriptor=Os.open(parent.getPath(),OsConstants.O_RDONLY|OsConstants.O_NOFOLLOW|OsConstants.O_CLOEXEC|OsConstants.O_NONBLOCK,0);
            StructStat directory=Os.fstat(descriptor);
            if(!OsConstants.S_ISDIR(directory.st_mode)||directory.st_dev!=expectedParent.device||directory.st_ino!=expectedParent.inode)
                throw new IOException("Cleanup parent changed before opening");
            try(ParcelFileDescriptor held=ParcelFileDescriptor.dup(descriptor)) {
                File anchored=new File("/proc/self/fd/"+held.getFd(),target.getName());StorageAudit.Stat actual=lstat(anchored);
                if(!expected.same(actual))throw new IOException("Cleanup entry changed before removal");
                // The held descriptor anchors the verified parent even if a path ancestor is renamed.
                // Files.delete unlinks a symlink itself, and removes directories only when empty.
                Files.delete(anchored.toPath());
            }
        } catch(ErrnoException e){throw new IOException("Cannot anchor private cleanup parent",e);}
        finally{if(descriptor!=null)try{Os.close(descriptor);}catch(ErrnoException ignored){}}
    }
    @Override public long nowMillis(){return System.currentTimeMillis();}
}
