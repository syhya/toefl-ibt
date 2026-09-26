"""Restore reviewed paragraph/line boundaries without rewriting saved content.

Only source identities, text hashes and character spans are shipped. No private
passage text is embedded in the layout manifest, and no greeting/signoff regex
is applied to unfamiliar questions. Some source signatures intentionally share
one line. The same projection serves active practice and historical review.
"""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re

MANIFEST = Path(__file__).resolve().parents[1] / 'shared/reading-layouts.json'


def normalized(text):
    return re.sub(r'\s+', ' ', text).strip()


@lru_cache(maxsize=1)
def layouts():
    data = json.loads(MANIFEST.read_text())
    if data.get('schemaVersion') != 1:
        raise ValueError('Unsupported reading layout manifest')
    result = {}
    for layout in data['layouts']:
        for source in layout['sources']:
            key = source['questionId']
            if key in result:
                raise ValueError('Duplicate reading layout identity')
            result[key] = (source, layout)
    return result


def project_reading_layout(question):
    binding = layouts().get(question.get('id'))
    if not binding:
        return question
    source, layout = binding
    original_source = question.get('source', {})
    if any(original_source.get(key) != source[key] for key in ['materialId', 'page']):
        return question
    blocks = question.get('stemBlocks', [])
    index = source['blockIndex']
    kind = layout.get('blockType', 'message')
    if kind not in ['message', 'paragraph'] or not 0 <= index < len(blocks) or blocks[index].get('type') != kind:
        return question
    paragraphs = blocks[index].get('paragraphs') if kind == 'message' else [blocks[index].get('text')]
    if not isinstance(paragraphs, list) or not all(isinstance(p, str) for p in paragraphs):
        return question
    text = normalized(' '.join(paragraphs))
    if hashlib.sha256(text.encode()).hexdigest() != layout['textSha256']:
        return question
    runs = layout.get('runs', [])
    if not runs:
        return question
    start = runs[0]['start']
    if start:
        # Two source records duplicate the instruction inside the message. It
        # may be removed there only while an identical preceding block remains.
        if (not layout.get('omitRepeatedInstruction') or index == 0
                or blocks[index - 1].get('type') != 'instruction'
                or normalized(blocks[index - 1].get('text', '')) != text[:start].strip()):
            return question
    restored = []
    cursor = start
    for run in runs:
        a, b, separator = run['start'], run['end'], run['breakBefore']
        if not (type(a) is int and type(b) is int and cursor <= a < b <= len(text)):
            return question
        gap, line = text[cursor:a], text[a:b]
        if (gap.strip() or line != line.strip() or restored and not gap
                or separator not in ['line', 'paragraph']):
            return question
        if separator == 'line' and restored:
            restored[-1] += '\n' + line
        else:
            restored.append(line)
        cursor = b
    if text[cursor:].strip() or restored == paragraphs:
        return question
    result = deepcopy(question)
    if kind == 'message':
        result['stemBlocks'][index]['paragraphs'] = restored
    else:
        result['stemBlocks'][index]['text'] = '\n\n'.join(restored)
    return result
