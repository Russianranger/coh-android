"""Execute shipped capture reporting routes; diagnostics cannot grant proof readiness."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_storage_ui import production_method

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'

HOST = r'''
import java.util.*;
class SystemClock {static long now=1000000;static long uptimeMillis(){return now;}}
class ClientRuntime {
    String session="owned";boolean finished;
    long clientWindowObservedUptime=100,clientWindowEndedUptime=-1,clientWindowFrameWatermark=10;
    FIELDS
    METHODS
    int proofCalls;boolean metricBeforeProof;
    void recordSurfaceCapture(Map<String,Object> record,byte[] png){proofCalls++;metricBeforeProof=captureTimingCount>0;}
    Map<String,Object> diagnostics(){return captureDiagnostics();}
}
class ClientSurface {static class Capture {
    String session="owned",sha256="hash";boolean nonUniform;
    long sequence=11,capturedAtUptimeMillis=200;
    int surfaceGeneration=1,width=800,height=600,surfaceWidth=800,surfaceHeight=600;
    byte[] png=null;
    long pixelCopyWallMs=7,encodingWallMs=90,encodingCpuMs=80,presentationFreezeMs=7,encodeQueueWallMs=2;
    boolean encodingOnUiThread=false;int pendingFramesPeak=1,framesCoalescedDuringCopy=3;
}}
class ClientService {
    ClientRuntime runtime=new ClientRuntime();boolean busy=true;String session="owned";int certified,published;
    void publish(){published++;}
    SERVICE
}
public class CaptureMetricsHost {
    static void require(boolean test){if(!test)throw new AssertionError();}
    static long count(ClientRuntime r){return ((Number)r.diagnostics().get("captures_observed")).longValue();}
    static Map<String,Object> metric(ClientRuntime r,String key){return (Map<String,Object>)r.diagnostics().get(key);}
    static Map<String,Object> record(){
        Map<String,Object> r=new LinkedHashMap<>();r.put("session_id","owned");r.put("pixel_copy_success",true);
        r.put("sequence",11L);r.put("captured_elapsed_ms",200L);
        for(String key:new String[]{"pixel_copy_wall_ms","encoding_wall_ms","encoding_cpu_ms","presentation_freeze_ms","encode_queue_wall_ms"})r.put(key,20L);
        r.put("encoding_on_ui_thread",false);r.put("pending_frames_peak",1);r.put("frames_coalesced_during_copy",3);return r;
    }
    public static void main(String[] args){
        ClientRuntime r=new ClientRuntime();Map<String,Object> value=record();
        switch(args[0]){
        case "unretained":{
            ClientService service=new ClientService();service.recordCapture(new ClientSurface.Capture());
            require(count(service.runtime)==1&&service.runtime.proofCalls==1&&service.runtime.metricBeforeProof);
            require(service.certified==0&&service.published==1);
            require(((Number)metric(service.runtime,"encoding_wall_ms").get("maximum")).longValue()==90);
            require(((Number)service.runtime.diagnostics().get("encoding_ui_thread_count")).longValue()==0);break;}
        case "foreign":{
            ClientService service=new ClientService();ClientSurface.Capture c=new ClientSurface.Capture();c.session="old";service.recordCapture(c);
            require(count(service.runtime)==0&&service.runtime.proofCalls==0);
            value.put("session_id","old");r.recordCaptureTiming(value);require(count(r)==0);
            value.put("session_id","owned");r.clientWindowEndedUptime=250;r.recordCaptureTiming(value);require(count(r)==0);
            r.clientWindowEndedUptime=-1;r.finished=true;r.recordCaptureTiming(value);require(count(r)==0);break;}
        case "freshness":{
            for(long stamp:new long[]{-1,99,1000001}){value.put("captured_elapsed_ms",stamp);r.recordCaptureTiming(value);require(count(r)==0);}
            value.put("captured_elapsed_ms",200L);value.put("sequence",10L);r.recordCaptureTiming(value);require(count(r)==0);
            value.put("sequence",11L);r.recordCaptureTiming(value);r.recordCaptureTiming(value);require(count(r)==1);
            value.put("sequence",12L);r.recordCaptureTiming(value);require(count(r)==2);break;}
        case "malformed":{
            for(Object bad:new Object[]{null,-1L,300001L,Double.NaN,Double.POSITIVE_INFINITY,1.5,20.0,"20"}){
                value.put("encoding_wall_ms",bad);r.recordCaptureTiming(value);require(count(r)==0);}
            value.put("encoding_wall_ms",20L);value.put("encoding_on_ui_thread",1);r.recordCaptureTiming(value);require(count(r)==0);
            value.put("encoding_on_ui_thread",false);value.put("frames_coalesced_during_copy",-1);r.recordCaptureTiming(value);require(count(r)==0);
            value=record();value.remove("encode_queue_wall_ms");r.recordCaptureTiming(value);require(count(r)==0);break;}
        case "aggregate":{
            r.recordCaptureTiming(value);value.put("sequence",12L);value.put("encoding_wall_ms",100L);value.put("encoding_on_ui_thread",true);value.put("pending_frames_peak",2);r.recordCaptureTiming(value);
            Map<String,Object> m=metric(r,"encoding_wall_ms");require(((Number)m.get("sum")).longValue()==120&&((Number)m.get("maximum")).longValue()==100&&((Number)m.get("mean")).doubleValue()==60);
            require(((Number)r.diagnostics().get("encoding_ui_thread_count")).longValue()==1&&((Number)r.diagnostics().get("pending_frames_peak")).longValue()==2);
            require(((Number)r.diagnostics().get("frames_coalesced_during_copy")).longValue()==6);break;}
        case "bounds":{
            value.put("encoding_wall_ms",300000L);value.put("frames_coalesced_during_copy",Integer.MAX_VALUE);
            for(int i=0;i<20002;i++){value.put("sequence",11L+i);r.recordCaptureTiming(value);}
            require(count(r)==20000&&Boolean.TRUE.equals(r.diagnostics().get("limit_reached")));
            require(((Number)metric(r,"encoding_wall_ms").get("sum")).longValue()==6000000000L);
            require(((Number)r.diagnostics().get("frames_coalesced_during_copy")).longValue()==42949672940000L);
            require(r.diagnostics().size()==14);break;}
        case "old_record":{
            Map<String,Object> old=new LinkedHashMap<>();old.put("session_id","owned");old.put("pixel_copy_success",true);old.put("sequence",11L);old.put("captured_elapsed_ms",200L);
            r.recordCaptureTiming(old);require(count(r)==0);r.recordSurfaceCapture(old,new byte[0]);require(r.proofCalls==1);
            require(Boolean.FALSE.equals(r.diagnostics().get("native_fps_measurement")));break;}
        default:throw new AssertionError("unknown case");
        }
    }
}
'''


class CaptureMetricsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime=(JAVA/'ClientRuntime.java').read_text()
        service=(JAVA/'ClientService.java').read_text()
        start=runtime.index('    private static final int MAX_CAPTURE_TIMINGS')
        end=runtime.index('    private final List<Map<String, Object>> loginSamples',start)
        methods='\n'.join(production_method(runtime,signature) for signature in (
            'public synchronized void recordCaptureTiming(', 'private static long captureMetric(',
            'private synchronized Map<String,Object> captureDiagnostics('))
        source=HOST.replace('FIELDS',runtime[start:end]).replace('METHODS',methods).replace(
            'SERVICE',production_method(service,'public void recordCapture('))
        cls.temp=tempfile.TemporaryDirectory();cls.directory=Path(cls.temp.name)
        (cls.directory/'CaptureMetricsHost.java').write_text(source)
        subprocess.run(['java','-m','jdk.compiler/com.sun.tools.javac.Main','--release','8',
                        '-d',str(cls.directory),str(cls.directory/'CaptureMetricsHost.java')],
                       check=True,capture_output=True,text=True)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def execute(self,case):
        run=subprocess.run(['java','-cp',str(self.directory),'CaptureMetricsHost',case],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
    def test_unretained_uniform_png_cannot_hide_encoding_cost(self):self.execute('unretained')
    def test_foreign_or_ended_session_never_changes_diagnostics(self):self.execute('foreign')
    def test_freshness_and_duplicate_callback_rejection(self):self.execute('freshness')
    def test_malformed_or_legacy_metrics_never_poison_report(self):self.execute('malformed')
    def test_actual_service_fields_and_thread_metrics_are_aggregated(self):self.execute('aggregate')
    def test_finite_count_and_wide_sums(self):self.execute('bounds')
    def test_old_proof_path_remains_independent(self):self.execute('old_record')
    def test_report_exports_diagnostics_alongside_existing_proofs(self):
        runtime=(JAVA/'ClientRuntime.java').read_text()
        publish=production_method(runtime,'private void publish(JSONObject guest,')
        self.assertIn('wrapper.put("android_capture_diagnostics", new JSONObject(captureDiagnostics()))',publish)
        self.assertIn('wrapper.put("surface_captures", new JSONArray(surfaceSamples))',publish)


if __name__=='__main__':unittest.main()
