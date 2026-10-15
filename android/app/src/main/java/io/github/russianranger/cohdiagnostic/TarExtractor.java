package io.github.russianranger.cohdiagnostic;

/* Adapted from Russianranger/lsb-android at
 * 228fe927fd8668cd0cfcb5a7084882cd924557c0, app/src/main/java/
 * io/github/russianranger/lsb/TarExtractor.java.
 * COH changes: require fresh staging; reject symlink ancestors and duplicate
 * files; copy archive hardlinks for Android compatibility; verify the complete
 * gzip/tar trailer; check cancellation during reads and deferred links.
 */

import android.system.Os;
import java.io.*;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.channels.Channels;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributeView;
import java.nio.file.attribute.BasicFileAttributes;
import java.nio.file.attribute.FileTime;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.zip.GZIPInputStream;

/** Extracts GNU/USTAR/PAX runtimes; all links are deferred until regular files finish. */
final class TarExtractor {
    private static final int MAX_PAX_BYTES=1024*1024, MAX_PATH_BYTES=16384;
    private static final long MAX_MEMBER_BYTES=8L*1024*1024*1024, MAX_TOTAL_BYTES=10L*1024*1024*1024;
    private static final class ArchiveLink {
        final String name,target;
        final char type;
        final FileTime modified;
        ArchiveLink(String name,String target,char type,FileTime modified) {
            this.name=name;this.target=target;this.type=type;this.modified=modified;
        }
    }
    interface Progress {void update(int count);}
    private static void cancelled() throws InterruptedIOException {
        if(Thread.currentThread().isInterrupted())throw new InterruptedIOException("Runtime extraction cancelled");
    }
    private static void checked(SetupMemoryGuard control) throws IOException {
        cancelled();if(control!=null)control.beforeIo();
    }
    private static InputStream source(InputStream in,SetupMemoryGuard control) {
        if(control==null)return in;
        return new FilterInputStream(in) {
            @Override public int read() throws IOException {
                checked(control);int value=in.read();if(value>=0)control.read(1);return value;
            }
            @Override public int read(byte[] bytes,int at,int length) throws IOException {
                checked(control);int count=in.read(bytes,at,length);if(count>0)control.read(count);return count;
            }
        };
    }
    private static void noSymlinkAncestors(Path path) throws IOException {
        Path current=path.getRoot();
        for(Path part:path) {
            current=current.resolve(part);
            if(Files.isSymbolicLink(current))throw new IOException("Symlink in runtime extraction path");
            if(Files.exists(current,LinkOption.NOFOLLOW_LINKS)&&!Files.isDirectory(current,LinkOption.NOFOLLOW_LINKS))
                throw new IOException("Non-directory runtime extraction ancestor");
        }
    }
    private static File staging(File root) throws IOException {
        cancelled();
        Path path=root.toPath().toAbsolutePath().normalize();
        noSymlinkAncestors(path);
        Files.createDirectories(path);
        try(DirectoryStream<Path> entries=Files.newDirectoryStream(path)) {
            if(entries.iterator().hasNext())throw new IOException("Runtime extraction requires an empty staging directory");
        }
        return path.toFile();
    }
    static File path(File root,String name) throws IOException {
        if(name.isEmpty()||name.startsWith("/")||name.contains("\\")||name.indexOf('\0')>=0)
            throw new IOException("Unsafe archive path");
        for(String component:name.split("/"))if(component.equals(".."))throw new IOException("Unsafe archive path");
        Path base=root.toPath().toAbsolutePath().normalize();
        Path target=base.resolve(name).normalize();
        if(!target.startsWith(base))throw new IOException("Archive path escapes runtime");
        noSymlinkAncestors(target.equals(base)?base:target.getParent());
        if(Files.isSymbolicLink(target))throw new IOException("Symlink in runtime extraction path");
        return target.toFile();
    }
    private static void parents(File dest) throws IOException {
        noSymlinkAncestors(dest.toPath().getParent());
        Files.createDirectories(dest.toPath().getParent());
    }
    private static FileTime memberTime(byte[] header,String paxTime) throws IOException {
        try {
            if(paxTime!=null) {
                // PAX times are decimal seconds. Bound both parsing work and
                // the representable nanosecond value; do not accept exponents.
                if(paxTime.length()>64||!paxTime.matches("-?[0-9]+(?:\\.[0-9]+)?"))
                    throw new IOException("Invalid PAX modification time");
                long nanos=new BigDecimal(paxTime).movePointRight(9)
                        .setScale(0,RoundingMode.FLOOR).longValueExact();
                // Java/Android metadata providers may silently clamp dates
                // before the Unix epoch. Refuse them instead of changing them.
                if(nanos<0)throw new IOException("Unsupported pre-epoch PAX modification time");
                return FileTime.from(nanos,TimeUnit.NANOSECONDS);
            }
            long seconds=octal(header,136,12);
            if(seconds<0)throw new IOException("Invalid tar modification time");
            return FileTime.from(Math.multiplyExact(seconds,1000000000L),TimeUnit.NANOSECONDS);
        } catch(ArithmeticException|NumberFormatException e) {
            throw new IOException("Archive modification time exceeds limits",e);
        }
    }
    private static void setModifiedTime(Path path,FileTime time,boolean directory) throws IOException {
        cancelled();
        noSymlinkAncestors(path.getParent());
        BasicFileAttributes attributes=Files.readAttributes(path,BasicFileAttributes.class,LinkOption.NOFOLLOW_LINKS);
        if(directory?!attributes.isDirectory():!attributes.isRegularFile())
            throw new IOException("Runtime metadata target changed type");
        BasicFileAttributeView view=Files.getFileAttributeView(path,BasicFileAttributeView.class,LinkOption.NOFOLLOW_LINKS);
        if(view==null)throw new IOException("Runtime modification times are unsupported");
        // Android may retain only microseconds. Wine uses whole INF seconds;
        // provider precision must not be confused with a new extraction date.
        view.setTimes(time,null,null);
    }
    static void extract(File archive,File root,Progress progress) throws Exception {
        extract(archive,root,progress,null);
    }
    static void extract(File archive,File root,Progress progress,SetupMemoryGuard control) throws Exception {
        if(control!=null)control.checkpoint();
        root=staging(root);
        List<ArchiveLink> links=new ArrayList<>();
        Map<Path,FileTime> directoryTimes=new LinkedHashMap<>();
        long total=0; int count=0; String longName=null,longLink=null;
        Map<String,String> globalPax=new HashMap<>(), localPax=new HashMap<>();
        boolean pendingPax=false;
        // Reuse the copy buffer for every regular member. The runtime contains
        // thousands of small files; allocating one MiB for each file previously
        // put several GiB of short-lived arrays through the Android heap.
        byte[] copyBuffer=new byte[65536];
        // Buffer compressed source bytes too: the default gzip source buffer is
        // only 512 bytes. Both source and inflater storage remain bounded.
        try(InputStream raw=new FileInputStream(archive);
                InputStream in=new GZIPInputStream(new BufferedInputStream(source(raw,control),65536),65536)) {
            byte[] header=new byte[512];
            while(true) {
                checked(control);
                full(in,header,512,control);
                boolean zero=true; for(byte b:header)if(b!=0){zero=false;break;}
                if(zero) {
                    if(pendingPax||longName!=null||longLink!=null)throw new IOException("Missing member after extended tar header");
                    // Require a complete two-block terminator, then consume padding
                    // through gzip EOF so its CRC/trailer are verified as well.
                    full(in,header,512,control);
                    for(byte b:header)if(b!=0)throw new IOException("Invalid tar terminator");
                    byte[] trailer=new byte[8192];int n;
                    while((n=in.read(trailer))!=-1) {
                        if(control!=null)control.read(n);
                        checked(control);
                        for(int i=0;i<n;i++)if(trailer[i]!=0)throw new IOException("Unexpected data after tar terminator");
                    }
                    break;
                }
                long checksum=octal(header,148,8), actual=0;
                for(int i=0;i<512;i++)actual+=(i>=148&&i<156)?32:header[i]&255;
                if(checksum!=actual)throw new IOException("Corrupt tar header");
                long size=octal(header,124,12); int mode=(int)octal(header,100,8); char type=(char)header[156];
                String name=text(header,0,100), prefix=text(header,345,155), link=text(header,157,100);
                if(!prefix.isEmpty())name=prefix+"/"+name;
                boolean metadata=type=='x'||type=='g'||type=='L'||type=='K';
                FileTime modified=null;
                if(!metadata) {
                    if(longName!=null){name=longName;longName=null;} if(longLink!=null){link=longLink;longLink=null;}
                    String value=paxValue(localPax,globalPax,"path"); if(value!=null)name=value;
                    value=paxValue(localPax,globalPax,"linkpath"); if(value!=null)link=value;
                    value=paxValue(localPax,globalPax,"size"); if(value!=null)size=paxSize(value);
                    value=paxValue(localPax,globalPax,"hdrcharset");
                    if(value!=null&&!value.equals("ISO-IR 10646 2000 UTF-8"))throw new IOException("Unsupported PAX header encoding");
                    modified=memberTime(header,paxValue(localPax,globalPax,"mtime"));
                    localPax.clear();pendingPax=false;
                }
                if(size<0||size>MAX_MEMBER_BYTES || (total+=size)>MAX_TOTAL_BYTES || ++count>400000)throw new IOException("Runtime archive exceeds limits");
                if(type=='x'||type=='g') {
                    if(size>MAX_PAX_BYTES)throw new IOException("PAX header exceeds limits");
                    byte[] data=new byte[(int)size]; full(in,data,data.length,control);
                    Map<String,String> values=pax(data);
                    if(type=='x'){localPax.putAll(values);pendingPax=true;}
                    else for(Map.Entry<String,String> entry:values.entrySet()) {
                        if(entry.getValue().isEmpty())globalPax.remove(entry.getKey());
                        else globalPax.put(entry.getKey(),entry.getValue());
                    }
                } else if(type=='L'||type=='K') {
                    if(size>MAX_PATH_BYTES)throw new IOException("Archive path is too long");
                    byte[] data=new byte[(int)size]; full(in,data,data.length,control);
                    String extended=new String(data,StandardCharsets.UTF_8).replace("\0","");
                    if(type=='L')longName=extended;else longLink=extended;
                } else {
                    File dest=path(root,name);
                    if(type=='0'||type=='\0') {
                        if(size>root.getUsableSpace()-128L*1024*1024)throw new IOException("Not enough storage to unpack runtime");
                        parents(dest);
                        try(FileChannel channel=FileChannel.open(dest.toPath(),StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS);
                                OutputStream out=Channels.newOutputStream(channel)) {
                            SetupMemoryGuard.Sync sync=()->channel.force(false);
                            try {transfer(in,out,size,copyBuffer,control,sync);}
                            finally {if(control!=null){sync.sync();control.synced();}}
                        }
                        Os.chmod(dest.getPath(),(mode&0111)!=0?0755:0644);
                        setModifiedTime(dest.toPath(),modified,false);
                    } else if(type=='5') {
                        if(size!=0)throw new IOException("Malformed directory entry");
                        checked(control);Files.createDirectories(dest.toPath());
                        directoryTimes.put(dest.toPath(),modified);
                    }
                    else if(type=='1'||type=='2') {if(size!=0)throw new IOException("Malformed link");links.add(new ArchiveLink(name,link,type,modified));}
                    else throw new IOException("Unsupported runtime tar member; use the release runtime archive (type "+type+")");
                }
                skip(in,(512-size%512)%512,control); if(count%500==0)progress.update(count);
            }
        }
        // All links are deferred: archive data can never write through a symlink.
        // Copy hardlink bytes rather than creating filesystem hardlinks. This also
        // avoids Android hardlink restrictions and preserves independent files.
        for(ArchiveLink link:links)if(link.type=='1') {
            checked(control);
            File dest=path(root,link.name),source=path(root,link.target);parents(dest);
            if(!Files.isRegularFile(source.toPath(),LinkOption.NOFOLLOW_LINKS)
                    ||Files.exists(dest.toPath(),LinkOption.NOFOLLOW_LINKS))throw new IOException("Invalid hardlink");
            long size=Files.size(source.toPath());
            if((total+=size)>MAX_TOTAL_BYTES)throw new IOException("Runtime archive copies exceed limits");
            if(size>root.getUsableSpace()-128L*1024*1024)throw new IOException("Not enough storage to copy runtime hardlink");
            // FileChannel transfer is bounded and observes the setup token;
            // Files.copy can otherwise run a large hardlink copy until EOF.
            try(InputStream in=Files.newInputStream(source.toPath(),LinkOption.NOFOLLOW_LINKS);
                    FileChannel channel=FileChannel.open(dest.toPath(),StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS);
                    OutputStream out=Channels.newOutputStream(channel)) {
                SetupMemoryGuard.Sync sync=()->channel.force(false);
                try {
                    transfer(in,out,size,copyBuffer,control,sync);
                    if(in.read()!=-1)throw new IOException("Runtime hardlink source grew");
                } finally {if(control!=null){sync.sync();control.synced();}}
            }
            checked(control);
            Os.chmod(dest.getPath(),Files.isExecutable(source.toPath())?0755:0644);
            setModifiedTime(dest.toPath(),link.modified,false);
        }
        for(ArchiveLink link:links)if(link.type=='2') {
            checked(control);
            File dest=path(root,link.name);parents(dest);
            // Keep guest absolute targets absolute; PRoot resolves them in its
            // rootfs. Never follow these links in the Android installer.
            if(link.target.isEmpty()||link.target.indexOf('\0')>=0||Files.exists(dest.toPath(),LinkOption.NOFOLLOW_LINKS))throw new IOException("Invalid symlink");
            Os.symlink(link.target,dest.getPath());
        }
        // Children and deferred links change directory dates. Apply explicit
        // archive directory times last, deepest first, without following links.
        checked(control);List<Path> directories=new ArrayList<>(directoryTimes.keySet());
        directories.sort((a,b)->Integer.compare(b.getNameCount(),a.getNameCount()));
        for(Path directory:directories){checked(control);setModifiedTime(directory,directoryTimes.get(directory),true);}
        checked(control);
        progress.update(count);
    }
    // A local empty value suppresses a global override for this member; a global
    // empty value removes that override. Keep only fields that affect extraction.
    private static String paxValue(Map<String,String> local,Map<String,String> global,String key) {
        String value=local.containsKey(key)?local.get(key):global.get(key);
        return value==null||value.isEmpty()?null:value;
    }
    private static long paxSize(String value)throws IOException {
        long size=0;
        for(int i=0;i<value.length();i++) {
            char c=value.charAt(i);
            if(c<'0'||c>'9'||size>(MAX_MEMBER_BYTES-(c-'0'))/10)throw new IOException("Invalid or oversized PAX size");
            size=size*10+c-'0';
        }
        return size;
    }
    private static String utf8(byte[] data,int start,int length)throws IOException {
        try{return StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(data,start,length)).toString();}
        catch(CharacterCodingException e){throw new IOException("Invalid UTF-8 in PAX header",e);}
    }
    private static Map<String,String> pax(byte[] data)throws IOException {
        Map<String,String> values=new HashMap<>();
        int offset=0;
        while(offset<data.length) {
            int space=offset, length=0;
            while(space<data.length&&data[space]!=' ') {
                int digit=data[space]-'0';
                if(digit<0||digit>9||length>(MAX_PAX_BYTES-digit)/10)throw new IOException("Invalid PAX record length");
                length=length*10+digit;space++;
            }
            if(space==offset||length<space-offset+4||length>data.length-offset)throw new IOException("Truncated or malformed PAX record");
            int end=offset+length, equals=space+1;
            if(data[end-1]!='\n')throw new IOException("Malformed PAX record terminator");
            while(equals<end-1&&data[equals]!='=') {
                if(data[equals]<33||data[equals]>126)throw new IOException("Invalid PAX keyword");
                equals++;
            }
            if(equals==space+1||equals>=end-1)throw new IOException("Malformed PAX key/value");
            String key=utf8(data,space+1,equals-space-1), value=utf8(data,equals+1,end-equals-2);
            // These extensions alter the file's data layout, unlike metadata such
            // as timestamps, ownership and xattrs. Never extract them as plain data.
            if(key.startsWith("GNU.sparse.")||key.startsWith("GNU.volume.")||key.equals("SCHILY.realsize")||key.equals("SCHILY.filetype"))throw new IOException("Unsupported sparse or multivolume runtime archive");
            if(key.equals("path")||key.equals("linkpath")||key.equals("size")||key.equals("hdrcharset")||key.equals("mtime")) {
                if(value.indexOf('\0')>=0)throw new IOException("Invalid PAX value");
                if((key.equals("path")||key.equals("linkpath"))&&end-equals-2>MAX_PATH_BYTES)throw new IOException("Archive path is too long");
                values.put(key,value);
            }
            offset=end;
        }
        return values;
    }
    static void transfer(InputStream in,OutputStream out,long size)throws IOException {transfer(in,out,size,new byte[65536],null,null);}
    static void transfer(InputStream in,FileOutputStream out,long size,SetupMemoryGuard control)throws IOException {
        SetupMemoryGuard.Sync sync=()->out.getFD().sync();
        try {transfer(in,out,size,new byte[65536],control,sync);}
        finally {if(control!=null){sync.sync();control.synced();}}
    }
    private static void transfer(InputStream in,OutputStream out,long size,byte[] buffer,SetupMemoryGuard control,SetupMemoryGuard.Sync sync)throws IOException {
        while(size>0) {
            checked(control);
            int n=in.read(buffer,0,(int)Math.min(size,buffer.length));
            if(n<0)throw new EOFException("Truncated runtime archive");
            if(control!=null)control.read(n);
            out.write(buffer,0,n);size-=n;
            if(control!=null)control.written(n,sync);
        }
    }
    static void full(InputStream in,byte[] b,int length)throws IOException {full(in,b,length,null);}
    private static void full(InputStream in,byte[] b,int length,SetupMemoryGuard control)throws IOException {
        int offset=0;while(offset<length){checked(control);int n=in.read(b,offset,Math.min(65536,length-offset));if(n<0)throw new EOFException("Truncated runtime archive");offset+=n;if(control!=null)control.read(n);}
    }
    static void skip(InputStream in,long n)throws IOException {skip(in,n,null);}
    private static void skip(InputStream in,long n,SetupMemoryGuard control)throws IOException {
        while(n-->0){checked(control);if(in.read()<0)throw new EOFException("Truncated runtime archive padding");if(control!=null)control.read(1);}
    }
    static String text(byte[] b,int at,int length){int end=at;while(end<at+length&&b[end]!=0)end++;return new String(b,at,end-at,StandardCharsets.UTF_8);}
    static long octal(byte[] b,int at,int length)throws IOException {String s=text(b,at,length).trim();try{return s.isEmpty()?0:Long.parseLong(s,8);}catch(NumberFormatException e){throw new IOException("Invalid tar size");}}
    static void remove(File file)throws IOException {
        remove(file,null);
    }
    static void remove(File file,SetupMemoryGuard control)throws IOException {
        if(!Files.exists(file.toPath(),LinkOption.NOFOLLOW_LINKS))return;
        // The platform walker uses a streaming DirectoryStream and does not
        // follow symbolic links. Neither wide directories nor cleanup under
        // pressure allocate an array containing the complete child inventory.
        final long[] entries={0};
        Files.walkFileTree(file.toPath(),EnumSet.noneOf(FileVisitOption.class),256,new SimpleFileVisitor<Path>() {
            private void visit() throws IOException {
                if(++entries[0]>1000000)throw new IOException("Runtime staging cleanup exceeds entry limit");
                if(control!=null)checked(control);
            }
            @Override public FileVisitResult preVisitDirectory(Path directory,BasicFileAttributes attributes)throws IOException {
                visit();return FileVisitResult.CONTINUE;
            }
            @Override public FileVisitResult visitFile(Path path,BasicFileAttributes attributes)throws IOException {
                visit();Files.delete(path);return FileVisitResult.CONTINUE;
            }
            @Override public FileVisitResult postVisitDirectory(Path directory,IOException failure)throws IOException {
                if(failure!=null)throw failure;if(control!=null)checked(control);Files.delete(directory);return FileVisitResult.CONTINUE;
            }
        });
    }
}
