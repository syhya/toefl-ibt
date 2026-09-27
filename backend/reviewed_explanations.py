"""Bilingual review notes bound to the exact Example 1 question and reference key.

These are project-authored explanations, not ETS commentary. They are served
only through the existing review/authorized-feedback boundary. Original imports,
answers and score snapshots are never rewritten when a note is displayed.
"""
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import unicodedata

MANIFEST = Path(__file__).resolve().parents[1] / 'shared/example1-explanations.en.json'
ZH_MANIFEST = MANIFEST.with_name('example1-explanations.zh-CN.json')


def _normalize(value):
    if isinstance(value, str):
        return re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', value)).strip()
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, dict):
        return {key:_normalize(item) for key,item in value.items()}
    return value


def explanation_fingerprint(q):
    keys = ['id', 'type', 'taskType', 'prompt', 'context', 'transcript', 'passageTemplate',
            'choices', 'tokens', 'slots', 'answer', 'acceptedAnswers', 'sourceReferenceAnswer',
            'expectedTokenOrder', 'sentencePrefix', 'terminalPunctuation']
    payload = {key:q[key] for key in keys if key in q}
    source = q.get('source') or {}
    payload['source'] = {key:source[key] for key in ['materialId', 'page'] if key in source}
    if q.get('audio'):
        payload['audio'] = {key:q['audio'][key] for key in
            ['url', 'materialId', 'sourceSha256', 'segmentId'] if key in q['audio']}
    if q.get('sourceVariant'):
        payload['sourceVariant'] = {key:q['sourceVariant'][key] for key in ['id', 'paperPrompt'] if key in q['sourceVariant']}
    if q.get('stemBlocks'):
        blocks = deepcopy(q['stemBlocks'])
        # Display-only paragraph restoration must not invalidate the content
        # binding. The same words still have to match, in the same order.
        for block in blocks:
            if block.get('type') == 'message':
                block['paragraphs'] = ' '.join(block.get('paragraphs', []))
        payload['stemBlocks'] = blocks
    elif 'passage' in q:
        payload['passage'] = q['passage']
    if q.get('blanks'):
        fields = ['id', 'number', 'prefix', 'suffix', 'length', 'missingLength', 'missingLetters',
                  'fullWord', 'answer', 'acceptedAnswers']
        payload['blanks'] = [{key:b[key] for key in fields if key in b} for b in q['blanks']]
    raw = json.dumps(_normalize(payload), sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode()).hexdigest()


@lru_cache(maxsize=2)
def manifest(language='en'):
    if language not in ('en', 'zh-CN'):
        raise ValueError('Unsupported reviewed explanation language')
    data = json.loads((ZH_MANIFEST if language == 'zh-CN' else MANIFEST).read_text(encoding='utf-8'))
    if data.get('schemaVersion') != 1 or data.get('language') != language:
        raise ValueError('Unsupported reviewed explanation manifest')
    return data


def reviewed_explanation(q):
    data = manifest()
    record = data['questions'].get(q.get('id'))
    if not record:
        return None
    translated = manifest('zh-CN')['questions'].get(q.get('id'))
    unresolved = lambda item: item.get('auditStatus') == 'answer-conflict' or (item.get('answerConflict') or {}).get('status') == 'needs-review'
    if (unresolved(q) or any(unresolved(b) for b in q.get('blanks', []))
            or explanation_fingerprint(q) != record['fingerprint']
            or not translated or translated['fingerprint'] != record['fingerprint']):
        return {'origin':'unavailable', 'label':'Explanation requires a new source check', 'language':'en',
                'reviewed':True, 'text':'This saved question or answer key differs from the version reviewed for this explanation. The reviewed rationale is withheld rather than applied to a different question. Check the original source and the saved answer key.',
                'warnings':[], 'translations':{'zh-CN':{
                    'language':'zh-CN', 'label':'解析需要重新核验来源',
                    'text':'此题保存的题目或答案键与解析所依据的版本不一致，或对应语言的解析尚未完成版本核验。暂不展示校核解析，请对照原始资料和已保存的答案键核查。',
                    'evidence':[], 'warnings':[]}}}
    source = q.get('source') or {}
    return {'origin':'local_assistance', 'label':'Reviewed explanation · Not ETS-authored',
            'language':'en', 'reviewed':True, 'reviewedAt':data['reviewedAt'],
            'text':record['text'], 'evidence':deepcopy(record.get('evidence', [])),
            'warnings':deepcopy(record.get('warnings', [])),
            'translations':{'zh-CN':{'language':'zh-CN', 'label':'校核解析 · 非 ETS 官方编写',
                'text':translated['text'], 'evidence':deepcopy(translated.get('evidence', [])),
                'warnings':deepcopy(translated.get('warnings', []))}},
            'source':{key:source[key] for key in ['page', 'materialId'] if key in source}}
