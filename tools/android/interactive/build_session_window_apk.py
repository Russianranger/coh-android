#!/usr/bin/env python3
"""Package phase-aware Atlas gameplay/save budgets from the exact 0.11.2 APK.

Only the Android session/UI sources, two guest deadline hooks, one new bounded
budget module and their verification manifests change. Native libraries, game,
server, geometry/materials, avatar data and unrelated sources retain donor bytes.
Focused host-side budget/save-guard regressions authorize packaging; they do
not claim new physical gameplay or rerun the accepted native runtime milestone.
"""
from __future__ import annotations

import argparse
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
DONOR_COMMIT = "7e2f44b122417192ec1d9dd6d973b27b594e0a82"
DONOR_RUN_ID = 36994687459
DONOR_APK_NAME = "COH-Atlas-Gameplay-0.11.2.apk"
DONOR_APK = {"bytes": 595104089, "sha256": "1e8b9ffd09dcfa6967685e31b1ccbff1acf200b892614e6ec2f6092d533e8adb"}
DONOR_BUILD = {"bytes": 38378, "sha256": "408618a7e8d71219f1547accc7e8b5169661edd48bc4ac5ffd9985c01aad2812"}
DONOR_URL = "https://github.com/" + REPOSITORY + "/releases/download/coh-atlas-gameplay-v0.11.2/" + DONOR_APK_NAME
AVATAR_COMMIT = "34b763a5518e3fa3740c197c0e824c17da088536"
AVATAR_RUN_ID = 36944389469
AVATAR_APK = {"bytes": 595104089, "sha256": "f4e30c728046771cb91beece46fb54663b0fcd57a28b8e055f6fc8918dd3c899"}
AVATAR_BUILD = {"bytes": 34498, "sha256": "993417b3c18902f73cc27f3068b5b309a4784177b80349877028586bc8476904"}
RETAINED_SOURCE_COMMIT = "1649e807d2b2310170e775c53bafa24cd932638a"
RETAINED_SOURCE_RUN_ID = 36937373454
RETAINED_SOURCE_BUILD = {"bytes": 45992, "sha256": "cc0ad0f09bf06f598e6f65e706260fa9bb1a90e699ad1794d9df9ff1625d1d00"}
RETAINED_SOURCE_APK = {"bytes": 595099993, "sha256": "e3a0760d23ef57747343ee8fd0c76e68a92194df040062266f3dc282cd15a924"}
SIGNER = "92955353965f118a748f1f2cadc00dfb39b3e8ade0a6cdd7d44058a3a776c282"
VERSION_NAME, VERSION_CODE = "0.11.3", 9
APK_NAME = "COH-Atlas-Gameplay-0.11.3.apk"
REPORT_NAME = "session-window-apk-build-report.json"
NOTES_NAME = "COH-Atlas-Gameplay-0.11.3-testing.txt"
RELEASE_TAG = "coh-atlas-gameplay-v0.11.3"
NOTES = ROOT / "docs" / NOTES_NAME
HELPERS = frozenset(("client_interactive_diagnostic.py", "character_reopen_diagnostic.py"))
GUEST_ADDITION = "character_session_budget.py"
CHANGED_PAYLOADS = frozenset("assets/runtime/" + name for name in
    (*HELPERS, "client-manifest.json", "runtime-manifest.json"))
ADDED_PAYLOADS = frozenset(("assets/runtime/" + GUEST_ADDITION,))
JAVA_ROOT = "android/interactive/src/main/java/io/github/russianranger/cohclientinteractive/"
JAVA_CHANGES = frozenset(JAVA_ROOT + name for name in ("ClientRuntime.java", "ClientActivity.java", "ClientService.java"))
JAVA_REQUIRED_CHANGES = frozenset(JAVA_ROOT + name for name in ("ClientRuntime.java", "ClientActivity.java"))
JAVA_ADDITION = JAVA_ROOT + "ClientSessionBudget.java"
QUALIFICATION_SCOPE = "phase_aware_session_and_save_window"
QUALIFICATION_SCRIPT = "tools/android/interactive/qualify_session_window.py"
WORKFLOW = ".github/workflows/android-session-window.yml"
SOURCE_FILES = frozenset((*("android/guest/" + name for name in HELPERS), *JAVA_CHANGES, JAVA_ADDITION,
    "android/guest/" + GUEST_ADDITION,
    QUALIFICATION_SCRIPT, WORKFLOW, "tools/android/interactive/build_session_window_apk.py",
    "tools/android/interactive/test_session_window_package.py", "tools/android/interactive/build_apk.py",
    "tools/android/interactive/build_atlas_gameplay_apk.py",
    "tools/android/interactive/test_session_budget_guest.py", "tools/android/interactive/test_session_budget_java.py",
    "android/guest/local_character_server.py", "tools/android/interactive/test_character_reopen_guest.py",
    "tools/android/interactive/test_ground_repair.py", "tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.log",
    "tools/android/interactive/fixtures/thor-ground-0.11.1-20261002.json"))


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


