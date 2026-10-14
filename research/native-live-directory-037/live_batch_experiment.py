#!/usr/bin/env python3
"""Controlled POSIX live-batch research, not Wine/PRoot/API parity authority.

Only owned temporary files are changed. No game, database, assets or processes
are launched. Names are captured once; metadata is read when each batch runs.
"""
from __future__ import annotations
import errno
import hashlib
import json
import mmap
import os
from pathlib import Path
import stat
import tempfile
import time

ATTR_READONLY, ATTR_HIDDEN, ATTR_SYSTEM, ATTR_DIRECTORY, ATTR_ARCHIVE = 1,2,4,16,32
EPOCH = 116444736000000000

def fields(directory_fd, name):
    # The raw POSIX model deliberately does not resolve guest absolute links.
    info = os.stat(name, dir_fd=directory_fd, follow_symlinks=True)
    attrs = ATTR_DIRECTORY if stat.S_ISDIR(info.st_mode) else ATTR_ARCHIVE
    if not info.st_mode & 0o222:
        attrs |= ATTR_READONLY
    return {'name':name,'consumed_attributes':attrs & 23,
            'size_low':0 if stat.S_ISDIR(info.st_mode) else info.st_size & 0xffffffff,
            'write_filetime':info.st_mtime_ns // 100 + EPOCH}

class LiveNames:
    def __init__(self, path):
        self.fd = os.open(path, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        # ASCII-only Wine b073 order. Production must preserve actual native
        # conversions/configuration, dot aliases and all unsupported cases.
        try:
            self.names = sorted(os.listdir(self.fd),key=lambda name:(name.upper(),name))
        except BaseException:
            owned_fd = self.fd
            self.fd = -1
            os.close(owned_fd)
            raise
        self.position = 0
    def batch(self, count):
        output=[]
        while self.position<len(self.names) and len(output)<count:
            name=self.names[self.position];self.position+=1
            try:
                output.append(fields(self.fd,name))
            except OSError as exc:
                # The source skips all get_file_info failures. This research
                # accepts only controlled missing-file failure, never maps a
                # transport/mapping failure to complete-branch absence.
                if exc.errno!=errno.ENOENT:
                    raise
        return output
    def close(self):
        os.close(self.fd)

def run():
    started=time.monotonic(); checks=[]
    def passed(name, **observations):
        checks.append({'name':name,'result':'passed',**observations})
    with tempfile.TemporaryDirectory(prefix='coh-live-directory-research-') as tmp:
        root=Path(tmp);data=root/'data';data.mkdir();first=data/'a';later=data/'z'
        first.write_bytes(b'a');later.write_bytes(b'z')
        reader=LiveNames(data)
        try:
            assert [row['name'] for row in reader.batch(1)]==['a']
            later.write_bytes(b'fresh-content');os.utime(later,ns=(1700000000123456700,1700000000123456700))
            row=reader.batch(1)[0]
            assert row['size_low']==13 and row['write_filetime']==17000000001234567+EPOCH
            passed('metadata_after_names_and_previous_batch_is_current',row=row)
        finally:reader.close()
        reader=LiveNames(data)
        try:
            (data/'new').write_bytes(b'new')
            assert 'new' not in [row['name'] for row in reader.batch(20)]
            passed('new_membership_after_open_is_not_added_to_names_snapshot')
        finally:reader.close()
        reader=LiveNames(data)
        try:
            later.unlink()
            assert 'z' not in [row['name'] for row in reader.batch(20)]
            passed('removed_name_before_its_metadata_read_is_skipped')
        finally:reader.close()
        reader=LiveNames(data)
        try:
            moved=root/'renamed-data';data.rename(moved)
            replacement=data;replacement.mkdir();(replacement/'a').write_bytes(b'replacement')
            rows=reader.batch(20)
            assert next(row for row in rows if row['name']=='a')['size_low']==1
            passed('held_directory_fd_retains_identity_after_path_replacement')
            data=moved
        finally:reader.close()
        alias=root/'outside-alias';os.link(data/'a',alias)
        reader=LiveNames(data)
        try:
            os.chmod(alias,0o444)
            row=next(row for row in reader.batch(20) if row['name']=='a')
            assert row['consumed_attributes'] & ATTR_READONLY
            passed('outside_hardlink_metadata_change_is_seen_at_current_read',row=row)
        finally:reader.close()
        os.chmod(alias,0o600)
        mapped=data/'mapped';mapped.write_bytes(b'original');handle=os.open(mapped,os.O_RDWR)
        mapping=mmap.mmap(handle,0)
        reader=LiveNames(data)
        try:
            os.utime(mapped,ns=(1000000000000000000,1000000000000000000))
            mapping[0:8]=b'changed!';mapping.flush()
            row=next(row for row in reader.batch(20) if row['name']=='mapped')
            assert mapped.read_bytes()==b'changed!' and row['write_filetime']!=10000000000000000+EPOCH
            passed('preexisting_mmap_write_is_seen_without_event_or_lease',row=row)
        finally:reader.close();mapping.close();os.close(handle)
        target=root/'import-file';target.write_bytes(b'import')
        guest='/__coh_live_bridge_control__/import-file';link=data/'guest-absolute';link.symlink_to(guest)
        try:os.stat(link)
        except FileNotFoundError:
            passed('raw_host_stat_cannot_resolve_guest_absolute_link',guest_path=guest,
                   mapped_target_current_size=target.stat().st_size)
        else:raise AssertionError('Controlled guest path unexpectedly exists')
        link.unlink()
        directory=data/'dir';directory.mkdir()
        fd=os.open(data,os.O_RDONLY|os.O_DIRECTORY)
        try:
            row=fields(fd,'dir');assert row['size_low']==0 and row['consumed_attributes'] & ATTR_DIRECTORY
            passed('Wine_source_consumed_directory_size_projection_is_zero',row=row,
                   actual_POSIX_directory_size=directory.stat().st_size)
        finally:os.close(fd)
    return {'format':1,'role':'controlled_POSIX_live_directory_batch_research',
            'status':'passed_controlled_POSIX_cases','cases':checks,'elapsed_seconds':time.monotonic()-started,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'platform':os.uname().sysname+' '+os.uname().release+' '+os.uname().machine,
            'uid':os.getuid(),'only_owned_temporary_files_changed':True,
            'Wine_or_PRooot_or_FEX_or_Game_executed':False,
            'WFD_API_or_race_parity_qualified':False,'provider_authority':False,
            'native_registration_allowed':False,'publication_allowed':False,
            'device_speedup_measured':False}

def initial_listing_failure_control():
    """Inject listdir failure and observe exact FD cleanup in the real kernel."""
    from unittest.mock import patch
    started=time.monotonic(); captured=[];closed=False
    failure=OSError(errno.EIO,'controlled initial directory listing failure')
    with tempfile.TemporaryDirectory(prefix='coh-live-init-failure-') as tmp:
        guard=os.open(tmp,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        def reject_listing(fd):
            assert fd!=guard and stat.S_ISDIR(os.fstat(fd).st_mode)
            captured.append(fd)
            raise failure
        try:
            with patch('os.listdir',side_effect=reject_listing):
                try:
                    LiveNames(tmp)
                except OSError as error:
                    assert error is failure,'Original listing failure was replaced'
                else:
                    raise AssertionError('Injected listing failure was swallowed')
            assert len(captured)==1
            try:
                os.fstat(captured[0])
            except OSError as error:
                assert error.errno==errno.EBADF
                closed=True
            assert closed,'Constructor leaked its owned directory FD'
            assert stat.S_ISDIR(os.fstat(guard).st_mode),'Unrelated guard FD was closed'
        finally:
            os.close(guard)
            if captured and not closed:
                os.close(captured[0])
    return {'format':1,'role':'controlled_live_directory_initial_listing_failure',
            'status':'passed_injected_failure_and_kernel_FD_cleanup',
            'cases':[{'name':'initial_listdir_failure_closes_exact_owned_FD',
                      'result':'passed','injected_error':errno.EIO,
                      'observed_closed_FD_error':errno.EBADF,
                      'original_exception_preserved':True,'unrelated_guard_FD_retained':True}],
            'elapsed_seconds':time.monotonic()-started,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'platform':os.uname().sysname+' '+os.uname().release+' '+os.uname().machine,
            'uid':os.getuid(),'only_owned_temporary_files_changed':True,
            'Wine_or_PRooot_or_FEX_or_Game_executed':False,
            'provider_authority':False,'native_registration_allowed':False,
            'publication_allowed':False,'device_speedup_measured':False}

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['--initial-listing-failure-control']:
        print(json.dumps(initial_listing_failure_control(),indent=2))
    elif not sys.argv[1:]:
        print(json.dumps(run(),indent=2))
    else:
        raise SystemExit('Unknown research control argument')
