#!/usr/bin/env python3
"""One private original-server transaction and fixed numeric projection.

The accepted supervisor remains byte-exact. Scoped capability views select its
existing lifecycle hooks after separate exact admission of the NEW Map/native
roles. Neither view is a receipt, artifact equivalence claim or public result.
"""
from __future__ import annotations

import argparse
from contextlib import AbstractContextManager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORE_DIR = ROOT / 'native-android/engine/scenecatalog-server'
MAP_RECIPE = ROOT / 'native-android/tools/server-initial-observer-20261018/recipe.py'
SOURCE_SCHEMA = ROOT / 'native-android/engine/initial-capture/server-initial-observer/schema.py'
RECEIVE_ADMISSION = ROOT / ('native-android/combined-client/diagnostics/gates25-27-thor-20261018/'
                          'server-initial-investigation-worker-c/receive_admission.py')
ACTUAL_MAP_ROLE = 'nonshipping_same_owner_initial_send_observer'
ACTUAL_NATIVE_SCHEMA = 'coh-initial-receive-focused-v1'
MAP_CAPABILITY = 'nonshipping_fresh_callback_sealed_groups_observer'
NATIVE_CAPABILITY = 'coh-initial-progress-focused-v1'
PRIVATE_SCHEMA = 'coh-private-server-initial-runtime-admission-v1'
PUBLIC_SCHEMA = 'coh-server-initial-runtime-public-v1'
MAX_PUBLIC_BYTES = 16 * 1024


def require(value):
    if not value:
        raise ValueError('SERVER_INITIAL_RUNTIME_REFUSED')


def load(name, path):
    path = path.resolve()
    existing = sys.modules.get(name)
    if existing is not None:
        require(Path(existing.__file__).resolve() == path)
        return existing
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module


def context():
    sys.path.insert(0, str(CORE_DIR))
    try:
        import capture_groups_transaction as core
        from fresh_callback_observer import runtime as fresh
        from fresh_callback_observer import probe
        import initial_progress_admission as progress
        import summarize_groups_capture as summary
    finally:
        sys.path.pop(0)
    for module, path in ((core, CORE_DIR / 'capture_groups_transaction.py'),
                         (fresh, CORE_DIR / 'fresh_callback_observer/runtime.py'),
                         (probe, CORE_DIR / 'fresh_callback_observer/probe.py'),
                         (progress, CORE_DIR / 'initial_progress_admission.py'),
                         (summary, CORE_DIR / 'summarize_groups_capture.py')):
        require(Path(module.__file__).resolve() == path)
    ledger = load('coh_server_initial_runtime_ledger', HERE / 'ledger.py')
    return core, fresh, probe, progress, summary, ledger


def suppliers():
    recipe = load('coh_server_initial_map_recipe', MAP_RECIPE)
    receive = load('coh_server_initial_receive_admission', RECEIVE_ADMISSION)
    source = load('coh_server_initial_ledger_schema', SOURCE_SCHEMA)
    require(recipe.ROLE == ACTUAL_MAP_ROLE and receive.BUILD_SCHEMA == ACTUAL_NATIVE_SCHEMA)
    return recipe, receive, source


