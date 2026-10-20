package org.coh.nativecombined;

/** Bounded per-attempt control observations. JSON size never controls an owner.
 * No packet, identity, permission or world-authority state is admitted here. */
final class HandoffState {
    static final int OWNER_PRESENT=1, TERMINAL=2, INITIAL_OBSERVED=4, CHARACTERS_READY=8;
    private boolean ownerPresent, controlKnown, terminal, initialKnown, initialObserved, charactersReady;
    private String lastPhase="UNKNOWN";
    private long[] firstFailure;
    private long[] catalogBoundary;

    synchronized void begin() {
        ownerPresent=true;controlKnown=false;terminal=false;initialKnown=false;
        initialObserved=false;charactersReady=false;lastPhase="UNKNOWN";firstFailure=null;catalogBoundary=null;
    }
    synchronized void control(int value) {
        if((value&OWNER_PRESENT)==0) {
            // A missing/busy/partial observation cannot retire a Java-owned token.
            controlKnown=false;initialKnown=initialObserved;charactersReady=false;return;
        }
        ownerPresent=true;controlKnown=true;initialKnown=true;
        initialObserved|=(value&INITIAL_OBSERVED)!=0;
        terminal|=(value&TERMINAL)!=0||initialObserved;
        charactersReady=!terminal&&(value&CHARACTERS_READY)!=0;
    }
    synchronized void stopped() {terminal=true;charactersReady=false;}
    synchronized void retired() {ownerPresent=false;controlKnown=true;terminal=true;charactersReady=false;}
    synchronized void phase(String phase) {
        if(phase==null||phase.length()>32||"REPORT_LIMIT".equals(phase)
                ||"REPORT_UNAVAILABLE".equals(phase)||"UNKNOWN".equals(phase)||phase.isEmpty())return;
        lastPhase=phase;
        if("INITIAL_OBSERVED".equals(phase)) {
            initialKnown=true;initialObserved=true;terminal=true;charactersReady=false;
        }
    }
    synchronized void initial(boolean observed) {
        initialKnown=true;initialObserved|=observed;
        if(initialObserved){terminal=true;charactersReady=false;}
    }
    synchronized Boolean initialObserved() {return initialObserved?Boolean.TRUE:initialKnown?Boolean.FALSE:null;}
    synchronized boolean shouldService() {return ownerPresent&&controlKnown&&!terminal;}
    synchronized boolean blocksNewAttempt() {return ownerPresent&&!terminal;}
    synchronized boolean charactersReady() {return ownerPresent&&controlKnown&&charactersReady&&!terminal;}
    synchronized boolean ownerPresent() {return ownerPresent;}
    synchronized boolean terminal() {return terminal;}
    synchronized boolean controlKnown() {return controlKnown;}
    synchronized String lastPhase() {return lastPhase;}
    synchronized void firstFailure(long local,long db,long map,long status,long failure) {
        if(firstFailure==null)firstFailure=new long[]{local,db,map,status,failure};
    }
    /** Numeric diagnostic only: never supplies a count or admits a dictionary. */
    synchronized void catalogBoundary(long[] value,boolean observed) {
        if(catalogBoundary!=null||!observed||value==null||value.length!=7)return;
        for(long scalar:value)if(scalar<0)return;
        if(value[0]!=2||(value[1]!=41&&value[1]!=43)||value[2]>256||value[3]>256
                ||value[4]>33554432L||value[5]>33554432L-value[4]||value[6]>0x1fffffffL)return;
        long metadata=value[6], count=(metadata>>21)&31, width=(metadata>>26)&7;
        boolean compressed=(metadata&(1L<<18))!=0;
        if(value[5]<(compressed?3272:3265)||(metadata&63)>54
                ||(compressed&&((metadata>>19)&3)!=0))return;
        if(value[1]==41?(count!=0||width!=0):(count>30||width==0||width>5
                ||(compressed?width!=5:width!=(count<15?1:2))))return;
        catalogBoundary=value.clone();
    }
    synchronized long[] catalogBoundary() {return catalogBoundary==null?null:catalogBoundary.clone();}
    synchronized String catalogDetail() {
        return catalogBoundary==null?null:catalogBoundary[1]==41
                ?"Initial update observed; costume stopped at stage 41. The current MapServer BodyPart catalog and generation are required for its default part count."
                :"Initial update observed; costume stopped at stage 43. Its explicit part count still requires the current MapServer BodyPart catalog and generation.";
    }
    synchronized long[] firstFailure() {return firstFailure==null?null:firstFailure.clone();}
}
