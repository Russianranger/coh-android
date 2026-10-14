"""Controlled private-file/Game-handoff tests; no native runtime qualification."""
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'android/guest/client_live_directory_control.py'
spec = importlib.util.spec_from_file_location('controlled_live_guest', SOURCE)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


class LiveControlTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='coh-live-control-host-')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        os.chmod(self.directory, 0o700)
        self.path = self.directory / m.FILENAME
        self.ctx = SimpleNamespace(secrets=[])
        self.counter = 0
        # Each unittest represents a distinct guest process. Replay/cap tests
        # exercise multiple calls without resetting this state inside a case.
        with m._claim_lock:
            m._claimed.clear()
        self.expected = self.context()
        self.environment = {'KEEP': 'unchanged', m.PREFIX: '1', m.PREFIX+'_AUTH': 'f'*64,
            m.PREFIX+'_ENDPOINT': '127.0.0.1:9999', m.PREFIX+'UNKNOWN': 'stale'}

    def context(self):
        self.counter += 1
        proof = m.VerifiedFixtureProducer('9'*64, '8'*40, m.PROOF_SCOPE,
            'a'*64, 9484288, 'b'*64, 'c'*64, 'd'*64)
        return m.ExpectedContext(f'{self.counter:032x}', f'1792000000000-{self.counter:012x}',
            '12345678-1234-1234-1234-123456789abc', 'a'*64, 9484288, 'b'*64, 'c'*64, 'd'*64,
            '/state/diagnostic/client-work-'+'1'*24+'/data', str(self.directory.stat().st_dev),
            '127.0.0.1:23456', 'e'*64, os.getuid(), proof)

    def document(self, expected=None):
        expected = expected or self.expected
        return {key: (1 if key == 'format' else m.RECIPE if key == 'recipe'
            else getattr(expected, key)) for key in m.FIELDS}

    def save(self, document=None, *, raw=None, mode=0o600):
        if self.path.is_file() and not self.path.is_symlink():
            os.chmod(self.path, 0o600)
        self.path.write_bytes(raw if raw is not None else json.dumps(
            document if document is not None else self.document(), ensure_ascii=False).encode())
        os.chmod(self.path, mode)

    def call(self, *, expected=None, path=None, role='Game', attempt=1, environment=None):
        return m.game_environment(self.environment if environment is None else environment, self.ctx,
            expected=self.expected if expected is None else expected,
            expected_path=self.path if path is None else path, native_role=role, game_attempt=attempt)

    def stock(self, result, reason=None):
        env, report = result
        self.assertFalse(any(key.startswith(m.PREFIX) for key in env if isinstance(key, str)))
        self.assertEqual(report['decision'], 'stock')
        self.assertFalse(report['native_provider_executed'])
        self.assertFalse(report['runtime_fixture_qualified_by_this_module'])
        if reason:
            self.assertEqual(report['reason'], reason)
        self.secret_free(report)

    def secret_free(self, report):
        text = json.dumps(report)
        for secret in self.ctx.secrets:
            self.assertNotIn(secret, text)
        self.assertNotIn('auth_nonce', text)
        self.assertLess(len(text), 1024)

    def test_absent_authority_is_default_stock_and_strips_shared_settings(self):
        original = dict(self.environment)
        self.stock(m.game_environment(self.environment, self.ctx))
        self.assertEqual(self.environment, original)

    def test_valid_control_only_selects_fresh_current_Game_environment(self):
        self.save()
        before = self.path.read_bytes()
        env, report = self.call()
        self.assertEqual(report['decision'], 'current_Game_handoff')
        self.assertEqual({k for k in env if k.startswith(m.PREFIX)}, {
            m.PREFIX, *(m.PREFIX+'_'+name for name in ('ENDPOINT','SESSION','AUTH','DEVICE','GUEST_ROOT','RECIPE','DESCRIPTOR'))})
        self.assertEqual(env[m.PREFIX+'_AUTH'], 'e'*64)
        self.assertEqual(env[m.PREFIX+'_SESSION'], self.expected.session_id)
        self.assertEqual(env['KEEP'], 'unchanged')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(set(self.ctx.secrets), {'e'*64, 'f'*64})
        self.secret_free(report)

    def test_Map_Db_and_shared_Wine_never_receive_live_variables(self):
        for role in ('MapServer','DbServer','Wine',None):
            self.stock(self.call(role=role), 'not_Game')
        self.assertEqual(m.strip_live_environment(self.environment), {'KEEP': 'unchanged'})

    def test_byte_environment_and_unknown_suffixes_are_stripped_too(self):
        env = dict(self.environment)
        env[m.PREFIX.encode() + b'_AUTH'] = b'7'*64
        env[m.PREFIX.encode() + b'UNKNOWN'] = b'stale'
        env[m.PREFIX + '_UNKNOWN_FUTURE_FLAG'] = 'stale'
        env[b'OTHER'] = b'unchanged'
        result, report = self.call(environment=env, role='MapServer')
        self.assertEqual(result, {'KEEP': 'unchanged', b'OTHER': b'unchanged'})
        self.assertIn('7'*64, self.ctx.secrets)
        self.secret_free(report)

    def test_every_ASCII_case_alias_is_removed_before_shared_role_diagnostic(self):
        env = dict(self.environment)
        env.update({'coh_client_live_directory': '1', 'Coh_Client_Live_Directory_Endpoint': 'old',
            'coh_client_live_directory_auth': '7'*64,
            b'cOh_cLiEnT_LiVe_dIrEcToRy_aUtH': b'8'*64,
            b'coh_client_live_directory_unknown': b'old'})
        original = dict(env)
        # Secret aliases must be registered before even the refusal reason is
        # created, not merely removed from the resulting environment.
        initial_secret = m._secret
        registrations = []
        def register(ctx, value):
            initial_secret(ctx, value)
            if value in ('7'*64, b'8'*64):
                registrations.append(value)
        with patch.object(m, '_secret', side_effect=register):
            result, report = self.call(environment=env, role='MapServer')
        self.assertEqual(result, {'KEEP': 'unchanged'})
        self.assertEqual(env, original)
        self.assertEqual(report['reason'], 'not_Game')
        self.assertEqual(registrations, ['7'*64, b'8'*64])
        self.assertTrue({'e'*64, 'f'*64, '7'*64, '8'*64}.issubset(self.ctx.secrets))
        self.secret_free(report)

    def test_ASCII_prefix_boundaries_preserve_unrelated_and_Unicode_lookalikes(self):
        keep = {'XCOH_CLIENT_LIVE_DIRECTORY': 'before', 'COH_CLIENT_LIVE_DIRECTOR': 'short',
            'COH_CLIENT_LIVE_DİRECTORY_AUTH': 'Unicode I',
            'COH_CLıENT_LIVE_DIRECTORY_AUTH': 'Unicode dotless i',
            b'XCOH_CLIENT_LIVE_DIRECTORY': b'before', b'COH_CLIENT_LIVE_DIRECTOR': b'short',
            b'COH_CLIENT_LIVE_D\xffRECTORY': b'nonASCII'}
        env = {**keep, 'coh_client_live_directory_future_unknown': 'strip',
            b'CoH_cLiEnT_lIvE_dIrEcToRyUNKNOWN': b'strip'}
        self.assertEqual(m.strip_live_environment(env), keep)

    def test_AUTH_alias_redaction_precedes_current_authority_validation(self):
        env = {**self.environment, 'coh_client_live_directory_auth': '7'*64,
            b'COh_CLIent_LIVE_DirectORY_AUTH': b'8'*64}
        def validate(expected):
            self.assertIs(expected, self.expected)
            self.assertTrue({'e'*64, 'f'*64, '7'*64, '8'*64}.issubset(self.ctx.secrets))
            return False
        with patch.object(m, '_expected_valid', side_effect=validate) as observed:
            self.stock(self.call(environment=env), 'authority_absent')
        observed.assert_called_once_with(self.expected)

    def test_fresh_Game_assignment_has_no_case_alias_collision(self):
        self.save()
        env = {**self.environment, 'coh_client_live_directory_auth': '7'*64,
            b'cOh_cLiEnT_LiVe_dIrEcToRy_sEsSiOn': b'old',
            'Coh_Client_Live_Directory_Recipe': 'old'}
        result, report = self.call(environment=env)
        self.assertEqual(report['decision'], 'current_Game_handoff')
        self.assertEqual(result[m.PREFIX+'_AUTH'], self.expected.auth_nonce)
        self.assertEqual(result[m.PREFIX+'_SESSION'], self.expected.session_id)
        self.assertTrue(all(k == m._environment_key(k) for k in result if m._environment_key(k).startswith(m.PREFIX)))
        self.assertFalse(any(isinstance(k, bytes) for k in result))
        self.assertIn('7'*64, self.ctx.secrets)
        self.secret_free(report)

    def test_second_attempt_and_reused_control_do_not_retry(self):
        self.save()
        self.assertEqual(self.call()[1]['decision'], 'current_Game_handoff')
        with patch.object(m, '_read_private_bytes', side_effect=AssertionError('must not reread/reconnect')):
            self.stock(self.call(), 'already_attempted')
            self.stock(self.call(attempt=2), 'not_first_Game_attempt')

    def test_bool_or_absent_attempt_is_never_first_attempt(self):
        for attempt in (True, False, None, 0, -1, '1', 2):
            self.stock(self.call(attempt=attempt), 'not_first_Game_attempt')

    def test_optional_missing_path_is_stock_and_cannot_activate_later(self):
        self.stock(m.game_environment(self.environment, self.ctx, expected=self.expected,
            native_role='Game', game_attempt=1), 'control_path_absent')
        self.save()
        self.stock(self.call(), 'already_attempted')

    def test_missing_file_is_stock_and_no_retry_after_file_appears(self):
        self.stock(self.call(), 'private_control_unavailable')
        self.save()
        self.stock(self.call(), 'already_attempted')

    def test_bare_config_flags_or_dictionary_proof_cannot_grant_authority(self):
        value = self.document();value['qualified']=True;self.save(value)
        self.stock(self.call(), 'document_fields_refused')
        for proof in (None, True, {'qualified':True}):
            expected = replace(self.context(), fixture_producer=proof)
            with patch.object(m, '_read_private_bytes', side_effect=AssertionError('unqualified cannot read config')):
                self.stock(self.call(expected=expected), 'authority_absent')

    def test_exact_current_fixture_producer_pins_and_scope_required(self):
        for field, value in [('proof_sha256','invalid'),('producer_commit','f'*39),('scope','host-only'),
            ('game_sha256','0'*64),('game_bytes',1),('runtime_sha256','0'*64),
            ('helper_sha256','0'*64),('descriptor_sha256','0'*64)]:
            expected=self.context();expected=replace(expected,fixture_producer=replace(expected.fixture_producer,**{field:value}))
            self.stock(self.call(expected=expected), 'authority_absent')

    def test_stale_identity_fields_are_refused(self):
        changes={'session_id':'0'*32,'operation_id':'1792000000000-ffffffffffff',
            'process_instance':'ffffffff-ffff-ffff-ffff-ffffffffffff','game_sha256':'0'*64,
            'game_bytes':9484287,'runtime_sha256':'0'*64,'helper_sha256':'0'*64,
            'descriptor_sha256':'0'*64,'guest_root':'/state/other/data','device':'0',
            'endpoint':'127.0.0.1:23457','auth_nonce':'7'*64,'recipe':'other'}
        for field,value in changes.items():
            expected=self.context();document=self.document(expected);document[field]=value;self.save(document)
            self.stock(self.call(expected=expected), 'current_identity_mismatch')

    def test_noncanonical_expected_values_cannot_authorize_file_read(self):
        changes={'session_id':'A'*32,'operation_id':'not-current','process_instance':'UPPER',
            'game_sha256':'a'*63,'game_bytes':True,'runtime_sha256':'0x'+'1'*64,
            'helper_sha256':'A'*64,'descriptor_sha256':' ','guest_root':'/state/diagnostic/client-work-1/data',
            'device':'01','endpoint':'127.0.0.1:023456','auth_nonce':'A'*64,'owner_uid':True}
        for field,value in changes.items():
            self.stock(self.call(expected=replace(self.context(),**{field:value})), 'authority_absent')

    def test_foreign_and_invalid_endpoints_or_unsigned_devices_refused(self):
        for endpoint in ('localhost:1','127.0.0.2:1','[::1]:1','127.0.0.1:0','127.0.0.1:65536',
            '127.0.0.1:1\n','127.0.0.1:1;command'):
            self.stock(self.call(expected=replace(self.context(),endpoint=endpoint)), 'authority_absent')
        for device in ('-1','+1','00',str(1<<64),'1.0','1\n',1):
            self.stock(self.call(expected=replace(self.context(),device=device)), 'authority_absent')

    def test_duplicate_JSON_keys_and_every_nonce_are_redacted(self):
        raw=json.dumps(self.document()).encode();raw=raw[:-1]+b',"auth_nonce":"'+b'7'*64+b'"}'
        self.save(raw=raw)
        self.stock(self.call(), 'duplicate_json_key')
        self.assertIn('e'*64,self.ctx.secrets);self.assertIn('7'*64,self.ctx.secrets)

    def test_malformed_JSON_registers_bounded_nonce_before_failure(self):
        self.save(raw=b'{"auth_nonce":"'+b'7'*64+b'", BAD JSON')
        self.stock(self.call(), 'invalid_json')
        self.assertIn('7'*64,self.ctx.secrets)

    def test_escaped_nonce_still_registered_and_unknown_fields_not_echoed(self):
        value=self.document();value['auth_nonce']='7'*64;raw=json.dumps(value).replace('auth_nonce','auth\\u005fnonce').encode()
        self.save(raw=raw);self.stock(self.call(), 'current_identity_mismatch');self.assertIn('7'*64,self.ctx.secrets)

    def test_non_ASCII_bytes_and_escaped_non_ASCII_values_refused(self):
        self.save(raw=b'{"auth_nonce":"'+b'7'*64+b'", "other":"\xc3\xa9"}')
        self.stock(self.call(), 'non_ascii_document');self.assertIn('7'*64,self.ctx.secrets)
        expected=self.context();value=self.document(expected);value['endpoint']='\u00e9'
        self.save(raw=json.dumps(value).encode());self.stock(self.call(expected=expected), 'document_types_refused')

    def test_unknown_missing_and_wrong_top_level_fields_refused(self):
        for change in ('unknown','missing','list'):
            expected=self.context();value=self.document(expected)
            if change=='unknown':value['token_to_echo']='7'*64
            if change=='missing':del value['descriptor_sha256']
            if change=='list':value=[value]
            self.save(value);self.stock(self.call(expected=expected), 'document_fields_refused')

    def test_JSON_bool_float_and_constants_never_coerce_identity(self):
        for field,value in [('format',True),('format',1.0),('game_bytes',True),('game_bytes',9484288.0),('device',123)]:
            expected=self.context();document=self.document(expected);document[field]=value;self.save(document)
            self.stock(self.call(expected=expected), 'document_types_refused')
        self.save(raw=b'{"format":NaN}')
        self.stock(self.call(expected=self.context()), 'invalid_json_constant')

    def test_empty_oversized_and_permissions_refuse(self):
        for raw,mode in [(b'',0o600),(b'x'*(m.MAX_BYTES+1),0o600),(b'{}',0o644),(b'{}',0o400),(b'{}',0o4600)]:
            self.save(raw=raw,mode=mode);self.stock(self.call(expected=self.context()), 'file_refused')

    def test_valid_JSON_exact_16KiB_bound_preserves_bytes(self):
        raw=json.dumps(self.document()).encode();self.save(raw=raw+b' '*(m.MAX_BYTES-len(raw)))
        self.assertEqual(self.call()[1]['decision'], 'current_Game_handoff')
        self.assertEqual(self.path.stat().st_size,m.MAX_BYTES)

    def test_symbolic_final_file_is_never_followed(self):
        target=self.directory/'target';target.write_text(json.dumps(self.document()));os.chmod(target,0o600)
        self.path.symlink_to(target)
        self.stock(self.call(),'file_refused');self.assertTrue(self.path.is_symlink())

    def test_hardlinked_control_refused_without_removal(self):
        self.save();other=self.directory/'other';os.link(self.path,other)
        self.stock(self.call(),'file_refused');self.assertEqual(other.stat().st_ino,self.path.stat().st_ino)

    def test_directory_and_FIFO_final_leaf_refused_without_blocking(self):
        self.path.mkdir();self.stock(self.call(),'file_refused');self.path.rmdir()
        os.mkfifo(self.path,0o600);self.stock(self.call(expected=self.context()),'file_refused')

    def test_symlink_ancestor_and_relative_or_wrong_filename_refused(self):
        self.save();alias=self.directory/'alias';alias.symlink_to(self.directory,target_is_directory=True)
        self.stock(self.call(path=alias/m.FILENAME),'private_control_unavailable')
        for path in ('client-live-directory-control.json',self.directory/'wrong.json',
            '//'+str(self.directory).lstrip('/')+'/'+m.FILENAME,
            str(self.directory)+'/../'+self.directory.name+'/'+m.FILENAME,
            str(self.directory)+'//'+m.FILENAME):
            self.stock(self.call(expected=self.context(),path=path),'path_refused')

    def test_wrong_owner_device_or_unprivate_directory_refused(self):
        self.save()
        self.stock(self.call(expected=replace(self.expected,owner_uid=os.getuid()+1)), 'directory_refused')
        os.chmod(self.directory,0o777)
        self.stock(self.call(expected=self.context()), 'directory_refused')
        os.chmod(self.directory,0o700)
        self.stock(self.call(expected=replace(self.context(),device='0')), 'directory_refused')

    def test_inode_replacement_during_read_refused_and_FDs_balanced(self):
        self.save();real_read=m.os.read;done=False
        before=len(os.listdir('/proc/self/fd'))
        def race(fd,length):
            nonlocal done
            value=real_read(fd,length)
            if not done:
                replacement=self.directory/'replacement';replacement.write_bytes(self.path.read_bytes());os.chmod(replacement,0o600)
                os.replace(replacement,self.path);done=True
            return value
        with patch.object(m.os,'read',side_effect=race):self.stock(self.call(),'file_changed')
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_current_file_mutation_during_read_refused(self):
        self.save();real_read=m.os.read;done=False
        def race(fd,length):
            nonlocal done
            value=real_read(fd,length)
            if not done:
                with self.path.open('ab') as output:output.write(b' ')
                done=True
            return value
        with patch.object(m.os,'read',side_effect=race):self.stock(self.call(),'file_changed')

    def test_ancestor_replacement_during_read_refused_and_closes_handles(self):
        child=self.directory/'held';child.mkdir(mode=0o700);self.path=child/m.FILENAME;self.save()
        real_read=m.os.read;done=False;before=len(os.listdir('/proc/self/fd'))
        def race(fd,length):
            nonlocal done
            value=real_read(fd,length)
            if not done:
                child.rename(self.directory/'old');child.mkdir(mode=0o700);done=True
            return value
        with patch.object(m.os,'read',side_effect=race):self.stock(self.call(),'directory_changed')
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_read_error_and_no_follow_open_error_do_not_leak(self):
        self.save();before=len(os.listdir('/proc/self/fd'))
        with patch.object(m.os,'read',side_effect=OSError('7'*64)):
            self.stock(self.call(),'private_control_unavailable')
        self.assertEqual(len(os.listdir('/proc/self/fd')),before)

    def test_secret_registration_failure_is_stock_before_file_read(self):
        self.ctx.secrets=()
        with patch.object(m,'_read_private_bytes',side_effect=AssertionError('cannot read before redaction')):
            self.stock(self.call(),'redaction_unavailable')

    def test_attempt_registry_is_bounded_and_never_retries_socket(self):
        for _ in range(m._MAX_CLAIMS):
            expected=self.context();self.save(self.document(expected))
            self.assertEqual(self.call(expected=expected)[1]['decision'],'current_Game_handoff')
        self.stock(self.call(expected=self.context()),'attempt_bound')


if __name__ == '__main__':
    unittest.main()
