"""Check tracked documentation paths/anchors, including this repo's Git history.

Standard library only. External sites are not contacted; repository blob links
are checked against the exact locally available Git ref instead of mutable HTTP.
"""
import argparse
from functools import lru_cache
import html
import json
from pathlib import Path
import re
import subprocess
import unicodedata
from urllib.parse import unquote, urlsplit


def prose(text):
    """Keep line numbers while excluding fenced/indented and inline code."""
    lines, fence = [], None
    for line in text.splitlines():
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})', line)
        if marker and fence is None:
            fence = marker[1]
            lines.append('')
        elif fence is not None:
            if re.fullmatch(r' {0,3}' + re.escape(fence[0]) + '{' + str(len(fence)) + r',}\s*', line):
                fence = None
            lines.append('')
        elif line.startswith(('    ', '\t')):
            lines.append('')
        else:
            lines.append(re.sub(r'(`+).*?\1', '', line))
    return '\n'.join(lines)


def anchors(text):
    # Headings retain inline-code text, unlike link extraction.
    visible = prose(re.sub(r'`([^`\n]+)`', r'\1', text))
    found = set(re.findall(r'<a\s+(?:[^>]*?\s)?(?:id|name)=["\']([^"\']+)', visible))
    counts = {}
    for line in visible.splitlines():
        match = re.match(r'^ {0,3}#{1,6}\s+(.+?)(?:\s+#+)?$', line)
        if not match:
            continue
        title = re.sub(r'<[^>]+>', '', html.unescape(match[1])).lower()
        slug = ''.join(c for c in title if c in '-_' or not unicodedata.category(c).startswith(('P', 'S', 'C')))
        slug = re.sub(r'\s', '-', slug)
        number = counts.get(slug, 0)
        counts[slug] = number + 1
        candidate = slug + (f'-{number}' if number else '')
        while candidate in found:
            number += 1
            counts[slug] = number + 1
            candidate = f'{slug}-{number}'
        found.add(candidate)
    return found


def destination(value):
    if value.startswith('<'):
        end = value.find('>')
        return value[1:end] if end >= 0 else None
    depth = 0
    for index, char in enumerate(value):
        if char == '(':
            depth += 1
        elif char == ')':
            if depth == 0:
                return value[:index]
            depth -= 1
        elif char.isspace() and depth == 0:
            return value[:index]
    return value


def links(text):
    text = prose(text)
    definitions = {}
    for match in re.finditer(r'^ {0,3}\[([^\]]+)\]:\s*(.+)$', text, re.M):
        definitions[' '.join(match[1].casefold().split())] = destination(match[2])
    for number, line in enumerate(text.splitlines(), 1):
        if re.match(r'^ {0,3}\[[^\]]+\]:', line):
            continue
        for match in re.finditer(r'(?<!\\)\]\(\s*', line):
            target = destination(line[match.end():])
            if target:
                yield number, target
        for match in re.finditer(r'(?<!\\)\[([^\]]+)\](?:\[([^\]]*)\])?', line):
            label = ' '.join((match[2] or match[1]).casefold().split())
            if label in definitions:
                yield number, definitions[label]


class Documents:
    def __init__(self, root, repository='Ningensei848/kaname'):
        self.root = Path(root).resolve()
        self.repository = repository.casefold()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.DEVNULL)

    @lru_cache(maxsize=None)
    def git_file(self, target):
        # A ref may contain slashes. Prefer the longest existing ref, and never
        # interpret URL text as Git options or a shell command.
        parts = target.split('/')
        for end in range(len(parts) - 1, 0, -1):
            ref, path = '/'.join(parts[:end]), '/'.join(parts[end:])
            if ref.startswith('-') or ':' in ref or any(p == '..' for p in parts):
                continue
            for revision in (ref, 'refs/remotes/origin/' + ref):
                try:
                    commit = self.git('rev-parse', '--verify', '--end-of-options', revision + '^{commit}').decode().strip()
                    return self.git('show', commit + ':' + path)
                except subprocess.CalledProcessError:
                    continue
        raise ValueError('missing_git_document')

    def resolve(self, source, target):
        url = urlsplit(html.unescape(target))
        if url.scheme or url.netloc:
            prefix = '/' + self.repository + '/blob/'
            if url.hostname != 'github.com' or not url.path.casefold().startswith(prefix):
                return None, None
            return self.git_file(unquote(url.path[len(prefix):])), unquote(url.fragment)
        if not url.path:
            path = self.root / source
        else:
            path = (self.root / source).parent / unquote(url.path)
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root):
            raise ValueError('link_outside_repository')
        if not resolved.exists():
            raise ValueError('missing_local_document')
        return resolved.read_bytes() if resolved.is_file() else None, unquote(url.fragment)

    def check(self, paths):
        issues, count = [], 0
        for name in paths:
            text = (self.root / name).read_text(encoding='utf-8')
            for line, target in links(text):
                count += 1
                try:
                    data, fragment = self.resolve(name, target)
                    if data is None or not fragment:
                        continue
                    if re.fullmatch(r'L\d+(?:-L\d+)?', fragment):
                        bounds = list(map(int, re.findall(r'\d+', fragment)))
                        if bounds[0] < 1 or bounds != sorted(bounds) or bounds[-1] > len(data.splitlines()):
                            raise ValueError('invalid_line_reference')
                    elif fragment not in anchors(data.decode('utf-8')):
                        raise ValueError('missing_document_anchor')
                except (ValueError, OSError, UnicodeError) as exc:
                    issues.append(dict(path=name, line=line, target=target, code=str(exc)))
        return dict(status='failed' if issues else 'passed', documents=len(paths), links=count, issues=issues)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    documents = Documents(args.root)
    paths = documents.git('ls-files', '-z', '--', 'README.md', 'docs/*.md', 'docs/**/*.md').decode().split('\0')
    # Deleted paths are absent from the working tree while a change is prepared.
    paths = sorted(p for p in paths if p and (args.root / p).is_file())
    result = documents.check(paths)
    print(json.dumps(result, ensure_ascii=False))
    return int(bool(result['issues']))


if __name__ == '__main__':
    raise SystemExit(main())
