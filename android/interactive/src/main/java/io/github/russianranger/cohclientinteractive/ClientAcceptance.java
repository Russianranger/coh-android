package io.github.russianranger.cohclientinteractive;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Pure acceptance checks: a decoded framebuffer alone never proves an Android display. */
final class ClientAcceptance {
    /** Exact stage sequence selected from the APK's already verified asset pins. */
    static int clientInteractionStageIndex(Object stagesValue, Object verifiedPinsValue) {
        if (!(stagesValue instanceof List) || !(verifiedPinsValue instanceof Map)) return -1;
        Map<?, ?> pins = object(verifiedPinsValue);
        int visualInputs = 0;
        for (String name : new String[]{"client_visual_assets.py", "client_animation_package.py",
                "client-visual-assets.zip", "client-visual-manifest.json"}) {
            if (!pins.containsKey(name)) continue;
            if (!assetPin(pins.get(name))) return -1;
            visualInputs++;
        }
        if (visualInputs != 0 && visualInputs != 4) return -1;
        boolean visual = visualInputs == 4;
        if (visual && (!assetPin(pins.get("server-animations.pigg"))
                || !assetPin(pins.get("server-animation-manifest.json")))) return -1;
        String[] before = {"client_inputs", "client_private_data", "persistent_server_profile", "postgres_local_login",
                "presentation_display", "wine_initialization", "local_login_odbc", "local_dbserver_startup",
                "local_atlas_startup"};
        String[] after = {"win32_runtime_dll", "actual_client_startup", "actual_client_interaction"};
        List<?> stages = (List<?>) stagesValue;
        if (stages.size() != before.length + after.length + (visual ? 2 : 0)) return -1;
        int index = 0;
        for (String name : before) if (!passedStage(stages.get(index++), name)) return -1;
        if (visual && (!passedStage(stages.get(index++), "client_visual_assets")
                || !passedStage(stages.get(index++), "client_animation_pack"))) return -1;
        for (String name : after) if (!passedStage(stages.get(index++), name)) return -1;
        return stages.size() - 1;
    }

    private static boolean assetPin(Object value) {
        Map<?, ?> pin = object(value);
        Object hash = pin.get("sha256");
        return positiveInteger(pin.get("bytes")) && hash instanceof String
                && ((String) hash).matches("[0-9a-f]{64}");
    }

