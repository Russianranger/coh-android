#!/usr/bin/env python3
"""Package a focused startup/cache and buffered-RFB derivative of the exact 0.11.3 APK.

The retained native backend, world, avatar, normal-save/ground proof and bounded
session policy stay unchanged. Host fixtures establish work/read-call reduction;
physical startup duration, native FPS and the next exterior reopen remain pending.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[3]
REPOSITORY = "Russianranger/coh-android"
BRANCH = "codex/character-persistence-continuation"
DONOR_COMMIT = "97565b0c28ba27ef79e70d4c04dddb1a8383ec1f"
DONOR_RUN_ID = 37015136168
DONOR_APK_NAME = "COH-Atlas-Gameplay-0.11.3.apk"
DONOR_APK = {"bytes": 595108273, "sha256": "3c97d5c85092ec9aec88de405cea92a91c760db379cdbf66a244714687f35dfd"}
DONOR_BUILD = {"bytes": 57142, "sha256": "4967e83deff3da231c4bfd3e0f6aa4d83b29669e6b014051c1dd0b196b08a248"}
DONOR_URL = "https://github.com/" + REPOSITORY + "/releases/download/coh-atlas-gameplay-v0.11.3/" + DONOR_APK_NAME
AVATAR_COMMIT = "34b763a5518e3fa3740c197c0e824c17da088536"
AVATAR_RUN_ID = 36944389469
AVATAR_APK = {"bytes": 595104089, "sha256": "f4e30c728046771cb91beece46fb54663b0fcd57a28b8e055f6fc8918dd3c899"}
AVATAR_BUILD = {"bytes": 34498, "sha256": "993417b3c18902f73cc27f3068b5b309a4784177b80349877028586bc8476904"}
RETAINED_SOURCE_COMMIT = "1649e807d2b2310170e775c53bafa24cd932638a"
RETAINED_SOURCE_RUN_ID = 36937373454
RETAINED_SOURCE_BUILD = {"bytes": 45992, "sha256": "cc0ad0f09bf06f598e6f65e706260fa9bb1a90e699ad1794d9df9ff1625d1d00"}
RETAINED_SOURCE_APK = {"bytes": 595099993, "sha256": "e3a0760d23ef57747343ee8fd0c76e68a92194df040062266f3dc282cd15a924"}
SIGNER = "92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282"
VERSION_NAME, VERSION_CODE = "0.11.4", 10
APK_NAME = "COH-Atlas-Gameplay-0.11.4.apk"
REPORT_NAME = "startup-perf-apk-build-report.json"
NOTES_NAME = "COH-Atlas-Gameplay-0.11.4-testing.txt"
RELEASE_TAG = "coh-atlas-gameplay-v0.11.4"
NOTES = ROOT / "docs" / NOTES_NAME
HELPERS = frozenset(("local_character_server.py", "character_creation_diagnostic.py",
                    "client_interactive_diagnostic.py", "character_reopen_diagnostic.py"))
GUEST_ADDITION = "character_server_data_cache.py"
ALLOWED_PAYLOADS = frozenset("assets/runtime/" + name for name in
    (*HELPERS, "client-manifest.json", "runtime-manifest.json"))
REQUIRED_PAYLOADS = frozenset("assets/runtime/" + name for name in
    ("local_character_server.py", "character_creation_diagnostic.py", "client-manifest.json", "runtime-manifest.json"))
ADDED_PAYLOADS = frozenset(("assets/runtime/" + GUEST_ADDITION,))
JAVA_ROOT = "android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/"
JAVA_CHANGES = frozenset((JAVA_ROOT + "InteractiveRfbClient.java",))
QUALIFICATION_SCOPE = "startup_cache_readiness_and_buffered_rfb_input"
QUALIFICATION_SCRIPT = "tools/android/interactive/qualify_startup_perf.py"
WORKFLOW = ".github/workflows/android-startup-perf.yml"
CHECKS = ("cache_isolation_and_reuse_regressions_passed", "readiness_and_log_boundaries_preserved",
          "buffered_rfb_equivalence_verified", "ground_save_and_budget_guards_preserved",
          "retained_donor_boundaries_preserved")
SOURCE_FILES = frozenset((*('android/guest/' + name for name in HELPERS),
    'android/guest/' + GUEST_ADDITION, *JAVA_CHANGES, QUALIFICATION_SCRIPT, WORKFLOW,
    'tools/android/interactive/build_startup_perf_apk.py', 'tools/android/interactive/test_startup_perf_package.py',
    'tools/android/interactive/build_session_window_apk.py', 'tools/android/interactive/build_apk.py',
    'tools/android/interactive/build_atlas_gameplay_apk.py', 'tools/android/interactive/qualify_session_window.py',
    'tools/android/interactive/test_server_worktree_reuse.py', 'tools/android/interactive/test_character_readiness.py',
    'tools/android/interactive/test_rfb_buffered_input.py', 'tools/android/interactive/test_input.py',
    'tools/android/presentation/test_rfb.py', 'tools/android/interactive/test_session_budget_guest.py',
    'tools/android/interactive/test_session_budget_java.py', 'tools/android/interactive/test_character_reopen_guest.py',
    'tools/android/interactive/test_ground_repair.py', 'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.log',
    'tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.json'))
SOURCE_FILES |= frozenset((*(JAVA_ROOT + name + '.java' for name in (
    'ClientAcceptance', 'ClientActivity', 'ClientInput', 'ClientRuntime', 'ClientService',
    'ClientSessionBudget', 'ClientSurface', 'InteractiveRfbClient')),
    'android/atlas/src/main/java/io/github/russianranger/cohatlas/AtlasAssetImporter.java',
    *('android/app/src/main/java/io/github/russianranger/cohdiagnostic/' + name + '.java' for name in (
        'TarExtractor', 'DeviceHosts', 'DiagnosticOutcome', 'DiagnosticReports',
        'CleanupGuard', 'DiagnosticRuntime', 'DbServerAcceptance')),
    'android/interactive/src/main/AndroidManifest.xml', 'android/native/client-launcher.c',
    'android/interactive/src/main/res/drawable/ic_coh_client.xml',
    'tools/android/interactive/classify_interactive_change.py',
    'tools/android/interactive/test_classify_interactive_change.py',
    'tools/android/interactive/test_session_window_package.py',
    'tools/android/interactive/fixtures/session-window-0.11.3-client_interactive_diagnostic.py',
    'tools/android/interactive/fixtures/session-window-0.11.3-character_reopen_diagnostic.py',
    'docs/COH-Atlas-Gameplay-0.11.4-testing.txt'))


def require(value, message):
    if not value:
        raise ValueError(message)


def builder(*, repaired=False):
    spec = importlib.util.spec_from_file_location("coh_session_window_base", Path(__file__).with_name("build_apk.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if repaired:
        module.VERSION_NAME, module.VERSION_CODE, module.APK_NAME = VERSION_NAME, VERSION_CODE, APK_NAME
    return module


def read_json(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and 0 < path.stat().st_size <= 8 * 1024 * 1024,
            "Missing, linked or oversized metadata: " + path.name)
    return json.loads(path.read_text())


def donor_link():
    return {"run_id": DONOR_RUN_ID, "repository_commit": DONOR_COMMIT,
            "apk": DONOR_APK, "build_report": DONOR_BUILD}


def session_builder():
    spec = importlib.util.spec_from_file_location("coh_retained_session", Path(__file__).with_name("build_session_window_apk.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_donor_receipt(report):
    prior = session_builder()
    require(report.get("format") == 1 and report.get("apk") == DONOR_APK_NAME
            and report.get("repository_commit") == DONOR_COMMIT
            and {key: report.get(key) for key in DONOR_APK} == DONOR_APK
            and report.get("application_id") == builder().APP_ID
            and report.get("version_name") == "0.11.3" and report.get("version_code") == 9
            and report.get("abi") == "arm64-v8a" and report.get("signer_certificate_sha256") == SIGNER
            and report.get("signing_key_created") is False
            and all(report.get(key) is True for key in ("signature_verified", "package_badging_verified", "payload_bytes_verified",
                "java_or_dex_recompiled", "unrelated_java_sources_preserved", "guest_source_derivative_scope_verified"))
            and all(report.get(key) is False for key in ("native_libraries_changed", "client_or_server_recompiled", "world_assets_changed", "physical_gameplay_validated"))
            and set(report.get("replaced_apk_payloads", [])) == prior.CHANGED_PAYLOADS
            and set(report.get("added_apk_payloads", [])) == prior.ADDED_PAYLOADS
            and set(report.get("changed_apk_payloads", [])) == prior.CHANGED_PAYLOADS | prior.ADDED_PAYLOADS
            and report.get("donor") == prior.donor_link()
            and report.get("retained_source_report") == {"run_id": RETAINED_SOURCE_RUN_ID,
                "repository_commit": RETAINED_SOURCE_COMMIT, **RETAINED_SOURCE_BUILD},
            "Exact published retained-signer 0.11.3 donor receipt differs")
    require(report.get("recompiled_dex") and len(report.get("java_sources", {})) == 16
            and len(report.get("payloads", {})) == 49
            and set(report.get("retained_android_resources", {})) ==
            {"resources.arsc", "res/drawable/ic_coh_client.xml"}, "Donor shell or source byte pins are incomplete")
    proof = report.get("qualification", {})
    require(proof.get("scope") == prior.QUALIFICATION_SCOPE and proof.get("repository_commit") == DONOR_COMMIT
            and proof.get("status") == "passed" and proof.get("policy") == POLICY
            and proof.get("physical_gameplay_validated") is False,
            "Published donor was not the qualified startup-perf package")


def validate_lineage(report_path, ground_report, avatar_report, retained_source_report):
    """Authenticate the retained 0.11.3 -> 0.11.2 -> 0.11.1 -> 0.11.0 chain."""
    base, prior = builder(), session_builder()
    base.checked_file(report_path, DONOR_BUILD)
    ground = prior.validate_lineage(ground_report, avatar_report, retained_source_report)
    donor = read_json(report_path)
    validate_donor_receipt(donor)
    require(set(donor['payloads']) == set(ground['payloads']) | prior.ADDED_PAYLOADS
            and {name for name in ground['payloads'] if ground['payloads'][name] != donor['payloads'][name]} == prior.CHANGED_PAYLOADS
            and donor.get('donor_dex') == ground.get('retained_dex')
            and donor.get('retained_android_resources') == ground.get('retained_android_resources')
            and donor.get('source_manifest') == ground.get('source_manifest'),
            "Published startup-perf donor does not retain its authenticated backend")
    return donor


def current_java_sources(donor, generated):
    """Retain the full sixteen-source authored closure; only RFB buffering changes."""
    base = builder()
    sources = base.java_sources(ROOT / "android/interactive/src/main", generated)
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources
            if path.is_relative_to(ROOT) and not path.is_relative_to(generated)}
    original = donor["java_sources"]
    require(set(pins) == set(original), "Unexpected Java source addition or omission")
    changed = {name for name in original if original[name] != pins[name]}
    require(changed == JAVA_CHANGES, "Java changes exceed the reviewed bounded RFB input wrapper")
    for name, pin in donor["preserved_sources"].items():
        if name not in JAVA_CHANGES:
            base.checked_file(ROOT / name, pin)
    base.checked_file(ROOT / "android/interactive/src/main/AndroidManifest.xml", donor["source_manifest"])
    return sources, pins, sorted(changed)


def validate_rfb_scope(source, donor_pin):
    """Reverse only the exact reviewed import, comment and 64KiB input wrapper."""
    addition = b'import java.io.BufferedInputStream;\n'
    before = b'        this.input = new DataInputStream(input);\n'
    after = (b'        // Raw rectangles arrive row by row. Bound read-ahead so those small\n'
             b'        // decoder reads do not each require a local-socket read.\n'
             b'        this.input = new DataInputStream(new BufferedInputStream(input, 64 * 1024));\n')
    require(source.count(addition) == 1 and source.count(after) == 1,
            "Reviewed RFB input wrapper differs")
    original = source.replace(addition, b'', 1).replace(after, before, 1)
    require({'bytes': len(original), 'sha256': hashlib.sha256(original).hexdigest()} == donor_pin,
            "RFB source changed outside the exact bounded input wrapper")


def validate_donor(apk, report_path, ground_report, avatar_report, retained_source_report):
    base = builder()
    base.checked_file(apk, DONOR_APK)
    report = validate_lineage(report_path, ground_report, avatar_report, retained_source_report)
    base.verify_packaged_payloads(apk, report["payloads"])
    with zipfile.ZipFile(apk) as archive:
        retained = {"classes.dex": report["recompiled_dex"], **report["retained_android_resources"]}
        require({name for name in archive.namelist() if not name.startswith("META-INF/")} ==
                set(report["payloads"]) | set(retained) | {"AndroidManifest.xml"}, "Unexpected donor APK member")
        for name, expected in retained.items():
            with archive.open(name) as source:
                size, digest = base.stream_digest(source)
            require({"bytes": size, "sha256": digest} == expected, "Retained donor shell bytes differ")
    return report


def verify_derivative(apk, donor, payloads, dex_pin):
    """Enforce four guest/manifest replacements, one compiled DEX and retained resources."""
    base = builder()
    require(set(payloads) == set(donor["payloads"]) | ADDED_PAYLOADS
            and {name for name in donor["payloads"] if payloads[name] != donor["payloads"][name]} >= REQUIRED_PAYLOADS
            and {name for name in donor["payloads"] if payloads[name] != donor["payloads"][name]} <= ALLOWED_PAYLOADS,
            "Startup performance derivative payload boundary differs")
    require(dex_pin != donor["recompiled_dex"], "Buffered RFB DEX was not revised")
    base.checked_pin(dex_pin)
    base.verify_packaged_payloads(apk, payloads)
    retained = donor["retained_android_resources"]
    with zipfile.ZipFile(apk) as archive:
        require({name for name in archive.namelist() if not name.startswith("META-INF/")} ==
                set(payloads) | set(retained) | {"AndroidManifest.xml", "classes.dex"}, "Unexpected startup performance APK member")
        for name, pin in {"classes.dex": dex_pin, **retained}.items():
            with archive.open(name) as source:
                size, digest = base.stream_digest(source)
            require({"bytes": size, "sha256": digest} == pin, "Recompiled DEX or retained Android resources differ")


POLICY = {"menu_seconds": 1200, "connected_seconds": 1200, "launcher_cap_seconds": 2040,
          "overall_reserve_seconds": 120, "recovery_age_ms": 600000, "save_request_age_ms": 420000,
          "neutral_reserve_ms": 60000, "save_proof_reserve_ms": 180000}


def validate_qualification(receipt, commit):
    base = builder()
    require(receipt.get("format") == 1 and receipt.get("status") == "passed"
            and receipt.get("scope") == QUALIFICATION_SCOPE and receipt.get("repository_commit") == commit
            and receipt.get("donor_apk_sha256") == DONOR_APK["sha256"]
            and receipt.get("physical_gameplay_validated") is False and receipt.get("native_runtime_booted") is False and receipt.get("policy") == POLICY,
            "Focused startup/cache qualification for this exact commit and policy is required")
    files = receipt.get("source_files", {})
    require(SOURCE_FILES <= set(files), "Startup qualification source closure is incomplete")
    for name, pin in files.items():
        require(isinstance(name, str) and Path(name).as_posix() == name and not Path(name).is_absolute()
                and ".." not in Path(name).parts and "\\" not in name, "Unsafe qualification source path")
        base.checked_file(ROOT / name, pin)
    require(type(receipt.get("tests_run")) is int and receipt["tests_run"] >= 20,
            "Focused startup/cache regression coverage is incomplete")
    require(set(receipt.get("checks", {})) == set(CHECKS)
            and all(receipt["checks"][name] is True for name in CHECKS), "Startup performance safety checks are incomplete")
    return receipt


def repair_manifests(runtime, client, helper_pins, client_pin, commit):
    """Revise only reviewed helper verification pins and add the cache module."""
    require(set(helper_pins) == HELPERS | {GUEST_ADDITION}, "Unexpected startup/cache helper inventory")
    revised_client = copy.deepcopy(client)
    require(HELPERS <= set(revised_client.get("files", {})) and GUEST_ADDITION not in revised_client["files"],
            "Donor client helper pins differ")
    revised_client["files"].update(helper_pins)
    revised_runtime = copy.deepcopy(runtime)
    require(HELPERS | {"client-manifest.json"} <= set(revised_runtime.get("files", {}))
            and GUEST_ADDITION not in revised_runtime["files"], "Donor runtime helper pins differ")
    revised_runtime["files"].update(helper_pins)
    revised_runtime["files"]["client-manifest.json"] = client_pin
    revised_runtime["repository_commit"] = commit
    revised_runtime["scope"] = ("Published 0.11.3 backend with isolated server-data reuse, bounded readiness reads and RFB buffering; "
                                "physical startup duration, native FPS and exterior reopen remain pending")
    return revised_runtime, revised_client


GUEST_BODIES = {
    'local_character_server.py': {'LocalCharacterServer.prepare_runtime',
        'LocalCharacterServer.stage_map_data', 'LocalCharacterServer.collect_server_logs'},
    'client_interactive_diagnostic.py': {'ClientInteractiveDiagnostic.execute'},
    'character_reopen_diagnostic.py': {'CharacterReopenDiagnostic.observe_console'},
    'character_creation_diagnostic.py': set(),
}
GUEST_ADDITIONS = {
    'local_character_server.py': {
        'LocalCharacterServer.cleanup_config': 'self',
        'LocalCharacterServer.server_log_paths': 'self',
        'LocalCharacterServer.current_logs': 'self'},
    'client_interactive_diagnostic.py': {'ClientInteractiveDiagnostic.record_observer_timing': 'self,name,started'},
    'character_reopen_diagnostic.py': {}, 'character_creation_diagnostic.py': {},
}


def validate_guest_scope(name, old, new):
    """Preserve every unapproved method and module byte outside reviewed edits.

    Approved existing bodies have fixed decorators/signatures except the one
    optional staging recorder. Module/class skeletons and unapproved functions
    remain exact. Added imports/methods and the creation inventory are explicit.
    """
    require(name in GUEST_BODIES, 'Unapproved startup guest helper')
    old_text, new_text = old.decode('utf-8'), new.decode('utf-8')
    old_tree, new_tree = ast.parse(old_text), ast.parse(new_text)
    def functions(tree):
        result = {}
        def walk(body, prefix=''):
            for node in body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    key = prefix + node.name
                    require(key not in result, 'Duplicate guest function: ' + key)
                    result[key] = node
                elif isinstance(node, ast.ClassDef):
                    walk(node.body, prefix + node.name + '.')
        walk(tree.body)
        return result
    old_functions, new_functions = functions(old_tree), functions(new_tree)
    additions = set(new_functions) - set(old_functions)
    require(set(old_functions) <= set(new_functions) and additions <= set(GUEST_ADDITIONS[name]),
            'Guest function addition or omission exceeds startup scope')
    def raw(text, node):
        lines = text.splitlines(keepends=True)
        first = min([node.lineno] + [item.lineno for item in getattr(node, 'decorator_list', [])])
        return ''.join(lines[first - 1:node.end_lineno])
    def signature(node):
        result = copy.deepcopy(node)
        result.body = [ast.Pass()]
        return ast.dump(result, include_attributes=False)
    for key, original in old_functions.items():
        current = new_functions[key]
        candidate = copy.deepcopy(current)
        if key == 'LocalCharacterServer.stage_map_data' and name == 'local_character_server.py':
            if len(candidate.args.kwonlyargs) == len(original.args.kwonlyargs) + 1:
                require(candidate.args.kwonlyargs[-1].arg == 'cache_recorder'
                        and isinstance(candidate.args.kw_defaults[-1], ast.Constant)
                        and candidate.args.kw_defaults[-1].value is None,
                        'Staging recorder must be an optional None keyword')
                candidate.args.kwonlyargs.pop()
                candidate.args.kw_defaults.pop()
        require(signature(original) == signature(candidate), 'Guest function signature/decorator differs: ' + key)
        if key == 'LocalCharacterServer.stage_map_data' and name == 'local_character_server.py':
            restored = raw(new_text, current).replace(', cache_recorder=None', '', 1)
            for addition, anchor in (
                ('                if cache_recorder is not None:\n'
                 '                    cache_recorder.observe(relative, destination, None, private)\n',
                 '                destination.mkdir(parents=True, exist_ok=True, mode=0o700)\n'),
                ('                if cache_recorder is not None:\n'
                 '                    cache_recorder.observe(relative, destination, resolved, private)\n',
                 '                private = private or current.suffix.casefold()'),
            ):
                require(restored.count(addition) <= 1
                        and (anchor not in raw(old_text, original) or restored.count(addition) == 1),
                        'Staging observation differs from the reviewed fallback-preserving insertion')
                restored = restored.replace(addition, '', 1)
            require(restored == raw(old_text, original),
                    'Staging fallback validation or filesystem operations changed')
        if key not in GUEST_BODIES[name]:
            require(raw(old_text, original) == raw(new_text, current),
                    'Unapproved guest function source differs: ' + key)
    for key in additions:
        current = new_functions[key]
        expected = ast.parse('def added(' + GUEST_ADDITIONS[name][key] + '):\n    pass\n').body[0]
        current = copy.deepcopy(current)
        current.name = 'added'
        require(signature(current) == signature(expected), 'Added observer/cache signature differs: ' + key)
    old_imports = {ast.dump(node, include_attributes=False) for node in old_tree.body
                   if isinstance(node, (ast.Import, ast.ImportFrom))}
    allowed_import = {
        'local_character_server.py': 'import character_server_data_cache as server_data_cache',
        'character_reopen_diagnostic.py': 'import copy',
    }.get(name)
    allowed_import = ast.dump(ast.parse(allowed_import).body[0], include_attributes=False) if allowed_import else None
    masks = {'old': [], 'new': []}
    def standalone(tree, node):
        require(not any(other is not node and other.lineno <= node.end_lineno and other.end_lineno >= node.lineno
                        for other in tree.body), 'Allowed guest addition shares a line with another statement')
    for side, tree, text, mapping in (('old', old_tree, old_text, old_functions),
                                      ('new', new_tree, new_text, new_functions)):
        for key, node in mapping.items():
            if key in GUEST_BODIES[name] or key in additions:
                first = min([node.lineno] + [item.lineno for item in node.decorator_list])
                masks[side].append((first, node.end_lineno, '' if key in additions else '# reviewed-body:' + key + '\n'))
        to_remove = []
        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                dump = ast.dump(node, include_attributes=False)
                if side == 'new' and dump not in old_imports:
                    require(dump == allowed_import, 'Unapproved guest import')
                    standalone(tree, node)
                    masks[side].append((node.lineno, node.end_lineno, ''))
                    to_remove.append(node)
            elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                key = node.targets[0].id
                if name == 'character_creation_diagnostic.py' and key == 'REQUIRED':
                    standalone(tree, node)
                    if side == 'new':
                        values = [item for item in ast.walk(node.value)
                                  if isinstance(item, ast.Set)]
                        require(len(values) == 1 and sum(isinstance(item, ast.Constant) and item.value == GUEST_ADDITION
                                                        for item in values[0].elts) == 1,
                                'Creation inventory must add exactly the startup cache helper')
                        values[0].elts = [item for item in values[0].elts
                                         if not isinstance(item, ast.Constant) or item.value != GUEST_ADDITION]
                    masks[side].append((node.lineno, node.end_lineno, '# reviewed-creation-inventory\n'))
                elif side == 'new' and name == 'client_interactive_diagnostic.py' and key == 'PROGRESS_POLL_SECONDS':
                    require(isinstance(node.value, ast.Constant) and type(node.value.value) is int and node.value.value == 5,
                            'Readiness cadence must remain five seconds')
                    standalone(tree, node)
                    masks[side].append((node.lineno, node.end_lineno, ''))
                    to_remove.append(node)
        tree.body = [node for node in tree.body if node not in to_remove]
        def normalize(body, prefix=''):
            result = []
            for node in body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    key = prefix + node.name
                    if key in additions:
                        continue
                    if key in GUEST_BODIES[name]:
                        node.body = [ast.Pass()]
                        if side == 'new' and key == 'LocalCharacterServer.stage_map_data':
                            original = old_functions[key]
                            node.args = copy.deepcopy(original.args)
                elif isinstance(node, ast.ClassDef):
                    node.body = normalize(node.body, prefix + node.name + '.')
                result.append(node)
            return result
        tree.body = normalize(tree.body)
    require(ast.dump(old_tree, include_attributes=False) == ast.dump(new_tree, include_attributes=False),
            'Guest module/class skeleton changed outside reviewed startup scope')
    def normalized_text(text, spans):
        lines = text.splitlines(keepends=True)
        for first, last, replacement in sorted(spans, reverse=True):
            lines[first - 1:last] = [replacement]
        # Blank separators may surround newly inserted methods/imports. Every
        # remaining nonblank line, including guard comments, stays byte exact.
        return ''.join(line for line in lines if line.strip())
    require(normalized_text(old_text, masks['old']) == normalized_text(new_text, masks['new']),
            'Guest source outside reviewed bodies/imports/inventory differs')


def extract_and_repair(apk, donor, destination, commit):
    base = builder()
    require(not destination.exists() and not destination.is_symlink(), "Fresh donor extraction tree required")
    destination.mkdir(parents=True)
    retained = {}
    with zipfile.ZipFile(apk) as archive:
        for entry in archive.infolist():
            name = entry.filename
            if name == "AndroidManifest.xml" or name.startswith("META-INF/"):
                continue
            require(name in donor["payloads"] or name in ("classes.dex", "resources.arsc", "res/drawable/ic_coh_client.xml"),
                    "Unexpected donor APK member")
            require(not stat.S_ISLNK(entry.external_attr >> 16), "Linked donor APK member")
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output, 1024 * 1024)
            retained[name] = base.file_pin(target)
    require(all(retained.get(name) == pin for name, pin in donor["payloads"].items()), "Donor payload bytes differ")
    assets = destination / "assets/runtime"
    runtime = read_json(assets / "runtime-manifest.json")
    client = read_json(assets / "client-manifest.json")
    require(runtime == donor["runtime_manifest"] and runtime["repository_commit"] == DONOR_COMMIT
            and all(donor["payloads"].get("assets/runtime/" + name) == pin for name, pin in runtime["files"].items())
            and all(runtime["files"].get(name) == pin for name, pin in client["files"].items()),
            "Donor verification manifests differ")
    for name, pin in donor["payloads"].items():
        if name.startswith("assets/runtime/") and name.endswith(".py") and Path(name).name not in HELPERS:
            base.checked_file(ROOT / "android/guest" / Path(name).name, pin)
    helper_pins = {}
    for name in sorted(HELPERS | {GUEST_ADDITION}):
        helper = ROOT / "android/guest" / name
        base.checked_file(helper)
        require(0 < helper.stat().st_size <= 1024 * 1024, "Bounded startup/cache helper required")
        if name in HELPERS:
            validate_guest_scope(name, (assets / name).read_bytes(), helper.read_bytes())
        else:
            require(not (assets / name).exists(), "New startup/cache module collides with donor")
        shutil.copyfile(helper, assets / name)
        helper_pins[name] = base.file_pin(helper)
    _, revised_client = repair_manifests(runtime, client, helper_pins, {}, commit)
    (assets / "client-manifest.json").write_text(json.dumps(revised_client, indent=2) + "\n")
    revised_runtime, expected_client = repair_manifests(runtime, client, helper_pins,
        base.file_pin(assets / "client-manifest.json"), commit)
    require(revised_client == expected_client, "Client manifest changed beyond startup/cache pins")
    (assets / "runtime-manifest.json").write_text(json.dumps(revised_runtime, indent=2) + "\n")
    payloads = {name: base.file_pin(destination / name) for name in donor["payloads"]}
    payloads.update({name: base.file_pin(destination / name) for name in ADDED_PAYLOADS})
    require({name for name in donor["payloads"] if payloads[name] != donor["payloads"][name]} >= REQUIRED_PAYLOADS
            and {name for name in donor["payloads"] if payloads[name] != donor["payloads"][name]} <= ALLOWED_PAYLOADS,
            "Startup performance repair changed unrelated donor payloads")
    return revised_runtime, payloads, retained


def repair_android_manifest(source, destination):
    base = builder()
    base.verify_source_manifest(source)
    tree = ET.parse(source)
    manifest = tree.getroot()
    manifest.set(base.ANDROID + "versionName", VERSION_NAME)
    manifest.set(base.ANDROID + "versionCode", str(VERSION_CODE))
    manifest.find("application").set(base.ANDROID + "label", "COH Atlas Gameplay")
    ET.register_namespace("android", base.ANDROID[1:-1])
    tree.write(destination, encoding="utf-8", xml_declaration=True)
    builder(repaired=True).verify_source_manifest(destination)


def download(args):
    require(not args.output.exists() and not args.output.is_symlink(), "Fresh donor APK output required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(DONOR_URL, timeout=120) as source, args.output.open("xb") as target:
        total = 0
        while chunk := source.read(1024 * 1024):
            total += len(chunk)
            require(total <= DONOR_APK["bytes"], "Donor download exceeds the pinned size")
            target.write(chunk)
    builder().checked_file(args.output, DONOR_APK)
    print("Exact published 0.11.3 donor APK downloaded and pinned.")


def build(args):
    base, current = builder(), builder(repaired=True)
    commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report, args.ground_build_report, args.avatar_build_report, args.retained_source_report)
    qualification = validate_qualification(read_json(args.qualification), commit)
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, "coh-client-interactive", SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), "Fresh startup-perf APK required")
    base.checked_file(args.testing_notes)
    require(0 < args.testing_notes.stat().st_size <= 65536, "Bounded testing notes required")
    for tool in (args.android_jar, args.build_tools / "aapt2", args.build_tools / "zipalign",
                 args.build_tools / "lib/d8.jar", args.build_tools / "lib/apksigner.jar"):
        require(tool.is_file() and not tool.is_symlink(), "Required Android tool missing")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coh-startup-perf-", dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, retained = extract_and_repair(args.donor_apk, donor, work / "donor", commit)
        classes, generated, dex = (work / name for name in ("classes", "generated", "dex"))
        for folder in (classes, generated, dex):
            folder.mkdir()
        # Check the complete authored compilation closure before invoking aapt/javac.
        current_java_sources(donor, generated)
        validate_rfb_scope((ROOT / next(iter(JAVA_CHANGES))).read_bytes(), donor["java_sources"][next(iter(JAVA_CHANGES))])
        manifest = work / "AndroidManifest.xml"
        repair_android_manifest(ROOT / "android/interactive/src/main/AndroidManifest.xml", manifest)
        resources, unsigned, aligned, signed = (work / name for name in ("resources.zip", "unsigned.apk", "aligned.apk", "signed.apk"))
        base.run(args.build_tools / "aapt2", "compile", "--dir", ROOT / "android/interactive/src/main/res", "-o", resources)
        base.run(args.build_tools / "aapt2", "link", "-I", args.android_jar, "--manifest", manifest,
                 "--min-sdk-version", "26", "--target-sdk-version", "35", "--java", generated, resources, "-o", unsigned)
        with zipfile.ZipFile(unsigned) as archive:
            require(set(archive.namelist()) == {"AndroidManifest.xml", "resources.arsc", "res/drawable/ic_coh_client.xml"},
                    "Generated Android resource inventory differs")
            for name in donor["retained_android_resources"]:
                data = archive.read(name)
                require({"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} == retained[name],
                        "Android resources changed beyond package version metadata")
        require({path.relative_to(generated).as_posix() for path in generated.rglob("*.java")} ==
                {base.APP_ID.replace(".", "/") + "/R.java"}, "Unexpected generated Java source inventory")
        sources, source_pins, changed_java = current_java_sources(donor, generated)
        base.run("java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "--release", "8", "-cp", args.android_jar,
                 "-d", classes, *sources)
        class_jar = work / "classes.jar"
        with zipfile.ZipFile(class_jar, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(classes.rglob("*.class")):
                archive.write(path, path.relative_to(classes).as_posix())
        base.run("java", "-cp", args.build_tools / "lib/d8.jar", "com.android.tools.r8.D8", "--min-api", "26",
                 "--lib", args.android_jar, "--output", dex, class_jar)
        require({path.name for path in dex.iterdir()} == {"classes.dex"}, "Unexpected DEX output inventory")
        dex_pin = base.file_pin(dex / "classes.dex")
        with zipfile.ZipFile(unsigned, "a", zipfile.ZIP_DEFLATED) as archive:
            base.append_payloads(archive, [(work / "donor" / name, name) for name in sorted(payloads)])
            archive.write(dex / "classes.dex", "classes.dex")
        base.run(args.build_tools / "zipalign", "-f", "4", unsigned, aligned)
        base.run("java", "-jar", args.build_tools / "lib/apksigner.jar", "sign", "--ks", args.keystore,
                 "--ks-key-alias", "coh-client-interactive", "--ks-pass", password, "--key-pass", password, "--out", signed, aligned)
        certificate = base.verify_signer_output(base.run("java", "-jar", args.build_tools / "lib/apksigner.jar",
                                                       "verify", "--verbose", "--print-certs", signed), SIGNER)
        base.run(args.build_tools / "zipalign", "-c", "4", signed)
        current.verify_badging(base.run(args.build_tools / "aapt2", "dump", "badging", signed))
        verify_derivative(signed, donor, payloads, dex_pin)
        shutil.copyfile(signed, args.output)
        replaced_payloads = {name for name in donor["payloads"] if donor["payloads"][name] != payloads[name]}
        report = {"format": 1, "apk": APK_NAME, **base.file_pin(args.output), "repository_commit": commit,
                  "application_id": base.APP_ID, "version_name": VERSION_NAME, "version_code": VERSION_CODE,
                  "abi": "arm64-v8a", "signer_certificate_sha256": certificate, "signing_key_created": False,
                  "signature_verified": True, "package_badging_verified": True, "payload_bytes_verified": True,
                  "runtime_manifest": runtime, "runtime_manifest_sha256": payloads["assets/runtime/runtime-manifest.json"]["sha256"],
                  "payloads": payloads, "changed_apk_payloads": sorted(replaced_payloads | ADDED_PAYLOADS),
                  "replaced_apk_payloads": sorted(replaced_payloads), "added_apk_payloads": sorted(ADDED_PAYLOADS),
                  "recompiled_dex": dex_pin, "donor_dex": donor["recompiled_dex"],
                  "retained_android_resources": donor["retained_android_resources"], "donor": donor_link(),
                  "retained_source_report": {"run_id": RETAINED_SOURCE_RUN_ID, "repository_commit": RETAINED_SOURCE_COMMIT,
                                             **RETAINED_SOURCE_BUILD},
                  "ground_build_report": {"run_id": session_builder().DONOR_RUN_ID, "repository_commit": session_builder().DONOR_COMMIT, **session_builder().DONOR_BUILD},
                  "avatar_build_report": {"run_id": AVATAR_RUN_ID, "repository_commit": AVATAR_COMMIT, **AVATAR_BUILD},
                  "java_sources": source_pins, "changed_java_sources": changed_java, "added_java_sources": [],
                  "preserved_sources": {name: pin for name, pin in donor["preserved_sources"].items() if name not in JAVA_CHANGES},
                  "source_manifest": donor["source_manifest"], "generated_manifest": base.file_pin(manifest),
                  "qualification": qualification, "qualification_receipt": base.file_pin(args.qualification),
                  "testing_notes": base.file_pin(args.testing_notes), "native_libraries_changed": False,
                  "client_or_server_recompiled": False, "java_or_dex_recompiled": True, "world_assets_changed": False,
                  "unrelated_java_sources_preserved": True, "guest_source_derivative_scope_verified": True,
                  "physical_gameplay_validated": False,
                  "scope": "Isolated server worktree reuse, bounded readiness/log observation and buffered RFB input retaining the complete published 0.11.3 backend, world, avatar, budget and normal-save guards; physical startup duration, native FPS and exterior reopen pending"}
        (args.output.parent / REPORT_NAME).write_text(json.dumps(report, indent=2) + "\n")
        args.output.with_suffix(".apk.sha256").write_text(report["sha256"] + "  " + APK_NAME + "\n")
        shutil.copyfile(args.testing_notes, args.output.parent / NOTES_NAME)
        print("Built focused retained-signer startup-perf candidate", report["sha256"])


def publish_release(api, report, assets, notes):
    base = builder()
    require(tuple(path.name for path in assets) == (APK_NAME, APK_NAME + ".sha256", NOTES_NAME), "Unexpected repair release assets")
    base.checked_file(assets[0], report)
    for path in ("/releases/tags/" + RELEASE_TAG, "/git/ref/tags/" + RELEASE_TAG):
        try:
            existing = api.request(path)
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
        else:
            require(not path.startswith("/releases/"), "Existing repair release is never replaced")
            require(existing.get("object", {}).get("type") == "commit" and existing["object"].get("sha") == report["repository_commit"],
                    "Existing repair tag points elsewhere")
    body = notes + "\n\nAPK SHA-256: `" + report["sha256"] + "`.\n"
    body += "[Focused startup/cache and save-guard qualification](https://github.com/" + REPOSITORY + "/actions/runs/" + os.environ.get("GITHUB_RUN_ID", "") + ").\n"
    release = api.request("/releases", {"tag_name": RELEASE_TAG, "target_commitish": report["repository_commit"],
        "name": "COH Atlas Gameplay 0.11.4 — server startup reuse and bounded RFB reads", "body": body, "draft": True,
        "prerelease": True, "generate_release_notes": False, "make_latest": "false"}, method="POST")
    require(type(release.get("id")) is int and release.get("draft") is True and release.get("prerelease") is True
            and release.get("tag_name") == RELEASE_TAG, "Unexpected created repair release")
    for path in assets:
        result = api.request("/releases/" + str(release["id"]) + "/assets?" + urllib.parse.urlencode({"name": path.name}),
                             path, method="POST", upload=True)
        pin = base.file_pin(path)
        require(result.get("state") == "uploaded" and result.get("name") == path.name and result.get("size") == pin["bytes"]
                and result.get("digest") == "sha256:" + pin["sha256"], "Repair release upload bytes differ")
    published = api.request("/releases/" + str(release["id"]), {"draft": False, "prerelease": True, "make_latest": "false"}, method="PATCH")
    require(published.get("id") == release["id"] and published.get("draft") is False and published.get("prerelease") is True
            and published.get("tag_name") == RELEASE_TAG, "Repair publication did not complete")
    return published.get("html_url")


def publish(args):
    base, current = builder(), builder(repaired=True)
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY and os.environ.get("GITHUB_REF") == "refs/heads/" + BRANCH
            and os.environ.get("GITHUB_EVENT_NAME") in ("push", "workflow_dispatch"),
            "Startup performance publication requires the authorized continuation branch")
    report = read_json(args.build_report)
    donor = validate_lineage(args.donor_build_report, args.ground_build_report, args.avatar_build_report, args.retained_source_report)
    with tempfile.TemporaryDirectory(prefix="coh-source-closure-") as temporary:
        _, source_pins, changed_java = current_java_sources(donor, Path(temporary))
    replaced_payloads = set(report.get("replaced_apk_payloads", []))
    validate_rfb_scope((ROOT / next(iter(JAVA_CHANGES))).read_bytes(), donor["java_sources"][next(iter(JAVA_CHANGES))])
    require(report.get("format") == 1 and report.get("apk") == APK_NAME and report.get("application_id") == base.APP_ID
            and report.get("version_name") == VERSION_NAME and report.get("version_code") == VERSION_CODE
            and report.get("repository_commit") == os.environ.get("GITHUB_SHA") and report.get("signer_certificate_sha256") == SIGNER
            and report.get("signing_key_created") is False
            and all(report.get(key) is True for key in ("signature_verified", "package_badging_verified", "payload_bytes_verified",
                "java_or_dex_recompiled", "unrelated_java_sources_preserved", "guest_source_derivative_scope_verified"))
            and all(report.get(key) is False for key in ("native_libraries_changed", "client_or_server_recompiled", "world_assets_changed", "physical_gameplay_validated"))
            and set(report.get("changed_apk_payloads", [])) == replaced_payloads | ADDED_PAYLOADS
            and REQUIRED_PAYLOADS <= replaced_payloads <= ALLOWED_PAYLOADS
            and set(report.get("added_apk_payloads", [])) == ADDED_PAYLOADS
            and report.get("donor") == donor_link()
            and report.get("retained_source_report") == {"run_id": RETAINED_SOURCE_RUN_ID,
                "repository_commit": RETAINED_SOURCE_COMMIT, **RETAINED_SOURCE_BUILD}
            and report.get("avatar_build_report") == {"run_id": AVATAR_RUN_ID, "repository_commit": AVATAR_COMMIT, **AVATAR_BUILD}
            and report.get("ground_build_report") == {"run_id": session_builder().DONOR_RUN_ID,
                "repository_commit": session_builder().DONOR_COMMIT, **session_builder().DONOR_BUILD}
            and report.get("java_sources") == source_pins and report.get("changed_java_sources") == changed_java
            and report.get("added_java_sources") == []
            and report.get("preserved_sources") == {name: pin for name, pin in donor["preserved_sources"].items() if name not in JAVA_CHANGES}
            and report.get("source_manifest") == donor["source_manifest"]
            and report.get("donor_dex") == donor["recompiled_dex"]
            and report.get("retained_android_resources") == donor["retained_android_resources"],
            "Startup performance build receipt or derivative boundaries differ")
    receipt = read_json(args.qualification)
    validate_qualification(receipt, report["repository_commit"])
    require(receipt == report.get("qualification") and base.file_pin(args.qualification) == report.get("qualification_receipt"),
            "Qualified startup/cache evidence changed")
    base.checked_file(args.apk, report)
    verify_derivative(args.apk, donor, report["payloads"], report["recompiled_dex"])
    for name in HELPERS | {GUEST_ADDITION}:
        require(report["payloads"]["assets/runtime/" + name] == base.file_pin(ROOT / "android/guest" / name),
                "Qualified guest source bytes differ from packaged deadline helpers")
    with zipfile.ZipFile(args.apk) as archive:
        runtime = json.loads(archive.read("assets/runtime/runtime-manifest.json"))
        client = json.loads(archive.read("assets/runtime/client-manifest.json"))
        expected = copy.deepcopy(donor["runtime_manifest"])
        for name in HELPERS | {GUEST_ADDITION, "client-manifest.json"}:
            expected["files"][name] = report["payloads"]["assets/runtime/" + name]
        expected["scope"] = runtime.get("scope")
        expected["repository_commit"] = report["repository_commit"]
        require(runtime == expected and runtime == report.get("runtime_manifest")
                and report.get("runtime_manifest_sha256") == report["payloads"]["assets/runtime/runtime-manifest.json"]["sha256"]
                and all(runtime["files"].get(name) == pin for name, pin in client.get("files", {}).items()),
                "Published verification metadata differs beyond startup/cache pins")
    base.verify_signer_output(base.run("java", "-jar", args.build_tools / "lib/apksigner.jar", "verify", "--verbose", "--print-certs", args.apk), SIGNER)
    current.verify_badging(base.run(args.build_tools / "aapt2", "dump", "badging", args.apk))
    base.checked_file(args.testing_notes, report["testing_notes"])
    checksum = args.apk.with_suffix(".apk.sha256")
    require(checksum.read_text() == report["sha256"] + "  " + APK_NAME + "\n", "Startup performance checksum differs")
    public_notes = args.apk.parent / NOTES_NAME
    base.checked_file(public_notes, report["testing_notes"])
    spec = importlib.util.spec_from_file_location("coh_startup_github", Path(__file__).with_name("build_atlas_gameplay_apk.py"))
    api_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_module)
    print("Published startup-perf prerelease:", publish_release(api_module.GitHub(os.environ.get("GH_TOKEN")), report,
          (args.apk, checksum, public_notes), public_notes.read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    get = commands.add_parser("download-donor")
    get.add_argument("--output", type=Path, required=True)
    create = commands.add_parser("build")
    for name in ("donor-apk", "donor-build-report", "ground-build-report", "avatar-build-report", "retained-source-report", "qualification", "android-jar", "build-tools", "keystore", "output"):
        create.add_argument("--" + name, type=Path, required=True)
    create.add_argument("--repository-commit")
    create.add_argument("--password-env", default="COH_INTERACTIVE_KEYSTORE_PASSWORD")
    create.add_argument("--testing-notes", type=Path, default=NOTES)
    release = commands.add_parser("publish")
    for name in ("apk", "build-report", "build-tools", "qualification", "donor-build-report", "ground-build-report", "avatar-build-report", "retained-source-report"):
        release.add_argument("--" + name, type=Path, required=True)
    release.add_argument("--testing-notes", type=Path, default=NOTES)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.absolute())
    {"download-donor": download, "build": build, "publish": publish}[args.command](args)


if __name__ == "__main__":
    main()
