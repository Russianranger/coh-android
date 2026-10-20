#!/usr/bin/env python3
"""Bounded host-Java controls for the optional historical surface capture store.

Compiles only the pure Java helper at source level 8. All classes, generated raw
frames and ZIPs stay in a temporary directory; no Android build or receipt input.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile


SOURCE = Path(__file__).resolve().parents[1] / "app/src/main/java/org/coh/nativecombined/SceneFrameCapture.java"
HARNESS = r'''
import org.coh.nativecombined.SceneFrameCapture;
import java.io.*;
import java.nio.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.zip.*;

public final class CaptureStoreControls {
    private static int checks;
    private static void require(boolean condition, String message) {
        checks++;
        if (!condition) throw new AssertionError(message);
    }
    private static ByteBuffer bytes(byte[] raw) {
        return ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN);
    }
    private static byte[] raw(int width, int height, long frame) throws Exception {
        byte[] raw = new byte[128 + width * height * 4];
        ByteBuffer b = bytes(raw);
        b.put("COHFB001".getBytes("US-ASCII"));
        b.putInt(8, 128); b.putInt(12, width); b.putInt(16, height);
        b.putInt(20, 1920); b.putInt(24, 1080); b.putInt(28, width * height * 4);
        b.putInt(32, 10239); b.putLong(40, frame); b.putLong(48, 22);
        b.putLong(56, 3); b.putLong(64, frame - 12); b.putLong(72, 4); b.putLong(80, 5);
        b.putFloat(88, 131.453125f); b.putFloat(92, 0.25f); b.putFloat(96, -114.953125f);
        b.putLong(104, 486030); b.putLong(112, 96L * 1024 * 1024);
        b.putInt(120, 12); b.putInt(124, 1);
        for (int i = 128; i < raw.length; i++) raw[i] = (byte) (i * 29);
        return raw;
    }
    private static File store(File directory) { return new File(directory, "scene-capture.bin"); }
    private static File temporary(File directory) { return new File(directory, "scene-capture.tmp"); }
    private static void rejected(File directory, byte[] candidate, long version, String session,
            byte[] previous, String name) throws Exception {
        boolean failed = false;
        try { SceneFrameCapture.save(directory, candidate, version, session); }
        catch (IOException expected) { failed = true; }
        require(failed, "accepted " + name);
        require(Arrays.equals(previous, Files.readAllBytes(store(directory).toPath())), "changed old " + name);
        require(!temporary(directory).exists(), "left temporary " + name);
    }
    private static void zip(File directory, File result, boolean expected) throws Exception {
        try (ZipOutputStream output = new ZipOutputStream(new FileOutputStream(result))) {
            output.putNextEntry(new ZipEntry("essential.txt")); output.write(7); output.closeEntry();
            require(SceneFrameCapture.append(directory, output) == expected, "append presence " + result);
            output.putNextEntry(new ZipEntry("after.txt")); output.write(9); output.closeEntry();
        }
    }
    private static void absent(File directory, File zip) throws Exception {
        require(SceneFrameCapture.metadata(directory) == null, "invalid metadata published");
        zip(directory, zip, false);
        ByteArrayOutputStream untouched = new ByteArrayOutputStream();
        require(!SceneFrameCapture.writeZip(directory, untouched), "invalid standalone ZIP accepted");
        require(untouched.size() == 0, "invalid standalone ZIP touched output");
    }
    private static void directZip(File directory, File result) throws Exception {
        final boolean[] closed = {false};
        try (OutputStream output = new FilterOutputStream(new FileOutputStream(result)) {
            public void close() throws IOException { closed[0] = true; super.close(); }
        }) {
            require(SceneFrameCapture.writeZip(directory, output), "standalone ZIP absent");
            require(!closed[0], "standalone ZIP closed caller output");
        }
    }
    public static void main(String[] args) throws Exception {
        File root = new File(args[0]), valid = new File(root, "valid");
        byte[] first = raw(4, 3, 37);
        String metadata = SceneFrameCapture.save(valid, first, 17, "ABc9");
        require(metadata.equals(SceneFrameCapture.metadata(valid)), "save/read metadata mismatch");
        require(store(valid).length() == first.length + 128, "container size");
        require(!temporary(valid).exists(), "successful temp cleanup");
        Files.write(new File(root, "expected.rgba").toPath(), first);
        Files.write(new File(root, "metadata.json").toPath(), metadata.getBytes("UTF-8"));
        zip(valid, new File(root, "valid.zip"), true);
        directZip(valid, new File(root, "direct-valid.zip"));
        byte[] previous = Files.readAllBytes(store(valid).toPath());

        rejected(valid, null, 17, "abc9", previous, "null raw");
        rejected(valid, new byte[127], 17, "abc9", previous, "short header");
        rejected(valid, new byte[83073], 17, "abc9", previous, "oversize raw");
        rejected(valid, Arrays.copyOf(first, first.length - 1), 17, "abc9", previous, "truncation");
        rejected(valid, Arrays.copyOf(first, first.length + 1), 17, "abc9", previous, "trailing raw byte");
        int[][] invalid32 = {{0,0}, {8,127}, {12,0}, {12,193}, {12,-1}, {16,109},
                {20,0}, {20,16385}, {24,0}, {24,16385}, {28,-1}, {32,0}, {32,10240},
                {36,1}, {88,0x7fc00000}, {92,0x7f800000}, {96,0xff800000}, {100,1}, {120,11}, {124,0}};
        for (int[] change : invalid32) {
            byte[] candidate = first.clone(); bytes(candidate).putInt(change[0], change[1]);
            rejected(valid, candidate, 17, "different", previous, "u32/float " + change[0]);
        }
        long[][] invalid64 = {{40,11}, {40,Long.MIN_VALUE}, {48,Long.MIN_VALUE}, {56,0},
                {64,26}, {64,Long.MAX_VALUE}, {64,Long.MIN_VALUE}, {72,0}, {80,0},
                {104,96L*1024*1024+1}, {104,Long.MIN_VALUE}, {112,1}};
        for (long[] change : invalid64) {
            byte[] candidate = first.clone(); bytes(candidate).putLong((int) change[0], change[1]);
            rejected(valid, candidate, 17, "a", previous, "u64 " + change[0]);
        }
        for (String session : new String[]{null, "", "g", "ff\"00", " f", "\u00e9", "fffffffffffffffffffffffffffffffff"})
            rejected(valid, first, 17, session, previous, "session");
        rejected(valid, first, 0, "a", previous, "zero version");
        rejected(valid, first, -1, "a", previous, "negative version");
        rejected(valid, first, 17, "abc9", previous, "duplicate frame");
        rejected(valid, raw(4, 3, 36), 17, "ABC9", previous, "older frame");

        byte[] next = raw(4, 3, 38);
        String nextMetadata = SceneFrameCapture.save(valid, next, 18, "abc9");
        require(!nextMetadata.equals(metadata), "replacement metadata unchanged");
        require(SceneFrameCapture.metadata(valid).equals(nextMetadata), "replacement not visible");
        require(!temporary(valid).exists(), "replacement left temp");
        // A different activity session may restart native frame numbering.
        SceneFrameCapture.save(valid, raw(1, 1, 12), 19, "1");
        previous = Files.readAllBytes(store(valid).toPath());

        // A preexisting nonempty temp directory makes writing fail. It is not
        // ours to recursively remove; the previous published record survives.
        require(temporary(valid).mkdir(), "prepare failed write");
        File obstruction = new File(temporary(valid), "owner");
        Files.write(obstruction.toPath(), new byte[]{1});
        boolean failed = false;
        try { SceneFrameCapture.save(valid, raw(1, 1, 13), 20, "1"); }
        catch (IOException expected) { failed = true; }
        require(failed, "write failure accepted");
        require(Arrays.equals(previous, Files.readAllBytes(store(valid).toPath())), "write failure changed old capture");
        require(obstruction.delete() && temporary(valid).delete(), "test cleanup");
        require(SceneFrameCapture.metadata(valid) != null, "write failure invalidated capture");

        File blocked = new File(root, "blocked"); require(blocked.mkdir(), "blocked directory");
        require(store(blocked).mkdir(), "blocked target");
        File child = new File(store(blocked), "owner"); Files.write(child.toPath(), new byte[]{1});
        failed = false;
        try { SceneFrameCapture.save(blocked, first, 17, "a"); }
        catch (IOException expected) { failed = true; }
        require(failed && !temporary(blocked).exists() && child.isFile(), "atomic move failure cleanup");

        File maximum = new File(root, "maximum"); byte[] largest = raw(192, 108, Long.MAX_VALUE);
        ByteBuffer max = bytes(largest);
        max.putInt(20,16384); max.putInt(24,16384); max.putLong(48,Long.MAX_VALUE);
        max.putLong(56,Long.MAX_VALUE); max.putLong(72,Long.MAX_VALUE); max.putLong(80,Long.MAX_VALUE);
        max.putLong(104,96L*1024*1024); max.putFloat(88,Float.MAX_VALUE);
        String maxMetadata = SceneFrameCapture.save(maximum, largest, Long.MAX_VALUE,
                "0123456789abcdef0123456789abcdef");
        require(largest.length == 83072 && store(maximum).length() == 83200, "maximum bound");
        require(maxMetadata.getBytes("UTF-8").length <= 4096, "metadata bound");
        Files.write(new File(root, "maximum.json").toPath(), maxMetadata.getBytes("UTF-8"));
        zip(maximum, new File(root, "maximum.zip"), true);
        directZip(maximum, new File(root, "direct-maximum.zip"));

        File corrupt = new File(root, "corrupt"); require(corrupt.mkdir(), "corrupt directory");
        byte[] original = Files.readAllBytes(store(maximum).toPath());
        for (int offset : new int[]{0,8,12,16,24,28,32,63,64,96,128,original.length-1}) {
            byte[] changed = original.clone(); changed[offset] ^= 1;
            Files.write(store(corrupt).toPath(), changed);
            absent(corrupt, new File(root, "invalid-" + offset + ".zip"));
        }
        for (int size : new int[]{0,127,128,255,original.length-1}) {
            Files.write(store(corrupt).toPath(), Arrays.copyOf(original, size));
            absent(corrupt, new File(root, "truncated-" + size + ".zip"));
        }
        try (RandomAccessFile file = new RandomAccessFile(store(corrupt), "rw")) { file.setLength(86017); }
        absent(corrupt, new File(root, "oversize.zip"));
        absent(new File(root, "absent"), new File(root, "absent.zip"));
        require(SceneFrameCapture.metadata(null) == null, "null directory metadata");
        zip(null, new File(root, "null.zip"), false);
        File notDirectory = new File(root, "not-directory"); Files.write(notDirectory.toPath(), new byte[]{1});
        absent(notDirectory, new File(root, "not-directory.zip"));
        // Invalid old storage can be replaced by one valid snapshot.
        SceneFrameCapture.save(corrupt, first, 17, "a");
        require(SceneFrameCapture.metadata(corrupt) != null, "invalid old capture not replaceable");

        AtomicInteger saved = new AtomicInteger(), refused = new AtomicInteger();
        File concurrent = new File(root, "concurrent");
        Runnable write = () -> {
            try { SceneFrameCapture.save(concurrent, first, 17, "a"); saved.incrementAndGet(); }
            catch (IOException expected) { refused.incrementAndGet(); }
        };
        Thread a = new Thread(write), b = new Thread(write); a.start(); b.start(); a.join(); b.join();
        require(saved.get() == 1 && refused.get() == 1, "duplicate writer serialization");
        for (int i = 0; i < 128; i++) require(SceneFrameCapture.metadata(maximum) != null, "repeat read");
        ZipOutputStream broken = new ZipOutputStream(new OutputStream() {
            public void write(int value) throws IOException { throw new IOException("intentional sink failure"); }
        });
        failed = false;
        try { SceneFrameCapture.append(maximum, broken); }
        catch (IOException expected) { failed = true; }
        require(failed, "ZIP sink failure hidden");
        failed = false;
        try {
            SceneFrameCapture.writeZip(maximum, new OutputStream() {
                public void write(int value) throws IOException { throw new IOException("intentional sink failure"); }
            });
        } catch (IOException expected) { failed = true; }
        require(failed, "standalone ZIP sink failure hidden");
        System.out.println("Scene frame capture controls passed: " + checks);
    }
}
'''


def check_outputs(root: Path) -> None:
    metadata = json.loads((root / "metadata.json").read_text())
    expected = (root / "expected.rgba").read_bytes()
    assert metadata["size_bytes"] == len(expected)
    assert metadata["sha256"] == hashlib.sha256(expected).hexdigest()
    assert metadata["frame"] == 37 and metadata["epoch"] == 22
    assert metadata["pose_generation"] == 3 and metadata["pose_lock_frame"] == 25
    assert metadata["pose"] == [131.453125, 0.25, -114.953125]
    assert metadata["selected_entity_index"] == 10239
    assert metadata["dimensions"] == {"width": 4, "height": 3}
    assert metadata["viewport"] == {"width": 1920, "height": 1080}
    assert metadata["source_app_version"] == 17 and metadata["activity_session"] == "abc9"
    assert metadata["whole_game_surface"] is True
    assert metadata["startup_witness"] is False and metadata["current_world_authority"] is False
    assert metadata["capture_state"] == "historical_saved_frame"
    assert metadata["pixel_format"] == "RGBA8" and metadata["origin"] == "bottom-left"
    assert metadata["raw_header_bytes"] == 128 and metadata["settled_frame_wait"] == 12
    assert metadata["world_packets"] == 4 and metadata["entity_draws"] == 5
    assert metadata["charged_scene_bytes"] == 486030
    assert metadata["memory_cap_bytes"] == 96 * 1024 * 1024
    for archive in root.glob("*.zip"):
        with zipfile.ZipFile(archive) as result:
            names = result.namelist()
            direct = archive.name.startswith("direct-")
            if not direct:
                assert result.read("essential.txt") == b"\x07"
                assert result.read("after.txt") == b"\x09"
            if archive.name in {"valid.zip", "maximum.zip", "direct-valid.zip", "direct-maximum.zip"}:
                expected_names = ["scene-capture.rgba", "scene-capture.json"]
                assert names == (expected_names if direct else ["essential.txt"] + expected_names + ["after.txt"])
                raw = result.read("scene-capture.rgba")
                info = json.loads(result.read("scene-capture.json"))
                assert len(raw) <= 83072 and len(result.read("scene-capture.json")) <= 4096
                assert info["size_bytes"] == len(raw)
                assert info["sha256"] == hashlib.sha256(raw).hexdigest()
                assert raw[:8] == b"COHFB001"
                if archive.name in {"valid.zip", "direct-valid.zip"}:
                    assert raw == expected and info == metadata
                if direct:
                    assert result.testzip() is None
                    assert all(entry.compress_type == zipfile.ZIP_STORED for entry in result.infolist())
                    expected_bytes = len(raw) + len(result.read("scene-capture.json")) + 30*2 + 46*2 + 22
                    expected_bytes += 2 * sum(len(name) for name in expected_names)
                    assert archive.stat().st_size == expected_bytes
            else:
                assert names == ["essential.txt", "after.txt"], archive
    maximum = json.loads((root / "maximum.json").read_text())
    assert maximum["size_bytes"] == 83072 and maximum["frame"] == 2**63 - 1
    assert maximum["source_app_version"] == 2**63 - 1
    assert maximum["activity_session"] == "0123456789abcdef0123456789abcdef"


def main() -> None:
    # Serialize externally with: flock /tmp/coh-next-build.lock python3 <this file>
    with tempfile.TemporaryDirectory(prefix="coh-frame-capture-") as directory:
        root = Path(directory)
        harness = root / "CaptureStoreControls.java"
        harness.write_text(HARNESS)
        subprocess.run(["java", "-Xmx128m", "com.sun.tools.javac.Main", "--release", "8",
                        "-d", str(root), str(SOURCE), str(harness)], check=True, timeout=60)
        subprocess.run(["java", "-Xmx64m", "-cp", str(root), "CaptureStoreControls", str(root)],
                       check=True, timeout=60)
        check_outputs(root)
    print("Verified raw/JSON ZIP bytes and SHA-256; absent/invalid captures preserve essential export.")


if __name__ == "__main__":
    main()
