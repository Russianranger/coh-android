package io.github.russianranger.cohdiagnostic;

import java.util.concurrent.atomic.AtomicInteger;

/** Arbitrates Stop versus completed cleanup before a report becomes immutable. */
final class DiagnosticOutcome {
    private static final int RUNNING = 0, STOP_REQUESTED = 1, FINISHED = 2, FINISHED_CANCELLED = 3;
    private final AtomicInteger state = new AtomicInteger(RUNNING);

    boolean requestStop() {
        return state.compareAndSet(RUNNING, STOP_REQUESTED) || state.get() == STOP_REQUESTED;
    }

    boolean cancelled() {
        int current = state.get();
        return current == STOP_REQUESTED || current == FINISHED_CANCELLED;
    }

    boolean finish() {
        for (;;) {
            int current = state.get();
            if (current == FINISHED || current == FINISHED_CANCELLED) return current == FINISHED_CANCELLED;
            if (state.compareAndSet(current, current == STOP_REQUESTED ? FINISHED_CANCELLED : FINISHED))
                return current == STOP_REQUESTED;
        }
    }
}
