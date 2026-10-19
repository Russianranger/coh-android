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
    private String nonce;
    private int nodes;
    private final Rect displayBounds=new Rect();
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
        if(depth>MAX_DEPTH||++nodes>MAX_NODES)throw new IOException("Snapshot traversal limit");
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
            AccessibilityNodeInfo child=value.getChild(i);
            if(child==null)throw new IOException("Snapshot child unavailable");
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
            // Dynamic frame/age labels need not become globally idle to expose
            // their current accessibility layout. No previous tree is reused.
            root=automation.getRootInActiveWindow();
            if(root==null)throw new IOException("Fresh active root unavailable");
            Display display=((WindowManager)getTargetContext().getSystemService(Context.WINDOW_SERVICE)).getDefaultDisplay();
            Point size=new Point();display.getRealSize(size);
            if(size.x<=0||size.y<=0||size.x>16384||size.y>16384)throw new IOException("Display bounds invalid");
            displayBounds.set(0,0,size.x,size.y);
            BoundedOutput output=new BoundedOutput();XmlSerializer xml=Xml.newSerializer();
            xml.setOutput(output,"UTF-8");xml.startDocument("UTF-8",true);xml.startTag("","hierarchy");
            attr(xml,"rotation",display.getRotation());attr(xml,"capture-nonce",nonce);
            attr(xml,"capture-method","fresh-ui-automation-active-root-without-global-idle");
            node(xml,root,0,0);xml.endTag("","hierarchy");xml.endDocument();xml.flush();
            byte[] raw=output.bytes.toByteArray();
            try(FileOutputStream file=new FileOutputStream(target)){file.write(raw);file.getFD().sync();}
            StringBuilder digest=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(raw))digest.append(String.format("%02x",b&255));
            result.putString("status","passed");result.putString("nonce",nonce);
            result.putString("file",target.getName());result.putString("sha256",digest.toString());
            result.putInt("bytes",raw.length);result.putInt("nodes",nodes);
            result.putLong("started_elapsed_ms",started);result.putLong("completed_elapsed_ms",SystemClock.elapsedRealtime());
            finish(-1,result);
        }catch(Exception failure){result.putString("status","failed");result.putString("error",failure.getClass().getSimpleName()+": "+failure.getMessage());finish(0,result);}
        finally{if(root!=null)root.recycle();}
    }
}
