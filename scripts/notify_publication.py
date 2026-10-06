"""Report publication workflow failures without article text or credentials."""
import os
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from techkb.operations import publish_issues


def failure_event(run_id, repository, collect, audit, export, publish, pages, collection_outcome=""):
    if not re.fullmatch(r'\d+', run_id) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise ValueError('invalid publication run identity')
    stages = [name for name, result in [('collection', collection_outcome), ('audit', audit),
              ('export', export), ('content', publish), ('pages', pages)] if result in {'failure', 'cancelled'}]
    if collect in {'failure', 'cancelled'} and not any(stage in stages for stage in ('collection', 'audit', 'export')):
        stages.insert(0, 'collection_workflow')
    if not stages:
        return []
    return [dict(kind='publication', key='publication-' + run_id, stages=stages,
                 run_url=f'https://github.com/{repository}/actions/runs/{run_id}')]


if __name__ == '__main__':
    try:
        events = failure_event(os.environ['GITHUB_RUN_ID'], os.environ['GITHUB_REPOSITORY'],
            *[os.environ.get(key, '') for key in ('COLLECT_RESULT', 'AUDIT_OUTCOME', 'EXPORT_OUTCOME', 'PUBLISH_RESULT', 'PAGES_RESULT')], collection_outcome=os.environ.get('COLLECT_OUTCOME', ''))
        result = publish_issues(events, os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_TOKEN']) if events else {'created': 0}
        print('Publication failure notifications created:', result['created'])
    except Exception:
        print('publication_notification_failed', file=sys.stderr); sys.exit(1)
