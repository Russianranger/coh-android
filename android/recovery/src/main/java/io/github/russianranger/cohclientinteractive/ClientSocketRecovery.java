package io.github.russianranger.cohclientinteractive;

import android.content.Context;
import android.net.LocalSocket;
import android.net.LocalSocketAddress;
import android.os.ParcelFileDescriptor;
import android.system.ErrnoException;
import android.system.Os;
import android.system.OsConstants;
import android.system.StructStat;
import java.io.Closeable;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileDescriptor;
import java.io.FileInputStream;
import java.io.IOException;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.charset.StandardCharsets;

/** Removes only a proved-dead app-owned display socket. Never stops a process. */
public final class ClientSocketRecovery {
    private ClientSocketRecovery() {}
    static final int DIRECTORY=1, SOCKET=2, OTHER=3;
    static final int MAX_PROC_ENTRIES=32768;
    static final int MAX_PROCESS_STATUS=65536;
    static final class Identity {
        final int kind,uid,gid,mode;
        final long device,inode,links;
        Identity(int kind,int uid,int mode,long device,long inode,long links) {
            this(kind,uid,uid,mode,device,inode,links);
        }
        Identity(int kind,int uid,int gid,int mode,long device,long inode,long links) {
            this.kind=kind;this.uid=uid;this.gid=gid;this.mode=mode;this.device=device;this.inode=inode;this.links=links;
        }
        boolean same(Identity other) {
            return other!=null&&kind==other.kind&&uid==other.uid&&gid==other.gid&&mode==other.mode
                &&device==other.device&&inode==other.inode&&links==other.links;
        }
    }
    /** The Android adapter holds directory fds throughout this decision. */
    interface Probe extends Closeable {
        int uid();
        Identity root() throws IOException;
        Identity directory() throws IOException;
        Identity socket() throws IOException;
        void requireNoOtherAppProcess() throws IOException;
        boolean connectionRefused() throws IOException;
        void unlink(Identity expected) throws IOException;
    }
    interface ProcessStat { Identity inspect(Path path) throws IOException; }
    static void requireNoOtherAppProcess(Iterable<Path> entries,ProcessStat reader,int appUid,int currentPid) throws IOException {
        int visited=0;boolean sawSelf=false;
        for(Path path:entries) {
            if(++visited>MAX_PROC_ENTRIES)throw refused("Process inventory exceeded its safety bound");
            String name=path.getFileName().toString();
            if(!name.matches("[1-9][0-9]{0,9}"))continue;
            long pid;
            try{pid=Long.parseLong(name);}catch(NumberFormatException failure){throw refused("Process identity is ambiguous");}
            Identity owner=reader.inspect(path);
            if(owner==null)continue; // ENOENT: process exited before its ownership could be inspected.
            if(owner.kind!=DIRECTORY)throw refused("Process inventory contains an unexpected entry");
            if(pid==currentPid) {
                if(owner.uid!=appUid)throw refused("Current process ownership cannot be verified");
                sawSelf=true;
            } else if(owner.uid==appUid)throw refused("Another app process is still present");
        }
        if(!sawSelf)throw refused("Process inventory could not verify this app process");
    }
    public static boolean prepare(Context context,File filesRoot) throws IOException {
        File trusted=context.getFilesDir().getCanonicalFile();
        if(!trusted.equals(filesRoot.getCanonicalFile()))throw refused("App files root does not match the application");
        try(Probe probe=new AndroidProbe(trusted)){return prepare(probe);}
    }
    static boolean prepare(Probe probe) throws IOException {
        Identity root=probe.root();requireDirectory(root,probe.uid());
        Identity directory=probe.directory();if(directory==null)return false;
        requireSocketDirectory(directory,probe.uid());
        Identity socket=probe.socket();if(socket==null)return false;
        requireSocket(socket,probe.uid());
        // A refused connect alone is insufficient: a live runtime may be between binds.
        probe.requireNoOtherAppProcess();
        if(!probe.connectionRefused())throw refused("The private display socket has a live listener or an ambiguous state");
        probe.requireNoOtherAppProcess();
        if(!root.same(probe.root())||!directory.same(probe.directory()))throw refused("The private display directory changed");
        Identity current=probe.socket();
        if(current==null)return false;
        if(!socket.same(current))throw refused("The private display socket changed");
        probe.unlink(socket);
        return true;
    }
    private static void requireDirectory(Identity value,int uid) throws IOException {
        // Context.getFilesDir() normally uses 0771 with the app's own UID/GID.
        if(value==null||value.kind!=DIRECTORY||value.uid!=uid||(value.mode&0002)!=0
                ||((value.mode&0020)!=0&&value.gid!=uid))
            throw refused("The private display directory is linked, writable by others, or not app-owned");
    }
    private static void requireSocket(Identity value,int uid) throws IOException {
        if(value==null||value.kind!=SOCKET||value.uid!=uid||value.links!=1)
            throw refused("The private display entry is not a single app-owned socket");
    }
    private static void requireSocketDirectory(Identity value,int uid) throws IOException {
        requireDirectory(value,uid);
        if((value.mode&0777)!=0700)throw refused("The private display directory must have mode 0700");
    }
    static int processOwner(byte[] bytes,long expectedPid,int appUid) throws IOException {
        if(bytes.length==0||bytes.length>MAX_PROCESS_STATUS)throw refused("Process status exceeded its safety bound");
        boolean sawPid=false,sawUid=false,appOwned=false;
        for(String line:new String(bytes,StandardCharsets.US_ASCII).split("\n")) {
            if(line.startsWith("Pid:")) {
                String value=line.substring(4).trim();
                if(sawPid||!value.matches("[1-9][0-9]{0,9}")||Long.parseLong(value)!=expectedPid)
                    throw refused("Process status identity is ambiguous");
                sawPid=true;
            } else if(line.startsWith("Uid:")) {
                if(sawUid)throw refused("Process status ownership is ambiguous");
                String[] values=line.substring(4).trim().split("\\s+");
                if(values.length!=4)throw refused("Process status ownership is incomplete");
                for(String value:values) {
                    if(!value.matches("[0-9]{1,10}"))throw refused("Process status ownership is invalid");
                    long uid=Long.parseLong(value);if(uid>Integer.MAX_VALUE)throw refused("Process status ownership is outside the supported range");
                    if(uid==appUid)appOwned=true;
                }
                sawUid=true;
            }
        }
        if(!sawPid||!sawUid)throw refused("Process status identity or ownership is unavailable");
        return appOwned?appUid:-1;
    }
    private static IOException refused(String reason) {
        return new IOException(reason+". Export the previous report and force-stop the app before retrying.");
    }
    static boolean explicitlyRefused(IOException failure) {
        Throwable cause=failure;
        // Prefer the numeric errno when a platform preserves it.
        for(int depth=0;cause!=null&&depth<8;depth++,cause=cause.getCause())
            if(cause instanceof ErrnoException)return ((ErrnoException)cause).errno==OsConstants.ECONNREFUSED;
        // AOSP LocalSocket's connectLocal JNI uses jniThrowIOException(errno), which
        // drops the cause and exposes precisely strerror(errno). Match only that
        // exact platform-derived form, never a substring, wrapper, or timeout class.
        return failure.getClass()==IOException.class&&failure.getCause()==null
            &&Os.strerror(OsConstants.ECONNREFUSED).equals(failure.getMessage());
    }
    private static Identity identity(StructStat stat) {
        return new Identity(OsConstants.S_ISDIR(stat.st_mode)?DIRECTORY:OsConstants.S_ISSOCK(stat.st_mode)?SOCKET:OTHER,
            stat.st_uid,stat.st_gid,stat.st_mode,stat.st_dev,stat.st_ino,stat.st_nlink);
    }
    private static Identity inspect(File path) throws IOException {
        try{return identity(Os.lstat(path.getPath()));}
        catch(ErrnoException failure){if(failure.errno==OsConstants.ENOENT)return null;throw refused("Cannot verify private display ownership");}
    }
    private static final class AndroidProbe implements Probe {
        private final File rootPath;
        private final int appUid=android.os.Process.myUid();
        private ParcelFileDescriptor rootFd,directoryFd;
        private File directoryPath,socketPath;
        AndroidProbe(File root) throws IOException {
            rootPath=root;
            try {
                Identity expected=inspect(root);requireDirectory(expected,appUid);
                rootFd=openDirectory(root,expected);
                directoryPath=new File("/proc/self/fd/"+rootFd.getFd(),"s");
                Identity directory=inspect(directoryPath);
                if(directory==null) {
                    try{Os.mkdir(directoryPath.getPath(),0700);}
                    catch(ErrnoException failure){throw refused("Cannot create the private display directory safely");}
                    directory=inspect(directoryPath);
                }
                requireSocketDirectory(directory,appUid);
                directoryFd=openDirectory(directoryPath,directory);
                socketPath=new File("/proc/self/fd/"+directoryFd.getFd(),"view.sock");
            } catch(IOException failure){close();throw failure;}
        }
        @Override public int uid(){return appUid;}
        @Override public Identity root() throws IOException {
            Identity opened=opened(rootFd),named=inspect(rootPath);
            if(!opened.same(named))throw refused("App files root changed during socket recovery");
            return opened;
        }
        @Override public Identity directory() throws IOException {
            Identity named=inspect(directoryPath);
            if(directoryFd==null){if(named!=null)throw refused("Private display directory appeared during recovery");return null;}
            Identity opened=opened(directoryFd);
            if(!opened.same(named))throw refused("Private display directory changed during recovery");
            return opened;
        }
        @Override public Identity socket() throws IOException {return socketPath==null?null:inspect(socketPath);}
        @Override public boolean connectionRefused() throws IOException {
            try(LocalSocket socket=new LocalSocket()) {
                // Opening the stream creates the socket without connecting or writing.
                // SO_TIMEOUT does not bound LocalSocket.connect; use O_NONBLOCK so a
                // full live listener backlog cannot hang recovery.
                socket.getOutputStream();
                try {
                    FileDescriptor descriptor=socket.getFileDescriptor();
                    int flags=Os.fcntlInt(descriptor,OsConstants.F_GETFL,0);
                    Os.fcntlInt(descriptor,OsConstants.F_SETFL,flags|OsConstants.O_NONBLOCK);
                } catch(ErrnoException failure){throw refused("Cannot safely bound the private display probe");}
                try {socket.connect(new LocalSocketAddress(socketPath.getPath(),LocalSocketAddress.Namespace.FILESYSTEM));return false;}
                catch(IOException failure){return explicitlyRefused(failure);}
            }
        }
        @Override public void requireNoOtherAppProcess() throws IOException {
            try(DirectoryStream<Path> entries=Files.newDirectoryStream(Paths.get("/proc"))) {
                ClientSocketRecovery.requireNoOtherAppProcess(entries,this::inspectProcess,appUid,android.os.Process.myPid());
            } catch(SecurityException failure){throw refused("Process ownership cannot be inspected safely");}
        }
        private Identity inspectProcess(Path path) throws IOException {
            File directory=path.toFile();Identity before=inspect(directory);
            if(before==null)return null;
            if(before.kind!=DIRECTORY)throw refused("Process inventory contains an unexpected entry");
            try(ParcelFileDescriptor held=openDirectory(directory,before)) {
                String statusPath="/proc/self/fd/"+held.getFd()+"/status";
                FileDescriptor descriptor=Os.open(statusPath,OsConstants.O_RDONLY|OsConstants.O_NOFOLLOW|OsConstants.O_CLOEXEC|OsConstants.O_NONBLOCK,0);
                byte[] bytes;
                try(FileInputStream input=new FileInputStream(descriptor)) {
                    StructStat status=Os.fstat(descriptor);
                    if(!OsConstants.S_ISREG(status.st_mode)||status.st_nlink!=1)throw refused("Process status is not a regular kernel entry");
                    ByteArrayOutputStream output=new ByteArrayOutputStream();byte[] buffer=new byte[4096];int count;
                    while((count=input.read(buffer))!=-1) {
                        if(output.size()+count>MAX_PROCESS_STATUS)throw refused("Process status exceeded its safety bound");
                        output.write(buffer,0,count);
                    }
                    bytes=output.toByteArray();
                }
                Identity after=inspect(directory);if(after==null)return null;
                if(!before.same(after))throw refused("Process identity changed while checking ownership");
                // Non-dumpable processes can expose root-owned /proc inodes. The
                // kernel Uid fields, not inode ownership, identify their real owner.
                int owner=processOwner(bytes,Long.parseLong(path.getFileName().toString()),appUid);
                return new Identity(DIRECTORY,owner,before.gid,before.mode,before.device,before.inode,before.links);
            } catch(ErrnoException failure) {
                if(failure.errno==OsConstants.ENOENT&&inspect(directory)==null)return null;
                throw refused("Cannot verify a process owner from kernel status");
            } catch(IOException failure) {
                if(inspect(directory)==null)return null;
                throw failure;
            }
        }
        @Override public void unlink(Identity expected) throws IOException {
            // Both pathname ancestors remain anchored to fds, and the exact inode is checked again.
            root();directory();
            Identity actual=socket();requireSocket(actual,appUid);
            if(!expected.same(actual))throw refused("Private display socket changed before removal");
            try{Files.delete(socketPath.toPath());}
            catch(IOException failure){throw refused("Private display socket could not be removed safely");}
        }
        @Override public void close() throws IOException {
            IOException failure=null;
            if(directoryFd!=null)try{directoryFd.close();}catch(IOException caught){failure=caught;}finally{directoryFd=null;}
            if(rootFd!=null)try{rootFd.close();}catch(IOException caught){failure=caught;}finally{rootFd=null;}
            if(failure!=null)throw failure;
        }
        private static Identity opened(ParcelFileDescriptor descriptor) throws IOException {
            try{return identity(Os.fstat(descriptor.getFileDescriptor()));}
            catch(ErrnoException failure){throw refused("Cannot verify held private display directory");}
        }
        private static ParcelFileDescriptor openDirectory(File path,Identity expected) throws IOException {
            FileDescriptor descriptor=null;
            try {
                // O_DIRECTORY is not part of Android's public SDK. The held fd
                // must still match the previously verified directory inode/type.
                descriptor=Os.open(path.getPath(),OsConstants.O_RDONLY|OsConstants.O_NOFOLLOW|OsConstants.O_CLOEXEC|OsConstants.O_NONBLOCK,0);
                if(!expected.same(identity(Os.fstat(descriptor))))throw refused("Private display directory changed while opening");
                return ParcelFileDescriptor.dup(descriptor);
            } catch(ErrnoException failure){throw refused("Cannot anchor private display directory without following links");}
            finally{if(descriptor!=null)try{Os.close(descriptor);}catch(ErrnoException ignored){}}
        }
    }
}
