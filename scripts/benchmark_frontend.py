"""Compare cold mobile page loads of two verified artifacts of one dataset."""
import argparse
import json
from pathlib import Path
from statistics import median
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'web')]

from kaname_web.artifact import load_artifact
from kaname_web.browser_acceptance import served_artifact, browser_session


def measure(artifact, samples):
    marker, files = load_artifact(artifact)
    results = []
    with served_artifact(artifact) as origin:
        for number in range(samples):
            with browser_session(origin, set()) as (context, page, _observed):
                page.set_viewport_size({'width': 375, 'height': 900})
                session = context.new_cdp_session(page)
                session.send('Network.enable')
                session.send('Network.setCacheDisabled', {'cacheDisabled': True})
                session.send('Network.emulateNetworkConditions', dict(offline=False, latency=150,
                    downloadThroughput=200000, uploadThroughput=93750))
                session.send('Emulation.setCPUThrottlingRate', {'rate': 4})
                page.add_init_script('''
                  window.kanameMetrics = {lcp_ms: 0, cls: 0};
                  new PerformanceObserver(list => {
                    for (const entry of list.getEntries()) window.kanameMetrics.lcp_ms = entry.startTime;
                  }).observe({type: 'largest-contentful-paint', buffered: true});
                  new PerformanceObserver(list => {
                    for (const entry of list.getEntries()) if (!entry.hadRecentInput) window.kanameMetrics.cls += entry.value;
                  }).observe({type: 'layout-shift', buffered: true});
                ''')
                page.goto(origin + '/kaname/', wait_until='load', timeout=120000)
                page.evaluate('document.fonts.ready')
                # fetch() is not part of the load event. Wait for the original
                # eager index and the bounded prefetch to finish before counting
                # transferred bytes; otherwise in-flight traffic is omitted.
                page.wait_for_load_state('networkidle', timeout=120000)
                page.wait_for_timeout(500)
                sample = page.evaluate('''() => {
                  const nav = performance.getEntriesByType('navigation')[0];
                  const all = performance.getEntriesByType('resource');
                  const resources = all.filter(r => !r.name.includes('/page/2'));
                  return {...window.kanameMetrics,
                    dom_elements: document.querySelectorAll('*').length,
                    cards: document.querySelectorAll('.note-card').length,
                    dcl_ms: nav.domContentLoadedEventEnd,
                    fcp_ms: performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? 0,
                    transfer_bytes: nav.transferSize + resources.reduce((n, r) => n + r.transferSize, 0),
                    requests: 1 + resources.length,
                    search_index_requests: resources.filter(r => r.name.includes('contentIndex.json')).length,
                    prefetch_bytes: all.filter(r => r.name.includes('/page/2')).reduce((n, r) => n + r.transferSize, 0)};
                }''')
                results.append(sample)
                print(json.dumps(dict(sample=number + 1, artifact=marker['artifact_digest'][:12], **sample)),
                      file=sys.stderr, flush=True)
    return dict(artifact_digest=marker['artifact_digest'], dataset_digest=marker['dataset_digest'],
                html_bytes=len(files['index.html']), samples=results,
                median={key: round(median(row[key] for row in results), 3) for key in results[0]},
                minimum={key: round(min(row[key] for row in results), 3) for key in results[0]},
                maximum={key: round(max(row[key] for row in results), 3) for key in results[0]})


def compare(before, after, samples=3):
    first, _ = load_artifact(before)
    second, _ = load_artifact(after)
    if first['dataset_digest'] != second['dataset_digest'] or first['content_commit'] != second['content_commit']:
        raise ValueError('benchmark requires the same fixed public edition')
    return dict(conditions='Chromium, 375px, cold cache, 150ms RTT, 1.6Mbps down, CPU 4x',
                before=measure(before, samples), after=measure(after, samples))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True)
    parser.add_argument('--after', type=Path, required=True)
    parser.add_argument('--samples', type=int, choices=range(1, 6), default=3)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = compare(args.before, args.after, args.samples)
    data = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data)
    print(data)
