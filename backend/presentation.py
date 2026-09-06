"""Validation and safe projection for source-verified structured question stems."""
import hashlib
import json
import re


SCHEMA = 'structured-v1'
STATUSES = {'source-verified', 'needs-review', 'source-review-only'}
SIMPLE_BLOCKS = {'instruction', 'title', 'paragraph', 'question', 'highlighted_sentence'}
BLOCK_TYPES = {*SIMPLE_BLOCKS, 'message', 'dialogue', 'table', 'list', 'form_diagram', 'essential_visual'}
ACTIVE_VISUAL_ROLE = 'essentialVisual'
LIST_MARKERS = {'bullet', 'decimal', 'lower-alpha'}
HASH = re.compile(r'^[0-9a-f]{64}$')
GENERIC_VISUAL_ALTS = {
    'image', 'photo', 'figure', 'diagram', 'visual', 'graphic', 'illustration', 'picture',
    'question image', 'question photo', 'question figure', 'question diagram', 'question visual',
    'question graphic', 'question illustration', 'question picture', 'original question',
    'original image', 'original photo', 'original figure', 'original visual', 'original question image',
    'original question visual', 'source image', 'source visual', 'original source image',
    'essential visual', 'question asset',
}


def is_structured(question):
    return question.get('presentationSchema') == SCHEMA


def has_legacy_question_image(question):
    return question.get('presentationSchema') is None and any(
        isinstance(asset, dict) and asset.get('role', 'stem') in {'stem', 'passage'}
        for asset in question.get('assets', [])
    )


def is_interactive(question):
    if has_legacy_question_image(question):
        return False
    return not is_structured(question) or question.get('structuredContentStatus') == 'source-verified'


def active_asset_roles(question, section=None):
    if is_structured(question):
        return {ACTIVE_VISUAL_ROLE}
    if has_legacy_question_image(question):
        return set()
    return {'stem', 'passage'} if section == 'reading' else {'stem'}


def referenced_essential_visual_indices(question):
    if not is_structured(question) or question.get('structuredContentStatus') != 'source-verified':
        return set()
    indices = {
        block['assetIndex']
        for block in question.get('stemBlocks', [])
        if isinstance(block, dict) and block.get('type') == 'essential_visual'
        and type(block.get('assetIndex')) is int and meaningful_visual_alt(block.get('alt'))
    }
    for block in question.get('stemBlocks', []):
        if not isinstance(block, dict) or block.get('type') != 'dialogue':
            continue
        for turn in block.get('turns', []):
            if isinstance(turn, dict) and type(turn.get('avatarAssetIndex')) is int:
                indices.add(turn['avatarAssetIndex'])
    return indices


def asset_is_active(question, asset, index, section=None):
    if is_structured(question):
        return (
            index in referenced_essential_visual_indices(question)
            and isinstance(asset, dict)
            and asset.get('role') == ACTIVE_VISUAL_ROLE
            and asset.get('highResolution') is True
            and meaningful_visual_alt(asset.get('alt'))
        )
    return not has_legacy_question_image(question) and asset.get('role', 'stem') in active_asset_roles(question, section)


def _strings(value):
    return list(value) if isinstance(value, list) and all(isinstance(item, str) for item in value) else None


def meaningful_visual_alt(value):
    if not isinstance(value, str):
        return False
    normalized = re.sub(r'[\W_]+', ' ', value.casefold()).strip()
    return bool(normalized) and normalized not in GENERIC_VISUAL_ALTS


