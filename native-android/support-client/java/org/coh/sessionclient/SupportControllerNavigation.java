package org.coh.sessionclient;

/** Pure local input ownership policy, shared by Android routing and host tests. */
final class SupportControllerNavigation {
    interface Sink { void axes(float x,float y); void clear(); }
    private static final int NONE=Integer.MIN_VALUE;
    private final Sink sink;
    private int selected=NONE;
    private long motions,hatSamples,clears;
    SupportControllerNavigation(Sink sink) { this.sink=sink; }
    void select(int device) {
        if(selected!=device) { sink.clear();selected=device; }
    }
    void motion(int device,float x,float y,float hatX,float hatY) {
        if(!Float.isFinite(x)||!Float.isFinite(y)||!Float.isFinite(hatX)||!Float.isFinite(hatY)) { clear();return; }
        select(device);motions++;
        // Keep an engaged stick through its release hysteresis; otherwise use HAT.
        if(Math.max(Math.abs(x),Math.abs(y))<.35f) { x=hatX;y=hatY;if(Math.max(Math.abs(x),Math.abs(y))>=.55f)hatSamples++; }
        sink.axes(Math.max(-1,Math.min(1,x)),Math.max(-1,Math.min(1,y)));
    }
    void deviceChanged(int device) { if(selected==device)clear(); }
    int selectedDevice() { return selected; }
    long motionSamples() { return motions; }
    long hatSamples() { return hatSamples; }
    long clears() { return clears; }
    void clear() { selected=NONE;clears++;sink.clear(); }
}
