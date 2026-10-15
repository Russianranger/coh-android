#!/usr/bin/env python3
"""Exercise ClientRuntime's exact optional Android exit-history adapter."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientRuntime.java'


def java_block(source, marker):
    start = source.index(marker)
    cursor = source.index('{', start)
    depth = 1
    end = cursor + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


STUBS = {
    'android/os/Build.java': '''package android.os;
public final class Build { public static final class VERSION { public static int SDK_INT=33; } }
''',
    'android/content/Context.java': '''package android.content;
public final class Context {
    public static final String ACTIVITY_SERVICE="activity";
    public android.app.ActivityManager service;
    public boolean forbidService;
    public Object getSystemService(String name) {
        if(forbidService)throw new AssertionError("Older API queried an unavailable service");
        if(!ACTIVITY_SERVICE.equals(name))throw new AssertionError("Unexpected service");
        return service;
    }
    public String getPackageName() { return "io.github.russianranger.cohclientinteractive"; }
}
''',
    'android/app/ActivityManager.java': '''package android.app;
public final class ActivityManager {
    public java.util.List<ApplicationExitInfo> history=new java.util.ArrayList<>();
    public String failure, queriedPackage; public int queriedPid, queriedLimit, calls;
    public java.util.List<ApplicationExitInfo> getHistoricalProcessExitReasons(String name,int pid,int limit) {
        calls++;queriedPackage=name;queriedPid=pid;queriedLimit=limit;
        if("security".equals(failure))throw new SecurityException("unavailable");
        if("runtime".equals(failure))throw new IllegalStateException("service failed");
        return history;
    }
}
''',
    'android/app/ApplicationExitInfo.java': '''package android.app;
public final class ApplicationExitInfo {
    public final String processName;
    public ApplicationExitInfo(String name) { processName=name; }
    public String getProcessName() { return processName; }
    public long getTimestamp() { return 2200000000000L; }
    public int getReason() { return 3; }
    public int getStatus() { return 9; }
    public int getImportance() { return 100; }
    public long getPss() { return 5000000000L; }
    public long getRss() { return 6000000000L; }
    public int getPid() { return 321; }
    public java.io.InputStream getTraceInputStream() { throw new AssertionError("Trace streams must not be opened"); }
}
''',
    'org/json/JSONObject.java': '''package org.json;
public final class JSONObject {
    private final java.util.Map<String,Object> values=new java.util.LinkedHashMap<>();
    public JSONObject put(String name,Object value) { values.put(name,value);return this; }
    public Object get(String name) { return values.get(name); }
}
''',
    'org/json/JSONArray.java': '''package org.json;
public final class JSONArray {
    private final java.util.List<Object> values=new java.util.ArrayList<>();
    public JSONArray put(Object value) { values.add(value);return this; }
    public int length() { return values.size(); }
    public Object get(int index) { return values.get(index); }
}
''',
}

HARNESS = '''import android.content.Context;
import android.app.ActivityManager;
import android.app.ApplicationExitInfo;
import android.os.Build;
import org.json.JSONObject;
import org.json.JSONArray;
import java.util.List;
public final class ExitHistoryHost {
%s
%s
    private static void require(boolean value,String message) {
        if(!value)throw new AssertionError(message);
    }
    public static void main(String[] args) throws Exception {
        Context context=new Context();
        ActivityManager manager=new ActivityManager();context.service=manager;
        String own=context.getPackageName(), scenario=args[0];
        if("old_api".equals(scenario)){Build.VERSION.SDK_INT=26;context.forbidService=true;}
        else if("no_service".equals(scenario)){context.service=null;}
        else if("security".equals(scenario)||"runtime".equals(scenario)){manager.failure=scenario;}
        else if("bounded".equals(scenario)) {
            manager.history.add(new ApplicationExitInfo(own));
            manager.history.add(new ApplicationExitInfo("another.application"));
            manager.history.add(new ApplicationExitInfo(own+"extra"));
            StringBuilder longName=new StringBuilder(own+":");
            while(longName.length()<300)longName.append('x');
            manager.history.add(new ApplicationExitInfo(longName.toString()));
            for(int i=0;i<10;i++)manager.history.add(new ApplicationExitInfo(own));
        } else if("null_history".equals(scenario)){manager.history=null;}
        else {manager.history.add(new ApplicationExitInfo(own));}
        JSONObject result=historicalProcessExits(context);
        JSONArray records=(JSONArray)result.get("records");
        require(Integer.valueOf(4).equals(result.get("maximum_records")),"bounded count");
        require(Boolean.TRUE.equals(result.get("own_processes_only")),"own processes only");
        require(Boolean.FALSE.equals(result.get("trace_streams_requested")),"no trace streams");
        if("old_api".equals(scenario)) {
            require("unsupported_api".equals(result.get("status"))&&manager.calls==0&&records.length()==0,"API26 guard");
        } else if("no_service".equals(scenario)||manager.failure!=null) {
            require("unavailable".equals(result.get("status"))&&records.length()==0,"optional failure");
            if(manager.failure!=null)require(result.get("error_class")!=null,"classified failure");
        } else {
            require("available".equals(result.get("status")),"history available");
            require(own.equals(manager.queriedPackage)&&manager.queriedPid==0&&manager.queriedLimit==4,"own package bounded query");
            require(records.length()==("bounded".equals(scenario)?2:"null_history".equals(scenario)?0:1),"filtered bounded records");
            if(records.length()>0) {
                JSONObject first=(JSONObject)records.get(0);
                require(Long.valueOf(2200000000000L).equals(first.get("timestamp_utc_ms")),"64bit timestamp");
                require(Long.valueOf(5000000000L).equals(first.get("pss_kib")),"64bit PSS in KiB");
                require(Long.valueOf(6000000000L).equals(first.get("rss_kib")),"64bit RSS in KiB");
                require(Integer.valueOf(3).equals(first.get("reason"))&&Integer.valueOf(9).equals(first.get("status")),"reason and status");
                require(Integer.valueOf(100).equals(first.get("importance"))&&Integer.valueOf(321).equals(first.get("pid")),"importance and pid");
                require(own.equals(first.get("process_name")),"process name");
            }
            if("bounded".equals(scenario))require(((String)((JSONObject)records.get(1)).get("process_name")).length()==160,"name byte bound");
        }
        System.out.println("PASS "+scenario);
    }
}
'''


class ProcessExitHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='coh-exit-history-')
        cls.classes = Path(cls.temp.name)
        source = SOURCE.read_text()
        harness = HARNESS % (java_block(source, 'private static JSONObject historicalProcessExits'),
                             java_block(source, 'private static final class ProcessExitHistory'))
        inputs = dict(STUBS, **{'ExitHistoryHost.java': harness})
        for name, contents in inputs.items():
            target = cls.classes/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', str(cls.classes), *map(str, sorted(cls.classes.rglob('*.java')))],
                       check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check_scenarios(self, *scenarios):
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                result = subprocess.run(['java', '-cp', str(self.classes), 'ExitHistoryHost', scenario],
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), 'PASS '+scenario)

    def test_old_api_and_missing_service_are_optional(self):
        self.check_scenarios('old_api', 'no_service')

    def test_own_process_history_preserves_numeric_exit_details(self):
        self.check_scenarios('available', 'null_history')

    def test_records_and_process_names_are_bounded_and_other_apps_are_excluded(self):
        self.check_scenarios('bounded')

    def test_security_and_runtime_failures_do_not_block_report_evidence(self):
        self.check_scenarios('security', 'runtime')


if __name__ == '__main__':
    unittest.main()