class Bridge(AbstractContextManager):
    """Single-call adaptation of fixed, separately admitted capabilities.

    Every patched attribute is restored on exit, including an exception. The
    actual new receipt bytes/hashes/roles are preserved; only internal dispatch
    copies contain old capability selectors. No source file is modified.
    """
    active = False

    def __init__(self, args, core, fresh, probe, progress, ledger, recipe, receive, source):
        self.args = args
        self.core, self.fresh, self.probe, self.progress = core, fresh, probe, progress
        self.ledger, self.recipe, self.receive, self.source = ledger, recipe, receive, source
        self.saved = []
        self.actual_map = self.actual_native = None
        self.owner = self.child = self.raw = self.binding = None
        self.diagnostic = ledger.empty()
        self.precreate_refused = False

    def replace(self, module, name, replacement):
        previous = getattr(module, name)
        self.saved.append((module, name, previous))
        setattr(module, name, replacement)
        return previous

    def __enter__(self):
        require(not Bridge.active)
        Bridge.active = True
        try:
            self.install()
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *_):
        for module, name, previous in reversed(self.saved):
            setattr(module, name, previous)
        self.saved.clear()
        Bridge.active = False
        return False

    def install(self):
        core, fresh = self.core, self.fresh
        recipe, receive, args = self.recipe, self.receive, self.args

        def inspect(directory, root, pin):
            require(Path(directory) == args.compile_directory and root == ROOT
                    and pin == args.compile_receipt_sha256)
            actual, staged = recipe.verify_artifact(directory, root, args.source_revision, pin)
            require(actual.get('build_role') == ACTUAL_MAP_ROLE)
            if self.actual_map is not None:
                require(actual == self.actual_map)
            self.actual_map = actual
            view = dict(actual)
            view['build_role'] = MAP_CAPABILITY
            return view, staged

        self.replace(core.admit, 'inspect', inspect)

        def native_input(binary, receipt, pin, root=ROOT):
            require(Path(binary) == args.native_capture and Path(receipt) == args.native_build_receipt
                    and pin == args.native_build_receipt_sha256 and root == ROOT)
            actual = receive.native_input(binary, receipt, pin, root)
            require(actual.get('build_schema') == ACTUAL_NATIVE_SCHEMA
                    and actual.get('initial_progress_compatibility_verified') is True)
            self.actual_native = actual
            view = dict(actual)
            view['build_schema'] = NATIVE_CAPABILITY
            return view

        self.replace(core, 'native_input', native_input)
        original_paths = core.orchestration_source_paths

        def source_paths(compiled=None, native=None):
            paths = set(original_paths(compiled, native))
            paths.update(recipe.checkout_closure(ROOT))
            paths.update((p.relative_to(ROOT).as_posix() for p in
                          (HERE / 'runtime.py', HERE / 'ledger.py', RECEIVE_ADMISSION, SOURCE_SCHEMA)))
            require(self.actual_native is not None)
            paths.update(self.actual_native['dependencies_sha256'])
            return paths

        self.replace(core, 'orchestration_source_paths', source_paths)
        original_unchanged = core.compiled_inputs_unchanged

        def unchanged(a, native, compiled):
            require(a is args)
            if not original_unchanged(a, native, compiled):
                return False
            actual, _ = recipe.verify_artifact(args.compile_directory, ROOT, args.source_revision,
                                               args.compile_receipt_sha256)
            require(actual == self.actual_map)
            return True

        self.replace(core, 'compiled_inputs_unchanged', unchanged)
        original_precreate = fresh.precreate

        def precreate(compiled, path):
            owner = original_precreate(compiled, path)
            try:
                require(path.name == 'source-profile-probe.json')
                self.owner = self.probe.precreate(path.parent / self.ledger.BASENAME)
            except Exception:
                self.precreate_refused = True
            return owner

        self.replace(fresh, 'precreate', precreate)
        original_start = core.start_owned

        def start(children, handles, logs, work, label, command, cwd, env):
            if label == 'map':
                require(work == args.work and cwd == args.work / 'map-runtime'
                        and self.actual_map is not None)
                env = dict(env)
                # Only this actual owned Map child receives the fixed private sink.
                if self.owner is not None:
                    require(self.probe._path_info(self.owner).st_size == 0)
                    env[self.ledger.ENVIRONMENT] = self.ledger.WINDOWS_PATH
            return original_start(children, handles, logs, work, label, command, cwd, env)

        self.replace(core, 'start_owned', start)
        original_bind = fresh.bind

        def bind(owner, child, streams, children, handles):
            original_bind(owner, child, streams, children, handles)
            self.child = child
            if self.owner is not None:
                try:
                    self.probe.bind(self.owner, child, streams, children, handles)
                except Exception:
                    self.precreate_refused = True

        self.replace(fresh, 'bind', bind)
        original_record = fresh.record

        def record(report, owner, child, *, cleanup_attempted):
            original_record(report, owner, child, cleanup_attempted=cleanup_attempted)
            diagnostic, binding, raw = self.ledger.collect(self.probe, self.source.parse,
                                                          self.owner, child, report)
            if self.precreate_refused:
                diagnostic = self.ledger.empty('REFUSED')
                binding = raw = None
            self.diagnostic, self.binding, self.raw = diagnostic, binding, raw

        self.replace(fresh, 'record', record)

        def finish(report, native, received, target):
            require(self.actual_map is not None and self.actual_native is not None)
            # The receive helper explicitly verifies compatibility, then delegates
            # only initial/progress retention to the accepted implementation.
            try:
                receive.finish(core, report, self.actual_native, received, target)
            except Exception:
                # The original GROUPS transaction and independently completed
                # cleanup survive an optional new receiver diagnostic failure.
                report['initial_observation'] = core.initial_status('REFUSED')
                report['receive_diagnostic'] = {'state': 'REFUSED'}
            report['native_tool'] = dict(self.actual_native)
            report['server_initial_runtime'] = {
                'schema': PRIVATE_SCHEMA, 'server_build_role': ACTUAL_MAP_ROLE,
                'native_build_schema': ACTUAL_NATIVE_SCHEMA,
                'source_revision': args.source_revision,
                'compile_receipt_sha256': args.compile_receipt_sha256,
                'native_build_receipt_sha256': args.native_build_receipt_sha256,
                'map_binary': self.actual_map['artifacts']['MapServer.exe'],
                'new_role_artifact_admission_verified': True,
                'compatibility_views_only_select_existing_lifecycle_hooks': True,
                'historical_artifact_equivalence_claimed': False,
                'public_upload_permitted': False}
            diagnostic = self.diagnostic
            try:
                if self.raw is not None:
                    self.ledger.paired(report)
                    self.probe._closed(self.owner, self.child)
                    require(self.probe._read_owned(self.owner) == self.raw)
                    self.ledger.retain(args.output / self.ledger.BASENAME, self.raw, self.progress.read_private)
                    report['server_initial_private_binding'] = self.binding
            except Exception:
                diagnostic = self.ledger.empty('REFUSED')
                report.pop('server_initial_private_binding', None)
            try:
                report['server_initial_diagnostic'] = self.ledger.public(diagnostic, self.source.parse)
            except Exception:
                report.pop('server_initial_private_binding', None)
                report['server_initial_diagnostic'] = self.ledger.empty('REFUSED')

        self.replace(core, 'finish_initial_observation', finish)


