"""Controlled same-UID host denial, without changing any production check."""
import importlib, pathlib, subprocess, sys, unittest
from unittest import mock
root=pathlib.Path(sys.argv[1]).resolve()
sys.path[:0]=[str(root/'tools/android/atlasgame'),str(root/'android/guest')]
test=importlib.import_module('test_device_cleanup_lineage')
guest=test.guest
original=guest.DeviceWineProcessOwner.initialize
children=[]
def initialize(owner):
    result=original(owner)
    child=subprocess.Popen([sys.executable,'-c',
      'import ctypes,time; assert ctypes.CDLL(None).prctl(4,0,0,0,0)==0; print("ready",flush=True); time.sleep(30)'],
      stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    children.append(child)
    if child.stdout.readline()!=b'ready\n':
        raise RuntimeError('Controlled non-dumpable host fixture did not initialize')
    return result
try:
    with mock.patch.object(guest.DeviceWineProcessOwner,'initialize',new=initialize):
        suite=unittest.TestSuite([test.CleanupLineageTests('test_real_pthread_leader_death_drains_only_authenticated_worker')])
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    print('CONTROLLED_UNRELATED_NONDUMPABLE_TASKS='+str(len(children)))
    sys.exit(0 if result.wasSuccessful() else 1)
finally:
    for child in children:
        child.terminate()
        child.communicate(timeout=3)
