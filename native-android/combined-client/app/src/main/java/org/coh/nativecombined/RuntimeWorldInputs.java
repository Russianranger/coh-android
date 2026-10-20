package org.coh.nativecombined;

import android.content.Context;
import android.content.res.AssetFileDescriptor;
import android.os.ParcelFileDescriptor;
import android.system.Os;
import android.system.OsConstants;
import android.system.StructStat;
import io.github.russianranger.cohdiagnostic.AssetPackStore;
import org.json.JSONObject;
import java.io.*;
import java.security.MessageDigest;
import java.util.Arrays;

/** Immutable existing imports and one APK index span for the native stream.
 * Close after native create_fds returns: native owns its own CLOEXEC duplicates.
 * The original import receipt establishes whole-archive SHA identity; opening
 * these sources does not rehash, extract or copy a859MB archive while gaming. */
public final class RuntimeWorldInputs implements AutoCloseable {
    static final String[] ARCHIVES={"atlas-world-supplement.zip","client-visual-assets.zip"};
    private static final int CLOEXEC=0x80000;
    private static final int VERIFY_BYTES=16384;
    public final int[] fds={-1,-1,-1};
    public final long[] offsets=new long[3],lengths=new long[3];
    private AssetFileDescriptor index;
    private final ParcelFileDescriptor[] archives=new ParcelFileDescriptor[2];
    private byte[] verification;
    private RuntimeWorldInputs() { }

    /** indexPin comes from the APK's existing combined/build-inputs.json asset
     * inventory, not a user-supplied manifest. Call on the render/init worker. */
    public static RuntimeWorldInputs open(Context context,ImportStore imports,JSONObject indexPin,ImportContract.Control control)throws Exception {
        RuntimeWorldInputs out=new RuntimeWorldInputs();
        try {
            control.check();ImportContract.Pin pin=ImportContract.pin(indexPin);
            if(pin.bytes<64||pin.bytes>64L+65536L*96L)throw new IOException("Runtime placement index exceeds its existing row bound");
            out.index=context.getAssets().openFd("live-world.bin");
            long start=out.index.getStartOffset(),length=out.index.getDeclaredLength();
            if(start<0||length!=pin.bytes||start>Long.MAX_VALUE-length)throw new IOException("Runtime placement asset span differs");
            StructStat before=Os.fstat(out.index.getFileDescriptor());
            if(!OsConstants.S_ISREG(before.st_mode)||before.st_size<start||length>before.st_size-start)throw new IOException("Runtime placement asset descriptor differs");
            out.verification=new byte[VERIFY_BYTES];MessageDigest hash=ImportContract.hash();long done=0;
            while(done<length){control.check();int count=(int)Math.min(out.verification.length,length-done);int n=Os.pread(out.index.getFileDescriptor(),out.verification,0,count,start+done);if(n<=0||n>count)throw new IOException("Runtime placement asset made no progress");hash.update(out.verification,0,n);done+=n;}
            if(!pin.sha256.equals(ImportContract.hex(hash.digest()))||!ImportStore.sameState(before,Os.fstat(out.index.getFileDescriptor())))throw new IOException("Runtime placement asset SHA or identity differs");
            out.fds[0]=out.index.getParcelFileDescriptor().getFd();out.offsets[0]=start;out.lengths[0]=length;
            AssetPackStore pack=imports.assetStore(control);
            for(int i=0;i<ARCHIVES.length;i++){
                control.check();String name=ARCHIVES[i];
                ImportContract.Pin archivePin=ImportContract.pin(imports.contract().runtimeManifest.getJSONObject("files").getJSONObject(name));
                File path=pack.resolve("runtime/"+name);
                out.archives[i]=openArchive(path,archivePin);out.fds[i+1]=out.archives[i].getFd();out.lengths[i+1]=archivePin.bytes;
            }
            control.check();return out;
        } catch(Throwable problem) {try{out.close();}catch(Throwable cleanup){problem.addSuppressed(cleanup);}if(problem instanceof Exception)throw (Exception)problem;if(problem instanceof Error)throw (Error)problem;throw new IOException(problem);}
    }

    private static ParcelFileDescriptor openArchive(File path,ImportContract.Pin pin)throws Exception {
        if(pin.bytes<22||pin.bytes>0xffffffffL)throw new IOException("Runtime source archive is outside ZIP32 bounds");
        StructStat before=ImportStore.immutableStat(path.toPath(),pin);
        if((before.st_mode&0222)!=0)throw new IOException("Runtime source archive is not an immutable imported object");
        FileDescriptor opened=Os.open(path.getPath(),OsConstants.O_RDONLY|OsConstants.O_NOFOLLOW|CLOEXEC,0);
        ParcelFileDescriptor result=null;Throwable failure=null;
        try {
            if(!ImportStore.sameState(before,Os.fstat(opened))||!ImportStore.sameState(before,ImportStore.immutableStat(path.toPath(),pin)))throw new IOException("Runtime source archive changed while opening");
            result=ParcelFileDescriptor.dup(opened);
            if(!ImportStore.sameState(before,Os.fstat(result.getFileDescriptor())))throw new IOException("Runtime source descriptor identity differs");
        } catch(Throwable problem){failure=problem;}
        finally {
            try{Os.close(opened);}catch(Throwable cleanup){if(failure==null)failure=cleanup;else failure.addSuppressed(cleanup);}
            if(failure!=null&&result!=null)try{result.close();}catch(Throwable cleanup){failure.addSuppressed(cleanup);}
        }
        if(failure instanceof Exception)throw (Exception)failure;
        if(failure instanceof Error)throw (Error)failure;
        if(failure!=null)throw new IOException(failure);
        return result;
    }

    /** Actual retained array payloads during native initialization; VM object
     * headers and measured process RSS/PSS remain outside this source inventory. */
    public long stagingPayloadBytes(){return verification==null?0:verification.length+3L*Integer.BYTES+6L*Long.BYTES;}

    @Override public void close()throws IOException {
        IOException failure=null;
        if(index!=null){try{index.close();}catch(IOException e){failure=e;}index=null;}
        for(int i=0;i<archives.length;i++)if(archives[i]!=null){try{archives[i].close();}catch(IOException e){if(failure==null)failure=e;else failure.addSuppressed(e);}archives[i]=null;}
        verification=null;Arrays.fill(fds,-1);Arrays.fill(offsets,0);Arrays.fill(lengths,0);
        if(failure!=null)throw failure;
    }
}
