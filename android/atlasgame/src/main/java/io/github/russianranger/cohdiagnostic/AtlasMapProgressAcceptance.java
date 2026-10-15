package io.github.russianranger.cohdiagnostic;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Independently decodes the selected observer; protocol readiness remains a separate gate. */
final class AtlasMapProgressAcceptance {
    private static final String[] STAGES={"INITIALIZED","STARTUP","MAP_LOAD","DB_SETUP","READY_PUBLISH","READY_PUBLISHED",
        "RUNTIME_PRIORITY","RUNTIME_PRIORITY_DONE","HEAP_VALIDATE","HEAP_VALIDATED","SG_VERIFY","SG_VERIFIED",
        "CALLBACKS_ENABLE","CALLBACKS_ENABLED","RANDOM_SEED","ITEM_POWER_REQUEST","ITEM_POWER_REQUESTED",
        "ERROR_QUEUE_DRAIN","ERROR_QUEUE_DRAINED","READY_STDOUT","LAUNCHER_CONTACT","LATE_STARTUP_DONE","LOOP_PRE_TICK",
        "TICK_BEGIN","TICK_TOP","DB_COMM","DB_COMM_DONE","FOLDER_CALLBACKS","FOLDER_CALLBACKS_DONE","TICK_TOP_DONE",
        "ENTITY_UPDATE","GAME_LOGIC","TICK_BOTTOM","TICK_DONE","LOOP_POST_TICK","SLEEP","SLEEP_DONE"};

