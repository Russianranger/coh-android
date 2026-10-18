"""Controlled registry API model only. Never call Windows registry APIs."""

import argparse
import ctypes
from dataclasses import dataclass, field
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import platform
import sys
import threading
import unittest
from unittest import mock

import windows_registry_lease as r


INSTANCE = 'cohauth-ci-' + '0123456789abcdef01234567'
PROJECT = 'coh-ci-' + '0123456789abcdef01234567'
V32, V64 = 0x0200, 0x0100
ROOT = Path(__file__).resolve().parents[4]


@dataclass
class Node:
    parent: object = None
    name: str = ''
    children: dict = field(default_factory=dict)
    values: dict = field(default_factory=dict)
    link: bool = False
    deleted: bool = False


class MockRegistry:
    """Finite controlled API, including shared aliases and deferred key removal.

    Failure injection occurs before an API's effect. A successful create returns
    the real disposition and handle, exactly as the native adapter contract says.
    This is not a Windows kernel/API implementation or platform qualification.
    """

    all_calls = 0
    max_live_handles = 0
    failure_sites = {}
    native_binding_double_calls = 0

    def __init__(self, *, parent=False, shared=True):
        software = Node(name='SOFTWARE')
        self.software = {V32: software, V64: software if shared else Node(name='SOFTWARE')}
        if parent:
            for root in self.software.values():
                self.add(root, 'Cryptic')
        self.handles = {}
        self.next_handle = 1
        self.calls = []
        self.fail_at = set()
        self.hook = None

    @staticmethod
    def add(parent, name):
        name = name.casefold()
        if name not in parent.children:
            parent.children[name] = Node(parent, name)
        return parent.children[name]

    def _call(self, op, component=None, view=None):
        self.calls.append((op, component, view))
        MockRegistry.all_calls += 1
        if len(self.calls) in self.fail_at:
            raise r.RegistryLeaseError('registry_api_failed')
        if self.hook:
            self.hook(op, component, view)

    def _handle(self, node):
        result = self.next_handle
        self.next_handle += 1
        self.handles[result] = node
        MockRegistry.max_live_handles = max(MockRegistry.max_live_handles, len(self.handles))
        return result

    def _node(self, handle):
        node = self.handles[handle]
        if node.deleted:
            raise r.RegistryLeaseError('registry_api_failed')
        return node

    def open_software(self, view):
        self._call('software', 'SOFTWARE', view)
        node = self.software.get(view)
        return self._handle(node) if node else None

    def open(self, parent, component, view):
        self._call('open', component, view)
        node = self._node(parent).children.get(component.casefold())
        if node is not None and node.deleted:
            raise r.RegistryLeaseError('registry_api_failed')
        return self._handle(node) if node is not None else None

    def create(self, parent, component, view):
        self._call('create', component, view)
        node = self._node(parent)
        existed = component.casefold() in node.children
        child = self.add(node, component)
        return self._handle(child), 2 if existed else 1

    def inspect(self, handle):
        self._call('inspect')
        node = self._node(handle)
        return r.KeyInfo(len(node.children), len(node.values), node.link)

    def delete(self, parent, component, view):
        self._call('delete', component, view)
        node = self._node(parent).children[component.casefold()]
        if node.children:
            raise r.RegistryLeaseError('registry_api_failed')
        # RegDeleteKeyEx can delete values. The lease's prior empty check must
        # prevent that call for unexpected content within its exclusive scope.
        node.deleted = True
        self._remove_if_closed(node)

    def _remove_if_closed(self, node):
        if node.deleted and all(value is not node for value in self.handles.values()):
            node.parent.children.pop(node.name, None)

    def close(self, handle):
        self._call('close')
        node = self.handles.pop(handle)
        self._remove_if_closed(node)

    def cryptic(self, view=V32):
        return self.software[view].children.get('cryptic')

    def leaf(self, view=V32):
        parent = self.cryptic(view)
        return parent.children.get(PROJECT) if parent else None

    def deletes(self):
        return [row for row in self.calls if row[0] == 'delete']


