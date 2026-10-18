// NEW focused model controls. No WindowsPlatform construction or Win32 calls.
// Compile later with /main:CohWpp.Tests; not executed during source preparation.
using System;
using System.Collections.Generic;

namespace CohWpp {
 public static class Tests {
  static int checks,cases;
  static void Check(bool ok){checks++;if(!ok)throw new InvalidOperationException("MODEL_CONTROL_FAILED");}
  sealed class Fake : IPlatform {
   public readonly List<string> Trace=new List<string>();
   public readonly HashSet<string> cleanupFailures=new HashSet<string>();
   public string fail,crash,cleanupFail;
   public bool loseSid,noExit,foreignSid,missingHive,profileChanged,wrongResume,terminationRefusal,
    refusedAccount,foreignAfterAccountRefusal;
   bool accountAttempted,account,sid,files,job,child,assigned,resumeAttempted,exited,empty,closed,guiClosed,hive,profileGone,accountGone,jobClosed;
   public bool IsNative {get{return false;}}
   void Hit(string stage,Cause code){
    Trace.Add(stage);if(crash==stage)throw new Exception("PRIVATE_PASSWORD_SID_PATH_CANARY");
    if(fail==stage)throw new Refusal(code);
   }
   void Cleanup(string stage){
    Trace.Add(stage);if(cleanupFail==stage||cleanupFailures.Contains(stage))throw new Refusal(Cause.CLEANUP);
   }
   static void Gate(bool ok){if(!ok)throw new Refusal(Cause.CLEANUP);}
   public void Caller(Receipt r){Hit("Caller",Cause.CALLER);}
   public void PrivateRoot(Receipt r){files=true;Hit("PrivateRoot",Cause.FILES);}
   public void Account(Receipt r){
    accountAttempted=true;
    if(refusedAccount){Trace.Add("Account");throw new Refusal(Cause.ACCOUNT);}
    account=true;r.accountCreated=true;sid=!loseSid;r.sidBound=sid;
    if(loseSid){Trace.Add("Account");throw new Refusal(Cause.ACCOUNT);}
    Hit("Account",Cause.ACCOUNT);
   }
   public void Files(Receipt r){r.privateAcl=true;Hit("Files",Cause.FILES);}
   public void Desktop(Receipt r){r.desktopPrivate=true;Hit("Desktop",Cause.DESKTOP);}
   public void Job(Receipt r){job=true;Hit("Job",Cause.JOB);}
   public void Launch(Receipt r){child=true;r.suspended=true;Hit("Launch",Cause.LAUNCH);}
   public void Verify(Receipt r){r.identity=true;Hit("Verify",Cause.IDENTITY);}
   public void Assign(Receipt r){assigned=true;r.assigned=true;Hit("Assign",Cause.ASSIGN);}
   public void Resume(Receipt r){
    Gate(assigned&&!resumeAttempted);resumeAttempted=true;r.resumeAttempted=true;
    if(wrongResume){Trace.Add("Resume");throw new Refusal(Cause.RESUME);}
    r.resumed=true;Hit("Resume",Cause.RESUME);
   }
   public void Probe(Receipt r){r.probe=true;Hit("Probe",Cause.PROBE);}
   public void StopJob(Receipt r){Cleanup("StopJob");}
   public void StopDirect(Receipt r){
    // Models an independent direct-child wait even after job/query refusal.
    Cleanup("StopDirect");Trace.Add("DirectWait");exited=!noExit;
    r.processExited=exited&&child;r.neverProcess=!child;
    Gate(exited);if(terminationRefusal)throw new Refusal(Cause.CLEANUP);
   }
   public void ObserveEmpty(Receipt r){Cleanup("ObserveEmpty");empty=!job||exited;r.jobEmpty=empty&&job;r.neverJob=!job;Gate(empty);}
   public void CloseChild(Receipt r){Cleanup("CloseChild");Gate(exited&&empty);closed=true;r.handlesClosed=true;}
   public void CloseGui(Receipt r){Cleanup("CloseGui");Gate(exited&&empty);guiClosed=true;r.guiClosed=true;}
   public void Hive(Receipt r){
    Cleanup("Hive");Gate(exited&&empty&&closed&&guiClosed&&jobClosed&&(!account||sid));
    hive=!missingHive;r.hiveAbsent=hive;Gate(hive);
   }
   public void DeleteProfile(Receipt r){
    Cleanup("DeleteProfile");Gate(exited&&empty&&closed&&guiClosed&&hive&&(!account||sid));
    Gate(!accountAttempted||account||!foreignAfterAccountRefusal);
    Gate(!profileChanged);profileGone=true;r.profileAbsent=true;
   }
   public void DeleteAccount(Receipt r){
    Cleanup("DeleteAccount");Gate(!account||(exited&&empty&&closed&&guiClosed&&hive&&profileGone&&sid&&!foreignSid));
    Gate(!accountAttempted||account||!foreignAfterAccountRefusal);
    accountGone=true;r.accountAbsent=true;
   }
   public void CloseJob(Receipt r){Cleanup("CloseJob");Gate(empty);jobClosed=true;r.jobHandleClosed=true;}
   public void Wipe(Receipt r){Cleanup("Wipe");r.secretWiped=true;}
   public void RetireFiles(Receipt r){
    r.journalRetained=files;Cleanup("RetireFiles");
    Gate(exited&&empty&&closed&&guiClosed&&jobClosed&&r.secretWiped&&(!accountAttempted||accountGone));
    files=false;r.filesAbsent=true;r.journalRetained=false;
   }
  }
  static readonly string[] Forward={"Caller","PrivateRoot","Account","Files","Desktop","Job","Launch","Verify","Assign","Resume","Probe"};
  static readonly string[] CleanupSteps={"StopJob","StopDirect","ObserveEmpty","CloseChild","CloseGui","CloseJob","Hive","DeleteProfile","DeleteAccount","Wipe","RetireFiles"};
  static void AllCleanup(Fake f){
   int last=-1;
   foreach(string stage in CleanupSteps){int at=f.Trace.IndexOf(stage);Check(at>last);last=at;}
  }
  static void Positive(){
   cases++;Fake f=new Fake();Receipt r=new Owner().Run(f);
   Check(r.passed&&r.cleanup&&r.first==Cause.NONE&&r.cleanupFirst==Cause.NONE&&
    r.accountCreated&&r.sidBound&&r.assigned&&r.resumed&&r.probe&&r.secretWiped&&!r.actual);
   AllCleanup(f);
   foreach(string stage in Forward)Check(f.Trace.Contains(stage));
   Check(f.Trace.IndexOf("Assign")<f.Trace.IndexOf("Resume"));
   Check(f.Trace.IndexOf("DirectWait")<f.Trace.IndexOf("DeleteProfile"));
  }
  static void ForwardRefusals(){
   foreach(string stage in Forward){
    cases++;Fake f=new Fake();f.fail=stage;Receipt r=new Owner().Run(f);
    Check(!r.passed&&r.first!=Cause.NONE&&r.secretWiped);AllCleanup(f);
    int at=Array.IndexOf(Forward,stage);
    for(int i=at+1;i<Forward.Length;i++)Check(!f.Trace.Contains(Forward[i]));
    if(at<Array.IndexOf(Forward,"Resume"))Check(!r.resumeAttempted);
    Check(!r.actual);
   }
  }
  static void CleanupRefusals(){
   foreach(string stage in CleanupSteps){
    cases++;Fake f=new Fake();f.fail="Probe";f.cleanupFail=stage;
    Receipt r=new Owner().Run(f);
    Check(!r.passed&&!r.cleanup&&r.first==Cause.PROBE&&r.cleanupFirst==Cause.CLEANUP);
    AllCleanup(f);
    if(stage=="StopJob")Check(f.Trace.Contains("DirectWait")&&r.processExited);
    if(stage!="Wipe")Check(r.secretWiped);
   }
   cases++;Fake multiple=new Fake();multiple.fail="Probe";
   multiple.cleanupFailures.Add("StopJob");multiple.cleanupFailures.Add("CloseChild");multiple.cleanupFailures.Add("CloseGui");
   Receipt blocked=new Owner().Run(multiple);
   Check(blocked.first==Cause.PROBE&&blocked.cleanupFirst==Cause.CLEANUP&&
    !blocked.cleanup&&!blocked.profileAbsent&&!blocked.accountAbsent&&blocked.secretWiped);
   Check(multiple.Trace.Contains("DirectWait"));AllCleanup(multiple);
  }
  static void Gates(){
   Fake[] fixtures={new Fake{loseSid=true},new Fake{noExit=true},new Fake{foreignSid=true},
    new Fake{missingHive=true},new Fake{profileChanged=true},new Fake{wrongResume=true},new Fake{terminationRefusal=true},
    new Fake{refusedAccount=true},new Fake{refusedAccount=true,foreignAfterAccountRefusal=true}};
   foreach(Fake f in fixtures){
    cases++;Receipt r=new Owner().Run(f);Check(!r.passed&&r.secretWiped&&
     (!r.cleanup||f.wrongResume||(f.refusedAccount&&!f.foreignAfterAccountRefusal)));AllCleanup(f);
    if(f.loseSid||f.noExit||f.foreignSid||f.missingHive||f.profileChanged)Check(!r.accountAbsent);
    if(f.noExit||f.missingHive||f.profileChanged)Check(!r.profileAbsent);
    if(f.wrongResume)Check(r.resumeAttempted&&!r.resumed);
    if(f.terminationRefusal)Check(f.Trace.Contains("DirectWait")&&r.processExited&&!r.cleanup);
    if(f.foreignAfterAccountRefusal)Check(!r.accountCreated&&!r.accountAbsent&&!r.profileAbsent&&r.journalRetained);
    if(f.refusedAccount&&!f.foreignAfterAccountRefusal)Check(!r.accountCreated&&r.accountAbsent&&r.profileAbsent&&r.cleanup);
   }
   cases++;Fake bad=new Fake();bad.crash="Verify";Receipt hidden=new Owner().Run(bad);
   Check(hidden.first==Cause.INTERNAL&&!hidden.Json().Contains("PRIVATE_PASSWORD_SID_PATH_CANARY"));
   Check(!hidden.Json().Contains("S-1-5-21")&&!hidden.Json().Contains(@"C:\"));
   AllCleanup(bad);
  }
  static void OneShot(){
   cases++;Owner owner=new Owner();Fake f=new Fake();owner.Run(f);int calls=f.Trace.Count;
   try{owner.Run(f);Check(false);}catch(Refusal e){Check(e.Code==Cause.ALREADY_USED);}
   Check(f.Trace.Count==calls);
   cases++;Owner rejected=new Owner();
   try{rejected.Run(null);Check(false);}catch(Refusal e){Check(e.Code==Cause.ALREADY_USED);}
   // A null argument does not acquire the one-shot state.
   Check(rejected.Run(new Fake()).passed);
  }
  public static int Main(string[] args){
   try{
    Check(args.Length==0);Positive();ForwardRefusals();CleanupRefusals();Gates();OneShot();
    Console.Out.WriteLine("{\"schema\":\"coh-owned-profile-process-model-controls-v1\",\"passed\":true,\"scenarios\":"+cases+
     ",\"checks\":"+checks+",\"actual_windows_api_executed\":false,\"native_probe_executed\":false,\"services_or_network_executed\":false}");
    return 0;
   }catch{
    Console.Out.WriteLine("{\"schema\":\"coh-owned-profile-process-model-controls-v1\",\"passed\":false,\"actual_windows_api_executed\":false}");
    return 2;
   }
  }
 }
}
