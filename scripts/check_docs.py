#!/usr/bin/env python3
"""Check bilingual document counterparts and repository-relative Markdown links.

Code fences are examples rather than hyperlinks. External URLs and local-only
historical evidence written as inline code are deliberately not fetched.
"""
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = sorted([*ROOT.glob('*.md'), *(ROOT / 'docs').glob('*.md'),
                    *(ROOT / 'public/fonts').glob('README*.md')])
    failures = []
    checked_links = 0
    for path in files:
        source = re.sub(r'```[\s\S]*?```', '', path.read_text(encoding='utf-8'))
        name = path.name
        counterpart = name.replace('.zh-CN.md', '.md') if name.endswith('.zh-CN.md') else name[:-3] + '.zh-CN.md'
        if not path.with_name(counterpart).is_file():
            failures.append(f'{path.relative_to(ROOT)}: missing {counterpart}')
        if f']({counterpart})' not in source:
            failures.append(f'{path.relative_to(ROOT)}: missing language switch link to {counterpart}')
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
    print(f'Checked {len(files)} bilingual documents and {checked_links} local links.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
