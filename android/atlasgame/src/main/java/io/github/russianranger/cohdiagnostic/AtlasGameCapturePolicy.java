package io.github.russianranger.cohdiagnostic;

import java.io.IOException;

/** Exact bounded capture names shared by verification and export. */
final class AtlasGameCapturePolicy {
    static long captureLimit(String group,String name) throws IOException {
        if("game-captures".equals(group)) {
            if("mapserver-progress.json".equals(name))return 512L*1024;
            if(name.matches("(first|second)-(ready|result)\\.json"))return 16384;
            if(name.matches("(first|second)-events\\.jsonl"))return 8L*1024*1024;
            if(name.matches("(first|second)-console\\.txt"))return 16L*1024*1024;
            if(name.matches("(first|restart|second)-snapshot\\.json"))return 1024*1024;
        } else if("game-service-captures".equals(group)) {
            if(name.matches("(first|restart)-(dbserver|atlas)-stdout\\.txt"))return 6L*1024*1024;
            if(name.matches("log-(00[1-9]|0[12][0-9]|03[0-2])\\.txt"))return 4L*1024*1024;
            if("manifest.json".equals(name))return 128*1024;
        } else if("game-hang-captures".equals(group)) {
            if("snapshot.json".equals(name))return 1024*1024;
            if("windows-contexts.jsonl".equals(name))return 384*1024;
            if("manifest.json".equals(name))return 64*1024;
        }
        throw new IOException("Unexpected capture name");
    }
    private AtlasGameCapturePolicy(){}
}
