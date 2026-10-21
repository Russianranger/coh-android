package org.coh.nativecombined;

import android.os.ParcelFileDescriptor;
import io.github.russianranger.cohdiagnostic.AssetPackStore;
import java.io.IOException;
import java.util.Arrays;

/** Selected live costume sources, borrowed from the existing verified imports.
 * Native preparation reads selected members and returns before these FDs close;
 * no archive is extracted, mapped whole, or copied into Java. */
public final class RuntimeActorInputs implements AutoCloseable {
    static final String[] ARCHIVES={"client-visual-assets.zip","zones-world-supplement.zip"};
    public final int[] fds={-1,-1};
    public final long[] offsets=new long[2],lengths=new long[2];
    private final ParcelFileDescriptor[] archives=new ParcelFileDescriptor[2];
    private RuntimeActorInputs() { }

    public static RuntimeActorInputs open(ImportStore imports,ImportContract.Control control)throws Exception {
        RuntimeActorInputs out=new RuntimeActorInputs();
        try {
            control.check();AssetPackStore pack=imports.assetStore(control);
            for(int i=0;i<ARCHIVES.length;i++) {
                control.check();String name=ARCHIVES[i];
                ImportContract.Pin pin=ImportContract.pin(imports.contract().runtimeManifest.getJSONObject("files").getJSONObject(name));
                out.archives[i]=RuntimeWorldInputs.openArchive(pack.resolve("runtime/"+name),pin);
                out.fds[i]=out.archives[i].getFd();out.lengths[i]=pin.bytes;
            }
            control.check();return out;
        } catch(Throwable problem) {
            try{out.close();}catch(Throwable cleanup){problem.addSuppressed(cleanup);}
            if(problem instanceof Exception)throw (Exception)problem;
            if(problem instanceof Error)throw (Error)problem;
            throw new IOException(problem);
        }
    }

    /** Array payloads only; native additionally accounts the supplied frame and
     * retained interop source bytes. RSS/PSS are observed separately. */
    public long stagingPayloadBytes(){return 2L*Integer.BYTES+4L*Long.BYTES;}

    @Override public void close()throws IOException {
        IOException failure=null;
        for(int i=0;i<archives.length;i++)if(archives[i]!=null) {
            try{archives[i].close();}catch(IOException e){if(failure==null)failure=e;else failure.addSuppressed(e);}
            archives[i]=null;
        }
        Arrays.fill(fds,-1);Arrays.fill(offsets,0);Arrays.fill(lengths,0);
        if(failure!=null)throw failure;
    }
}
