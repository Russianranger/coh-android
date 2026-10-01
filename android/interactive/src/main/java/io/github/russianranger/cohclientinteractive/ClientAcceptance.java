package io.github.russianranger.cohclientinteractive;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Pure acceptance checks: a decoded framebuffer alone never proves an Android display. */
final class ClientAcceptance {
    static boolean clientWindowAccepted(Object value, Object clientPid) {
        Map<?, ?> window = object(value);
        Object title = window.get("title"), width = window.get("width"), height = window.get("height");
        if (!positiveInteger(clientPid) || ((Number) clientPid).longValue() >= (1L << 32)
                || !(title instanceof String) || ((String) title).length() > 1000
                || !yes(window.get("mapped")) || !integer(width) || !integer(height)
                || ((Number) width).longValue() < 320 || ((Number) height).longValue() < 240
                || ((Number) width).longValue() > Integer.MAX_VALUE
                || ((Number) height).longValue() > Integer.MAX_VALUE) return false;
        // The same owned window keeps its Atlas title after ordinary logout.
        // Only this milestone's exact relative map path may supplement the menu
        // title; arbitrary maps, traversal and text following the PID cannot pass.
        return ((String) title).matches("City of Heroes[ \\t]+:[ \\t]+"
                + "(?:City_Zones[\\\\/]City_01_01[\\\\/]City_01_01\\.txt[ \\t]+)?PID:[ \\t]+"
                + ((Number) clientPid).longValue());
    }

    static boolean localLoginVerified(Object value, String session, long clientPid) {
        Map<?, ?> report = object(value), login = object(report.get("local_login"));
        return session != null && session.matches("[0-9a-f]{32}") && clientPid > 0
                && session.equals(login.get("session_id")) && number(login.get("client_pid"), clientPid)
                && "android-local-login".equals(login.get("profile"))
                && yes(login.get("local_login_verified")) && yes(login.get("character_list_sent"))
                && yes(login.get("local_account_verified")) && yes(login.get("character_list_response_sent"))
                && yes(login.get("database_preserved"));
    }

    static boolean characterConnectedEvent(Object value, String session, long clientPid) {
        Map<?, ?> event = object(value);
        return session != null && session.matches("[0-9a-f]{32}") && clientPid > 0
                && "character_connected".equals(event.get("type"))
                && session.equals(event.get("session_id")) && number(event.get("client_pid"), clientPid)
                && positiveInteger(event.get("character_id")) && "THORHERO".equals(event.get("name"))
                && "COHLOCAL".equals(event.get("account")) && number(event.get("map_id"), 1);
    }

    static boolean characterSavedEvent(Object value, String session, long clientPid) {
        Map<?, ?> event = object(value);
        return session != null && session.matches("[0-9a-f]{32}") && clientPid > 0
                && "character_saved".equals(event.get("type"))
                && session.equals(event.get("session_id")) && number(event.get("client_pid"), clientPid)
                && positiveInteger(event.get("character_id")) && "THORHERO".equals(event.get("name"))
                && yes(event.get("committed_sql_verified"));
    }

    static boolean characterCreationVerified(Object value, Object savedEvent, Object connectedEvent, String session, long clientPid) {
        Map<?, ?> report = object(value), character = object(report.get("character_creation")), event = object(savedEvent);
        return localLoginVerified(value, session, clientPid) && characterSavedEvent(savedEvent, session, clientPid)
                && characterConnectedEvent(connectedEvent, session, clientPid)
                && number(event.get("character_id"), ((Number) object(connectedEvent).get("character_id")).longValue())
                && yes(character.get("verified")) && session.equals(character.get("session_id"))
                && number(character.get("client_pid"), clientPid) && positiveInteger(character.get("character_id"))
                && number(character.get("character_id"), ((Number) event.get("character_id")).longValue())
                && "THORHERO".equals(character.get("name")) && "COHLOCAL".equals(character.get("account"))
                && positiveInteger(character.get("auth_id"))
                && number(object(report.get("local_login")).get("auth_id"), ((Number) character.get("auth_id")).longValue())
                && yes(character.get("connected_on_atlas")) && number(character.get("map_id"), 1)
                && yes(character.get("committed_sql_verified")) && yes(character.get("requested_logout_observed"))
                && yes(character.get("logout_timer_observed"))
                && yes(character.get("disconnected_before_sql")) && Boolean.FALSE.equals(character.get("forced_stop_before_save"));
    }

