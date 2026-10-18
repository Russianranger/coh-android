"""Empty, nonce-owned HKCU key for a separate disposable development experiment.

Import and construction do not load a Windows DLL or access the registry. The
caller must source-admit this module before prepare(), and must use one owner
thread, the fresh hosted user's unchanged token, and an exclusive random nonce.
No other process may mutate the nonce or replace its ancestors. This is not an
atomic check/delete primitive against unrelated same-user registry writers.
"""

from dataclasses import dataclass
import os
import re
import threading


_VIEWS = (0x0200, 0x0100)  # KEY_WOW64_32KEY, KEY_WOW64_64KEY
_NEW = 1
_CODES = frozenset({
    'owned_instance_name_invalid', 'registry_wrong_thread', 'registry_busy',
    'services_already_started', 'services_not_stopped', 'registry_prepare_state',
    'registry_platform_refused', 'registry_api_failed', 'registry_close_failed',
    'registry_api_contract', 'registry_software_missing', 'registry_link_refused',
    'registry_nonce_preexisting', 'registry_view_layout_refused',
    'registry_parent_not_owned', 'registry_nonce_not_owned',
    'registry_key_not_empty', 'registry_nonce_still_present',
    'registry_parent_still_present', 'registry_owned_handle_missing',
})


class RegistryLeaseError(ValueError):
    """A fixed public code; native error text, paths and values never escape."""

    def __init__(self, code):
        super().__init__(code if code in _CODES else 'registry_api_failed')


@dataclass(frozen=True)
class KeyInfo:
    subkeys: int
    values: int
    is_link: bool = False


def client_project(owned_localdb_instance):
    """Derive the sole allowed app name from the existing owned LocalDB nonce."""
    if (type(owned_localdb_instance) is not str or
            re.fullmatch(r'cohauth-ci-[0-9a-f]{24}', owned_localdb_instance) is None):
        raise RegistryLeaseError('owned_instance_name_invalid')
    return 'coh-ci-' + owned_localdb_instance[len('cohauth-ci-'):]


class NativeRegistry:
    """Lazy 64-bit Windows binding; no values are read or written.

    open/create failure transfers no handle. Successful handles are noninherited;
    close failure retains caller ownership. Fixed HKCU SOFTWARE is opened, never
    created. REG_OPTION_OPEN_LINK prevents following the final component's link;
    inspect checks only counts and the SymbolicLinkValue *type*, never its data.
    HKCU SOFTWARE Cryptic is documented shared across WOW64 views on this scope.
    """

    def __init__(self):
        import ctypes as c
        if os.name != 'nt' or c.sizeof(c.c_void_p) != 8:
            raise RegistryLeaseError('registry_platform_refused')
        self._c = c
        self._dll = c.WinDLL('advapi32.dll', use_last_error=True, winmode=0x0800)
        h, d, p, s = c.c_void_p, c.c_uint32, c.c_void_p, c.c_wchar_p
        self._open = self._dll.RegOpenKeyExW
        self._open.argtypes, self._open.restype = [h, s, d, d, p], c.c_int32
        self._create = self._dll.RegCreateKeyExW
        self._create.argtypes = [h, s, d, s, d, d, p, p, p]
        self._create.restype = c.c_int32
        self._info = self._dll.RegQueryInfoKeyW
        self._info.argtypes, self._info.restype = [h, s] + [p] * 10, c.c_int32
        self._type = self._dll.RegQueryValueExW
        self._type.argtypes, self._type.restype = [h, s, p, p, p, p], c.c_int32
        self._delete = self._dll.RegDeleteKeyExW
        self._delete.argtypes, self._delete.restype = [h, s, d, d], c.c_int32
        self._close = self._dll.RegCloseKey
        self._close.argtypes, self._close.restype = [h], c.c_int32
        # HKEY_CURRENT_USER is a sign-extended LONG pseudo handle on Win64.
        self._hkcu = h(-2147483647)

    @staticmethod
    def _success(status):
        if status != 0:
            raise RegistryLeaseError('registry_api_failed')

    def open_software(self, view):
        return self.open(self._hkcu, 'SOFTWARE', view)

    def open(self, parent, component, view):
        handle = self._c.c_void_p()
        status = self._open(parent, component, 8, 0x2001F | view,
                            self._c.byref(handle))
        if status in (2, 3):  # ERROR_FILE_NOT_FOUND / ERROR_PATH_NOT_FOUND only
            return None
        self._success(status)
        if not handle.value:
            raise RegistryLeaseError('registry_api_contract')
        return handle.value

    def create(self, parent, component, view):
        handle, disposition = self._c.c_void_p(), self._c.c_uint32()
        self._success(self._create(parent, component, 0, None, 0,
                                   0x2001F | view, None,
                                   self._c.byref(handle), self._c.byref(disposition)))
        if not handle.value:
            raise RegistryLeaseError('registry_api_contract')
        return handle.value, disposition.value

    def inspect(self, handle):
        children, values = self._c.c_uint32(), self._c.c_uint32()
        self._success(self._info(handle, None, None, None,
                                 self._c.byref(children), None, None,
                                 self._c.byref(values), None, None, None, None))
        kind, size = self._c.c_uint32(), self._c.c_uint32()
        status = self._type(handle, 'SymbolicLinkValue', None,
                            self._c.byref(kind), None, self._c.byref(size))
        if status not in (0, 2):
            raise RegistryLeaseError('registry_api_failed')
        return KeyInfo(children.value, values.value, status == 0 and kind.value == 6)

    def delete(self, parent, component, view):
        self._success(self._delete(parent, component, view, 0))

    def close(self, handle):
        if self._close(handle) != 0:
            raise RegistryLeaseError('registry_close_failed')