def capture(args):
    require(re.fullmatch('[0-9a-f]{40}', args.source_revision) is not None
            and args.source_revision == os.environ.get('GITHUB_SHA'))
    for name in ('compile_directory', 'native_capture', 'native_build_receipt', 'work', 'output'):
        setattr(args, name, Path(os.path.abspath(getattr(args, name))))
    core, fresh, probe, progress, _, ledger = context()
    recipe, receive, source = suppliers()
    with Bridge(args, core, fresh, probe, progress, ledger, recipe, receive, source):
        return core.capture(args)


def projection(report, directory, core, progress, summary, ledger, receive, source):
    """Read one exact private receipt and fixed sidecars, then rebuild allowlists."""
    meta = report.get('server_initial_runtime')
    require(type(meta) is dict and meta.get('schema') == PRIVATE_SCHEMA
            and meta.get('server_build_role') == ACTUAL_MAP_ROLE
            and meta.get('native_build_schema') == ACTUAL_NATIVE_SCHEMA
            and meta.get('new_role_artifact_admission_verified') is True
            and meta.get('compatibility_views_only_select_existing_lifecycle_hooks') is True
            and meta.get('historical_artifact_equivalence_claimed') is False
            and meta.get('public_upload_permitted') is False)
    require(report.get('native_tool', {}).get('build_schema') == ACTUAL_NATIVE_SCHEMA)
    require(meta.get('compile_receipt_sha256') == report.get('compile_receipt_sha256')
            and meta.get('native_build_receipt_sha256') == report['native_tool'].get('build_receipt_sha256')
            and meta.get('map_binary') == report.get('original_map_binary'))
    core.d.sha(meta.get('compile_receipt_sha256'))
    core.d.sha(meta.get('native_build_receipt_sha256'))
    require(type(meta.get('map_binary')) is dict and set(meta['map_binary']) == {'bytes', 'sha256'})
    core.d.uint(meta['map_binary']['bytes'], 16 * 1024**2, nonzero=True)
    core.d.sha(meta['map_binary']['sha256'])
    # This exact private identity was emitted after admission/restoration and
    # before Map startup. Bind projection to that invocation and its actual
    # compile/native receipts, rather than just accepting matching schema tags.
    identity_raw = progress.read_private(directory / 'run-identity.json', 8 * 1024**2)
    require(hashlib.sha256(identity_raw).hexdigest() == report.get('run_identity_sha256'))
    identity = core.d.json_object(identity_raw)
    require(identity.get('schema') == 'coh-private-original-native-groups-identity-v1'
            and identity.get('compile_receipt_sha256') == meta['compile_receipt_sha256']
            and identity.get('native_build_receipt_sha256') == meta['native_build_receipt_sha256']
            and identity.get('source_sha256') == report.get('source_sha256')
            and identity.get('source_revision') == meta.get('source_revision')
            and all(identity.get(name) is True for name in ('private_fresh_wine_prefix',
                    'private_fresh_pg_cluster', 'restored_existing_database_only')))
    result = {'schema': PUBLIC_SCHEMA, 'diagnostic_only': True,
              'transaction': summary.summarize(report),
              'server_initial': ledger.public(report['server_initial_diagnostic'], source.parse),
              'request_progress': None, 'native_receive': None,
              'normal_authentication_qualified': False, 'source_generation_admitted': False,
              'actor_publication': False, 'ack_permitted': False, 'world_authority': False}
    if result['server_initial']['state'] == 'VALID':
        ledger.paired(report)
        raw = progress.read_private(directory / ledger.BASENAME, ledger.MAXIMUM)
        binding = report.get('server_initial_private_binding', {})
        require(binding.get('schema') == 'coh-private-server-initial-ledger-binding-v1'
                and binding.get('bytes') == len(raw)
                and binding.get('sha256') == hashlib.sha256(raw).hexdigest()
                and binding.get('retained_after_owned_cleanup') is True
                and binding.get('public_upload_permitted') is False
                and source.parse(raw) == result['server_initial']['ledger'])
    if report.get('request_progress_private_binding') is not None:
        ledger.paired(report)
        raw = progress.read_private(directory / 'native/request-progress.json')
        binding = report['request_progress_private_binding']
        require(binding == {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                            'retained_after_owned_cleanup': True, 'public_upload_permitted': False})
        result['request_progress'] = progress.parse(raw)
        require(result['request_progress'] == report.get('request_progress_diagnostic'))
    # The receive producer owns this fixed parser/retention admission. This call
    # reads only its exact bounded private filename and verifies the saved binding.
    try:
        result['native_receive'] = receive.project(report, directory)
    except Exception:
        result['native_receive'] = {'schema': 'coh-server-initial-receive-projection-v1',
            'state': 'REFUSED', 'diagnostic_only': True,
            **{name: False for name in receive.FALSE}}
    require(len((json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + '\n').encode('ascii'))
            <= MAX_PUBLIC_BYTES)
    return result


