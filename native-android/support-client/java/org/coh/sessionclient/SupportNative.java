package org.coh.sessionclient;
import android.content.res.AssetManager;
public final class SupportNative {
 static { System.loadLibrary("coh_support_client"); }
 private SupportNative() {}
 public static native boolean initialize(long h,AssetManager manager,byte[] punch,byte[] jump,byte[] fall);
 public static native void trigger(long h);
 public static native boolean touch(long h,int action,int pointer,float x,float y);
 public static native boolean key(long h,int key,int action,int repeat,int shift);
 public static native void text(long h,byte[] utf8);
 public static native String snapshot(long h);
}
