package io.github.russianranger.cohclientinteractive;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Comparator;

/** Actual JNI load/handle/error/lifetime controls on the host VM, no Game. */
public final class NativeLiveDirectoryFixture {
    private static int controls;
    private interface Action { void run() throws Exception; }
    private static void require(boolean condition) {
        if (!condition) throw new AssertionError("JNI fixture control " + controls);
        controls++;
    }
    private static void refuses(Action action, String phase) throws Exception {
        try { action.run(); } catch (IOException expected) {
            require(expected.getMessage().contains("COH_LIVE_FAIL") && expected.getMessage().contains("phase=" + phase));
            return;
        }
        throw new AssertionError("Missing JNI refusal " + phase);
    }
    private static long attr(Path root, String key) throws IOException {
        return ((Number)Files.getAttribute(root, "unix:" + key)).longValue();
    }
    public static void main(String[] args) throws Exception {
        System.load(Path.of(args[0]).toAbsolutePath().toString());
        Path root=Files.createTempDirectory("coh-live-jni-fixture-");
        long namespace=0;
        try {
            Path items=Files.createDirectory(root.resolve("items"));
            for(int i=0;i<180;i++)Files.writeString(items.resolve(String.format("f%05d",i)),"old");
            String[] guest={"/data"},host={root.toString()};
            long[] devices={attr(root,"dev")},inodes={attr(root,"ino")};int[] owners={(int)attr(root,"uid")};
            byte[] op=new byte[16],dir=new byte[16];for(int i=0;i<16;i++){op[i]=(byte)i;dir[i]=(byte)(16+i);}
            refuses(() -> NativeLiveDirectory.nativeCreate(null,host,devices,inodes,owners,owners[0],1000,false,false),"create");
            refuses(() -> NativeLiveDirectory.nativeCreate(guest,host,new long[0],inodes,owners,owners[0],1000,false,false),"create");
            for(String bad:new String[]{null,"","/caf\u00e9"}) {
                refuses(() -> NativeLiveDirectory.nativeCreate(new String[]{bad},host,devices,inodes,owners,owners[0],1000,false,false),"string");
                refuses(() -> NativeLiveDirectory.nativeCreate(guest,new String[]{bad},devices,inodes,owners,owners[0],1000,false,false),"string");
            }
            namespace=NativeLiveDirectory.nativeCreate(guest,host,devices,inodes,owners,owners[0],1000,false,false);
            require(namespace!=0);final long ns=namespace;
            refuses(() -> NativeLiveDirectory.nativeCreate(guest,host,devices,inodes,owners,owners[0],1000,false,false),"create");
            refuses(() -> NativeLiveDirectory.nativeOpen(ns,"/data/items",new byte[15],dir),"open");
            refuses(() -> NativeLiveDirectory.nativeOpen(ns,"/foreign",op,dir),"open");
            long cursor=NativeLiveDirectory.nativeOpen(ns,"/data/items",op,dir);
            long[] identity=NativeLiveDirectory.nativeIdentity(cursor);
            require(identity.length==3&&identity[0]==attr(items,"dev")&&identity[1]==attr(items,"ino")&&identity[2]==owners[0]);
            require(NativeLiveDirectory.nativeCanonicalGuestPath(cursor).equals("/data/items"));
            require(NativeLiveDirectory.nativeStats(ns)[0]==0);
            byte[] first=NativeLiveDirectory.nativeNext(cursor);
            ByteBuffer header=ByteBuffer.wrap(first).order(ByteOrder.LITTLE_ENDIAN);
            require(first.length<=27944&&header.getInt(40)==0&&header.getInt(44)==0&&header.getInt(48)>0&&header.getInt(52)==0);
            Files.writeString(items.resolve("f00170"),"current JNI metadata payload");
            boolean found=false;int sequence=1,ordinal=header.getInt(48);
            while(true){
                byte[] frame=NativeLiveDirectory.nativeNext(cursor);ByteBuffer b=ByteBuffer.wrap(frame).order(ByteOrder.LITTLE_ENDIAN);
                require(b.getInt(40)==sequence++&&b.getInt(44)==ordinal&&b.getInt(60)==frame.length);
                int count=b.getInt(48);ordinal+=count;
                for(int row=0;row<count;row++){
                    int start=64+row*328+8,n=0;while(frame[start+44+n]!=0)n++;
                    String name=new String(frame,start+44,n,java.nio.charset.StandardCharsets.US_ASCII);
                    if(name.equals("f00170")){require(b.getInt(start+32)==28);found=true;}
                }
                if(b.getInt(52)==1)break;
            }
            require(found);
            refuses(() -> NativeLiveDirectory.nativeNext(cursor),"next");
            NativeLiveDirectory.nativeCloseCursor(cursor);
            refuses(() -> NativeLiveDirectory.nativeNext(cursor),"next");
            refuses(() -> NativeLiveDirectory.nativeCloseCursor(cursor),"closeCursor");
            long reopened=NativeLiveDirectory.nativeOpen(ns,"/data/items",op,dir);require(reopened!=cursor);
            NativeLiveDirectory.nativeCloseNamespace(ns);namespace=0;
            refuses(() -> NativeLiveDirectory.nativeNext(reopened),"next");
            refuses(() -> NativeLiveDirectory.nativeCloseNamespace(ns),"closeNamespace");
            namespace=NativeLiveDirectory.nativeCreate(guest,host,devices,inodes,owners,owners[0],1000,false,false);require(namespace!=ns);
            refuses(() -> NativeLiveDirectory.nativeStats(ns),"stats");
            System.out.println("{\"schema\":\"coh-live-host-JNI-fixture-v1\",\"controls_passed\":"+controls+",\"failures\":0,\"shipping_admission\":false,\"android_vm_or_game_qualified\":false}");
        } finally {
            if(namespace!=0)NativeLiveDirectory.nativeCloseNamespace(namespace);
            try(var files=Files.walk(root)){for(Path item:files.sorted(Comparator.reverseOrder()).toList())Files.delete(item);}
        }
    }
}
