package io.github.russianranger.cohdiagnostic;

import java.io.File;
import java.lang.management.GarbageCollectorMXBean;
import java.lang.management.ManagementFactory;

/** Uses the APK's exact parser for CI rootfs, Wine and PostgreSQL extraction. */
public final class ExtractRuntimeHost {
    private static long collections() {
        long count=0;
        for(GarbageCollectorMXBean collector:ManagementFactory.getGarbageCollectorMXBeans())
            if(collector.getCollectionCount()>=0)count+=collector.getCollectionCount();
        return count;
    }
    public static void main(String[] args) throws Exception {
        if(args.length<2||args.length>3)
            throw new IllegalArgumentException("Usage: ExtractRuntimeHost ARCHIVE EMPTY_DEST [INTERRUPT_AFTER_COUNT|measure-gc]");
        final boolean measure=args.length==3&&args[2].equals("measure-gc");
        final int cancelAfter=args.length==3&&!measure?Integer.parseInt(args[2]):-1;
        final long before=measure?collections():0;
        if(cancelAfter==0)Thread.currentThread().interrupt();
        TarExtractor.extract(new File(args[0]),new File(args[1]),count->{
            if(cancelAfter>0&&count>=cancelAfter)Thread.currentThread().interrupt();
        });
        if(measure)System.out.println("COH_RUNTIME_EXTRACTION_GC_COUNT "+(collections()-before));
        System.out.println("COH_RUNTIME_EXTRACT_V1 PASS");
    }
}
