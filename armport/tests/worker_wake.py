#!/usr/bin/env python3
"""Force publication between the original worker's empty check and sleep.

The barrier is inserted in a temporary test copy, never in upstream/source.
Host adapters are a scheduling test, not evidence of ARM64 memory ordering.
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/android/interactive'))
from test_client_render_queue_worker import adapters


def harness(source, *, windows=False, atomic_path=False):
    header = (source / 'libs/UtilitiesLib/include/utilitieslib/components/WorkerThread.h').read_text()
    worker = (source / 'libs/UtilitiesLib/src/components/WorkerThread.c').read_text()
    anchor = '                cmd = peekStoredCmd(&wt->cmd_queue);\n                if (!cmd) {'
    if worker.count(anchor) != 1:
        raise ValueError('Expected exactly one final empty-queue recheck')
    worker = worker.replace(anchor, anchor.replace('\n                if', '\n                test_empty_barrier(cmd);\n                if'))
    strip = lambda text: re.sub(r'^#include[^\n]*\n', '', text, flags=re.M)
    before = r'''
static HANDLE arrived,release_gate;
static volatile LONG armed=1,delivered;
static DWORD bounded_wait(HANDLE h,DWORD milliseconds) {
    return WaitForSingleObject(h,milliseconds==INFINITE?10000:milliseconds);
}
#define WaitForSingleObject bounded_wait
static void test_empty_barrier(void *cmd) {
    if(!cmd && InterlockedCompareExchange(&armed,0,1)==1) {
        assert(SetEvent(arrived));
        assert(WaitForSingleObject(release_gate,10000)==WAIT_OBJECT_0);
    }
}
'''
    after = r'''
static U32 command_count,message_count;
static void dispatch(void *user,int type,void *data) {
    U32 *words=data,sequence=words[0],i;
    if(type==WT_CMD_USER_START) {
        assert(sequence==0x12345678u);InterlockedIncrement(&delivered);return;
    }
    assert(type==WT_CMD_USER_START+1);assert(sequence==command_count++);
    for(i=1;i<2+sequence%55;i++)assert(words[i]==(sequence^i^0xa5a55a5au));
    wtQueueMsg(*(WorkerThread**)user,WT_CMD_USER_START,&sequence,sizeof(sequence));
}
static void message(void *unused,int type,void *data) {
    (void)unused;assert(type==WT_CMD_USER_START);assert(*(U32*)data==message_count++);
}
int main(int argc,char **argv) {
    WorkerThread *wt;U32 value=0x12345678u,words[56],sequence,j;int observed,i,expected;
    assert(argc==2);expected=atoi(argv[1]);
    arrived=CreateEvent(NULL,0,0,NULL);release_gate=CreateEvent(NULL,0,0,NULL);
    wt=wtCreate(dispatch,64,message,NULL,64,&wt);wtSetThreaded(wt,1);wtStart(wt);
    assert(WaitForSingleObject(arrived,10000)==WAIT_OBJECT_0);
    wtQueueCmd(wt,WT_CMD_USER_START,&value,sizeof(value));
    assert(SetEvent(release_gate));
    for(i=0;i<200 && !InterlockedCompareExchange(&delivered,0,0);i++)Sleep(1);
    observed=InterlockedCompareExchange(&delivered,0,0);
    printf("final-empty-check publication: dispatched=%d expected=%d\n",observed,expected);
    /* Always release the negative control before destroying its worker. */
    assert(SetEvent(wt->data_queued));wtFlush(wt);
    for(sequence=0;sequence<4096;sequence++) {
        words[0]=sequence;
        for(j=1;j<2+sequence%55;j++)words[j]=sequence^j^0xa5a55a5au;
        wtQueueCmd(wt,WT_CMD_USER_START+1,words,(2+sequence%55)*sizeof(U32));
        /* The original message producer requires enough free message slots. */
        if(sequence%16==15){wtFlush(wt);wtMonitor(wt);}
    }
    wtFlush(wt);wtMonitor(wt);
    assert(command_count==4096 && message_count==4096);
    printf("wrapped payloads: commands=%u messages=%u\n",command_count,message_count);
    wtDestroy(wt);
    CloseHandle(arrived);CloseHandle(release_gate);
    return observed==expected?0:1;
}
'''
    adapter = adapters(windows)
    if windows:
        adapter = adapter.replace('#ifdef _WIN64\n#error Genuine worker qualification must target Win32\n#endif\n', '')
    selection = ''
    if atomic_path:
        if '__atomic_load_n' not in worker:
            raise ValueError('The selected source has no ARM64 atomic path')
        # Headers were already read by the adapter. Select only the worker's
        # actual ARM64 preprocessor branch for this host scheduling test.
        selection = '\n#define __aarch64__ 1\n#define __MINGW32__ 1\n'
    return adapter + strip(header) + before + selection + strip(worker) + after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--expect-dispatch', choices=('0', '1'), required=True)
    parser.add_argument('--atomic-path', action='store_true')
    parser.add_argument('--emit-windows', type=Path)
    args = parser.parse_args()
    if args.emit_windows:
        args.emit_windows.write_text(harness(args.source, windows=True))
        return
    with tempfile.TemporaryDirectory(prefix='armport-worker-') as directory:
        source = Path(directory) / 'worker.c'
        binary = Path(directory) / 'worker'
        source.write_text(harness(args.source, atomic_path=args.atomic_path))
        subprocess.run(['cc', '-std=c11', '-O2', '-pthread', str(source), '-o', str(binary)], check=True)
        subprocess.run([str(binary), args.expect_dispatch], check=True, timeout=15)


if __name__ == '__main__':
    main()