def validate_donor_receipt(report):
    require(report.get("format") == 1 and report.get("apk") == DONOR_APK_NAME
            and report.get("repository_commit") == DONOR_COMMIT
            and {key: report.get(key) for key in DONOR_APK} == DONOR_APK
            and report.get("application_id") == builder().APP_ID
            and report.get("version_name") == "0.11.2" and report.get("version_code") == 8
            and report.get("abi") == "arm64-v8a" and report.get("signer_certificate_sha256") == SIGNER
            and report.get("signing_key_created") is False
            and all(report.get(key) is True for key in ("signature_verified", "package_badging_verified", "payload_bytes_verified"))
            and all(report.get(key) is False for key in ("native_libraries_changed", "client_or_server_recompiled", "java_or_dex_recompiled", "world_assets_changed"))
            and set(report.get("changed_apk_payloads", [])) == {
                "assets/runtime/local_character_server.py", "assets/runtime/client-manifest.json", "assets/runtime/runtime-manifest.json"}
            and report.get("donor") == {"run_id": AVATAR_RUN_ID, "repository_commit": AVATAR_COMMIT,
                "apk": AVATAR_APK, "build_report": AVATAR_BUILD}
            and report.get("retained_source_report") == {"run_id": RETAINED_SOURCE_RUN_ID,
                "repository_commit": RETAINED_SOURCE_COMMIT, **RETAINED_SOURCE_BUILD},
            "Exact published retained-signer 0.11.2 donor receipt differs")
    require(report.get("retained_dex") and set(report.get("retained_android_resources", {})) ==
            {"resources.arsc", "res/drawable/ic_coh_client.xml"}, "Donor retained shell byte pins are incomplete")


def validate_lineage(report_path, avatar_report, retained_source_report):
    """Authenticate the complete retained 0.11.2 -> 0.11.1 -> 0.11.0 lineage."""
    base = builder()
    for path, expected in ((report_path, DONOR_BUILD), (avatar_report, AVATAR_BUILD),
                           (retained_source_report, RETAINED_SOURCE_BUILD)):
        base.checked_file(path, expected)
    donor, avatar, original = (read_json(path) for path in (report_path, avatar_report, retained_source_report))
    validate_donor_receipt(donor)
    require(avatar.get("repository_commit") == AVATAR_COMMIT and avatar.get("version_name") == "0.11.1"
            and {key: avatar.get(key) for key in AVATAR_APK} == AVATAR_APK
            and avatar.get("donor") == {"run_id": RETAINED_SOURCE_RUN_ID,
                "repository_commit": RETAINED_SOURCE_COMMIT, "apk": RETAINED_SOURCE_APK,
                "build_report": RETAINED_SOURCE_BUILD}
            and original.get("repository_commit") == RETAINED_SOURCE_COMMIT
            and original.get("version_name") == "0.11.0"
            and {key: original.get(key) for key in RETAINED_SOURCE_APK} == RETAINED_SOURCE_APK,
            "Authenticated retained donor lineage identity differs")
    for old, new, names in ((original, avatar, {
            "assets/runtime/character_avatar_assets.py", "assets/runtime/client-manifest.json", "assets/runtime/runtime-manifest.json"}),
        (avatar, donor, {"assets/runtime/local_character_server.py", "assets/runtime/client-manifest.json", "assets/runtime/runtime-manifest.json"})):
        require(set(old["payloads"]) == set(new["payloads"])
                and {name for name in old["payloads"] if old["payloads"][name] != new["payloads"][name]} == names,
                "Retained donor lineage changed payload boundaries")
    require(donor.get("retained_dex") == avatar.get("retained_dex")
            and donor.get("retained_android_resources") == avatar.get("retained_android_resources")
            and all(donor.get(name) == original.get(name) and donor.get(name)
                for name in ("java_sources", "preserved_sources", "source_manifest")),
            "Original retained Android and backend source pins differ")
    return donor


