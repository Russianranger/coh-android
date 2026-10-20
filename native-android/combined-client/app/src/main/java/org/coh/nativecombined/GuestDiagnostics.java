package org.coh.nativecombined;

import java.util.ArrayList;
import java.util.List;

/** Bounded public progress for one owned run; this never authorizes cleanup. */
final class GuestDiagnostics {
    private String session="",stage="",failure="",failureReason="";
    private long started,stageStarted,finished;
    private boolean ended;
    private final List<String> stages=new ArrayList<>();
    private final List<Long> times=new ArrayList<>();
    static boolean sameSession(String expected,String actual){
        return expected!=null&&expected.matches("[0-9a-f]{32}")&&expected.equals(actual);
    }
    static boolean currentReport(String expected,String actual,Object format,String app){
        return sameSession(expected,actual)&&Integer.valueOf(1).equals(format)&&"org.coh.nativecombined".equals(app);
    }
    static boolean cleanupProved(boolean exited,boolean current,Object complete){
        return exited&&current&&Boolean.TRUE.equals(complete);
    }
    static String failureCode(String value){
        return value!=null&&value.matches("[A-Z][A-Z0-9_]{0,79}")?value:"";
    }
    static String stageName(String value){
        return value!=null&&value.matches("[A-Za-z0-9_ .:-]{1,120}")?value:"";
    }
    static Long numericMetric(Object value){
        if(!(value instanceof Integer)&&!(value instanceof Long))return null;
        long number=((Number)value).longValue();
        return number>=0&&number<=(1L<<50)?number:null;
    }
    synchronized void start(String id,long now){
        if(!sameSession(id,id)||now<0)throw new IllegalArgumentException("Invalid run identity");
        session=id;stage="";failure="";failureReason="";started=stageStarted=now;finished=0;ended=false;stages.clear();times.clear();
        stage(id,"guest_starting",now);
    }
    synchronized boolean stage(String id,String value,long now){
        String safe=stageName(value);
        if(!sameSession(session,id)||safe.isEmpty()||safe.equals(stage)||now<stageStarted||ended)return false;
        stage=safe;stageStarted=now;
        if(stages.size()==64){stages.remove(0);times.remove(0);}
        stages.add(safe);times.add(now-started);return true;
    }
    static String failureDetail(Throwable error){
        if(error==null)return "Unknown exception";
        String type=error.getClass().getSimpleName();if(type.isEmpty())type="Exception";
        StringBuilder out=new StringBuilder(type.substring(0,Math.min(80,type.length())));
        String message=error.getMessage();
        if(message!=null&&!message.isEmpty()){
            out.append(": ");for(int i=0;i<message.length()&&out.length()<240;i++){
                char ch=message.charAt(i);int kind=Character.getType(ch);
                out.append(Character.isISOControl(ch)||kind==Character.LINE_SEPARATOR||kind==Character.PARAGRAPH_SEPARATOR?' ':ch);
            }
        }
        return out.toString();
    }
    synchronized void failure(String id,String code){failure(id,code,null);}
    synchronized void failure(String id,String code,Throwable error){
        String safe=failureCode(code);
        if(sameSession(session,id)&&failure.isEmpty()&&!safe.isEmpty()){
            failure=safe;failureReason=error==null?"":failureDetail(error);
        }
    }
    synchronized void finish(long now){if(!session.isEmpty()&&!ended&&now>=stageStarted){finished=now;ended=true;}}
    synchronized Snapshot snapshot(long now){
        long observed=ended?finished:Math.max(now,stageStarted);
        long[] elapsed=new long[times.size()];for(int i=0;i<elapsed.length;i++)elapsed[i]=times.get(i);
        return new Snapshot(stage,failure,failureReason,session.isEmpty()?0:observed-started,
            session.isEmpty()?0:observed-stageStarted,stages.toArray(new String[0]),elapsed);
    }
    static final class Snapshot {
        final String stage,failure,failureReason;
        final long elapsedMs,stageElapsedMs;
        final String[] stages;
        final long[] stageTimes;
        Snapshot(String stage,String failure,String reason,long elapsed,long stageElapsed,String[] stages,long[] times){
            this.stage=stage;this.failure=failure;failureReason=reason;elapsedMs=elapsed;stageElapsedMs=stageElapsed;this.stages=stages;stageTimes=times;
        }
    }
}
