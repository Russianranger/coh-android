#!/usr/bin/env python3
"""Read ArmPort CI results from check-run annotations.

Step logs and artifacts are not reachable from the agent environments used on
this branch, so every job reports through annotations (notices, warnings,
errors). This waits for one job of the "ArmPort build" run on a commit, saves
its annotations, rebuilds any images exported by screen_export.py and prints
the report sections.

  ci_results.py --sha <commit> --job server-run [--out DIR] [--grep TEXT ...]
  ci_results.py --run <run id> --job client-run

  --grep     print only sections whose title or text contains one of these
  --no-wait  read whatever is there now

Uses the gh CLI (REST only; GraphQL is not available), or unauthenticated
public REST reads when gh is not installed. Images are written to DIR as
<title>.jpg.
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = 'Russianranger/coh-android'


def gh(path):
    try:
        r = subprocess.run(['gh', 'api', path], capture_output=True, text=True)
    except FileNotFoundError:
        # Public repository evidence needs no credentials. Do not read tokens
        # or fall back after a CLI authentication/permission failure.
        request = urllib.request.Request(
            'https://api.github.com/' + path,
            headers={'Accept': 'application/vnd.github+json',
                     'User-Agent': 'coh-armport-ci-results'})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    if r.returncode:
        raise RuntimeError(f'gh api {path}: {r.stderr.strip()}')
    return json.loads(r.stdout)


def find_run(sha):
    for _ in range(60):
        runs = gh(f'repos/{REPO}/actions/runs?head_sha={sha}')['workflow_runs']
        ids = [r['id'] for r in runs if r['name'] == 'ArmPort build']
        if ids:
            return ids[0]
        time.sleep(20)
    sys.exit(f'no ArmPort build run for {sha}')


def wait_job(run, name, wait):
    while True:
        jobs = gh(f'repos/{REPO}/actions/runs/{run}/jobs?per_page=50')['jobs']
        job = next((j for j in jobs if j['name'] == name), None)
        if job and (job['status'] == 'completed' or not wait):
            return job
        if not job and not wait:
            sys.exit(f'job {name} not found in run {run}')
        time.sleep(60)


def sections(annotations):
    """Split the buffered report notes ('### title' blocks) into (title, text)."""
    out = []
    for a in annotations:
        msg = a.get('message') or ''
        if '%0A' in msg[:300]:          # an escaped duplicate of a multi-line note
            continue
        parts = re.split(r'(?m)^### ', msg)
        if len(parts) == 1:
            out.append((a.get('title') or '', msg))
        for p in parts[1:]:
            title, _, body = p.partition('\n')
            out.append((title.strip(), body.rstrip()))
    return out


def images(annotations, out):
    found = {}
    for a in annotations:
        m = re.match(r'(.+) (\d+)/(\d+)$', a.get('title') or '')
        if m and re.fullmatch(r'[A-Za-z0-9+/=]+', (a.get('message') or '').strip()):
            found.setdefault(m.group(1), {})[int(m.group(2))] = a['message'].strip()
    paths = []
    for title, parts in found.items():
        path = out / (re.sub(r'[^A-Za-z0-9_-]+', '-', title) + '.jpg')
        try:
            path.write_bytes(base64.b64decode(''.join(parts[i] for i in sorted(parts))))
            paths.append(path)
        except ValueError:
            pass
    return paths


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sha')
    ap.add_argument('--run', type=int)
    ap.add_argument('--job', required=True)
    ap.add_argument('--out', type=Path, default=Path('ci-results'))
    ap.add_argument('--grep', nargs='*', default=[])
    ap.add_argument('--no-wait', action='store_true')
    a = ap.parse_args()
    if not (a.sha or a.run):
        sys.exit('give --sha or --run')
    run = a.run or find_run(a.sha)
    job = wait_job(run, a.job, not a.no_wait)
    a.out.mkdir(parents=True, exist_ok=True)
    ann = gh(f'repos/{REPO}/check-runs/{job["id"]}/annotations?per_page=100')
    (a.out / f'{a.job}-annotations.json').write_text(json.dumps(ann, indent=1))
    failed = [s['name'] for s in job.get('steps', []) if s.get('conclusion') == 'failure']
    print(f'run {run} job {a.job}: {job["status"]} {job.get("conclusion")}'
          + (f'; failed step: {", ".join(failed)}' if failed else ''))
    for path in images(ann, a.out):
        print(f'image: {path}')
    seen = set()
    for title, body in sections(ann):
        if 'Node.js 20' in body or not body.strip():
            continue
        if a.grep and not any(g.lower() in (title + body).lower() for g in a.grep):
            continue
        if re.fullmatch(r'[A-Za-z0-9+/=\s]+', body) and len(body) > 200:
            continue                    # image part
        key = (title, body[:80])
        if key in seen:
            continue
        seen.add(key)
        print(f'\n### {title}\n{body[:4000]}')


if __name__ == '__main__':
    main()
