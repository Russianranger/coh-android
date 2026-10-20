package org.coh.nativecombined;

import java.util.*;

/** Five SHOW values from the owned PostgreSQL instance; no admission authority. */
final class PostgresMemoryObservation {
    static final String[] KEYS={"max_connections","superuser_reserved_connections","shared_buffers","work_mem","maintenance_work_mem"};
    private String session="",status="not_observed",reason="POSTGRES_SHOW_NOT_OBSERVED";
    private Map<String,String> requested,observed;
    static Map<String,String> values(Map<String,String> source){
        if(source==null||source.size()!=KEYS.length)return null;
        Map<String,String> out=new LinkedHashMap<>();
        for(int i=0;i<KEYS.length;i++){
            String value=source.get(KEYS[i]);
            if(value==null||!value.matches(i<2?"[0-9]{1,10}":"[0-9]{1,15}(?:kB|MB|GB)?"))return null;
            out.put(KEYS[i],value);
        }return out;
    }
    synchronized void start(String id){
        session=id;status="not_observed";reason="POSTGRES_SHOW_NOT_OBSERVED";requested=observed=null;
    }
    synchronized boolean capture(String id,String source,String nextStatus,String nextReason,Map<String,String> nextRequested,Map<String,String> nextObserved){
        if(!GuestDiagnostics.sameSession(session,id)||!"owned_postgresql_SHOW".equals(source))return false;
        Map<String,String> safeRequested=values(nextRequested),safeObserved=values(nextObserved);
        if(safeRequested==null)return false;
        if("observed".equals(nextStatus)){
            if(!"".equals(nextReason)||safeObserved==null)return false;
        }else if(!"unavailable".equals(nextStatus)||nextObserved!=null||
                !("POSTGRES_SHOW_FAILED".equals(nextReason)||"POSTGRES_SHOW_RESULT_INVALID".equals(nextReason)))return false;
        status=nextStatus;reason=nextReason;requested=safeRequested;observed=safeObserved;return true;
    }
    synchronized Map<String,Object> snapshot(){
        Map<String,Object> out=new LinkedHashMap<>();out.put("observation_status",status);out.put("reason",reason);
        out.put("source","owned_postgresql_SHOW");out.put("session_id",session);out.put("rss_pss_change_measured",false);
        out.put("source_dbserver_connections",65);out.put("ordinary_spare_connections",4);
        if(requested!=null)out.put("requested",new LinkedHashMap<>(requested));
        if(observed!=null)out.put("observed",new LinkedHashMap<>(observed));return out;
    }
}
