package io.github.russianranger.cohatlastest;

/** Keeps one document-picker result alive while a recreated service inspects
 * saved state. This queue is intentionally in memory: process death cannot
 * restart an operation or retain a document URI. */
final class AtlasOperationDispatch<T> {
    private boolean initialized;
    private T current, pending;

    synchronized boolean offer(T request) {
        if (request == null) throw new NullPointerException("request");
        if (current != null) return false;
        current = pending = request;
        return true;
    }

    synchronized T initialized() {
        initialized = true;
        return takeReady();
    }

    synchronized T takeReady() {
        if (!initialized) return null;
        T request = pending;
        pending = null;
        return request;
    }

    synchronized void finish(T request) {
        if (current != request) return;
        current = pending = null;
    }
}
