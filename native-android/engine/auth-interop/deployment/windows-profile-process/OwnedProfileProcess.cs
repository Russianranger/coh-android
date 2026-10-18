// Scratch/source-only. C# 5 / .NET Framework 4.x, x64. Not yet compiled or run.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Cryptography;
using System.Security.Principal;
using System.Text;
using System.Threading;
using Microsoft.Win32;
using Microsoft.Win32.SafeHandles;

namespace CohWpp {
 public enum Cause { NONE, CALLER, FILES, ACCOUNT, PROFILE, DESKTOP, JOB, LAUNCH,
  IDENTITY, ASSIGN, RESUME, TIMEOUT, PROBE, CLEANUP, INTERNAL, ALREADY_USED }
 public sealed class Refusal : Exception {
  public readonly Cause Code;
  public Refusal(Cause code) : base(code.ToString()) { Code=code; }
 }
 public sealed class Receipt {
  public Cause first=Cause.NONE,cleanupFirst=Cause.NONE;
  public bool passed,cleanup,actual,nativeSelected,accountCreated,sidBound,privateAcl,desktopPrivate,
   suspended,identity,assigned,resumeAttempted,resumed,probe,processExited,jobEmpty,
   handlesClosed,guiClosed,hiveAbsent,profileAbsent,accountAbsent,filesAbsent,
   secretWiped,journalRetained,neverProcess,neverJob,jobHandleClosed;
  static string B(bool b) { return b?"true":"false"; }
  public string Json() {
   return "{\"schema\":\"coh-owned-profile-inert-process-v1\",\"passed\":"+B(passed)+
    ",\"first_failure\":\""+first+"\",\"first_cleanup_failure\":\""+cleanupFirst+
    "\",\"cleanup_complete\":"+B(cleanup)+",\"actual_windows_api_executed\":"+B(actual)+
    ",\"native_backend_selected\":"+B(nativeSelected)+
    ",\"owned_account_created\":"+B(accountCreated)+",\"exact_sid_bound\":"+B(sidBound)+
    ",\"new_private_acl_verified\":"+B(privateAcl)+",\"new_private_desktop_verified\":"+B(desktopPrivate)+
    ",\"created_suspended\":"+B(suspended)+",\"process_thread_token_identity_verified\":"+B(identity)+
    ",\"owned_job_assigned\":"+B(assigned)+",\"resume_attempted\":"+B(resumeAttempted)+
    ",\"resume_previous_count_one\":"+B(resumed)+",\"inert_hkcu_probe_verified\":"+B(probe)+
    ",\"owned_process_exit_observed\":"+B(processExited)+",\"owned_job_empty_observed\":"+B(jobEmpty)+
    ",\"owned_process_creation_not_attempted\":"+B(neverProcess)+",\"owned_job_not_created\":"+B(neverJob)+
    ",\"child_observation_handles_closed\":"+B(handlesClosed)+",\"new_gui_objects_closed\":"+B(guiClosed)+
    ",\"owned_job_handle_closed\":"+B(jobHandleClosed)+
    ",\"owned_hives_absent\":"+B(hiveAbsent)+",\"owned_profile_absent\":"+B(profileAbsent)+
    ",\"owned_account_absent\":"+B(accountAbsent)+",\"new_private_tree_absent\":"+B(filesAbsent)+
    ",\"native_credential_buffer_wiped\":"+B(secretWiped)+",\"private_journal_retained\":"+B(journalRetained)+
    ",\"inert_mode_requested\":true,\"probe_build_provenance_verified\":false,"+
    "\"auth_db_map_or_service_authority_admitted\":false,"+
    "\"source_generation_admitted\":false,\"world_authority\":false,"+
    "\"strict_native_api_deadline_claimed\":false}";
  }
 }
 // No public raw handle/PID/SID selectors. Each platform instance owns one lease.
 public interface IPlatform {
  bool IsNative { get; }
  void Caller(Receipt r); void PrivateRoot(Receipt r); void Account(Receipt r);
  void Files(Receipt r); void Desktop(Receipt r); void Job(Receipt r);
  void Launch(Receipt r); void Verify(Receipt r); void Assign(Receipt r);
  void Resume(Receipt r); void Probe(Receipt r);
  void StopJob(Receipt r); void StopDirect(Receipt r); void ObserveEmpty(Receipt r);
  void CloseChild(Receipt r); void CloseGui(Receipt r); void Hive(Receipt r);
  void DeleteProfile(Receipt r); void DeleteAccount(Receipt r); void CloseJob(Receipt r);
  void Wipe(Receipt r); void RetireFiles(Receipt r);
 }
 public sealed class Owner {
  bool used;
  static void Clean(Action a,Receipt r) {
   try { a(); } catch(Refusal e) {
    if(r.cleanupFirst==Cause.NONE)r.cleanupFirst=e.Code;
    if(r.first==Cause.NONE)r.first=e.Code;
   } catch { if(r.cleanupFirst==Cause.NONE)r.cleanupFirst=Cause.INTERNAL;
    if(r.first==Cause.NONE)r.first=Cause.INTERNAL; }
  }
  public Receipt Run(IPlatform p) {
   if(used||p==null)throw new Refusal(Cause.ALREADY_USED);
   used=true;Receipt r=new Receipt();r.nativeSelected=p.IsNative;
   try {
    p.Caller(r);p.PrivateRoot(r);p.Account(r);p.Files(r);p.Desktop(r);p.Job(r);
    p.Launch(r);p.Verify(r);p.Assign(r);p.Resume(r);p.Probe(r);
   } catch(Refusal e) { r.first=e.Code; }
   catch { r.first=Cause.INTERNAL; }
   finally {
    // Every independent cleanup path is attempted, even after another throws.
    Clean(delegate{p.StopJob(r);},r);Clean(delegate{p.StopDirect(r);},r);
    Clean(delegate{p.ObserveEmpty(r);},r);Clean(delegate{p.CloseChild(r);},r);
    Clean(delegate{p.CloseGui(r);},r);Clean(delegate{p.CloseJob(r);},r);Clean(delegate{p.Hive(r);},r);
    Clean(delegate{p.DeleteProfile(r);},r);Clean(delegate{p.DeleteAccount(r);},r);
    Clean(delegate{p.Wipe(r);},r);
    Clean(delegate{p.RetireFiles(r);},r);
   }
   r.cleanup=r.cleanupFirst==Cause.NONE&&(r.processExited||r.neverProcess)&&(r.jobEmpty||r.neverJob)&&
    r.handlesClosed&&r.guiClosed&&r.jobHandleClosed&&r.hiveAbsent&&r.profileAbsent&&r.accountAbsent&&
    r.filesAbsent&&r.secretWiped;
   r.passed=r.first==Cause.NONE&&r.probe&&r.cleanup;
   return r;
  }
 }
 internal static class N {
  [StructLayout(LayoutKind.Sequential)] internal struct SA { public int cb;public IntPtr sd;public int inherit; }
  [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] internal struct UI1 {
   [MarshalAs(UnmanagedType.LPWStr)] public string name;public IntPtr password;
   public uint age,priv;public IntPtr home,comment;public uint flags;public IntPtr script;
  }
  [StructLayout(LayoutKind.Sequential)] internal struct UI23 {public IntPtr name,full,comment;public uint flags;public IntPtr sid;}
  [StructLayout(LayoutKind.Sequential)] internal struct FT { public uint lo,hi;public ulong Value {get{return ((ulong)hi<<32)|lo;}} }
  [StructLayout(LayoutKind.Sequential,CharSet=CharSet.Unicode)] internal struct SI {
   public int cb;public string reserved,desktop,title;public uint x,y,xs,ys,xc,yc,fill,flags;
   public ushort show,reserved2;public IntPtr reservedPtr,stdin,stdout,stderr;
  }
  [StructLayout(LayoutKind.Sequential)] internal struct PI {public IntPtr process,thread;public uint pid,tid;}
  [StructLayout(LayoutKind.Sequential)] internal struct BasicLimit {
   public long processTime,jobTime;public uint flags;public UIntPtr min,max;
   public uint active;public UIntPtr affinity;public uint priority,scheduling;
  }
  [StructLayout(LayoutKind.Sequential)] internal struct IO {public ulong a,b,c,d,e,f;}
  [StructLayout(LayoutKind.Sequential)] internal struct Extended {
   public BasicLimit basic;public IO io;public UIntPtr processMemory,jobMemory,peakProcess,peakJob;
  }
  [StructLayout(LayoutKind.Sequential)] internal struct Accounting {
   public long a,b,c,d;public uint faults,total,active,terminated;
  }
  [StructLayout(LayoutKind.Sequential)] internal struct FileInfo {
   public uint attrs;public FT created,accessed,written;public uint volume,sizeHi,sizeLo,links,indexHi,indexLo;
   public ulong Length {get{return ((ulong)sizeHi<<32)|sizeLo;}}
  }
  internal static readonly IntPtr Invalid=new IntPtr(-1);
  internal const uint Timeout=258;
  [DllImport("netapi32.dll",CharSet=CharSet.Unicode)] internal static extern uint NetUserAdd(string server,uint level,ref UI1 info,out uint parameter);
  [DllImport("netapi32.dll",CharSet=CharSet.Unicode)] internal static extern uint NetUserGetInfo(string server,string user,uint level,out IntPtr info);
  [DllImport("netapi32.dll",CharSet=CharSet.Unicode)] internal static extern uint NetUserDel(string server,string user);
  [DllImport("netapi32.dll")] internal static extern uint NetApiBufferFree(IntPtr p);
  [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
  [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool CreateProcessWithLogonW(string user,string domain,IntPtr password,uint logon,string application,StringBuilder command,uint flags,IntPtr environment,string cwd,ref SI si,out PI pi);
  [DllImport("advapi32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)]
  internal static extern bool OpenProcessToken(IntPtr process,uint access,out IntPtr token);
  [DllImport("advapi32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)]
  internal static extern bool GetTokenInformation(IntPtr token,int info,IntPtr buffer,uint length,out uint required);
  [DllImport("advapi32.dll",CharSet=CharSet.Unicode,SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)]
  internal static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string text,uint revision,out IntPtr sd,out uint length);
  [DllImport("advapi32.dll",CharSet=CharSet.Unicode)] internal static extern int RegOpenKeyExW(IntPtr root,string name,uint reserved,uint access,out IntPtr key);
  [DllImport("advapi32.dll")] internal static extern int RegCloseKey(IntPtr key);
  [DllImport("advapi32.dll",CharSet=CharSet.Unicode)] internal static extern int RegQueryValueExW(IntPtr key,string name,IntPtr reserved,out uint kind,byte[] data,ref uint bytes);
  [DllImport("kernel32.dll",SetLastError=true)] internal static extern IntPtr LocalFree(IntPtr p);
  [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool CloseHandle(IntPtr h);
  [DllImport("kernel32.dll",SetLastError=true)] internal static extern uint GetProcessId(IntPtr h);
  [DllImport("kernel32.dll")] internal static extern uint GetCurrentProcessId();
  [DllImport("kernel32.dll",SetLastError=true)] internal static extern uint GetThreadId(IntPtr h);
  [DllImport("kernel32.dll",SetLastError=true)] internal static extern uint GetProcessIdOfThread(IntPtr h);
  [DllImport("kernel32.dll",SetLastError=true)] internal static extern uint WaitForSingleObject(IntPtr h,uint milliseconds);
  [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool GetExitCodeProcess(IntPtr h,out uint code);
  [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool TerminateProcess(IntPtr h,uint code);
  [DllImport("kernel32.dll",SetLastError=true)] internal static extern uint ResumeThread(IntPtr h);
  [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool GetProcessTimes(IntPtr h,out FT created,out FT exited,out FT kernel,out FT user);
  [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool GetThreadTimes(IntPtr h,out FT created,out FT exited,out FT kernel,out FT user);
  [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool ProcessIdToSessionId(uint pid,out uint session);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)]
  internal static extern bool QueryFullProcessImageNameW(IntPtr h,uint flags,StringBuilder path,ref uint length);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] internal static extern IntPtr CreateJobObjectW(IntPtr sa,string name);
  [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool SetInformationJobObject(IntPtr job,int info,ref Extended data,uint bytes);
  [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
  [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool IsProcessInJob(IntPtr process,IntPtr job,out bool inside);
  [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool QueryInformationJobObject(IntPtr job,int info,IntPtr data,uint length,out uint returned);
  [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool TerminateJobObject(IntPtr job,uint code);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] internal static extern IntPtr CreateFileW(string path,uint access,uint share,IntPtr security,uint mode,uint flags,IntPtr template);
  [DllImport("kernel32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool GetFileInformationByHandle(IntPtr h,out FileInfo info);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] internal static extern uint GetFileAttributesW(string path);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode)] internal static extern uint GetDriveTypeW(string root);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool CreateDirectoryW(string path,ref SA security);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool DeleteFileW(string path);
  [DllImport("kernel32.dll",CharSet=CharSet.Unicode,SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool RemoveDirectoryW(string path);
  [DllImport("userenv.dll",CharSet=CharSet.Unicode,SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool GetProfilesDirectoryW(StringBuilder p,ref uint count);
  [DllImport("userenv.dll",CharSet=CharSet.Unicode,SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool GetUserProfileDirectoryW(IntPtr token,StringBuilder path,ref uint count);
  [DllImport("userenv.dll",CharSet=CharSet.Unicode,SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool DeleteProfileW(string sid,string path,string computer);
  [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)] internal static extern IntPtr CreateWindowStationW(string name,uint flags,uint access,ref SA sa);
  [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)] internal static extern IntPtr CreateDesktopW(string name,IntPtr device,IntPtr mode,uint flags,uint access,ref SA sa);
  [DllImport("user32.dll")] internal static extern IntPtr GetProcessWindowStation();
  [DllImport("user32.dll")] internal static extern IntPtr GetThreadDesktop(uint tid);
  [DllImport("kernel32.dll")] internal static extern uint GetCurrentThreadId();
  [DllImport("user32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool SetProcessWindowStation(IntPtr h);
  [DllImport("user32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool SetThreadDesktop(IntPtr h);
  [DllImport("user32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool CloseDesktop(IntPtr h);
  [DllImport("user32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)] internal static extern bool CloseWindowStation(IntPtr h);
  [DllImport("user32.dll",SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)]
  internal static extern bool GetUserObjectSecurity(IntPtr h,ref uint requested,IntPtr sd,uint length,out uint needed);
  [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)] [return:MarshalAs(UnmanagedType.Bool)]
  internal static extern bool GetUserObjectInformationW(IntPtr h,int index,StringBuilder text,uint bytes,out uint needed);
 }
 // Failures never expose Win32 error strings, input paths, usernames or SIDs.
 internal sealed class WindowsPlatform : IPlatform {
  readonly string probePath,expectedHash,parent;
  string runner,user,sid,root,target,image,profile,stationName,desktopName;
  IntPtr password,job,station,desktop,oldStation,oldDesktop,token;
  N.PI child;ulong processBirth,threadBirth;bool accountAddAttempted,accountOwned,launchAttempted,assigned;
  Pin sourcePin,imagePin,inputPin,resultPin,rootPin,targetPin,profilePin,journalPin;
  FileStream journal;bool rootOwned,targetOwned,profileSeen,accountDeleted,profileDeleted;
  bool processExit,jobEmpty,childClosed,guiClosed,hivesAbsent,jobClosed;
  bool secretWiped,releaseFault;byte[] nonce;
  public bool IsNative {get{return true;}}
  static void Need(bool b,Cause c) {if(!b)throw new Refusal(c);}
  static string Hex(byte[] b) {return BitConverter.ToString(b).Replace("-","").ToLowerInvariant();}
  static string Hash(byte[] b) {using(SHA256 s=SHA256.Create())return Hex(s.ComputeHash(b));}
  static string PathLocal(string p) {
   Need(p!=null&&p.Length>3&&p.Length<230&&!p.StartsWith(@"\\")&&p[1]==':'&&p[2]=='\\',Cause.FILES);
   foreach(char c in p)Need(c>31&&c!='"'&&c!='|',Cause.FILES);
   Need(p.IndexOf(':',2)<0&&Path.GetFullPath(p).TrimEnd('\\').Equals(p.TrimEnd('\\'),StringComparison.OrdinalIgnoreCase),Cause.FILES);
   return p.TrimEnd('\\');
  }
  static bool Missing(string p) {
   uint a=N.GetFileAttributesW(p);if(a!=UInt32.MaxValue)return false;
   int e=Marshal.GetLastWin32Error();Need(e==2||e==3,Cause.FILES);return true;
  }
  static void Chain(string p) {
   string at=Path.GetPathRoot(p);Need(at.Length==3&&N.GetDriveTypeW(at)==3,Cause.FILES);
   foreach(string part in p.Substring(3).Split('\\')) {
    if(part.Length==0)continue;at=Path.Combine(at,part);uint a=N.GetFileAttributesW(at);
    Need(a!=UInt32.MaxValue&&(a&0x400)==0,Cause.FILES);
   }
  }
  string Sddl(bool withTarget) {
   return "O:"+runner+"G:"+runner+"D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;"+runner+")"+
    (withTarget?"(A;OICI;FA;;;"+sid+")":"");
  }
  void Acl(string path,bool withTarget,bool file) {
   FileSystemSecurity ds=file?(FileSystemSecurity)File.GetAccessControl(path,AccessControlSections.Access|AccessControlSections.Owner):
    Directory.GetAccessControl(path,AccessControlSections.Access|AccessControlSections.Owner);
   Need(file||ds.AreAccessRulesProtected,Cause.FILES);
   string owner=ds.GetOwner(typeof(SecurityIdentifier)).Value;
   Need(owner==runner||owner=="S-1-5-18",Cause.FILES);
   HashSet<string> allowed=new HashSet<string>(StringComparer.Ordinal);
   allowed.Add(runner);allowed.Add("S-1-5-18");if(withTarget)allowed.Add(sid);
   HashSet<string> seen=new HashSet<string>(StringComparer.Ordinal);
   foreach(FileSystemAccessRule a in ds.GetAccessRules(true,true,typeof(SecurityIdentifier))) {
    string who=a.IdentityReference.Value;
    Need(a.AccessControlType==AccessControlType.Allow&&allowed.Contains(who)&&
     (a.FileSystemRights&FileSystemRights.FullControl)==FileSystemRights.FullControl,Cause.FILES);
    seen.Add(who);
   }
   Need(seen.SetEquals(allowed),Cause.FILES);
  }
  void MakeDir(string path,bool withTarget,Action acquired) {
   Need(Missing(path),Cause.FILES);IntPtr sd=IntPtr.Zero;uint bytes;
   Need(N.ConvertStringSecurityDescriptorToSecurityDescriptorW(Sddl(withTarget),1,out sd,out bytes),Cause.FILES);
   try {N.SA sa=new N.SA();sa.cb=Marshal.SizeOf(typeof(N.SA));sa.sd=sd;
    Need(N.CreateDirectoryW(path,ref sa),Cause.FILES);acquired();
   } finally {if(sd!=IntPtr.Zero&&N.LocalFree(sd)!=IntPtr.Zero)releaseFault=true;}
   Need(!releaseFault,Cause.CLEANUP);
   Acl(path,withTarget,false);
  }
  void Journal() {
   if(journal==null)return;
   Need(journalPin!=null,Cause.FILES);journalPin.Same();
   // Private newly-created runner/SYSTEM file. No credential bytes are stored.
   byte[] b=Encoding.UTF8.GetBytes("coh-owned-profile-private-v1\nuser="+(user??"")+
    "\nsid="+(sid??"")+"\nprofile="+(profile??"")+"\nroot="+(root??"")+
    "\nprocess="+child.pid+"\nthread="+child.tid+"\nprocess_birth="+processBirth+
    "\nthread_birth="+threadBirth+"\naccount_add_attempted="+accountAddAttempted+"\naccount_owned="+accountOwned+
    "\nlaunch_attempted="+launchAttempted+"\nassigned="+assigned+"\n");
   Need(b.Length<4096,Cause.FILES);journal.Position=0;journal.Write(b,0,b.Length);
   journal.SetLength(b.Length);journal.Flush(true);Array.Clear(b,0,b.Length);journalPin.Same();
  }
  public WindowsPlatform(string probe,string sha,string privateParent) {
   probePath=PathLocal(probe);parent=PathLocal(privateParent);
   Need(sha!=null&&sha.Length==64,Cause.FILES);
   foreach(char c in sha)Need((c>='0'&&c<='9')||(c>='a'&&c<='f'),Cause.FILES);
   expectedHash=sha;
  }
  public void Caller(Receipt r) {
   Need(Environment.OSVersion.Platform==PlatformID.Win32NT&&Environment.Is64BitProcess,Cause.CALLER);
   r.actual=true;
   using(WindowsIdentity impersonated=WindowsIdentity.GetCurrent(true))Need(impersonated==null,Cause.CALLER);
   using(WindowsIdentity who=WindowsIdentity.GetCurrent()) {
    Need(!who.IsSystem&&who.User!=null&&new WindowsPrincipal(who).IsInRole(WindowsBuiltInRole.Administrator),Cause.CALLER);
    runner=who.User.Value;
   }
   Need(Marshal.SizeOf(typeof(N.Extended))==144&&Marshal.SizeOf(typeof(N.PI))==24,Cause.CALLER);
   Chain(parent);Acl(parent,false,false);Chain(probePath);
   sourcePin=Pin.Open(probePath,false,false);Need(sourcePin.Info.Length>0&&sourcePin.Info.Length<=16*1024*1024,Cause.FILES);
   Need(Hash(sourcePin.Bytes(16*1024*1024))==expectedHash,Cause.FILES);
  }
  public void PrivateRoot(Receipt r) {
   nonce=new byte[16];using(RandomNumberGenerator g=RandomNumberGenerator.Create())g.GetBytes(nonce);
   string tag=Hex(nonce);root=Path.Combine(parent,"wpp-"+tag);target=Path.Combine(root,"target");
   MakeDir(root,false,delegate{rootOwned=true;});rootPin=Pin.Open(root,true,false);
   // CreateNew + exclusive parent: never overwrite any prior lease's journal.
   journal=new FileStream(Path.Combine(root,"owner.private"),FileMode.CreateNew,FileAccess.ReadWrite,FileShare.Read);
   journalPin=Pin.Open(Path.Combine(root,"owner.private"),false,true);
   Acl(journalPin.Path,false,true);
   Journal();
  }
  string AccountSid(bool absentAllowed) {
   IntPtr p=IntPtr.Zero;uint result=N.NetUserGetInfo(null,user,23,out p);
   if(result==2221&&absentAllowed)return null;
   Need(result==0&&p!=IntPtr.Zero,Cause.ACCOUNT);
   string value;
   try {N.UI23 row=(N.UI23)Marshal.PtrToStructure(p,typeof(N.UI23));
    Need(row.sid!=IntPtr.Zero,Cause.ACCOUNT);value=new SecurityIdentifier(row.sid).Value;
   } finally {if(N.NetApiBufferFree(p)!=0)releaseFault=true;}
   Need(!releaseFault,Cause.CLEANUP);return value;
  }
  bool KeyAbsent(IntPtr hive,string sub) {
   IntPtr key=IntPtr.Zero;int e=N.RegOpenKeyExW(hive,sub,0,0x20019|0x100,out key);
   if(e==2)return true;Need(e==0&&key!=IntPtr.Zero,Cause.PROFILE);
   if(N.RegCloseKey(key)!=0){releaseFault=true;throw new Refusal(Cause.CLEANUP);}return false;
  }
  bool HiveAbsent() {
   IntPtr hku=new IntPtr(unchecked((int)0x80000003));
   return KeyAbsent(hku,sid)&&KeyAbsent(hku,sid+"_Classes");
  }
  bool ProfileRegistrationAbsent() {
   return KeyAbsent(new IntPtr(unchecked((int)0x80000002)),
    @"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\"+sid);
  }
  bool RegisteredProfileMatches() {
   IntPtr key;Need(N.RegOpenKeyExW(new IntPtr(unchecked((int)0x80000002)),
    @"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList\"+sid,0,0x20019|0x100,out key)==0&&key!=IntPtr.Zero,Cause.PROFILE);
   bool same=false;
   try {
    byte[] data=new byte[520];uint bytes=520,kind;
    Need(N.RegQueryValueExW(key,"ProfileImagePath",IntPtr.Zero,out kind,data,ref bytes)==0&&
     (kind==1||kind==2)&&bytes>=2&&bytes<=520&&bytes%2==0&&data[bytes-1]==0&&data[bytes-2]==0,Cause.PROFILE);
    string text=Encoding.Unicode.GetString(data,0,(int)bytes-2);
    Need(text.IndexOf('\0')<0,Cause.PROFILE);
    if(kind==2)text=Environment.ExpandEnvironmentVariables(text);
    same=PathLocal(text).Equals(profile,StringComparison.OrdinalIgnoreCase);
   }finally{if(N.RegCloseKey(key)!=0)releaseFault=true;}
   Need(!releaseFault,Cause.CLEANUP);return same;
  }
  public void Account(Receipt r) {
   user="cwp"+Hex(nonce).Substring(0,16);Need(AccountSid(true)==null,Cause.ACCOUNT);
   password=Marshal.AllocHGlobal(130);byte[] random=new byte[60];
   for(int i=0;i<130;i++)Marshal.WriteByte(password,i,0);
   try {
    using(RandomNumberGenerator g=RandomNumberGenerator.Create())g.GetBytes(random);
    const string alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%_-";
    const string prefix="Aa1!";
    for(int i=0;i<64;i++)Marshal.WriteInt16(password,i*2,(short)(i<4?prefix[i]:alphabet[random[i-4]%alphabet.Length]));
    Marshal.WriteInt16(password,128,0);
   } finally {Array.Clear(random,0,random.Length);}
   N.UI1 info=new N.UI1();info.name=user;info.password=password;info.priv=1;
   info.flags=0x200|0x1|0x10000;uint parameter;
   // Persist the exact new-name intent before the first account side effect.
   // A crash can still interrupt the API/result/SID journal boundary; the
   // retained private intent is not permission to delete an unbound account.
   accountAddAttempted=true;Journal();
   Need(N.NetUserAdd(null,1,ref info,out parameter)==0,Cause.ACCOUNT);
   accountOwned=true;r.accountCreated=true;Journal();
   sid=AccountSid(false);Need(sid!=runner&&sid!="S-1-5-18",Cause.ACCOUNT);
   r.sidBound=true;Journal();
   uint cap=260;StringBuilder p=new StringBuilder(260);
   Need(N.GetProfilesDirectoryW(p,ref cap),Cause.PROFILE);
   string profiles=PathLocal(p.ToString());Chain(profiles);profile=Path.Combine(profiles,user);
   Need(Missing(profile)&&ProfileRegistrationAbsent()&&HiveAbsent(),Cause.PROFILE);Journal();
  }
  public void Files(Receipt r) {
   MakeDir(target,true,delegate{targetOwned=true;});targetPin=Pin.Open(target,true,false);
   byte[] imageBytes=sourcePin.Bytes(16*1024*1024);
   Need(Hash(imageBytes)==expectedHash,Cause.FILES);image=Path.Combine(target,"probe.exe");
   using(FileStream s=new FileStream(image,FileMode.CreateNew,FileAccess.Write,FileShare.Read)) {
    s.Write(imageBytes,0,imageBytes.Length);s.Flush(true);
   }
   imagePin=Pin.Open(image,false,false);Need(Hash(imagePin.Bytes(16*1024*1024))==expectedHash,Cause.FILES);
   // Only opaque nonce and expected SID/profile enter this protected file.
   using(FileStream f=new FileStream(Path.Combine(target,"probe.input"),FileMode.CreateNew,FileAccess.Write,FileShare.Read))
   using(BinaryWriter w=new BinaryWriter(f,Encoding.UTF8)) {
    w.Write(0x31505057);w.Write(nonce);w.Write(sid);w.Write(profile);w.Flush();f.Flush(true);
   }
   inputPin=Pin.Open(Path.Combine(target,"probe.input"),false,false);
   using(FileStream f=new FileStream(Path.Combine(target,"probe.result"),FileMode.CreateNew,FileAccess.Write,FileShare.ReadWrite))f.Flush(true);
   resultPin=Pin.Open(Path.Combine(target,"probe.result"),false,true);
   Acl(image,true,true);Acl(inputPin.Path,true,true);Acl(resultPin.Path,true,true);
   r.privateAcl=true;Journal();
  }
  public void Desktop(Receipt r) {
   oldStation=N.GetProcessWindowStation();oldDesktop=N.GetThreadDesktop(N.GetCurrentThreadId());
   Need(oldStation!=IntPtr.Zero&&oldDesktop!=IntPtr.Zero,Cause.DESKTOP);
   stationName="wpp_"+Hex(nonce);desktopName="probe";
   IntPtr sd=IntPtr.Zero;uint size;Need(N.ConvertStringSecurityDescriptorToSecurityDescriptorW(Sddl(true).Replace(";FA;;;",";GA;;;"),1,out sd,out size),Cause.DESKTOP);
   try {
    N.SA sa=new N.SA();sa.cb=Marshal.SizeOf(typeof(N.SA));sa.sd=sd;
    station=N.CreateWindowStationW(stationName,1,0xF037F,ref sa);Need(station!=IntPtr.Zero,Cause.DESKTOP);
    Need(N.SetProcessWindowStation(station),Cause.DESKTOP);
    desktop=N.CreateDesktopW(desktopName,IntPtr.Zero,IntPtr.Zero,0,0xF01FF,ref sa);
    Need(desktop!=IntPtr.Zero&&N.SetThreadDesktop(desktop),Cause.DESKTOP);
   } finally {if(sd!=IntPtr.Zero&&N.LocalFree(sd)!=IntPtr.Zero)releaseFault=true;}
   Need(!releaseFault,Cause.CLEANUP);
   GuiIdentity();r.desktopPrivate=true;Journal();
  }
  static string ObjectName(IntPtr h) {
   Need(h!=IntPtr.Zero,Cause.DESKTOP);StringBuilder name=new StringBuilder(128);uint needed;
   Need(N.GetUserObjectInformationW(h,2,name,256,out needed)&&needed>0&&needed<=256,Cause.DESKTOP);
   return name.ToString();
  }
  void ObjectAcl(IntPtr h,int all) {
   uint requested=5,needed;N.GetUserObjectSecurity(h,ref requested,IntPtr.Zero,0,out needed);
   Need(needed>=20&&needed<=4096,Cause.DESKTOP);IntPtr p=Marshal.AllocHGlobal((int)needed);
   try {
    uint written;Need(N.GetUserObjectSecurity(h,ref requested,p,needed,out written)&&written<=needed,Cause.DESKTOP);
    byte[] raw=new byte[(int)needed];Marshal.Copy(p,raw,0,raw.Length);
    RawSecurityDescriptor sd=new RawSecurityDescriptor(raw,0);
    Need(sd.Owner!=null&&sd.Owner.Value==runner&&sd.DiscretionaryAcl!=null&&
     (sd.ControlFlags&ControlFlags.DiscretionaryAclProtected)!=0&&sd.DiscretionaryAcl.Count==3,Cause.DESKTOP);
    HashSet<string> expected=new HashSet<string>(new string[]{runner,sid,"S-1-5-18"},StringComparer.Ordinal);
    foreach(GenericAce ace in sd.DiscretionaryAcl) {
     CommonAce a=ace as CommonAce;
     Need(a!=null&&a.AceQualifier==AceQualifier.AccessAllowed&&expected.Remove(a.SecurityIdentifier.Value)&&
      (a.AccessMask==0x10000000||a.AccessMask==all),Cause.DESKTOP);
    }
    Need(expected.Count==0,Cause.DESKTOP);
   }finally{Marshal.FreeHGlobal(p);}
  }
  void GuiIdentity() {
   Need(ObjectName(N.GetProcessWindowStation()).Equals(stationName,StringComparison.OrdinalIgnoreCase)&&
    ObjectName(N.GetThreadDesktop(N.GetCurrentThreadId())).Equals(desktopName,StringComparison.OrdinalIgnoreCase),Cause.DESKTOP);
   ObjectAcl(station,0xF037F);ObjectAcl(desktop,0xF01FF);
  }
  bool JobIsEmpty() {
   IntPtr list=Marshal.AllocHGlobal(8+64*8),acct=Marshal.AllocHGlobal(48);
   try {
    uint returned;Need(N.QueryInformationJobObject(job,3,list,520,out returned)&&returned>=8&&returned<=520,Cause.JOB);
    uint assignedCount=(uint)Marshal.ReadInt32(list),listed=(uint)Marshal.ReadInt32(list,4);
    Need(assignedCount==listed&&listed<=64&&8+listed*8<=returned,Cause.JOB);
    Need(N.QueryInformationJobObject(job,1,acct,48,out returned)&&returned==48,Cause.JOB);
    N.Accounting a=(N.Accounting)Marshal.PtrToStructure(acct,typeof(N.Accounting));
    return assignedCount==0&&listed==0&&a.active==0;
   } finally {Marshal.FreeHGlobal(list);Marshal.FreeHGlobal(acct);}
  }
  public void Job(Receipt r) {
   job=N.CreateJobObjectW(IntPtr.Zero,null);Need(job!=IntPtr.Zero,Cause.JOB);
   N.Extended e=new N.Extended();e.basic.flags=0x2000|0x8;e.basic.active=1;
   Need(N.SetInformationJobObject(job,9,ref e,144)&&JobIsEmpty(),Cause.JOB);
  }
  public void Launch(Receipt r) {
   Need(AccountSid(false)==sid&&HiveAbsent()&&ProfileRegistrationAbsent()&&Missing(profile),Cause.PROFILE);
   sourcePin.Same();imagePin.Same();inputPin.Same();resultPin.Same();
   Need(resultPin.Bytes(64).Length==0,Cause.FILES);
   N.SI si=new N.SI();si.cb=Marshal.SizeOf(typeof(N.SI));si.desktop=stationName+@"\"+desktopName;
   // No STARTF_USESTDHANDLES. No caller handle-value forwarding.
   StringBuilder command=new StringBuilder("\""+image+"\" --inert-probe",1024);
   Need(command.Length<1024,Cause.LAUNCH);launchAttempted=true;Journal();
   N.PI made;bool ok=N.CreateProcessWithLogonW(user,".",password,1,image,command,
    0x4|0x400|0x08000000,IntPtr.Zero,target,ref si,out made);
   if(!ok)throw new Refusal(Cause.LAUNCH);
   child=made;Need(child.process!=IntPtr.Zero&&child.thread!=IntPtr.Zero,Cause.LAUNCH);
   r.suspended=true;Journal();
  }
  void Identity(bool first) {
   Need(child.process!=IntPtr.Zero&&child.thread!=IntPtr.Zero&&
    N.GetProcessId(child.process)==child.pid&&N.GetThreadId(child.thread)==child.tid&&
    N.GetProcessIdOfThread(child.thread)==child.pid&&N.WaitForSingleObject(child.process,0)==N.Timeout&&
    N.WaitForSingleObject(child.thread,0)==N.Timeout,Cause.IDENTITY);
   N.FT pc,pe,pk,pu,tc,te,tk,tu;
   Need(N.GetProcessTimes(child.process,out pc,out pe,out pk,out pu)&&N.GetThreadTimes(child.thread,out tc,out te,out tk,out tu),Cause.IDENTITY);
   Need(pc.Value>0&&tc.Value>=pc.Value,Cause.IDENTITY);
   if(first){processBirth=pc.Value;threadBirth=tc.Value;}
   Need(pc.Value==processBirth&&tc.Value==threadBirth,Cause.IDENTITY);
   uint a,b;Need(N.ProcessIdToSessionId(child.pid,out a)&&
    N.ProcessIdToSessionId(N.GetCurrentProcessId(),out b)&&a==b,Cause.IDENTITY);
   StringBuilder path=new StringBuilder(1024);uint n=1024;
   Need(N.QueryFullProcessImageNameW(child.process,0,path,ref n)&&
    PathLocal(path.ToString()).Equals(image,StringComparison.OrdinalIgnoreCase),Cause.IDENTITY);
   if(token==IntPtr.Zero)Need(N.OpenProcessToken(child.process,8,out token),Cause.IDENTITY);
   Need(TokenSid()==sid,Cause.IDENTITY);
   imagePin.Same();Need(Hash(imagePin.Bytes(16*1024*1024))==expectedHash,Cause.IDENTITY);
  }
  string TokenSid() {
   uint size;N.GetTokenInformation(token,1,IntPtr.Zero,0,out size);
   Need(size>=16&&size<=4096,Cause.IDENTITY);IntPtr p=Marshal.AllocHGlobal((int)size);
   try {
    uint used;Need(N.GetTokenInformation(token,1,p,size,out used)&&used>=16&&used<=size,Cause.IDENTITY);
    IntPtr sp=Marshal.ReadIntPtr(p);ulong v=(ulong)sp.ToInt64(),start=(ulong)p.ToInt64();
    Need(start<=UInt64.MaxValue-size&&v>=start+16&&v<=start+used-8,Cause.IDENTITY);
    byte subs=Marshal.ReadByte(sp,1);Need(subs<=15&&v<=start+used-(8+(uint)subs*4),Cause.IDENTITY);
    return new SecurityIdentifier(sp).Value;
   } finally {Marshal.FreeHGlobal(p);}
  }
  public void Verify(Receipt r) {
   Identity(true);uint cap=260;StringBuilder p=new StringBuilder(260);
   Need(N.GetUserProfileDirectoryW(token,p,ref cap)&&
    PathLocal(p.ToString()).Equals(profile,StringComparison.OrdinalIgnoreCase)&&!ProfileRegistrationAbsent()&&
    RegisteredProfileMatches()&&!KeyAbsent(new IntPtr(unchecked((int)0x80000003)),sid),Cause.PROFILE);
   Chain(profile);profilePin=Pin.Open(profile,true,false);profileSeen=true;
   r.identity=true;Journal();
  }
  public void Assign(Receipt r) {
   Need(JobIsEmpty()&&N.AssignProcessToJobObject(job,child.process),Cause.ASSIGN);
   assigned=true;bool inside;Need(N.IsProcessInJob(child.process,job,out inside)&&inside,Cause.ASSIGN);
   r.assigned=true;Journal();
  }
  public void Resume(Receipt r) {
   Need(assigned&&!r.resumeAttempted,Cause.RESUME);Identity(false);GuiIdentity();
   bool inside;Need(N.IsProcessInJob(child.process,job,out inside)&&inside&&AccountSid(false)==sid,Cause.RESUME);
   r.resumeAttempted=true;Journal();
   uint previous=N.ResumeThread(child.thread);Need(previous==1,Cause.RESUME);
   r.resumed=true;Journal();
  }
  public void Probe(Receipt r) {
   Need(N.WaitForSingleObject(child.process,30000)==0,Cause.TIMEOUT);
   uint code;Need(N.GetExitCodeProcess(child.process,out code)&&code==0,Cause.PROBE);
   Need(JobIsEmpty(),Cause.JOB);resultPin.Same();
   byte[] bytes=resultPin.Bytes(64);
   Need(bytes.Length==8&&BitConverter.ToUInt32(bytes,0)==0x31525057&&BitConverter.ToUInt32(bytes,4)==0x3F,Cause.PROBE);
   Need(AccountSid(false)==sid&&Hash(sourcePin.Bytes(16*1024*1024))==expectedHash&&
    Hash(imagePin.Bytes(16*1024*1024))==expectedHash,Cause.IDENTITY);
   r.probe=true;
  }
  public void StopJob(Receipt r) {
   if(job==IntPtr.Zero)return;
   if(!JobIsEmpty())Need(N.TerminateJobObject(job,0xC000013A),Cause.CLEANUP);
  }
  public void StopDirect(Receipt r) {
   if(child.process==IntPtr.Zero){processExit=!launchAttempted;r.neverProcess=processExit;return;}
   bool ok=true;
   try {
    uint state=N.WaitForSingleObject(child.process,0);
    if(state==N.Timeout){if(!N.TerminateProcess(child.process,0xC000013A))ok=false;}
    else if(state!=0)ok=false;
   }catch{ok=false;}
   // A termination/query refusal must not skip the independent exact wait.
   try{processExit=N.WaitForSingleObject(child.process,10000)==0;}catch{processExit=false;ok=false;}
   r.processExited=processExit;Need(ok&&processExit,Cause.CLEANUP);
  }
  public void ObserveEmpty(Receipt r) {
   if(job==IntPtr.Zero){jobEmpty=true;r.neverJob=true;return;}
   Stopwatch w=Stopwatch.StartNew();
   do {if(JobIsEmpty()){jobEmpty=true;r.jobEmpty=true;return;}Thread.Sleep(20);}while(w.ElapsedMilliseconds<10000);
   throw new Refusal(Cause.CLEANUP);
  }
  static void Close(ref IntPtr h) {
   if(h==IntPtr.Zero)return;
   Need(N.CloseHandle(h),Cause.CLEANUP);h=IntPtr.Zero;
  }
  public void CloseChild(Receipt r) {
   Need(processExit&&jobEmpty,Cause.CLEANUP);
   bool ok=!Pin.CloseRefused;
   try{Close(ref token);}catch{ok=false;}
   try{Close(ref child.thread);}catch{ok=false;}
   try{Close(ref child.process);}catch{ok=false;}
   // Profile directory observation handle must be gone before hive/delete.
   try{if(profilePin!=null)profilePin.Close();}catch{ok=false;}
   ok=ok&&!Pin.CloseRefused;childClosed=ok;r.handlesClosed=ok;Need(ok,Cause.CLEANUP);
  }
  public void CloseGui(Receipt r) {
   Need(processExit&&jobEmpty,Cause.CLEANUP);
   bool ok=true;
   if(oldStation!=IntPtr.Zero)try{Need(N.SetProcessWindowStation(oldStation),Cause.CLEANUP);}catch{ok=false;}
   if(oldDesktop!=IntPtr.Zero)try{Need(N.SetThreadDesktop(oldDesktop),Cause.CLEANUP);}catch{ok=false;}
   if(desktop!=IntPtr.Zero)try{Need(N.CloseDesktop(desktop),Cause.CLEANUP);desktop=IntPtr.Zero;}catch{ok=false;}
   if(station!=IntPtr.Zero)try{Need(N.CloseWindowStation(station),Cause.CLEANUP);station=IntPtr.Zero;}catch{ok=false;}
   guiClosed=ok;r.guiClosed=ok;Need(ok,Cause.CLEANUP);
  }
  public void Hive(Receipt r) {
   Need(processExit&&jobEmpty&&childClosed&&guiClosed&&jobClosed,Cause.CLEANUP);
   if(sid==null){Need(!accountOwned,Cause.CLEANUP);hivesAbsent=true;r.hiveAbsent=true;return;}
   Stopwatch w=Stopwatch.StartNew();
   do {if(HiveAbsent()){hivesAbsent=true;r.hiveAbsent=true;return;}Thread.Sleep(50);}while(w.ElapsedMilliseconds<15000);
   throw new Refusal(Cause.CLEANUP);
  }
  public void DeleteProfile(Receipt r) {
   Need(processExit&&jobEmpty&&childClosed&&guiClosed&&hivesAbsent,Cause.CLEANUP);
   if(!accountOwned){
    // No profile API is eligible without a bound account. After an account-add
    // attempt, observe actual name absence; never infer it from missing SID.
    Need(!launchAttempted&&(!accountAddAttempted||AccountSid(true)==null),Cause.CLEANUP);
    r.profileAbsent=true;return;
   }
   Need(sid!=null&&AccountSid(false)==sid,Cause.ACCOUNT);
   if(!launchAttempted) {
    // No profile-load/process API has been invoked for this fresh SID.
    Need(ProfileRegistrationAbsent()&&HiveAbsent()&&(profile==null||Missing(profile)),Cause.CLEANUP);
    profileDeleted=true;r.profileAbsent=true;return;
   }
   if(ProfileRegistrationAbsent()) {
    Need(profile!=null&&Missing(profile),Cause.CLEANUP);profileDeleted=true;r.profileAbsent=true;return;
   }
   // Only the observed token-created profile, never a registry-only path guess.
   Need(profileSeen&&profilePin!=null&&profilePin.PathIdentitySame()&&RegisteredProfileMatches(),Cause.CLEANUP);
   Need(N.DeleteProfileW(sid,profile,null)&&ProfileRegistrationAbsent()&&HiveAbsent()&&Missing(profile),Cause.CLEANUP);
   profileDeleted=true;r.profileAbsent=true;
  }
  public void DeleteAccount(Receipt r) {
   if(!accountOwned){
    Need(!launchAttempted&&(!accountAddAttempted||AccountSid(true)==null),Cause.ACCOUNT);
    accountDeleted=true;r.accountAbsent=true;return;
   }
   Need(processExit&&jobEmpty&&childClosed&&guiClosed&&hivesAbsent&&profileDeleted&&sid!=null,Cause.CLEANUP);
   Need(AccountSid(false)==sid&&N.NetUserDel(null,user)==0&&AccountSid(true)==null,Cause.ACCOUNT);
   accountDeleted=true;r.accountAbsent=true;Journal();
  }
  public void CloseJob(Receipt r) {Need(jobEmpty,Cause.CLEANUP);Close(ref job);jobClosed=true;r.jobHandleClosed=true;}
  public void Wipe(Receipt r) {
   if(password!=IntPtr.Zero){
    for(int i=0;i<130;i++)Marshal.WriteByte(password,i,0);
    for(int i=0;i<130;i++)Need(Marshal.ReadByte(password,i)==0,Cause.CLEANUP);
    Marshal.FreeHGlobal(password);password=IntPtr.Zero;
   }
   if(nonce!=null)Array.Clear(nonce,0,nonce.Length);
   secretWiped=true;r.secretWiped=true;
  }
  public void RetireFiles(Receipt r) {
   r.journalRetained=journal!=null;
   bool safe=!releaseFault&&!Pin.CloseRefused&&processExit&&jobEmpty&&childClosed&&guiClosed&&jobClosed&&secretWiped&&
    (!accountAddAttempted||accountDeleted)&&(!accountOwned||profileDeleted);
   Journal();
   if(!safe)throw new Refusal(Cause.CLEANUP);
   // All known handles close independently; no unknown-name recursive delete.
   bool ok=true;
   foreach(Pin p in new Pin[]{sourcePin,imagePin,inputPin,resultPin,targetPin,rootPin})
    try{if(p!=null)p.Close();}catch{ok=false;}
   Need(ok&&!Pin.CloseRefused,Cause.CLEANUP);
   if(targetOwned) {
    foreach(Pin p in new Pin[]{imagePin,inputPin,resultPin}) {
     if(p==null)continue;Need(p.PathIdentitySame()&&N.DeleteFileW(p.Path)&&Missing(p.Path),Cause.CLEANUP);
    }
    Need(targetPin.PathIdentitySame()&&N.RemoveDirectoryW(target)&&Missing(target),Cause.CLEANUP);
   }
   if(journal!=null){
    journalPin.Same();journal.Dispose();journal=null;journalPin.Close();
    Need(journalPin.PathIdentitySame()&&N.DeleteFileW(Path.Combine(root,"owner.private")),Cause.CLEANUP);
    r.journalRetained=false;
   }
   if(rootOwned)Need(rootPin.PathIdentitySame()&&N.RemoveDirectoryW(root)&&Missing(root),Cause.CLEANUP);
   r.filesAbsent=true;r.journalRetained=false;
  }
  // File identity holds exclude writes/deletes while executing an image. Result
  // permits the one owned writer but denies replacement; directory handles are
  // closed before identity-checked deletion.
  sealed class Pin {
   public static bool CloseRefused;
   // Failed closes are not blindly retried. Keep private ownership until this
   // dedicated helper exits and refuse every complete-cleanup claim.
   static readonly List<IntPtr> heldRefusals=new List<IntPtr>();
   public readonly string Path;public readonly N.FileInfo Info;IntPtr h;
   Pin(string path,IntPtr handle,N.FileInfo info){Path=path;h=handle;Info=info;}
   public static Pin Open(string path,bool directory,bool writable) {
    IntPtr h=N.CreateFileW(path,0x80000000|0x20000,writable?3u:1u,IntPtr.Zero,3,
     0x00200000|(directory?0x02000000u:0u),IntPtr.Zero);
    Need(h!=N.Invalid,Cause.FILES);
    try{N.FileInfo i;Need(N.GetFileInformationByHandle(h,out i)&&(i.attrs&0x400)==0&&
      (((i.attrs&0x10)!=0)==directory)&&(directory||i.links==1),Cause.FILES);
     return new Pin(path,h,i);
    }catch{if(!N.CloseHandle(h)){CloseRefused=true;heldRefusals.Add(h);}throw;}
   }
   bool Equal(N.FileInfo b) {return b.volume==Info.volume&&b.indexHi==Info.indexHi&&b.indexLo==Info.indexLo&&
    b.created.Value==Info.created.Value&&b.attrs==Info.attrs&&b.links==Info.links;}
   public void Same() {Need(h!=IntPtr.Zero,Cause.FILES);N.FileInfo b;Need(N.GetFileInformationByHandle(h,out b)&&Equal(b)&&PathIdentitySame(),Cause.FILES);}
   public bool PathIdentitySame() {
    Pin p=Open(Path,(Info.attrs&0x10)!=0,true);
    bool equal=Equal(p.Info);
    try{p.Close();}catch{if(!equal)throw new Refusal(Cause.FILES);throw;}
    return equal;
   }
   public byte[] Bytes(int max) {
    Same();N.FileInfo now;Need(N.GetFileInformationByHandle(h,out now)&&now.Length<=(ulong)max,Cause.FILES);
    byte[] b=new byte[(int)now.Length];
    using(SafeFileHandle safe=new SafeFileHandle(h,false))
    using(FileStream f=new FileStream(safe,FileAccess.Read)) {
     f.Position=0;int at=0;while(at<b.Length){int n=f.Read(b,at,b.Length-at);Need(n>0,Cause.FILES);at+=n;}
     Need(f.ReadByte()==-1,Cause.FILES);
    }
    Same();N.FileInfo after;Need(N.GetFileInformationByHandle(h,out after)&&after.Length==now.Length&&
     after.written.Value==now.written.Value,Cause.FILES);return b;
   }
   public void Close(){
    try{WindowsPlatform.Close(ref h);}
    catch{CloseRefused=true;if(h!=IntPtr.Zero&&!heldRefusals.Contains(h))heldRefusals.Add(h);throw;}
   }
  }
 }
 public static class Program {
  public static int Main(string[] args) {
   Receipt r;
   try {
    if(args.Length!=4||args[0]!="--qualify-inert")throw new Refusal(Cause.CALLER);
    r=new Owner().Run(new WindowsPlatform(args[1],args[2],args[3]));
   }catch(Refusal e){r=new Receipt();r.first=e.Code;}
   catch{r=new Receipt();r.first=Cause.INTERNAL;}
   Console.Out.WriteLine(r.Json());return r.passed?0:1;
  }
 }
}
