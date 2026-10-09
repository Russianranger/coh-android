package io.github.russianranger.cohpresentation;

import android.Manifest;
import android.app.Activity;
import android.content.*;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;

/** Short, visible Wine graphics test. The accepted Atlas server remains separate. */
public final class PresentationActivity extends Activity {
    private static final int EXPORT=11,NOTIFY=12;
    private final ExecutorService exporter=Executors.newSingleThreadExecutor();
    private PresentationService service;
    private PresentationService.State state;
    private PresentationSurface display;
    private TextView status,detail,counter,logs;
    private Button setup,run,stop,export;
    private boolean bound,exporting;
    private String pendingExport,pendingAction,shownSession="";
    private final PresentationService.Listener listener=new PresentationService.Listener(){
        @Override public void onState(PresentationService.State value){render(value);}
        @Override public void onFrame(int[] pixels,int width,int height,long sequence){display.setFrame(pixels,width,height,sequence);}
    };
    private final ServiceConnection connection=new ServiceConnection(){
        @Override public void onServiceConnected(ComponentName name,IBinder binder){service=((PresentationService.LocalBinder)binder).service();service.setUiVisible(true);service.addListener(listener);}
        @Override public void onServiceDisconnected(ComponentName name){service=null;setup.setEnabled(false);run.setEnabled(false);stop.setEnabled(false);status.setText("Service disconnected");detail.setText("Reopen this screen to reconnect.");}
    };
    @Override public void onCreate(Bundle saved){
        super.onCreate(saved);getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        if(saved!=null){pendingExport=saved.getString("export");pendingAction=saved.getString("action");}
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.HORIZONTAL);root.setBackgroundColor(Color.rgb(9,19,30));root.setPadding(dp(12),dp(8),dp(12),dp(8));
        root.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(dp(12)+insets.getSystemWindowInsetLeft(),dp(8)+insets.getSystemWindowInsetTop(),dp(12)+insets.getSystemWindowInsetRight(),dp(8)+insets.getSystemWindowInsetBottom());return insets;});
        LinearLayout controls=new LinearLayout(this);controls.setOrientation(LinearLayout.VERTICAL);controls.setPadding(0,0,dp(12),0);
        ScrollView scroll=new ScrollView(this);scroll.addView(controls);root.addView(scroll,new LinearLayout.LayoutParams(dp(224),-1));
        TextView title=text("COH Client Test",22,true);controls.addView(title);
        controls.addView(text("Visible graphics · v0.5.0",12,false));
        controls.addView(text("This short test displays animated Wine graphics inside Android. It does not boot the server or import game assets.",13,false));
        setup=button("1 · Set up runtime",()->request(PresentationService.SETUP));controls.addView(setup);
        run=button("2 · Run display test",()->request(PresentationService.RUN));controls.addView(run);
        stop=button("Stop",()->{if(service!=null)startService(new Intent(this,PresentationService.class).setAction(PresentationService.STOP));});controls.addView(stop);
        export=button("Export latest report",this::chooseExport);controls.addView(export);
        status=text("Connecting",17,true);controls.addView(status);
        detail=text("Connecting to the private runtime service…",13,false);controls.addView(detail);
        counter=text("Surface frames verified: 0",12,false);controls.addView(counter);
        controls.addView(text("Keep this screen visible. Wine starts first; the animation then runs for 60 seconds and stops automatically. First setup needs Internet and 5 GiB free.",12,false));
        logs=text("",10,false);logs.setTypeface(Typeface.MONOSPACE);logs.setTextIsSelectable(true);controls.addView(logs);
        LinearLayout right=new LinearLayout(this);right.setOrientation(LinearLayout.VERTICAL);root.addView(right,new LinearLayout.LayoutParams(0,-1,1));
        TextView caption=text("WINDOWS GRAPHICS → ANDROID DISPLAY",12,true);right.addView(caption);
        display=new PresentationSurface(this);right.addView(display,new LinearLayout.LayoutParams(-1,0,1));
        right.addView(text("Expect changing colored bars and two black/white code strips. This verifies the display path; CoH menus and gameplay come next.",12,false));
        display.setCertificationListener(new PresentationSurface.CertificationListener(){
            @Override public void onFrameCertified(PresentationSurface.Certification sample){if(service!=null)service.recordCertification(sample);}
            @Override public void onCertificationError(String error){if(service!=null)service.recordCertificationError(error);}
        });
        setContentView(root);root.requestApplyInsets();setup.setEnabled(false);run.setEnabled(false);stop.setEnabled(false);export.setEnabled(false);
    }
    private TextView text(String value,int size,boolean bold){TextView t=new TextView(this);t.setText(value);t.setTextSize(size);t.setTextColor(Color.rgb(221,234,245));t.setPadding(0,dp(3),0,dp(7));if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return t;}
    private Button button(String label,Runnable click){Button b=new Button(this);b.setText(label);b.setAllCaps(false);b.setTextSize(13);b.setOnClickListener(v->click.run());return b;}
    private int dp(int value){return Math.round(value*getResources().getDisplayMetrics().density);}
    @Override protected void onStart(){super.onStart();bound=bindService(new Intent(this,PresentationService.class),connection,BIND_AUTO_CREATE);}
    @Override protected void onStop(){if(service!=null){service.setUiVisible(false);service.removeListener(listener);}service=null;if(bound){unbindService(connection);bound=false;}super.onStop();}
    private void render(PresentationService.State next){
        state=next;status.setText(next.stage);detail.setText(next.detail);logs.setText(next.log);counter.setText("Surface frames verified: "+next.certified);
        boolean idle=!next.busy&&!next.blocked;setup.setEnabled(idle);run.setEnabled(idle);stop.setEnabled(next.busy);export.setEnabled(!next.busy&&next.report!=null&&!exporting);
        if(!next.session.isEmpty()&&!next.session.equals(shownSession)){shownSession=next.session;display.setExpectedSession(shownSession);}
    }
    private void request(String action){
        if(state==null||state.busy||state.blocked)return;
        if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){pendingAction=action;requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},NOTIFY);return;}
        launch(action);
    }
    private void launch(String action){try{startForegroundService(new Intent(this,PresentationService.class).setAction(action));}catch(RuntimeException e){Toast.makeText(this,"Could not start. Return to this screen and retry.",Toast.LENGTH_LONG).show();}}
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] results){super.onRequestPermissionsResult(request,permissions,results);if(request==NOTIFY&&pendingAction!=null){String action=pendingAction;pendingAction=null;launch(action);}}
    private void chooseExport(){
        if(state==null||state.busy||state.report==null||exporting)return;pendingExport=state.report.getPath();
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/zip").addCategory(Intent.CATEGORY_OPENABLE);
        SimpleDateFormat format=new SimpleDateFormat("yyyyMMdd-HHmmss",Locale.ROOT);format.setTimeZone(TimeZone.getTimeZone("UTC"));intent.putExtra(Intent.EXTRA_TITLE,"coh-client-test-"+format.format(new Date())+".zip");
        try{startActivityForResult(intent,EXPORT);}catch(RuntimeException e){pendingExport=null;Toast.makeText(this,"No export destination is available.",Toast.LENGTH_LONG).show();}
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);if(request!=EXPORT)return;String selected=pendingExport;pendingExport=null;
        if(result!=RESULT_OK||data==null||data.getData()==null||selected==null)return;final android.net.Uri uri=data.getData();exporting=true;if(state!=null)render(state);
        exporter.execute(()->{String message;try(InputStream in=new FileInputStream(selected);OutputStream out=getContentResolver().openOutputStream(uri,"w")){if(out==null)throw new IOException("No export stream");byte[] buffer=new byte[65536];int n;while((n=in.read(buffer))!=-1)out.write(buffer,0,n);message="Report exported";}catch(Exception e){message="Export failed. Try another destination.";}final String finish=message;runOnUiThread(()->{exporting=false;if(state!=null)render(state);Toast.makeText(this,finish,Toast.LENGTH_LONG).show();});});
    }
    @Override protected void onSaveInstanceState(Bundle out){out.putString("export",pendingExport);out.putString("action",pendingAction);super.onSaveInstanceState(out);}
    @Override protected void onDestroy(){exporter.shutdown();super.onDestroy();}
}
