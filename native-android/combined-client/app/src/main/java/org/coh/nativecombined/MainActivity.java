package org.coh.nativecombined;

import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.*;
import android.widget.*;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.zip.*;

/** One launcher: import once, start owned local servers, manually open native client. */
public final class MainActivity extends Activity {
    private static final int PICK=41,EXPORT=42;
    private final Handler main=new Handler(Looper.getMainLooper());
    private final ExecutorService exports=Executors.newSingleThreadExecutor();
    private final List<Button> mutations=new ArrayList<>();
    private TextView status;
    private Button launch,stop;
    private ServerService service;
    private boolean bound,active;
    private String pendingKind="";
    private final ServiceConnection connection=new ServiceConnection(){
        public void onServiceConnected(ComponentName name,IBinder binder){service=((ServerService.LocalBinder)binder).service();update();}
        public void onServiceDisconnected(ComponentName name){service=null;update();}
    };
    private final Runnable poll=new Runnable(){public void run(){update();if(active)main.postDelayed(this,1000);}};
    @Override public void onCreate(Bundle state){
        super.onCreate(state);if(state!=null)pendingKind=state.getString("pending_kind","");
        ScrollView scroll=new ScrollView(this);LinearLayout body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);body.setPadding(20,16,20,24);scroll.addView(body);setContentView(scroll);
        TextView title=new TextView(this);title.setText("City of Heroes · Native Combined");title.setTextSize(23);body.addView(title);
        TextView help=new TextView(this);help.setText("Import your existing files, set up once, start the server, then launch the native client manually.\nThis app keeps a separate test profile and preserves your working launcher. First setup can provision one real disposable test character.\nThe native scene is a local preview. Full server-world rendering remains in development.");body.addView(help);
        button(body,"Import launcher APK",R.id.native_main_import_launcher,()->pick("launcher"),true);
        button(body,"Import game asset part",R.id.native_main_import_part,()->pick("part"),true);
        button(body,"Import runtime archive (optional)",0,()->new AlertDialog.Builder(this).setTitle("Existing runtime archive").setItems(new String[]{"Linux ARM64 runtime","Wine/FEX ARM64 runtime"},(d,n)->pick(n==0?"base":"wine")).show(),true);
        button(body,"Import character backup (optional)",0,()->pick("profile"),true);
        button(body,"Set up runtime",R.id.native_main_setup,()->withService(()->service.setupRuntime()),true);
        button(body,"Start server",R.id.native_main_start_server,()->withService(()->service.startServer()),true);
        launch=button(body,"Launch native client",R.id.native_main_launch_client,()->{
            Intent client=new Intent(this,NativeClientActivity.class);
            client.putExtra("session_policy_path",new File(getFilesDir(),"native-session-policy.json").getAbsolutePath());startActivity(client);
        },false);
        stop=button(body,"Stop server / current operation",R.id.native_main_stop_server,()->withService(()->service.stopOperation()),false);
        button(body,"Recover interrupted server",0,()->withService(()->service.recoverInterrupted()),true);
        button(body,"Export report",R.id.native_main_export,this::export,false);
        status=new TextView(this);status.setId(R.id.native_main_status);status.setTextIsSelectable(true);status.setText("Connecting to the local runtime owner…");body.addView(status);
        Intent owner=new Intent(this,ServerService.class);startForegroundService(owner);bound=bindService(owner,connection,BIND_AUTO_CREATE);
        if(Build.VERSION.SDK_INT>=33&&checkSelfPermission("android.permission.POST_NOTIFICATIONS")!=PackageManager.PERMISSION_GRANTED)requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"},100);
    }
    private Button button(LinearLayout parent,String text,int id,Runnable action,boolean mutation){Button b=new Button(this);b.setText(text);if(id!=0)b.setId(id);b.setOnClickListener(v->action.run());parent.addView(b);if(mutation)mutations.add(b);return b;}
    private void withService(Runnable work){if(service==null){Toast.makeText(this,"Runtime owner is starting",Toast.LENGTH_SHORT).show();return;}work.run();update();}
    private void update(){
        if(status==null)return;if(service==null){status.setText("Runtime owner is starting…");return;}
        JSONObject s=service.snapshot();JSONObject server=s.optJSONObject("server");boolean busy=s.optBoolean("busy"),ready=server!=null&&server.optBoolean("ready");
        String progress=s.optLong("progress_total")>0?"\nProgress: "+s.optLong("progress_done")+" / "+s.optLong("progress_total"):"";
        String stage=server==null?"":server.optString("last_stage");
        String timing=stage.isEmpty()?"":"\nStage: "+stage.replace('_',' ')+" · "+(server.optLong("stage_elapsed_ms")/1000)+" s\nRun elapsed: "+(server.optLong("elapsed_ms")/1000)+" s";
        status.setText(s.optString("message")+"\n\n"+s.optString("imports")+"\nRuntime: "+(s.optBoolean("runtime_ready")?"ready":"setup required")
            +"\nServer: "+(server==null?"stopped":server.optString("phase"))+timing+progress
            +"\n\n"+(ready?"Server ready. Open the native client and tap Connect local server.":"The native preview can open now; server connection requires fresh readiness."));
        for(Button b:mutations)b.setEnabled(!busy);launch.setEnabled(!busy||ready);stop.setEnabled(busy||ready||(server!=null&&server.optBoolean("owned_process_alive")));
    }
    private void pick(String kind){
        pendingKind=kind;Intent choose=new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE);
        choose.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
        if(kind.equals("part"))choose.putExtra(Intent.EXTRA_ALLOW_MULTIPLE,true);
        startActivityForResult(choose,PICK);
    }
    private void export(){Intent choose=new Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/zip").addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE,"COH-NativeCombined-"+System.currentTimeMillis()+".zip");startActivityForResult(choose,EXPORT);}
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);if(result!=RESULT_OK||data==null)return;
        if(request==PICK){
            List<Uri> files=new ArrayList<>();if(data.getClipData()!=null){for(int i=0;i<data.getClipData().getItemCount()&&i<4;i++)files.add(data.getClipData().getItemAt(i).getUri());}else if(data.getData()!=null)files.add(data.getData());
            for(Uri uri:files)try{getContentResolver().takePersistableUriPermission(uri,Intent.FLAG_GRANT_READ_URI_PERMISSION);}catch(SecurityException ignored){}
            if(!pendingKind.matches("launcher|part|base|wine|profile")){Toast.makeText(this,"Choose an import operation again",Toast.LENGTH_SHORT).show();return;}
            final String kind=pendingKind;withService(()->service.importDocuments(kind,files));pendingKind="";
        }else if(request==EXPORT&&data.getData()!=null){
            final Uri output=data.getData();final ServerService currentService=service;exports.execute(()->{try(OutputStream stream=getContentResolver().openOutputStream(output);ZipOutputStream zip=new ZipOutputStream(Objects.requireNonNull(stream))){
                JSONObject combined=currentService!=null?currentService.snapshot():ServerService.readJson(new File(getFilesDir(),"combined-report.json"),2*1024*1024);
                if(combined==null)throw new IOException("Launcher report unavailable");
                zip.putNextEntry(new ZipEntry("combined-report.json"));zip.write(combined.toString(2).getBytes(StandardCharsets.UTF_8));zip.closeEntry();
                for(String path:new String[]{"native-client-report.json","combined-server/latest-report.json"}){
                    File f=new File(getFilesDir(),path);if(!f.isFile()||f.length()>2*1024*1024)continue;
                    JSONObject report=ServerService.readJson(f,2*1024*1024);if(report==null)continue;
                    if(report.optJSONObject("server_readiness")!=null)report.getJSONObject("server_readiness").remove("account");
                    String name=path.replace('/','-');
                    if(path.equals("combined-server/latest-report.json")){
                        JSONObject server=combined.optJSONObject("server");
                        boolean current=server!=null&&GuestDiagnostics.sameSession(server.optString("session_id"),report.optString("session_id"));
                        if(!current)name="previous-session-"+name;
                    }
                    zip.putNextEntry(new ZipEntry(name));zip.write(report.toString(2).getBytes(StandardCharsets.UTF_8));zip.closeEntry();
                }
                }catch(Exception e){main.post(()->Toast.makeText(this,"Report export failed",Toast.LENGTH_LONG).show());return;}main.post(()->Toast.makeText(this,"Report exported",Toast.LENGTH_LONG).show());});
        }
    }
    @Override protected void onSaveInstanceState(Bundle out){out.putString("pending_kind",pendingKind);super.onSaveInstanceState(out);}
    @Override protected void onResume(){super.onResume();active=true;main.post(poll);}
    @Override protected void onPause(){active=false;main.removeCallbacks(poll);super.onPause();}
    @Override protected void onDestroy(){if(bound)unbindService(connection);exports.shutdown();super.onDestroy();}
}
