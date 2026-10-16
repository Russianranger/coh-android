#!/usr/bin/env python3
"""Qualify read-only schema admission; optionally inspect exact original source."""
import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from source_audit import qualify
from checksum_candidate import qualify as qualify_checksum_candidate

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path,
                        help='Optional expanded original source tree; all listed source pins must match')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--sanitize', action='store_true', help='Run declared checksum candidate with ASan/UBSan too')
    args = parser.parse_args()
    suites = ['test_deployment'] + (['test_hosted_stage'] if args.source_root else [])
    result = subprocess.run(['python3', '-m', 'unittest', '-v', *suites], cwd=HERE,
                            capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    proof = {'schema': 'coh-auth-deployment-qualification-v1', 'passed': True,
             'metadata_tests': {'passed': True, 'runner_log': result.stderr},
             'source_audit': None, 'sql_executed': False, 'schema_changed': False,
             'real_account_login_verified': False, 'native_live_world': False,
             'physical_thor_accepted': False,
             'environment_tools_available': {name: shutil.which(name) is not None
                                             for name in ('wine', 'wine64', 'sqlcmd', 'odbcinst', 'cc', 'objcopy', 'nm')},
             'network_connections_opened': False, 'process_or_listener_probing': False,
             'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(HERE.iterdir())
                               if p.is_file() and p.suffix in ('.py', '.sql', '.json')}}
    if args.source_root:
        with tempfile.TemporaryDirectory(prefix='coh-auth-source-audit-') as temp:
            proof['source_audit'] = qualify(args.source_root.resolve(), Path(temp))
            proof['declared_checksum_candidate'] = qualify_checksum_candidate(args.source_root.resolve(), Path(temp), args.sanitize)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'passed': True, 'original_source_audited': proof['source_audit'] is not None,
                      'sql_executed': False, 'real_account_login_verified': False}))


if __name__ == '__main__':
    main()
