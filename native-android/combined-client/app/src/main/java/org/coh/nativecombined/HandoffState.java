package org.coh.nativecombined;

/** Bounded per-attempt control observations. JSON size never controls an owner.
 * No packet, identity, permission or world-authority state is admitted here. */
final class HandoffState {
    static final int OWNER_PRESENT=1, TERMINAL=2, INITIAL_OBSERVED=4, CHARACTERS_READY=8;
    private boolean ownerPresent, controlKnown, terminal, initialKnown, initialObserved, charactersReady;
    private String lastPhase="UNKNOWN";
    private long[] firstFailure;

    synchronized void begin() {
        ownerPresent=true;controlKnown=false;terminal=false;initialKnown=false;
        initialObserved=false;charactersReady=false;lastPhase="UNKNOWN";firstFailure=null;
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
    synchronized long[] firstFailure() {return firstFailure==null?null:firstFailure.clone();}
}
