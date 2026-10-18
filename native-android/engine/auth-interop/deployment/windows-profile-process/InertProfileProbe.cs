// NEW inert child only. Never launches a process, socket, service or UI.
// Source-only: not compiled or executed during this preparation.
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Text;
using Microsoft.Win32;

namespace CohWpp {
 public static class InertProfileProbe {
  [DllImport("user32.dll")] static extern IntPtr GetProcessWindowStation();
  [DllImport("user32.dll")] static extern IntPtr GetThreadDesktop(uint tid);
  [DllImport("kernel32.dll")] static extern uint GetCurrentThreadId();
  [DllImport("user32.dll",CharSet=CharSet.Unicode,SetLastError=true)]
  [return:MarshalAs(UnmanagedType.Bool)]
  static extern bool GetUserObjectInformationW(IntPtr h,int index,StringBuilder text,uint bytes,out uint needed);
  static void Need(bool ok) {if(!ok)throw new InvalidDataException();}
  static string ReadString(BinaryReader r) {
   uint n=0;int shift=0;
   for(int i=0;i<5;i++){
    byte b=r.ReadByte();Need(i<4||(b&0xF0)==0);
    n|=(uint)(b&127)<<shift;
    if((b&128)==0){
     Need(n>0&&n<=512);byte[] value=r.ReadBytes((int)n);Need(value.Length==n);
     string s=new UTF8Encoding(false,true).GetString(value);
     foreach(char c in s)Need(c>=32&&c!=0);return s;
    }
    shift+=7;
   }
   throw new InvalidDataException();
  }
  static string Name(IntPtr h) {
   Need(h!=IntPtr.Zero);StringBuilder s=new StringBuilder(128);uint required;
   Need(GetUserObjectInformationW(h,2,s,256,out required)&&required>0&&required<=256);
   return s.ToString();
  }
  static string Hex(byte[] b){return BitConverter.ToString(b).Replace("-","").ToLowerInvariant();}
  public static int Main(string[] args) {
   // No exception text or private value is ever written to either console stream.
   try {
    Need(args.Length==1&&args[0]=="--inert-probe"&&Environment.Is64BitProcess);
    string cwd=Environment.CurrentDirectory;
    string input=Path.Combine(cwd,"probe.input"),output=Path.Combine(cwd,"probe.result");
    Need((File.GetAttributes(input)&FileAttributes.ReparsePoint)==0&&
     (File.GetAttributes(output)&FileAttributes.ReparsePoint)==0);
    byte[] nonce;string expectedSid,expectedProfile;
    using(FileStream f=new FileStream(input,FileMode.Open,FileAccess.Read,FileShare.Read))
    using(BinaryReader r=new BinaryReader(f,Encoding.UTF8)){
     Need(f.Length>0&&f.Length<=1024&&r.ReadUInt32()==0x31505057);
     nonce=r.ReadBytes(16);Need(nonce.Length==16);
     expectedSid=ReadString(r);expectedProfile=ReadString(r);Need(f.Position==f.Length);
    }
    uint flags=0;
    using(WindowsIdentity me=WindowsIdentity.GetCurrent()){
     Need(me.User!=null&&!me.IsSystem&&me.User.Value==expectedSid);flags|=1;
    }
    Need(Path.GetFullPath(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile)).
     TrimEnd('\\').Equals(expectedProfile,StringComparison.OrdinalIgnoreCase));flags|=2;
    Need(Name(GetProcessWindowStation())=="wpp_"+Hex(nonce));flags|=16;
    Need(Name(GetThreadDesktop(GetCurrentThreadId()))=="probe");flags|=32;
    string key=@"Software\CohOwnedProfileProbe-"+Hex(nonce);
    using(RegistryKey hkcu=RegistryKey.OpenBaseKey(RegistryHive.CurrentUser,RegistryView.Registry64)){
     using(RegistryKey before=hkcu.OpenSubKey(key,false))Need(before==null);
     bool created=false;
     try{
      using(RegistryKey own=hkcu.CreateSubKey(key,RegistryKeyPermissionCheck.ReadWriteSubTree)){
       Need(own!=null);created=true;own.SetValue("inert",1,RegistryValueKind.DWord);own.Flush();
       Need(own.GetValueKind("inert")==RegistryValueKind.DWord&&
        own.GetValue("inert") is int&&(int)own.GetValue("inert")==1);flags|=4;
      }
     }finally{if(created)hkcu.DeleteSubKeyTree(key,false);}
     using(RegistryKey after=hkcu.OpenSubKey(key,false))Need(after==null);flags|=8;
    }
    Need(flags==0x3F);
    using(FileStream f=new FileStream(output,FileMode.Open,FileAccess.Write,FileShare.ReadWrite))
    using(BinaryWriter w=new BinaryWriter(f,Encoding.UTF8)){
     Need(f.Length==0);w.Write(0x31525057);w.Write(flags);w.Flush();f.SetLength(8);f.Flush(true);
    }
    Array.Clear(nonce,0,nonce.Length);return 0;
   }catch{return 2;}
  }
 }
}