    static boolean accepts(Map<?,?> game,Map<?,?> producer) {
        Map<?,?> progress=object(game.get("mapserver_progress")),stages=object(progress.get("stages"));
        if(!yes(progress.get("enabled"))||!no(progress.get("is_success_proof"))||!number(progress.get("format"),1)
                ||!"COH_WINE_MAP_PROGRESS".equals(progress.get("environment_variable"))
                ||!number(progress.get("record_bytes"),128)||!number(progress.get("mapping_bytes"),4096)
                ||!producer.equals(progress.get("producer"))||!number(progress.get("history_limit_per_phase"),128)
                ||!number(progress.get("initial_history_per_phase"),16)||!number(progress.get("sample_interval_seconds"),5)
                ||stages.size()!=STAGES.length)return false;
        for(int i=0;i<STAGES.length;i++)if(!STAGES[i].equals(stages.get(String.valueOf(i+1))))return false;
        Map<?,?> phases=object(progress.get("phases")),startup=object(game.get("mapserver_startup")),guards=object(startup.get("phases"));
        if(!phases.keySet().equals(new HashSet<>(Arrays.asList("first","restart")))
                ||!guards.keySet().equals(phases.keySet())||!"dispatch_progress_v1".equals(startup.get("profile"))
                ||!yes(startup.get("requires_completed_tick_before_protocol")))return false;
        List<?> ready=list(game.get("phases"));if(ready.size()!=2)return false;
        Set<Object> paths=new HashSet<>(),identities=new HashSet<>();int phaseIndex=0;
        for(String label:new String[]{"first","restart"}) {
            Map<?,?> phase=object(phases.get(label));Object path=phase.get("path_name");
            if(!yes(phase.get("fresh_path_before_launch"))||!(label+"-atlas").equals(phase.get("process_label"))
                    ||!(path instanceof String)||((String)path).length()>128
                    ||!((String)path).matches("coh-map-progress-"+label+"-[^/\\\\]+\\.bin")||!paths.add(path)
                    ||!clock(phase.get("launch_monotonic"))||!positive(phase.get("launcher_pid")))return false;
            List<?> samples=list(phase.get("samples"));Object count=phase.get("sample_count"),dropped=phase.get("dropped_samples");
            if(samples.isEmpty()||samples.size()>128||!nonnegativeInteger(count)||!nonnegativeInteger(dropped)
                    ||samples.size()!=Math.min(longValue(count),128)||longValue(count)!=samples.size()+longValue(dropped))return false;
            Map<?,?> first=null,previous=null;double lastTime=doubleValue(phase.get("launch_monotonic"));long lastNumber=0;
            int sampleIndex=0;
            for(Object entry:samples) {
                Map<?,?> sample=object(entry);Object sampleNumber=sample.get("sample_number"),reason=sample.get("reason");
                long expectedNumber=sampleIndex<16||longValue(count)<=128?sampleIndex+1:longValue(count)-127+sampleIndex;
                sampleIndex++;
                if(!no(sample.get("is_success_proof"))||!(sample.get("available") instanceof Boolean)
                        ||!number(sampleNumber,expectedNumber)
                        ||!clock(sample.get("observed_monotonic"))||doubleValue(sample.get("observed_monotonic"))<lastTime
                        ||!(reason instanceof String)||((String)reason).length()>128)return false;
                lastNumber=longValue(sampleNumber);lastTime=doubleValue(sample.get("observed_monotonic"));
                if(!yes(sample.get("available")))continue;
                if(!record(sample)||!freshness(sample,phase))return false;
                if(previous!=null) {
                    if(!monotonic(previous,sample)||"initial".equals(sample.get("freshness"))
                            ||doubleValue(sample.get("last_advance_monotonic"))<doubleValue(previous.get("last_advance_monotonic")))return false;
                    if(longValue(sampleNumber)==longValue(previous.get("sample_number"))+1) {
                        boolean advanced=longValue(sample.get("sequence"))>longValue(previous.get("sequence"));
                        if(!(advanced?"advanced":"unchanged").equals(sample.get("freshness"))
                                ||(!advanced&&!sample.get("last_advance_monotonic").equals(previous.get("last_advance_monotonic"))))return false;
                    }
                }
                if(first==null)first=sample;previous=sample;
            }
            if(lastNumber!=longValue(count)||first==null||!identities.add(first.get("file_identity"))
                    ||longValue(previous.get("tick_started"))<=longValue(first.get("tick_started"))
                    ||longValue(previous.get("tick_completed"))<=longValue(first.get("tick_completed")))return false;
            Map<?,?> guard=object(guards.get(label)),before=object(guard.get("before")),after=object(guard.get("after")),protocol=object(guard.get("protocol"));
            if(!"passed".equals(guard.get("status"))||!positive(guard.get("attempts"))
                    ||!witness(before,phase,"startup-tick-before:"+label+"-ready")
                    ||!witness(after,phase,"startup-tick-after:"+label+"-ready")
                    ||longValue(before.get("sample_number"))>=longValue(after.get("sample_number"))
                    ||!sameIdentity(first,before)||!monotonic(before,after)||!monotonic(after,previous)
                    ||!positive(before.get("tick_completed"))||!clock(before.get("observed_monotonic"))
                    ||!clock(after.get("observed_monotonic"))||!clock(protocol.get("monotonic"))
                    ||doubleValue(before.get("observed_monotonic"))<doubleValue(phase.get("launch_monotonic"))
                    ||doubleValue(before.get("observed_monotonic"))>doubleValue(protocol.get("monotonic"))
                    ||doubleValue(protocol.get("monotonic"))>doubleValue(after.get("observed_monotonic"))
                    ||doubleValue(after.get("observed_monotonic"))>doubleValue(previous.get("observed_monotonic"))
                    ||!protocol.equals(object(ready.get(phaseIndex++)).get("map")))return false;
        }
        return true;
    }
    private static boolean witness(Map<?,?> sample,Map<?,?> phase,String reason) {
        Object number=sample.get("sample_number");long count=longValue(phase.get("sample_count"));
        if(!record(sample)||!freshness(sample,phase)||!positive(number)||longValue(number)>count||!reason.equals(sample.get("reason")))return false;
        for(Object retained:list(phase.get("samples")))if(number.equals(object(retained).get("sample_number")))return sample.equals(retained);
        // The first sixteen publications are never discarded. Only the middle
        // window between them and the 112-sample tail can carry a detached witness.
        return count>128&&longValue(number)>16&&longValue(number)<=count-112;
    }
    private static boolean freshness(Map<?,?> sample,Map<?,?> phase) {
        Object kind=sample.get("freshness"),last=sample.get("last_advance_monotonic"),observed=sample.get("observed_monotonic"),unchanged=sample.get("unchanged_seconds");
        if(!Arrays.asList("initial","advanced","unchanged").contains(kind)||!clock(last)||!clock(observed)||!clock(unchanged)
                ||doubleValue(last)<doubleValue(phase.get("launch_monotonic"))||doubleValue(last)>doubleValue(observed)
                ||Math.abs(doubleValue(unchanged)-(doubleValue(observed)-doubleValue(last)))>0.000501)return false;
        return "unchanged".equals(kind)||last.equals(observed);
    }
    private static boolean sameIdentity(Map<?,?> before,Map<?,?> after) {
        return before.get("windows_pid").equals(after.get("windows_pid"))&&before.get("main_thread_id").equals(after.get("main_thread_id"))
            &&before.get("file_identity").equals(after.get("file_identity"));
    }
    private static boolean monotonic(Map<?,?> before,Map<?,?> after) {
        if(!sameIdentity(before,after))return false;
        for(String key:new String[]{"sequence","tick_started","tick_completed"})if(longValue(after.get(key))<longValue(before.get(key)))return false;
        return !before.get("sequence").equals(after.get("sequence"))||before.get("raw_record_hex").equals(after.get("raw_record_hex"));
    }
    private static boolean record(Map<?,?> sample) {
        if(!yes(sample.get("available"))||!no(sample.get("is_success_proof")))return false;
        Object encoded=sample.get("raw_record_hex");if(!(encoded instanceof String)||!((String)encoded).matches("[0-9a-f]{256}"))return false;
        byte[] raw=new byte[128];for(int i=0;i<raw.length;i++)raw[i]=(byte)Integer.parseInt(((String)encoded).substring(i*2,i*2+2),16);
        byte[] magic={'C','O','H','M','A','P','1',0};for(int i=0;i<magic.length;i++)if(raw[i]!=magic[i])return false;
        for(int i=48;i<raw.length;i++)if(raw[i]!=0)return false;
        ByteBuffer data=ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);long[] fields=new long[10];
        for(int i=0;i<fields.length;i++)fields[i]=Integer.toUnsignedLong(data.getInt(8+4*i));
        if(fields[0]!=1||fields[1]!=128||fields[2]==0||fields[3]==0||fields[4]==0||fields[4]%2!=0
                ||fields[5]<1||fields[5]>STAGES.length||fields[7]>fields[6]||fields[6]>fields[7]+1||fields[8]!=0||fields[9]!=STAGES.length)return false;
        String[] keys={"format",null,"windows_pid","main_thread_id","sequence","stage_id","tick_started","tick_completed","flags","stage_count"};
        for(int i=0;i<keys.length;i++)if(keys[i]!=null&&!number(sample.get(keys[i]),fields[i]))return false;
        if(!STAGES[(int)fields[5]-1].equals(sample.get("stage")))return false;
        try {
            StringBuilder hash=new StringBuilder();for(byte b:MessageDigest.getInstance("SHA-256").digest(raw))hash.append(String.format(java.util.Locale.ROOT,"%02x",b&255));
            if(!hash.toString().equals(sample.get("raw_record_sha256")))return false;
        } catch(java.security.NoSuchAlgorithmException impossible){return false;}
        Map<?,?> identity=object(sample.get("file_identity"));return identity.size()==2&&nonnegativeInteger(identity.get("device"))&&nonnegativeInteger(identity.get("inode"));
    }
    private static Map<?,?> object(Object value){return value instanceof Map?(Map<?,?>)value:Collections.emptyMap();}
    private static List<?> list(Object value){return value instanceof List?(List<?>)value:Collections.emptyList();}
    private static boolean yes(Object value){return Boolean.TRUE.equals(value);}
    private static boolean no(Object value){return Boolean.FALSE.equals(value);}
    private static double doubleValue(Object value){return ((Number)value).doubleValue();}
    private static long longValue(Object value){return ((Number)value).longValue();}
    private static boolean clock(Object value){return value instanceof Number&&Double.isFinite(doubleValue(value))&&doubleValue(value)>=0;}
    private static boolean nonnegativeInteger(Object value){return clock(value)&&doubleValue(value)==longValue(value);}
    private static boolean positive(Object value){return nonnegativeInteger(value)&&longValue(value)>0;}
    private static boolean number(Object value,long expected){return nonnegativeInteger(value)&&longValue(value)==expected;}
    private AtlasMapProgressAcceptance(){}
}
