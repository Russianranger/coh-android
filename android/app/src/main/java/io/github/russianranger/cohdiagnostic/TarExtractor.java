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
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.GZIPInputStream;

/** Extracts GNU/USTAR/PAX runtimes; all links are deferred until regular files finish. */
final class TarExtractor {
    private static final int MAX_PAX_BYTES=1024*1024, MAX_PATH_BYTES=16384;
    private static final long MAX_MEMBER_BYTES=8L*1024*1024*1024, MAX_TOTAL_BYTES=10L*1024*1024*1024;
    interface Progress {void update(int count);}
    private static void cancelled() throws InterruptedIOException {
        if(Thread.currentThread().isInterrupted())throw new InterruptedIOException("Runtime extraction cancelled");
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
    static void extract(File archive,File root,Progress progress) throws Exception {
        root=staging(root);
        List<String[]> links=new ArrayList<>(); long total=0; int count=0; String longName=null,longLink=null;
        Map<String,String> globalPax=new HashMap<>(), localPax=new HashMap<>();
        boolean pendingPax=false;
        // Reuse the copy buffer for every regular member. The runtime contains
        // thousands of small files; allocating one MiB for each file previously
        // put several GiB of short-lived arrays through the Android heap.
        byte[] copyBuffer=new byte[65536];
        try(InputStream in=new BufferedInputStream(new GZIPInputStream(new FileInputStream(archive)),1024*1024)) {
            byte[] header=new byte[512];
            while(true) {
                if(Thread.currentThread().isInterrupted())throw new InterruptedIOException("Runtime extraction cancelled");
                full(in,header,512);
                boolean zero=true; for(byte b:header)if(b!=0){zero=false;break;}
                if(zero) {
                    if(pendingPax||longName!=null||longLink!=null)throw new IOException("Missing member after extended tar header");
                    // Require a complete two-block terminator, then consume padding
                    // through gzip EOF so its CRC/trailer are verified as well.
                    full(in,header,512);
                    for(byte b:header)if(b!=0)throw new IOException("Invalid tar terminator");
                    byte[] trailer=new byte[8192];int n;
                    while((n=in.read(trailer))!=-1) {
                        cancelled();
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
                if(!metadata) {
                    if(longName!=null){name=longName;longName=null;} if(longLink!=null){link=longLink;longLink=null;}
                    String value=paxValue(localPax,globalPax,"path"); if(value!=null)name=value;
                    value=paxValue(localPax,globalPax,"linkpath"); if(value!=null)link=value;
                    value=paxValue(localPax,globalPax,"size"); if(value!=null)size=paxSize(value);
                    value=paxValue(localPax,globalPax,"hdrcharset");
                    if(value!=null&&!value.equals("ISO-IR 10646 2000 UTF-8"))throw new IOException("Unsupported PAX header encoding");
                    localPax.clear();pendingPax=false;
                }
                if(size<0||size>MAX_MEMBER_BYTES || (total+=size)>MAX_TOTAL_BYTES || ++count>400000)throw new IOException("Runtime archive exceeds limits");
                if(type=='x'||type=='g') {
                    if(size>MAX_PAX_BYTES)throw new IOException("PAX header exceeds limits");
                    byte[] data=new byte[(int)size]; full(in,data,data.length);
                    Map<String,String> values=pax(data);
                    if(type=='x'){localPax.putAll(values);pendingPax=true;}
                    else for(Map.Entry<String,String> entry:values.entrySet()) {
                        if(entry.getValue().isEmpty())globalPax.remove(entry.getKey());
                        else globalPax.put(entry.getKey(),entry.getValue());
                    }
                } else if(type=='L'||type=='K') {
                    if(size>MAX_PATH_BYTES)throw new IOException("Archive path is too long");
                    byte[] data=new byte[(int)size]; full(in,data,data.length);
                    String extended=new String(data,StandardCharsets.UTF_8).replace("\0","");
                    if(type=='L')longName=extended;else longLink=extended;
                } else {
                    File dest=path(root,name);
                    if(type=='0'||type=='\0') {
                        if(size>root.getUsableSpace()-128L*1024*1024)throw new IOException("Not enough storage to unpack runtime");
                        parents(dest);
                        try(OutputStream out=Files.newOutputStream(dest.toPath(),StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE,LinkOption.NOFOLLOW_LINKS)){transfer(in,out,size,copyBuffer);}
                        Os.chmod(dest.getPath(),(mode&0111)!=0?0755:0644);
                    } else if(type=='5') {
                        if(size!=0)throw new IOException("Malformed directory entry");
                        Files.createDirectories(dest.toPath());
                    }
                    else if(type=='1'||type=='2') {if(size!=0)throw new IOException("Malformed link");links.add(new String[]{name,link,String.valueOf(type)});}
                    else throw new IOException("Unsupported runtime tar member; use the release runtime archive (type "+type+")");
                }
                skip(in,(512-size%512)%512); if(count%500==0)progress.update(count);
            }
        }
        // All links are deferred: archive data can never write through a symlink.
        // Copy hardlink bytes rather than creating filesystem hardlinks. This also
        // avoids Android hardlink restrictions and preserves independent files.
        for(String[] link:links)if(link[2].equals("1")) {
            cancelled();
            File dest=path(root,link[0]),source=path(root,link[1]);parents(dest);
            if(!Files.isRegularFile(source.toPath(),LinkOption.NOFOLLOW_LINKS)
                    ||Files.exists(dest.toPath(),LinkOption.NOFOLLOW_LINKS))throw new IOException("Invalid hardlink");
            long size=Files.size(source.toPath());
            if((total+=size)>MAX_TOTAL_BYTES)throw new IOException("Runtime archive copies exceed limits");
            if(size>root.getUsableSpace()-128L*1024*1024)throw new IOException("Not enough storage to copy runtime hardlink");
            Files.copy(source.toPath(),dest.toPath());
            cancelled();
            Os.chmod(dest.getPath(),Files.isExecutable(source.toPath())?0755:0644);
        }
        for(String[] link:links)if(link[2].equals("2")) {
            cancelled();
            File dest=path(root,link[0]);parents(dest);
            // Keep guest absolute targets absolute; PRoot resolves them in its
            // rootfs. Never follow these links in the Android installer.
            if(link[1].isEmpty()||link[1].indexOf('\0')>=0||Files.exists(dest.toPath(),LinkOption.NOFOLLOW_LINKS))throw new IOException("Invalid symlink");
            Os.symlink(link[1],dest.getPath());
        }
        cancelled();
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
            if(key.equals("path")||key.equals("linkpath")||key.equals("size")||key.equals("hdrcharset")) {
                if(value.indexOf('\0')>=0)throw new IOException("Invalid PAX value");
                if((key.equals("path")||key.equals("linkpath"))&&end-equals-2>MAX_PATH_BYTES)throw new IOException("Archive path is too long");
                values.put(key,value);
            }
            offset=end;
        }
        return values;
    }
    static void transfer(InputStream in,OutputStream out,long size)throws IOException {transfer(in,out,size,new byte[65536]);}
    private static void transfer(InputStream in,OutputStream out,long size,byte[] buffer)throws IOException {
        while(size>0) {
            cancelled();
            int n=in.read(buffer,0,(int)Math.min(size,buffer.length));
            if(n<0)throw new EOFException("Truncated runtime archive");
            out.write(buffer,0,n);size-=n;
        }
    }
    static void full(InputStream in,byte[] b,int length)throws IOException {int offset=0;while(offset<length){cancelled();int n=in.read(b,offset,length-offset);if(n<0)throw new EOFException("Truncated runtime archive");offset+=n;}}
    static void skip(InputStream in,long n)throws IOException {while(n-->0){cancelled();if(in.read()<0)throw new EOFException("Truncated runtime archive padding");}}
    static String text(byte[] b,int at,int length){int end=at;while(end<at+length&&b[end]!=0)end++;return new String(b,at,end-at,StandardCharsets.UTF_8);}
    static long octal(byte[] b,int at,int length)throws IOException {String s=text(b,at,length).trim();try{return s.isEmpty()?0:Long.parseLong(s,8);}catch(NumberFormatException e){throw new IOException("Invalid tar size");}}
    static void remove(File file)throws IOException {
        if(!Files.exists(file.toPath(),LinkOption.NOFOLLOW_LINKS))return;
        if(!Files.isSymbolicLink(file.toPath())&&file.isDirectory()){File[] children=file.listFiles();if(children==null)throw new IOException("Cannot read "+file);for(File child:children)remove(child);}
        if(!file.delete())throw new IOException("Cannot remove "+file);
    }
}
