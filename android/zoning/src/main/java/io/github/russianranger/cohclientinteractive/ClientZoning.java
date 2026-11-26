package io.github.russianranger.cohclientinteractive;

import java.util.Map;

/** Finite, session-owned instance and stock monorail transfers; or the game's own zone travel. */
public final class ClientZoning {
    private int epoch, currentMap, targetMap, captures;
    private String phase="disabled", session, lastStatus="", currentName="";
    private boolean monorail;
    /** The game's own zone travel: doors, tunnels and the monorail move the player; the app only follows. */
    private boolean stockTravel;
    private boolean monorailRequiresReopen;
    private long stationPid, stationRequest;
    private final java.util.Map<Long,Long> stationSequences=new java.util.HashMap<>();
    private long pid, requestUtc, deliveredUtc, eventUtc, arrivalUptime, watermark, lastCapture=-1, lastSequence=-1;
    public synchronized int epoch(){return epoch;}
    public synchronized int currentMap(){return currentMap;}
    public synchronized int targetMap(){return targetMap;}
    public synchronized int captures(){return captures;}
    public synchronized String phase(){return phase;}
    public synchronized boolean enabled(){return !"disabled".equals(phase);}
    public synchronized boolean stockTravel(){return stockTravel;}
    public synchronized String currentName(){return currentName.isEmpty()?name(currentMap):currentName;}
    public synchronized boolean blocksInput(){return !stockTravel&&(monorail&&("preparing".equals(phase)||"ready".equals(phase))||"delivering".equals(phase)||"transferring".equals(phase)||"capturing".equals(phase)||"failed".equals(phase));}
    public synchronized boolean stockMonorail(){return monorail;}
    public synchronized boolean monorailRequiresReopen(){return monorailRequiresReopen;}
    public synchronized boolean commandInFlight(){return "delivering".equals(phase);}
    public synchronized boolean canPrepare(){return !monorail&&!stockTravel&&"idle".equals(phase)&&epoch<4;}
    public synchronized boolean canTravel(){return !monorail&&!stockTravel&&"ready".equals(phase);}
    public static boolean supported(int map){return map==1||map==5||map==101;}
    /**
     * 0.13.85, the second hero slot: swap the saved hero's folder with the other slot's by renaming.
     * `saved`: the saved hero's folder is complete; `readable`: it is complete or absent (never
     * touch an incomplete one). No folder is opened, copied or deleted. Kept here (plain Java) so
     * the shipped code is the code the tests run.
     */
    public static String switchHeroFolders(java.io.File current,java.io.File other,java.io.File pending,boolean saved,boolean readable) throws java.io.IOException {
        if(!readable)throw new java.io.IOException("The saved hero's data is incomplete or unreadable. Nothing was changed.");
        if(pending.exists())throw new java.io.IOException("An earlier hero switch did not finish. Nothing was changed; export a report.");
        boolean hasOther=other.isDirectory();
        if(other.exists()&&!hasOther)throw new java.io.IOException("The other hero slot is not a folder. Nothing was changed.");
        if(!saved){
            if(current.exists())throw new java.io.IOException("The saved hero's folder is not empty. Nothing was changed.");
            if(!hasOther)throw new java.io.IOException("There is no saved hero in either slot.");
            if(!other.renameTo(current))throw new java.io.IOException("The other hero could not be brought back. Nothing was changed.");
            return "The hero from the other slot is now the saved hero.";
        }
        if(!hasOther){
            if(!current.renameTo(other))throw new java.io.IOException("The saved hero could not be set aside. Nothing was changed.");
            return "The saved hero is in the other slot. Use Create fresh character for a new hero; Switch hero slot brings this one back.";
        }
        if(!current.renameTo(pending))throw new java.io.IOException("The saved hero could not be moved. Nothing was changed.");
        if(!other.renameTo(current)){
            if(!pending.renameTo(current))throw new java.io.IOException("The switch stopped half way; the saved hero is in "+pending.getName()+". Export a report.");
            throw new java.io.IOException("The other hero could not be brought back. Nothing was changed.");
        }
        if(!pending.renameTo(other))throw new java.io.IOException("The other hero is now the saved hero, but the first one stayed in "+pending.getName()+". Export a report.");
        return "Switched to the hero from the other slot.";
    }
    /** 0.13.86 (owner, 2026-11-25): the menu says what is happening in plain words. The checks a session
     *  makes ("check complete", "verified", captures) stay in the report; they are shown only with
     *  "Show test details and tools" ticked. Returns {status, detail}; an unknown status passes unchanged. */
    public static String[] plainStatus(String stage,String detail){
        String s=stage==null?"":stage,d=detail==null?"":detail;
        final String report=" A report of this session is kept under Reports / export.";
        if(s.endsWith(" check complete"))return new String[]{"Session finished","Your hero is saved."+report};
        if(s.endsWith(" check incomplete"))return new String[]{"Session finished","The game is closed and your hero's last save is kept."+report};
        if(s.endsWith(" check stopped"))return new String[]{"Session stopped","The game was stopped. Your hero's last save is kept."+report};
        if(s.endsWith(" check failed")){
            String reason=d;int cut=reason.indexOf(" check failed. ");
            if(cut>=0)reason=reason.substring(cut+" check failed. ".length());
            reason=reason.replace("Export the latest report.","").trim();
            return new String[]{"Session ended with a problem",(reason.isEmpty()?"":reason+" ")+"Your hero's last save is kept."+report};
        }
        switch(s){
            case "Starting City of Heroes":return new String[]{s,"Starting the local server and the game. This can take a minute or two."};
            case "Client window observed":return new String[]{"Game window open","The game is starting."};
            case "Client ready for input":
            case "Local server login observed":
            case "Local login verified":
            {
                // A first hero is made in the game's creator; a saved one is chosen from the game's list.
                String next=d.contains("Create your character")
                    ?"create your hero. After Enter Game the first zone can take a few minutes to load."
                    :"choose your hero and click Enter Game.";
                return new String[]{s.startsWith("Client")?"Game ready":"Logged in",s.startsWith("Client")
                    ?"Log in as COHLOCAL (offline), then "+next:Character.toUpperCase(next.charAt(0))+next.substring(1)};
            }
            case "Saved destination verified":return new String[]{"Hero found",sentence(d)};
            case "Character connected":
            case "Ready for zone travel":
            case "Atlas ready for task check":
            case "Atlas connected for startup timing":{
                String who=sentence(d).replace(" connected to "," is in ");
                if(!who.contains(" is in "))who="";
                return new String[]{"In the game",(who.isEmpty()?"":who+" ")+"Play as long as you like. When you are done, tap Save character / log out, then Finish."};
            }
            case "Destination view captured":return new String[]{"Arrived",d.replace(" · movement available","")};
            case "Saving character":
            case "Waiting for saved character":return new String[]{"Saving","Logging out and saving your hero. Keep the controls released for a moment."};
            case "Character saved":return new String[]{"Saved","Your hero is saved. One moment…"};
            case "Saved character verified":return new String[]{"Saved","Your hero is saved. Tap Finish to close the game."};
            case "Stand still before saving":return new String[]{"Time to save","Release the controls, then tap Save character / log out."};
            case "Save window expired":return new String[]{"Save did not finish","The save was not sent in time. Tap Abort operation; your hero's last save is kept."};
            case "Finishing session":return new String[]{"Closing","Closing the game and the local server."};
            case "Session ownership not verified":return new String[]{"Save not available yet","The game has not confirmed this session yet. If Save stays greyed out, log out from the game's own menu and tap Abort operation."};
            case "FPS command sent":return new String[]{"FPS setting sent",d};
            case "Returning to safe ground":return new String[]{s,"Stay still for about half a minute while the game moves your hero to safe ground."};
            case "Stable Atlas position observed":
            case "Atlas position verified":return new String[]{"On safe ground","Release the controls, then tap Save character / log out when you are ready."};
            default:return new String[]{s,d};
        }
    }
    /** The first sentence of a detail line (it names the hero and the zone). */
    private static String sentence(String text){
        int end=text.indexOf(". ");
        return end<0?text:text.substring(0,end+1);
    }
    /** The line under the status: only what the player has to act on (a time limit applies to a first hero only). */
    public static String plainTiming(boolean inputReady,boolean saved,long readyRemaining,boolean readyLimited,long saveRemaining,long moveRemaining,boolean saveLimited){
        if(!inputReady||saved)return "";
        if(saveLimited)return saveRemaining==0?"The time to save has run out.":moveRemaining==0
                ?"Stand still and save within "+saveRemaining+" s.":"Save within "+saveRemaining+" s.";
        return readyLimited?"Time left for this first session: "+readyRemaining+" s.":"";
    }
    /** maps.db static zones (ids 1-999, Atlas Park instance 2 is 101). */
    public static boolean staticZone(long map){return map>=1&&map<=999;}
    /**
     * 0.13.84 (test option): a mission map of this session. The DbServer numbers it itself; the
     * guest marks its arrival event (mission_map) and names it "Mission".
     */
    public static boolean missionMap(Map<?,?> e,long map){return yes(e,"mission_map")&&map>=1&&map<=99999;}
    private static String zoneName(Object value){
        return value instanceof String&&((String)value).matches("[A-Za-z0-9_' ]{1,48}")?(String)value:"";
    }
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
        boolean stockEvent="stock_travel".equals(e.get("travel_method"));
        if(stockEvent||stockTravel){
            boolean mission="arrived".equals(next)&&missionMap(e,mapValue);
            if(!stockEvent||!allowMonorail||!(staticZone(mapValue)||mission)||targetValue!=mapValue)return false;
            int map=(int)mapValue;
            if("enabled".equals(next)){
                if(enabled()||integer(e.get("epoch"))!=0||map!=connectedMap||!yes(e,"current_map_verified")
                        ||!yes(e,"zoning_enabled"))return false;
                stockTravel=true;monorail=false;monorailRequiresReopen=false;
                session=selectedSession;pid=selectedPid;currentMap=targetMap=map;phase="idle";
            }else if("arrived".equals(next)){
                if(!stockTravel||!selectedSession.equals(session)||pid!=selectedPid
                        ||integer(e.get("epoch"))!=epoch+1||map==currentMap||!"idle".equals(phase)
                        ||integer(e.get("from_map_id"))!=currentMap
                        ||!yes(e,"current_map_verified")||!yes(e,"character_identity_preserved"))return false;
                epoch++;currentMap=targetMap=map;
            }else return false;
            currentName=zoneName(e.get("current_map_name"));
            eventUtc=generated;lastStatus=next;return true;
        }
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
            monorailRequiresReopen=!stock&&yes(e,"monorail_requires_reopen");
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
