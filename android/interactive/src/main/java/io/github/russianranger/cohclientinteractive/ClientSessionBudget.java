package io.github.russianranger.cohclientinteractive;

import java.util.Map;

/** One-way deadlines for the current native character, never a gameplay proof. */
public final class ClientSessionBudget {
    private int revision;
    private long deadline, saveDeadline, movementDeadline;
    public synchronized int revision() { return revision; }
    public synchronized String phase() { return revision == 2 ? "grounded" : revision == 1 ? "connected" : "menu"; }
    public synchronized long deadline() { return deadline; }
    public synchronized long saveDeadline() { return saveDeadline; }
    public synchronized long movementDeadline() { return movementDeadline; }
    public synchronized boolean canMove(long now) { return revision == 2 && now < movementDeadline; }
    public synchronized boolean canSave(long now) { return revision == 2 && now < saveDeadline; }

    private static long integer(Object value) {
        return value instanceof Integer || value instanceof Long ? ((Number)value).longValue() : -1;
    }
    public synchronized boolean apply(Map<String,Object> event, String session, long pid,
            boolean connected, boolean grounded, long relocationSentUtc,
            long wallNow, long uptimeNow, long hardCapUptime) {
        if (event == null || session == null || !session.matches("[0-9a-f]{32}") || pid <= 0
                || wallNow <= 0 || wallNow > Long.MAX_VALUE - 1201000
                || uptimeNow < 0 || uptimeNow > Long.MAX_VALUE - 1201000 || hardCapUptime <= uptimeNow
                || !"character_session_budget".equals(event.get("type"))
                || integer(event.get("format")) != 1 || !session.equals(event.get("session_id"))
                || integer(event.get("client_pid")) != pid || integer(event.get("character_id")) != 1
                || !"THORHERO".equals(event.get("name")) || !"COHLOCAL".equals(event.get("account"))
                || integer(event.get("map_id")) != 1 || !connected
                || !Boolean.TRUE.equals(event.get("native_client_ready_observed"))
                || !Boolean.TRUE.equals(event.get("reopen_verified"))) return false;
        long next = integer(event.get("revision")), generated = integer(event.get("generated_utc_ms"));
        long end = integer(event.get("deadline_utc_ms")), save = integer(event.get("save_request_deadline_utc_ms"));
        long movement = integer(event.get("movement_deadline_utc_ms"));
        if (next != revision + 1 || next > 2 || generated <= 0 || generated > wallNow + 1000
                || wallNow - generated > 120000 || end <= wallNow || end - generated > 1200000
                || end - wallNow > hardCapUptime - uptimeNow) return false;
        if (next == 1) {
            if (!"connected".equals(event.get("phase")) || save != 0 || movement != 0) return false;
        } else {
            if (!"grounded".equals(event.get("phase")) || !grounded || deadline <= uptimeNow || relocationSentUtc <= 0
                    || relocationSentUtc > wallNow + 1000 || wallNow - relocationSentUtc > 600000
                    || !Boolean.TRUE.equals(event.get("ordinary_stuck_observed"))
                    || !Boolean.TRUE.equals(event.get("stable_ground_verified"))
                    || save <= wallNow || movement <= generated || movement != save - 60000
                    || save > relocationSentUtc + 420000 || end > relocationSentUtc + 600000
                    || end - save != 180000) return false;
        }
        deadline = uptimeNow + end - wallNow;
        saveDeadline = save == 0 ? 0 : uptimeNow + save - wallNow;
        movementDeadline = movement == 0 ? 0 : uptimeNow + movement - wallNow;
        revision = (int)next;
        return true;
    }
}
