package org.coh.nativecombined;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.function.LongSupplier;

/** Read-only OS observations, never process ownership, cleanup or admission. */
final class ProcessSetMemory {
    static final int PROCESS_LIMIT=32, DIRECTORY_LIMIT=8192, FILE_LIMIT=16384;
    static final long INTERVAL_MS=5000, WINDOW_LIMIT_MS=1500, METRIC_LIMIT=1L<<50;
    interface ProcReader {String read(Path path,int cap)throws IOException;}
    private final ProcReader reader;
    ProcessSetMemory(){this(ProcessSetMemory::readFile);}
    ProcessSetMemory(ProcReader reader){this.reader=Objects.requireNonNull(reader);}
    private String read(Path path,int cap)throws IOException {String value=reader.read(path,cap);if(value==null||value.length()>cap)throw new IOException("PROC_FILE_LIMIT");return value;}
    private Map<String,Object> latest;
    private Long peakPss,peakRss;
    private long samples;
    private static final class Values {
        long uid=-1;Long rss;String name="";
    }
    private static String readFile(Path file,int cap)throws IOException {
        try(InputStream input=Files.newInputStream(file);ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            byte[] buffer=new byte[1024];int n;
            while((n=input.read(buffer))!=-1){if(n==0)continue;if(out.size()>cap-n)throw new IOException("PROC_FILE_LIMIT");out.write(buffer,0,n);}
            return new String(out.toByteArray(),StandardCharsets.US_ASCII);
        }
    }
    private static Long number(String value) {
        try{long n=Long.parseLong(value);return n>=0&&n<=METRIC_LIMIT?n:null;}catch(NumberFormatException invalid){return null;}
    }
    private static Long kib(String text,String key) {
        for(String line:text.split("\n"))if(line.startsWith(key)) {
            String[] fields=line.substring(key.length()).trim().split("\\s+");
            if(fields.length!=2||!"kB".equals(fields[1]))return null;
            Long value=number(fields[0]);return value==null||value>METRIC_LIMIT/1024?null:value*1024;
        }
        return null;
    }
    private static Values status(String raw) {
        Values result=new Values();result.rss=kib(raw,"VmRSS:");
        for(String line:raw.split("\n")) {
            if(line.startsWith("Uid:")){String[] fields=line.substring(4).trim().split("\\s+");Long uid=fields.length==4?number(fields[0]):null;if(uid!=null)result.uid=uid;}
            if(line.startsWith("Name:"))result.name=line.substring(5).trim();
        }
        return result;
    }
    private static Long startTicks(String raw,long pid) {
        int open=raw.indexOf('('),close=raw.lastIndexOf(") ");
        if(open<1||close<=open)return null;
        Long identity=number(raw.substring(0,open).trim());if(identity==null||identity!=pid)return null;
        String[] fields=raw.substring(close+2).trim().split("\\s+");
        return fields.length>19?number(fields[19]):null;
    }
    private static String namedRole(String word) {
        String base=word.replace('\\','/');int at=base.lastIndexOf('/');base=base.substring(at+1).toLowerCase(Locale.ROOT);
        if(base.equals("postgres")||base.startsWith("postgres:"))return "POSTGRESQL";
        if(Arrays.asList("wine","wine64","wine-preloader","wine64-preloader","wineserver","dbserver.exe","mapserver.exe","wineboot.exe","services.exe","explorer.exe","rpcss.exe","winedevice.exe").contains(base))return "WINE_SERVERS";
        return null;
    }
    private static String role(String name,String command,boolean self) {
        if(self)return "ANDROID_APP_AND_NATIVE_CLIENT";
        String known=namedRole(name);if(known!=null)return known;
        // Only executable positions; an arbitrary SQL/password argument must
        // never turn another process into PostgreSQL or Wine.
        if(command!=null){String[] args=command.split("\\x00",3);for(int i=0;i<Math.min(args.length,2);i++){
            known=namedRole(args[i]);if(known!=null)return known;
        }}
        return "OTHER_APP_UID";
    }
    private static Map<String,Object> unknown(long pid,String role) {
        Map<String,Object> row=new LinkedHashMap<>();row.put("pid",pid);row.put("start_ticks",null);row.put("role",role);
        row.put("rss_bytes",null);row.put("pss_bytes",null);row.put("identity_stable",false);return row;
    }
    private Map<String,Object> process(Path root,long pid,Values info,boolean self) {
        Path dir=root.resolve(Long.toString(pid));Map<String,Object> row=unknown(pid,self?"ANDROID_APP_AND_NATIVE_CLIENT":"OTHER_APP_UID");
        try {
            Long before=startTicks(read(dir.resolve("stat"),FILE_LIMIT),pid);if(before==null)return row;
            Values stable=status(read(dir.resolve("status"),FILE_LIMIT));if(stable.uid!=info.uid)return row;
            String command=null;try{command=read(dir.resolve("cmdline"),4096);}catch(IOException unavailable){/* comm remains usable, other roles stay unknown. */}
            String role=role(stable.name,command,self);Long pss=null;
            try{pss=kib(read(dir.resolve("smaps_rollup"),FILE_LIMIT),"Pss:");}catch(IOException unavailable){/* No guessed fallback or full smaps walk. */}
            Long after=startTicks(read(dir.resolve("stat"),FILE_LIMIT),pid);
            if(!before.equals(after))return row;
            row.put("start_ticks",before);row.put("role",role);row.put("rss_bytes",stable.rss);row.put("pss_bytes",pss);row.put("identity_stable",true);
        }catch(IOException|RuntimeException unavailable){/* Vanished/reused/inaccessible processes stay explicitly unknown. */}
        return row;
    }
    private static Long add(Long sum,Long value){return sum==null||value==null||value>Long.MAX_VALUE-sum?null:sum+value;}
    void sample(Path root,long uid,long self,boolean expectServer,LongSupplier clock,long utc) {
        long begin=clock.getAsLong(),unreadable=0,scanned=0;boolean complete=true;
        List<Map<String,Object>> rows=new ArrayList<>();Set<Long> seen=new HashSet<>();
        Map<String,Object> selfRow=unknown(self,"ANDROID_APP_AND_NATIVE_CLIENT");
        try{Values values=status(read(root.resolve(Long.toString(self)).resolve("status"),FILE_LIMIT));
            if(values.uid==uid)selfRow=process(root,self,values,true);else complete=false;
        }catch(IOException|RuntimeException unavailable){complete=false;}
        rows.add(selfRow);seen.add(self);
        try(DirectoryStream<Path> paths=Files.newDirectoryStream(root)) {
            for(Path path:paths){
                if(++scanned>DIRECTORY_LIMIT||clock.getAsLong()-begin>WINDOW_LIMIT_MS){complete=false;break;}
                String name=path.getFileName().toString();if(!name.matches("[0-9]{1,10}"))continue;
                Long pid=number(name);if(pid==null||pid==0||seen.contains(pid))continue;
                Values values;
                try{values=status(read(path.resolve("status"),FILE_LIMIT));}catch(IOException|RuntimeException unavailable){unreadable++;complete=false;continue;}
                if(values.uid<0){unreadable++;complete=false;continue;}if(values.uid!=uid)continue;
                if(rows.size()==PROCESS_LIMIT){complete=false;break;}
                seen.add(pid);rows.add(process(root,pid,values,false));
            }
        }catch(IOException|RuntimeException unavailable){complete=false;}
        long end=clock.getAsLong();if(end<begin||end-begin>WINDOW_LIMIT_MS)complete=false;
        Long rss=0L,pss=0L,observedRss=0L,observedPss=0L;int wine=0,postgres=0,missing=0;
        for(Map<String,Object> row:rows){
            Long r=(Long)row.get("rss_bytes"),p=(Long)row.get("pss_bytes");rss=add(rss,r);pss=add(pss,p);
            if(r!=null)observedRss=add(observedRss,r);if(p!=null)observedPss=add(observedPss,p);
            if(!Boolean.TRUE.equals(row.get("identity_stable"))||r==null||p==null)missing++;
            if("WINE_SERVERS".equals(row.get("role")))wine++;
            if("POSTGRESQL".equals(row.get("role")))postgres++;
        }
        boolean roles=!expectServer||(wine>0&&postgres>0);
        if(!complete||!roles){rss=null;pss=null;}
        Map<String,Object> out=new LinkedHashMap<>();
        out.put("schema","coh-same-uid-process-memory-v1");out.put("sampled_utc_ms",utc);
        out.put("begin_elapsed_ms",begin);out.put("end_elapsed_ms",end);out.put("sample_window_ms",Math.max(0,end-begin));
        out.put("uid",uid);out.put("self_pid",self);out.put("server_process_expected",expectServer);
        out.put("scan_complete",complete);out.put("expected_roles_observed",roles);out.put("unreadable_status_count",unreadable);
        out.put("process_limit",PROCESS_LIMIT);out.put("process_count",rows.size());out.put("wine_processes",wine);out.put("postgresql_processes",postgres);out.put("incomplete_process_metrics",missing);
        out.put("observed_rss_sum_bytes",observedRss);out.put("observed_pss_sum_bytes",observedPss);
        out.put("total_rss_bytes",rss);out.put("total_pss_bytes",pss);
        out.put("rss_sum_includes_repeated_shared_pages",true);out.put("pss_is_proportional",true);
        out.put("atomic_snapshot",false);out.put("deduplication","one row per PID/start_ticks; native client and launcher share the Android app row");
        out.put("scope","observed same-Android-UID processes; Wine/PostgreSQL identified by bounded kernel comm/argv; unavailable values are null; no GPU or whole-device total");
        out.put("source","proc PID status/stat/smaps_rollup; no full smaps scan");out.put("processes",rows);
        synchronized(this){
            if(rss!=null)peakRss=peakRss==null?rss:Math.max(peakRss,rss);
            if(pss!=null)peakPss=peakPss==null?pss:Math.max(peakPss,pss);
            out.put("sampled_peak_total_rss_bytes",peakRss);out.put("sampled_peak_total_pss_bytes",peakPss);
            if(samples<Long.MAX_VALUE)samples++;out.put("samples",samples);latest=out;
        }
    }
    synchronized Map<String,Object> snapshot() {
        if(latest==null){Map<String,Object> unknown=new LinkedHashMap<>();unknown.put("schema","coh-same-uid-process-memory-v1");unknown.put("status","not_sampled");unknown.put("total_rss_bytes",null);unknown.put("total_pss_bytes",null);return unknown;}
        Map<String,Object> copy=new LinkedHashMap<>(latest);List<Map<String,Object>> rows=new ArrayList<>();
        @SuppressWarnings("unchecked") List<Map<String,Object>> source=(List<Map<String,Object>>)latest.get("processes");
        for(Map<String,Object> row:source)rows.add(new LinkedHashMap<>(row));copy.put("processes",rows);return copy;
    }
}
