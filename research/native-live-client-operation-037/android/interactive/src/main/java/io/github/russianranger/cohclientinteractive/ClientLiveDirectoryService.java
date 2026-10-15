package io.github.russianranger.cohclientinteractive;

import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.EOFException;
import java.io.IOException;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

/** Dormant operation-owned live metadata transport. The owner must first prove
 * native library, finalized guest mapping, Wine access and ABI compatibility.
 * This class grants none of those authorities and never changes player data.
 */
final class ClientLiveDirectoryService implements AutoCloseable {
    static final int REQUEST_BYTES = 96, RESPONSE_BYTES = 32, MAX_PATH_BYTES = 1024;
    static final int MAX_BATCH_BYTES = 27944, MAX_CURSORS = 16, MAX_DIRECTORY_ROWS = 8192;
    static final int OPEN = 1, NEXT = 2, CLOSE = 3;
    static final int SUCCESS = 0, INITIAL_DECLINE = 1, TERMINAL = 2;
    private static final byte[] REQUEST_MAGIC = "COHLDIR1".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] RESPONSE_MAGIC = {'C','O','H','R','S','P','1',0};
    private static final byte[] BATCH_MAGIC = "COHLIVE1".getBytes(StandardCharsets.US_ASCII);

    interface Backend extends AutoCloseable {
        long open(String guestDirectory, byte[] operation, byte[] directory) throws IOException;
        long[] identity(long cursor) throws IOException;
        byte[] next(long cursor) throws IOException;
        void closeCursor(long cursor) throws IOException;
        void close() throws IOException;
    }
    interface PathAdmission { boolean allows(String guestDirectory); }
    interface Journal { void record(String phase, String directoryToken, long rowsProduced, String result); }

    private static final class Cursor {
        final long handle;
        final byte[] token;
        long rows, batchSequence;
        boolean finalBatch;
        Cursor(long handle, byte[] token) { this.handle=handle; this.token=token.clone(); }
    }
    private final Backend backend;
    private final PathAdmission paths;
    private final Journal journal;
    private final byte[] operation, nonce = new byte[32];
    private final long registeredDevice;
    private final int registeredUid;
    private final ServerSocket server;
    private final Map<String, Cursor> cursors = new HashMap<>();
    private final Thread worker;
    private volatile boolean closed;
    private volatile Socket active;
    private volatile IOException failure;
    private long requestSequence=1;
    private boolean acceptedAuthenticatedPeer;

    ClientLiveDirectoryService(byte[] operation, long registeredDevice, int registeredUid,
            Backend backend, PathAdmission paths, Journal journal) throws IOException {
        if(operation==null||operation.length!=16||registeredUid<0||backend==null||paths==null||journal==null)
            throw new IOException("Complete current live-directory operation boundary required");
        this.operation=operation.clone();this.backend=backend;this.paths=paths;this.journal=journal;
        this.registeredDevice=registeredDevice;this.registeredUid=registeredUid;
        new SecureRandom().nextBytes(nonce);
        server=new ServerSocket(0,1,InetAddress.getByName("127.0.0.1"));
        try{
            worker=new Thread(this::serve,"coh-live-directory");worker.setDaemon(true);worker.start();
        }catch(Throwable error){
            // The operation factory cannot close an instance whose constructor
            // did not return. Release this constructor's own listening socket.
            try{server.close();}catch(IOException cleanup){error.addSuppressed(cleanup);}
            if(error instanceof Error)throw (Error)error;
            if(error instanceof RuntimeException)throw (RuntimeException)error;
            throw new IOException("Cannot start owned live-directory service",error);
        }
    }
    int port(){return server.getLocalPort();}
    byte[] authenticationNonce(){return nonce.clone();}
    IOException failure(){return failure;}
    static String hex(byte[] bytes){StringBuilder out=new StringBuilder(bytes.length*2);
        for(byte value:bytes)out.append(String.format(java.util.Locale.ROOT,"%02x",value&255));return out.toString();}

    private void serve(){
        try {
            int rejected=0;
            while(!closed && !acceptedAuthenticatedPeer){
                try(Socket peer=server.accept()){
                    active=peer;
                    peer.setTcpNoDelay(true);
                    if(!peer.getInetAddress().isLoopbackAddress())throw new IOException("Nonloopback metadata peer refused");
                    // Admission I/O bound applies only before authentication.
                    // A current authenticated Game has no idle/session expiry.
                    peer.setSoTimeout(2000);
                    DataInputStream input=new DataInputStream(peer.getInputStream());
                    DataOutputStream output=new DataOutputStream(peer.getOutputStream());
                    byte[] header=new byte[REQUEST_BYTES];readHeader(input,header,false);
                    if(!authenticates(header)){if(++rejected>=8)throw new IOException("Metadata peer admission bound exceeded");continue;}
                    acceptedAuthenticatedPeer=true;peer.setSoTimeout(0);
                    while(!closed){
                        handle(header,input,output);
                        if(!readHeader(input,header,true))break;
                    }
                } finally {active=null;}
            }
        }catch(IOException error){if(!closed)failure=error;
        }catch(Throwable error){if(!closed)failure=new IOException("Live-directory service failed",error);
        }finally{
            try{
                IOException cleanup=cleanupBackend();
                if(cleanup!=null){if(failure==null)failure=cleanup;else failure.addSuppressed(cleanup);}
            }finally{
                try{server.close();}catch(IOException error){if(failure==null)failure=error;else failure.addSuppressed(error);}
            }
        }
    }
    private boolean readHeader(DataInputStream input,byte[] header,boolean allowCleanEOF)throws IOException{
        int count=0;
        while(count<header.length){
            int got=input.read(header,count,header.length-count);
            if(got<0){
                if(count==0&&allowCleanEOF&&cursors.isEmpty())return false;
                throw new EOFException(count==0?"Authenticated metadata peer ended with live cursor"
                    :"Interrupted metadata request header: "+count+"/"+header.length);
            }
            if(got==0)continue;count+=got;
        }
        return true;
    }
    private boolean authenticates(byte[] header){return header.length==REQUEST_BYTES
        && MessageDigest.isEqual(Arrays.copyOfRange(header,0,8),REQUEST_MAGIC)
        && MessageDigest.isEqual(Arrays.copyOfRange(header,16,32),operation)
        && MessageDigest.isEqual(Arrays.copyOfRange(header,32,64),nonce);}

    private void handle(byte[] header,DataInputStream input,DataOutputStream output)throws IOException{
        ByteBuffer fields=ByteBuffer.wrap(header).order(ByteOrder.LITTLE_ENDIAN);
        int command=fields.getInt(12),length=fields.getInt(84);
        long sequence=Integer.toUnsignedLong(fields.getInt(64));
        if(!authenticates(header)||fields.getInt(8)!=1||fields.getInt(92)!=0
                ||sequence!=requestSequence||sequence>1000000||length<0||length>MAX_PATH_BYTES
                ||fields.getInt(88)!=REQUEST_BYTES+length||command<OPEN||command>CLOSE
                ||(command!=OPEN&&length!=0)||(command==OPEN&&length==0))
            throw new IOException("Malformed or stale live-directory request");
        requestSequence++;
        byte[] token=Arrays.copyOfRange(header,68,84);String key=hex(token);
        byte[] rawPath=new byte[length];input.readFully(rawPath);
        if(command==OPEN){
            if(cursors.containsKey(key)||cursors.size()>=MAX_CURSORS)throw new IOException("Duplicate or excessive metadata cursor");
            String path=path(rawPath);
            if(path==null||!paths.allows(path)){reply(output,INITIAL_DECLINE,sequence,new byte[0],0);return;}
            long handle=0;
            byte[] identityAck;
            try{
                handle=backend.open(path,operation.clone(),token.clone());
                if(handle==0)throw new IOException("Native metadata cursor missing");
                long[] identity=backend.identity(handle);
                if(identity==null||identity.length!=3||identity[0]!=registeredDevice||identity[2]!=registeredUid)
                    throw new IOException("Held native directory differs from registered device/owner");
                identityAck=ByteBuffer.allocate(32).order(ByteOrder.LITTLE_ENDIAN)
                    .putLong(identity[0]).putLong(identity[1]).putInt(1).putInt(1).putLong(0).array();
                cursors.put(key,new Cursor(handle,token));
                journal.record("directory_open",key,0,"opened_read_only_no_native_authority_granted");
            }catch(IOException error){
                if(handle!=0)try{backend.closeCursor(handle);}catch(IOException cleanup){error.addSuppressed(cleanup);}
                journal.record("directory_open",key,0,"initial_decline: "+reason(error));
                reply(output,INITIAL_DECLINE,sequence,new byte[0],0);return;
            }
            // Transport failure after success is not another native reply.
            reply(output,SUCCESS,sequence,identityAck,0);
            return;
        }
        Cursor cursor=cursors.get(key);if(cursor==null)throw new IOException("Unknown live metadata cursor");
        if(command==CLOSE){
            backend.closeCursor(cursor.handle);cursors.remove(key);
            journal.record("directory_close",key,cursor.rows,"closed");reply(output,SUCCESS,sequence,new byte[0],0);return;
        }
        byte[] batch;
        try{
            if(cursor.finalBatch)throw new IOException("Metadata cursor already finished");
            batch=backend.next(cursor.handle);
            int count=validateBatch(batch,cursor);
            cursor.rows+=count;cursor.batchSequence++;
            cursor.finalBatch=ByteBuffer.wrap(batch).order(ByteOrder.LITTLE_ENDIAN).getInt(52)==1;
            journal.record("batch_produced",key,cursor.rows,"current_metadata_not_callback_or_world_evidence");
        }catch(IOException error){
            int status=cursor.rows==0?INITIAL_DECLINE:TERMINAL;
            journal.record("batch_failure",key,cursor.rows,
                (status==TERMINAL?"terminal_no_restart: ":"initial_decline: ")+reason(error));
            try{backend.closeCursor(cursor.handle);}catch(IOException cleanup){error.addSuppressed(cleanup);}
            cursors.remove(key);reply(output,status,sequence,new byte[0],0);return;
        }
        reply(output,SUCCESS,sequence,batch,0);
    }
    private static String reason(IOException error){String text=error.getClass().getSimpleName()+": "+error.getMessage();
        return text.length()>1024?text.substring(0,1024):text;}
    private static String path(byte[] raw){
        if(raw.length==0||raw[0]!='/')return null;
        for(byte value:raw)if(value<32||value>=127||value=='\\'||value==':'||value=='*'||value=='?')return null;
        String path=new String(raw,StandardCharsets.US_ASCII);
        for(String part:path.substring(1).split("/",-1))if(part.isEmpty()||part.equals(".")||part.equals(".."))return null;
        return path;
    }
    private int validateBatch(byte[] bytes,Cursor cursor)throws IOException{
        if(bytes==null||bytes.length<64||bytes.length>MAX_BATCH_BYTES)throw new IOException("Bounded native metadata batch required");
        ByteBuffer data=ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN);
        int count=data.getInt(48),finished=data.getInt(52);
        if(!Arrays.equals(Arrays.copyOfRange(bytes,0,8),BATCH_MAGIC)
            ||!MessageDigest.isEqual(Arrays.copyOfRange(bytes,8,24),operation)
            ||!MessageDigest.isEqual(Arrays.copyOfRange(bytes,24,40),cursor.token)
            ||Integer.toUnsignedLong(data.getInt(40))!=cursor.batchSequence
            ||Integer.toUnsignedLong(data.getInt(44))!=cursor.rows||count<0||count>85
            ||finished<0||finished>1||data.getInt(56)!=0||data.getInt(60)!=bytes.length
            ||bytes.length!=64+count*328||cursor.rows+count>MAX_DIRECTORY_ROWS||count==0&&finished==0)
            throw new IOException("Stale or malformed native metadata batch");
        int used=0;
        for(int i=0;i<count;i++){
            int row=64+i*328,wfd=row+8;
            if(Integer.toUnsignedLong(data.getInt(row))!=cursor.rows+i||data.getInt(row+4)!=0)
                throw new IOException("Native metadata ordinal differs");
            int name=0;
            while(name<260&&bytes[wfd+44+name]!=0){
                int c=bytes[wfd+44+name]&255;
                if(c<32||c>=127||"/\\:*?\"<>|".indexOf(c)>=0)throw new IOException("Unsupported native metadata name");
                name++;
            }
            if(name==0||name==260)throw new IOException("Native metadata name length differs");
            for(int j=44+name;j<304;j++)if(bytes[wfd+j]!=0)throw new IOException("Native metadata name padding differs");
            for(int j=36;j<44;j++)if(bytes[wfd+j]!=0)throw new IOException("Native metadata reserved fields differ");
            for(int j=304;j<320;j++)if(bytes[wfd+j]!=0)throw new IOException("Scoped recipe requires normalized unused short name");
            used=((used+7)&~7)+94+name*2;
            if(used>8192)throw new IOException("Native metadata observation batch exceeds NT boundary");
        }
        return count;
    }
    private static void reply(DataOutputStream output,int status,long sequence,byte[] body,int error)throws IOException{
        ByteBuffer header=ByteBuffer.allocate(RESPONSE_BYTES).order(ByteOrder.LITTLE_ENDIAN);
        header.put(RESPONSE_MAGIC).putInt(1).putInt(status).putInt((int)sequence).putInt(body.length).putInt(error).putInt(0);
        byte[] frame=Arrays.copyOf(header.array(),RESPONSE_BYTES+body.length);
        System.arraycopy(body,0,frame,RESPONSE_BYTES,body.length);
        output.write(frame);output.flush();
    }
    private IOException cleanupBackend(){
        IOException errors=null;
        for(Cursor cursor:cursors.values())try{backend.closeCursor(cursor.handle);}catch(Throwable problem){
            IOException error=cleanupError(problem);
            if(errors==null)errors=error;else errors.addSuppressed(error);}
        cursors.clear();try{backend.close();}catch(Throwable problem){IOException error=cleanupError(problem);
            if(errors==null)errors=error;else errors.addSuppressed(error);}
        return errors;
    }
    private static IOException cleanupError(Throwable problem){return problem instanceof IOException
        ?(IOException)problem:new IOException("Unexpected native metadata cleanup failure",problem);}
    public void close()throws IOException{
        closed=true;IOException errors=null;
        try{server.close();}catch(IOException error){errors=error;}
        Socket peer=active;if(peer!=null)try{peer.close();}catch(IOException error){if(errors==null)errors=error;else errors.addSuppressed(error);}
        try{worker.join(2000);}catch(InterruptedException error){Thread.currentThread().interrupt();
            if(errors==null)errors=new IOException("Interrupted metadata service cleanup",error);else errors.addSuppressed(error);}
        if(worker.isAlive()){IOException error=new IOException("Metadata service cleanup has not completed");
            if(errors==null)errors=error;else errors.addSuppressed(error);}
        if(failure!=null){if(errors==null)errors=failure;else errors.addSuppressed(failure);}
        Arrays.fill(nonce,(byte)0);if(errors!=null)throw errors;
    }
}