class RegistryLease:
    """One owner, one prepare, retryable conservative cleanup of empty keys only.

    api is a trusted native-API adapter (or a controlled test double), not a value
    provider. This module never enumerates values/subkeys, writes values, changes
    security, deletes trees, or accepts caller-selected registry paths.

    The driver must pass strict True before services start and after *all* owned
    services and descendants have exited. The original getter leaks its key
    handle; process exit is therefore needed before final absence admission.
    Unexpected content refuses deletion and leaves the owner available to retry.
    """

    def __init__(self, owned_localdb_instance, *, api=None):
        self._project = client_project(owned_localdb_instance)
        self._api = api
        self._thread = threading.get_ident()
        self._busy = False
        self._state = 'new'
        self._handles = {}
        self._parent_owned = self._leaf_owned = False
        self._parent_deleted = self._leaf_deleted = False
        self._prepared = self._preflight_absent = False
        self._cleanup_attempted = self._stopped = self._clean = False
        self._nonce_absent = self._parent_absent = False
        self._failure = self._cleanup_failure = None
        self._secondary_close_failures = 0

    @property
    def client_project(self):
        return self._project

    def _enter(self):
        if threading.get_ident() != self._thread:
            raise RegistryLeaseError('registry_wrong_thread')
        if self._busy:
            raise RegistryLeaseError('registry_busy')
        self._busy = True

    @staticmethod
    def _code(error):
        code = str(error) if type(error) is RegistryLeaseError else None
        return code if code in _CODES else 'registry_api_failed'

    def snapshot(self):
        if threading.get_ident() != self._thread:
            raise RegistryLeaseError('registry_wrong_thread')
        return {
            'schema': 1, 'scope': 'empty_nonce_registry_lease',
            'client_project_derivation': 'owned_localdb_nonce',
            'prepare_attempted': self._state != 'new',
            'prepared': self._prepared,
            'preflight_absent_both_views': self._preflight_absent,
            'parent_created_by_lease': self._parent_owned,
            'nonce_created_by_lease': self._leaf_owned,
            'cleanup_attempted': self._cleanup_attempted,
            'services_stopped_confirmed': self._stopped,
            'nonce_absent_both_views': self._nonce_absent,
            'owned_parent_absent_both_views': self._parent_absent,
            'handles_closed': not self._handles,
            'cleanup_verified': self._clean,
            'failure': self._failure, 'cleanup_failure': self._cleanup_failure,
            'secondary_close_failures': self._secondary_close_failures,
            'source_inferred_getter_branch': 'existing_key_missing_installation_value_null',
            'registry_atomicity_claimed': False,
        }

    def _open(self, role, parent, component, view):
        if role in self._handles:
            raise RegistryLeaseError('registry_api_contract')
        handle = (self._api.open_software(view) if parent is None else
                  self._api.open(parent, component, view))
        if handle is not None:
            self._handles[role] = handle
        return handle

    def _close_roles(self, roles):
        first = None
        for role in tuple(roles):
            if role not in self._handles:
                continue
            try:
                self._api.close(self._handles[role])
                del self._handles[role]
            except Exception as error:
                self._secondary_close_failures = min(65535, self._secondary_close_failures + 1)
                if first is None:
                    first = error
        if first is not None:
            raise RegistryLeaseError('registry_close_failed') from None

    def _inspect(self, handle, *, empty=False):
        info = self._api.inspect(handle)
        if (not isinstance(info, KeyInfo) or type(info.subkeys) is not int or
                type(info.values) is not int or not 0 <= info.subkeys <= 0xFFFFFFFF or
                not 0 <= info.values <= 0xFFFFFFFF or type(info.is_link) is not bool):
            raise RegistryLeaseError('registry_api_contract')
        if info.is_link:
            raise RegistryLeaseError('registry_link_refused')
        if empty and (info.subkeys or info.values):
            raise RegistryLeaseError('registry_key_not_empty')

    def _create(self, role, parent, component, view, kind):
        handle, disposition = self._api.create(parent, component, view)
        # Record the successful handle before checking the disposition. An
        # unexpectedly existing key is closed, never assigned ownership/deleted.
        self._handles[role] = handle
        if type(disposition) is not int or disposition != _NEW:
            raise RegistryLeaseError('registry_' + kind + '_not_owned')
        if kind == 'parent':
            self._parent_owned = True
        else:
            self._leaf_owned = True
        self._inspect(handle, empty=True)
        return handle

    def _prepare(self):
        for view in _VIEWS:
            software = self._open(('software', view), None, None, view)
            if software is None:
                raise RegistryLeaseError('registry_software_missing')
            self._inspect(software)
            parent = self._open(('parent', view), software, 'Cryptic', view)
            if parent is not None:
                self._inspect(parent)
                leaf = self._open(('leaf', view), parent, self._project, view)
                if leaf is not None:
                    raise RegistryLeaseError('registry_nonce_preexisting')
        self._preflight_absent = True
        present = [('parent', view) in self._handles for view in _VIEWS]
        if present[0] != present[1]:
            raise RegistryLeaseError('registry_view_layout_refused')
        if not present[0]:
            self._create(('parent', _VIEWS[0]), self._handles['software', _VIEWS[0]],
                         'Cryptic', _VIEWS[0], 'parent')
            alias = self._open(('parent', _VIEWS[1]), self._handles['software', _VIEWS[1]],
                               'Cryptic', _VIEWS[1])
            if alias is None:
                raise RegistryLeaseError('registry_view_layout_refused')
            self._inspect(alias, empty=True)
        self._create(('leaf', _VIEWS[0]), self._handles['parent', _VIEWS[0]],
                     self._project, _VIEWS[0], 'nonce')
        alias = self._open(('leaf', _VIEWS[1]), self._handles['parent', _VIEWS[1]],
                           self._project, _VIEWS[1])
        if alias is None:
            raise RegistryLeaseError('registry_view_layout_refused')
        self._inspect(alias, empty=True)

    def prepare(self, *, owned_services_not_started):
        self._enter()
        try:
            if owned_services_not_started is not True:
                raise RegistryLeaseError('services_already_started')
            if self._state != 'new':
                raise RegistryLeaseError('registry_prepare_state')
            self._state = 'preparing'
            try:
                if self._api is None:
                    self._api = NativeRegistry()
                self._prepare()
                self._prepared = True
                self._state = 'prepared'
            except Exception as error:
                self._failure = self._code(error)
                self._state = 'failed'
                # No service has started by the explicit caller precondition.
                # Attempt every safe rollback step; retain ownership on refusal.
                self._cleanup_attempted = self._stopped = True
                try:
                    self._cleanup()
                except Exception as cleanup_error:
                    self._cleanup_failure = self._code(cleanup_error)
                    self._close_unneeded()
                raise RegistryLeaseError(self._failure) from None
            return self.snapshot()
        finally:
            self._busy = False

    def _verify_absent(self, *, parent=False):
        primary = None
        try:
            for view in _VIEWS:
                software = self._handles.get(('software', view))
                if software is None:
                    software = self._open(('software', view), None, None, view)
                    if software is None:
                        raise RegistryLeaseError('registry_software_missing')
                    self._inspect(software)
                key = self._open(('probe_parent', view), software, 'Cryptic', view)
                if key is not None:
                    self._inspect(key)
                    if parent:
                        raise RegistryLeaseError('registry_parent_still_present')
                    leaf = self._open(('probe_leaf', view), key, self._project, view)
                    if leaf is not None:
                        raise RegistryLeaseError('registry_nonce_still_present')
        except Exception as error:
            primary = error
        try:
            self._close_roles(role for role in self._handles if role[0].startswith('probe_'))
        except Exception as close_error:
            if primary is None:
                primary = close_error
        if primary is not None:
            raise primary

    def _cleanup(self):
        if self._api is None:
            raise RegistryLeaseError('registry_platform_refused')
        # Retry close failures of temporary verification handles first.
        self._close_roles(role for role in self._handles if role[0].startswith('probe_'))
        if self._leaf_owned and not self._leaf_deleted:
            leaf = self._handles.get(('leaf', _VIEWS[0]))
            parent = self._handles.get(('parent', _VIEWS[0]))
            if leaf is None or parent is None:
                raise RegistryLeaseError('registry_owned_handle_missing')
            for view in _VIEWS:
                handle = self._handles.get(('leaf', view))
                if handle is not None:
                    self._inspect(handle, empty=True)
            self._api.delete(parent, self._project, _VIEWS[0])
            self._leaf_deleted = True
        self._close_roles(role for role in self._handles if role[0] == 'leaf')
        self._verify_absent()
        self._nonce_absent = True
        if self._parent_owned and not self._parent_deleted:
            parent = self._handles.get(('parent', _VIEWS[0]))
            if parent is None:
                raise RegistryLeaseError('registry_owned_handle_missing')
            for view in _VIEWS:
                handle = self._handles.get(('parent', view))
                if handle is not None:
                    self._inspect(handle, empty=True)
            self._api.delete(self._handles['software', _VIEWS[0]], 'Cryptic', _VIEWS[0])
            self._parent_deleted = True
        self._close_roles(role for role in self._handles if role[0] == 'parent')
        if self._parent_owned:
            self._verify_absent(parent=True)
            self._parent_absent = True
        self._close_roles(tuple(self._handles))
        self._clean = True

    def _close_unneeded(self):
        # Keep original handles needed to prove a still-owned key's identity.
        # Independently attempt all other closes while preserving the first error.
        keep = set()
        if self._leaf_owned and not self._leaf_deleted:
            keep.update(('leaf', 'parent', 'software'))
        elif self._parent_owned and not self._parent_deleted:
            keep.update(('parent', 'software'))
        try:
            self._close_roles(role for role in self._handles if role[0] not in keep)
        except Exception:
            pass  # Fixed secondary count remains visible; primary is authoritative.

    def cleanup(self, *, services_stopped):
        try:
            self._enter()
        except RegistryLeaseError as error:
            # Wrong-thread callers cannot read/mutate the live owner's fields.
            return {'schema': 1, 'cleanup_verified': False, 'failure': str(error)}
        try:
            if services_stopped is not True:
                result = self.snapshot()
                result.update(cleanup_verified=False, services_stopped_confirmed=False,
                              cleanup_failure='services_not_stopped')
                return result
            self._cleanup_attempted = self._stopped = True
            if self._clean:
                return self.snapshot()
            try:
                self._cleanup()
                self._cleanup_failure = None
                self._state = 'closed'
            except Exception as error:
                self._cleanup_failure = self._code(error)
                self._close_unneeded()
            return self.snapshot()
        finally:
            self._busy = False
