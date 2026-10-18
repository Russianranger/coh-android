"""New mocked preflight controls. No child process/project import/native run."""
from contextlib import ExitStack
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('retained_receiver_proposal', HERE / 'admit_retained_initial_receiver.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
ROOT = HERE.parent / 'coh-android'
CASES = 0

def counted():
    global CASES
    CASES += 1

class Controls(unittest.TestCase):
    def test_fixed_retained_artifact_bytes_without_executing_artifacts(self):
        counted();binary,build,mapping,pins=M.evidence(ROOT)
        self.assertEqual((len(binary),len(build),len(mapping),len(pins)),(180424,240894,43,15))
        self.assertEqual((M.digest(binary),M.digest(build)),(M.ELF_SHA,M.BUILD_SHA))
        counted()
        with self.assertRaises(M.Refused):M.fixed(ROOT,M.ELF,180423,M.ELF_SHA)

    def test_actual_preimport_gate_refusals_with_fixed_F173_metadata(self):
        focused=(ROOT/M.FOLLOWUP).read_bytes()
        base=json.loads(focused)['merged_effective_current_gate']['source_sha256']
        self.assertEqual(hashlib.sha256(focused).hexdigest(),M.FOLLOWUP_SHA)
        own='admit.py';artifact='retained/artifact';revision='c'*40
        scene='native-android/engine/scenecatalog-server/'
        superseded=sorted(scene+p for p in ('fresh_callback_observer/stage.py','fresh_callback_observer/test_stage.py',
            'admit_groups_capture.py','admit_source_snapshot.py','capture_groups_transaction.py',
            'retain_fresh_initial_observation.py','retain_fresh_source_snapshot.py','summarize_groups_capture.py'))
        for mode in ('good','schema','extra-key','revision','execution','base-pin','self-missing','artifact-pin','focused-pin','committed-head'):
            counted();pins={**base,own:'a'*64,artifact:'b'*64}
            gate={'schema':'coh-fresh-groups-live-source-admission-v1','passed':True,'source_revision':revision,
                'historical_core_source_reference':'55f4dd46061bc378f72921ab83b51c79883a1b6e',
                'focused_helper_source_reference':'419b61c1188acef7b208066d13b8eca42c0887d1',
                'historical_helper_pins_superseded':superseded,'source_sha256':pins,'host_controls_reexecuted':False,
                'historical_worker_commit_replayed_in_CI':False,'source_preflight_only':True,'runtime_executed':False,
                'accepted_observer_equivalence':False,'source_generation_admitted':False,'world_authority':False}
            if mode=='schema':gate['schema']='foreign'
            if mode=='extra-key':gate['foreign']=False
            if mode=='revision':gate['source_revision']='d'*40
            if mode=='execution':gate['runtime_executed']=True
            if mode=='base-pin':pins[next(iter(base))]='f'*64
            if mode=='self-missing':pins.pop(own)
            if mode=='artifact-pin':pins[artifact]='f'*64
            gate_bytes=json.dumps(gate).encode()
            def read(path,*args):
                if path.name=='fresh-groups-source-admission.json':return gate_bytes
                self.assertEqual(path,Path('/mock-root')/M.FOLLOWUP)
                return focused+b'x' if mode=='focused-pin' else focused
            with patch.object(M,'raw',side_effect=read),patch.object(M,'committed',
                    side_effect=M.Refused('SOURCE_HEAD') if mode=='committed-head' else None) as committed, \
                    patch.object(M.importlib,'import_module',side_effect=AssertionError('preimport execution')) as imported:
                if mode=='good':
                    result=M.admit_gate(Path('/mock-root'),Path('/mock-runner'),revision,own,{artifact:'b'*64})
                    self.assertEqual(result[2],pins);self.assertEqual(committed.call_count,1)
                else:
                    with self.assertRaises(M.Refused):M.admit_gate(Path('/mock-root'),Path('/mock-runner'),revision,own,{artifact:'b'*64})
                    self.assertEqual(committed.call_count,int(mode=='committed-head'))
                imported.assert_not_called()

    def test_actual_committed_source_gate_git_and_hash_refusals_are_mocked(self):
        revision='c'*40;content=b'committed source';sha=M.digest(content)
        pins={f'source/{i}.py':sha for i in range(173)}
        blob=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
        for mode in ('good','head','untracked','mode','worktree','git-blob'):
            counted()
            def git(root,*args):
                if args[0]=='rev-parse':return ((revision if mode!='head' else 'd'*40)+'\n').encode()
                names=sorted(pins)
                if mode=='untracked':names.pop()
                return b''.join((('120000' if mode=='mode' else '100644')+' blob '+
                    ('e'*40 if mode=='git-blob' else blob)+'\t'+name+'\0').encode() for name in names)
            with patch.object(M,'git',side_effect=git),patch.object(M,'raw',return_value=content+b'x' if mode=='worktree' else content):
                if mode=='good':M.committed(Path('/mock-root'),pins,revision)
                else:
                    with self.assertRaises(M.Refused):M.committed(Path('/mock-root'),pins,revision)

    def test_static_elf_metadata_without_readelf_execution(self):
        folder = ROOT / M.REVIEW
        good = [(folder / ('readelf-' + name + '.txt')).read_bytes()
                for name in ('header', 'segments', 'dynamic', 'versions')]
        variants = [None, (0, b'ELF64', b'ELF32'), (1, M.INTERPRETER.encode(), b'/foreign/loader'),
                    (2, b'libcrypto.so.3', b'libforeign.so.3'), (2, b'(FLAGS)', b'(RPATH)'),
                    (3, b'OPENSSL_3.0.0', b'OPENSSL_4.0.0')]
        for mutation in variants:
            counted();values = list(good)
            if mutation:
                index, old, new = mutation;values[index] = values[index].replace(old, new)
            with patch.object(M, 'child', side_effect=[(0, value, b'') for value in values]) as child:
                if mutation:
                    with self.assertRaises(M.Refused):M.static_elf(Path('/mock/binary'), Path('/mock'))
                else:M.static_elf(Path('/mock/binary'), Path('/mock'))
                self.assertTrue(all(call.args[0][0] == '/usr/bin/readelf' for call in child.call_args_list))

    def test_loader_and_smoke_refusals_are_only_mocked_calls(self):
        listing = (b'linux-vdso.so.1 (0x123)\n' + b''.join(
            f'{name} => /lib/x86_64-linux-gnu/{name} (0x123)\n'.encode() for name in M.NEEDED) +
            (M.INTERPRETER + ' (0x123)\n').encode())
        systems = {name: {'resolved': '/lib/x86_64-linux-gnu/' + name} for name in M.NEEDED}
        variants = [None, 'verify-rc', 'verify-output', 'verify-error', 'list-rc', 'list-error',
                    'list-extra', 'list-missing', 'list-duplicate', 'list-path', 'smoke-rc', 'smoke-out', 'smoke-error']
        for mode in variants:
            counted();values = [(0, b'', b''), (0, listing, b''), (2, b'', b'')]
            if mode == 'verify-rc':values[0] = (1, b'', b'')
            if mode == 'verify-output':values[0] = (0, b'x', b'')
            if mode == 'verify-error':values[0] = (0, b'', b'x')
            if mode == 'list-rc':values[1] = (1, listing, b'')
            if mode == 'list-error':values[1] = (0, listing, b'x')
            if mode == 'list-extra':values[1] = (0, listing + b'libx.so => /lib/libx.so (0x123)\n', b'')
            if mode == 'list-missing':values[1] = (0, listing.replace(b'linux-vdso.so.1 (0x123)\n', b''), b'')
            if mode == 'list-duplicate':values[1] = (0, listing + b'linux-vdso.so.1 (0x123)\n', b'')
            if mode == 'list-path':values[1] = (0, listing.replace(b'/lib/x86_64-linux-gnu/libz.so.1', b'/foreign/libz.so.1'), b'')
            if mode == 'smoke-rc':values[2] = (0, b'', b'')
            if mode == 'smoke-out':values[2] = (2, b'x', b'')
            if mode == 'smoke-error':values[2] = (2, b'', b'x')
            with patch.object(M, 'child', side_effect=values) as child, patch.object(M.os.path, 'lexists', return_value=False), \
                    patch.object(Path, 'resolve', lambda p, **kw: p):
                if mode:
                    with self.assertRaises(M.Refused):M.loader_checks(Path('/mock/binary'), Path('/mock'), systems)
                else:M.loader_checks(Path('/mock/binary'), Path('/mock'), systems)
                self.assertEqual(child.call_args_list[0].args[0], [M.INTERPRETER, '--verify', '/mock/binary'])

    def test_write_flush_fsync_close_combined_failure_rolls_back_owned_receipt(self):
        real_fdopen, real_close, real_fstat = os.fdopen, os.close, os.fstat
        for mode in ('write', 'flush', 'fsync', 'close', 'fsync-close', 'fstat'):
            counted()
            with tempfile.TemporaryDirectory() as name:
                path = Path(name) / 'receiver-reuse.json';closed = []
                class Stream:
                    def __init__(self, fd):self.stream = real_fdopen(fd, 'wb', closefd=False)
                    def __enter__(self):return self
                    def write(self, value):
                        self.stream.write(value)
                        if mode == 'write':raise OSError('private-must-not-escape')
                    def flush(self):
                        self.stream.flush()
                        if mode == 'flush':raise OSError('private-must-not-escape')
                    def __exit__(self, *args):self.stream.close()
                def close(fd):
                    closed.append(fd);real_close(fd)
                    if mode in ('close', 'fsync-close'):raise OSError('secondary-close')
                with ExitStack() as stack:
                    stack.enter_context(patch.object(M.os, 'fdopen', side_effect=lambda fd, *a, **k: Stream(fd)))
                    stack.enter_context(patch.object(M.os, 'close', side_effect=close))
                    if mode in ('fsync', 'fsync-close'):stack.enter_context(patch.object(M.os, 'fsync', side_effect=OSError('primary-fsync')))
                    if mode == 'fstat':stack.enter_context(patch.object(M.os, 'fstat', side_effect=OSError('initial-fstat')))
                    with self.assertRaises(M.Refused) as caught:M.write_new(path, b'{"passed":true}\n', 0o600)
                self.assertEqual(caught.exception.code, 'OUTPUT_CLOSE' if mode == 'close' else 'OUTPUT_WRITE')
                self.assertEqual(len(closed), 1)
                with self.assertRaises(OSError):real_fstat(closed[0])
                if mode == 'fstat':
                    self.assertFalse(caught.exception.cleanup_verified)
                    self.assertEqual(path.read_bytes(), b'')
                else:self.assertFalse(path.exists())

    def test_rollback_never_deletes_foreign_replacement(self):
        counted()
        with tempfile.TemporaryDirectory() as name:
            path, other = Path(name) / 'copy', Path(name) / 'other'
            identity = M.write_new(path, b'owned', 0o600)
            other.write_bytes(b'foreign');other.replace(path)
            self.assertFalse(M.unlink_owned(path, identity));self.assertEqual(path.read_bytes(), b'foreign')

    def test_environment_append_rolls_back_partial_fsync_and_close_errors(self):
        real_write, real_sync, real_close = os.write, os.fsync, os.close
        for mode in ('good', 'short', 'fsync', 'close', 'fsync-close', 'concurrent'):
            counted()
            with tempfile.TemporaryDirectory() as name:
                runner=Path(name);path=runner/'environment';path.write_bytes(b'PRIOR=x\n');path.chmod(0o600)
                syncs=closes=0
                def write(fd,value):return real_write(fd,value[:5] if mode=='short' else value)
                def sync(fd):
                    nonlocal syncs
                    syncs+=1
                    if syncs==1 and mode in ('fsync','fsync-close','concurrent'):
                        if mode=='concurrent':
                            other=os.open(path,os.O_WRONLY|os.O_APPEND);real_write(other,b'FOREIGN=y\n');real_close(other)
                        raise OSError('primary-sync')
                    return real_sync(fd)
                def close(fd):
                    nonlocal closes
                    closes+=1;real_close(fd)
                    if closes==1 and mode in ('close','fsync-close'):raise OSError('secondary-close')
                with patch.object(M.os,'write',side_effect=write),patch.object(M.os,'fsync',side_effect=sync),patch.object(M.os,'close',side_effect=close):
                    if mode=='good':M.export_env(path,runner)
                    else:
                        with self.assertRaises(M.Refused) as caught:M.export_env(path,runner)
                        self.assertEqual(caught.exception.code,'ENV_EXPORT')
                        if mode=='concurrent':self.assertFalse(caught.exception.cleanup_verified)
                if mode=='good':self.assertEqual(path.read_bytes(),b'PRIOR=x\n'+('INITIAL_BUILD_SHA256='+M.BUILD_SHA+'\n').encode())
                elif mode=='concurrent':self.assertTrue(path.read_bytes().endswith(b'FOREIGN=y\n'))
                else:self.assertEqual(path.read_bytes(),b'PRIOR=x\n')

    def test_child_dead_leader_group_and_combined_cleanup_failures_mocked(self):
        for mode in ('good', 'dead-leader-held-pipe', 'output-and-cleanup'):
            counted();closed, killed = [], []
            class Pipe:
                def __init__(self, fd):self.fd = fd
                def close(self):
                    closed.append(self.fd)
                    if mode == 'output-and-cleanup':raise OSError('close')
            process = NS(pid=43210, stdout=Pipe(10), stderr=Pipe(11))
            process.wait = lambda **kw: 0
            if mode == 'output-and-cleanup':
                process.wait = lambda **kw: (_ for _ in ()).throw(subprocess.TimeoutExpired('not-exposed', 2))
            class Selector:
                def __init__(self):self.items = {}
                def __enter__(self):return self
                def __exit__(self, *args):return False
                def register(self, stream, events, index):self.items[stream.fd] = NS(fd=stream.fd, fileobj=stream, data=index)
                def unregister(self, stream):self.items.pop(stream.fd)
                def get_map(self):return self.items
                def select(self, timeout):
                    return [] if mode == 'dead-leader-held-pipe' else [(value, 1) for value in list(self.items.values())]
            clock = iter(i / 10 for i in range(100))
            def kill(pid, sig):
                killed.append((pid, sig))
                if sig == 0:raise ProcessLookupError()
                if mode == 'output-and-cleanup':raise OSError('kill')
            with patch.object(M.subprocess, 'Popen', return_value=process) as popen, \
                    patch.object(M.selectors, 'DefaultSelector', Selector), \
                    patch.object(M.os, 'read', return_value=b'x'*8 if mode == 'output-and-cleanup' else b''), \
                    patch.object(M.os, 'killpg', side_effect=kill), \
                    patch.object(M.time, 'monotonic', side_effect=lambda: next(clock)), patch.object(M.time, 'sleep'):
                if mode == 'good':self.assertEqual(M.child(['/mock'], '/mock', limit=4, seconds=1), (0, b'', b''))
                else:
                    with self.assertRaises(M.Refused) as caught:M.child(['/mock'], '/mock', limit=4, seconds=0.2)
                    self.assertEqual(caught.exception.code, 'CHILD_OUTPUT' if mode == 'output-and-cleanup' else 'CHILD_TIMEOUT')
                    self.assertEqual(caught.exception.cleanup_verified, mode != 'output-and-cleanup')
                self.assertEqual(set(closed), {10, 11});self.assertIn((43210, signal.SIGKILL), killed)
                self.assertIn((43210, 0), killed)
                self.assertEqual(popen.call_args.kwargs['env'], M.CLEAN_ENV)

    def test_full_copy_success_and_every_late_failure_are_mocked(self):
        real_stat, real_fstat, real_write = Path.stat, os.fstat, M.write_new
        modes = ('good', 'native', 'loader', 'late-source', 'late-system', 'late-binary',
                 'late-build', 'late-gate', 'late-receipt', 'failure-receipt-io', 'env-write')
        for mode in modes:
            counted()
            with tempfile.TemporaryDirectory() as name:
                base = Path(name);root = base / 'root';root.mkdir();runner = base / 'runner';runner.mkdir()
                parent = runner / 'inputs';parent.mkdir(mode=0o700);output = parent / 'initial-capture'
                own = root / 'admit.py';own.write_bytes(b'mocked helper')
                gate = runner / 'fresh-groups-source-admission.json';gate.write_bytes(b'mocked gate')
                envfile = runner / 'environment';envfile.write_bytes(b'')
                mapping = {f'native-android/mock/{i}.c': 'b'*64 for i in range(43)}
                pins = {'admit.py': 'a'*64}
                source_calls = system_calls = 0
                def committed(*args):
                    nonlocal source_calls
                    source_calls += 1
                    if mode == 'late-source' and source_calls == 4:raise M.Refused('SOURCE_BYTES')
                def systems():
                    nonlocal system_calls
                    system_calls += 1
                    return {'mock': 'changed' if mode == 'late-system' and system_calls == 3 else 'stable'}
                def native(binary, build, pin, actual_root):
                    self.assertEqual(actual_root, root);self.assertEqual(binary.read_bytes(), b'mocked ELF')
                    self.assertEqual(build.read_bytes(), b'mocked original receipt')
                    if mode == 'native':raise ValueError('private-native-error')
                    return {'dependencies_sha256': mapping, 'project_dependencies': 43, 'source_revision': M.HISTORICAL}
                capture = NS(__file__=str(root/'native-android/engine/scenecatalog-server/capture_groups_transaction.py'), native_input=native)
                def project_import(*args):
                    self.assertGreaterEqual(source_calls,1)
                    return capture
                def write(path, value, flags):
                    identity = real_write(path, value, flags)
                    if path.name == 'receiver-reuse.json' and json.loads(value).get('passed'):
                        if mode == 'late-binary':(output/M.BASENAME).write_bytes(b'changed')
                        if mode == 'late-build':(output/'build.json').write_bytes(b'changed')
                        if mode == 'late-gate':gate.write_bytes(b'changed')
                        if mode == 'late-receipt':path.write_bytes(b'changed')
                    if mode == 'failure-receipt-io' and path.name == 'receiver-reuse.json' and not json.loads(value).get('passed'):
                        raise M.Refused('SECONDARY_DIAGNOSTIC_IO')
                    return identity
                def stat_uid(info):
                    return NS(**{key: getattr(info,key) for key in ('st_mode','st_dev','st_ino','st_size','st_mtime_ns')}, st_uid=1)
                env = {'GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted','RUNNER_OS':'Linux',
                       'RUNNER_ARCH':'X64','GITHUB_REPOSITORY':'Russianranger/coh-android',
                       'GITHUB_REF':'refs/heads/native-android','GITHUB_SHA':'c'*40,
                       'RUNNER_TEMP':str(runner),'GITHUB_ENV':str(envfile)}
                with ExitStack() as stack:
                    stack.enter_context(patch.dict(os.environ, env, clear=True))
                    stack.enter_context(patch.object(M, '__file__', str(own)))
                    stack.enter_context(patch.object(M.os, 'geteuid', return_value=1))
                    stack.enter_context(patch.object(Path, 'stat', lambda p, *a, **kw: stat_uid(real_stat(p,*a,**kw)) if p==parent else real_stat(p,*a,**kw)))
                    stack.enter_context(patch.object(M.os, 'fstat', side_effect=lambda fd: stat_uid(real_fstat(fd))))
                    stack.enter_context(patch.object(M.platform, 'machine', return_value='x86_64'))
                    stack.enter_context(patch.object(M, 'evidence', return_value=(b'mocked ELF',b'mocked original receipt',mapping,{})))
                    stack.enter_context(patch.object(M, 'admit_gate', return_value=(gate,M.digest(gate.read_bytes()),pins)))
                    stack.enter_context(patch.object(M, 'committed', side_effect=committed))
                    stack.enter_context(patch.object(M, 'static_elf'))
                    stack.enter_context(patch.object(M, 'system_files', side_effect=systems))
                    stack.enter_context(patch.object(M, 'loader_checks', side_effect=M.Refused('LOADER_LIST') if mode in ('loader','failure-receipt-io') else None))
                    stack.enter_context(patch.object(M, 'imported_sources'))
                    stack.enter_context(patch.object(M.importlib, 'import_module', side_effect=project_import))
                    stack.enter_context(patch.object(M, 'write_new', side_effect=write))
                    if mode == 'env-write':stack.enter_context(patch.object(M.os, 'write', return_value=0))
                    if mode == 'good':
                        result=M.admit(root,output);self.assertTrue(result['passed'])
                    else:
                        with self.assertRaises(M.Refused) as caught:M.admit(root,output)
                        if mode == 'failure-receipt-io':self.assertEqual(caught.exception.code,'LOADER_LIST')
                if mode == 'good':
                    self.assertEqual(envfile.read_text(),'INITIAL_BUILD_SHA256='+M.BUILD_SHA+'\n')
                    self.assertEqual((output/'build.json').read_bytes(),b'mocked original receipt')
                    self.assertEqual({p.name for p in output.iterdir()},{M.BASENAME,'build.json','receiver-reuse.json'})
                    self.assertEqual((output.stat().st_mode&0o777),(0o700))
                else:
                    self.assertEqual(envfile.read_bytes(),b'')
                    self.assertFalse((output/M.BASENAME).exists());self.assertFalse((output/'build.json').exists())
                    receipt=output/'receiver-reuse.json'
                    if receipt.exists():self.assertFalse(json.loads(receipt.read_bytes()).get('passed'))

if __name__ == '__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    proof={'schema':'coh-retained-initial-receiver-new-mocked-controls-v1','passed':True,
           'methods':result.testsRun,'cases':CASES,'helper_sha256':hashlib.sha256((HERE/'admit_retained_initial_receiver.py').read_bytes()).hexdigest(),
           'test_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'mocked_only':True,'actual_subprocess_executed':False,'actual_native_or_loader_executed':False,
           'fixed_retained_artifact_bytes_read_without_execution':True,
           'compiler_executed':False,'old_151_controls_reexecuted':False,'project_capture_import_executed':False,
           'required_destination_branch':'refs/heads/native-android','qualification_scope':'scratch proposal with mocked platform/process/project interfaces; no workflow or destination execution',
           'services_executed':False,'source_generation_admitted':False,'world_authority':False}
    path=HERE/'retained-initial-receiver-mocked-controls.json';path.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
    print(json.dumps(proof,sort_keys=True))
