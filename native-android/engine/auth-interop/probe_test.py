"""Real TCP lifecycle without any authentication-success or DB response."""
import json
import os
import signal
import socket
import subprocess


def qualify(binary):
    checks = 0
    env = dict(os.environ, ASAN_OPTIONS='detect_leaks=0:halt_on_error=1', UBSAN_OPTIONS='halt_on_error=1')
    for mode in ('cancel', 'timeout', 'invalid_credentials'):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(3)
            args = [str(binary), '127.0.0.1', str(listener.getsockname()[1]), '127.0.0.1', '7000',
                    '127.0.0.1', '7002', '1', '0', 'source-test-version', '01000000000000000000000000000000', '1000', '123456']
            process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            try:
                credentials = b'fixture\nfixture-only\n' if mode != 'invalid_credentials' else b'longaccountinvalid\nfixture-only\n'
                process.stdin.write(credentials)
                process.stdin.close()
                process.stdin = None
                if mode != 'invalid_credentials':
                    peer, _ = listener.accept()
                    with peer:
                        if mode == 'cancel':
                            process.send_signal(signal.SIGTERM)
                        stdout, stderr = process.communicate(timeout=5)
                        assert process.returncode == 1 and not stderr
                        result = json.loads(stdout)
                        assert result['auth_receipts'] == 0 and result['shard_choices'] == 0
                        assert result['opened_sockets'] == result['closed_sockets'] == 1
                        assert result['cleanup_complete'] and not result['real_account_login_verified']
                        assert result['interrupted'] == (mode == 'cancel')
                        assert result['phase'] == (10 if mode == 'cancel' else 12)
                        assert result['status'] in (5, 7)
                        peer.settimeout(2)
                        assert peer.recv(1024) == b''  # No hello means no credential request.
                        checks += 9
                else:
                    stdout, stderr = process.communicate(timeout=5)
                    assert process.returncode == 2 and not stdout
                    assert stderr == b'Invalid private credential input\n'
                    checks += 2
                assert b'fixture-only' not in stdout + stderr and b'longaccountinvalid' not in stdout + stderr
                checks += 1
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
    return {'passed': True, 'checks': checks, 'real_tcp_lifecycle_cases': 2,
            'credential_input_rejection_cases': 1, 'auth_success_replies_sent': 0,
            'real_account_login_verified': False, 'credentials_logged': False}
