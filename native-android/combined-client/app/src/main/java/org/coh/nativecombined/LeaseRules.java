package org.coh.nativecombined;

/** Pure admission rules between the retained guest owner and native client. */
public final class LeaseRules {
    private LeaseRules(){}
    public static boolean accept(boolean alive,String expectedSession,String actualSession,
            String expectedGeneration,String actualGeneration,String address,int port,
            long nowWall,long observedWall,long fileWall,long nowElapsed){
        if(!alive||expectedSession==null||!expectedSession.matches("[0-9a-f]{32}")
            ||!expectedSession.equals(actualSession)||expectedGeneration==null
            ||!expectedGeneration.matches("generation-[0-9a-f]{32}")||!expectedGeneration.equals(actualGeneration)
            ||!"127.0.0.1".equals(address)||port!=7000||nowElapsed<0)return false;
        return fresh(nowWall,observedWall)&&fresh(nowWall,fileWall);
    }
    private static boolean fresh(long now,long then){return then>0&&now>=then&&now-then<=15000;}
}