def safe_stem_blocks(value):
    """Copy only documented display fields; never recursively expose importer metadata."""
    if not isinstance(value, list):
        return []
    result = []
    for block in value:
        if not isinstance(block, dict) or block.get('type') not in BLOCK_TYPES:
            continue
        kind = block['type']
        safe = {'type': kind}
        if kind in SIMPLE_BLOCKS:
            if isinstance(block.get('text'), str):
                safe['text'] = block['text']
        elif kind == 'message':
            for key in ['sender', 'recipient', 'date', 'subject']:
                if isinstance(block.get(key), str):
                    safe[key] = block[key]
            paragraphs = _strings(block.get('paragraphs'))
            if paragraphs is not None:
                safe['paragraphs'] = paragraphs
        elif kind == 'dialogue':
            turns = block.get('turns')
            if isinstance(turns, list):
                safe['turns'] = []
                for turn in turns:
                    if not isinstance(turn, dict) or not isinstance(turn.get('speaker'), str) or not isinstance(turn.get('text'), str):
                        continue
                    projected = {'speaker': turn['speaker'], 'text': turn['text']}
                    if type(turn.get('avatarAssetIndex')) is int:
                        projected['avatarAssetIndex'] = turn['avatarAssetIndex']
                    safe['turns'].append(projected)
        elif kind == 'table':
            if isinstance(block.get('caption'), str):
                safe['caption'] = block['caption']
            if isinstance(block.get('rowHeaders'), bool):
                safe['rowHeaders'] = block['rowHeaders']
            headers = _strings(block.get('headers'))
            rows = block.get('rows')
            if headers is not None:
                safe['headers'] = headers
            if isinstance(rows, list) and all(_strings(row) is not None for row in rows):
                safe['rows'] = [list(row) for row in rows]
        elif kind == 'list':
            items = _strings(block.get('items'))
            if items is not None:
                safe['items'] = items
            if isinstance(block.get('ordered'), bool):
                safe['ordered'] = block['ordered']
            if block.get('marker') in LIST_MARKERS:
                safe['marker'] = block['marker']
        elif kind == 'form_diagram':
            if type(block.get('highlightedPosition')) is int:
                safe['highlightedPosition'] = block['highlightedPosition']
        elif kind == 'essential_visual':
            if type(block.get('assetIndex')) is int:
                safe['assetIndex'] = block['assetIndex']
            if isinstance(block.get('alt'), str):
                safe['alt'] = block['alt']
        result.append(safe)
    return result


def validate_question(question, strict=False):
    """Return stable issue codes. Legacy questions intentionally remain compatible."""
    schema = question.get('presentationSchema')
    if schema is None:
        return []
    if schema != SCHEMA:
        return ['unsupported-presentation-schema']
    issues = []
    status = question.get('structuredContentStatus')
    if status not in STATUSES:
        issues.append('invalid-structured-content-status')
    elif strict and status != 'source-verified':
        issues.append('structured-content-not-source-verified')
    blocks = question.get('stemBlocks')
    if not isinstance(blocks, list) or not blocks:
        issues.append('structured-stem-blocks-missing')
        return issues
    assets = question.get('assets', [])
    if not isinstance(assets, list):
        assets = []
        issues.append('structured-assets-invalid')
    for asset in assets:
        if not isinstance(asset, dict) or asset.get('role') != ACTIVE_VISUAL_ROLE or asset.get('highResolution') is not True or not isinstance(asset.get('url'), str):
            issues.append('structured-asset-not-essential-high-resolution')
            break
        if not meaningful_visual_alt(asset.get('alt')):
            issues.append('essential-visual-alt-not-semantic')
            break
    for source in question.get('sourceEvidenceAssets', []):
        if not isinstance(source, dict) or source.get('reviewOnly') is not True or not isinstance(source.get('url'), str):
            issues.append('source-evidence-asset-not-review-only')
            break
    stimulus_source = question.get('stimulusSource')
    if stimulus_source is not None and (
        not isinstance(stimulus_source, dict)
        or not isinstance(stimulus_source.get('materialId'), str)
        or not stimulus_source['materialId'].strip()
        or type(stimulus_source.get('page')) is not int
        or stimulus_source['page'] < 1
        or not isinstance(stimulus_source.get('url'), str)
        or not stimulus_source['url'].strip()
    ):
        issues.append('invalid-stimulus-source')
    allowed = {
        **{kind: {'type', 'text'} for kind in SIMPLE_BLOCKS},
        'message': {'type', 'sender', 'recipient', 'date', 'subject', 'paragraphs'},
        'dialogue': {'type', 'turns'},
        'table': {'type', 'caption', 'headers', 'rows', 'rowHeaders'},
        'list': {'type', 'items', 'ordered', 'marker'},
        'form_diagram': {'type', 'highlightedPosition'},
        'essential_visual': {'type', 'assetIndex', 'alt'},
    }
    for block in blocks:
        if not isinstance(block, dict) or block.get('type') not in BLOCK_TYPES:
            issues.append('invalid-structured-block')
            continue
        kind = block['type']
        if set(block) - allowed[kind]:
            issues.append('unknown-structured-block-field')
        if kind in SIMPLE_BLOCKS:
            if not isinstance(block.get('text'), str) or not block['text'].strip():
                issues.append('structured-text-missing')
        elif kind == 'message':
            if any(key in block and not isinstance(block[key], str) for key in ['sender', 'recipient', 'date', 'subject']):
                issues.append('invalid-message-field')
            paragraphs = _strings(block.get('paragraphs'))
            if not paragraphs or any(not item.strip() for item in paragraphs):
                issues.append('message-paragraphs-missing')
        elif kind == 'dialogue':
            turns = block.get('turns')
            if not isinstance(turns, list) or not turns:
                issues.append('dialogue-turns-missing')
            elif any(not isinstance(turn, dict) or set(turn) - {'speaker', 'text', 'avatarAssetIndex'} or
                     not isinstance(turn.get('speaker'), str) or not turn['speaker'].strip() or
                     not isinstance(turn.get('text'), str) or not turn['text'].strip() or
                     ('avatarAssetIndex' in turn and (
                         type(turn.get('avatarAssetIndex')) is not int or
                         not 0 <= turn['avatarAssetIndex'] < len(assets) or
                         assets[turn['avatarAssetIndex']].get('role') != ACTIVE_VISUAL_ROLE or
                         assets[turn['avatarAssetIndex']].get('highResolution') is not True
                     )) for turn in turns):
                issues.append('invalid-dialogue-turn')
        elif kind == 'table':
            headers, rows = _strings(block.get('headers')), block.get('rows')
            if 'caption' in block and not isinstance(block['caption'], str):
                issues.append('invalid-table-caption')
            if 'rowHeaders' in block and not isinstance(block['rowHeaders'], bool):
                issues.append('invalid-table-row-headers')
            if not headers or not isinstance(rows, list) or not rows or any(_strings(row) is None or len(row) != len(headers) for row in rows):
                issues.append('invalid-table-cells')
        elif kind == 'list':
            items = _strings(block.get('items'))
            if not items or any(not item.strip() for item in items):
                issues.append('list-items-missing')
            if 'ordered' in block and not isinstance(block['ordered'], bool):
                issues.append('invalid-list-ordered')
            if 'marker' in block and block['marker'] not in LIST_MARKERS:
                issues.append('invalid-list-marker')
        elif kind == 'form_diagram':
            if type(block.get('highlightedPosition')) is not int or not 1 <= block['highlightedPosition'] <= 8:
                issues.append('invalid-form-diagram-position')
        elif kind == 'essential_visual':
            index = block.get('assetIndex')
            if type(index) is not int or not 0 <= index < len(assets) or not meaningful_visual_alt(block.get('alt')):
                issues.append('invalid-essential-visual-reference')
            elif assets[index].get('role') != ACTIVE_VISUAL_ROLE or assets[index].get('highResolution') is not True:
                issues.append('invalid-essential-visual-reference')
    return list(dict.fromkeys(issues))


