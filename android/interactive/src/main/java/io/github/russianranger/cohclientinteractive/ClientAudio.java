package io.github.russianranger.cohclientinteractive;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.AudioFocusRequest;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioTrack;
import android.net.LocalServerSocket;
import android.net.LocalSocket;
import android.net.LocalSocketAddress;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.os.SystemClock;
import android.system.Os;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.EOFException;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Game audio (0.13.53): the guest's ALSA playback device to an Android AudioTrack.
 *
 * The client's DirectSound goes through Wine's ALSA driver to the TRASC ALSA
 * plugin (armport/audio/pcm_trasc.c), which connects to this app-private
 * filesystem socket. Protocol 1: open {0x50414c54, 1, 48000, 2, buffer frames},
 * then 1 start, 2 stop, 3 playback head, 4 write {frames} + PCM (reply: frames
 * accepted, never blocking), 5 prepare. The AudioTrack playback head is the
 * clock. Adapted from the owner's lsb-android AudioBridge, AudioPcmSession and
 * AudioBufferPolicy (the TRASC bridge used on the Thor). No TCP, capture or root.
 */
final class ClientAudio implements AutoCloseable {
    /** The socket's path inside the guest (the presentation socket directory). */
    static final String GUEST_SOCKET = "/presentation-socket/audio.sock";
    private static final int MAX_EVENTS = 64, MAX_STREAMS = 8;
    private final File path;
    private final LocalSocket bound = new LocalSocket();
    private LocalServerSocket server;
    private final Set<Connection> connections = new HashSet<>();
    private volatile boolean closed;
    private volatile float volume = 1;
    private final AudioManager manager;
    private final AudioFocusRequest focus;
    private final AudioAttributes attributes = new AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_GAME).setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build();
    // Never held while taking another lock (connections and streams take it last).
    private final Object stats = new Object();
    private final List<String> events = new ArrayList<>();
    private int opened, refusedStreams, focusResult;
    private long frames, nonzeroSamples, underruns;
    private String listenerError;
    private final long startedUptime = SystemClock.uptimeMillis();

    static ClientAudio start(Context context, File path) throws IOException {
        ClientAudio bridge = new ClientAudio(context, path);
        try { bridge.listen(); return bridge; } catch (IOException | RuntimeException e) { bridge.close(); throw e; }
    }

    private ClientAudio(Context context, File path) {
        this.path = path;
        manager = (AudioManager) context.getSystemService(Context.AUDIO_SERVICE);
        focus = new AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN).setAudioAttributes(attributes)
                .setOnAudioFocusChangeListener(change -> {
                    volume = change == AudioManager.AUDIOFOCUS_GAIN ? 1
                            : change == AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK ? .2f : 0;
                    synchronized (connections) { for (Connection c : connections) c.volume(volume); }
                    record("focus=" + change);
                }, new Handler(Looper.getMainLooper())).build();
    }

    private void listen() throws IOException {
        Files.deleteIfExists(path.toPath());
        bound.bind(new LocalSocketAddress(path.getPath(), LocalSocketAddress.Namespace.FILESYSTEM));
        try { Os.chmod(path.getPath(), 0600); } catch (android.system.ErrnoException e) { throw new IOException("Audio socket mode", e); }
        server = new LocalServerSocket(bound.getFileDescriptor());
        focusResult = manager.requestAudioFocus(focus);
        volume = focusResult == AudioManager.AUDIOFOCUS_REQUEST_GRANTED ? 1 : 0;
        record("bridge=alsa-audiotrack protocol=1 rate=48000 channels=2 focus=" + focusResult
                + " media_volume=" + manager.getStreamVolume(AudioManager.STREAM_MUSIC));
        Thread listener = new Thread(() -> {
            try {
                while (!closed) {
                    LocalSocket socket = server.accept();
                    synchronized (connections) {
                        if (closed || connections.size() >= MAX_STREAMS
                                || socket.getPeerCredentials().getUid() != android.os.Process.myUid()) {
                            synchronized (stats) { refusedStreams++; }
                            socket.close(); continue;
                        }
                        Connection c = new Connection(socket); connections.add(c);
                        synchronized (stats) { opened++; }
                        Thread worker = new Thread(c, "coh-client-audio-playback"); worker.setDaemon(true); worker.start();
                    }
                }
            } catch (Exception e) {
                if (!closed) { synchronized (stats) { listenerError = e.getClass().getSimpleName(); } record("listener_error=" + e); }
            }
        }, "coh-client-audio-listener");
        listener.setDaemon(true); listener.start();
    }

    private void record(String text) {
        synchronized (stats) { if (events.size() < MAX_EVENTS) events.add((SystemClock.uptimeMillis() - startedUptime) + "ms " + text); }
    }

    private void streamClosed(long streamFrames, long streamNonzero, long streamUnderruns) {
        synchronized (stats) { frames += streamFrames; nonzeroSamples += streamNonzero; underruns += streamUnderruns; }
    }

    /** Report for android-client-report.json; counts include streams still open. */
    JSONObject summary() throws JSONException {
        long liveFrames = 0, liveNonzero = 0;
        // Live counters are volatile; no stream lock is taken here.
        synchronized (connections) { for (Connection c : connections) { liveFrames += c.session.frames; liveNonzero += c.session.nonzeroSamples; } }
        synchronized (stats) {
            JSONArray log = new JSONArray(); for (String event : events) log.put(event);
            return new JSONObject().put("format", 1).put("protocol", 1).put("socket", GUEST_SOCKET)
                    .put("streams_opened", opened).put("streams_refused", refusedStreams)
                    .put("frames", frames + liveFrames).put("nonzero_samples", nonzeroSamples + liveNonzero)
                    .put("underruns", underruns).put("focus_request", focusResult)
                    .put("listener_error", listenerError == null ? JSONObject.NULL : listenerError)
                    .put("events", log).put("events_truncated", events.size() >= MAX_EVENTS);
        }
    }

    private final class Connection implements Runnable, Sink {
        final LocalSocket socket; final PcmSession session = new PcmSession();
        AudioTrack track; int capacity; boolean ended; long submitted, nonzero, nextReport, streamUnderruns; boolean firstSignal;
        Connection(LocalSocket socket) { this.socket = socket; }
        public void run() {
            try { session.run(socket.getInputStream(), socket.getOutputStream(), this); }
            catch (Exception e) { if (!closed) record("stream_error=" + e); }
            finally {
                close();
                synchronized (connections) { connections.remove(this); }
                streamClosed(session.frames, session.nonzeroSamples, streamUnderruns);
                record("stream_closed frames=" + session.frames + " nonzero_samples=" + session.nonzeroSamples);
            }
        }
        public synchronized void configure(int frames) throws IOException { capacity = frames; reset(); }
        public synchronized void reset() throws IOException {
            if (ended) throw new IOException("Audio stream closed");
            release();
            int minimum = AudioTrack.getMinBufferSize(48000, AudioFormat.CHANNEL_OUT_STEREO, AudioFormat.ENCODING_PCM_16BIT);
            if (minimum <= 0) throw new IOException("Stereo audio format unavailable");
            track = new AudioTrack.Builder().setAudioAttributes(attributes)
                    .setAudioFormat(new AudioFormat.Builder().setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                            .setSampleRate(48000).setChannelMask(AudioFormat.CHANNEL_OUT_STEREO).build())
                    .setTransferMode(AudioTrack.MODE_STREAM).setBufferSizeInBytes(Math.max(minimum, capacity * 4)).build();
            if (track.getState() != AudioTrack.STATE_INITIALIZED) throw new IOException("Could not initialize Android audio");
            configureBuffer(); submitted = nonzero = nextReport = 0; firstSignal = false;
            track.setVolume(volume);
            record("stream_config producer_frames=" + capacity + " minimum_bytes=" + minimum
                    + " buffer_frames=" + track.getBufferSizeInFrames() + " allocated_frames=" + track.getBufferCapacityInFrames()
                    + " start_frames=" + threshold());
        }
        private int threshold() { return Build.VERSION.SDK_INT >= 31 ? track.getStartThresholdInFrames() : track.getBufferSizeInFrames(); }
        private void configureBuffer() throws IOException {
            BufferPolicy.configure(new BufferPolicy.Track() {
                public int resize(int frames) { return track.setBufferSizeInFrames(frames); }
                public int startThreshold(int frames) {
                    return Build.VERSION.SDK_INT >= 31 ? track.setStartThresholdInFrames(frames) : track.getBufferSizeInFrames();
                }
            }, capacity, Build.VERSION.SDK_INT >= 31);
        }
        public synchronized void start() throws IOException {
            if (track != null) { configureBuffer(); track.play(); record("stream_start queued_frames=" + submitted + " start_frames=" + threshold()); }
        }
        public synchronized void stop() { if (track != null) { report("stream_stop"); track.pause(); track.flush(); submitted = nonzero = 0; } }
        private void report(String event) {
            record(event + " written=" + submitted + " played=" + Integer.toUnsignedLong(track.getPlaybackHeadPosition())
                    + " nonzero_samples=" + nonzero + " underruns=" + track.getUnderrunCount() + " state=" + track.getPlayState()
                    + " volume=" + volume);
        }
        public synchronized int position() throws IOException {
            if (track == null) throw new IOException("Audio stream closed");
            long now = SystemClock.elapsedRealtime();
            if (now >= nextReport) {
                // Routing can enlarge Android's buffers after creation. Reapply the producer limit.
                if (track.getBufferSizeInFrames() > capacity || threshold() > capacity) configureBuffer();
                if (nextReport == 0) report("stream_progress");
                nextReport = now + 5000;
            }
            return track.getPlaybackHeadPosition();
        }
        public synchronized int write(byte[] bytes, int length) throws IOException {
            if (track == null) throw new IOException("Audio stream closed");
            int accepted = track.write(bytes, 0, length, AudioTrack.WRITE_NON_BLOCKING);
            if (accepted > 0) {
                submitted += accepted / 4;
                for (int i = 0; i + 1 < accepted; i += 2) if (bytes[i] != 0 || bytes[i + 1] != 0) nonzero++;
                if (nonzero > 0 && !firstSignal) { firstSignal = true; record("stream_first_signal written=" + submitted); }
            }
            return accepted;
        }
        synchronized void volume(float value) { if (track != null) track.setVolume(value); }
        private void release() {
            if (track == null) return;
            if (track.getState() == AudioTrack.STATE_INITIALIZED) { streamUnderruns += Math.max(0, track.getUnderrunCount()); report("stream_release"); }
            track.release(); track = null;
        }
        public synchronized void close() {
            ended = true; release();
            try { socket.close(); } catch (IOException ignored) {}
        }
    }

    public void close() {
        if (closed) return;
        closed = true;
        try { if (server != null) server.close(); } catch (IOException ignored) {}
        try { bound.close(); } catch (IOException ignored) {}
        synchronized (connections) { for (Connection c : connections) c.close(); }
        manager.abandonAudioFocusRequest(focus);
        if (!path.delete() && path.exists()) record("socket_not_removed");
        record("bridge_closed streams=" + opened);
    }

    interface Sink {
        void configure(int frames) throws IOException;
        void start() throws IOException;
        void stop() throws IOException;
        void reset() throws IOException;
        int position() throws IOException;
        int write(byte[] bytes, int length) throws IOException;
        void close();
    }

    /** Bounded playback protocol (lsb-android AudioPcmSession, protocol 1). */
    static final class PcmSession {
        volatile long frames, nonzeroSamples;
        private static int read(DataInputStream in) throws IOException { return Integer.reverseBytes(in.readInt()); }
        private static void reply(DataOutputStream out, int value) throws IOException { out.writeInt(Integer.reverseBytes(value)); out.flush(); }
        void run(InputStream input, OutputStream output, Sink sink) throws IOException {
            DataInputStream in = new DataInputStream(input); DataOutputStream out = new DataOutputStream(output);
            try {
                if (read(in) != 0x50414c54 || read(in) != 1 || read(in) != 48000 || read(in) != 2) throw new IOException("Unsupported audio stream");
                int capacity = read(in); if (capacity < 64 || capacity > 48000) throw new IOException("Invalid audio buffer size");
                sink.configure(capacity); reply(out, 0);
                byte[] pcm = new byte[4096 * 4];
                for (;;) {
                    int command;
                    try { command = read(in); } catch (EOFException end) { return; }
                    switch (command) {
                        case 1: sink.start(); reply(out, 0); break;
                        case 2: sink.stop(); reply(out, 0); break;
                        case 3: reply(out, sink.position()); break;
                        case 4:
                            int count = read(in); if (count < 1 || count > 4096) throw new IOException("Invalid PCM frame count");
                            in.readFully(pcm, 0, count * 4);
                            int accepted = sink.write(pcm, count * 4);
                            if (accepted < 0 || accepted > count * 4 || accepted % 4 != 0) throw new IOException("Android audio write failed: " + accepted);
                            frames += accepted / 4;
                            for (int i = 0; i < accepted; i += 2) if (pcm[i] != 0 || pcm[i + 1] != 0) nonzeroSamples++;
                            reply(out, accepted / 4); break;
                        case 5: sink.reset(); reply(out, 0); break;
                        default: throw new IOException("Unknown audio command");
                    }
                }
            } finally { sink.close(); }
        }
    }

    /** Keep Android's start watermark within what the ALSA producer can queue (lsb-android AudioBufferPolicy). */
    static final class BufferPolicy {
        interface Track { int resize(int frames); int startThreshold(int frames); }
        static int configure(Track track, int producerFrames, boolean hasStartThreshold) throws IOException {
            if (producerFrames < 64 || producerFrames > 48000) throw new IOException("Invalid producer audio capacity");
            int actual = track.resize(producerFrames);
            if (actual < 1) throw new IOException("Could not size Android audio buffer: " + actual);
            // API 31+ permits immediate startup even for a partially filled Wine buffer.
            int threshold = hasStartThreshold ? track.startThreshold(1) : actual;
            if (threshold < 1 || threshold > producerFrames)
                throw new IOException("Android audio start threshold exceeds producer capacity: " + threshold + " > " + producerFrames);
            return actual;
        }
    }
}
