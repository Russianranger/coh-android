"""Execute the shipped Surface capture pipeline with controlled Android adapters.

PixelCopy and Bitmap are platform seams; scheduling, ownership, bounds, encoding,
SHA-256, diversity checks and main-thread delivery execute the actual Java source.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
PACKAGE = 'io.github.russianranger.cohclientinteractive'

STUBS = {
    'android/content/Context.java': 'package android.content; public class Context {}',
    'android/os/Looper.java': r'''package android.os;
public class Looper {
 static final Thread owner=Thread.currentThread(); static final Looper MAIN=new Looper();
 public static Looper getMainLooper(){return MAIN;}
 public static Looper myLooper(){return Thread.currentThread()==owner?MAIN:null;}
}''',
    'android/os/SystemClock.java': r'''package android.os;
public class SystemClock {public static volatile long now=100;public static long uptimeMillis(){return now;}}''',
    'android/os/Debug.java': r'''package android.os;
public class Debug {public static long threadCpuTimeNanos(){return System.nanoTime();}}''',
    'android/os/Handler.java': r'''package android.os;
import java.util.*;
public class Handler {
 static class Entry {final Runnable r;final long at;Entry(Runnable r,long at){this.r=r;this.at=at;}}
 static final List<Entry> queue=new ArrayList<>();public Handler(Looper ignored){}
 public boolean post(Runnable r){return postAtTime(r,SystemClock.now);}
 public boolean postAtTime(Runnable r,long at){synchronized(queue){queue.add(new Entry(r,at));}return true;}
 public void removeCallbacks(Runnable r){synchronized(queue){queue.removeIf(e->e.r==r);}}
 public static void drain(){
  if(Looper.myLooper()!=Looper.getMainLooper())throw new AssertionError("not main");
  for(int guard=0;guard<10000;guard++){
   Runnable next=null;synchronized(queue){for(int i=0;i<queue.size();i++)if(queue.get(i).at<=SystemClock.now){next=queue.remove(i).r;break;}}
   if(next==null)return;next.run();
  }throw new AssertionError("unbounded main queue");
 }
}''',
    'android/graphics/Color.java': r'''package android.graphics;
public class Color {public static final int BLACK=0xff000000;
 public static int red(int p){return p>>>16&255;}public static int green(int p){return p>>>8&255;}public static int blue(int p){return p&255;}}''',
    'android/graphics/Paint.java': 'package android.graphics; public class Paint {public void setFilterBitmap(boolean b){}public void setDither(boolean b){}}',
    'android/graphics/RectF.java': r'''package android.graphics;
public class RectF {public final float left,top,right,bottom;public RectF(float l,float t,float r,float b){left=l;top=t;right=r;bottom=b;}}''',
    'android/graphics/Bitmap.java': r'''package android.graphics;
import java.io.*;import java.util.*;import java.util.concurrent.*;import android.os.Looper;
public class Bitmap {
 public enum Config {ARGB_8888}public enum CompressFormat {PNG}
 public static final List<Bitmap> all=Collections.synchronizedList(new ArrayList<>());
 public static volatile CountDownLatch encodeEntered,encodeProceed;
 public static volatile boolean failEncode,overflow;public static volatile boolean scannedOnMain,encodedOnMain;
 public final int width,height;public int[] pixels;public int recycled;
 Bitmap(int w,int h){width=w;height=h;pixels=new int[w*h];all.add(this);}
 public static Bitmap createBitmap(int w,int h,Config config){return new Bitmap(w,h);}
 public int getWidth(){return width;}public int getHeight(){return height;}
 public void setPixels(int[] p,int offset,int stride,int x,int y,int w,int h){pixels=p.clone();}
 public int getPixel(int x,int y){if(Looper.myLooper()==Looper.getMainLooper())scannedOnMain=true;return pixels[y*width+x];}
 public boolean compress(CompressFormat f,int q,OutputStream out){
  encodedOnMain=Looper.myLooper()==Looper.getMainLooper();
  if(encodeEntered!=null)encodeEntered.countDown();
  try{if(encodeProceed!=null&&!encodeProceed.await(5,TimeUnit.SECONDS))throw new AssertionError("encoder was not released");
   if(failEncode)return false;
   if(overflow)out.write(new byte[2*1024*1024+1]);
   else {out.write(new byte[]{(byte)137,80,78,71});for(int i=0;i<128;i++)out.write(pixels[i%pixels.length]);}
   return true;
  }catch(IOException|InterruptedException e){throw new IllegalStateException(e);}
 }
 public synchronized void recycle(){if(++recycled!=1)throw new AssertionError("bitmap recycled twice");}
}''',
    'android/graphics/Canvas.java': r'''package android.graphics;
import android.view.SurfaceView;
public class Canvas {
 final SurfaceView.TestHolder holder;public Canvas(SurfaceView.TestHolder h){holder=h;}
 public int getWidth(){return holder.width;}public int getHeight(){return holder.height;}
 public void drawColor(int c){}public void drawBitmap(Bitmap b,Object source,RectF destination,Paint p){holder.marker=b.pixels[0];holder.pixels=b.pixels.clone();holder.frameWidth=b.width;holder.frameHeight=b.height;}
}''',
    'android/view/SurfaceHolder.java': r'''package android.view;import android.graphics.Canvas;
public interface SurfaceHolder {
 interface Callback {void surfaceCreated(SurfaceHolder h);void surfaceChanged(SurfaceHolder h,int f,int w,int z);void surfaceDestroyed(SurfaceHolder h);}
 void addCallback(Callback c);Canvas lockCanvas();void unlockCanvasAndPost(Canvas c);
}''',
    'android/view/SurfaceView.java': r'''package android.view;
import android.content.Context;import android.graphics.Canvas;
public class SurfaceView {
 public static class TestHolder implements SurfaceHolder {
  public int width=800,height=600,marker,posts,frameWidth,frameHeight;public int[] pixels;
  public void addCallback(Callback c){}public Canvas lockCanvas(){return new Canvas(this);}public void unlockCanvasAndPost(Canvas c){posts++;}
 }
 public static class Parent {public void requestDisallowInterceptTouchEvent(boolean b){}}
 final TestHolder holder=new TestHolder();public SurfaceView(Context context){}
 public TestHolder getHolder(){return holder;}public void setWillNotDraw(boolean b){}
 public int getWidth(){return holder.width;}public int getHeight(){return holder.height;}public Parent getParent(){return null;}
 public boolean onTouchEvent(MotionEvent e){return false;}public boolean performClick(){return true;}
 public void onWindowFocusChanged(boolean b){}protected void onAttachedToWindow(){}protected void onDetachedFromWindow(){}
}''',
    'android/view/MotionEvent.java': r'''package android.view;
public class MotionEvent {
 public static final int ACTION_DOWN=0,ACTION_UP=1,ACTION_MOVE=2,ACTION_CANCEL=3,ACTION_POINTER_DOWN=5,ACTION_POINTER_UP=6;
 public int getActionMasked(){return 0;}public float getX(){return 0;}public float getY(){return 0;}
 public float getX(int n){return 0;}public float getY(int n){return 0;}public int getPointerId(int n){return 0;}
 public int findPointerIndex(int n){return 0;}public int getActionIndex(){return 0;}
}''',
    'android/view/PixelCopy.java': r'''package android.view;
import android.graphics.Bitmap;import android.os.Handler;
public class PixelCopy {
 public static final int SUCCESS=0;public interface OnPixelCopyFinishedListener {void onPixelCopyFinished(int result);}
 public static OnPixelCopyFinishedListener callback;public static Bitmap bitmap;public static int requests;
 public static boolean reject;static int[] source;static int sw,sh;
 public static void request(SurfaceView view,Bitmap target,OnPixelCopyFinishedListener cb,Handler handler){
  requests++;if(reject)throw new IllegalStateException("request rejected");
  if(callback!=null)throw new AssertionError("overlapping PixelCopy");
  callback=cb;bitmap=target;source=view.getHolder().pixels.clone();sw=view.getHolder().frameWidth;sh=view.getHolder().frameHeight;
 }
 public static void complete(int result){
  if(callback==null)throw new AssertionError("no copy");
  for(int y=0;y<bitmap.height;y++)for(int x=0;x<bitmap.width;x++)bitmap.pixels[y*bitmap.width+x]=source[(y*sh/bitmap.height)*sw+x*sw/bitmap.width];
  OnPixelCopyFinishedListener done=callback;callback=null;done.onPixelCopyFinished(result);
 }
}''',
    PACKAGE.replace('.', '/') + '/InteractiveRfbClient.java': 'package '+PACKAGE+'; public class InteractiveRfbClient {public static final int MAX_WIDTH=1920,MAX_HEIGHT=1200;}',
}

HOST = r'''
package io.github.russianranger.cohclientinteractive;
import android.content.*;import android.os.*;import android.view.*;import android.graphics.*;
import java.lang.reflect.*;import java.util.*;import java.util.concurrent.*;import java.security.*;
public class SurfaceCaptureHost {
 static final String FIRST="0123456789abcdef0123456789abcdef",SECOND="1123456789abcdef0123456789abcdef";
 static class Evidence implements ClientSurface.Listener {
  final List<ClientSurface.Capture> captures=new ArrayList<>();final List<String> errors=new ArrayList<>();
  public void onCapture(ClientSurface.Capture c){need(Looper.myLooper()==Looper.getMainLooper(),"delivery offmain");captures.add(c);}
  public void onCaptureError(String e){need(Looper.myLooper()==Looper.getMainLooper(),"error offmain");errors.add(e);}
 }
 static void need(boolean value,String reason){if(!value)throw new AssertionError(reason);}
 static Object field(ClientSurface s,String name)throws Exception {Field f=ClientSurface.class.getDeclaredField(name);f.setAccessible(true);return f.get(s);}
 static int[] pixels(int marker){int[] p=new int[128*96];for(int i=0;i<p.length;i++)p[i]=0xff000000|((i%16)*16)<<16|((i/16%16)*16)<<8|(i/256%16)*16;p[0]=marker;return p;}
 static void frame(ClientSurface s,int marker,long sequence){s.setFrame(pixels(marker),128,96,sequence);Handler.drain();}
 static void waitIdle(ClientSurface s)throws Exception {
  long deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(5);
  while(field(s,"captureWork")!=null&&System.nanoTime()<deadline){Handler.drain();Thread.sleep(1);}
  Handler.drain();need(field(s,"captureWork")==null,"capture never completed");
 }
 static void startHold(){Bitmap.encodeEntered=new CountDownLatch(1);Bitmap.encodeProceed=new CountDownLatch(1);}
 static void encoded(){try{need(Bitmap.encodeEntered.await(3,TimeUnit.SECONDS),"encoder never started");}catch(InterruptedException e){throw new AssertionError(e);}}
 static void release(){Bitmap.encodeProceed.countDown();}
 static void copied(){SystemClock.now+=17;PixelCopy.complete(PixelCopy.SUCCESS);}
 static void oneRecycle(Bitmap b){need(b.recycled==1,"capture bitmap ownership leak");}
 static void hash(ClientSurface.Capture c)throws Exception {byte[] digest=MessageDigest.getInstance("SHA-256").digest(c.png);StringBuilder hex=new StringBuilder();for(byte b:digest)hex.append(String.format("%02x",b&255));need(c.sha256.equals(hex.toString()),"PNG hash does not close");}
 public static void main(String[] args)throws Exception {
  ClientSurface surface=new ClientSurface(new Context());Evidence evidence=new Evidence();
  surface.setSession(FIRST);surface.setCaptureListener(evidence);surface.surfaceCreated(surface.getHolder());Handler.drain();
  if(args[0].equals("request_failure"))PixelCopy.reject=true;
  frame(surface,0xff101010,1);Bitmap owned=Bitmap.all.get(Bitmap.all.size()-1);
  switch(args[0]) {
  case "resume": {
   startHold();for(int i=2;i<=12;i++)frame(surface,0xff101010+i,i);
   need(surface.getHolder().posts==1,"copy did not freeze presentation");
   copied();encoded();Handler.drain();
   need(surface.getHolder().posts>1&&surface.getHolder().marker==0xff10101c,"latest presentation waits for PNG");
   need(evidence.captures.isEmpty(),"slow encoder already delivered");
   SystemClock.now+=500;for(int i=13;i<90;i++)frame(surface,0xff101010+i,i);
   need(PixelCopy.requests==1,"encoder admitted capture queue growth");
   need(!Bitmap.scannedOnMain&&!Bitmap.encodedOnMain,"expensive capture work on UI");
   SystemClock.now+=200;release();waitIdle(surface);
   need(evidence.captures.size()==1,"capture not retained");ClientSurface.Capture c=evidence.captures.get(0);
   need(c.sequence==1&&c.capturedAtUptimeMillis==117&&c.nonUniform,"copy frame identity or diversity changed");
   need(c.pixelCopyWallMs==17&&c.presentationFreezeMs==17&&c.encodingWallMs>=700,"incorrect capture costs");
   need(!c.encodingOnUiThread&&c.encodeQueueWallMs>=0&&c.encodingCpuMs>=0,"incorrect encoder telemetry");
   need(c.pendingFramesPeak==1&&c.framesCoalescedDuringCopy==10,"pending frames not bounded/measured");
   hash(c);oneRecycle(owned);break;
  }
  case "session_copy":
   surface.setSession(SECOND);frame(surface,0xff202020,2);
   need(surface.getHolder().marker==0xff202020,"stale copy freezes replacement session");
   copied();waitIdle(surface);need(evidence.captures.isEmpty(),"stale copy established readiness");oneRecycle(owned);break;
  case "session_encode":
   startHold();copied();encoded();surface.setSession(SECOND);Handler.drain();release();waitIdle(surface);
   need(evidence.captures.isEmpty(),"stale encoded session delivered");oneRecycle(owned);break;
  case "listener": {
   startHold();copied();encoded();surface.setCaptureListener(null);surface.setCaptureListener(evidence);Handler.drain();release();waitIdle(surface);
   need(evidence.captures.isEmpty(),"same listener resurrected old capture");oneRecycle(owned);break;
  }
  case "generation":
   startHold();copied();encoded();surface.surfaceChanged(surface.getHolder(),0,800,600);Handler.drain();release();waitIdle(surface);
   need(evidence.captures.isEmpty(),"stale surface established readiness");oneRecycle(owned);break;
  case "destroy":
   surface.surfaceDestroyed(surface.getHolder());copied();waitIdle(surface);
   need(evidence.captures.isEmpty(),"destroyed surface delivered evidence");oneRecycle(owned);break;
  case "detach": {
   startHold();copied();encoded();Method detach=ClientSurface.class.getDeclaredMethod("onDetachedFromWindow");detach.setAccessible(true);detach.invoke(surface);
   release();waitIdle(surface);need(evidence.captures.isEmpty(),"detached view delivered");oneRecycle(owned);break;
  }
  case "clear":
   surface.clearFrames();copied();waitIdle(surface);need(evidence.captures.isEmpty(),"cleared session delivered");oneRecycle(owned);break;
  case "pixel_failure":
   SystemClock.now+=20;PixelCopy.complete(7);waitIdle(surface);
   need(evidence.errors.equals(Arrays.asList("PixelCopy result 7")),"copy failure not reported");oneRecycle(owned);break;
  case "encode_failure":
   Bitmap.failEncode=true;copied();waitIdle(surface);need(evidence.captures.isEmpty()&&evidence.errors.size()==1,"PNG failure delivered proof");oneRecycle(owned);break;
  case "png_bound":
   Bitmap.overflow=true;copied();waitIdle(surface);need(evidence.captures.isEmpty()&&evidence.errors.size()==1,"unbounded PNG accepted");oneRecycle(owned);break;
  case "reject":
   ((ThreadPoolExecutor)field(surface,"captureEncoder")).shutdown();copied();waitIdle(surface);
   need(evidence.captures.isEmpty()&&evidence.errors.size()==1,"encoder rejection did not settle");oneRecycle(owned);break;
  case "request_failure":
   need(field(surface,"captureWork")==null&&evidence.errors.size()==1,"PixelCopy request failure left ownership busy");oneRecycle(owned);
   PixelCopy.reject=false;SystemClock.now+=1001;frame(surface,0xff202020,2);copied();waitIdle(surface);
   need(evidence.captures.size()==1&&evidence.captures.get(0).sequence==2,"request failure prevented fresh retry");break;
  case "duplicate_callback": {
   startHold();PixelCopy.OnPixelCopyFinishedListener original=PixelCopy.callback;copied();encoded();
   original.onPixelCopyFinished(PixelCopy.SUCCESS);need(owned.recycled==0,"duplicate callback recycled under encoder");
   release();waitIdle(surface);need(evidence.captures.size()==1,"duplicate callback delivered twice");oneRecycle(owned);break;
  }
  case "recreate": {
   startHold();copied();encoded();Method detach=ClientSurface.class.getDeclaredMethod("onDetachedFromWindow");detach.setAccessible(true);detach.invoke(surface);
   ClientSurface replacement=new ClientSurface(new Context());Evidence next=new Evidence();replacement.setSession(SECOND);replacement.setCaptureListener(next);replacement.surfaceCreated(replacement.getHolder());Handler.drain();
   frame(replacement,0xff303030,2);Bitmap second=PixelCopy.bitmap;copied();waitIdle(replacement);
   ThreadPoolExecutor encoder=(ThreadPoolExecutor)field(surface,"captureEncoder");
   need(encoder==field(replacement,"captureEncoder")&&encoder.getPoolSize()==1&&encoder.getQueue().isEmpty(),"recreation grew encoder workers/queue");
   need(next.captures.isEmpty()&&next.errors.size()==1,"busy global encoder admitted another bitmap");oneRecycle(second);
   release();waitIdle(surface);oneRecycle(owned);need(evidence.captures.isEmpty(),"retired view delivered stale proof");
   SystemClock.now+=1001;frame(replacement,0xff404040,3);copied();waitIdle(replacement);
   need(next.captures.size()==1&&next.captures.get(0).sequence==3,"recreated view cannot collect fresh evidence");break;
  }
  case "fresh":
   copied();waitIdle(surface);
   for(int i=2;i<=3;i++){SystemClock.now+=1001;frame(surface,0xff303030+i,i);copied();waitIdle(surface);}
   need(evidence.captures.size()==3,"three fresh readiness samples lost");
   for(int i=1;i<3;i++){ClientSurface.Capture a=evidence.captures.get(i-1),b=evidence.captures.get(i);need(b.sequence>a.sequence&&b.capturedAtUptimeMillis-a.capturedAtUptimeMillis>=1000,"sample freshness changed");}
   for(ClientSurface.Capture c:evidence.captures)hash(c);break;
  default:throw new AssertionError("unknown scenario");
  }
  System.out.println("PASS "+args[0]);
 }
}'''


class ClientSurfaceCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name)
        sources = []
        for name, content in STUBS.items():
            path = cls.output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            sources.append(str(path))
        host = cls.output / 'SurfaceCaptureHost.java'
        host.write_text(HOST)
        sources += [str(JAVA / 'ClientSurface.java'), str(JAVA / 'ClientInput.java'), str(host)]
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', str(cls.output), *sources], check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def scenario(self, name):
        result = subprocess.run(['java', '-cp', str(self.output), PACKAGE + '.SurfaceCaptureHost', name],
                                check=True, capture_output=True, text=True, timeout=12)
        self.assertEqual(result.stdout.strip(), 'PASS ' + name)


for _name in ('resume', 'session_copy', 'session_encode', 'listener', 'generation', 'destroy',
              'detach', 'clear', 'pixel_failure', 'encode_failure', 'png_bound', 'reject',
              'request_failure', 'duplicate_callback', 'recreate', 'fresh'):
    setattr(ClientSurfaceCaptureTests, 'test_' + _name,
            lambda self, scenario=_name: self.scenario(scenario))


if __name__ == '__main__':
    unittest.main()
