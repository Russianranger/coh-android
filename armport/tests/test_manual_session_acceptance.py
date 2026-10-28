"""Run the shipped Java policy against the actual guest's emitted stage flags."""
import ast
import json
from pathlib import Path
import re
import subprocess
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[2]
JAVA = ROOT / 'android/interactive/src/main/java/io/github/russianranger/cohclientinteractive'


def guest_stage(manual, reason='finish_requested'):
    source = ROOT / 'android/guest/client_interactive_diagnostic.py'
    tree = ast.parse(source.read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and any(key.arg == 'bounded_live_observation' for key in node.keywords)]
    assert len(calls) == 1, 'Expected the actual final interaction-stage publication'
    owner = SimpleNamespace(MANUAL_SESSION=manual,
                            ctx=SimpleNamespace(passed=lambda **fields: fields))
    return eval(compile(ast.Expression(calls[0]), str(source), 'eval'),
                {'self': owner, 'evidence': {'stage': 'actual_client_interaction', 'status': 'passed'},
                 'reason': reason})


def java_map(value):
    def literal(item):
        if isinstance(item, bool):
            return 'Boolean.TRUE' if item else 'Boolean.FALSE'
        return json.dumps(item)
    return 'map(' + ','.join(literal(item) for pair in value.items() for item in pair) + ')'


HARNESS = r'''
package io.github.russianranger.cohclientinteractive;
import java.util.*;
public final class ManualSessionAcceptanceHost {
    static Map<String,Object> map(Object... items) {
        Map<String,Object> result = new LinkedHashMap<>();
        for (int i=0;i<items.length;i+=2) result.put((String)items[i],items[i+1]);
        return result;
    }
    static Object jsonValue(Object value) { return value; }
    public static void main(String[] args) {
        boolean reopen = Boolean.parseBoolean(args[0]);
        Map<String,Object> startup = reopen ? MANUAL : BOUNDED;
        switch(args[1]) {
            case "valid": break;
            case "missing": startup.remove(args[2]); break;
            case "string": startup.put(args[2], "true"); break;
            case "invert": startup.put(args[2], !Boolean.TRUE.equals(startup.get(args[2]))); break;
            case "timeout": startup.put("interaction_completion_reason", "interaction_timeout"); break;
            case "failed": startup.put("status", "failed"); break;
            case "wrong_stage": startup.put("stage", "actual_client_startup"); break;
            case "old_guard":
                // The old Runtime condition rejected a valid manual-stage publication.
                System.out.print(Boolean.TRUE.equals(startup.get("bounded_live_observation"))); return;
            default: throw new AssertionError(args[1]);
        }
        System.out.print(RUNTIME_POLICY_CALL);
    }
}
'''


class ManualSessionAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        runtime = (JAVA / 'ClientRuntime.java').read_text()
        calls = re.findall(r'ClientAcceptance\.clientInteractionPolicyAccepted\(jsonValue\(startup\), reopen\)', runtime)
        assert len(calls) == 1, 'Runtime must use the tested policy with its selected operation'
        cls.tmp = tempfile.TemporaryDirectory(prefix='armport-manual-policy-')
        harness = Path(cls.tmp.name) / 'ManualSessionAcceptanceHost.java'
        harness.write_text(HARNESS.replace('MANUAL', java_map(guest_stage(True)))
                           .replace('BOUNDED', java_map(guest_stage(False)))
                           .replace('RUNTIME_POLICY_CALL', calls[0]))
        subprocess.run(['java', '-m', 'jdk.compiler/com.sun.tools.javac.Main', '--release', '8',
                        '-d', cls.tmp.name, str(JAVA / 'ClientAcceptance.java'), str(harness)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def check(self, manual, mutation='valid', field='', expected=False):
        result = subprocess.run(['java', '-cp', self.tmp.name,
            'io.github.russianranger.cohclientinteractive.ManualSessionAcceptanceHost',
            str(manual).lower(), mutation, field], check=True, capture_output=True, text=True)
        self.assertEqual(result.stdout, str(expected).lower())

    def test_real_guest_flags_accept_creation_and_manual_reopen(self):
        tree = ast.parse((ROOT / 'android/guest/character_reopen_diagnostic.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == 'CharacterReopenDiagnostic')
        manual = next(node.value for node in cls.body if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'MANUAL_SESSION' for t in node.targets))
        self.assertIs(ast.literal_eval(manual), True)
        for selected in (False, True):
            with self.subTest(manual=selected): self.check(selected, expected=True)
        self.check(True, 'old_guard', expected=False)
        self.check(False, 'old_guard', expected=True)

    def test_each_policy_flag_is_required_and_typed(self):
        for manual in (False, True):
            for field in ('bounded_live_observation', 'user_controlled_observation',
                          'interaction_session_completed', 'input_effect_verified'):
                for mutation in ('missing', 'string', 'invert'):
                    with self.subTest(manual=manual, field=field, mutation=mutation):
                        self.check(manual, mutation, field)

    def test_manual_needs_explicit_finish_bounded_creation_keeps_timeout(self):
        self.check(True, 'timeout')
        self.check(False, 'timeout', expected=True)
        for manual in (False, True):
            self.check(manual, 'missing', 'interaction_completion_reason')

    def test_only_successful_interaction_stage_is_eligible(self):
        for manual in (False, True):
            for mutation in ('failed', 'wrong_stage'):
                with self.subTest(manual=manual, mutation=mutation):
                    self.check(manual, mutation)


if __name__ == '__main__':
    unittest.main()
