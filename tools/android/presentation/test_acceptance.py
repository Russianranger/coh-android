#!/usr/bin/env python3
"""Exercise shipped Java acceptance against stale frames and incomplete cleanup."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/presentation/src/main/java/io/github/russianranger/cohpresentation/PresentationAcceptance.java'
FIXTURE = r'''
package io.github.russianranger.cohpresentation;
import java.util.*;
public final class PresentationAcceptanceHost {
    static Map<String,Object> map(Object... values) {
        Map<String,Object> result = new LinkedHashMap<>();
        for (int i=0;i<values.length;i+=2) result.put((String)values[i],values[i+1]);
        return result;
    }
    static final String SESSION = "0123456789abcdef0123456789abcdef";
    static List<Map<String,Object>> samples() {
        List<Map<String,Object>> samples = new ArrayList<>();
        for (int i=0;i<6;i++) samples.add(map("session_id",SESSION,"frame_id",i+1,
            "pixel_copy_success",true,"matching_session",true,"captured_elapsed_ms",1000L+i*500));
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
            case "last_producer_frame": frames.get(5).put("frame_id",120); expected=true; break;
            case "stale_session": frames.get(0).put("session_id","ffffffffffffffffffffffffffffffff"); break;
            case "missing_pixelcopy": frames.get(0).remove("pixel_copy_success"); break;
            case "duplicate_frame": frames.get(0).put("frame_id",2); break;
            case "zero_frame": frames.get(0).put("frame_id",0); break;
            case "beyond_producer": frames.get(5).put("frame_id",121); break;
            case "short_span": for(int i=0;i<6;i++) frames.get(i).put("captured_elapsed_ms",1000+i*100); break;
            case "previous_operation": frames.get(0).put("captured_elapsed_ms",999); break;
            case "future_capture": frames.get(5).put("captured_elapsed_ms",4001); break;
            case "fractional_frame": frames.get(0).put("frame_id",1.5); break;
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
        actual=args[0].startsWith("cleanup_") ? PresentationAcceptance.cleanupSafe(cleanup)
            : PresentationAcceptance.surfaceAccepted(frames,SESSION,1000,4000,120);
        if(actual!=expected) throw new AssertionError(args[0]+" expected="+expected+" actual="+actual);
    }
}
'''


class PresentationAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='coh-presentation-gate-')
        harness = Path(cls.tmp.name) / 'PresentationAcceptanceHost.java'
        harness.write_text(FIXTURE)
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', cls.tmp.name, str(SOURCE), str(harness)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_frame_boundaries(self):
        for mode in ('valid', 'last_producer_frame', 'stale_session', 'missing_pixelcopy',
                     'duplicate_frame', 'zero_frame', 'beyond_producer', 'short_span',
                     'previous_operation', 'future_capture', 'fractional_frame', 'fractional_time'):
            with self.subTest(mode=mode): self.execute(mode)

    def test_cleanup_boundaries(self):
        for mode in ('cleanup_valid', 'cleanup_missing', 'cleanup_orphan', 'cleanup_unreadable',
                     'cleanup_capture_live', 'cleanup_child_omitted', 'cleanup_no_guest'):
            with self.subTest(mode=mode): self.execute(mode)

    def execute(self, mode):
        subprocess.run(['java', '-cp', self.tmp.name,
                        'io.github.russianranger.cohpresentation.PresentationAcceptanceHost', mode],
                       check=True, capture_output=True, timeout=10)


if __name__ == '__main__': unittest.main()
