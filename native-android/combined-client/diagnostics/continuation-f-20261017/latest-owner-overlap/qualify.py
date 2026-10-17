#!/usr/bin/env python3
"""Source-bound host layouts and named-overlap arithmetic; no module replay."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ENGINE = "native-android/engine/"
WR = ENGINE + "world-render-adapter/"
CHAR = ENGINE + "character-dictionary/"
DIAG = "native-android/combined-client/diagnostics/continuation-f-20261017/"
RECEIPTS = {
    "parent_reference": DIAG + "parent-phase-replay.json",
    "sealed_source": ENGINE + "scenecatalog/evidence/source-sealed-complete-host.json",
    "lod": WR + "qualification/lod-cache-20261017/host.json",
    "model_policy": WR + "qualification/model-material-policy-20261017/host.json",
    "join": CHAR + "qualification/power-join-20261017-final.json.gz",
    "ids": CHAR + "qualification/power-ids-20261017-final.json.gz",
    "shared": CHAR + "qualification/shared-power-sets-20261017-final.json.gz",
    "presentation": WR + "qualification/presentation-e1b844b88-host.json",
}
TYPES = ("CohWrBudget", "CohWrSnapshot", "CohWrMailbox", "CohWrBindings",
         "CohWrFrame", "CohWrPreparedFrame", "CohWrPresentation", "CohWrDrawInput",
         "CohRenderVertex", "CohPowerStreamDictionary", "CohPowerJoin",
         "CohPowerJoinWorkspace", "CohPowerIDs", "CohPowerIDsWorkspace",
         "CohSharedPowerSets", "CohSharedPowerSetsWorkspace",
         "CohWrModelMaterialInput", "CohWrModelMaterialPart", "CohWrModelMaterialProjection")
PRIVATE_TYPES = TYPES[:7]
OPTIONAL_LAYOUTS = {
    WR + "coh_wr_trick_model.h": ("CohWrTrickModelQuery", "CohWrTrickModelLimits", "CohWrTrickModelSelection"),
    CHAR + "coh_schedules.h": ("CohSchedules", "CohSchedulesWorkspace"),
    CHAR + "coh_power_boost_slots.h": ("CohPowerBoostSlots", "CohPowerBoostSlotsWorkspace"),
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(argv):
    try:
        return subprocess.check_output(list(map(str, argv)), text=True, stderr=subprocess.STDOUT, timeout=60)
    except subprocess.CalledProcessError as error:
        raise ValueError("inspection tool refused:\n" + error.output[-4000:]) from error


def receipt(root, relative, historical_reference=False):
    raw = (root / relative).read_bytes()
    value = json.loads(gzip.decompress(raw) if relative.endswith(".gz") else raw)
    require(value["passed"] is True, "failed receipt " + relative)
    checked = 0
    remapped = {}
    changes = {}
    for name, digest in value.get("source_sha256", {}).items():
        source_relative = name
        if Path(name).is_absolute():
            matches = [name.split("/" + marker, 1)[1] for marker in ("native-android/", "upstream/") if "/" + marker in name]
            require(len(matches) == 1, "unmapped historical source path " + name)
            marker = "native-android/" if "/native-android/" in name else "upstream/"
            source_relative = marker + matches[0]
            remapped[name] = source_relative
        path = (root / source_relative).resolve()
        require(path.is_relative_to(root), "source hash escapes checkout")
        actual = sha(path.read_bytes())
        if actual != digest:
            require(historical_reference, "receipt source changed " + name)
            changes[source_relative] = {"historical_sha256": digest, "current_sha256": actual}
        checked += 1
    return value, {"path": relative, "bytes": len(raw), "sha256": sha(raw),
                   "source_hash_entries_checked": checked,
                   "historical_absolute_path_comparison_only_remapping": remapped,
                   "historical_source_changes_no_current_execution_requalification": changes}


def closure(root, seeds):
    pending = [root / name for name in seeds]
    result = {}
    while pending:
        path = pending.pop().resolve()
        require(path.is_relative_to(root), "include escapes checkout")
        name = path.relative_to(root).as_posix()
        if name in result:
            continue
        raw = path.read_bytes()
        result[name] = sha(raw)
        for include in re.findall(r'^#include "([^\"]+)"', raw.decode(), re.M):
            child = path.parent / include
            if child.is_file():
                pending.append(child)
    return result


def layouts(root):
    """Compile actual C definitions; compare verbatim declarations under C++."""
    original = (root / (WR + "coh_world_render.c")).read_text()
    original += "\n" + (root / (WR + "coh_wr_presentation.inc")).read_text()
    declarations = []
    for name in PRIVATE_TYPES:
        matches = re.findall(r"struct " + name + r"\s*\{.*?\};", original, re.S)
        require(len(matches) == 1, "private declaration count " + name)
        declarations.append(matches[0])
    common = "struct FLayout { const char *name; size_t size, alignment; };\n"
    headers = [WR + "coh_world_render.h", WR + "coh_wr_presentation.h",
               CHAR + "coh_shared_power_sets.h", WR + "coh_wr_model_material.h"]
    types = list(TYPES)
    for header, names in OPTIONAL_LAYOUTS.items():
        if (root / header).is_file():
            headers.append(header)
            types.extend(names)
    includes = "".join('#include "' + str(root / name) + '"\n' for name in headers)
    entries = ",\n".join('{"' + name + '",sizeof(' + name + '),ALIGN(' + name + ')}' for name in types)
    c = ('#include "' + str(root / (WR + "coh_world_render.c")) + '"\n' + includes + common
         + "#define ALIGN(T) _Alignof(T)\nstatic const struct FLayout rows[]={\n" + entries
         + "};\nconst struct FLayout *f_owner_layout(size_t *n){*n=sizeof(rows)/sizeof(rows[0]);return rows;}\n")
    cpp = ("#include <atomic>\n#include <cstdio>\n#include <cstring>\n#include <pthread.h>\n" + includes
           + "using atomic_uint=std::atomic_uint;\n" + "\n".join(declarations) + "\n" + common
           + 'extern "C" const FLayout *f_owner_layout(size_t*);\n'
           + "#define ALIGN(T) alignof(T)\nstatic const FLayout expected[]={\n" + entries + "};\n"
           + 'int main(){size_t n=0;const FLayout *p=f_owner_layout(&n);'
           + 'if(n!=sizeof(expected)/sizeof(expected[0]))return 1;std::printf("{");'
           + 'for(size_t i=0;i<n;i++){if(std::strcmp(p[i].name,expected[i].name)||p[i].size!=expected[i].size||p[i].alignment!=expected[i].alignment)return 2;'
           + 'std::printf("%s\\\"%s\\\":{\\\"bytes\\\":%zu,\\\"alignment\\\":%zu}",i?",":"",p[i].name,p[i].size,p[i].alignment);}'
           + 'std::printf("}\\n");return 0;}\n')
    with tempfile.TemporaryDirectory(prefix="coh-f-owner-layout-") as raw:
        work = Path(raw)
        (work / "layout.c").write_text(c)
        (work / "layout.cpp").write_text(cpp)
        run(["cc", "-std=c11", "-O2", "-ffunction-sections", "-fdata-sections", "-c", work / "layout.c", "-o", work / "layout.o"])
        run(["c++", "-std=c++11", "-O2", "-Wall", "-Wextra", "-Werror", "-ffunction-sections", work / "layout.cpp", work / "layout.o", "-Wl,--gc-sections", "-lpthread", "-lm", "-o", work / "layout"])
        result = json.loads(run([work / "layout"]))
    return result, {"C": sha(c.encode()), "C++": sha(cpp.encode()),
                    "verbatim_private_declarations": sha("\n".join(declarations).encode()),
                    "C_compiler": run(["cc", "--version"]).splitlines()[0],
                    "C++_compiler": run(["c++", "--version"]).splitlines()[0],
                    "matching_size_and_alignment": True,
                    "module_functions_or_captures_executed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    require(not args.output.exists(), "output must be fresh")
    seeds = [WR + "coh_world_render.c", CHAR + "coh_shared_power_sets.h", WR + "coh_wr_model_material.h",
             WR + "coh_wr_lod_cache.c", ENGINE + "scenecatalog/coh_source_sealed.c",
             ENGINE + "scenecatalog/tests/test_source_sealed.c", WR + "coh_wr_trick_detached.h",
             WR + "coh_wr_tex_dependencies.h"]
    seeds.extend(header for header in OPTIONAL_LAYOUTS if (root / header).is_file())
    hashes = closure(root, seeds)
    proofs, identities = {}, {}
    for role, path in RECEIPTS.items():
        # Receipts remain historical behavior witnesses. New source extensions
        # may append functions without changing these layouts; record every
        # source difference rather than silently requalifying old executions.
        proofs[role], identities[role] = receipt(root, path, True)
    sizes, build = layouts(root)
    size = lambda name: sizes[name]["bytes"]
    for role, name in (("join", "CohPowerJoin"), ("ids", "CohPowerIDs"), ("shared", "CohSharedPowerSets")):
        row = proofs[role]["modes"]["release"]["checks"][0]
        require(size(name) == row["owner_bytes"] == row["workspace_bytes"], "qualified owner layout " + role)
    parent = proofs["parent_reference"]["modes"]["release"]
    cap = 96 * 1024 * 1024
    require(parent["old_candidate_transition"] == 100074681 and parent["after_retirement_and_sets"] == 67361231, "reference phase identity")
    lod = proofs["lod"]["modes"]["release"]
    owners = {"B_LOD_raw_cache_metadata": lod["cache_owned_bytes"],
              "B_LOD_dictionary_retaining_cache": lod["dictionary_owned_bytes"],
              "C_streamed_power_dictionary_metadata": size("CohPowerStreamDictionary"),
              "C_complete_forward_join": size("CohPowerJoin"),
              "C_sorted_ID_view": size("CohPowerIDs"),
              "C_shared_set_layout": size("CohSharedPowerSets")}
    for role, source in (("lod", WR + "coh_wr_lod_cache.c"), ("lod", WR + "coh_wr_lod_cache.h"),
                         ("model_policy", WR + "coh_wr_model_material.c"),
                         ("model_policy", WR + "coh_wr_model_material.h")):
        require(proofs[role]["source_sha256"][source] == sha((root / source).read_bytes()), "owner source identity " + source)
    if "CohSchedules" in sizes:
        owners["C_schedules_if_new_header_present"] = size("CohSchedules")
    if "CohPowerBoostSlots" in sizes:
        owners["C_boost_slot_projection_if_new_header_present"] = size("CohPowerBoostSlots")
    additional = sum(owners.values())
    phases = []
    for label, baseline in (("old_plus_candidate_reference_before_external_cleanup", parent["old_candidate_transition"]),
                            ("reference_after_explicit_cleanup_and_existing_power_sets", parent["after_retirement_and_sets"])):
        total = baseline + additional
        phases.append({"phase": label, "reference_bytes": baseline, "additional_named_owners": additional,
                       "total_named_lower_bound": total, "allowance": cap - total,
                       "fits_named_cap_before_unmeasured_charges": total <= cap})
    # One explicit per-part adaptation scenario, not a claim that production
    # geometry identities are already selected or that all source meshes fit.
    sealed = proofs["sealed_source"]["modes"]["release"]["result"]
    draws = sealed["parts"]
    source_bar_payload = sealed["packet_bytes"]
    context = size("CohWrBudget") + size("CohWrPresentation") + size("CohWrMailbox")
    snapshot = size("CohWrSnapshot") + draws * size("CohWrDrawInput") + source_bar_payload
    bundle = size("CohWrPreparedFrame") + size("CohWrFrame") + size("CohWrBindings") + draws * (8 + 26)
    policy = size("CohWrModelMaterialProjection")
    selection = size("CohWrTrickModelSelection") if "CohWrTrickModelSelection" in sizes else 0
    base = phases[1]["total_named_lower_bound"]
    consumer = {"assumption": "one distinct geometry identity per source part; 21 descriptors; only bar ordinal26509 payload is known here",
                "draws": draws, "known_bar_parts": 12, "known_bar_payload_bytes": source_bar_payload,
                "other_plaza_payload_charged": False, "selected_actor_payload_charged": False,
                "adapter_context_bytes": context, "one_snapshot_lower_bound": snapshot,
                "one_frame_binding_bundle_bytes": bundle, "one_caller_policy_result_bytes": policy,
                "one_caller_model_selection_result_if_present": selection,
                "one_snapshot_plus_one_bundle_total": base + context + snapshot + bundle + policy + selection,
                "two_snapshots_plus_two_bundles_total": base + context + 2 * (snapshot + bundle) + policy + selection,
                "same_snapshot_camera_publications_share_geometry": True,
                "actual_consumer_instantiated": False}
    consumer["one_snapshot_named_allowance"] = cap - consumer["one_snapshot_plus_one_bundle_total"]
    consumer["two_snapshot_named_allowance"] = cap - consumer["two_snapshots_plus_two_bundles_total"]
    require(all(sha((root / name).read_bytes()) == digest for name, digest in hashes.items()), "source changed during audit")
    result = {"schema": "coh-source-bound-latest-owner-overlap-v1", "passed": True,
              "source_revision": run(["git", "-C", root, "rev-parse", "HEAD"]).strip(),
              "audit_source_sha256": sha(Path(__file__).read_bytes()), "source_sha256": hashes,
              "audit_handoff_sha256": sha((HERE / "HANDOFF.md").read_bytes()),
              "qualified_receipts": identities, "host_layouts": sizes, "host_layout_build": build,
              "old_world_phase_numbers_are_historical_reference_not_current_pipeline_measurements": True,
              "cap_bytes": cap, "new_named_owner_bytes": owners, "new_named_owner_total": additional,
              "reference_phase_comparisons": phases, "conditional_E_consumer_overlap": consumer,
              "preparation_workspace_bytes": {"join": size("CohPowerJoinWorkspace"), "IDs": size("CohPowerIDsWorkspace"),
                  "shared_sets": size("CohSharedPowerSetsWorkspace"), "optional_prior_shared_layout": size("CohSharedPowerSets")},
              "excluded_required_charges": ["LOD whole loader reservation/blob/provider/control peaks",
                  "power stream provider context/handles and scratch", "all other preparation stacks/runtime peaks",
                  "unmeasured actor and omitted plaza geometry", "effective texture/material/GPU/driver and resource provider owners"],
              "retirement_boundary": {"source": WR + "coh_world_render.c::prepare",
                  "condition": "only successful complete synchronous validation/copy return, then release all independent material/source borrowers",
                  "actual_existing_owner_release": ENGINE + "scenecatalog/coh_source_sealed.c::coh_source_sealed_free",
                  "actual_existing_deferred_callback": WR + "coh_wr_presentation.inc::coh_wr_presentation_collect -> resources.drop",
                  "source_payload_is_live_during_copy": True, "callback_is_currently_real_source_provider": False,
                  "graph_required_for_future_GROUPS_deltas_must_remain": True,
                  "external_GEO_loader_FILE_requires_actual_trim_destroy_close": True,
                  "arithmetic_credit_taken": False, "production_handoff_executed": False},
              "A_capture_tools_are_host_MapServer_PostgreSQL_scope_not_client_96MiB_owners": True,
              "literal_child_caps_do_not_automatically_become_parent_tickets": True,
              "current_parent_module_adapter_exists": False, "actual_owner_retirement_observed_by_this_audit": False,
              "Android_ABI_checked": False, "RSS_measured": False, "startup_improvement_measured": False,
              "world_authority": False}
    for name in ("CohSchedulesWorkspace", "CohPowerBoostSlotsWorkspace"):
        if name in sizes:
            result["preparation_workspace_bytes"][name] = size(name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps({"passed": True, "new_named_owner_total": additional,
                      "old_candidate_named_overage": -phases[0]["allowance"],
                      "C_CPP_size_alignment_match": True, "world_authority": False}))


if __name__ == "__main__":
    main()
