"""Publish validated snapshots with non-force Git and remote byte verification."""
import base64
import os
from pathlib import Path
import re
import subprocess
import tempfile

from .distribution import publish_snapshot
from .pages import content_snapshot
from .publication import ExportError


def publish_remote(snapshot, remote, workspace):
    # HTTPS GitHub is the production route. Existing local bare repos support
    # offline integration tests, without changing any network trust policy.
    if not re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\.git', remote):
        if not Path(remote).is_dir():
            raise ExportError('invalid_publication_remote')
    env = dict(os.environ)
    env['GIT_TERMINAL_PROMPT'] = '0'
    token = env.get('GITHUB_TOKEN')
    if token and remote.startswith('https://github.com/'):
        number = int(env.get('GIT_CONFIG_COUNT', '0'))
        env['GIT_CONFIG_COUNT'] = str(number + 1)
        env[f'GIT_CONFIG_KEY_{number}'] = 'http.https://github.com/.extraheader'
        env[f'GIT_CONFIG_VALUE_{number}'] = 'AUTHORIZATION: basic ' + base64.b64encode(('x-access-token:' + token).encode()).decode()
    def git(*args, code='publication_git_failed'):
        result = subprocess.run(['git', '-c', 'core.hooksPath=' + os.devnull, *map(str, args)],
                                env=env, capture_output=True, timeout=120)
        if result.returncode:
            raise ExportError(code)
        return result.stdout
    def remote_head():
        output = git('ls-remote', '--exit-code', '--heads', remote, 'refs/heads/content', code='content_remote_unavailable')
        match = re.fullmatch(rb'([0-9a-f]{40})\trefs/heads/content\n', output)
        if not match:
            raise ExportError('invalid_remote_content_ref')
        return match[1].decode()
    parent = remote_head()  # Absence/access failure is never an empty branch.
    with tempfile.TemporaryDirectory(prefix='kaname-publish-', dir=workspace) as temporary:
        bare, checkout = Path(temporary) / 'distribution.git', Path(temporary) / 'verified'
        git('init', '--bare', '--initial-branch=content', bare)
        git('--git-dir=' + str(bare), 'fetch', '--no-tags', '--no-recurse-submodules', remote,
            'refs/heads/content:refs/heads/content')
        if git('--git-dir=' + str(bare), 'rev-parse', 'refs/heads/content').strip().decode() != parent:
            raise ExportError('content_remote_conflict')
        result = publish_snapshot(snapshot, bare)
        if remote_head() != parent:
            raise ExportError('content_remote_conflict')
        if not result['unchanged']:
            git('--git-dir=' + str(bare), 'push', '--porcelain', remote,
                result['commit'] + ':refs/heads/content', code='content_push_failed')
        if remote_head() != result['commit']:
            raise ExportError('content_remote_conflict')
        git('clone', '--single-branch', '--branch', 'content', '--no-local', remote, checkout)
        manifest, _, _ = content_snapshot(checkout, result['commit'])
        if manifest['dataset_digest'] != result['dataset_digest'] or len(manifest['notes']) != result['notes']:
            raise ExportError('remote_snapshot_mismatch')
        return result