def current_java_sources(donor, generated):
    """Compile only original shipped sources plus the explicitly added budget class."""
    base = builder()
    sources = base.java_sources(ROOT / "android/interactive/src/main", generated)
    pins = {path.relative_to(ROOT).as_posix(): base.file_pin(path) for path in sources
            if path.is_relative_to(ROOT) and not path.is_relative_to(generated)}
    original = donor["java_sources"]
    require(set(pins) == set(original) | {JAVA_ADDITION}, "Unexpected Java source addition or omission")
    changed = {name for name in original if original[name] != pins[name]}
    require(JAVA_REQUIRED_CHANGES <= changed <= JAVA_CHANGES, "Java changes exceed the focused phase-budget sources")
    for name, pin in donor["preserved_sources"].items():
        if name not in JAVA_CHANGES:
            base.checked_file(ROOT / name, pin)
    base.checked_file(ROOT / "android/interactive/src/main/AndroidManifest.xml", donor["source_manifest"])
    return sources, pins, sorted(changed)


def validate_donor(apk, report_path, avatar_report, retained_source_report):
    base = builder()
    base.checked_file(apk, DONOR_APK)
    report = validate_lineage(report_path, avatar_report, retained_source_report)
    base.verify_packaged_payloads(apk, report["payloads"])
    with zipfile.ZipFile(apk) as archive:
        retained = {"classes.dex": report["retained_dex"], **report["retained_android_resources"]}
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
            and {name for name in donor["payloads"] if payloads[name] != donor["payloads"][name]} == CHANGED_PAYLOADS,
            "Session-window derivative payload boundary differs")
    require(dex_pin != donor["retained_dex"], "Session-window DEX was not revised")
    base.checked_pin(dex_pin)
    base.verify_packaged_payloads(apk, payloads)
    retained = donor["retained_android_resources"]
    with zipfile.ZipFile(apk) as archive:
        require({name for name in archive.namelist() if not name.startswith("META-INF/")} ==
                set(payloads) | set(retained) | {"AndroidManifest.xml", "classes.dex"}, "Unexpected session-window APK member")
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
            and receipt.get("physical_gameplay_validated") is False and receipt.get("policy") == POLICY,
            "Focused phase-budget qualification for this exact commit and policy is required")
    files = receipt.get("source_files", {})
    require(SOURCE_FILES <= set(files), "Session-window qualification source closure is incomplete")
    for name, pin in files.items():
        require(isinstance(name, str) and Path(name).as_posix() == name and not Path(name).is_absolute()
                and ".." not in Path(name).parts and "\\" not in name, "Unsafe qualification source path")
        base.checked_file(ROOT / name, pin)
    require(type(receipt.get("tests_run")) is int and receipt["tests_run"] >= 20,
            "Focused phase-budget regression coverage is incomplete")
    require(all(receipt.get("checks", {}).get(name) is True for name in (
        "guest_budget_regressions_passed", "java_budget_regressions_passed", "ground_and_save_guards_preserved",
        "phase_identity_and_deadline_caps_preserved")), "Session-window safety checks are incomplete")
    return receipt


def repair_manifests(runtime, client, helper_pins, client_pin, commit):
    """Replace only the two deadline hooks, add their module and revise verification pins."""
    require(set(helper_pins) == HELPERS | {GUEST_ADDITION}, "Unexpected phase-budget helper inventory")
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
    revised_runtime["scope"] = ("Published 0.11.2 backend with bounded phase-aware Atlas gameplay/save windows; "
                                "physical budget behavior and an outdoor save/reopen remain pending")
    return revised_runtime, revised_client


CLIENT_DEADLINE_HOOK = b'    def interaction_deadline(self, deadline, launch):\n        """Modes may bound a validated phase; ordinary menu/creation stay fixed."""\n        return deadline\n\n'
REOPEN_DEADLINE_HOOK = b"    def interaction_deadline(self, deadline, launch):\n        if not self.connected_announced:\n            return deadline\n        proof = self.ctx.report.get(self.REPORT_KEY, {})\n        require(self.identity_verified(proof, self.args.session_id)\n                and isinstance(launch, dict) and proof.get('client_pid') == launch.get('pid'),\n                'Reopen phase budget lacks the current validated graphical character')\n        now, utc_ms = time.monotonic(), int(time.time() * 1000)\n        if not hasattr(self, 'session_budget'):\n            require(session_budget.finite_seconds(deadline) and now < deadline,\n                    'Native connection arrived after the current menu deadline')\n            self.session_budget = session_budget.SessionBudget(self.args.session_id, launch['pid'],\n                self.launcher_started_monotonic, self.ctx.deadline)\n        events = [self.session_budget.connected(proof, now, utc_ms)]\n        if getattr(self, 'relocated_announced', False):\n            if self.session_budget.revision < 2:\n                require(now < self.session_budget.deadline,\n                        'Ground verification arrived after the current connected deadline')\n            events.append(self.session_budget.grounded(proof, now, utc_ms))\n        for event in events:\n            if event is not None:\n                budgets = self.ctx.report.setdefault('character_session_budgets', [])\n                budgets.append(dict(event))\n                self.ctx.event('character_session_budget', **event)\n        return self.session_budget.deadline\n\n"