def canonical_content(question):
    """The answer-free presentation payload bound by the optional curation manifest."""
    keys = ['id', 'type', 'taskType', 'prompt', 'passage', 'passageTemplate', 'context', 'choices', 'blanks',
            'tokens', 'fixedTokens', 'extraTokens', 'slots', 'wordLimit', 'recommendedWords', 'interaction',
            'presentationSchema', 'structuredContentStatus', 'stemBlocks', 'assets', 'stimulusSource']
    return {key: question[key] for key in keys if key in question}


def content_digest(question):
    raw = json.dumps(canonical_content(question), sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def exam_questions(exam):
    return [question for section in exam.get('sections', []) for module in section.get('modules', [])
            for question in module.get('questions', [])]


def manifest_issues(exam, expected=None):
    """Validate an optional per-question map; absence keeps legacy imports compatible."""
    if expected is None:
        expected = (exam.get('verificationInputs') or {}).get('structuredContentSha256ByQuestionId')
    if expected is None:
        return []
    if not isinstance(expected, dict):
        return [{'code': 'structured-content-manifest-invalid'}]
    issues = []
    structured = {q.get('id'): q for q in exam_questions(exam) if is_structured(q)}
    for question_id, question in structured.items():
        value = expected.get(question_id)
        if not isinstance(value, str) or not HASH.fullmatch(value) or value != content_digest(question):
            issues.append({'code': 'structured-content-manifest-mismatch', 'questionId': question_id})
    for question_id in set(expected) - set(structured):
        issues.append({'code': 'structured-content-manifest-stale-entry', 'questionId': str(question_id)})
    return issues
