#!/usr/bin/env python3
"""Replay the device's stage contract against the production Java validator."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
JAVA_ROOT = ROOT/'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'
FIXTURE_PATH = Path(__file__).parent/'fixtures/client-stage-0.13.7.json'
VISUAL_PINS = ('client_visual_assets.py', 'client_animation_package.py',
               'client-visual-assets.zip', 'client-visual-manifest.json')
ANIMATION_PINS = ('server-animations.pigg', 'server-animation-manifest.json')


def java_value(value):
    if isinstance(value, dict):
        return 'map('+','.join(java_value(item) for pair in value.items() for item in pair)+')'
    if isinstance(value, list):
        return 'new ArrayList<Object>(Arrays.asList('+','.join(map(java_value, value))+'))'
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=True)
    if isinstance(value, bool):
        return 'Boolean.TRUE' if value else 'Boolean.FALSE'
    if value is None:
        return 'null'
    if isinstance(value, int):
        return str(value)+'L'
    raise AssertionError('Unexpected fixture type: '+repr(value))


HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
public final class ClientStageAcceptanceHost {
    static Map<String,Object> map(Object... values) {
        Map<String,Object> result = new LinkedHashMap<>();
        for (int i=0;i<values.length;i+=2) result.put((String)values[i],values[i+1]);
        return result;
    }
    @SuppressWarnings("unchecked") public static void main(String[] args) {
        List<Object> stages = STAGES;
        Map<String,Object> pins = PINS;
        Object stageValue = stages, pinValue = pins;
        String mode = args[0];
        if (mode.startsWith("historical")) {
            stages.remove(10); stages.remove(9);
            for (String name : new String[]{"client_visual_assets.py", "client_animation_package.py",
                    "client-visual-assets.zip", "client-visual-manifest.json"}) pins.remove(name);
        }
        if (mode.equals("missing")) stages.remove(Integer.parseInt(args[1]));
        if (mode.equals("failed") || mode.equals("historical_failed"))
            ((Map<String,Object>)stages.get(Integer.parseInt(args[1]))).put("status", "failed");
        if (mode.equals("wrong_status"))
            ((Map<String,Object>)stages.get(Integer.parseInt(args[1]))).put("status", Boolean.TRUE);
        if (mode.equals("reordered") || mode.equals("historical_reordered"))
            Collections.swap(stages, Integer.parseInt(args[1]), Integer.parseInt(args[1])+1);
        if (mode.equals("duplicate")) stages.set(Integer.parseInt(args[1]), stages.get(0));
        if (mode.equals("extra") || mode.equals("historical_extra"))
            stages.add(map("stage", "extra", "status", "passed"));
        if (mode.equals("foreign"))
            ((Map<String,Object>)stages.get(Integer.parseInt(args[1]))).put("stage", "foreign_stage");
        if (mode.equals("stage_not_map")) stages.set(Integer.parseInt(args[1]), "passed");
        if (mode.equals("null_stages")) stageValue = null;
        if (mode.equals("not_list")) stageValue = map("stage", "passed");
        if (mode.equals("null_pins")) pinValue = null;
        if (mode.equals("not_map")) pinValue = stages;
        if (mode.equals("partial_bundle") || mode.equals("missing_animation")) pins.remove(args[1]);
        if (mode.equals("short_guest_claim")) { stages.remove(10); stages.remove(9); }
        if (mode.equals("historical_visual_stages")) {
            stages.add(9, map("stage", "client_visual_assets", "status", "passed"));
            stages.add(10, map("stage", "client_animation_pack", "status", "passed"));
        }
        if (mode.equals("bad_pin")) {
            Map<String,Object> pin = (Map<String,Object>) pins.get(args[1]);
            switch(args[2]) {
                case "zero": pin.put("bytes", 0L); break;
                case "negative": pin.put("bytes", -1L); break;
                case "fraction": pin.put("bytes", 1.5); break;
                case "string": pin.put("bytes", "10"); break;
                case "boolean": pin.put("bytes", Boolean.TRUE); break;
                case "missing_bytes": pin.remove("bytes"); break;
                case "missing_hash": pin.remove("sha256"); break;
                case "uppercase": pin.put("sha256", ((String)pin.get("sha256")).toUpperCase(Locale.ROOT)); break;
                case "short_hash": pin.put("sha256", "a"); break;
                case "wrong_type": pins.put(args[1], "passed"); break;
                default: throw new AssertionError(args[2]);
            }
        }
        System.out.print(ClientAcceptance.clientInteractionStageIndex(stageValue, pinValue));
    }
}
'''


class ClientStageAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE_PATH.read_text())
        cls.tmp = tempfile.TemporaryDirectory(prefix='coh-client-stage-')
        harness = Path(cls.tmp.name)/'ClientStageAcceptanceHost.java'
        harness.write_text(HARNESS.replace('STAGES', java_value(cls.fixture['stages']))
                           .replace('PINS', java_value(cls.fixture['files'])))
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', cls.tmp.name, str(JAVA_ROOT/'ClientAcceptance.java'), str(harness)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def execute(self, mode, *values, expected=-1):
        result = subprocess.run(['java', '-cp', self.tmp.name,
            'io.github.russianranger.cohclientinteractive.ClientStageAcceptanceHost', mode,
            *map(str, values)], check=True, capture_output=True, text=True)
        self.assertEqual(int(result.stdout), expected)

    def test_actual_0_13_7_device_report_stage_and_payload_replay(self):
        self.assertEqual(len(self.fixture['files']), 56)
        self.assertEqual(len(self.fixture['stages']), 14)
        self.assertEqual(self.fixture['guest_report_sha256'],
                         '9153fe0f178ab16c3598ccced6885d88b55007957a28814d608c3c321ef1f889')
        self.execute('current', expected=13)

    def test_exact_historical_contract(self):
        self.execute('historical', expected=11)

    def test_every_required_stage_must_be_present(self):
        for i in range(14):
            with self.subTest(stage=i): self.execute('missing', i)

    def test_every_required_stage_must_pass(self):
        for i in range(14):
            with self.subTest(stage=i): self.execute('failed', i)

    def test_historical_stage_status_still_required(self):
        for i in range(12):
            with self.subTest(stage=i): self.execute('historical_failed', i)

    def test_status_boolean_does_not_replace_passed_string(self):
        for i in range(14):
            with self.subTest(stage=i): self.execute('wrong_status', i)

    def test_stage_order_is_exact(self):
        for i in range(13):
            with self.subTest(stage=i): self.execute('reordered', i)

    def test_historical_order_is_exact(self):
        for i in range(11):
            with self.subTest(stage=i): self.execute('historical_reordered', i)

    def test_no_foreign_or_duplicate_stage(self):
        for i in range(14):
            with self.subTest(stage=i): self.execute('foreign', i)
        for i in range(1, 14):
            with self.subTest(duplicate=i): self.execute('duplicate', i)

    def test_no_unexpected_additional_stage(self):
        self.execute('extra'); self.execute('historical_extra')

    def test_apk_pins_require_both_new_stages(self):
        self.execute('short_guest_claim')

    def test_historical_pins_cannot_accept_unverified_visual_stages(self):
        self.execute('historical_visual_stages')

    def test_partial_visual_bundle_fails_closed(self):
        for name in VISUAL_PINS:
            with self.subTest(pin=name): self.execute('partial_bundle', name)

    def test_visual_bundle_requires_both_stock_animation_pins(self):
        for name in ANIMATION_PINS:
            with self.subTest(pin=name): self.execute('missing_animation', name)

    def test_preparation_pins_are_well_formed(self):
        for name in VISUAL_PINS + ANIMATION_PINS:
            for malformed in ('zero', 'negative', 'fraction', 'string', 'boolean',
                              'missing_bytes', 'missing_hash', 'uppercase', 'short_hash', 'wrong_type'):
                with self.subTest(pin=name, malformed=malformed):
                    self.execute('bad_pin', name, malformed)

    def test_stage_and_pin_types_fail_closed(self):
        for mode in ('null_stages', 'not_list', 'null_pins', 'not_map'):
            with self.subTest(mode=mode): self.execute(mode)
        for i in range(14):
            with self.subTest(stage=i): self.execute('stage_not_map', i)

    def test_caller_retains_session_identity_surface_and_cleanup_validation(self):
        source = (JAVA_ROOT/'ClientRuntime.java').read_text()
        body = source.split('private boolean guestAccepted(JSONObject report)', 1)[1].split(
            'private ', 1)[0]
        self.assertIn('jsonValue(stages), jsonValue(clientPins)', body)
        self.assertIn('stages.getJSONObject(interactionStage)', body)
        self.assertNotIn('stages.getJSONObject(11)', body)
        for proof in ('bounded_live_observation', 'ClientAcceptance.cleanupSafe',
                      'ClientAcceptance.characterReopenVerified', 'ClientAcceptance.characterCreationVerified',
                      'ClientAcceptance.clientWindowAccepted', 'asset_sha256', 'receipt_sha256',
                      'distinct_colors_capped', 'presentation_socket_removed',
                      'client_main_loop_reached', 'client-startup.ppm', 'client-observed.ppm'):
            self.assertIn(proof, body)
        self.assertIn('ClientAcceptance.surfaceAccepted(surfaceSamples, session', source)
        self.assertIn('ClientAcceptance.characterReopenAccepted(jsonValue(report)', source)


if __name__ == '__main__': unittest.main()