def validate_guest_scope(name, old, new):
    """Require the exact reviewed hooks; all original lifecycle/save code stays byte-identical."""
    if name == "client_interactive_diagnostic.py":
        hook = CLIENT_DEADLINE_HOOK
        replacements = (
            (b"    def initialize(self):\n", hook + b"    def initialize(self):\n"),
            (b"        started = time.monotonic()\n        deadline = started + self.args.startup_timeout_seconds\n",
             b"        started = time.monotonic()\n        self.launcher_started_monotonic = started\n        deadline = started + self.args.startup_timeout_seconds\n"),
            (b"                        'Could not attach to actual client console within 120 seconds')\n",
             b"                        'Could not attach to actual client console within 120 seconds')\n                if ready_at is not None:\n                    deadline = self.interaction_deadline(deadline, launch)\n"),
            (b"                                interaction_timeout_seconds=self.args.interaction_seconds)\n                        if finish_request is None:\n",
             b"                                interaction_timeout_seconds=self.args.interaction_seconds)\n                        deadline = self.interaction_deadline(deadline, launch)\n                        if finish_request is None:\n"),
        )
    elif name == "character_reopen_diagnostic.py":
        replacements = (
            (b"import sys\n", b"import sys\nimport time\n"),
            (b"import character_creation_diagnostic as creation\n",
             b"import character_creation_diagnostic as creation\nimport character_session_budget as session_budget\n"),
            (b"{'character_reopen_diagnostic.py', 'atlas_world_assets.py',",
             b"{'character_reopen_diagnostic.py', 'character_session_budget.py', 'atlas_world_assets.py',"),
            (b"    def observe_console(self):\n", REOPEN_DEADLINE_HOOK + b"    def observe_console(self):\n"),
        )
    else:
        raise ValueError("Unexpected session-window guest derivative")
    require(old != new, "Reviewed deadline hook did not change")
    for before, after in replacements:
        require(old.count(before) == 1, "Expected donor deadline-hook anchor differs")
        old = old.replace(before, after)
    require(old == new, "Guest changes exceed the exact reviewed deadline hooks")


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
        require(0 < helper.stat().st_size <= 1024 * 1024, "Bounded phase-budget helper required")
        if name in HELPERS:
            validate_guest_scope(name, (assets / name).read_bytes(), helper.read_bytes())
        else:
            require(not (assets / name).exists(), "New phase-budget module collides with donor")
        shutil.copyfile(helper, assets / name)
        helper_pins[name] = base.file_pin(helper)
    _, revised_client = repair_manifests(runtime, client, helper_pins, {}, commit)
    (assets / "client-manifest.json").write_text(json.dumps(revised_client, indent=2) + "\n")
    revised_runtime, expected_client = repair_manifests(runtime, client, helper_pins,
        base.file_pin(assets / "client-manifest.json"), commit)
    require(revised_client == expected_client, "Client manifest changed beyond phase-budget pins")
    (assets / "runtime-manifest.json").write_text(json.dumps(revised_runtime, indent=2) + "\n")
    payloads = {name: base.file_pin(destination / name) for name in donor["payloads"]}
    payloads.update({name: base.file_pin(destination / name) for name in ADDED_PAYLOADS})
    require({name for name in donor["payloads"] if payloads[name] != donor["payloads"][name]} == CHANGED_PAYLOADS,
            "Session-window repair changed unrelated donor payloads")
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
    print("Exact published 0.11.2 donor APK downloaded and pinned.")