    private static boolean passedStage(Object value, String name) {
        Map<?, ?> stage = object(value);
        return name.equals(stage.get("stage")) && "passed".equals(stage.get("status"));
    }

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
        return characterPersistenceVerified(value, savedEvent, connectedEvent, session, clientPid, "character_creation");
    }

    private static boolean characterPersistenceVerified(Object value, Object savedEvent, Object connectedEvent, String session, long clientPid, String key) {
        Map<?, ?> report = object(value), character = object(report.get(key)), event = object(savedEvent);
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

    static boolean characterReopenConnectedEvent(Object value, String session, long clientPid) {
        Map<?, ?> event = object(value);
        return characterConnectedEvent(value, session, clientPid)
                && number(event.get("character_id"), 1) && number(event.get("baseline_character_id"), 1)
                && yes(event.get("reopen_verified")) && yes(event.get("existing_character_verified"));
    }

    static boolean characterRelocatedEvent(Object value, String session, long clientPid) {
        Map<?, ?> event = object(value);
        return session != null && session.matches("[0-9a-f]{32}") && clientPid > 0
                && "character_relocated".equals(event.get("type"))
                && session.equals(event.get("session_id")) && number(event.get("client_pid"), clientPid)
                && number(event.get("character_id"), 1) && "THORHERO".equals(event.get("name"))
                && "COHLOCAL".equals(event.get("account")) && number(event.get("map_id"), 1)
                && yes(event.get("recovery_requested")) && yes(event.get("recovery_verified"))
                && yes(event.get("ordinary_stuck_observed")) && yes(event.get("on_atlas_safe_position"))
                && yes(event.get("stable_ground_verified"));
    }

    static boolean characterReopenVerified(Object value, Object savedEvent, Object connectedEvent,
                                           String session, long clientPid) {
        Map<?, ?> reopen = object(object(value).get("character_reopen"));
        return characterPersistenceVerified(value, savedEvent, connectedEvent, session, clientPid, "character_reopen")
                && characterReopenConnectedEvent(connectedEvent, session, clientPid)
                && yes(reopen.get("reopen_verified")) && yes(reopen.get("existing_character_verified"))
                && yes(reopen.get("preserved_existing_identity")) && yes(reopen.get("native_client_ready_observed"))
                && yes(reopen.get("powers_preserved")) && yes(reopen.get("costume_preserved"))
                && yes(reopen.get("selected_rows_preserved")) && yes(reopen.get("committed_native_position_verified"))
                && optionalRecoveryVerified(reopen)
                && number(reopen.get("before_character_id"), 1) && number(reopen.get("baseline_character_id"), 1)
                && number(reopen.get("character_id"), 1);
    }

    private static boolean optionalRecoveryVerified(Map<?, ?> reopen) {
        if (Boolean.FALSE.equals(reopen.get("recovery_requested")))
            return Boolean.FALSE.equals(reopen.get("recovery_verified"))
                    && Boolean.FALSE.equals(reopen.get("ordinary_stuck_observed"))
                    && Boolean.FALSE.equals(reopen.get("on_atlas_safe_position"))
                    && Boolean.FALSE.equals(reopen.get("stable_ground_verified"))
                    && Boolean.FALSE.equals(reopen.get("committed_safe_position_verified"));
        return yes(reopen.get("recovery_requested")) && yes(reopen.get("recovery_verified"))
                && yes(reopen.get("ordinary_stuck_observed")) && yes(reopen.get("on_atlas_safe_position"))
                && yes(reopen.get("stable_ground_verified")) && yes(reopen.get("committed_safe_position_verified"));
    }

    static boolean characterReopenAccepted(Object value, Object savedEvent, Object connectedEvent,
                                           Object relocatedEvent, List<?> connectedSamples, List<?> relocationSamples, List<?> savedSamples, String session, long clientPid,
                                           long started, long ended, long connectedObserved, long connectedFrameWatermark,
                                           long relocatedObserved, long relocatedFrameWatermark,
                                           long savedObserved, long windowEnded, long savedFrameWatermark) {
        if (!characterReopenVerified(value, savedEvent, connectedEvent, session, clientPid)
                || connectedObserved < started || savedObserved < connectedObserved
                || !surfaceAccepted(savedSamples, session, started, ended, savedObserved, windowEnded, savedFrameWatermark)) return false;
        boolean requested = yes(object(object(value).get("character_reopen")).get("recovery_requested"));
        if (!requested)
            return surfaceAccepted(connectedSamples, session, started, ended, connectedObserved,
                    savedObserved, connectedFrameWatermark);
        return characterRelocatedEvent(relocatedEvent, session, clientPid)
                && relocatedObserved >= connectedObserved && savedObserved >= relocatedObserved
                && surfaceAccepted(connectedSamples, session, started, ended, connectedObserved, relocatedObserved, connectedFrameWatermark)
                && surfaceAccepted(relocationSamples, session, started, ended, relocatedObserved, savedObserved, relocatedFrameWatermark);
    }

    static boolean interactionCompleted(Object value) {
        Map<?, ?> report = object(value);
        Object reason = report.get("interaction_completion_reason");
        return yes(report.get("interaction_session_completed"))
                && Boolean.FALSE.equals(report.get("input_effect_verified"))
                && ("finish_requested".equals(reason) || "interaction_timeout".equals(reason));
    }

    /** Reopen may grant a new 20 minute window only after an owned native connection. */
    static boolean clientObservationAccepted(Object value, List<?> acceptedBudgets, String session,
            long clientPid, long windowStarted, long windowEnded, long budgetDeadline,
            long launcherStarted, long operationStarted) {
        Map<?, ?> report = object(value);
        Object seconds = report.get("observation_seconds");
        if (!(seconds instanceof Number)) return false;
        double observed = ((Number) seconds).doubleValue();
        if (!Double.isFinite(observed) || observed < 30) return false;
        if (acceptedBudgets == null || acceptedBudgets.isEmpty()) return observed <= 1210;
        Object rows = report.get("character_session_budgets");
        if (!(rows instanceof List) || ((List<?>) rows).size() != acceptedBudgets.size()
                || acceptedBudgets.size() > 2 || !number(report.get("interaction_timeout_seconds"), 1200)
                || session == null || !session.matches("[0-9a-f]{32}") || clientPid <= 0
                || operationStarted < 0 || launcherStarted < operationStarted || windowStarted < launcherStarted
                || windowEnded < windowStarted || budgetDeadline <= windowStarted
                || budgetDeadline - operationStarted > 5400000 || budgetDeadline - launcherStarted > 2100000
                || windowEnded - budgetDeadline > 10000
                || observed > (budgetDeadline - windowStarted) / 1000.0 + 10
                || observed > (windowEnded - windowStarted) / 1000.0 + 10) return false;
        // These events were accepted by ClientSessionBudget.apply during this
        // operation, after the current character-connected/relocated event.
        // A guest report alone cannot extend the old menu observation bound.
        String[] integers = {"format", "client_pid", "character_id", "map_id", "revision",
                "generated_utc_ms", "deadline_utc_ms", "save_request_deadline_utc_ms", "movement_deadline_utc_ms"};
        for (int i = 0; i < acceptedBudgets.size(); i++) {
            Map<?, ?> accepted = object(acceptedBudgets.get(i)), row = object(((List<?>) rows).get(i));
            if (!"character_session_budget".equals(accepted.get("type"))
                    || !session.equals(row.get("session_id")) || !number(row.get("client_pid"), clientPid)
                    || !number(row.get("format"), 1) || !number(row.get("character_id"), 1)
                    || !number(row.get("map_id"), 1) || !number(row.get("revision"), i + 1)
                    || !"THORHERO".equals(row.get("name")) || !"COHLOCAL".equals(row.get("account"))
                    || !(i == 0 ? "connected" : "grounded").equals(row.get("phase"))) return false;
            for (String name : integers) {
                Object reported = row.get(name), approved = accepted.get(name);
                if (!(reported instanceof Integer || reported instanceof Long)
                        || !(approved instanceof Integer || approved instanceof Long)
                        || ((Number) reported).longValue() != ((Number) approved).longValue()) return false;
            }
            for (String name : new String[]{"session_id", "name", "account", "phase"})
                if (!row.get(name).equals(accepted.get(name))) return false;
            for (String name : new String[]{"native_client_ready_observed", "reopen_verified"})
                if (!yes(row.get(name)) || !yes(accepted.get(name))) return false;
            if (i == 1)
                for (String name : new String[]{"ordinary_stuck_observed", "stable_ground_verified",
                        "recovery_requested", "recovery_verified"})
                    if (!yes(row.get(name)) || !yes(accepted.get(name))) return false;
        }
        return true;
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

    static boolean taskIdentity(Object value) {
        Map<?, ?> task = object(value);
        Object name = task.get("name"), context = task.get("context"), subhandle = task.get("subhandle");
        return name instanceof String && ((String) name).matches("[ -~]{1,256}")
                && integer(context) && ((Number) context).longValue() != 0
                && ((Number) context).longValue() >= Integer.MIN_VALUE && ((Number) context).longValue() <= Integer.MAX_VALUE
                && integer(subhandle) && ((Number) subhandle).longValue() >= 0
                && ((Number) subhandle).longValue() <= Integer.MAX_VALUE && number(task.get("task_index"), 0);
    }

    static boolean sameTaskIdentity(Object first, Object second) {
        Map<?, ?> a = object(first), b = object(second);
        return taskIdentity(a) && taskIdentity(b) && a.get("name").equals(b.get("name"))
                && number(b.get("context"), ((Number) a.get("context")).longValue())
                && number(b.get("subhandle"), ((Number) a.get("subhandle")).longValue());
    }

    static boolean taskEvent(Object value, String type, String session, long clientPid) {
        Map<?, ?> event = object(value);
        return ("character_task_accepted".equals(type) || "character_task_completed".equals(type))
                && session != null && session.matches("[0-9a-f]{32}") && clientPid > 0 && clientPid <= 4294967295L
                && type.equals(event.get("type")) && session.equals(event.get("session_id"))
                && number(event.get("client_pid"), clientPid) && number(event.get("character_id"), 1)
                && number(event.get("active_task_count"), 1)
                && yes(event.get("native_task_verified")) && yes(event.get("sql_task_verified"))
                && positiveInteger(event.get("observed_utc_ms")) && taskIdentity(event.get("task"));
    }

    static boolean taskSaveReady(Object accepted, Object completed, int acceptedViews, int completedViews,
                                 String session, long clientPid) {
        return acceptedViews == 3 && completedViews == 3
                && taskEvent(accepted, "character_task_accepted", session, clientPid)
                && taskEvent(completed, "character_task_completed", session, clientPid)
                && sameTaskIdentity(object(accepted).get("task"), object(completed).get("task"));
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
