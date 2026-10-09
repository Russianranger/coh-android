package io.github.russianranger.cohdiagnostic;

import java.io.IOException;
import java.util.Arrays;
import java.util.LinkedHashSet;

/** Mirrors the hosted test's controlled local hostname resolution. */
final class DeviceHosts {
    static String contents(String hostname) throws IOException {
        if (hostname == null || hostname.isEmpty() || hostname.length() > 253)
            throw new IOException("Kernel hostname is not a safe hosts-file name");
        String[] labels = hostname.split("\\.", -1);
        for (String label : labels)
            if (!label.matches("[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"))
                throw new IOException("Kernel hostname is not a safe hosts-file name");
        return "127.0.0.1 " + String.join(" ", new LinkedHashSet<>(Arrays.asList("localhost", hostname, labels[0]))) + "\n";
    }
    private DeviceHosts() {}
}
