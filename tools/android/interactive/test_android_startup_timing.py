"""Execute the shipped Android elapsedRealtime timing helper and receipt handler."""
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_client_sidebar_runtime import method

ROOT = Path(__file__).resolve().parents[3]
JAVA = ROOT/'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'


def harness():
    runtime = (JAVA/'ClientRuntime.java').read_text()
    actual = '\n'.join(method(runtime, signature) for signature in (
        'public synchronized void attachStartupTiming(',
        'private synchronized JSONObject startupTimingReport(',
        'static Map<String, Object> startupThermalSnapshot(',
        'private synchronized void observeMapServerReady(',
        'private synchronized void observeStartupWorldReady(',
    ))
    return r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
import android.content.Context;
import android.os.Build;
final class SystemClock {
    static long elapsed, uptime;
    static long elapsedRealtime(){return elapsed;}
    static long uptimeMillis(){throw new AssertionError("startup timing used a suspend-excluding clock");}
}
final class JSONObject extends LinkedHashMap<String,Object> {
    static final Object NULL=new Object();
    JSONObject(){}
    JSONObject(Map<?,?> values){for(Map.Entry<?,?> row:values.entrySet())put((String)row.getKey(),row.getValue());}
    boolean has(String key){return containsKey(key);}
    boolean isNull(String key){return !has(key)||get(key)==null||get(key)==NULL;}
    int optInt(String key,int otherwise){return get(key) instanceof Number?((Number)get(key)).intValue():otherwise;}
}
public final class StartupTimingHarness {
    static final String SESSION="1234567890abcdef1234567890abcdef";
    String session=SESSION;
    ClientAcceptance.StartupTiming startupTiming;
    Map<String,Object> startupServiceThermal, startupReadyThermal;
    final Context context=new Context();
    boolean inputReady=false, saveReady=false;
    int lifecycle, checkpoints;
    Object jsonValue(Object value){return value;}
    void recordLifecycle(String event){lifecycle++;}
    void checkpoint(){checkpoints++;}
    ACTUAL_METHODS
    static Map<String,Object> event(){
        Map<String,Object> row=new LinkedHashMap<>();
        row.put("type","map_server_ready_observed");row.put("format",1);row.put("session_id",SESSION);
        row.put("request_kind","initial_guest_service_request");row.put("epoch",null);
        row.put("destination_already_resident",false);row.put("map_id",1);
        row.put("readiness_proof","existing_owned_completed_tick_and_DbServer_endpoint_status");
        row.put("process_spawn_observed",true);row.put("native_ready_observed",true);return row;
    }
    static void need(boolean value){if(!value)throw new AssertionError();}
    static void equal(Object actual,Object expected){if(!Objects.equals(actual,expected))throw new AssertionError(actual+" != "+expected);}
    static void valid(){
        ClientAcceptance.StartupTiming timing=new ClientAcceptance.StartupTiming(1000,900);
        equal(timing.report().get("service_receipt_to_map_ready_seconds"),null);
        Map<String,Object> first=event();need(timing.observeMapReady(first,SESSION,61000));
        first.put("map_id",5);need(!timing.observeMapReady(event(),SESSION,62000));
        timing.observeWorldReady(64000);timing.observeWorldReady(65000);
        Map<String,Object> report=timing.report();
        equal(report.get("service_receipt_to_map_ready_seconds"),60.0);
        equal(report.get("ui_action_to_map_ready_seconds"),60.1);
        equal(report.get("service_receipt_to_client_world_ready_seconds"),63.0);
        equal(report.get("ui_action_to_client_world_ready_seconds"),63.1);
        equal(((Map<?,?>)report.get("map_ready_event")).get("map_id"),1);
        equal(report.get("includes_system_suspend"),true);
        equal(report.get("is_success_proof"),false);
        equal(report.get("movement_readiness_measured"),false);
        equal(report.get("physical_60_second_acceptance_validated"),false);
        Map<String,Object> kings=event();kings.put("map_id",5);
        need(new ClientAcceptance.StartupTiming(0,-1).observeMapReady(kings,SESSION,1));
    }
    static void invalid(){
        Object[][] changes={{"type","other"},{"format",2},{"format",1.5},{"session_id","other"},
            {"request_kind","zoning_supervisor_request"},{"epoch",1},{"destination_already_resident",true},
            {"map_id",101},{"map_id",1.5},{"readiness_proof","ready_stdout"},
            {"process_spawn_observed",false},{"native_ready_observed",false}};
        for(Object[] change:changes){Map<String,Object> row=event();row.put((String)change[0],change[1]);
            ClientAcceptance.StartupTiming timing=new ClientAcceptance.StartupTiming(1000,900);
            need(!timing.observeMapReady(row,SESSION,2000));equal(timing.report().get("service_receipt_to_map_ready_seconds"),null);}
        for(String key:event().keySet()){Map<String,Object> row=event();row.remove(key);
            need(!ClientAcceptance.initialMapReadyObservation(row,SESSION));}
        need(!ClientAcceptance.initialMapReadyObservation(event(),null));
        need(!ClientAcceptance.initialMapReadyObservation(null,SESSION));
    }
    static void unavailable(){
        ClientAcceptance.StartupTiming missing=new ClientAcceptance.StartupTiming(1000,-1);
        missing.observeWorldReady(3000);equal(missing.report().get("ui_action_to_client_world_ready_seconds"),null);
        equal(missing.report().get("service_receipt_to_map_ready_seconds"),null);
        equal(missing.report().get("service_receipt_to_client_world_ready_seconds"),2.0);
        ClientAcceptance.StartupTiming futureUi=new ClientAcceptance.StartupTiming(1000,1001);
        need(futureUi.observeMapReady(event(),SESSION,2000));equal(futureUi.report().get("ui_action_to_map_ready_seconds"),null);
        ClientAcceptance.StartupTiming reversed=new ClientAcceptance.StartupTiming(1000,900);
        need(!reversed.observeMapReady(event(),SESSION,999));equal(reversed.report().get("clock_valid"),false);
        need(!reversed.observeMapReady(event(),SESSION,2000));equal(reversed.report().get("service_receipt_to_map_ready_seconds"),null);
        ClientAcceptance.StartupTiming negative=new ClientAcceptance.StartupTiming(-1,-1);
        need(!negative.observeMapReady(event(),SESSION,2000));equal(negative.report().get("service_receipt_to_map_ready_seconds"),null);
        ClientAcceptance.StartupTiming worldReversed=new ClientAcceptance.StartupTiming(1000,900);
        need(worldReversed.observeMapReady(event(),SESSION,3000));worldReversed.observeWorldReady(2999);
        equal(worldReversed.report().get("clock_valid"),false);
        equal(worldReversed.report().get("service_receipt_to_map_ready_seconds"),null);
        ClientAcceptance.StartupTiming mapAfterWorld=new ClientAcceptance.StartupTiming(1000,900);
        mapAfterWorld.observeWorldReady(2000);need(!mapAfterWorld.observeMapReady(event(),SESSION,3000));
        equal(mapAfterWorld.report().get("clock_valid"),false);
        equal(mapAfterWorld.report().get("service_receipt_to_map_ready_seconds"),null);
        equal(mapAfterWorld.report().get("service_receipt_to_client_world_ready_seconds"),null);
    }
    static void runtime(){
        StartupTimingHarness runtime=new StartupTimingHarness();
        runtime.attachStartupTiming(1000,900,null);runtime.attachStartupTiming(7000,6000,null);
        JSONObject wrong=new JSONObject(event());wrong.put("session_id","other");SystemClock.elapsed=10000;
        runtime.observeMapServerReady(wrong);need(runtime.lifecycle==0);
        JSONObject ready=new JSONObject(event());ready.put("epoch",JSONObject.NULL);
        SystemClock.elapsed=61000;runtime.observeMapServerReady(ready);need(runtime.lifecycle==1);
        need(runtime.checkpoints==1);
        SystemClock.elapsed=62000;runtime.observeMapServerReady(ready);need(runtime.lifecycle==1);
        need(runtime.checkpoints==1);
        SystemClock.elapsed=64000;runtime.observeStartupWorldReady();
        equal(runtime.startupTimingReport().get("service_receipt_to_map_ready_seconds"),60.0);
        equal(runtime.startupTimingReport().get("ui_action_to_client_world_ready_seconds"),63.1);
        need(!runtime.inputReady&&!runtime.saveReady);
        StartupTimingHarness unbound=new StartupTimingHarness();unbound.observeMapServerReady(ready);
        need(!unbound.startupTimingReport().containsKey("service_receipt_to_map_ready_seconds")&&unbound.lifecycle==0);
        StartupTimingHarness lateMap=new StartupTimingHarness();lateMap.attachStartupTiming(1000,900,null);
        SystemClock.elapsed=2000;lateMap.observeStartupWorldReady();
        SystemClock.elapsed=3000;lateMap.observeMapServerReady(ready);
        equal(lateMap.startupTimingReport().get("clock_valid"),false);
        equal(lateMap.startupTimingReport().get("service_receipt_to_map_ready_seconds"),null);
        equal(lateMap.startupTimingReport().get("service_receipt_to_client_world_ready_seconds"),null);
        need(lateMap.lifecycle==0&&lateMap.checkpoints==0&&!lateMap.inputReady&&!lateMap.saveReady);
    }
    static void thermal(){
        Context context=new Context();SystemClock.elapsed=1500;Build.VERSION.SDK_INT=29;
        Map<String,Object> snapshot=startupThermalSnapshot(context);
        equal(snapshot.get("observed_elapsed_realtime_ms"),1500L);
        equal(snapshot.get("thermal_status"),2);equal(snapshot.get("battery_temperature_deci_celsius"),370);
        equal(snapshot.get("thermal_status_is_temperature"),false);
        equal(snapshot.get("battery_temperature_is_cpu_temperature"),false);
        context.failPower=true;context.failBattery=true;snapshot=startupThermalSnapshot(context);
        equal(snapshot.get("thermal_status_available"),false);equal(snapshot.get("battery_temperature_available"),false);
        need(snapshot.containsKey("thermal_status_error")&&snapshot.containsKey("battery_temperature_error"));
        context.failPower=false;context.failBattery=false;context.battery=null;Build.VERSION.SDK_INT=28;
        snapshot=startupThermalSnapshot(context);equal(snapshot.get("thermal_status_available"),false);
        equal(snapshot.get("battery_temperature_available"),false);
    }
    public static void main(String[] args){
        if(args[0].equals("valid"))valid();else if(args[0].equals("invalid"))invalid();
        else if(args[0].equals("unavailable"))unavailable();else if(args[0].equals("thermal"))thermal();else runtime();
    }
}
'''.replace('ACTUAL_METHODS', actual)


class AndroidStartupTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='coh-android-startup-timing-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.path = Path(cls.tmp.name)
        source = cls.path/'StartupTimingHarness.java'
        source.write_text(harness())
        stubs = {
            'android/content/Context.java': '''package android.content;
                public class Context {public static final String POWER_SERVICE="power";
                public boolean failPower,failBattery;public Intent battery=new Intent();
                public Object getSystemService(String name){if(failPower)throw new SecurityException();return new android.os.PowerManager();}
                public Intent registerReceiver(Object receiver,IntentFilter filter){if(failBattery)throw new SecurityException();return battery;}}''',
            'android/content/Intent.java': '''package android.content;
                public class Intent {public static final String ACTION_BATTERY_CHANGED="battery";
                public boolean hasExtra(String name){return true;}public int getIntExtra(String name,int otherwise){return 370;}}''',
            'android/content/IntentFilter.java': 'package android.content;public class IntentFilter {public IntentFilter(String action){}}',
            'android/os/PowerManager.java': 'package android.os;public class PowerManager {public int getCurrentThermalStatus(){return 2;}}',
            'android/os/Build.java': 'package android.os;public class Build {public static class VERSION {public static int SDK_INT=29;}}',
        }
        paths = []
        for name, text in stubs.items():
            path = cls.path/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            paths.append(str(path))
        result = subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
            '-d', str(cls.path), str(JAVA/'ClientAcceptance.java'), str(source), *paths], capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def execute(self, mode):
        result = subprocess.run(['java', '-cp', str(self.path),
            'io.github.russianranger.cohclientinteractive.StartupTimingHarness', mode], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_same_android_clock_includes_preparation_and_suspend(self):
        self.execute('valid')

    def test_only_exact_current_initial_cold_map_events(self):
        self.execute('invalid')

    def test_incomplete_and_invalid_clocks_never_fabricate_elapsed(self):
        self.execute('unavailable')

    def test_actual_runtime_handler_null_epoch_first_receipt_and_no_input(self):
        self.execute('runtime')

    def test_sparse_thermal_observations_have_units_and_unavailable_fallback(self):
        self.execute('thermal')

    def test_production_service_activity_and_report_wiring(self):
        service = (JAVA/'ClientService.java').read_text()
        start = method(service, '@Override public int onStartCommand(')
        self.assertTrue(start.split('{', 1)[1].lstrip().startswith(
            'final long serviceReceiptElapsedRealtime = SystemClock.elapsedRealtime();'))
        self.assertLess(start.index('serviceReceiptElapsedRealtime ='), start.index('refreshProfileState();'))
        self.assertLess(start.index('attachStartupTiming('), start.index('worker.execute('))
        self.assertIn('intent.getLongExtra(EXTRA_STARTUP_UI_ACTION_ELAPSED_REALTIME,-1),serviceThermal)', start)
        runtime = (JAVA/'ClientRuntime.java').read_text()
        for signature in ('private synchronized void checkpoint(', 'private void publish(', 'private File retainFailureReport('):
            self.assertIn('.put("android_startup_timing",startupTimingReport())', method(runtime, signature))
        output = method(runtime, 'private void captureOutput(')
        self.assertIn('if ("map_server_ready_observed".equals(event.optString("type"))) observeMapServerReady(event);', output)
        connected = method(output, 'if ((reopen ? ClientAcceptance.characterReopenConnectedEvent(')
        self.assertIn('observeStartupWorldReady();', connected)
        self.assertIn('checkpoint();', method(runtime, 'private synchronized void observeMapServerReady('))
        activity = (JAVA/'ClientActivity.java').read_text()
        request = method(activity, 'private void request(')
        self.assertLess(request.index('SystemClock.elapsedRealtime()'), request.index('diagnosticControlsReady('))
        self.assertIn('intent.putExtra(ClientService.EXTRA_STARTUP_UI_ACTION_ELAPSED_REALTIME,uiActionElapsedRealtime)',
            method(activity, 'private void launch('))


if __name__ == '__main__':
    unittest.main()
