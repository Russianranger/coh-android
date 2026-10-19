package org.coh.qualification.capture;

import android.accessibilityservice.AccessibilityServiceInfo;
import android.app.Instrumentation;
import android.app.UiAutomation;
import android.content.Context;
import android.graphics.Point;
import android.graphics.Rect;
import android.os.Bundle;
import android.os.SystemClock;
import android.util.Xml;
import android.view.Display;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityNodeInfo;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.security.MessageDigest;
import org.xmlpull.v1.XmlSerializer;

/** Disposable qualification tool. It never starts, instruments or stops CoH. */
public final class UiSnapshotInstrumentation extends Instrumentation {
    private static final int MAX_NODES=8192, MAX_DEPTH=64, MAX_BYTES=8*1024*1024;
    private static final int ROOT_ATTEMPTS=32, ROOT_WAIT_MS=3000;
    private static final int SNAPSHOT_ATTEMPTS=3;
    private String nonce;
    private int nodes,totalNodes;
    private long captureStarted;
    private final Rect displayBounds=new Rect();
    private static final class SnapshotChangedException extends IOException {
        SnapshotChangedException(){super("Snapshot child unavailable during traversal");}
    }
    private static final class BoundedOutput extends OutputStream {
        final ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        @Override public void write(int value)throws IOException {
            if(bytes.size()>=MAX_BYTES)throw new IOException("Snapshot byte limit");bytes.write(value);
        }
        @Override public void write(byte[] value,int offset,int count)throws IOException {
            if(count<0||count>MAX_BYTES-bytes.size())throw new IOException("Snapshot byte limit");
            bytes.write(value,offset,count);
        }
    }
    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments);nonce=arguments==null?null:arguments.getString("nonce");start();
    }
    private static String text(CharSequence value)throws IOException {
        if(value==null)return "";
        if(value.length()>65536)throw new IOException("Snapshot attribute limit");return value.toString();
    }
    private static void attr(XmlSerializer xml,String key,Object value)throws Exception {
        xml.attribute("",key,String.valueOf(value));
    }
    private void node(XmlSerializer xml,AccessibilityNodeInfo value,int index,int depth)throws Exception {
        if(SystemClock.elapsedRealtime()-captureStarted>ROOT_WAIT_MS)throw new IOException("Snapshot work deadline exceeded");
        if(depth>MAX_DEPTH||++nodes>MAX_NODES)throw new IOException("Snapshot traversal limit");
        if(++totalNodes>MAX_NODES*SNAPSHOT_ATTEMPTS)throw new IOException("Snapshot total work limit");
        xml.startTag("","node");attr(xml,"index",index);
        attr(xml,"text",text(value.getText()));attr(xml,"resource-id",text(value.getViewIdResourceName()));
        attr(xml,"class",text(value.getClassName()));attr(xml,"package",text(value.getPackageName()));
        attr(xml,"content-desc",text(value.getContentDescription()));
        attr(xml,"checkable",value.isCheckable());attr(xml,"checked",value.isChecked());
        attr(xml,"clickable",value.isClickable());attr(xml,"enabled",value.isEnabled());
        attr(xml,"focusable",value.isFocusable());attr(xml,"focused",value.isFocused());
        attr(xml,"scrollable",value.isScrollable());attr(xml,"long-clickable",value.isLongClickable());
        attr(xml,"password",value.isPassword());attr(xml,"selected",value.isSelected());
        Rect bounds=new Rect();value.getBoundsInScreen(bounds);
        if(!bounds.intersect(displayBounds))bounds.setEmpty();
        attr(xml,"bounds",bounds.toShortString());
        int children=value.getChildCount();
        if(children<0||children>MAX_NODES)throw new IOException("Snapshot child limit");
        for(int i=0;i<children;i++) {
            if(SystemClock.elapsedRealtime()-captureStarted>ROOT_WAIT_MS)throw new IOException("Snapshot work deadline exceeded");
            AccessibilityNodeInfo child=value.getChild(i);
            if(child==null)throw new SnapshotChangedException();
            try{if(child.isVisibleToUser())node(xml,child,i,depth+1);}finally{child.recycle();}
        }
        xml.endTag("","node");
    }
    @Override public void onStart() {
        Bundle result=new Bundle();AccessibilityNodeInfo root=null;
        try {
            if(nonce==null||!nonce.matches("[0-9a-f]{32}"))throw new IOException("Invalid snapshot nonce");
            File target=new File(getTargetContext().getFilesDir(),"snapshot-"+nonce+".xml");
            if(target.exists())throw new IOException("Snapshot destination already exists");
            UiAutomation automation=getUiAutomation();
            AccessibilityServiceInfo info=automation.getServiceInfo();
            info.flags|=AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS|AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS;
            automation.setServiceInfo(info);
            long started=SystemClock.elapsedRealtime();
            captureStarted=started;
            // Dynamic frame/age labels need not become globally idle to expose
            // their current accessibility layout. No previous tree is reused.
            int rootAttempts=0;
            long rootWait=0;
            int snapshotAttempts=0;
            BoundedOutput output=new BoundedOutput();byte[] raw=null;
            // A child can disappear while SAF replaces its hierarchy. A typed
            // transient restarts the WHOLE fresh tree; no child is omitted.
            // One buffer is reset and reused, never retained across attempts.
            for(snapshotAttempts=1;snapshotAttempts<=SNAPSHOT_ATTEMPTS;snapshotAttempts++) {
              output.bytes.reset();nodes=0;
              try {
            // A newly connected accessibility service can temporarily have no
            // active root while a document picker restores the foreground
            // window. Poll only for a NEW root; never wait for global idle or
            // substitute a previous tree. The host also caps instrumentation.
            // ROOT_ACQUISITION_BEGIN
            while(rootAttempts<ROOT_ATTEMPTS) {
                rootAttempts++;root=automation.getRootInActiveWindow();
                rootWait=SystemClock.elapsedRealtime()-started;
                if(rootWait>ROOT_WAIT_MS)throw new IOException("Fresh active root deadline exceeded");
                if(root!=null)break;
                if(rootAttempts==ROOT_ATTEMPTS||rootWait==ROOT_WAIT_MS)break;
                SystemClock.sleep(Math.min(100,ROOT_WAIT_MS-rootWait));
            }
            if(root==null)throw new IOException("Fresh active root unavailable after bounded acquisition");
            // ROOT_ACQUISITION_END
            Display display=((WindowManager)getTargetContext().getSystemService(Context.WINDOW_SERVICE)).getDefaultDisplay();
            Point size=new Point();display.getRealSize(size);
            if(size.x<=0||size.y<=0||size.x>16384||size.y>16384)throw new IOException("Display bounds invalid");
            displayBounds.set(0,0,size.x,size.y);
            XmlSerializer xml=Xml.newSerializer();
            xml.setOutput(output,"UTF-8");xml.startDocument("UTF-8",true);xml.startTag("","hierarchy");
            attr(xml,"rotation",display.getRotation());attr(xml,"capture-nonce",nonce);
            attr(xml,"capture-method","fresh-ui-automation-active-root-without-global-idle");
            attr(xml,"capture-root-attempts",rootAttempts);attr(xml,"capture-root-wait-ms",rootWait);
            attr(xml,"capture-snapshot-attempts",snapshotAttempts);attr(xml,"capture-discarded-partial-trees",snapshotAttempts-1);
            node(xml,root,0,0);xml.endTag("","hierarchy");xml.endDocument();xml.flush();
            if(SystemClock.elapsedRealtime()-started>ROOT_WAIT_MS)throw new IOException("Snapshot work deadline exceeded");
            raw=output.bytes.toByteArray();break;
              }catch(SnapshotChangedException changed) {
                output.bytes.reset();
                long remaining=ROOT_WAIT_MS-(SystemClock.elapsedRealtime()-started);
                if(snapshotAttempts==SNAPSHOT_ATTEMPTS||remaining<=0)throw changed;
                if(root!=null){root.recycle();root=null;}
                SystemClock.sleep(Math.min(50,remaining));
              }finally{if(root!=null){root.recycle();root=null;}}
            }
            if(raw==null)throw new IOException("Complete fresh snapshot unavailable");
            try(FileOutputStream file=new FileOutputStream(target)){file.write(raw);file.getFD().sync();}
            StringBuilder digest=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(raw))digest.append(String.format("%02x",b&255));
            result.putString("status","passed");result.putString("nonce",nonce);
            result.putString("file",target.getName());result.putString("sha256",digest.toString());
            result.putInt("bytes",raw.length);result.putInt("nodes",nodes);
            result.putInt("root_attempts",rootAttempts);result.putLong("root_wait_ms",rootWait);
            result.putInt("snapshot_attempts",snapshotAttempts);result.putInt("discarded_partial_trees",snapshotAttempts-1);
            result.putInt("total_nodes_visited",totalNodes);result.putBoolean("partial_xml_reused",false);
            result.putLong("started_elapsed_ms",started);result.putLong("completed_elapsed_ms",SystemClock.elapsedRealtime());
            finish(-1,result);
        }catch(Exception failure){result.putString("status","failed");result.putString("error",failure.getClass().getSimpleName()+": "+failure.getMessage());finish(0,result);}
        finally{if(root!=null)root.recycle();}
    }
}