def build(args):
    base, current = builder(), builder(repaired=True)
    commit = base.source_commit(args.repository_commit)
    donor = validate_donor(args.donor_apk, args.donor_build_report, args.avatar_build_report, args.retained_source_report)
    qualification = validate_qualification(read_json(args.qualification), commit)
    password = base.signing_password_spec(args.password_env)
    base.verify_signing_identity(args.keystore, "coh-client-interactive", SIGNER, password)
    require(args.output.name == APK_NAME and not args.output.exists() and not args.output.is_symlink(), "Fresh session-window APK required")
    base.checked_file(args.testing_notes)
    require(0 < args.testing_notes.stat().st_size <= 65536, "Bounded testing notes required")
    for tool in (args.android_jar, args.build_tools / "aapt2", args.build_tools / "zipalign",
                 args.build_tools / "lib/d8.jar", args.build_tools / "lib/apksigner.jar"):
        require(tool.is_file() and not tool.is_symlink(), "Required Android tool missing")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="coh-session-window-", dir=args.output.parent) as temporary:
        work = Path(temporary)
        runtime, payloads, retained = extract_and_repair(args.donor_apk, donor, work / "donor", commit)
        classes, generated, dex = (work / name for name in ("classes", "generated", "dex"))
        for folder in (classes, generated, dex):
            folder.mkdir()
        # Check the complete authored compilation closure before invoking aapt/javac.
        current_java_sources(donor, generated)
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
        report = {"format": 1, "apk": APK_NAME, **base.file_pin(args.output), "repository_commit": commit,
                  "application_id": base.APP_ID, "version_name": VERSION_NAME, "version_code": VERSION_CODE,
                  "abi": "arm64-v8a", "signer_certificate_sha256": certificate, "signing_key_created": False,
                  "signature_verified": True, "package_badging_verified": True, "payload_bytes_verified": True,
                  "runtime_manifest": runtime, "runtime_manifest_sha256": payloads["assets/runtime/runtime-manifest.json"]["sha256"],
                  "payloads": payloads, "changed_apk_payloads": sorted(CHANGED_PAYLOADS | ADDED_PAYLOADS),
                  "replaced_apk_payloads": sorted(CHANGED_PAYLOADS), "added_apk_payloads": sorted(ADDED_PAYLOADS),
                  "recompiled_dex": dex_pin, "donor_dex": donor["retained_dex"],
                  "retained_android_resources": donor["retained_android_resources"], "donor": donor_link(),
                  "retained_source_report": {"run_id": RETAINED_SOURCE_RUN_ID, "repository_commit": RETAINED_SOURCE_COMMIT,
                                             **RETAINED_SOURCE_BUILD},
                  "avatar_build_report": {"run_id": AVATAR_RUN_ID, "repository_commit": AVATAR_COMMIT, **AVATAR_BUILD},
                  "java_sources": source_pins, "changed_java_sources": changed_java, "added_java_sources": [JAVA_ADDITION],
                  "preserved_sources": {name: pin for name, pin in donor["preserved_sources"].items() if name not in JAVA_CHANGES},
                  "source_manifest": donor["source_manifest"], "generated_manifest": base.file_pin(manifest),
                  "qualification": qualification, "qualification_receipt": base.file_pin(args.qualification),
                  "testing_notes": base.file_pin(args.testing_notes), "native_libraries_changed": False,
                  "client_or_server_recompiled": False, "java_or_dex_recompiled": True, "world_assets_changed": False,
                  "unrelated_java_sources_preserved": True, "guest_source_derivative_scope_verified": True,
                  "physical_gameplay_validated": False,
                  "scope": "Phase-aware bounded Atlas gameplay and save windows retaining the complete published 0.11.2 native backend, world, avatar and save guards; physical phase behavior and outdoor save/reopen pending"}
        (args.output.parent / REPORT_NAME).write_text(json.dumps(report, indent=2) + "\n")
        args.output.with_suffix(".apk.sha256").write_text(report["sha256"] + "  " + APK_NAME + "\n")
        shutil.copyfile(args.testing_notes, args.output.parent / NOTES_NAME)
        print("Built focused retained-signer session-window candidate", report["sha256"])


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
    body += "[Focused phase-budget and save-guard qualification](https://github.com/" + REPOSITORY + "/actions/runs/" + os.environ.get("GITHUB_RUN_ID", "") + ").\n"
    release = api.request("/releases", {"tag_name": RELEASE_TAG, "target_commitish": report["repository_commit"],
        "name": "COH Atlas Gameplay 0.11.3 — bounded gameplay and save windows", "body": body, "draft": True,
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
            "Session-window publication requires the authorized continuation branch")
    report = read_json(args.build_report)
    donor = validate_lineage(args.donor_build_report, args.avatar_build_report, args.retained_source_report)
    with tempfile.TemporaryDirectory(prefix="coh-source-closure-") as temporary:
        _, source_pins, changed_java = current_java_sources(donor, Path(temporary))
    require(report.get("format") == 1 and report.get("apk") == APK_NAME and report.get("application_id") == base.APP_ID
            and report.get("version_name") == VERSION_NAME and report.get("version_code") == VERSION_CODE
            and report.get("repository_commit") == os.environ.get("GITHUB_SHA") and report.get("signer_certificate_sha256") == SIGNER
            and report.get("signing_key_created") is False
            and all(report.get(key) is True for key in ("signature_verified", "package_badging_verified", "payload_bytes_verified",
                "java_or_dex_recompiled", "unrelated_java_sources_preserved", "guest_source_derivative_scope_verified"))
            and all(report.get(key) is False for key in ("native_libraries_changed", "client_or_server_recompiled", "world_assets_changed", "physical_gameplay_validated"))
            and set(report.get("changed_apk_payloads", [])) == CHANGED_PAYLOADS | ADDED_PAYLOADS
            and set(report.get("replaced_apk_payloads", [])) == CHANGED_PAYLOADS
            and set(report.get("added_apk_payloads", [])) == ADDED_PAYLOADS
            and report.get("donor") == donor_link()
            and report.get("retained_source_report") == {"run_id": RETAINED_SOURCE_RUN_ID,
                "repository_commit": RETAINED_SOURCE_COMMIT, **RETAINED_SOURCE_BUILD}
            and report.get("avatar_build_report") == {"run_id": AVATAR_RUN_ID, "repository_commit": AVATAR_COMMIT, **AVATAR_BUILD}
            and report.get("java_sources") == source_pins and report.get("changed_java_sources") == changed_java
            and report.get("added_java_sources") == [JAVA_ADDITION]
            and report.get("preserved_sources") == {name: pin for name, pin in donor["preserved_sources"].items() if name not in JAVA_CHANGES}
            and report.get("source_manifest") == donor["source_manifest"]
            and report.get("donor_dex") == donor["retained_dex"]
            and report.get("retained_android_resources") == donor["retained_android_resources"],
            "Session-window build receipt or derivative boundaries differ")
    receipt = read_json(args.qualification)
    validate_qualification(receipt, report["repository_commit"])
    require(receipt == report.get("qualification") and base.file_pin(args.qualification) == report.get("qualification_receipt"),
            "Qualified phase-budget evidence changed")
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
                "Published verification metadata differs beyond phase-budget pins")
    base.verify_signer_output(base.run("java", "-jar", args.build_tools / "lib/apksigner.jar", "verify", "--verbose", "--print-certs", args.apk), SIGNER)
    current.verify_badging(base.run(args.build_tools / "aapt2", "dump", "badging", args.apk))
    base.checked_file(args.testing_notes, report["testing_notes"])
    checksum = args.apk.with_suffix(".apk.sha256")
    require(checksum.read_text() == report["sha256"] + "  " + APK_NAME + "\n", "Session-window checksum differs")
    public_notes = args.apk.parent / NOTES_NAME
    base.checked_file(public_notes, report["testing_notes"])
    spec = importlib.util.spec_from_file_location("coh_session_github", Path(__file__).with_name("build_atlas_gameplay_apk.py"))
    api_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_module)
    print("Published session-window prerelease:", publish_release(api_module.GitHub(os.environ.get("GH_TOKEN")), report,
          (args.apk, checksum, public_notes), public_notes.read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    get = commands.add_parser("download-donor")
    get.add_argument("--output", type=Path, required=True)
    create = commands.add_parser("build")
    for name in ("donor-apk", "donor-build-report", "avatar-build-report", "retained-source-report", "qualification", "android-jar", "build-tools", "keystore", "output"):
        create.add_argument("--" + name, type=Path, required=True)
    create.add_argument("--repository-commit")
    create.add_argument("--password-env", default="COH_INTERACTIVE_KEYSTORE_PASSWORD")
    create.add_argument("--testing-notes", type=Path, default=NOTES)
    release = commands.add_parser("publish")
    for name in ("apk", "build-report", "build-tools", "qualification", "donor-build-report", "avatar-build-report", "retained-source-report"):
        release.add_argument("--" + name, type=Path, required=True)
    release.add_argument("--testing-notes", type=Path, default=NOTES)
    args = parser.parse_args()
    for key, value in vars(args).items():
        if isinstance(value, Path):
            setattr(args, key, value.absolute())
    {"download-donor": download, "build": build, "publish": publish}[args.command](args)


if __name__ == "__main__":
    main()
