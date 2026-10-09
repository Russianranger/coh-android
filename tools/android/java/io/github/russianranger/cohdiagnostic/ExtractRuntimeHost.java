package io.github.russianranger.cohdiagnostic;

import java.io.File;
import java.io.IOException;
import java.io.InterruptedIOException;
import java.lang.management.GarbageCollectorMXBean;
import java.lang.management.ManagementFactory;

/** Uses the APK's exact parser for CI rootfs, Wine and PostgreSQL extraction. */
public final class ExtractRuntimeHost {
    private static void controlled(String mode,File archive,File root)throws Exception {
        final long[] time={0},samples={0};
        final boolean[] paused={false};
        final File observed=new File(root,mode.equals("token-hardlink")?"copy":"large");
        SetupMemoryGuard control=new SetupMemoryGuard(()->{
            samples[0]++;
            boolean low=mode.equals("memory-low")||mode.equals("memory-recover")&&samples[0]<=3
                    ||mode.equals("memory-member")&&observed.length()>=65536;
            return new SetupMemoryGuard.Sample(low?0:3L<<30,4L<<30,128L<<20,low,8L<<20,64L<<20);
        },()->time[0],millis->time[0]+=millis,()->{
            if(mode.startsWith("token-")&&observed.length()>=65536)
                throw new InterruptedIOException("Operation token stopped extraction");
        },value->{paused[0]=value;});
        try {
            TarExtractor.extract(archive,root,count->{},control);control.finishWrites();
            if(paused[0])throw new IOException("Pressure observer did not resume");
            System.out.println("COH_RUNTIME_EXTRACT_V1 PASS");
        } catch(Exception failure) {
            System.out.println("COH_SETUP_CONTROL_FAILURE "+failure.getClass().getSimpleName()
                    +" thread_interrupted="+Thread.currentThread().isInterrupted());
            throw failure;
        } finally {
            java.util.Map<String,Object> receipt=control.receipt();
            System.out.println("COH_SETUP_CONTROL written="+receipt.get("written_bytes")
                    +" syncs="+receipt.get("file_syncs")+" dirty="+receipt.get("active_dirty_bytes")
                    +" max_dirty="+receipt.get("maximum_active_dirty_bytes")+" paused="+receipt.get("pressure_paused_ms")
                    +" samples="+receipt.get("samples")+" status="+receipt.get("status"));
        }
    }
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
        if(args.length==3&&(args[2].startsWith("token-")||args[2].startsWith("memory-"))) {
            controlled(args[2],new File(args[0]),new File(args[1]));return;
        }
        if(args.length==3&&args[2].equals("remove")) {TarExtractor.remove(new File(args[1]));System.out.println("COH_RUNTIME_REMOVE_V1 PASS");return;}
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
