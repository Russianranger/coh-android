#!/usr/bin/env python3
"""Run the APK's device-receipt and immutable-report code with the host JDK."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
JAVA = ROOT / 'android/app/src/main/java/io/github/russianranger/cohdiagnostic'
CLASS = 'io.github.russianranger.cohdiagnostic.DeviceDbServerHost'
FIXTURE = r'''
package io.github.russianranger.cohdiagnostic;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;

public final class DeviceDbServerHost {
    static final String LOOP = "COH_WINE_DB_LOOPBACK_ONLY=1 active: IPv4 listener binds restricted to loopback; endpoint verification required";
    static final String FIXED = "COH_WINE_DB_FIXED_INPUTS=1 active: directory monitoring disabled; initial reads and lookup mode preserved";
    static Map<String,Object> map(Object... items) {
        Map<String,Object> value = new HashMap<>();
        for (int i=0;i<items.length;i+=2) value.put((String)items[i],items[i+1]);
        return value;
    }
    static void check(boolean condition, String detail) { if (!condition) throw new AssertionError(detail); }
    @SuppressWarnings("unchecked") static Map<String,Object> obj(Map<String,Object> value, String key) {
        return (Map<String,Object>)value.get(key);
    }
    @SuppressWarnings("unchecked") static List<Map<String,Object>> phases(Map<String,Object> report, String key) {
        return (List<Map<String,Object>>)obj(report,key).get("phases");
    }
    static Map<String,Object> loop(boolean endpoints) {
        List<Map<String,Object>> values = new ArrayList<>();
        if (endpoints) for (int i=0;i<13;i++) values.add(map("protocol",i==12?"udp":"tcp", "address","127.0.0.1","port",7000+i));
        return map("requested",true,"startup_acknowledgement",LOOP,"endpoints",values);
    }
    static Map<String,Object> receipt() {
        List<Map<String,Object>> fixture = new ArrayList<>(), schema = new ArrayList<>();
        String[] modes = {"initial","fail","exhaust","delete-fail","disconnect","verify","verify","verify",
            "rebuild","verify-rebuilt","rebuild-fail","rebuild-fail-view","verify-rebuilt","verify-rebuilt"};
        for (int i=0;i<modes.length;i++) fixture.add(map("mode",modes[i],"exit_code",i>=1&&i<=4?3:i==10||i==11?2:0,"loopback_only",loop(false)));
        for (int i=1;i<=2;i++) schema.add(map("number",i,"exit_code",0,"failure_diagnostic_lines",new ArrayList<>(),
            "loopback_only",loop(true),"fixed_inputs",map("requested",true,"startup_acknowledgement",FIXED)));
        return map("diagnostic_mode","dbserver_persistence_and_generated_schema","execution_platform_requested","android",
            "listener_policy","device","status","passed","passed",true,"failures",new ArrayList<>(),"cleanup_complete",true,
            "android_execution_validated",false,"android_listener_binding_validated",false,"gameplay_validated",false,
            "generated_character_persistence_validated",false,
            "cleanup",map("postgres_graceful",true,"wine_prefix_stopped",true,"owned_processes_reaped",true),
            "fixture",map("status","passed","check_count",21,"checks",Collections.nCopies(21,"checked"),"phases",fixture),
            "generated_schema",map("status","passed","reload_stable",true,"fixture_enabled",false,"phases",schema));
    }
    @SuppressWarnings("unchecked") static Map<String,Object> contract() {
        List<Map<String,Object>> values = (List<Map<String,Object>>)loop(true).get("endpoints");
        for (Map<String,Object> endpoint:values) endpoint.put("required_before_export",true);
        values.add(map("protocol","tcp","address","127.0.0.1","port",6992,"required_before_export",false));
        return map("endpoints",values);
    }
    @SuppressWarnings("unchecked") public static void main(String[] args) throws Exception {
        String test=args[0];
        if (test.equals("outcome")) {
            DiagnosticOutcome stopFirst = new DiagnosticOutcome();
            check(stopFirst.requestStop(),"Running operation refused Stop");
            check(stopFirst.finish() && stopFirst.cancelled(),"Accepted Stop was lost at report commit");
            check(stopFirst.finish(),"Repeated finish changed cancelled report outcome");
            DiagnosticOutcome finishFirst = new DiagnosticOutcome();
            check(!finishFirst.finish(),"Completed work unexpectedly cancelled");
            check(!finishFirst.requestStop() && !finishFirst.cancelled(),"Late Stop relabelled already committed evidence");
            // Race Stop and report commitment repeatedly. Exactly one outcome
            // must win; an accepted Stop may never coexist with a passed report.
            for(int i=0;i<100;i++) {
                DiagnosticOutcome race = new DiagnosticOutcome();
                java.util.concurrent.CountDownLatch ready = new java.util.concurrent.CountDownLatch(1);
                boolean[] accepted = new boolean[1];
                Thread stopper = new Thread(()->{try{ready.await();accepted[0]=race.requestStop();}catch(InterruptedException e){throw new AssertionError(e);}});
                stopper.start();ready.countDown();boolean cancelledAtPublication=race.finish();stopper.join();
                check(accepted[0]==cancelledAtPublication,"Stop acceptance and immutable report disagree");
                check(race.cancelled()==cancelledAtPublication,"Report outcome changed after publication");
            }
            return;
        }
        if (test.equals("hosts")) {
            check(DeviceHosts.contents("localhost").equals("127.0.0.1 localhost\n"),"Duplicate localhost");
            check(DeviceHosts.contents("thor.example").equals("127.0.0.1 localhost thor.example thor\n"),"Missing full or short hostname");
            for(String bad:new String[]{"","-thor","thor-","thor.","thor..test","thor\nremote","thor other","127.0.0.1\n0.0.0.0 remote"}) {
                try {DeviceHosts.contents(bad);throw new AssertionError("Unsafe hostname accepted");}catch(IOException expected) {}
            }
            return;
        }
        if (test.equals("reports")) {
            File home = new File(args[1]);
            DiagnosticReports first = new DiagnosticReports(home), cancelled = new DiagnosticReports(home), failed = new DiagnosticReports(home);
            check(!first.target.equals(cancelled.target),"Runs share a report path");
            Files.write(first.prepare().toPath(),"first success".getBytes(StandardCharsets.UTF_8)); first.publish();
            File exportAlreadySelected = first.target;
            Files.write(cancelled.prepare().toPath(),"cancelled before startup".getBytes(StandardCharsets.UTF_8)); cancelled.publish();
            Files.write(failed.prepare().toPath(),"incomplete".getBytes(StandardCharsets.UTF_8)); failed.discardPartial();
            check(!failed.target.exists(),"Incomplete report became exportable");
            check(new String(Files.readAllBytes(exportAlreadySelected.toPath()),StandardCharsets.UTF_8).equals("first success"),"Later run replaced selected export");
            check(cancelled.target.isFile(),"Cancellation report was lost");
            try { first.prepare(); throw new AssertionError("Completed report can be overwritten"); } catch (IOException expected) {}
            first.discardPartial();
            check(first.target.isFile(),"Discarding partial report removed completed evidence");
            return;
        }
        Map<String,Object> value = receipt();
        Map<String,Object> contract = contract();
        check(DbServerAcceptance.accepts(value,contract),"Complete device-policy receipt rejected");
        if (test.equals("good")) return;
        switch(test) {
            case "host": value.put("execution_platform_requested","host"); break;
            case "host_policy": value.put("listener_policy","host-default"); break;
            case "guest_attestation": value.put("android_execution_validated",true); break;
            case "gameplay_claim": value.put("gameplay_validated",true); break;
            case "wrong_mode": value.put("diagnostic_mode","database"); break;
            case "string_success": value.put("passed","true"); break;
            case "missing_failures": value.remove("failures"); break;
            case "cancelled": value.put("status","cancelled"); break;
            case "cleanup": obj(value,"cleanup").put("owned_processes_reaped",false); break;
            case "capture_open": value.put("cleanup_complete",false); break;
            case "fixture_phase_missing": phases(value,"fixture").remove(6); break;
            case "fixture_wrong_exit": phases(value,"fixture").get(1).put("exit_code",0); break;
            case "fixture_no_policy": obj(phases(value,"fixture").get(0),"loopback_only").put("requested",false); break;
            case "schema_no_policy": obj(phases(value,"generated_schema").get(0),"loopback_only").put("requested",false); break;
            case "schema_not_fixed": obj(phases(value,"generated_schema").get(1),"fixed_inputs").put("requested",false); break;
            case "schema_reload": obj(value,"generated_schema").put("reload_stable",false); break;
            case "schema_fixture": obj(value,"generated_schema").put("fixture_enabled",true); break;
            case "missing_listener": ((List<?>)obj(phases(value,"generated_schema").get(1),"loopback_only").get("endpoints")).remove(0); break;
            case "wildcard_listener": ((List<Map<String,Object>>)obj(phases(value,"generated_schema").get(0),"loopback_only").get("endpoints")).get(0).put("address","0.0.0.0"); break;
            case "duplicate_listener": ((List<Map<String,Object>>)obj(phases(value,"generated_schema").get(0),"loopback_only").get("endpoints")).get(1).put("port",7000); break;
            case "no_udp": ((List<Map<String,Object>>)obj(phases(value,"generated_schema").get(0),"loopback_only").get("endpoints")).get(12).put("protocol","tcp"); break;
            case "wrong_port": ((List<Map<String,Object>>)obj(phases(value,"generated_schema").get(0),"loopback_only").get("endpoints")).get(0).put("port",9000); break;
            case "bad_contract": ((List<Map<String,Object>>)contract.get("endpoints")).get(0).put("required_before_export",false); break;
            default: throw new AssertionError("Unknown test " + test);
        }
        check(!DbServerAcceptance.accepts(value,contract),"Invalid receipt accepted: " + test);
    }
}
'''


class DeviceDbServerAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='coh-device-app-')
        cls.directory = Path(cls.temporary.name)
        fixture = cls.directory / 'DeviceDbServerHost.java'
        fixture.write_text(FIXTURE)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', str(cls.directory), str(JAVA / 'DbServerAcceptance.java'),
                        str(JAVA / 'DiagnosticReports.java'), str(JAVA / 'DiagnosticOutcome.java'),
                        str(JAVA / 'DeviceHosts.java'), str(fixture)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def execute(self, mode):
        result = subprocess.run(['java', '-cp', str(self.directory), CLASS, mode,
                                 str(self.directory / 'reports-test')],
                                text=True, capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_complete_device_receipt(self):
        self.execute('good')

    def test_platform_scope_and_status_fail_closed(self):
        for mode in ('host', 'host_policy', 'guest_attestation', 'gameplay_claim', 'wrong_mode',
                     'string_success', 'missing_failures', 'cancelled'):
            with self.subTest(mode=mode):
                self.execute(mode)

    def test_cleanup_and_real_phase_coverage_required(self):
        for mode in ('cleanup', 'capture_open', 'fixture_phase_missing', 'fixture_wrong_exit',
                     'fixture_no_policy', 'schema_no_policy', 'schema_not_fixed',
                     'schema_reload', 'schema_fixture'):
            with self.subTest(mode=mode):
                self.execute(mode)

    def test_normal_listeners_must_be_complete_unique_loopback(self):
        for mode in ('missing_listener', 'wildcard_listener', 'duplicate_listener', 'no_udp', 'wrong_port', 'bad_contract'):
            with self.subTest(mode=mode):
                self.execute(mode)

    def test_report_and_cancelled_report_survive_later_runs(self):
        self.execute('reports')

    def test_stop_and_final_publication_have_one_atomic_outcome(self):
        self.execute('outcome')

    def test_owned_hosts_maps_only_valid_full_and_short_hostname(self):
        self.execute('hosts')


if __name__ == '__main__':
    unittest.main()
