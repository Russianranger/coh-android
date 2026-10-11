package io.github.russianranger.cohclientinteractive;

import java.util.Map;

/** Finite, session-owned instance and stock monorail transfers. */
public final class ClientZoning {
    private int epoch, currentMap, targetMap, captures;
    private String phase="disabled", session, lastStatus="";
    private boolean monorail;
    private long stationPid, stationRequest;
    private final java.util.Map<Long,Long> stationSequences=new java.util.HashMap<>();
    private long pid, requestUtc, deliveredUtc, eventUtc, arrivalUptime, watermark, lastCapture=-1, lastSequence=-1;
    public synchronized int epoch(){return epoch;}
    public synchronized int currentMap(){return currentMap;}
    public synchronized int targetMap(){return targetMap;}
    public synchronized int captures(){return captures;}
    public synchronized String phase(){return phase;}
    public synchronized boolean enabled(){return !"disabled".equals(phase);}
    public synchronized boolean blocksInput(){return monorail&&("preparing".equals(phase)||"ready".equals(phase))||"delivering".equals(phase)||"transferring".equals(phase)||"capturing".equals(phase)||"failed".equals(phase);}
    public synchronized boolean stockMonorail(){return monorail;}
    public synchronized boolean commandInFlight(){return "delivering".equals(phase);}
    public synchronized boolean canPrepare(){return !monorail&&"idle".equals(phase)&&epoch<4;}
    public synchronized boolean canTravel(){return !monorail&&"ready".equals(phase);}
    public static boolean supported(int map){return map==1||map==5||map==101;}
    public static String name(int map){return map==5?"Kings Row":map==101?"Atlas Park instance 2":"Atlas Park";}
    private static long integer(Object value){return value instanceof Integer||value instanceof Long?((Number)value).longValue():-1;}
    private static boolean yes(Map<?,?> e,String key){return Boolean.TRUE.equals(e.get(key));}
    public synchronized boolean prepare(long utc){
        if(!canPrepare()||utc<=eventUtc)return false;
        epoch++;targetMap=currentMap==1?101:1;requestUtc=utc;deliveredUtc=0;captures=0;
        phase="preparing";return true;
    }
    public synchronized boolean beginTravel(){if(!canTravel())return false;phase="delivering";return true;}
    public synchronized boolean delivered(long utc){
        if(!commandInFlight()||utc<requestUtc)return false;
        deliveredUtc=utc;phase="transferring";return true;
    }
    public synchronized void fail(){if(enabled())phase=blocksInput()?"failed":"prepare_failed";}
    public synchronized boolean accept(Map<?,?> e,String selectedSession,long selectedPid,int connectedMap,
            long wallNow,long uptimeNow,long sequence){
        return accept(e,selectedSession,selectedPid,connectedMap,wallNow,uptimeNow,sequence,false);
    }
    public synchronized boolean accept(Map<?,?> e,String selectedSession,long selectedPid,int connectedMap,
            long wallNow,long uptimeNow,long sequence,boolean allowMonorail){
        if(e==null||selectedSession==null||!selectedSession.matches("[0-9a-f]{32}")||selectedPid<=0
                ||!"character_zoning".equals(e.get("type"))||integer(e.get("format"))!=1
                ||!selectedSession.equals(e.get("session_id"))||integer(e.get("client_pid"))!=selectedPid
                ||integer(e.get("character_id"))!=1||uptimeNow<0||sequence<0)return false;
        long generated=integer(e.get("generated_utc_ms"));
        if(generated<=0||generated>wallNow+1000||wallNow-generated>120000||generated<eventUtc)return false;
        String next=String.valueOf(e.get("status"));
        if(generated==eventUtc&&next.equals(lastStatus))return false;
        long mapValue=integer(e.get("current_map_id")),targetValue=integer(e.get("target_map_id"));
        if(mapValue!=1&&mapValue!=101&&!(allowMonorail&&mapValue==5)
                ||targetValue!=1&&targetValue!=101&&!(allowMonorail&&targetValue==5))return false;
        int map=(int)mapValue,target=(int)targetValue;
        if(!supported(map)||!supported(target)||map==target&& !"arrived".equals(next))return false;
        if("enabled".equals(next)){
            if(enabled()||integer(e.get("epoch"))!=0||map!=connectedMap||!yes(e,"current_map_verified")||!yes(e,"zoning_enabled"))return false;
            boolean stock="stock_monorail".equals(e.get("travel_method"));
            if(stock&&(!allowMonorail||map!=1&&map!=5||target!=(map==1?5:1)))return false;
            if(!stock&&(map==5||target==5))return false;
            monorail=stock;
            session=selectedSession;pid=selectedPid;currentMap=map;targetMap=target;phase="idle";
        }else{
            if(monorail){
                if(!"stock_monorail".equals(e.get("travel_method"))||!allowMonorail)return false;
                long request=integer(e.get("native_request_sequence")),server=integer(e.get("native_station_pid"));
                long requested=integer(e.get("requested_utc_ms"));
                if(server<=0||request<=0||requested<=0||requested>generated)return false;
                if("preparing".equals(next)&&!"idle".equals(phase))return false;
                if("preparing".equals(next)&&"idle".equals(phase)){
                    if(!selectedSession.equals(session)||pid!=selectedPid||epoch>=4||integer(e.get("epoch"))!=epoch+1
                            ||map!=currentMap||target!=(currentMap==1?5:1)||requested<=eventUtc
                            ||!yes(e,"current_map_verified")||!yes(e,"native_station_request_verified")
                            ||request<=stationSequences.getOrDefault(server,0L))return false;
                    epoch++;targetMap=target;requestUtc=requested;deliveredUtc=0;captures=0;
                    stationPid=server;stationRequest=request;stationSequences.put(server,request);phase="preparing";
                }else if(server!=stationPid||request!=stationRequest||requested!=requestUtc)return false;
            }
            if(!selectedSession.equals(session)||pid!=selectedPid||integer(e.get("epoch"))!=epoch
                    ||epoch<1||target!=targetMap||generated<requestUtc)return false;
            if("preparing".equals(next)){
                if(!"preparing".equals(phase)||map!=currentMap)return false;
                // Already preparing locally; this event only records guest ownership.
            }else if("ready".equals(next)){
                if(!"preparing".equals(phase)||map!=currentMap||!yes(e,"destination_ready"))return false;
                phase="ready";
            }else if("transferring".equals(next)){
                if(monorail){
                    long sent=integer(e.get("sent_utc_ms"));
                    if(!"ready".equals(phase)||map!=currentMap||sent<requestUtc||sent>generated||!yes(e,"native_station_departure_verified"))return false;
                    deliveredUtc=sent;phase="transferring";
                }
                if(!"transferring".equals(phase)||map!=currentMap||generated<deliveredUtc)return false;
            }else if("arrived".equals(next)){
                if(!"transferring".equals(phase)||deliveredUtc<=0||generated<deliveredUtc
                        ||map!=targetMap||!yes(e,"arrival_native_verified")||!yes(e,"current_map_verified")
                        ||!yes(e,"character_identity_preserved")||!yes(e,"exact_destination_endpoint_verified")||integer(e.get("mapserver_pid"))<=0
                        ||integer(e.get("elapsed_ms"))<0)return false;
                currentMap=map;phase="capturing";arrivalUptime=uptimeNow;watermark=sequence;
                lastCapture=lastSequence=-1;captures=0;
            }else if("failed".equals(next)){
                if("idle".equals(phase)||"disabled".equals(phase)||"failed".equals(phase))return false;
                if(("preparing".equals(phase)||"ready".equals(phase))&&!yes(e,"transfer_requested")
                        &&yes(e,"current_map_verified")&&map==currentMap)phase="prepare_failed";
                else phase="failed";
            }else return false;
        }
        eventUtc=generated;lastStatus=next;return true;
    }
    public synchronized boolean canCapture(long captured,long sequence){
        return "capturing".equals(phase)&&captures<3&&captured>arrivalUptime&&sequence>watermark
                &&sequence>lastSequence&&(lastCapture<0||captured-lastCapture>=1000);
    }
    public synchronized boolean capture(long captured,long sequence){
        if(!canCapture(captured,sequence))return false;
        lastCapture=captured;lastSequence=sequence;if(++captures==3)phase="idle";return true;
    }
}
