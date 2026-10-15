package io.github.russianranger.cohdiagnostic;

import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/** Checks the device-only receipt without treating guest platform flags as attestation. */
final class DbServerAcceptance {
    private static final String LOOPBACK_ACK = "COH_WINE_DB_LOOPBACK_ONLY=1 active: IPv4 listener binds restricted to loopback; endpoint verification required";
    private static final String FIXED_ACK = "COH_WINE_DB_FIXED_INPUTS=1 active: directory monitoring disabled; initial reads and lookup mode preserved";
    private static final String[] MODES = {"initial", "fail", "exhaust", "delete-fail", "disconnect",
            "verify", "verify", "verify", "rebuild", "verify-rebuilt", "rebuild-fail",
            "rebuild-fail-view", "verify-rebuilt", "verify-rebuilt"};

    static boolean accepts(Object value, Object listenerContract) {
        Object sourceEndpoints = object(listenerContract).get("endpoints");
        if (!(sourceEndpoints instanceof List) || ((List<?>)sourceEndpoints).size() != 14) return false;
        Set<String> requiredEndpoints = new HashSet<>(), allowedEndpoints = new HashSet<>();
        for (Object raw : (List<?>)sourceEndpoints) {
            Map<?, ?> endpoint = object(raw);
            String key = endpointKey(endpoint);
            Object required = endpoint.get("required_before_export");
            if (key == null || !(required instanceof Boolean) || !allowedEndpoints.add(key)) return false;
            if (yes(required)) requiredEndpoints.add(key);
        }
        if (requiredEndpoints.size() != 13) return false;
        Map<?, ?> report = object(value);
        if (!"dbserver_persistence_and_generated_schema".equals(report.get("diagnostic_mode"))
                || !"android".equals(report.get("execution_platform_requested"))
                || !"device".equals(report.get("listener_policy"))
                || !"passed".equals(report.get("status")) || !yes(report.get("passed"))
                || !empty(report.get("failures")) || !yes(report.get("cleanup_complete"))) return false;
        for (String key : new String[]{"android_execution_validated", "android_listener_binding_validated",
                "gameplay_validated", "generated_character_persistence_validated"})
            if (!Boolean.FALSE.equals(report.get(key))) return false;
        Map<?, ?> cleanup = object(report.get("cleanup"));
        for (String key : new String[]{"postgres_graceful", "wine_prefix_stopped", "owned_processes_reaped"})
            if (!yes(cleanup.get(key))) return false;
        Map<?, ?> fixture = object(report.get("fixture"));
        if (!"passed".equals(fixture.get("status")) || !number(fixture.get("check_count"), 21)
                || !size(fixture.get("checks"), 21) || !size(fixture.get("phases"), MODES.length)) return false;
        List<?> phases = (List<?>) fixture.get("phases");
        for (int i = 0; i < MODES.length; i++) {
            Map<?, ?> phase = object(phases.get(i));
            int exit = i >= 1 && i <= 4 ? 3 : i == 10 || i == 11 ? 2 : 0;
            if (!MODES[i].equals(phase.get("mode")) || !number(phase.get("exit_code"), exit)
                    || !loopback(phase.get("loopback_only"), Collections.emptySet(), Collections.emptySet())) return false;
        }
        Map<?, ?> schema = object(report.get("generated_schema"));
        if (!"passed".equals(schema.get("status")) || !yes(schema.get("reload_stable"))
                || !Boolean.FALSE.equals(schema.get("fixture_enabled")) || !size(schema.get("phases"), 2)) return false;
        phases = (List<?>) schema.get("phases");
        for (int i = 0; i < 2; i++) {
            Map<?, ?> phase = object(phases.get(i));
            Map<?, ?> fixed = object(phase.get("fixed_inputs"));
            if (!number(phase.get("number"), i + 1) || !number(phase.get("exit_code"), 0)
                    || !empty(phase.get("failure_diagnostic_lines"))
                    || !loopback(phase.get("loopback_only"), requiredEndpoints, allowedEndpoints)
                    || !yes(fixed.get("requested")) || !FIXED_ACK.equals(fixed.get("startup_acknowledgement"))) return false;
        }
        return true;
    }

    private static boolean loopback(Object value, Set<String> required, Set<String> allowed) {
        Map<?, ?> evidence = object(value);
        if (!yes(evidence.get("requested")) || !LOOPBACK_ACK.equals(evidence.get("startup_acknowledgement"))
                || !(evidence.get("endpoints") instanceof List)) return false;
        List<?> endpoints = (List<?>) evidence.get("endpoints");
        Set<String> unique = new HashSet<>();
        for (Object valueEndpoint : endpoints) {
            Map<?, ?> endpoint = object(valueEndpoint);
            String key = endpointKey(endpoint);
            if (key == null || !allowed.contains(key) || !unique.add(key)) return false;
        }
        return unique.containsAll(required);
    }

    private static String endpointKey(Map<?, ?> endpoint) {
        Object protocol = endpoint.get("protocol"), port = endpoint.get("port");
        if (!"127.0.0.1".equals(endpoint.get("address"))
                || !("tcp".equals(protocol) || "udp".equals(protocol)) || !(port instanceof Number)) return null;
        int number = ((Number) port).intValue();
        return number(port, number) && number > 0 && number <= 65535 ? protocol + ":" + number : null;
    }

    private static Map<?, ?> object(Object value) {
        return value instanceof Map ? (Map<?, ?>) value : Collections.emptyMap();
    }
    private static boolean yes(Object value) { return Boolean.TRUE.equals(value); }
    private static boolean number(Object value, int expected) {
        return value instanceof Number && ((Number) value).doubleValue() == expected;
    }
    private static boolean size(Object value, int expected) {
        return value instanceof List && ((List<?>) value).size() == expected;
    }
    private static boolean empty(Object value) { return size(value, 0); }
    private DbServerAcceptance() {}
}
