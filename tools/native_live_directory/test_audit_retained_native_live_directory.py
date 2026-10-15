"""Read-only audit refusals using the authenticated original ARM evidence."""
from __future__ import annotations
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("retained_live_audit",HERE/"audit_retained_native_live_directory.py")
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
class RetainedAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive=Path(os.environ["COH_LIVE_RETAINED_ARM_ARTIFACT"])
        cls.manifest=json.loads(audit.MANIFEST.read_text())
        cls.members=audit.authenticate_zip(cls.archive,cls.manifest)
        with tempfile.TemporaryDirectory(prefix="coh-retained-ELF-check-") as td:
            so=Path(td)/"libcoh_live_directory.so";so.write_bytes(cls.members["out/native-live-directory-037/libcoh_live_directory.so"])
            cls.elf=subprocess.check_output(["readelf","--wide","--file-header","--program-headers","--dynamic","--dyn-syms",so],text=True)
    def test_full_original_artifact_and_source_inventory(self):
        self.assertEqual(len(self.members),43)
        source=audit.current_source(self.members,HERE.parents[1]);self.assertEqual(len(source),9)
    def test_original_failed_report_and_passed_components_remain_distinct(self):
        report,execution=audit.original_execution(self.members)
        self.assertEqual(report["status"],"failed");self.assertEqual(execution["static_Bionic_ARM64_controls"],26)
        self.assertFalse(report["shipping_admission"])
    def test_actual_ELF_has_unused_libdl_and_exact_eight_exports(self):
        result=audit.inspect_elf(self.elf)
        self.assertEqual(result["needed"],["libdl.so","libc.so"])
        self.assertEqual(result["LIBDL_undefined_imports"],0);self.assertEqual(len(result["JNI_exports"]),8)
    def test_changed_whole_zip_is_refused(self):
        manifest=copy.deepcopy(self.manifest);manifest["origin"]["sha256"]="0"*64
        with self.assertRaises(audit.AuditFailure):audit.authenticate_zip(self.archive,manifest)
    def test_oversized_intake_refuses_before_any_payload_open(self):
        with tempfile.TemporaryDirectory(prefix="coh-retained-size-refusal-") as td:
            p=Path(td)/"oversized.zip"
            with p.open("wb") as stream:stream.truncate(self.manifest["origin"]["bytes"]+1)
            with mock.patch.object(audit.os,"open",side_effect=AssertionError("Payload must not open")) as opened:
                with self.assertRaises(audit.AuditFailure):audit.authenticate_zip(p,self.manifest)
                opened.assert_not_called()
    def test_changed_member_pin_is_refused(self):
        manifest=copy.deepcopy(self.manifest);manifest["members"]["out/native-live-directory-037/libcoh_live_directory.so"]["sha256"]="0"*64
        with self.assertRaises(audit.AuditFailure):audit.authenticate_zip(self.archive,manifest)
    def test_unknown_dependency_is_refused(self):
        with self.assertRaises(audit.AuditFailure):audit.inspect_elf(self.elf.replace("[libdl.so]","[foreign.so]"))
    def test_libdl_symbol_use_is_refused(self):
        with self.assertRaises(audit.AuditFailure):audit.inspect_elf(self.elf.replace("getuid@LIBC","dlopen@LIBDL"))
    def test_wrong_machine_is_refused(self):
        with self.assertRaises(audit.AuditFailure):audit.inspect_elf(self.elf.replace("AArch64","X86_64"))
    def test_executable_stack_is_refused(self):
        lines=self.elf.splitlines()
        changed="\n".join(x.replace("RW  ","RWE ") if "GNU_STACK" in x else x for x in lines)
        with self.assertRaises(audit.AuditFailure):audit.inspect_elf(changed)
    def test_changed_JNI_scope_is_refused(self):
        with self.assertRaises(audit.AuditFailure):audit.inspect_elf(self.elf.replace(audit.PREFIX+"nativeOpen",audit.PREFIX+"unknownOpen"))
    def test_fabricated_original_overall_pass_is_refused(self):
        members=dict(self.members);name="out/native-live-directory-037/qualification.json";report=json.loads(members[name]);report["status"]="passed";members[name]=json.dumps(report).encode()
        with self.assertRaises(audit.AuditFailure):audit.original_execution(members)
    def test_unexecuted_Bionic_command_is_refused(self):
        members=dict(self.members);name="out/native-live-directory-037/qualification.json";report=json.loads(members[name]);next(x for x in report["commands"] if x["label"]=="execute-Bionic-ARM64-fixture")["exit_code"]=1;members[name]=json.dumps(report).encode()
        with self.assertRaises(audit.AuditFailure):audit.original_execution(members)
if __name__=="__main__":unittest.main(verbosity=2)
