"""Fresh Linux controls for NEW dormant owner; no recovered-count inheritance."""
from dataclasses import replace
import json
import os
from pathlib import Path
import pickle
import stat
import tempfile
import threading
import unittest
from unittest.mock import patch

import owner as m


class OwnerControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="coh-new-owner-host-")
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)
        self.parent.chmod(0o700)
        self.operation = m.CurrentOperation("a" * 32, "1792000000000-" + "b" * 12,
            "12345678-1234-1234-1234-123456789abc", os.getuid(), self.parent.stat().st_dev)
        self.registry = m.PrivateSecrets()
        self.owner = None

    def create(self):
        owner = m.FixtureOwner.create(self.parent, self.operation, self.registry)
        self.addCleanup(owner.close)
        self.owner = owner
        return owner

    def refused(self, function, reason=None):
        with self.assertRaises(m.Refusal) as error:
            function()
        if reason:
            self.assertEqual(str(error.exception), reason)
        self.assertNotIn(str(self.parent), str(error.exception))
        for secret in self.registry._values:
            self.assertNotIn(secret, str(error.exception))

    def child_path(self, ticket):
        return self.parent / self.owner._root_name / ("child-%d.json" % ticket.index)

    def parser_bytes(self, child, raw):
        """Parser-only corruption fixture; not admitted as unchanged custody."""
        os.ftruncate(child.fd, 0)
        os.pwrite(child.fd, raw, 0)
        child.identity = m._file_identity(os.fstat(child.fd))
        return lambda: self.owner._read_document(child)

    def test_new_root_is_exclusive_private_and_all_descriptors_cloexec(self):
        owner = self.create()
        root = self.parent / owner._root_name
        self.assertEqual(stat.S_IMODE(root.stat().st_mode), 0o700)
        self.assertEqual(root.stat().st_uid, os.getuid())
        self.assertTrue(all(not os.get_inheritable(fd) for fd in owner._fds))
        self.assertFalse(list(root.iterdir()))
        self.assertTrue(owner.close()["cleanup_complete"])
        self.assertFalse(root.exists())

    def test_child_document_matches_current_operation_and_is_private(self):
        owner = self.create()
        ticket = owner.issue_child()
        path = self.child_path(ticket)
        document = json.loads(path.read_bytes())
        self.assertEqual(document["operation_id"], self.operation.operation_id)
        self.assertEqual(document["session_id"], self.operation.session_id)
        self.assertEqual(document["process_instance"], self.operation.process_instance)
        self.assertEqual(document["auth_nonce"], ticket._nonce)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(path.stat().st_nlink, 1)
        self.assertFalse(os.get_inheritable(owner._children[1].fd))

    def test_ninth_issue_has_zero_rng_redaction_io_or_state_effects(self):
        owner = self.create()
        for _ in range(8):
            owner.issue_child()
        children_before = dict(owner._children)
        secrets_before = set(self.registry._values)
        files_before = {p.name: (p.read_bytes(), p.stat()) for p in (self.parent / owner._root_name).iterdir()}
        poisoned_before = owner._poisoned
        with patch.object(m.secrets, "token_hex", side_effect=AssertionError("RNG effect")) as rng, \
             patch.object(self.registry, "remember", side_effect=AssertionError("redaction effect")) as remember, \
             patch.object(owner, "_check_live", side_effect=AssertionError("lifecycle effect")) as live, \
             patch.object(m.os, "open", side_effect=AssertionError("open effect")) as opened, \
             patch.object(m.os, "write", side_effect=AssertionError("write effect")) as written:
            self.refused(owner.issue_child, "child_limit")
        for mocked in (rng, remember, live, opened, written):
            mocked.assert_not_called()
        self.assertEqual(owner._children, children_before)
        self.assertEqual(self.registry._values, secrets_before)
        self.assertEqual(owner._poisoned, poisoned_before)
        for p in (self.parent / owner._root_name).iterdir():
            raw, info = files_before[p.name]
            self.assertEqual(p.read_bytes(), raw)
            self.assertEqual(m._file_identity(p.stat()), m._file_identity(info))

    def test_consumed_children_still_count_toward_eight_issued_limit(self):
        owner = self.create()
        for _ in range(8):
            self.assertEqual(owner.consume_child(owner.issue_child())["decision"], "consumed_once")
        self.assertEqual(len(os.listdir(owner._root_fd)), 0)
        with patch.object(m.secrets, "token_hex", side_effect=AssertionError("must not run")):
            self.refused(owner.issue_child, "child_limit")
        self.assertTrue(owner.close()["cleanup_complete"])

    def test_child_is_one_use_and_second_attempt_poisons_owner(self):
        owner = self.create()
        ticket = owner.issue_child()
        report = owner.consume_child(ticket)
        self.assertNotIn(ticket._nonce, json.dumps(report))
        self.assertFalse(report["runtime_admission"])
        self.assertFalse(self.child_path(ticket).exists())
        self.refused(lambda: owner.consume_child(ticket), "child_already_used")
        self.refused(owner.issue_child, "owner_poisoned")

    def test_forged_ticket_with_same_nonce_and_index_is_refused(self):
        owner = self.create()
        ticket = owner.issue_child()
        forged = m.ChildTicket(ticket.index, ticket._nonce)
        self.refused(lambda: owner.consume_child(forged), "foreign_ticket")

    def test_ticket_from_other_current_owner_is_refused(self):
        first = self.create()
        ticket = first.issue_child()
        other_parent = self.parent / "other"
        other_parent.mkdir(mode=0o700)
        other = m.FixtureOwner.create(other_parent, self.operation, m.PrivateSecrets())
        self.addCleanup(other.close)
        self.refused(lambda: other.consume_child(ticket), "foreign_ticket")

    def test_duplicate_nonce_is_refused_and_never_written(self):
        owner = self.create()
        ticket = owner.issue_child()
        with patch.object(m.secrets, "token_hex", return_value=ticket._nonce):
            self.refused(owner.issue_child, "fresh_nonce_required")
        self.assertEqual(len(owner._children), 1)
        self.assertEqual(len(os.listdir(owner._root_fd)), 1)

    def test_parallel_issuance_cannot_exceed_eight(self):
        owner = self.create()
        results, failures = [], []
        def issue():
            try:
                results.append(owner.issue_child())
            except m.Refusal as error:
                failures.append(str(error))
        threads = [threading.Thread(target=issue) for _ in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(results), 8)
        self.assertEqual(failures, ["child_limit"] * 8)
        self.assertEqual(len({ticket._nonce for ticket in results}), 8)

    def test_untyped_context_cannot_create_files(self):
        self.refused(lambda: m.FixtureOwner.create(self.parent, {}, self.registry), "typed_context_required")
        self.assertFalse(list(self.parent.iterdir()))

    def test_wrong_uid_context_cannot_create_files(self):
        self.operation = replace(self.operation, real_uid=os.getuid() + 1)
        self.refused(lambda: m.FixtureOwner.create(self.parent, self.operation, self.registry), "operation_refused")
        self.assertFalse(list(self.parent.iterdir()))

    def test_wrong_device_context_cannot_create_files(self):
        self.operation = replace(self.operation, device=self.operation.device + 1)
        self.refused(lambda: m.FixtureOwner.create(self.parent, self.operation, self.registry), "private_parent_required")
        self.assertFalse(list(self.parent.iterdir()))

    def test_shared_parent_mode_refused(self):
        self.parent.chmod(0o750)
        self.refused(lambda: m.FixtureOwner.create(self.parent, self.operation, self.registry), "private_parent_required")

    def test_symlink_parent_refused_without_following(self):
        alias = self.parent / "alias"
        target = self.parent / "target"
        target.mkdir(mode=0o700)
        alias.symlink_to(target, target_is_directory=True)
        self.refused(lambda: m.FixtureOwner.create(alias, self.operation, self.registry))
        self.assertFalse(list(target.iterdir()))

    def test_noncanonical_parent_refused(self):
        for path in (str(self.parent) + "/", str(self.parent) + "/../" + self.parent.name,
                     str(self.parent) + "/./", "relative"):
            self.refused(lambda path=path: m.FixtureOwner.create(path, self.operation, self.registry), "parent_path_refused")

    def test_root_retarget_refuses_and_cleanup_leaves_replacement_untouched(self):
        owner = self.create()
        ticket = owner.issue_child()
        original = self.parent / owner._root_name
        moved = self.parent / "owned-moved"
        original.rename(moved)
        original.mkdir(mode=0o700)
        sentinel = original / "user-file"
        sentinel.write_text("preserve")
        self.refused(lambda: owner.consume_child(ticket), "fixture_root_changed")
        report = owner.close()
        self.assertFalse(report["cleanup_complete"])
        self.assertEqual(sentinel.read_text(), "preserve")
        self.assertFalse((moved / "child-1.json").exists())

    def test_ancestor_rename_retarget_refuses(self):
        private = self.parent / "private"
        private.mkdir(mode=0o700)
        owner = m.FixtureOwner.create(private, self.operation, self.registry)
        self.addCleanup(owner.close)
        ticket = owner.issue_child()
        private.rename(self.parent / "moved-private")
        private.mkdir(mode=0o700)
        self.refused(lambda: owner.consume_child(ticket), "ancestor_changed")
        self.assertFalse(owner.close()["cleanup_complete"])

    def test_root_permission_sharing_refused(self):
        owner = self.create()
        ticket = owner.issue_child()
        (self.parent / owner._root_name).chmod(0o750)
        self.refused(lambda: owner.consume_child(ticket), "fixture_root_changed")

    def test_unexpected_file_or_subdirectory_refused_and_not_deleted(self):
        for subdirectory in (False, True):
            with self.subTest(subdirectory=subdirectory):
                owner = self.create()
                ticket = owner.issue_child()
                foreign = self.parent / owner._root_name / "foreign"
                foreign.mkdir() if subdirectory else foreign.write_text("preserve")
                self.refused(lambda: owner.consume_child(ticket))
                self.assertFalse(owner.close()["cleanup_complete"])
                self.assertTrue(foreign.exists())

    def test_directory_membership_scan_is_bounded_before_collecting_foreign_tree(self):
        owner = self.create()
        root = self.parent / owner._root_name
        for index in range(9):
            (root / ("foreign-%d" % index)).touch()
        self.refused(owner.issue_child, "fixture_membership_bound")
        self.assertFalse(owner.close()["cleanup_complete"])
        self.assertEqual(len(list(root.iterdir())), 9)

    def test_child_symlink_retarget_refused_and_target_untouched(self):
        owner = self.create()
        ticket = owner.issue_child()
        path = self.child_path(ticket)
        path.unlink()
        sentinel = self.parent / "user-file"
        sentinel.write_text("preserve")
        path.symlink_to(sentinel)
        self.refused(lambda: owner.consume_child(ticket), "child_custody_changed")
        self.assertFalse(owner.close()["cleanup_complete"])
        self.assertEqual(sentinel.read_text(), "preserve")
        self.assertTrue(path.is_symlink())

    def test_child_same_name_replacement_refused_and_not_deleted(self):
        owner = self.create()
        ticket = owner.issue_child()
        path = self.child_path(ticket)
        original_bytes = path.read_bytes()
        path.unlink()
        path.write_bytes(original_bytes)
        path.chmod(0o600)
        self.refused(lambda: owner.consume_child(ticket), "child_custody_changed")
        self.assertFalse(owner.close()["cleanup_complete"])
        self.assertEqual(path.read_bytes(), original_bytes)

    def test_child_hardlink_sharing_refused_and_alias_preserved(self):
        owner = self.create()
        ticket = owner.issue_child()
        alias = self.parent / "shared-alias"
        os.link(self.child_path(ticket), alias)
        self.refused(lambda: owner.consume_child(ticket), "child_custody_changed")
        self.assertFalse(owner.close()["cleanup_complete"])
        self.assertEqual(alias.stat().st_nlink, 2)

    def test_child_mode_change_refused(self):
        owner = self.create()
        ticket = owner.issue_child()
        self.child_path(ticket).chmod(0o640)
        self.refused(lambda: owner.consume_child(ticket), "child_custody_changed")

    def test_child_byte_mutation_refused_without_repinning(self):
        owner = self.create()
        ticket = owner.issue_child()
        path = self.child_path(ticket)
        raw = path.read_bytes().replace(b'"format":1', b'"format":2')
        path.write_bytes(raw)
        self.refused(lambda: owner.consume_child(ticket), "child_custody_changed")

    def test_during_read_retarget_is_detected(self):
        owner = self.create()
        ticket = owner.issue_child()
        path = self.child_path(ticket)
        real_read = m.os.pread
        def retarget(fd, count, offset):
            raw = real_read(fd, count, offset)
            path.unlink()
            path.write_bytes(raw)
            path.chmod(0o600)
            return raw
        with patch.object(m.os, "pread", side_effect=retarget):
            self.refused(lambda: owner.consume_child(ticket), "child_custody_changed")
        self.assertTrue(owner._children[1].consumed)

    def test_parser_rejects_duplicate_key_and_redacts_both_nonce_values(self):
        owner = self.create()
        ticket = owner.issue_child()
        injected = "f" * 64
        raw = ('{"auth_nonce":"' + ticket._nonce + '","auth_nonce":"' + injected + '"}').encode()
        self.refused(self.parser_bytes(owner._children[1], raw), "duplicate_json_key")
        self.assertEqual(self.registry.redact(ticket._nonce + injected), "[private][private]")

    def test_parser_rejects_non_ascii(self):
        owner = self.create()
        owner.issue_child()
        self.refused(self.parser_bytes(owner._children[1], b'{"bad":"\xc3\xa9"}'), "non_ascii_document")

    def test_parser_rejects_nonfinite_constant(self):
        owner = self.create()
        owner.issue_child()
        self.refused(self.parser_bytes(owner._children[1], b'{"bad":NaN}'), "invalid_constant")

    def test_parser_rejects_unknown_fields(self):
        owner = self.create()
        ticket = owner.issue_child()
        value = json.loads(self.child_path(ticket).read_bytes())
        value["grants_admission"] = True
        self.refused(self.parser_bytes(owner._children[1], json.dumps(value).encode()), "document_fields_refused")

    def test_parser_rejects_boolean_integer_and_old_operation(self):
        for key, value in (("format", True), ("child_index", True), ("operation_id", "1792000000001-" + "b" * 12)):
            with self.subTest(key=key):
                owner = self.create()
                ticket = owner.issue_child()
                document = json.loads(self.child_path(ticket).read_bytes())
                document[key] = value
                self.refused(self.parser_bytes(owner._children[1], json.dumps(document).encode()), "current_document_mismatch")

    def test_oversize_file_refused_with_bounded_read(self):
        owner = self.create()
        ticket = owner.issue_child()
        self.child_path(ticket).write_bytes(b"x" * (m.MAX_DOCUMENT_BYTES + 1))
        with patch.object(m.os, "pread", side_effect=AssertionError("must refuse before read")):
            self.refused(lambda: owner.consume_child(ticket), "child_custody_changed")

    def test_process_change_blocks_use_and_forked_cleanup_never_unlinks(self):
        owner = self.create()
        ticket = owner.issue_child()
        path = self.child_path(ticket)
        # PID observation is a stand-in; this is not a Wine child lifecycle test.
        owner._lock.acquire()
        with patch.object(m.os, "getpid", return_value=owner._pid + 1):
            self.refused(lambda: owner.consume_child(ticket), "process_changed")
            self.refused(owner.issue_child, "process_changed")
            report = owner.close()
        owner._lock.release()
        self.assertFalse(report["cleanup_complete"])
        self.assertEqual(report["reasons"], ["foreign_process_cleanup_refused"])
        self.assertTrue(path.exists())

    def test_closed_fd_and_reused_fd_identity_refused(self):
        owner = self.create()
        ticket = owner.issue_child()
        fd = owner._children[1].fd
        os.close(fd)
        replacement = os.open(self.parent, os.O_RDONLY | os.O_DIRECTORY)
        self.addCleanup(os.close, replacement)
        self.refused(lambda: owner.consume_child(ticket))
        self.assertFalse(owner.close()["cleanup_complete"])
        # Closing the owner must not close an unrelated reused descriptor.
        self.assertTrue(stat.S_ISDIR(os.fstat(replacement).st_mode))

    def test_partial_root_creation_cannot_claim_complete_cleanup(self):
        original_open = m.os.open
        created = []
        original_close = m.FixtureOwner.close
        reports = []
        def fail_after_mkdir(path, flags, *args, **kwargs):
            if str(path).startswith("live-fixture-"):
                created.append(path)
                raise PermissionError("injected host-only refusal")
            return original_open(path, flags, *args, **kwargs)
        def capture(owner):
            report = original_close(owner)
            reports.append(report)
            return report
        with patch.object(m.os, "open", side_effect=fail_after_mkdir), \
             patch.object(m.FixtureOwner, "close", new=capture):
            self.refused(lambda: m.FixtureOwner.create(self.parent, self.operation, self.registry), "fixture_creation_cleanup_incomplete")
        self.assertEqual(len(created), 1)
        self.assertFalse(reports[0]["cleanup_complete"])
        self.assertIn("unanchored_created_root_cleanup_refused", reports[0]["reasons"])
        self.assertTrue((self.parent / created[0]).is_dir())

    def test_fresh_child_fstat_failure_closes_unpublished_fd_and_keeps_gate_closed(self):
        owner = self.create()
        real_fstat = m.os.fstat
        captured = []
        def failing_fstat(fd):
            info = real_fstat(fd)
            if stat.S_ISREG(info.st_mode) and info.st_size == 0:
                captured.append(fd)
                raise OSError("injected fresh child fstat refusal")
            return info
        with patch.object(m.os, "fstat", side_effect=failing_fstat):
            self.refused(owner.issue_child, "private_issue_refused")
        self.assertEqual(len(captured), 1)
        with self.assertRaises(OSError):
            real_fstat(captured[0])
        self.assertFalse(owner.close()["cleanup_complete"])
        self.assertEqual(len(list((self.parent / owner._root_name).iterdir())), 1)

    def test_fresh_directory_fstat_failure_closes_unpublished_fd(self):
        real_fstat = m.os.fstat
        captured = []
        def failing_fstat(fd):
            captured.append(fd)
            raise OSError("injected fresh directory fstat refusal")
        with patch.object(m.os, "fstat", side_effect=failing_fstat):
            self.refused(lambda: m.FixtureOwner.create(self.parent, self.operation, self.registry), "fixture_creation_refused")
        self.assertEqual(len(captured), 1)
        with self.assertRaises(OSError):
            real_fstat(captured[0])
        self.assertFalse(list(self.parent.iterdir()))

    def test_short_write_failure_is_poisoned_and_cleanup_closes_owned_fds(self):
        owner = self.create()
        with patch.object(m.os, "write", return_value=0):
            self.refused(owner.issue_child, "short_private_write")
        self.refused(owner.issue_child, "owner_poisoned")
        descriptors = list(owner._fds) + [c.fd for c in owner._children.values()]
        self.assertTrue(owner.close()["cleanup_complete"])
        for fd in descriptors:
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_cleanup_is_idempotent_closed_owner_cannot_issue(self):
        owner = self.create()
        ticket = owner.issue_child()
        first = owner.close()
        self.assertEqual(first, owner.close())
        self.assertTrue(first["cleanup_complete"])
        self.assertNotIn(ticket._nonce, json.dumps(first))
        self.refused(owner.issue_child, "owner_closed")

    def test_cleanup_report_cannot_mutate_recorded_reasons(self):
        owner = self.create()
        root = self.parent / owner._root_name
        (root / "foreign").touch()
        first = owner.close()
        first["reasons"].clear()
        self.assertFalse(owner.close()["cleanup_complete"])
        self.assertEqual(owner.close()["reasons"], ["root_cleanup_custody_refused"])

    def test_private_credential_owner_ticket_are_not_serializable_or_in_repr(self):
        owner = self.create()
        ticket = owner.issue_child()
        for value in (owner, ticket, self.registry):
            self.assertNotIn(ticket._nonce, repr(value))
            with self.assertRaises(TypeError):
                pickle.dumps(value)


if __name__ == "__main__":
    unittest.main(verbosity=2)
