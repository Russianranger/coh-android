#!/usr/bin/env python3
"""Fresh original Auth/Db shard selection; stop and wipe before DB client login.

Links only a new narrow probe, reusing exactly retained x64 static OpenSSL.
The original services, login core and crypto are not rebuilt or modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile

import auth_service_profile
import hosted_db_shard_activation as activation
import password_fixture

HERE=Path(__file__).resolve().parent
prior=activation.prior
login=activation.login
CRYPTO_MANIFEST_SHA='1c1c05eb10132e4d1d172d29a04d36311981e6c7023c7ee388348339c460896b'
CRYPTO_LIBRARY_SHA='95aec97b796992a58f8745e1bbbc6eac634931420f13b0763d2db57537543698'
CRYPTO_ARCHIVE_SHA='aa7a1badbeb8926cec15009f7f87ebb797aa2345c0c97a183cd1e23866a3499b'
USERDATA_QUERY=("SET NOCOUNT ON;SELECT COUNT(*) FROM cohauth.dbo.user_data WHERE uid=900001 "
    "AND user_data IS NOT NULL AND DATALENGTH(user_data)=16 "
    "AND user_data_new IS NOT NULL AND DATALENGTH(user_data_new)=112 "
    "AND user_game_data IS NOT NULL AND DATALENGTH(user_game_data)=16 "
    "AND user_game_data_new IS NOT NULL AND DATALENGTH(user_game_data_new)=112;")


def admit_crypto(directory, root):
    crypto=directory/'intact-openssl-reuse'
    manifest=crypto/'manifest.json'
    if (directory.is_symlink() or crypto.is_symlink() or manifest.is_symlink()
            or not manifest.is_file() or manifest.stat().st_size!=58665
            or prior.sha(manifest)!=CRYPTO_MANIFEST_SHA):
        raise ValueError('selected_retained_crypto_manifest_identity')
    value=json.loads(manifest.read_text())
    if (value.get('schema')!='coh-intact-openssl-build-ownership-v1'
            or value.get('build_policy')!=login.PROBE_BUILD_POLICY
            or value.get('source',{}).get('sha256')!=login.OPENSSL_SHA256
            or value.get('future_reuse_requires_separate_exact_admission') is not True
            or not isinstance(value.get('files'),dict) or not 1<=len(value['files'])<=2048):
        raise ValueError('selected_retained_crypto_policy')
    total=0
    for name,pin in value['files'].items():
        parts=PurePosixPath(name)
        if (parts.is_absolute() or '..' in parts.parts or '\\' in name
                or type(pin.get('bytes')) is not int or not 0<=pin['bytes']<=64*1024*1024):
            raise ValueError('selected_retained_crypto_member')
        path=crypto/name
        if (any(p.is_symlink() for p in (path,*path.parents[:len(parts.parts)]))
                or not path.is_file() or path.stat().st_size!=pin['bytes']
                or prior.sha(path)!=pin['sha256']):
            raise ValueError('selected_retained_crypto_file_identity')
        total+=pin['bytes']
    if (total!=value['total_bytes'] or total>128*1024*1024
            or value['files'].get('libcrypto.lib',{}).get('sha256')!=CRYPTO_LIBRARY_SHA
            or {p.relative_to(crypto).as_posix() for p in crypto.rglob('*') if p.is_file()}
                !=set(value['files'])|{'manifest.json'}):
        raise ValueError('selected_retained_crypto_inventory')
    pins=json.loads((HERE/'intact-build-reuse-pins.json').read_text())
    # Preserve every previously qualified core/adapter/header byte. The new main
    # is the sole protocol-scope addition; no compatibility or policy patch.
    sources=pins['build']['source_files_sha256']
    if any(prior.sha(root/name)!=expected for name,expected in sources.items()):
        raise ValueError('selected_qualified_core_source_changed')
    return crypto,{'manifest_sha256':CRYPTO_MANIFEST_SHA,'static_library_sha256':CRYPTO_LIBRARY_SHA,
        'qualified_archive_sha256_reference':CRYPTO_ARCHIVE_SHA,'artifact_id':12078663003,
        'files_revalidated':len(value['files']),'bytes_revalidated':total,
        'crypto_rebuilt':False,'prior_auth_only_probe_executed':False,
        'qualified_core_source_sha256':sources}


def prepare_project(root, project, crypto):
    project.mkdir()
    native=root/'native-android';windows=HERE/'windows'
    sources=[windows/'shard_play_probe.c',windows/'winsock_compat.c',windows/'wrapped_login.c',
        native/'engine/auth/coh_auth.c',native/'engine/auth/coh_auth_openssl.c',
        native/'src/coh_blowfish.c',native/'protocol/coh_protocol.c']
    def quoted(path):
        if '"' in str(path) or '\n' in str(path) or ';' in str(path):
            raise ValueError('selected_project_path')
        return '"'+path.as_posix()+'"'
    (project/'CMakeLists.txt').write_text(
        'cmake_minimum_required(VERSION 3.24)\nproject(CohSelectedShardPlay C)\nset(CMAKE_C_STANDARD 11)\n'
        'set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreaded)\nadd_executable(coh-selected-shard-play\n'
        +'\n'.join(quoted(p) for p in sources)+')\n'
        +'target_compile_definitions(coh-selected-shard-play PRIVATE _CRT_SECURE_NO_WARNINGS WIN32_LEAN_AND_MEAN _WIN32_WINNT=0x0601 WINVER=0x0601)\n'
        +'target_include_directories(coh-selected-shard-play PRIVATE '+' '.join(quoted(p) for p in
            (windows/'compat',crypto/'include',native/'include'))+')\n'
        +'target_link_libraries(coh-selected-shard-play PRIVATE '+quoted(crypto/'libcrypto.lib')
        +' ws2_32 gdi32 crypt32 bcrypt advapi32 user32)\n',encoding='utf-8')
    return sources


def build_probe(root, temporary, output, retained, runner):
    crypto,admission=admit_crypto(retained,root)
    project,build=temporary/'selected-project',temporary/'selected-build'
    sources=prepare_project(root,project,crypto)
    policy=login.PROBE_BUILD_POLICY
    runner.run('configure-selected-probe',['cmake','-S',project,'-B',build,'-G',policy['cmake_generator'],'-A',policy['architecture']],timeout=180)
    runner.run('build-selected-probe',['cmake','--build',build,'--config',policy['configuration'],'--parallel',policy['parallel']],timeout=180)
    binary=output/'coh-selected-shard-play.exe'
    shutil.copy2(build/'Release/coh-selected-shard-play.exe',binary)
    identity=login.probe_identity(binary)
    # Revalidate immutable retained inputs after linking as well.
    if admit_crypto(retained,root)[1]!=admission:raise ValueError('selected_crypto_changed_during_link')
    return binary,dict(binary=identity,retained_crypto=admission,
        probe_source_sha256={p.relative_to(root).as_posix():prior.sha(p) for p in sources},
        generated_project_sha256=prior.sha(project/'CMakeLists.txt'),
        build_policy=policy,server_rebuilt=False,core_modified=False,
        db_client_linked=False,map_client_linked=False)


def account_sql():
    # Reuse the unchanged normal paid account insert. Replace only its old
    # Auth-only cardinality assertion, since this experiment owns real shard 1.
    original=auth_service_profile.account_sql()
    assertion="IF (SELECT COUNT(*) FROM dbo.server)<>0 THROW 51000,'auth-only server table must remain empty',1;\n"
    if original.count(assertion)!=1:raise ValueError('selected_account_fixture_source_changed')
    account=original.replace(assertion,'')
    return account+('INSERT dbo.user_data(uid,user_data,user_data_new,user_game_data,user_game_data_new) '
        'VALUES(900001,0x'+bytes(16).hex()+',0x'+bytes(112).hex()+',0x'+bytes(16).hex()+',0x'+bytes(112).hex()+');\n'
        "IF (SELECT COUNT(*) FROM dbo.server WHERE id=1 AND ip='127.0.0.1' AND client_port=7000)<>1 "
        "OR (SELECT COUNT(*) FROM dbo.server)<>1 OR (SELECT COUNT(*) FROM dbo.user_data)<>1 "
        "THROW 51000,'selected fixture cardinality',1;\n")


def admit_probe(value,send_cap):
    integers={'state','protocol','shards','received_frames','sent_bytes','elapsed_ms','send_cap'}
    positive={'passed','selected_shard_verified','live_grant_retained_then_wiped','local_sensitive_buffers_wiped',
        'authorization_invalid_after_close','socket_cleanup_complete'}
    negative={'password_retained_after_close','db_login_attempted','authenticated_db_map_handoff_verified',
        'checksum_policy_relaxed','nondevelopment_version_admitted','real_server_provenance_verified_by_probe'}
    if (type(send_cap) is not int or send_cap not in (7,1024) or not isinstance(value,dict)
            or set(value)!=integers|positive|negative|{'schema'}
            or value.get('schema')!='coh-selected-shard-play-probe-v1'
            or any(type(value.get(k)) is not int for k in integers)
            or any(value.get(k) is not True for k in positive)
            or any(value.get(k) is not False for k in negative)
            or (value['state'],value['protocol'],value['shards'],value['received_frames'],value['send_cap'])!=(7,191021,1,4,send_cap)
            or not 0<value['sent_bytes']<=4096 or not 0<=value['elapsed_ms']<=22000):
        raise ValueError('selected_native_probe_scope')
    return value


def run_probe(binary,port,send_cap,temporary):
    if type(port) is not int or not 20000<=port<=59999 or type(send_cap) is not int or send_cap not in (7,1024):
        raise ValueError('selected_probe_owned_input')
    job=login.OwnedJob();child=None;clean=False
    credentials=bytearray((password_fixture.ACCOUNT+'\n'+password_fixture.PASSWORD+'\n').encode('ascii'))
    try:
        with tempfile.TemporaryFile(dir=temporary) as output:
            child=subprocess.Popen([str(binary),str(port),str(send_cap)],cwd=temporary,
                stdin=subprocess.PIPE,stdout=output,stderr=subprocess.DEVNULL)
            job.assign(child)
            child.communicate(input=credentials,timeout=25)
            if child.returncode!=0 or os.fstat(output.fileno()).st_size>8192:
                raise ValueError('selected_private_probe_failed')
            output.seek(0)
            result=admit_probe(json.loads(output.read(8193)),send_cap)
    finally:
        for i in range(len(credentials)):credentials[i]=0
        if child is not None:
            pipe_clean=activation.close_streams([child.stdin]) if child.stdin is not None else True
            try:clean=job.stop(child) and pipe_clean
            finally:
                if job.handle:
                    try:job.kernel.CloseHandle(job.handle)
                    finally:job.handle=None
        elif job.handle:
            clean=bool(job.kernel.CloseHandle(job.handle));job.handle=None
    if not clean:raise ValueError('selected_probe_owned_cleanup')
    return result


class SelectedScope:
    def __init__(self,retained,send_cap=1024,db_candidate_generation=None):
        if db_candidate_generation is not None and type(db_candidate_generation) is not activation.DbCandidateGeneration:
            raise ValueError('selected_candidate_generation_type')
        self.retained,self.send_cap=retained,send_cap
        self.db_candidate_generation=db_candidate_generation

    def prepare(self,root,temporary,output,runner,proof,sql,sql_runner):
        proof['selected_scope_source_sha256']=admit_scope_sources(root)
        self.binary,proof['selected_probe_build']=build_probe(root,temporary,output,self.retained,runner)
        password_fixture.write_private_fixture(temporary/'private-credentials')
        account=temporary/'private-selected-account.sql';account.write_text(account_sql(),encoding='ascii')
        sql_runner.run('seed-private-selected-password',[*sql,'-i',temporary/'private-credentials/credential.sql'],timeout=150)
        sql_runner.run('seed-private-selected-account-userdata',[*sql,'-i',account],timeout=150)
        if activation.scalar(sql,USERDATA_QUERY,temporary)!=1:raise ValueError('selected_userdata_not_complete')
        proof.update(selected_scope='fresh_encrypted_login_shard_1_ac_play_ok_then_wipe',
            auth_only_negative_cases_repeated=False,db_login_attempted=False,
            grant_values_exported=False,private_credentials_exported=False,
            complete_userdata_preflight_verified=True)

    def exercise(self,temporary,proof,sql,ports,auth_child,db_child,auth,db,auth_start,db_start,sql_pid,sql_start):
        def observe_db():
            if self.db_candidate_generation is None:
                return activation.service_process_snapshot(db_child,db,db_start)
            return activation.service_process_snapshot(db_child,db,db_start,
                expected_binary_sha256=self.db_candidate_generation.binary_sha256)
        def observe():
            result={'auth':activation.service_process_snapshot(auth_child,auth,auth_start),
                'db':observe_db(),
                'sql':login.owned_process_snapshot(sql_pid),
                'channel':activation.owned_channel(auth_child.pid,db_child.pid,ports[0]),
                'game_listener':activation.game_listener(db_child.pid)}
            if (result['sql']!=sql_start or login.inspect_listeners(auth_child.pid)!=set(ports)
                    or activation.scalar(sql,"SET NOCOUNT ON;SELECT COUNT(*) FROM cohauth.dbo.worldstatus WHERE idx=1 AND status=1;",temporary)!=1):
                raise ValueError('selected_owned_runtime_unavailable')
            return result
        proof['selected_runtime_before_probe']=observe()
        if activation.scalar(sql,USERDATA_QUERY,temporary)!=1:raise ValueError('selected_userdata_not_complete')
        if login.probe_identity(self.binary)!=proof['selected_probe_build']['binary']:
            raise ValueError('selected_probe_binary_changed')
        proof['client_login_attempted']=True
        proof['selected_probe_result']=run_probe(self.binary,ports[1],self.send_cap,temporary)
        proof['selected_runtime_after_probe']=observe()
        return True


def admit_scope_sources(root):
    names=('deployment/hosted_selected_shard_play.py','deployment/windows/shard_play_probe.c')
    committed={}
    for name in names:
        relative='native-android/engine/auth-interop/'+name
        try:
            raw=subprocess.check_output(['git','-C',str(root),'show','HEAD:'+relative],stderr=subprocess.DEVNULL,timeout=30)
        except subprocess.CalledProcessError:
            raise ValueError('selected_scope_not_owned_by_head') from None
        path=root/relative
        if path.is_symlink() or path.read_bytes()!=raw:raise ValueError('selected_scope_not_owned_by_head')
        committed[relative]=hashlib.sha256(raw).hexdigest()
    return committed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source-root','output','auth-success-archive','auth-candidate-stage','retained-intact-stage'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--expected-commit',required=True)
    parser.add_argument('--send-cap',type=int,choices=(7,1024),default=1024)
    args=parser.parse_args()
    value=activation.run(args,SelectedScope(args.retained_intact_stage.resolve(),args.send_cap))
    print(json.dumps({key:value.get(key) for key in ('passed','failure','original_interserver_shard_activation_verified',
        'selected_shard_play_verified','authenticated_db_map_handoff_verified')}))
    return 0 if value['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