    static boolean characterCreationAccepted(Object value, Object savedEvent, Object connectedEvent,
                                               List<?> samples, String session, long clientPid,
                                               long started, long ended, long savedObserved,
                                               long windowEnded, long frameWatermark) {
        return characterCreationVerified(value, savedEvent, connectedEvent, session, clientPid)
                && surfaceAccepted(samples, session, started, ended, savedObserved, windowEnded, frameWatermark);
    }

    static boolean interactionCompleted(Object value) {
        Map<?, ?> report = object(value);
        Object reason = report.get("interaction_completion_reason");
        return yes(report.get("interaction_session_completed"))
                && Boolean.FALSE.equals(report.get("input_effect_verified"))
                && ("finish_requested".equals(reason) || "interaction_timeout".equals(reason));
    }
    static boolean cleanupSafe(Object value) {
        Map<?, ?> report = object(value), execution = object(report.get("cleanup_execution"));
        Object children = report.get("processes");
        if (!yes(report.get("cleanup_complete")) || !(children instanceof List)
                || !(execution.get("diagnostic_initialized") instanceof Boolean)
                || !(execution.get("wine_started") instanceof Boolean)
                || !number(execution.get("owned_child_count"), ((List<?>) children).size())) return false;
        for (Object item : (List<?>) children) {
            Map<?, ?> process = object(item);
            if (!integer(process.get("exit_code")) || !yes(process.get("input_closed"))
                    || !yes(process.get("output_capture_closed"))) return false;
        }
        if (Boolean.FALSE.equals(execution.get("diagnostic_initialized")))
            return ((List<?>) children).isEmpty() && Boolean.FALSE.equals(execution.get("wine_started"));
        if (!yes(object(report.get("cleanup")).get("owned_processes_reaped"))) return false;
        if (yes(report.get("postgres_started")) && !yes(object(report.get("cleanup")).get("postgres_graceful"))) return false;
        if (yes(execution.get("wine_started"))) {
            Map<?, ?> owned = object(report.get("wine_process_cleanup"));
            return yes(object(report.get("cleanup")).get("wine_prefix_stopped"))
                    && yes(owned.get("complete")) && number(owned.get("remaining"), 0)
                    && number(owned.get("inspection_failures"), 0);
        }
        return true;
    }

    static boolean surfaceAccepted(List<?> samples, String session, long started, long ended,
                                   long windowObserved, long windowEnded, long frameWatermark) {
        if (session == null || !session.matches("[0-9a-f]{32}") || started < 0 || ended < started
                || windowObserved < started || windowObserved > ended || windowEnded < windowObserved
                || windowEnded > ended || frameWatermark < 0) return false;
        Set<Long> times = new HashSet<>();
        long first = Long.MAX_VALUE, last = Long.MIN_VALUE;
        for (Object item : samples) {
            Map<?, ?> sample = object(item);
            Object captured = sample.get("captured_elapsed_ms"), sequence = sample.get("sequence");
            Object hash = sample.get("png_sha256");
            if (!session.equals(sample.get("session_id")) || !yes(sample.get("pixel_copy_success"))
                    || !yes(sample.get("non_uniform")) || !yes(sample.get("png_verified"))
                    || !integer(captured) || !integer(sequence) || ((Number) sequence).longValue() <= frameWatermark
                    || !(hash instanceof String) || !((String) hash).matches("[0-9a-f]{64}")
                    || !number(sample.get("source_width"), 800) || !number(sample.get("source_height"), 600)) continue;
            long time = ((Number) captured).longValue();
            // A static client menu may legitimately produce the same frame/hash repeatedly.
            // Each capture must use pixels received after the client-startup event watermark.
            if (time < windowObserved || time > windowEnded || !times.add(time)) continue;
            first = Math.min(first, time); last = Math.max(last, time);
        }
        return times.size() >= 3 && last - first >= 2000;
    }

    private static Map<?, ?> object(Object value) {
        return value instanceof Map ? (Map<?, ?>) value : Collections.emptyMap();
    }
    private static boolean yes(Object value) { return Boolean.TRUE.equals(value); }
    private static boolean integer(Object value) {
        return value instanceof Number && Double.isFinite(((Number) value).doubleValue())
                && ((Number) value).doubleValue() == ((Number) value).longValue();
    }
    private static boolean positiveInteger(Object value) {
        return integer(value) && ((Number) value).longValue() > 0;
    }
    private static boolean number(Object value, long expected) {
        return integer(value) && ((Number) value).longValue() == expected;
    }
    private ClientAcceptance() {}
}
