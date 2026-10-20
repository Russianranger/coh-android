package org.coh.nativecombined;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.function.LongSupplier;

/** Read-only OS observations, never process ownership, cleanup or admission. */
final class ProcessSetMemory {
    static final int PROCESS_LIMIT=64, DIRECTORY_LIMIT=8192, FILE_LIMIT=16384;
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
        row.put("rss_bytes",null);row.put("pss_bytes",null);row.put("identity_stable",false);row.put("unavailable","OTHER_APP_UID".equals(role)?40:8);return row;
    }
    private static boolean emptyZombie(String raw,long pid) {
        if(startTicks(raw,pid)==null)return false;
        int close=raw.lastIndexOf(") ");String[] fields=raw.substring(close+2).trim().split("\\s+");
        // Linux stat fields 3/state, 23/vsize and 24/rss. No page-size guess:
        // a stable zombie with no address space contributes zero resident/PSS.
        return fields.length>21&&"Z".equals(fields[0])&&Long.valueOf(0).equals(number(fields[20]))
                &&Long.valueOf(0).equals(number(fields[21]));
    }
    private String command(Path dir) {
        try{return read(dir.resolve("cmdline"),4096);}catch(IOException unavailable){return null;}
    }
    private Map<String,Object> process(Path root,long pid,Values info,boolean self) {
        Path dir=root.resolve(Long.toString(pid));Map<String,Object> row=unknown(pid,self?"ANDROID_APP_AND_NATIVE_CLIENT":"OTHER_APP_UID");
        try {
            String beforeRaw=read(dir.resolve("stat"),FILE_LIMIT);Long before=startTicks(beforeRaw,pid);if(before==null)return row;
            Values stable=status(read(dir.resolve("status"),FILE_LIMIT));if(stable.uid!=info.uid)return row;
            String command=command(dir),role=role(stable.name,command,self);Long pss=null;int unavailable=stable.rss==null?1:0;
            if(!self&&namedRole(stable.name)==null&&(command==null||command.isEmpty()))unavailable|=32;
            boolean zombie=emptyZombie(beforeRaw,pid);
            if(!zombie)try{pss=kib(read(dir.resolve("smaps_rollup"),FILE_LIMIT),"Pss:");if(pss==null)unavailable|=2;}
            catch(IOException missing){unavailable|=4;}
            String afterRaw=read(dir.resolve("stat"),FILE_LIMIT);Long after=startTicks(afterRaw,pid);
            if(!before.equals(after))return row;
            zombie=zombie&&emptyZombie(afterRaw,pid);
            if(!zombie&&pss==null&&(unavailable&6)==0)unavailable|=2;
            row.put("start_ticks",before);row.put("role",role);row.put("rss_bytes",zombie?Long.valueOf(0):stable.rss);row.put("pss_bytes",zombie?Long.valueOf(0):pss);row.put("identity_stable",true);
            row.remove("unavailable");
            if(zombie){row.put("zombie_no_address_space",true);if((unavailable&32)!=0)row.put("unavailable",32);}
            else if(unavailable!=0)row.put("unavailable",unavailable);
        }catch(IOException|RuntimeException unavailable){row.put("unavailable",self?24:56);}
        return row;
    }
    private static Map<String,String> unavailableCodes(int flags) {
        Map<String,String> codes=new LinkedHashMap<>();
        for(int i=0;i<6;i++)if((flags&(1<<i))!=0)codes.put(Integer.toString(1<<i),new String[]{"RSS_FIELD_UNAVAILABLE","PSS_FIELD_UNAVAILABLE","PSS_READ_FAILED","PROCESS_IDENTITY_UNAVAILABLE","PROCESS_READ_FAILED","PROCESS_ROLE_UNAVAILABLE"}[i]);
        return codes;
    }
    private static Long add(Long sum,Long value){return sum==null||value==null||value>Long.MAX_VALUE-sum?null:sum+value;}
    private static final String[] ROLES={"ANDROID_APP_AND_NATIVE_CLIENT","WINE_SERVERS","POSTGRESQL","OTHER_APP_UID"};
    private static int roleIndex(Map<String,Object> row){for(int i=0;i<ROLES.length;i++)if(ROLES[i].equals(row.get("role")))return i;return 3;}
    static final class Aggregate {
        long count,missingRss,missingPss,zombies,unstable,unclassified;Long rss=0L,pss=0L;
        void accept(Map<String,Object> row){
            count++;Long r=(Long)row.get("rss_bytes"),p=(Long)row.get("pss_bytes");
            if(r==null)missingRss++;else rss=add(rss,r);
            if(p==null)missingPss++;else pss=add(pss,p);
            if(Boolean.TRUE.equals(row.get("zombie_no_address_space")))zombies++;
            if(!Boolean.TRUE.equals(row.get("identity_stable")))unstable++;
            if(row.get("unavailable") instanceof Integer&&(((Integer)row.get("unavailable"))&32)!=0)unclassified++;
        }
        Map<String,Object> snapshot(boolean scan,boolean classified,boolean expected){
            boolean r=scan&&classified&&expected&&missingRss==0&&rss!=null;
            boolean p=scan&&classified&&expected&&missingPss==0&&pss!=null;
            int reasons=(!scan?1:0)|(missingRss>0?2:0)|(missingPss>0?4:0)|(rss==null||pss==null?8:0)
                    |(unstable>0?16:0)|(!classified?32:0)|(!expected?64:0);
            Map<String,Object> out=new LinkedHashMap<>();out.put("process_count",count);out.put("observed_rss_bytes",rss);out.put("observed_pss_bytes",pss);
            out.put("rss_bytes",r?rss:null);out.put("pss_bytes",p?pss:null);out.put("rss_complete",r);out.put("pss_complete",p);
            out.put("missing_rss_processes",missingRss);out.put("missing_pss_processes",missingPss);out.put("zombie_processes",zombies);out.put("reason_flags",reasons);return out;
        }
    }
    private static Map<String,Object> aggregation(Aggregate total,Aggregate[] groups,boolean scan,boolean expected,long scanned){
        Map<String,Object> out=new LinkedHashMap<>(),categories=new LinkedHashMap<>();
        out.put("scope","all_scanned_same_uid_processes");out.put("directory_entry_limit",DIRECTORY_LIMIT);out.put("directory_entries_scanned",scanned);
        out.put("role_unclassified_processes",total.unclassified);out.put("total",total.snapshot(scan,true,expected));
        for(int i=0;i<groups.length;i++)categories.put(ROLES[i],groups[i].snapshot(scan,total.unclassified==0,expected));
        out.put("categories",categories);
        Map<String,String> reasons=new LinkedHashMap<>();String[] codes={"SCAN_INCOMPLETE","RSS_UNAVAILABLE","PSS_UNAVAILABLE","SUM_OVERFLOW","IDENTITY_UNSTABLE","ROLE_UNCLASSIFIED","EXPECTED_ROLES_NOT_OBSERVED"};
        for(int i=0;i<codes.length;i++)reasons.put(Integer.toString(1<<i),codes[i]);out.put("reason_codes",reasons);return out;
    }
    void sample(Path root,long uid,long self,boolean expectServer,LongSupplier clock,long utc) {
        long begin=clock.getAsLong(),unreadable=0,scanned=0,omitted=0;boolean complete=true;int unavailableFlags=0;
        Map<String,Object> cgroup=AppCgroupMemory.observe(root,uid,reader);
        Aggregate total=new Aggregate();Aggregate[] groups={new Aggregate(),new Aggregate(),new Aggregate(),new Aggregate()};
        List<Map<String,Object>> rows=new ArrayList<>();Set<Long> seen=new HashSet<>();
        Map<String,Object> selfRow=unknown(self,"ANDROID_APP_AND_NATIVE_CLIENT");
        try{Values values=status(read(root.resolve(Long.toString(self)).resolve("status"),FILE_LIMIT));
            if(values.uid==uid)selfRow=process(root,self,values,true);else complete=false;
        }catch(IOException|RuntimeException unavailable){complete=false;}
        rows.add(selfRow);seen.add(self);total.accept(selfRow);groups[0].accept(selfRow);if(selfRow.get("unavailable") instanceof Integer)unavailableFlags|=(Integer)selfRow.get("unavailable");
        try(DirectoryStream<Path> paths=Files.newDirectoryStream(root)) {
            for(Path path:paths){
                if(++scanned>DIRECTORY_LIMIT||clock.getAsLong()-begin>WINDOW_LIMIT_MS){complete=false;break;}
                String name=path.getFileName().toString();if(!name.matches("[0-9]{1,10}"))continue;
                Long pid=number(name);if(pid==null||pid==0||!Long.toString(pid).equals(name)||seen.contains(pid))continue;
                if(Files.isSymbolicLink(path)){unreadable++;complete=false;continue;}
                Values values;
                try{values=status(read(path.resolve("status"),FILE_LIMIT));}catch(IOException|RuntimeException unavailable){unreadable++;complete=false;continue;}
                if(values.uid<0){unreadable++;complete=false;continue;}if(values.uid!=uid)continue;
                seen.add(pid);Map<String,Object> measured=process(root,pid,values,false);
                total.accept(measured);groups[roleIndex(measured)].accept(measured);
                if(measured.get("unavailable") instanceof Integer)unavailableFlags|=(Integer)measured.get("unavailable");
                if(rows.size()==PROCESS_LIMIT){
                    omitted++;
                    // Detail retention is independent of streaming accounting.
                    if(roleIndex(measured)!=3)for(int i=rows.size()-1;i>0;i--)if(roleIndex(rows.get(i))==3){rows.set(i,measured);break;}
                }else rows.add(measured);
            }
        }catch(IOException|RuntimeException unavailable){complete=false;}
        long end=clock.getAsLong();if(end<begin||end-begin>WINDOW_LIMIT_MS)complete=false;
        int wine=0,postgres=0,missing=0;
        for(Map<String,Object> row:rows){
            if(!Boolean.TRUE.equals(row.get("identity_stable"))||row.get("rss_bytes")==null||row.get("pss_bytes")==null)missing++;
            if("WINE_SERVERS".equals(row.get("role")))wine++;if("POSTGRESQL".equals(row.get("role")))postgres++;
        }
        boolean roles=!expectServer||(groups[1].count>0&&groups[2].count>0);
        Map<String,Object> aggregate=aggregation(total,groups,complete,roles,Math.min(scanned,DIRECTORY_LIMIT));
        @SuppressWarnings("unchecked") Map<String,Object> overall=(Map<String,Object>)aggregate.get("total");
        Long rss=(Long)overall.get("rss_bytes"),pss=(Long)overall.get("pss_bytes");
        Map<String,Object> out=new LinkedHashMap<>();
        out.put("schema","coh-same-uid-process-memory-v1");out.put("sampled_utc_ms",utc);
        out.put("begin_elapsed_ms",begin);out.put("end_elapsed_ms",end);out.put("sample_window_ms",Math.max(0,end-begin));
        out.put("app_uid_cgroup",cgroup);out.put("uid",uid);out.put("self_pid",self);out.put("server_process_expected",expectServer);
        out.put("scan_complete",complete);out.put("expected_roles_observed",roles);out.put("unreadable_status_count",unreadable);
        out.put("omitted_same_uid_processes",omitted);out.put("detail_rows_omitted",omitted);out.put("unavailable_codes",unavailableCodes(unavailableFlags));out.put("aggregation",aggregate);
        out.put("process_limit",PROCESS_LIMIT);out.put("process_count",rows.size());out.put("wine_processes",wine);out.put("postgresql_processes",postgres);out.put("incomplete_process_metrics",missing);
        out.put("observed_rss_sum_bytes",total.rss);out.put("observed_pss_sum_bytes",total.pss);
        out.put("total_rss_bytes",rss);out.put("total_pss_bytes",pss);
        out.put("rss_sum_includes_repeated_shared_pages",true);out.put("pss_is_proportional",true);
        out.put("atomic_snapshot",false);out.put("deduplication","PID/start_ticks; app and native client share one row");
        out.put("scope","same UID; Wine/PostgreSQL by comm/argv; null means unknown; zombie zeros use stable stat Z/vsize/rss=0; no GPU/device total");
        out.put("source","proc PID status/stat/smaps_rollup; no full smaps scan");out.put("processes",rows);
        synchronized(this){
            if(rss!=null)peakRss=peakRss==null?rss:Math.max(peakRss,rss);
            if(pss!=null)peakPss=peakPss==null?pss:Math.max(peakPss,pss);
            out.put("sampled_peak_total_rss_bytes",peakRss);out.put("sampled_peak_total_pss_bytes",peakPss);
            if(samples<Long.MAX_VALUE)samples++;out.put("samples",samples);latest=out;
        }
    }
    Map<String,Object> exportSnapshot() {
        Map<String,Object> copy=snapshot();
        @SuppressWarnings("unchecked") List<Map<String,Object>> rows=(List<Map<String,Object>>)copy.get("processes");
        if(rows==null)return copy;
        // Aggregates preserve every measurement; optional PID detail is bounded
        // separately so category and cgroup metadata fit the unchanged reader.
        List<Map<String,Object>> detail=new ArrayList<>();for(int category=0;category<ROLES.length;category++)for(Map<String,Object> row:rows)if(roleIndex(row)==category&&detail.size()<32)detail.add(row);
        int limit=detail.size(),wine=0,postgres=0,missing=0;
        List<String> fields=Arrays.asList("pid","start_ticks","role","rss_bytes","pss_bytes","identity_stable","unavailable","zombie_no_address_space");
        List<List<Object>> compact=new ArrayList<>();
        for(int i=0;i<limit;i++){Map<String,Object> row=detail.get(i);List<Object> values=new ArrayList<>();for(String field:fields){
            Object value=row.get(field);if(field.equals("unavailable")&&value==null)value=0;if(field.equals("zombie_no_address_space")&&value==null)value=false;values.add(value);
        }compact.add(values);if(roleIndex(row)==1)wine++;if(roleIndex(row)==2)postgres++;
            if(!Boolean.TRUE.equals(row.get("identity_stable"))||row.get("rss_bytes")==null||row.get("pss_bytes")==null)missing++;
        }
        @SuppressWarnings("unchecked") Map<String,Object> aggregate=(Map<String,Object>)copy.get("aggregation");
        @SuppressWarnings("unchecked") Map<String,Object> total=(Map<String,Object>)aggregate.get("total");
        long omitted=((Number)total.get("process_count")).longValue()-limit;
        copy.put("detail_selection","app_then_wine_then_postgresql_then_other");copy.put("detail_export_limit",32);copy.put("detail_rows_omitted",omitted);copy.put("omitted_same_uid_processes",omitted);
        copy.put("process_count",limit);copy.put("wine_processes",wine);copy.put("postgresql_processes",postgres);copy.put("incomplete_process_metrics",missing);
        copy.put("process_row_fields",fields);copy.put("processes",compact);return copy;
    }
    private static Object detached(Object value){
        if(value instanceof Map){Map<String,Object> copy=new LinkedHashMap<>();for(Object entry:((Map<?,?>)value).entrySet()){
            Map.Entry<?,?> e=(Map.Entry<?,?>)entry;copy.put((String)e.getKey(),detached(e.getValue()));}return copy;}
        if(value instanceof List){List<Object> copy=new ArrayList<>();for(Object item:(List<?>)value)copy.add(detached(item));return copy;}
        return value;
    }
    @SuppressWarnings("unchecked") synchronized Map<String,Object> snapshot() {
        if(latest==null){Map<String,Object> unknown=new LinkedHashMap<>();unknown.put("schema","coh-same-uid-process-memory-v1");unknown.put("status","not_sampled");unknown.put("total_rss_bytes",null);unknown.put("total_pss_bytes",null);return unknown;}
        return (Map<String,Object>)detached(latest);
    }
}
