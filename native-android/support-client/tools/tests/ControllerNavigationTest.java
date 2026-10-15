package org.coh.sessionclient;
public final class ControllerNavigationTest {
    static final class Probe implements SupportControllerNavigation.Sink {
        int clears,updates;float x,y;
        public void axes(float x,float y) {this.x=x;this.y=y;updates++;}
        public void clear() {x=y=0;clears++;}
    }
    static int checks;
    static void check(boolean value) {checks++;if(!value)throw new AssertionError("check "+checks);}
    public static void main(String[] ignored) {
        Probe p=new Probe();SupportControllerNavigation n=new SupportControllerNavigation(p);
        n.motion(41,0,0,0,-1);check(p.y==-1&&p.x==0);check(p.clears==1);
        n.motion(41,0,0,0,0);check(p.y==0&&p.x==0);check(p.clears==1);
        n.motion(41,.7f,0,0,-1);check(p.x==.7f&&p.y==0);
        n.motion(41,.4f,0,0,-1);check(p.x==.4f&&p.y==0);
        n.motion(41,.1f,0,0,-1);check(p.x==0&&p.y==-1);
        // Device first used entirely in UI mode still owns its held axes.
        n.deviceChanged(42);check(p.y==-1);
        n.deviceChanged(41);check(p.x==0&&p.y==0);check(p.clears==2);
        n.motion(42,-1,0,0,0);check(p.x==-1);check(p.clears==3);
        n.select(43);check(p.x==0&&p.y==0);check(p.clears==4);
        n.motion(43,0,0,3,-2);check(p.x==1&&p.y==-1);
        n.motion(43,Float.NaN,0,0,0);check(p.x==0&&p.y==0);check(p.clears==5);
        n.motion(-1,1,0,0,0);check(p.x==1);n.clear();check(p.x==0&&p.y==0);
        System.out.println("{\"passed\":true,\"checks\":"+checks+",\"scope\":\"real pure-Java UI controller/HAT ownership policy; no Android input injection\"}");
    }
}
