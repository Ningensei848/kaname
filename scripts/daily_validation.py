"""Reuse successful Checks for this exact main commit; otherwise run tests here.

Configuration and all operational state/publication checks still run daily.
Only the duplicate unit test suite can be satisfied by the CI result.
"""
import argparse
from http.client import HTTPException
import json
import os
import re
import subprocess
import sys
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from kaname.read_snapshot import read_workers


def github_json(path, token):
    request = Request('https://api.github.com' + path, headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    })
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def checks_evidence(environment, fetch=github_json):
    """Never use a PR, another SHA, a partial run or an older successful retry."""
    repository = environment.get('GITHUB_REPOSITORY', '')
    sha = environment.get('GITHUB_SHA', '')
    token = environment.get('GH_TOKEN', '')
    if (environment.get('GITHUB_REF') != 'refs/heads/main' or
            environment.get('GITHUB_API_URL') != 'https://api.github.com' or
            not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository) or
            not re.fullmatch(r'[0-9a-f]{40}', sha) or not token):
        return {'unit_tests': 'local', 'reason': 'unsupported_or_missing_ci_context'}
    try:
        query = urlencode({'head_sha': sha, 'branch': 'main', 'event': 'push', 'per_page': 100})
        response = fetch(f'/repos/{repository}/actions/workflows/checks.yml/runs?{query}', token)
        runs = response['workflow_runs']
        if response['total_count'] != len(runs) or not runs:
            raise ValueError('incomplete evidence')
        # Do not hide a newer running/failed run by querying only successes.
        run = max(runs, key=lambda item: item['id'])
        if (run['head_sha'] != sha or run['head_branch'] != 'main' or run['event'] != 'push' or
                run['path'] != '.github/workflows/checks.yml' or
                run['repository']['full_name'] != repository or
                run['status'] != 'completed' or run['conclusion'] != 'success' or
                type(run['id']) is not int or run['id'] <= 0 or
                type(run['run_attempt']) is not int or run['run_attempt'] <= 0):
            raise ValueError('unaccepted run')
        jobs = fetch(f'/repos/{repository}/actions/runs/{run["id"]}/attempts/'
                     f'{run["run_attempt"]}/jobs?per_page=100', token)
        if jobs['total_count'] != len(jobs['jobs']):
            raise ValueError('incomplete jobs')
        for name in ('repository-checks', 'scope', 'test', 'web-preview'):
            matches = [job for job in jobs['jobs'] if job['name'] == name]
            if (len(matches) != 1 or matches[0]['status'] != 'completed' or
                    matches[0]['conclusion'] != 'success' or matches[0]['head_sha'] != sha):
                raise ValueError('required check missing')
        return {'unit_tests': 'checks', 'reason': 'same_main_commit_passed',
                'checks_run_id': run['id'], 'checks_run_attempt': run['run_attempt']}
    except (HTTPException, URLError, OSError, ValueError, KeyError, TypeError):
        # Do not log API exceptions: request details may contain credentials.
        return {'unit_tests': 'local', 'reason': 'checks_not_confirmed'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-tests', action='store_true', help='Run unit tests here regardless of CI')
    args = parser.parse_args(argv)
    # Production configuration is checked on every run, before API/GCS auth.
    subprocess.run([sys.executable, '-m', 'kaname', 'validate-config'], check=True)
    read_workers()  # Reject invalid operational bounds before auth or generation.
    evidence = ({'unit_tests': 'local', 'reason': 'explicit_full_tests'} if args.full_tests else
                checks_evidence(os.environ))
    print(json.dumps(evidence), flush=True)
    if evidence['unit_tests'] == 'local':
        subprocess.run([sys.executable, '-m', 'pytest', '-q'], check=True)


if __name__ == '__main__':
    main()
