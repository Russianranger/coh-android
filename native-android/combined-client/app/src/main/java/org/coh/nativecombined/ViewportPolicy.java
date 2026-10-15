package org.coh.nativecombined;

/** Keep the Android Surface inside the unchanged source camera's supported bounds. */
final class ViewportPolicy {
    private static final int MAX_DIMENSION = 16384;

    private ViewportPolicy() { }

    /** Largest supported rectangle that fits the available measured pixels. */
    static int[] fit(int availableWidth, int availableHeight) {
        if (availableWidth <= 0 || availableHeight <= 0) return new int[] {0, 0};
        long width = Math.min((long) availableWidth, MAX_DIMENSION);
        long height = Math.min((long) availableHeight, MAX_DIMENSION);
        // coh_world_camera accepts aspect [1/4, 8]; the renderer bounds each
        // EGL dimension to 16384. Fit the actual Surface, not its projection.
        if (width > height * 8L) width = height * 8L;
        if (height > width * 4L) height = width * 4L;
        return new int[] {(int) width, (int) height};
    }

    /** Bound scrolling controls so a visible scene retains at least 40% height. */
    static int controlsHeight(int availableHeight, int preferredControlsHeight) {
        if (availableHeight <= 0 || preferredControlsHeight <= 0) return 0;
        return (int) Math.min((long) preferredControlsHeight, availableHeight * 3L / 5L);
    }
}
