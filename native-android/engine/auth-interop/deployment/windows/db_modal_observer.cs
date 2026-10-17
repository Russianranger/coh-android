// Read-only, bounded current-desktop observer. Raw rows stay in a private file
// and are classified by Python; never send input, click, close or dismiss UI.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

public static class CohDbModalReader {
    public sealed class Row {
        public int pid;
        public bool top_level;
        public string class_name;
        public int control_id;
        public string text;
        public string text_status;
    }
    public sealed class Result {
        public int pid;
        public List<Row> rows = new List<Row>();
        public int enumerated_top_level;
        public bool deadline_reached;
        public bool inventory_bound_reached;
        public bool text_bound_reached;
        public int owner_changed_count;
        public bool top_level_enumeration_completed;
    }
    private delegate bool EnumCallback(IntPtr window, IntPtr data);
    [DllImport("user32.dll")] private static extern bool EnumWindows(EnumCallback callback, IntPtr data);
    [DllImport("user32.dll")] private static extern bool EnumChildWindows(IntPtr parent, EnumCallback callback, IntPtr data);
    [DllImport("user32.dll")] private static extern uint GetWindowThreadProcessId(IntPtr window, out uint pid);
    [DllImport("user32.dll", CharSet=CharSet.Unicode, ExactSpelling=true)] private static extern int GetClassNameW(IntPtr window, StringBuilder value, int count);
    [DllImport("user32.dll")] private static extern int GetDlgCtrlID(IntPtr window);
    [DllImport("user32.dll", EntryPoint="SendMessageTimeoutW", CharSet=CharSet.Unicode, ExactSpelling=true)]
    private static extern IntPtr ReadLength(IntPtr window, uint message, UIntPtr count, IntPtr value, uint flags, uint timeout, out UIntPtr result);
    [DllImport("user32.dll", EntryPoint="SendMessageTimeoutW", CharSet=CharSet.Unicode, ExactSpelling=true)]
    private static extern IntPtr ReadText(IntPtr window, uint message, UIntPtr count, StringBuilder value, uint flags, uint timeout, out UIntPtr result);
    private static Result result;
    private static Stopwatch clock;
    private static int characters, children, tops;
    private static bool WithinBounds() {
        if(clock.ElapsedMilliseconds>=8000) {result.deadline_reached=true;return false;}
        if(result.rows.Count>=80) {result.inventory_bound_reached=true;return false;}
        return true;
    }
    private static bool Owned(IntPtr window) {
        uint pid;GetWindowThreadProcessId(window,out pid);
        return pid==(uint)result.pid;
    }
    private static void Read(IntPtr window, bool top) {
        if(!WithinBounds() || !Owned(window))return;
        StringBuilder name=new StringBuilder(256);GetClassNameW(window,name,256);
        Row row=new Row {pid=result.pid,top_level=top,class_name=name.ToString(),
            control_id=GetDlgCtrlID(window),text="",text_status="timeout"};
        UIntPtr length;
        if(ReadLength(window,0x000e,UIntPtr.Zero,IntPtr.Zero,2,100,out length)!=IntPtr.Zero) {
            ulong requested=length.ToUInt64();
            int remaining=65536-characters;
            int capacity=(int)Math.Min(requested,(ulong)Math.Min(32768,remaining));
            bool truncated=requested>(ulong)capacity;
            if(truncated)result.text_bound_reached=true;
            if(capacity==0)row.text_status=truncated?"truncated":"ok";
            else if(WithinBounds() && Owned(window)) {
                StringBuilder text=new StringBuilder(capacity+1);UIntPtr copied;
                if(ReadText(window,0x000d,new UIntPtr((uint)(capacity+1)),text,2,100,out copied)!=IntPtr.Zero) {
                    row.text=text.ToString();characters+=row.text.Length;
                    row.text_status=truncated?"truncated":"ok";
                }
            }
        }
        if(!Owned(window)) {row.text="";row.text_status="owner_changed";result.owner_changed_count++;}
        result.rows.Add(row);
    }
    private static bool Child(IntPtr window,IntPtr data) {
        if(!WithinBounds())return false;
        if(!Owned(window))return true;
        if(children>=64) {result.inventory_bound_reached=true;return false;}
        children++;Read(window,false);return WithinBounds();
    }
    private static bool Top(IntPtr window,IntPtr data) {
        result.enumerated_top_level++;
        if(!WithinBounds() || result.enumerated_top_level>512) {result.inventory_bound_reached=true;return false;}
        if(!Owned(window))return true;
        if(tops>=16) {result.inventory_bound_reached=true;return false;}
        tops++;Read(window,true);
        if(WithinBounds())EnumChildWindows(window,Child,IntPtr.Zero);
        return WithinBounds();
    }
    public static Result Observe(int pid) {
        if(pid<=0)throw new ArgumentException("owned_pid");
        result=new Result {pid=pid};clock=Stopwatch.StartNew();characters=children=tops=0;
        result.top_level_enumeration_completed=EnumWindows(Top,IntPtr.Zero);return result;
    }
}
