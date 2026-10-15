#!/usr/bin/env python3
"""Run the production progress projection against stale and malformed evidence."""
from pathlib import Path
import json
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1] / 'app/src/main/java/org/coh/nativecombined/GuestDiagnostics.java'
HARNESS = r'''
package org.coh.nativecombined;
public final class DiagnosticsTest {
 static int checks;
 static void need(boolean value){checks++;if(!value)throw new AssertionError("diagnostics "+checks);}
 public static void main(String[] args){
  String id="0123456789abcdef0123456789abcdef",foreign="ffffffffffffffffffffffffffffffff";
  GuestDiagnostics d=new GuestDiagnostics();
  need(d.snapshot(500).elapsedMs==0);
  d.start(id,1000);need(d.snapshot(2000).elapsedMs==1000);
  need(!d.stage(foreign,"sql_admin",2000));
  need(!d.stage("","sql_admin",2000));
  need(!d.stage(id,"secret\npassword",2000));
  need(!d.stage(id,"x".repeat(121),2000));
  need(!d.stage(id,"sql_admin",999));
  need(d.stage(id,"local_dbserver_startup",2500));
  need(!d.stage(id,"local_dbserver_startup",3000));
  need(d.snapshot(3500).stageElapsedMs==1000);
  d.failure(foreign,"OWNED_CLEANUP_INCOMPLETE");need(d.snapshot(3500).failure.isEmpty());
  for(String invalid:new String[]{"", "null", "secret password", "BAD\nCODE", "A".repeat(81)}){
   d.failure(id,invalid);need(d.snapshot(3500).failure.isEmpty());
  }
  d.failure(id,"ENDPOINT_LEASE_FAILED");d.failure(id,"OWNED_CLEANUP_INCOMPLETE");
  need(d.snapshot(3500).failure.equals("ENDPOINT_LEASE_FAILED"));
  d.finish(4000);need(d.snapshot(8000).elapsedMs==3000);
  need(d.snapshot(8000).stageElapsedMs==1500);
  need(!d.stage(id,"late_old_stage",9000));
  d.start(foreign,10000);need(d.snapshot(10000).failure.isEmpty());
  need(d.snapshot(10000).stages.length==1);
  d.failure(id,"RETAINED_GUEST_DEPENDENCY_FAILED");need(d.snapshot(11000).failure.isEmpty());
  for(int i=0;i<100;i++)need(d.stage(foreign,"step_"+i,11000+i));
  GuestDiagnostics.Snapshot s=d.snapshot(12000);need(s.stages.length==64);
  need(s.stages[0].equals("step_36"));need(s.stageTimes[0]==1036);
  s.stages[0]="changed";s.stageTimes[0]=-1;
  need(d.snapshot(12000).stages[0].equals("step_36"));
  need(d.snapshot(12000).stageTimes[0]==1036);
  need(!GuestDiagnostics.sameSession(null,id));need(!GuestDiagnostics.sameSession("bad","bad"));
  need(GuestDiagnostics.currentReport(id,id,1,"org.coh.nativecombined"));
  need(!GuestDiagnostics.currentReport(id,foreign,1,"org.coh.nativecombined"));
  need(!GuestDiagnostics.currentReport(id,id,"1","org.coh.nativecombined"));
  need(!GuestDiagnostics.currentReport(id,id,true,"org.coh.nativecombined"));
  need(!GuestDiagnostics.currentReport(id,id,1,"org.coh.sessionclient"));
  need(GuestDiagnostics.cleanupProved(true,true,true));
  need(!GuestDiagnostics.cleanupProved(false,true,true));
  need(!GuestDiagnostics.cleanupProved(true,false,true));
  for(Object invalid:new Object[]{false,"true",1,null})need(!GuestDiagnostics.cleanupProved(true,true,invalid));
  d.start(id,0);d.finish(0);need(d.snapshot(1000).elapsedMs==0);
  need(Long.valueOf(0).equals(GuestDiagnostics.numericMetric(0)));
  need(Long.valueOf(1L<<50).equals(GuestDiagnostics.numericMetric(1L<<50)));
  for(Object invalid:new Object[]{null,true,"123",1.0,-1,-1L,Long.MAX_VALUE})need(GuestDiagnostics.numericMetric(invalid)==null);
  System.out.println("{\"status\":\"passed\",\"checks\":"+checks+",\"actual_server_interoperability_verified\":false}");
 }
}
'''


def main():
    with tempfile.TemporaryDirectory(prefix='coh-diagnostics-') as tmp:
        root = Path(tmp)
        test = root / 'DiagnosticsTest.java'
        test.write_text(HARNESS)
        subprocess.run(['java', 'com.sun.tools.javac.Main', '-d', str(root), str(SOURCE), str(test)],
                       check=True, capture_output=True, text=True)
        result = subprocess.run(['java', '-cp', str(root), 'org.coh.nativecombined.DiagnosticsTest'],
                                check=True, capture_output=True, text=True)
        print(json.dumps(json.loads(result.stdout)))


if __name__ == '__main__':
    main()
