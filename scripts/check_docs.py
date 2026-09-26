#!/usr/bin/env python3
"""Check the bilingual root README, English-only docs, and Markdown links.

Code fences are examples rather than hyperlinks. External URLs and local-only
historical evidence written as inline code are deliberately not fetched.
"""
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = sorted([*ROOT.glob('*.md'), *(ROOT / 'docs').rglob('*.md'),
                    *(ROOT / 'public/fonts').glob('README*.md'),
                    *(ROOT / 'examples').rglob('*.md'),
                    *(ROOT / '.github').rglob('*.md')])
    failures = []
    for name in ['README.md', 'README.zh-CN.md']:
        if not (ROOT / name).is_file():
            failures.append(f'Missing bilingual project overview: {name}')
    checked_links = 0
    for path in files:
        source = re.sub(r'```[\s\S]*?```', '', path.read_text(encoding='utf-8'))
        if path in [ROOT / 'README.md', ROOT / 'README.zh-CN.md']:
            counterpart = 'README.md' if path.name == 'README.zh-CN.md' else 'README.zh-CN.md'
            if not path.with_name(counterpart).is_file():
                failures.append(f'{path.relative_to(ROOT)}: missing {counterpart}')
            if f']({counterpart})' not in source:
                failures.append(f'{path.relative_to(ROOT)}: missing language switch link to {counterpart}')
        elif path.name.endswith('.zh-CN.md'):
            failures.append(f'{path.relative_to(ROOT)}: only the root README has a translated edition')
        for match in re.finditer(r'\]\((<?[^)]+>?)\)', source):
            raw = match.group(1).strip().strip('<>')
            parsed = urlsplit(raw)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            checked_links += 1
            if not target.is_relative_to(ROOT) or not target.exists():
                failures.append(f'{path.relative_to(ROOT)}: broken repository link {raw}')
    if failures:
        print('\n'.join(failures), file=sys.stderr)
        return 1
    print(f'Checked {len(files)} Markdown documents and {checked_links} local links; only the root README is bilingual.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
