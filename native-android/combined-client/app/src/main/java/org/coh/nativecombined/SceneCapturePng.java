package org.coh.nativecombined;

import java.io.IOException;
import java.io.OutputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.zip.Adler32;
import java.util.zip.CRC32;

/** PNG with stored DEFLATE blocks: one bounded scanline and64B headers.
 * It never allocates an encoded image, Bitmap, Deflater or whole-window image. */
final class SceneCapturePng {
    static final int MAX_BYTES=51+360*(640*4+18);
    private SceneCapturePng(){}
    static final class Info {
        final int bytes;final long crc;final String sha256;
        Info(int n,long c,String s){bytes=n;crc=c;sha256=s;}
    }
    private static void validate(byte[] raw,int width,int height)throws IOException {
        if(raw==null||width<1||width>640||height<1||height>360||raw.length!=128+width*height*4)
            throw new IOException("Scene PNG dimensions differ");
    }
    static Info measure(byte[] raw,int width,int height)throws IOException {
        validate(raw,width,height);
        final MessageDigest hash;
        try{hash=MessageDigest.getInstance("SHA-256");}catch(NoSuchAlgorithmException unavailable){throw new IOException(unavailable);}
        final CRC32 crc=new CRC32();final int[] count={0};
        OutputStream sink=new OutputStream(){
            @Override public void write(int b){hash.update((byte)b);crc.update(b);count[0]++;}
            @Override public void write(byte[] b,int at,int n){hash.update(b,at,n);crc.update(b,at,n);count[0]+=n;}
        };
        write(raw,width,height,sink);
        if(count[0]!=51+height*(width*4+18)||count[0]>MAX_BYTES)throw new IOException("Scene PNG bound differs");
        StringBuilder hex=new StringBuilder(64);for(byte b:hash.digest()){
            hex.append(Character.forDigit((b>>>4)&15,16)).append(Character.forDigit(b&15,16));
        }
        return new Info(count[0],crc.getValue(),hex.toString());
    }
    static void write(byte[] raw,int width,int height,OutputStream out)throws IOException {
        validate(raw,width,height);if(out==null)throw new IOException("Scene PNG destination unavailable");
        byte[] head=new byte[64],row=new byte[1+width*4];
        byte[] signature={(byte)137,80,78,71,13,10,26,10};out.write(signature);
        put(head,0,width);put(head,4,height);head[8]=8;head[9]=6;
        chunk(out,"IHDR",head,0,13);
        CRC32 crc=new CRC32();Adler32 adler=new Adler32();
        for(int y=0;y<height;y++){
            row[0]=0;System.arraycopy(raw,128+(height-1-y)*width*4,row,1,width*4);adler.update(row);
            int prefix=y==0?2:0,suffix=y==height-1?4:0;
            put(head,0,prefix+5+row.length+suffix);type(head,4,"IDAT");out.write(head,0,8);crc.reset();crc.update(head,4,4);
            int at=0;if(y==0){head[at++]=0x78;head[at++]=1;}
            head[at++]=(byte)(y==height-1?1:0);head[at++]=(byte)row.length;head[at++]=(byte)(row.length>>>8);
            int inverse=65535-row.length;head[at++]=(byte)inverse;head[at++]=(byte)(inverse>>>8);
            out.write(head,0,at);crc.update(head,0,at);out.write(row);crc.update(row);
            if(suffix!=0){put(head,0,adler.getValue());out.write(head,0,4);crc.update(head,0,4);}
            put(head,0,crc.getValue());out.write(head,0,4);
        }
        chunk(out,"IEND",head,0,0);
    }
    private static void chunk(OutputStream out,String type,byte[] data,int at,int bytes)throws IOException {
        byte[] head=new byte[12];put(head,0,bytes);type(head,4,type);out.write(head,0,8);
        CRC32 crc=new CRC32();crc.update(head,4,4);crc.update(data,at,bytes);out.write(data,at,bytes);
        put(head,0,crc.getValue());out.write(head,0,4);
    }
    private static void type(byte[] b,int at,String type){for(int i=0;i<4;i++)b[at+i]=(byte)type.charAt(i);}
    private static void put(byte[] b,int at,long value){for(int i=0;i<4;i++)b[at+i]=(byte)(value>>>(24-i*8));}
}