class RegistryLeaseTests(unittest.TestCase):
    def lease(self, *, parent=False, shared=True):
        api = MockRegistry(parent=parent, shared=shared)
        return r.RegistryLease(INSTANCE, api=api), api

    def prepared(self, *, parent=False):
        lease, api = self.lease(parent=parent)
        receipt = lease.prepare(owned_services_not_started=True)
        self.assertTrue(receipt['prepared'])
        return lease, api

    def test_exact_nonce_derivation_and_no_constructor_api(self):
        self.assertEqual(r.client_project(INSTANCE), PROJECT)
        lease, api = self.lease()
        self.assertEqual(lease.client_project, PROJECT)
        self.assertEqual(api.calls, [])
        self.assertFalse(lease.snapshot()['prepare_attempted'])
        for value in (None, False, 1, b'cohauth-ci-' + b'a'*24, PROJECT,
                      'cohauth-ci-'+'A'*24, 'cohauth-ci-'+'a'*23,
                      'cohauth-ci-'+'a'*25, INSTANCE+'\n', INSTANCE+'\\other',
                      INSTANCE+'\0', 'MSSQLLocalDB', 'cohauth-ci-'+'0'*23+'g'):
            with self.subTest(value=repr(value)), self.assertRaisesRegex(
                    r.RegistryLeaseError, '^owned_instance_name_invalid$'):
                r.RegistryLease(value, api=api)
        self.assertEqual(api.calls, [])

    def test_import_and_constructor_never_load_native_binding(self):
        path = Path(r.__file__)
        name = '_registry_lease_import_control'
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            # On Linux WinDLL does not exist; creating the attribute also makes
            # this a control that will fail if import starts using native ctypes.
            with mock.patch('ctypes.WinDLL', create=True, side_effect=AssertionError('native forbidden')):
                spec.loader.exec_module(module)
                self.assertEqual(module.RegistryLease(INSTANCE).client_project, PROJECT)
        finally:
            del sys.modules[name]

    def test_prepare_requires_strict_not_started(self):
        for value in (False, None, 0, 1, 'true', [], object()):
            lease, api = self.lease()
            with self.subTest(value=type(value).__name__), self.assertRaisesRegex(
                    r.RegistryLeaseError, '^services_already_started$'):
                lease.prepare(owned_services_not_started=value)
            self.assertEqual(api.calls, [])
            self.assertFalse(lease.snapshot()['prepare_attempted'])

    def test_shared_views_one_create_and_one_delete_each_key(self):
        lease, api = self.prepared()
        self.assertIs(api.cryptic(V32), api.cryptic(V64))
        self.assertIs(api.leaf(V32), api.leaf(V64))
        self.assertEqual(api.leaf().values, {})
        self.assertEqual(api.leaf().children, {})
        creates = [row for row in api.calls if row[0] == 'create']
        self.assertEqual(creates, [('create', 'Cryptic', V32), ('create', PROJECT, V32)])
        self.assertEqual(lease.snapshot()['source_inferred_getter_branch'],
                         'existing_key_missing_installation_value_null')
        self.assertNotIn(PROJECT, json.dumps(lease.snapshot()))
        result = lease.cleanup(services_stopped=True)
        self.assertTrue(result['cleanup_verified'])
        self.assertTrue(result['nonce_absent_both_views'])
        self.assertTrue(result['owned_parent_absent_both_views'])
        self.assertTrue(result['handles_closed'])
        self.assertEqual(api.deletes(), [('delete', PROJECT, V32), ('delete', 'Cryptic', V32)])
        self.assertIsNone(api.cryptic())
        self.assertIsNone(api.cryptic(V64))
        self.assertEqual(api.handles, {})
        before = len(api.calls)
        self.assertEqual(lease.cleanup(services_stopped=True), result)
        self.assertEqual(len(api.calls), before)
        with self.assertRaisesRegex(r.RegistryLeaseError, '^registry_prepare_state$'):
            lease.prepare(owned_services_not_started=True)
        self.assertEqual(len(api.calls), before)

    def test_preexisting_parent_with_values_and_unrelated_subkey_preserved(self):
        lease, api = self.lease(parent=True)
        parent = api.cryptic()
        parent.values['unrelated-private-value'] = b'not exported'
        api.add(parent, 'other-product')
        before = repr(parent.values), set(parent.children)
        lease.prepare(owned_services_not_started=True)
        result = lease.cleanup(services_stopped=True)
        self.assertTrue(result['cleanup_verified'])
        self.assertFalse(result['parent_created_by_lease'])
        self.assertFalse(result['owned_parent_absent_both_views'])
        self.assertIs(api.cryptic(), parent)
        self.assertEqual((repr(parent.values), set(parent.children)), before)
        self.assertEqual(api.deletes(), [('delete', PROJECT, V32)])
        self.assertNotIn('not exported', json.dumps(result))
        self.assertEqual(api.handles, {})

    def test_preexisting_nonce_in_either_view_never_deleted(self):
        for shared, view in ((True, V32), (False, V32), (False, V64)):
            lease, api = self.lease(parent=True, shared=shared)
            node = api.add(api.cryptic(view), PROJECT.upper())
            node.values['private'] = b'do not delete'
            with self.subTest(shared=shared, view=view), self.assertRaisesRegex(
                    r.RegistryLeaseError, '^registry_nonce_preexisting$'):
                lease.prepare(owned_services_not_started=True)
            self.assertEqual(api.deletes(), [])
            self.assertEqual([row for row in api.calls if row[0] == 'create'], [])
            self.assertEqual(node.values, {'private': b'do not delete'})
            self.assertFalse(lease.snapshot()['cleanup_verified'])
            self.assertEqual(api.handles, {})

    def test_cleanup_requires_strict_stopped_and_leaves_live_handles(self):
        lease, api = self.prepared()
        before = len(api.calls)
        for value in (False, None, 0, 1, 'true', [], object()):
            result = lease.cleanup(services_stopped=value)
            self.assertFalse(result['cleanup_verified'])
            self.assertEqual(result['cleanup_failure'], 'services_not_stopped')
            self.assertFalse(result['services_stopped_confirmed'])
            self.assertEqual(len(api.calls), before)
            self.assertIsNotNone(api.leaf())
        self.assertTrue(lease.cleanup(services_stopped=True)['cleanup_verified'])

    def test_unexpected_leaf_values_or_children_refuse_all_delete(self):
        for content in ('value', 'subkey'):
            lease, api = self.prepared()
            leaf = api.leaf()
            if content == 'value':
                leaf.values['Installation Directory'] = b'private'
            else:
                api.add(leaf, 'unexpected')
            result = lease.cleanup(services_stopped=True)
            self.assertFalse(result['cleanup_verified'])
            self.assertEqual(result['cleanup_failure'], 'registry_key_not_empty')
            self.assertEqual(api.deletes(), [])
            self.assertIs(api.leaf(), leaf)
            self.assertTrue(api.handles)
            leaf.values.clear()
            leaf.children.clear()
            self.assertTrue(lease.cleanup(services_stopped=True)['cleanup_verified'])

    def test_created_parent_unexpected_content_preserved_after_leaf_removal(self):
        for content in ('value', 'subkey'):
            lease, api = self.prepared()
            parent = api.cryptic()
            if content == 'value':
                parent.values['private'] = b'preserve'
            else:
                api.add(parent, 'other-product')
            result = lease.cleanup(services_stopped=True)
            self.assertFalse(result['cleanup_verified'])
            self.assertTrue(result['nonce_absent_both_views'])
            self.assertEqual(api.deletes(), [('delete', PROJECT, V32)])
            self.assertIs(api.cryptic(), parent)
            parent.values.clear()
            parent.children.clear()
            self.assertTrue(lease.cleanup(services_stopped=True)['cleanup_verified'])

    def test_deferred_removal_and_original_process_handle_survival(self):
        lease, api = self.prepared()
        # Models the original getter's unclosed HKEY, not a running process.
        leaked_source_handle = api._handle(api.leaf())
        result = lease.cleanup(services_stopped=True)
        self.assertFalse(result['cleanup_verified'])
        self.assertFalse(result['nonce_absent_both_views'])
        self.assertEqual(api.deletes(), [('delete', PROJECT, V32)])
        api.close(leaked_source_handle)  # controlled model of actual process exit
        self.assertTrue(lease.cleanup(services_stopped=True)['cleanup_verified'])
        self.assertEqual(api.deletes(), [('delete', PROJECT, V32), ('delete', 'Cryptic', V32)])

    def test_wrong_thread_and_callback_reentry_do_not_touch_api(self):
        lease, api = self.lease()
        failures = []
        def foreign():
            try:
                lease.prepare(owned_services_not_started=True)
            except r.RegistryLeaseError as error:
                failures.append(str(error))
            failures.append(lease.cleanup(services_stopped=True)['failure'])
            try:
                lease.snapshot()
            except r.RegistryLeaseError as error:
                failures.append(str(error))
        thread = threading.Thread(target=foreign)
        thread.start()
        thread.join()
        self.assertEqual(failures, ['registry_wrong_thread']*3)
        self.assertEqual(api.calls, [])
        reentries = []
        def hook(op, component, view):
            before = len(api.calls)
            with self.assertRaisesRegex(r.RegistryLeaseError, '^registry_busy$'):
                lease.prepare(owned_services_not_started=True)
            self.assertEqual(lease.cleanup(services_stopped=True),
                             {'schema': 1, 'cleanup_verified': False, 'failure': 'registry_busy'})
            self.assertEqual(len(api.calls), before)
            reentries.append(op)
        api.hook = hook
        lease.prepare(owned_services_not_started=True)
        self.assertTrue(lease.cleanup(services_stopped=True)['cleanup_verified'])
        self.assertTrue(reentries)

    def test_shared_layout_required_never_creates_second_view(self):
        for parent in (False, True):
            lease, api = self.lease(parent=parent, shared=False)
            with self.subTest(parent=parent), self.assertRaisesRegex(
                    r.RegistryLeaseError, '^registry_view_layout_refused$'):
                lease.prepare(owned_services_not_started=True)
            self.assertTrue(lease.snapshot()['cleanup_verified'])
            self.assertTrue(all(row[2] == V32 for row in api.calls if row[0] == 'create'))
            self.assertIsNone(api.leaf(V32))
            self.assertIsNone(api.leaf(V64))
            self.assertEqual(api.handles, {})

    def test_asymmetric_parent_refuses_before_creation(self):
        lease, api = self.lease(shared=False)
        api.add(api.software[V64], 'Cryptic')
        with self.assertRaisesRegex(r.RegistryLeaseError, '^registry_view_layout_refused$'):
            lease.prepare(owned_services_not_started=True)
        self.assertEqual([row for row in api.calls if row[0] == 'create'], [])
        self.assertIsNotNone(api.cryptic(V64))
        self.assertEqual(api.handles, {})

    def test_never_creates_missing_software_or_follows_link(self):
        for target in ('software_missing', 'software_link', 'parent_link', 'leaf_link'):
            lease, api = self.lease(parent=target == 'parent_link')
            if target == 'software_missing':
                api.software[V32] = None
            elif target == 'software_link':
                api.software[V32].link = True
            elif target == 'parent_link':
                api.cryptic().link = True
            else:
                def set_link(op, component, view):
                    if op == 'open' and component == PROJECT and view == V64:
                        api.leaf().link = True
                api.hook = set_link
            with self.subTest(target=target), self.assertRaises(r.RegistryLeaseError):
                lease.prepare(owned_services_not_started=True)
            self.assertTrue(all(row[1] != 'SOFTWARE' for row in api.calls if row[0] == 'create'))
            if target != 'leaf_link':
                self.assertEqual(api.deletes(), [])
            else:
                self.assertEqual(lease.snapshot()['cleanup_failure'], 'registry_link_refused')
                self.assertEqual(api.deletes(), [])

    def test_native_create_disposition_existing_never_transfers_ownership(self):
        for target in ('Cryptic', PROJECT):
            lease, api = self.lease(parent=target == PROJECT)
            def create_race(op, component, view):
                if op == 'create' and component == target:
                    parent = api.software[view] if component == 'Cryptic' else api.cryptic(view)
                    api.add(parent, component)
            api.hook = create_race
            code = 'registry_parent_not_owned' if target == 'Cryptic' else 'registry_nonce_not_owned'
            with self.subTest(target=target), self.assertRaisesRegex(r.RegistryLeaseError, '^'+code+'$'):
                lease.prepare(owned_services_not_started=True)
            self.assertEqual(api.deletes(), [])
            self.assertFalse(lease.snapshot()['nonce_created_by_lease'])
            self.assertFalse(lease.snapshot()['parent_created_by_lease'])
            self.assertIsNotNone(api.cryptic())
            self.assertEqual(api.handles, {})

    def test_late_unowned_nonce_preserves_disposition_owned_parent(self):
        lease, api = self.lease()
        def create_race(op, component, view):
            if op == 'create' and component == PROJECT:
                api.add(api.cryptic(), PROJECT).values['private'] = b'preserve'
        api.hook = create_race
        with self.assertRaisesRegex(r.RegistryLeaseError, '^registry_nonce_not_owned$'):
            lease.prepare(owned_services_not_started=True)
        result = lease.snapshot()
        self.assertTrue(result['parent_created_by_lease'])
        self.assertFalse(result['nonce_created_by_lease'])
        self.assertFalse(result['cleanup_verified'])
        self.assertEqual(api.deletes(), [])
        self.assertEqual(api.leaf().values, {'private': b'preserve'})
        # Simulate the out-of-contract writer removing its own child; the lease
        # never deletes that unowned child. Only its original empty parent retires.
        api.cryptic().children.pop(PROJECT)
        api.hook = None
        self.assertTrue(lease.cleanup(services_stopped=True)['cleanup_verified'])
        self.assertEqual(api.deletes(), [('delete', 'Cryptic', V32)])
        self.assertEqual(api.handles, {})

    def test_all_prepare_api_failure_sites_roll_back_owned_effects(self):
        baseline, api = self.prepared()
        sites = len(api.calls)
        MockRegistry.failure_sites['prepare'] = sites
        baseline.cleanup(services_stopped=True)
        for at in range(1, sites+1):
            lease, api = self.lease()
            api.fail_at = {at}
            with self.subTest(at=at), self.assertRaisesRegex(r.RegistryLeaseError, '^registry_api_failed$'):
                lease.prepare(owned_services_not_started=True)
            self.assertEqual(lease.snapshot()['failure'], 'registry_api_failed')
            self.assertIsNone(api.leaf())
            self.assertIsNone(api.cryptic())
            self.assertEqual(api.handles, {})
            self.assertTrue(lease.snapshot()['cleanup_verified'])

    def test_all_cleanup_api_failure_sites_remain_false_until_safe_retry(self):
        baseline, api = self.prepared()
        first = len(api.calls)
        baseline.cleanup(services_stopped=True)
        sites = len(api.calls)-first
        MockRegistry.failure_sites['cleanup'] = sites
        for offset in range(1, sites+1):
            lease, api = self.prepared()
            api.fail_at = {len(api.calls)+offset}
            result = lease.cleanup(services_stopped=True)
            with self.subTest(offset=offset):
                self.assertFalse(result['cleanup_verified'])
                self.assertIsNotNone(result['cleanup_failure'])
                self.assertTrue(lease.cleanup(services_stopped=True)['cleanup_verified'])
                self.assertIsNone(api.cryptic())
                self.assertEqual(api.handles, {})

    def test_primary_preserved_and_later_closes_attempted_on_secondary_failure(self):
        lease, api = self.lease(parent=True)
        leaf = api.add(api.cryptic(), PROJECT)
        leaf.values['private'] = b'not public'
        def hook(op, component, view):
            if op == 'close':
                raise RuntimeError('arbitrary private registry text')
        api.hook = hook
        with self.assertRaisesRegex(r.RegistryLeaseError, '^registry_nonce_preexisting$'):
            lease.prepare(owned_services_not_started=True)
        snapshot = lease.snapshot()
        self.assertEqual(snapshot['failure'], 'registry_nonce_preexisting')
        self.assertFalse(snapshot['cleanup_verified'])
        self.assertGreaterEqual(snapshot['secondary_close_failures'], 3)
        self.assertGreaterEqual(sum(row[0] == 'close' for row in api.calls), 3)
        self.assertNotIn('private', json.dumps(snapshot))
        self.assertNotIn('arbitrary', json.dumps(snapshot))
        api.hook = None
        result = lease.cleanup(services_stopped=True)
        self.assertFalse(result['cleanup_verified'])  # preexisting nonce survives
        self.assertEqual(api.handles, {})
        self.assertEqual(api.deletes(), [])

    def test_info_shape_and_arbitrary_api_error_fail_closed(self):
        for value in (None, r.KeyInfo(True, 0), r.KeyInfo(-1, 0),
                      r.KeyInfo(0, 2**32), r.KeyInfo(0, 0, 1)):
            lease, api = self.lease()
            api.inspect = lambda handle, value=value: value
            with self.subTest(value=value), self.assertRaisesRegex(
                    r.RegistryLeaseError, '^registry_api_contract$'):
                lease.prepare(owned_services_not_started=True)
            self.assertEqual(api.deletes(), [])
        lease, api = self.lease()
        api.hook = lambda *args: (_ for _ in ()).throw(RuntimeError('private native path'))
        with self.assertRaisesRegex(r.RegistryLeaseError, '^registry_api_failed$'):
            lease.prepare(owned_services_not_started=True)
        self.assertNotIn('private', json.dumps(lease.snapshot()))

    def test_native_adapter_prototypes_flags_and_metadata_only_calls(self):
        class Function:
            def __init__(self, callback):
                self.callback = callback
            def __call__(self, *args):
                return self.callback(*args)
        class DLL:
            def __init__(self):
                self.calls, self.status, self.link = [], {}, False
                for name in ('RegOpenKeyExW', 'RegCreateKeyExW', 'RegQueryInfoKeyW',
                             'RegQueryValueExW', 'RegDeleteKeyExW', 'RegCloseKey'):
                    setattr(self, name, Function(lambda *args, name=name: self.call(name, args)))
            def call(self, name, args):
                self.calls.append((name, args))
                status = self.status.get(name, 0)
                if status:
                    return status
                if name == 'RegOpenKeyExW':
                    ctypes.cast(args[4], ctypes.POINTER(ctypes.c_void_p)).contents.value = 77
                elif name == 'RegCreateKeyExW':
                    ctypes.cast(args[7], ctypes.POINTER(ctypes.c_void_p)).contents.value = 88
                    ctypes.cast(args[8], ctypes.POINTER(ctypes.c_uint32)).contents.value = 1
                elif name == 'RegQueryInfoKeyW':
                    ctypes.cast(args[4], ctypes.POINTER(ctypes.c_uint32)).contents.value = 3
                    ctypes.cast(args[7], ctypes.POINTER(ctypes.c_uint32)).contents.value = 4
                elif name == 'RegQueryValueExW':
                    if not self.link:
                        return 2
                    ctypes.cast(args[3], ctypes.POINTER(ctypes.c_uint32)).contents.value = 6
                    ctypes.cast(args[5], ctypes.POINTER(ctypes.c_uint32)).contents.value = 1024
                return 0
        dll = DLL()
        with mock.patch.object(r.os, 'name', 'nt'), mock.patch(
                'ctypes.WinDLL', create=True, return_value=dll) as loader:
            native = r.NativeRegistry()
        loader.assert_called_once_with('advapi32.dll', use_last_error=True, winmode=0x0800)
        self.assertEqual(len(dll.RegOpenKeyExW.argtypes), 5)
        self.assertEqual(len(dll.RegCreateKeyExW.argtypes), 9)
        self.assertEqual(len(dll.RegQueryInfoKeyW.argtypes), 12)
        self.assertEqual(len(dll.RegQueryValueExW.argtypes), 6)
        self.assertEqual(len(dll.RegDeleteKeyExW.argtypes), 4)
        self.assertEqual(len(dll.RegCloseKey.argtypes), 1)
        for name in ('RegOpenKeyExW', 'RegCreateKeyExW', 'RegQueryInfoKeyW',
                     'RegQueryValueExW', 'RegDeleteKeyExW', 'RegCloseKey'):
            self.assertIs(getattr(dll, name).restype, ctypes.c_int32)
        self.assertEqual(native.open_software(V32), 77)
        _, args = dll.calls[-1]
        self.assertEqual(args[0].value, (1 << 64)-2147483647)
        self.assertEqual(args[1:4], ('SOFTWARE', 8, 0x2001F | V32))
        self.assertEqual(native.open(77, 'Cryptic', V64), 77)
        self.assertEqual(dll.calls[-1][1][:4], (77, 'Cryptic', 8, 0x2001F | V64))
        self.assertEqual(native.create(77, PROJECT, V32), (88, 1))
        self.assertEqual(dll.calls[-1][1][:7], (77, PROJECT, 0, None, 0, 0x2001F | V32, None))
        self.assertEqual(native.inspect(88), r.KeyInfo(3, 4, False))
        dll.link = True
        self.assertEqual(native.inspect(88), r.KeyInfo(3, 4, True))
        for name, args in dll.calls:
            if name == 'RegQueryValueExW':
                self.assertEqual(args[1], 'SymbolicLinkValue')
                self.assertIsNone(args[2])
                self.assertIsNone(args[4])  # no value-body destination buffer
        native.delete(77, PROJECT, V32)
        self.assertEqual(dll.calls[-1], ('RegDeleteKeyExW', (77, PROJECT, V32, 0)))
        native.close(88)
        self.assertEqual(dll.calls[-1], ('RegCloseKey', (88,)))
        for status in (2, 3):
            dll.status['RegOpenKeyExW'] = status
            self.assertIsNone(native.open(77, PROJECT, V32))
        dll.status['RegOpenKeyExW'] = 5
        with self.assertRaisesRegex(r.RegistryLeaseError, '^registry_api_failed$'):
            native.open(77, PROJECT, V32)
        for name, call in (('RegCreateKeyExW', lambda: native.create(77, PROJECT, V32)),
                           ('RegQueryInfoKeyW', lambda: native.inspect(88)),
                           ('RegQueryValueExW', lambda: native.inspect(88)),
                           ('RegDeleteKeyExW', lambda: native.delete(77, PROJECT, V32))):
            dll.status = {name: 5}
            with self.subTest(name=name), self.assertRaisesRegex(r.RegistryLeaseError, '^registry_api_failed$'):
                call()
        dll.status = {'RegCloseKey': 5}
        with self.assertRaisesRegex(r.RegistryLeaseError, '^registry_close_failed$'):
            native.close(88)
        MockRegistry.native_binding_double_calls = len(dll.calls)

    def test_source_contract_pins_and_controlled_branch_projection(self):
        source = (ROOT/'upstream/ouroboros/libs/UtilitiesLib/src/version/AppRegCache.c').read_text()
        start = source.index('const char* regGetInstallationDir(void){')
        end = source.index('\n\nstatic RegReader rr = 0;', start)
        getter = source[start:end]
        for token in ('RegCreateKeyExA(', 'KEY_READ | KEY_WRITE',
                      'if(REG_CREATED_NEW_KEY == disposition)', 'return NULL;',
                      'RegQueryValueExA(', '"Installation Directory"'):
            self.assertIn(token, getter)
        self.assertNotIn('RegCloseKey', getter)
        self.assertLess(getter.index('if(REG_CREATED_NEW_KEY == disposition)'),
                        getter.index('RegQueryValueExA('))
        # Source-derived branch projection only, not execution of original C.
        def original_fresh_getter(created, values):
            if created:
                return None, 'created_immediate_null'
            return values.get('Installation Directory'), 'existing_query'
        self.assertEqual(original_fresh_getter(True, {}), (None, 'created_immediate_null'))
        self.assertEqual(original_fresh_getter(False, {}), (None, 'existing_query'))
        cfg = (ROOT/'upstream/ouroboros/Common/dbserver/servercfg.c').read_text()
        db = (ROOT/'upstream/ouroboros/DBServer/src/dbinit.c').read_text()
        self.assertIn('else if (stricmp(s,"ClientProject")==0)', cfg)
        self.assertIn('regSetAppName(server_cfg.client_project);', db)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    paths = [Path(__file__).resolve(), Path(r.__file__).resolve(),
             ROOT/'native-android/engine/auth-interop/deployment/WINDOWS-REGISTRY-LEASE.md',
             ROOT/'upstream/ouroboros/libs/UtilitiesLib/src/version/AppRegCache.c',
             ROOT/'upstream/ouroboros/libs/UtilitiesLib/src/version/AppVersion.c',
             ROOT/'upstream/ouroboros/Common/dbserver/servercfg.c',
             ROOT/'upstream/ouroboros/DBServer/src/dbinit.c',
             ROOT/'native-android/engine/auth-interop/deployment/hosted_auth_stage.py']
    before = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    if args.output and (args.output.exists() or args.output.is_symlink()):
        parser.error('output_must_be_fresh')
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RegistryLeaseTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    after = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    if after != before:
        raise ValueError('source_changed_during_mock_qualification')
    receipt = {'schema': 1, 'scope': 'source_and_controlled_mock_registry_only',
               'passed': result.wasSuccessful(), 'test_methods': result.testsRun,
               'failures': len(result.failures), 'errors': len(result.errors),
               'controlled_api_calls': MockRegistry.all_calls,
               'controlled_max_live_handles': MockRegistry.max_live_handles,
               'controlled_failure_sites': MockRegistry.failure_sites,
               'controlled_native_binding_double_calls': MockRegistry.native_binding_double_calls,
               'python_version': platform.python_version(),
               'host_platform': sys.platform,
               'source_sha256': before,
               'actual_windows_registry_executed': False,
               'original_c_compiled_or_executed': False,
               'services_compiled_or_started': False,
               'development_activation_qualified': False,
               'atomicity_against_unrelated_same_user_writers': False}
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
