"""Select CI checks from fixed Git endpoints; unknown changes require all checks."""
import argparse
import os
from pathlib import Path
import subprocess

SOURCES_TESTS = ['test_extraction', 'test_google_research', 'test_html_cleaner', 'test_images', 'test_fetcher', 'test_regression_corpus']
APP_TESTS = ['test_e2e', 'test_composer', 'test_gemini', 'test_batch_sdk', 'test_publication', 'test_site', 'test_pages', 'test_image_refresh', 'test_pipeline', 'test_parallel', 'test_batch', 'test_usage_recovery']


def classify(paths):
    scopes = set()
    web = False
    for path in paths:
        if path == 'config/sources.yaml':
            scopes.add('sources')
        elif path == 'config/app.yaml':
            scopes.add('app'); web = True
        elif path.startswith('config/image-repairs/') and path.endswith(('.yaml', '.yml', '.json')):
            scopes.add('images')
        elif path.startswith('web/'):
            web = True
        elif path.startswith('docs/') or path in {'README.md', '.gitignore'}:
            pass
        elif path.startswith(('src/', 'tests/')) or path in {'pyproject.toml', 'requirements.lock', 'requirements-browser.lock'}:
            scopes.add('full')
            if path.startswith(('src/techkb/publication/', 'src/techkb/pages', 'src/techkb/site', 'src/techkb/composer', 'src/techkb/models', 'src/techkb/config', 'src/techkb/normalize', 'src/techkb/hashes', 'src/techkb/images', 'tests/test_publication', 'tests/test_site', 'tests/test_pages')):
                web = True
        else:
            scopes.add('full'); web = True
    if 'full' in scopes:
        python = 'full'
    else:
        python = ','.join(sorted(scopes)) or 'none'
    return {'python': python, 'web': str(web).lower()}


def selected_tests(scope):
    if scope == 'full':
        return []
    tests = set()
    for part in scope.split(','):
        tests.update({'sources': SOURCES_TESTS, 'app': APP_TESTS, 'images': ['test_image_refresh']}[part])
    return [f'tests/{name}.py' for name in sorted(tests)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base'); parser.add_argument('--head')
    parser.add_argument('--run', help='run a selected Python scope')
    args = parser.parse_args()
    if args.run is not None:
        subprocess.run(['python', '-m', 'techkb', 'validate-config'], check=True)
        # Regression tests do not validate the changed production plan itself.
        if args.run == 'full' or 'images' in args.run.split(','):
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
            from techkb.image_refresh import load_plan
            for plan in sorted(Path('config/image-repairs').glob('*.json')):
                load_plan(plan)
        subprocess.run(['python', '-m', 'pytest', '-q', *selected_tests(args.run)], check=True)
        return
    try:
        if not args.base or not args.head or set(args.base) == {'0'}:
            raise ValueError('missing comparison endpoint')
        # Treat rename as deletion + addition so both contracts are checked.
        result = subprocess.run(['git', 'diff', '--no-renames', '--name-only', '-z', args.base, args.head, '--'],
                                check=True, capture_output=True)
        paths = result.stdout.decode('utf-8').split('\0')
        scope = classify([path for path in paths if path])
    except (ValueError, UnicodeError, subprocess.CalledProcessError):
        scope = {'python': 'full', 'web': 'true'}
    output = '\n'.join(f'{key}={value}' for key, value in scope.items()) + '\n'
    print(output, end='')
    if os.environ.get('GITHUB_OUTPUT'):
        with Path(os.environ['GITHUB_OUTPUT']).open('a') as file:
            file.write(output)


if __name__ == '__main__':
    main()
