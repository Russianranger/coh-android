package io.github.russianranger.cohpresentation;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Pure acceptance checks: a decoded framebuffer alone never proves an Android display. */
final class PresentationAcceptance {
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
        if (yes(execution.get("wine_started"))) {
            Map<?, ?> owned = object(report.get("wine_process_cleanup"));
            return yes(object(report.get("cleanup")).get("wine_prefix_stopped"))
                    && yes(owned.get("complete")) && number(owned.get("remaining"), 0)
                    && number(owned.get("inspection_failures"), 0);
        }
        return true;
    }

    static boolean surfaceAccepted(List<?> samples, String session, long started, long ended,
                                   long producerFrameCount) {
        if (session == null || !session.matches("[0-9a-f]{32}") || started < 0 || ended < started
                || producerFrameCount < 6) return false;
        Set<Long> frames = new HashSet<>();
        long first = Long.MAX_VALUE, last = Long.MIN_VALUE;
        for (Object item : samples) {
            Map<?, ?> sample = object(item);
            Object frame = sample.get("frame_id"), captured = sample.get("captured_elapsed_ms");
            if (!session.equals(sample.get("session_id")) || !yes(sample.get("pixel_copy_success"))
                    || !yes(sample.get("matching_session")) || !integer(frame) || !integer(captured)) continue;
            long id = ((Number) frame).longValue(), time = ((Number) captured).longValue();
            // Frame IDs are emitted by this session's producer, starting at one.
            if (id < 1 || id > producerFrameCount || time < started || time > ended) continue;
            if (!frames.add(id)) continue;
            first = Math.min(first, time); last = Math.max(last, time);
        }
        return frames.size() >= 6 && last - first >= 2000;
    }

    private static Map<?, ?> object(Object value) {
        return value instanceof Map ? (Map<?, ?>) value : Collections.emptyMap();
    }
    private static boolean yes(Object value) { return Boolean.TRUE.equals(value); }
    private static boolean integer(Object value) {
        return value instanceof Number && Double.isFinite(((Number) value).doubleValue())
                && ((Number) value).doubleValue() == ((Number) value).longValue();
    }
    private static boolean number(Object value, long expected) {
        return integer(value) && ((Number) value).longValue() == expected;
    }
    private PresentationAcceptance() {}
}
