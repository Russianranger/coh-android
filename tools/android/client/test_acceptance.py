#!/usr/bin/env python3
"""Exercise shipped Java acceptance against stale frames and incomplete cleanup."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/client/src/main/java/io/github/russianranger/cohclienttest/ClientAcceptance.java'
FIXTURE = r'''
package io.github.russianranger.cohclienttest;
import java.util.*;
public final class ClientAcceptanceHost {
    static Map<String,Object> map(Object... values) {
        Map<String,Object> result = new LinkedHashMap<>();
        for (int i=0;i<values.length;i+=2) result.put((String)values[i],values[i+1]);
        return result;
    }
    static final String SESSION = "0123456789abcdef0123456789abcdef";
    static List<Map<String,Object>> samples() {
        List<Map<String,Object>> samples = new ArrayList<>();
        for (int i=0;i<3;i++) samples.add(map("session_id",SESSION,"sequence",7,
            "pixel_copy_success",true,"non_uniform",true,"png_verified",true,
            "source_width",800,"source_height",600,"png_sha256",String.join("", Collections.nCopies(64,"a")),
            "captured_elapsed_ms",1000L+i*1000));
        return samples;
    }
    static Map<String,Object> cleanup() {
        return map("cleanup_complete",true,"cleanup_execution",map("diagnostic_initialized",true,
            "wine_started",true,"owned_child_count",1),"processes",Arrays.asList(map("exit_code",0,
            "input_closed",true,"output_capture_closed",true)),"cleanup",map("owned_processes_reaped",true,
            "wine_prefix_stopped",true),"wine_process_cleanup",map("complete",true,"remaining",0,"inspection_failures",0));
    }
    @SuppressWarnings("unchecked") static Map<String,Object> at(Map<String,Object> value,String key) {
        return (Map<String,Object>) value.get(key);
    }
    public static void main(String[] args) {
        List<Map<String,Object>> frames=samples(); Map<String,Object> cleanup=cleanup();
        boolean expected=false,actual;
        switch(args[0]) {
            case "valid": expected=true; break;
            case "static_frame": expected=true; break;
            case "stale_session": frames.get(0).put("session_id","ffffffffffffffffffffffffffffffff"); break;
            case "missing_pixelcopy": frames.get(0).remove("pixel_copy_success"); break;
            case "missing_png": frames.get(0).remove("png_verified"); break;
            case "blank_frame": frames.get(0).put("non_uniform",false); break;
            case "bad_hash": frames.get(0).put("png_sha256","not-a-hash"); break;
            case "wrong_size": frames.get(0).put("source_width",1024); break;
            case "short_span": for(int i=0;i<3;i++) frames.get(i).put("captured_elapsed_ms",1000+i*100); break;
            case "before_window": frames.get(0).put("captured_elapsed_ms",999); break;
            case "after_window": frames.get(2).put("captured_elapsed_ms",3501); break;
            case "duplicate_capture": frames.get(2).put("captured_elapsed_ms",2000); break;
            case "zero_sequence": frames.get(0).put("sequence",0); break;
            case "pre_event_frame": frames.get(0).put("sequence",5); break;
            case "at_event_frame": frames.get(0).put("sequence",6); break;
            case "fractional_time": frames.get(0).put("captured_elapsed_ms",1000.5); break;
            case "cleanup_valid": expected=true; break;
            case "cleanup_missing": cleanup.remove("cleanup_execution"); break;
            case "cleanup_orphan": at(cleanup,"wine_process_cleanup").put("remaining",1); break;
            case "cleanup_unreadable": at(cleanup,"wine_process_cleanup").put("inspection_failures",1); break;
            case "cleanup_capture_live": ((Map)((List)cleanup.get("processes")).get(0)).put("output_capture_closed",false); break;
            case "cleanup_child_omitted": at(cleanup,"cleanup_execution").put("owned_child_count",2); break;
            case "cleanup_no_guest": cleanup=map("cleanup_complete",true,"processes",Collections.emptyList(),
                "cleanup_execution",map("diagnostic_initialized",false,"wine_started",false,"owned_child_count",0));expected=true;break;
            default: throw new AssertionError("Unknown fixture");
        }
        actual=args[0].startsWith("cleanup_") ? ClientAcceptance.cleanupSafe(cleanup)
            : ClientAcceptance.surfaceAccepted(frames,SESSION,500,4000,1000,3500,6);
        if(actual!=expected) throw new AssertionError(args[0]+" expected="+expected+" actual="+actual);
    }
}
'''


class ClientAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='coh-client-gate-')
        harness = Path(cls.tmp.name) / 'ClientAcceptanceHost.java'
        harness.write_text(FIXTURE)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', cls.tmp.name, str(SOURCE), str(harness)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_frame_boundaries(self):
        for mode in ('valid', 'static_frame', 'stale_session', 'missing_pixelcopy',
                     'missing_png', 'blank_frame', 'bad_hash', 'wrong_size', 'short_span',
                     'before_window', 'after_window', 'duplicate_capture', 'zero_sequence', 'pre_event_frame', 'at_event_frame', 'fractional_time'):
            with self.subTest(mode=mode): self.execute(mode)

    def test_cleanup_boundaries(self):
        for mode in ('cleanup_valid', 'cleanup_missing', 'cleanup_orphan', 'cleanup_unreadable',
                     'cleanup_capture_live', 'cleanup_child_omitted', 'cleanup_no_guest'):
            with self.subTest(mode=mode): self.execute(mode)

    def execute(self, mode):
        subprocess.run(['java', '-cp', self.tmp.name,
                        'io.github.russianranger.cohclienttest.ClientAcceptanceHost', mode],
                       check=True, capture_output=True, timeout=10)


if __name__ == '__main__': unittest.main()