def project(directory, output):
    core, _, _, progress, summary, ledger = context()
    recipe, receive, source = suppliers()
    directory, output = core.d.path(directory), core.d.path(output)
    report = summary.private_receipt(directory)
    pins = report.get('source_sha256')
    require(type(pins) is dict and 1 <= len(pins) <= 2048)
    revision = os.environ.get('GITHUB_SHA')
    require(report.get('server_initial_runtime', {}).get('source_revision') == revision)
    # Every executed wrapper/supplier/native/source helper is committed exactly;
    # hashes are checked again at projection, rather than trusting report strings.
    for path in (HERE / 'runtime.py', HERE / 'ledger.py', MAP_RECIPE, RECEIVE_ADMISSION, SOURCE_SCHEMA):
        relative = path.relative_to(ROOT).as_posix()
        require(pins.get(relative) == hashlib.sha256(path.read_bytes()).hexdigest())
    core.verify_orchestration(ROOT, pins, revision)
    result = projection(report, directory, core, progress, summary, ledger, receive, source)
    require(output.parent.is_dir() and not output.exists())
    core.d.emit_json(output, result)
    return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    c = sub.add_parser('capture')
    for name in ('runtime', 'control-fixture', 'db-donor-apk', 'compile-directory', 'database-dump',
                 'account-file', 'native-capture', 'native-build-receipt', 'pg-bin', 'work', 'output'):
        c.add_argument('--' + name, type=Path, required=True)
    for name in ('source-revision', 'compile-receipt-sha256', 'database-dump-sha256', 'native-build-receipt-sha256'):
        c.add_argument('--' + name, required=True)
    c.add_argument('--wire-slot', type=int, required=True)
    c.add_argument('--timeout-seconds', type=int, default=1200)
    c.add_argument('--wine', default='wine')
    c.add_argument('--wineserver', default='wineserver')
    e = sub.add_parser('project')
    e.add_argument('--private-output', type=Path, required=True)
    e.add_argument('--output', type=Path, required=True)
    return p


def main():
    args = parser().parse_args()
    os.umask(0o077)
    try:
        if args.command == 'capture':
            value = capture(args)
            passed = value.get('passed') is True
            print(json.dumps({'schema': 'coh-server-initial-runtime-status-v1', 'passed': passed,
                              'matching_groups_transaction_captured': value.get('matching_groups_transaction_captured') is True,
                              'cleanup_verified': value.get('cleanup_verified') is True,
                              'world_authority': False}))
            return 0 if passed else 2
        value = project(args.private_output, args.output)
        print(json.dumps({'schema': 'coh-server-initial-projection-status-v1', 'projection_written': True,
                          'transaction_passed': value['transaction']['passed'],
                          'ledger_state': value['server_initial']['state'], 'world_authority': False}))
        return 0
    except Exception:
        # No private path, account, owner, packet, source log or exception text.
        print(json.dumps({'schema': 'coh-server-initial-runtime-status-v1', 'passed': False,
                          'failure': 'ADMISSION_OR_PROJECTION_REFUSED', 'world_authority': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
