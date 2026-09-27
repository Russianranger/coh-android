package io.github.russianranger.cohdiagnostic;

import java.io.File;

/** Uses the APK's exact parser for CI rootfs, Wine and PostgreSQL extraction. */
public final class ExtractRuntimeHost {
    public static void main(String[] args) throws Exception {
        if(args.length<2||args.length>3)
            throw new IllegalArgumentException("Usage: ExtractRuntimeHost ARCHIVE EMPTY_DEST [INTERRUPT_AFTER_COUNT]");
        final int cancelAfter=args.length==3?Integer.parseInt(args[2]):-1;
        if(cancelAfter==0)Thread.currentThread().interrupt();
        TarExtractor.extract(new File(args[0]),new File(args[1]),count->{
            if(cancelAfter>0&&count>=cancelAfter)Thread.currentThread().interrupt();
        });
        System.out.println("COH_RUNTIME_EXTRACT_V1 PASS");
    }
}
