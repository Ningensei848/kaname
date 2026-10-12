"""Compare versioned synthetic source fixtures with reviewed conversion outputs."""
import difflib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from techkb.config import load_config
from techkb.converter import Converter
from techkb.extraction import extract_main
from techkb.html_cleaner import clean_html
from techkb.images import article_images
from techkb.normalize import normalize_markdown


def project(case):
    app, sources = load_config(ROOT / 'config/app.yaml', ROOT / 'config/sources.yaml')
    source = next(source for source in sources if source.id == case['source_id'])
    raw = (ROOT / case['html']).read_bytes()
    extracted = extract_main(raw, source.content_selector) if source.extract_main or source.content_selector else raw
    markdown = normalize_markdown(Converter().convert(clean_html(extracted)))
    return markdown, article_images(extracted, case['url'], markdown[:app.llm.max_input_chars])


def check(case):
    markdown, images = project(case)
    expected = (ROOT / case['markdown']).read_text(encoding='utf-8')
    differences = list(difflib.unified_diff(expected.splitlines(), markdown.splitlines(),
                                          fromfile=case['markdown'], tofile='current', lineterm=''))
    if images != case['images']:
        differences.append('Image candidates changed:\n' + json.dumps(images, ensure_ascii=False, indent=2))
    return differences


def cases():
    return json.loads((ROOT / 'tests/fixtures/corpus/manifest.json').read_text())['cases']


def main():
    failed = False
    for case in cases():
        diff = check(case)
        print(f"{case['id']}: {'changed' if diff else 'unchanged'}")
        if diff:
            failed = True
            print('\n'.join(diff))
    return int(failed)


if __name__ == '__main__':
    sys.exit(main())
