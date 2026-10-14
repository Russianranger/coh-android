package org.coh.integrationprobe;

import org.json.JSONArray;
import org.json.JSONObject;

/** Fail-closed receipt checks shared by the screen and executed host tests. */
final class ReceiptRules {
    private ReceiptRules() { }
    static boolean bool(JSONObject o, String key, boolean wanted) {
        return o != null && o.opt(key) instanceof Boolean && o.optBoolean(key) == wanted;
    }
    static boolean integer(JSONObject o, String key, long wanted) {
        Object value = o == null ? null : o.opt(key);
        return value instanceof Number && ((Number)value).doubleValue() == wanted;
    }
    static boolean positive(JSONObject o, String key) {
        Object value = o == null ? null : o.opt(key);
        return value instanceof Number && Double.isFinite(((Number)value).doubleValue())
            && ((Number)value).doubleValue() > 0 && ((Number)value).doubleValue() == ((Number)value).longValue();
    }
    static boolean zeroInput(JSONObject o) {
        JSONArray axes = o == null ? null : o.optJSONArray("axes");
        if (axes == null || axes.length() != 4) return false;
        for (int i = 0; i < 4; ++i) if (axes.optDouble(i, Double.NaN) != 0) return false;
        return integer(o,"result",1) && integer(o,"held",0) && integer(o,"pressed",0)
            && integer(o,"released",0) && integer(o,"delta_x",0) && integer(o,"delta_y",0);
    }
    static boolean decodePassed(JSONObject decode) {
        return bool(decode,"passed",true) && integer(decode,"result",0)
            && bool(decode,"reference_compared",true) && bool(decode,"reference_passed",true)
            && bool(decode,"opened",true) && bool(decode,"cleared",true) && bool(decode,"eos",true)
            && integer(decode,"streams",1) && integer(decode,"sample_rate",44100)
            && integer(decode,"channels",2) && integer(decode,"frames",18168)
            && integer(decode,"pcm_bytes",72672) && positive(decode,"ov_read_calls")
            && positive(decode,"compared_samples") && integer(decode,"failed",0)
            && decode.opt("maximum_sample_error") instanceof Number
            && decode.optDouble("maximum_sample_error",Double.NaN)>=0
            && decode.optDouble("maximum_sample_error",Double.NaN)<=1;
    }
    static boolean audioRunFailed(JSONObject run) {
        if (!decodePassed(run == null ? null : run.optJSONObject("decode"))
            || !integer(run,"backend_errors",0)
            || !(run.opt("passed") instanceof Boolean) || !(run.opt("cancelled") instanceof Boolean)
            || !(run.opt("result") instanceof Number)) return true;
        boolean complete = bool(run,"passed",true) && bool(run,"cancelled",false) && integer(run,"result",0)
            && bool(run,"decoded_audio_played",true);
        boolean cancellation = bool(run,"passed",false) && bool(run,"cancelled",true) && integer(run,"result",1);
        boolean late = bool(run,"passed",false) && bool(run,"cancelled",true) && integer(run,"result",0)
            && bool(run,"decoded_audio_played",true) && integer(run,"completed_clips",3) && integer(run,"requested_clips",3)
            && bool(run,"opened",true) && bool(run,"started",true) && bool(run,"stopped",true) && bool(run,"closed",true);
        return !(complete || cancellation || late);
    }
    static boolean audioInterrupted(JSONObject run, long id, long pause) {
        return !audioRunFailed(run) && integer(run,"run_id",id) && integer(run,"result",1)
            && bool(run,"cancelled",true) && bool(run,"opened",true) && bool(run,"started",true)
            && bool(run,"stopped",true) && bool(run,"closed",true) && positive(run,"submitted_frames")
            && run.optLong("started_after_event",Long.MAX_VALUE)<pause;
    }
    static boolean transportRunFailed(JSONObject run) {
        if (run == null || run.has("session_failure") && !bool(run,"session_failure",false)
            || !integer(run,"backend_errors",0) || !bool(run,"opened",true)
            || !bool(run,"closed",true) || !positive(run,"sockets_opened")
            || !integer(run,"sockets_closed",run.optLong("sockets_opened"))
            || !(run.opt("passed") instanceof Boolean) || !(run.opt("cancelled") instanceof Boolean)
            || !(run.opt("result") instanceof Number)) return true;
        boolean clean = bool(run,"passed",true) && bool(run,"cancelled",false) && integer(run,"result",0);
        boolean interrupted = bool(run,"passed",true) && bool(run,"cancelled",true)
            && integer(run,"result",0) && positive(run,"blocked_polls") && integer(run,"interrupted_blocked_poll",1);
        // A bounded empty wait that expires cleanly is retryable, never Home proof.
        boolean timeout = bool(run,"passed",false) && bool(run,"cancelled",false)
            && positive(run,"timeouts") && integer(run,"result",1);
        boolean earlyCancel = bool(run,"passed",false) && bool(run,"cancelled",false)
            && integer(run,"result",1) && integer(run,"blocked_polls",0)
            && integer(run,"timeouts",0) && integer(run,"interrupted_blocked_poll",0);
        return !(clean || interrupted || timeout || earlyCancel);
    }
    static boolean nativeCorePassed(JSONObject run) {
        JSONObject input=run==null?null:run.optJSONObject("input_source");
        return decodePassed(run==null?null:run.optJSONObject("decode")) && bool(input,"passed",true)
            && integer(input,"result",1) && integer(input,"failed",0) && positive(input,"checks");
    }
    static boolean nativeCheckPassed(JSONObject run) {
        JSONObject transport=run==null?null:run.optJSONObject("transport");
        return bool(run,"passed",true) && nativeCorePassed(run) && !transportRunFailed(transport)
            && bool(transport,"passed",true) && bool(transport,"cancelled",false)
            && positive(transport,"datagrams_sent") && positive(transport,"datagrams_received")
            && positive(transport,"clear_frames") && positive(transport,"encrypted_frames")
            && positive(transport,"expected_rejects") && positive(transport,"byte_parity_checks")
            && positive(transport,"decoded_payloads");
    }
    static boolean nativeCheckFailed(JSONObject run,boolean staleForeground) {
        if(nativeCheckPassed(run))return false;
        JSONObject transport=run==null?null:run.optJSONObject("transport");
        boolean noOwnedSockets=integer(transport,"sockets_opened",0)&&integer(transport,"sockets_closed",0);
        boolean releasedSockets=positive(transport,"sockets_opened")
            && integer(transport,"sockets_closed",transport.optLong("sockets_opened"))&&bool(transport,"closed",true);
        boolean expected=staleForeground&&nativeCorePassed(run)&&bool(run,"passed",false)
            && bool(transport,"expected_cancel",true)&&bool(transport,"session_failure",false)
            && bool(transport,"cancelled",true)
            && bool(transport,"passed",false)&&integer(transport,"result",1)
            && integer(transport,"backend_errors",0)&&(noOwnedSockets||releasedSockets);
        return !expected;
    }
    static boolean transportInterrupted(JSONObject run, long id, long pause) {
        return !transportRunFailed(run) && integer(run,"run_id",id)
            && bool(run,"cancelled",true) && integer(run,"interrupted_blocked_poll",1)
            && positive(run,"blocked_polls") && run.optLong("started_after_event",Long.MAX_VALUE)<pause;
    }
    static boolean worldEnginePassed(JSONObject run) {
        return bool(run,"java_obsolete",false) && bool(run,"session_failure",false)
            && bool(run,"engine_passed",true) && bool(run,"fixtures_valid",true)
            && bool(run,"baseline_cpu_passed",true) && bool(run,"baseline_gpu_passed",true)
            && bool(run,"context_created",true) && bool(run,"objects_released",true)
            && bool(run,"cancelled",false) && integer(run,"gl_errors",0)
            && integer(run,"source_frames_consumed",180) && integer(run,"frames",180)
            && integer(run,"stationary_mismatches",0) && integer(run,"camera_determinism_mismatches",0)
            && integer(run,"same_camera_image_mismatches",0) && integer(run,"interactive_transform_mismatches",0);
    }
    static boolean worldCurrentPassed(JSONObject run,long generation,int width,int height,long token) {
        return worldEnginePassed(run) && integer(run,"generation",generation)
            && integer(run,"width",width) && integer(run,"height",height)
            && integer(run,"render_token",token) && bool(run,"foreground_at_completion",true);
    }
    static boolean worldObsoleteHarmless(JSONObject run,boolean obsolete) {
        return obsolete && bool(run,"session_failure",false) && bool(run,"objects_released",true)
            && integer(run,"gl_errors",0)
            && (!run.has("stationary_mismatches") || integer(run,"stationary_mismatches",0))
            && (!run.has("camera_determinism_mismatches") || integer(run,"camera_determinism_mismatches",0))
            && (!run.has("same_camera_image_mismatches") || integer(run,"same_camera_image_mismatches",0))
            && (!run.has("interactive_transform_mismatches") || integer(run,"interactive_transform_mismatches",0))
            && (bool(run,"engine_passed",true)
                || bool(run,"cancelled",true) && bool(run,"expected_cancel",true));
    }
}
