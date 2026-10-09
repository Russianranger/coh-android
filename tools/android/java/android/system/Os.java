package android.system;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.attribute.PosixFilePermission;
import java.util.EnumSet;

/** Linux host adapter for the production Android tar extractor, never packaged. */
public final class Os {
    public static void chmod(String path,int mode) throws IOException {
        EnumSet<PosixFilePermission> permissions=EnumSet.noneOf(PosixFilePermission.class);
        PosixFilePermission[] flags=PosixFilePermission.values();
        for(int i=0;i<9;i++)if((mode&(1<<(8-i)))!=0)permissions.add(flags[i]);
        Files.setPosixFilePermissions(Paths.get(path),permissions);
    }
    public static void symlink(String target,String link) throws IOException {
        Files.createSymbolicLink(Paths.get(link),Paths.get(target));
    }
}
