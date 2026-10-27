package io.github.russianranger.cohclientinteractive;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** The actual app validator must retain strict ordering for both selections. */
public final class ArmPortAcceptanceTest {
    static int checks;
    static void require(boolean result) {
        checks++;
        if (!result) throw new AssertionError("case " + checks);
    }
    static Map<String, Object> pin() {
        Map<String, Object> value = new HashMap<>();
        value.put("bytes", 12); value.put("sha256", String.join("", java.util.Collections.nCopies(64, "a")));
        return value;
    }
    static List<Object> stages(boolean arm64, boolean visual) {
        List<String> names = new ArrayList<>(Arrays.asList("client_inputs", "client_private_data",
            "persistent_server_profile", "postgres_local_login", "presentation_display", "wine_initialization",
            "local_login_odbc", "local_dbserver_startup", "local_atlas_startup"));
        if (visual) names.addAll(Arrays.asList("client_visual_assets", "client_animation_pack"));
        if (arm64) names.add("armport_client_data");
        names.addAll(Arrays.asList("win32_runtime_dll", "actual_client_startup", "actual_client_interaction"));
        List<Object> result = new ArrayList<>();
        for (String name : names) {
            Map<String, Object> item = new HashMap<>();
            item.put("stage", name); item.put("status", "passed"); result.add(item);
        }
        return result;
    }
    public static void main(String[] ignored) {
        Map<String, Object> pins = new HashMap<>();
        List<Object> x86 = stages(false, false), arm64 = stages(true, false);
        require(ClientAcceptance.clientInteractionStageIndex(x86, pins) == 11);
        require(ClientAcceptance.clientInteractionStageIndex(arm64, pins, "arm64") == -1);
        for (String name : new String[]{"armport-client.zip", "armport_client_package.py",
                "armport_interactive.py", "client_stdio.py"}) pins.put(name, pin());
        require(ClientAcceptance.clientInteractionStageIndex(x86, pins, "x86") == 11);
        require(ClientAcceptance.clientInteractionStageIndex(arm64, pins, "arm64") == 12);
        require(ClientAcceptance.clientInteractionStageIndex(x86, pins, "arm64") == -1);
        require(ClientAcceptance.clientInteractionStageIndex(arm64, pins, "x86") == -1);
        require(ClientAcceptance.clientInteractionStageIndex(arm64, pins, "unknown") == -1);
        java.util.Collections.swap(arm64, 8, 9);
        require(ClientAcceptance.clientInteractionStageIndex(arm64, pins, "arm64") == -1);
        arm64 = stages(true, false);
        ((Map<String, Object>)arm64.get(9)).put("status", "failed");
        require(ClientAcceptance.clientInteractionStageIndex(arm64, pins, "arm64") == -1);
        for (String name : new String[]{"client_visual_assets.py", "client_animation_package.py",
                "client-visual-assets.zip", "client-visual-manifest.json", "server-animations.pigg",
                "server-animation-manifest.json"}) pins.put(name, pin());
        require(ClientAcceptance.clientInteractionStageIndex(stages(true, false), pins, "arm64") == -1);
        require(ClientAcceptance.clientInteractionStageIndex(stages(true, true), pins, "arm64") == 14);
        require(ClientAcceptance.clientInteractionStageIndex(stages(false, true), pins, "x86") == 13);
        pins.remove("client_stdio.py");
        require(ClientAcceptance.clientInteractionStageIndex(stages(true, true), pins, "arm64") == -1);
        System.out.println("Actual ClientAcceptance ARM64/x86 stage checks: " + checks + " passed");
    }
}
