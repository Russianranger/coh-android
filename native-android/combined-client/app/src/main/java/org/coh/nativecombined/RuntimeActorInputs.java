package org.coh.nativecombined;

import android.os.ParcelFileDescriptor;
import android.content.Context;
import org.json.JSONObject;
import io.github.russianranger.cohdiagnostic.AssetPackStore;
import java.io.IOException;
import java.util.Arrays;
import java.util.ArrayList;
import java.util.List;
import java.util.SortedMap;
import java.util.TreeMap;
import java.util.Iterator;
import java.util.Locale;

/** Selected live costume sources, borrowed from the existing verified imports.
 * Native preparation reads selected members and returns before these FDs close;
 * no archive is extracted, mapped whole, or copied into Java. */
public final class RuntimeActorInputs implements AutoCloseable {
    static final int MAX_ARCHIVES=16;
    private static final String[] PRIORITY={"runtime/client-visual-assets.zip","runtime/zones-world-supplement.zip"};
    public final int[] fds;
    public final long[] offsets,lengths;
    private final ParcelFileDescriptor[] archives;
    private RuntimeActorInputs(int count) {
        fds=new int[count];Arrays.fill(fds,-1);offsets=new long[count];lengths=new long[count];archives=new ParcelFileDescriptor[count];
    }

    public static RuntimeActorInputs open(Context context,ImportStore imports,ImportContract.Control control)throws Exception {
        control.check();AssetPackStore pack=imports.assetStore(control);
        SortedMap<String,ImportContract.Pin> pins=archivePins(context);
        if(pins.size()>MAX_ARCHIVES)throw new IOException("Loaded archive descriptor capacity exceeded");
        List<String> names=new ArrayList<>();
        for(String name:PRIORITY)if(pins.containsKey(name))names.add(name);
        for(String name:pins.keySet())if(!names.contains(name))names.add(name);
        RuntimeActorInputs out=new RuntimeActorInputs(names.size());
        try {
            for(int i=0;i<names.size();i++) {
                control.check();String name=names.get(i);
                ImportContract.Pin pin=pins.get(name);
                out.archives[i]=RuntimeWorldInputs.openArchive(pack.resolve(name),pin);
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

    /** Names and pins from the shipped descriptor already checked by AssetPackStore.
     * No import-store behavior or protected input contract is changed. */
    private static SortedMap<String,ImportContract.Pin> archivePins(Context context)throws Exception {
        JSONObject files=new JSONObject(new String(ImportContract.asset(context,"runtime/asset-pack-manifest.json",1024*1024),java.nio.charset.StandardCharsets.UTF_8)).getJSONObject("files");
        SortedMap<String,ImportContract.Pin> result=new TreeMap<>();
        for(Iterator<String> names=files.keys();names.hasNext();) {
            String name=names.next();
            if(name.toLowerCase(Locale.ROOT).endsWith(".zip"))result.put(name,ImportContract.pin(files.getJSONObject(name)));
        }
        return result;
    }

    /** Array payloads only; native additionally accounts the supplied frame and
     * retained interop source bytes. RSS/PSS are observed separately. */
    public long stagingPayloadBytes(){return (long)fds.length*(Integer.BYTES+2L*Long.BYTES);}

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
