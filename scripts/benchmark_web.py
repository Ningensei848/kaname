"""Repeat a fixed public Web build and its complete browser acceptance.

No collection, cloud client, publication or dependency updates. Outputs stay on
the builder's filesystem; record medians and variation instead of a single run.
"""
import argparse
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'web')]
from build_pages import build_pages
from check_pages import check
from kaname.publication.git_snapshot import content_snapshot


def benchmark(content, commit, repeats=3):
    if type(repeats) is not int or not 2 <= repeats <= 10:
        raise ValueError('benchmark requires 2 to 10 repetitions')
    manifest, original, _ = content_snapshot(content, commit)
    samples, expected_artifact, expected_checks = [], None, None
    with tempfile.TemporaryDirectory(prefix='benchmark-', dir=ROOT / 'web/.cache') as temporary:
        for number in range(repeats):
            # Each repetition has a fresh catalog/checkout/provenance check.
            if content_snapshot(content, commit)[1] != original:
                raise ValueError('benchmark_input_changed')
            output = Path(temporary) / str(number)
            started = time.perf_counter()
            built = build_pages(content, commit, output)
            after_build = time.perf_counter()
            checked = check(content, commit, output)
            finished = time.perf_counter()
            if content_snapshot(content, commit)[1] != original:
                raise ValueError('benchmark_input_changed')
            coverage = {key: checked[key] for key in ('notes', 'search_links', 'image_notes',
                'image_workers', 'external_requests', 'offline_search_clicks', 'approved_image_requests')}
            if expected_artifact is None:
                expected_artifact, expected_checks = built['artifact_digest'], coverage
            if built['artifact_digest'] != expected_artifact or coverage != expected_checks:
                raise ValueError('benchmark_validation_scope_changed')
            sample = dict(build_seconds=round(after_build - started, 3),
                          check_seconds=round(finished - after_build, 3),
                          total_seconds=round(finished - started, 3))
            samples.append(sample)
            print(json.dumps(dict(repetition=number + 1, **sample)), file=sys.stderr, flush=True)
    # Temporary outputs are gone; the previous successful pointer must not name
    # them. build_pages points to the retained immutable web/public artifact.
    fields = ('build_seconds', 'check_seconds', 'total_seconds')
    return dict(status='passed', content_commit=commit, dataset_digest=manifest['dataset_digest'],
                artifact_digest=expected_artifact, coverage=expected_checks, samples=samples,
                median={key: statistics.median(s[key] for s in samples) for key in fields},
                minimum={key: min(s[key] for s in samples) for key in fields},
                maximum={key: max(s[key] for s in samples) for key in fields})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content', type=Path, required=True)
    parser.add_argument('--content-commit', required=True)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    try:
        print(json.dumps(benchmark(args.content, args.content_commit, args.repeats)))
    except Exception:
        print('{"status":"failed","code":"web_benchmark_failed"}', file=sys.stderr)
        raise SystemExit(1)
