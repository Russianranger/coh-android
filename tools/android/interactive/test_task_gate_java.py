"""Exercise shipped task event/identity acceptance on the host JVM."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/ClientAcceptance.java'
FIXTURE = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
public final class TaskGateHost {
    static final String SESSION="0123456789abcdef0123456789abcdef";
    static Map<String,Object> map(Object... fields) {
        Map<String,Object> out=new LinkedHashMap<>();
        for(int i=0;i<fields.length;i+=2)out.put((String)fields[i],fields[i+1]);
        return out;
    }
    static Map<String,Object> task() {
        return map("name","Mission1","context",-52,"subhandle",1,"task_index",0);
    }
    static Map<String,Object> event(String phase) {
        return map("type",phase,"session_id",SESSION,"client_pid",664,"character_id",1,
                "observed_utc_ms",1791025200000L,"active_task_count",1,
                "native_task_verified",true,"sql_task_verified",true,"task",task());
    }
    static boolean accepted(Map<String,Object> event) {
        return ClientAcceptance.taskEvent(event,"character_task_accepted",SESSION,664);
    }
    static void need(boolean value) {if(!value)throw new AssertionError();}
    public static void main(String[] args) {
        switch(args[0]) {
        case "qualified": {
            Map<String,Object> a=event("character_task_accepted"),c=event("character_task_completed");
            need(accepted(a));need(!accepted(c));
            need(ClientAcceptance.taskEvent(c,"character_task_completed",SESSION,664));
            need(ClientAcceptance.sameTaskIdentity(a.get("task"),c.get("task")));
            need(!ClientAcceptance.taskEvent(a,"task_view_captured",SESSION,664));
            need(!ClientAcceptance.taskEvent(a,null,SESSION,664));
            break;
        }
        case "identity": {
            for(Object[] change:new Object[][] {
                {"session_id","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"},{"client_pid",665},
                {"character_id",2},{"character_id",1.5},{"client_pid",664.25}}) {
                Map<String,Object> value=event("character_task_accepted");value.put((String)change[0],change[1]);
                need(!accepted(value));
            }
            need(!ClientAcceptance.taskEvent(event("character_task_accepted"),"character_task_accepted",null,664));
            need(!ClientAcceptance.taskEvent(event("character_task_accepted"),"character_task_accepted",SESSION,4294967296L));
            break;
        }
        case "proof": {
            for(String key:Arrays.asList("native_task_verified","sql_task_verified")) {
                for(Object invalid:Arrays.asList(false,"true",1)) {
                    Map<String,Object> value=event("character_task_accepted");value.put(key,invalid);need(!accepted(value));
                }
                Map<String,Object> value=event("character_task_accepted");value.remove(key);need(!accepted(value));
            }
            for(Object count:Arrays.asList(0,2,1.25,"1")) {
                Map<String,Object> value=event("character_task_accepted");value.put("active_task_count",count);need(!accepted(value));
            }
            for(Object time:Arrays.asList(0,-1,Double.NaN,Double.POSITIVE_INFINITY,"1791025200000")) {
                Map<String,Object> value=event("character_task_accepted");value.put("observed_utc_ms",time);need(!accepted(value));
            }
            break;
        }
        case "bounds": {
            need(ClientAcceptance.taskIdentity(task()));
            for(Object[] change:new Object[][] {
                {"context",0},{"context",2147483648L},{"context",-2147483649L},{"context",-52.5},
                {"subhandle",-1},{"subhandle",2147483648L},{"subhandle",1.25},{"task_index",1},
                {"name",""},{"name","Mission1\n"},{"name","M\u00edssion1"}}) {
                Map<String,Object> value=task();value.put((String)change[0],change[1]);
                need(!ClientAcceptance.taskIdentity(value));
            }
            need(!ClientAcceptance.taskIdentity(null));need(!ClientAcceptance.taskIdentity(Collections.emptyMap()));
            break;
        }
        case "same_task": {
            Map<String,Object> first=task(),other=task();
            other.put("context",-52L);other.put("subhandle",1L);other.put("task_index",0L);
            need(ClientAcceptance.sameTaskIdentity(first,other));
            for(Object[] change:new Object[][] {
                {"context",-53},{"subhandle",2},{"name","Mission2"},{"task_index",1}}) {
                other=task();other.put((String)change[0],change[1]);
                need(!ClientAcceptance.sameTaskIdentity(first,other));
                need(!ClientAcceptance.sameTaskIdentity(other,first));
            }
            need(!ClientAcceptance.sameTaskIdentity(first,null));
            break;
        }
        case "save_readiness": {
            Map<String,Object> a=event("character_task_accepted"),c=event("character_task_completed");
            need(ClientAcceptance.taskSaveReady(a,c,3,3,SESSION,664));
            for(int acceptedViews=0;acceptedViews<=3;acceptedViews++)
                for(int completedViews=0;completedViews<=3;completedViews++)
                    if(acceptedViews!=3 || completedViews!=3)
                        need(!ClientAcceptance.taskSaveReady(a,c,acceptedViews,completedViews,SESSION,664));
            need(!ClientAcceptance.taskSaveReady(null,c,3,3,SESSION,664));
            need(!ClientAcceptance.taskSaveReady(a,null,3,3,SESSION,664));
            need(!ClientAcceptance.taskSaveReady(a,a,3,3,SESSION,664));
            Map<String,Object> unrelated=event("character_task_completed");
            Map<String,Object> unrelatedTask=task();unrelatedTask.put("subhandle",2);unrelated.put("task",unrelatedTask);
            need(!ClientAcceptance.taskSaveReady(a,unrelated,3,3,SESSION,664));
            c.put("sql_task_verified",false);need(!ClientAcceptance.taskSaveReady(a,c,3,3,SESSION,664));
            break;
        }
        default:throw new AssertionError("unknown scenario");
        }
    }
}
'''


class TaskGateJavaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory(prefix='coh-task-gate-java-')
        cls.path = Path(cls.folder.name)
        host = cls.path / 'TaskGateHost.java'
        host.write_text(FIXTURE)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', str(cls.path), str(SOURCE), str(host)],
                       check=True, capture_output=True, text=True)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def scenario(self, name):
        subprocess.run(['java', '-cp', str(self.path),
                        'io.github.russianranger.cohclientinteractive.TaskGateHost', name],
                       check=True, capture_output=True, text=True)

    def test_qualified_native_sql_events_keep_distinct_phases(self): self.scenario('qualified')
    def test_foreign_session_client_and_character_never_qualify(self): self.scenario('identity')
    def test_single_task_requires_both_native_and_sql_proofs(self): self.scenario('proof')
    def test_invalid_task_handles_indices_and_names_are_rejected(self): self.scenario('bounds')
    def test_completion_must_match_the_exact_accepted_task(self): self.scenario('same_task')
    def test_save_requires_matching_completion_and_both_finished_capture_phases(self): self.scenario('save_readiness')


if __name__ == '__main__': unittest.main()
