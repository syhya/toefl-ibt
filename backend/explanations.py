"""Bounded, deterministic review assistance. Never creates questions or answer keys.

Source explanations are distinguished from mechanical local assistance. Keyword
location is explicitly not a semantic proof, and unresolved answers stay unknown.
"""
from .engine import grade, normalize
from .reviewed_explanations import reviewed_explanation
import re

STOP_WORDS = set('a an the to of in on at for from by with as and or but if is are was were be been being it its this that these those he she they them their his her we our you your i me my do does did have has had can could will would should not which what who where when why how than then also some any all'.split())
AUXILIARIES = set('do does did am is are was were have has had can could may might will would shall should must'.split())
WH_WORDS = set('what who whom whose which when where why how'.split())


def source_info(q, explanation=False):
    source = (q.get('explanationSource') if explanation else None) or q.get('source') or {}
    return {key: source[key] for key in ['page', 'materialId', 'label', 'origin', 'official'] if key in source}


def unavailable(q, text, warnings=None):
    result = {'origin': 'unavailable', 'label': '解析依据不足', 'text': text, 'source': source_info(q)}
    if warnings:
        result['warnings'] = warnings
    return result


def unresolved(value):
    return value.get('auditStatus') == 'answer-conflict' or (value.get('answerConflict') or {}).get('status') == 'needs-review'


def _original_explanation(q):
    if q.get('explanationOrigin') in ['local_assistance', 'generated', 'ai']:
        return None
    value = q.get('explanation')
    if isinstance(value, dict):
        if value.get('origin') and value['origin'] not in ['source', 'official', 'material', 'provided']:
            return None
        value = value.get('text')
    if isinstance(value, str) and value.strip():
        return value.strip()
    values = q.get('explanations')
    if isinstance(values, list):
        texts = [item if isinstance(item, str) else item.get('text', '') if isinstance(item, dict) else '' for item in values]
        text = '\n'.join(item.strip() for item in texts if item.strip())
        return text or None
    return None


def _blank_parts(blank):
    prefix, suffix = str(blank.get('prefix') or ''), str(blank.get('suffix') or '')
    full, missing = blank.get('fullWord'), blank.get('missingLetters')
    answer = blank.get('answer')
    if not full and answer:
        answer = str(answer)
        if normalize(answer).startswith(normalize(prefix)) and (not suffix or normalize(answer).endswith(normalize(suffix))):
            full = answer
        else:
            missing = missing or answer
    if not full and missing:
        full = prefix + str(missing) + suffix
    if full and missing is None:
        full = str(full)
        if not normalize(full).startswith(normalize(prefix)) or (suffix and not normalize(full).endswith(normalize(suffix))):
            return None
        missing = full[len(prefix):len(full) - len(suffix) if suffix else None]
    if not full or missing is None:
        return None
    if normalize(prefix + str(missing) + suffix) != normalize(full):
        return None
    return prefix, str(missing), suffix, str(full)


def _cloze(q):
    evidence, warnings = [], []
    for index, blank in enumerate(q.get('blanks', []), start=1):
        number = blank.get('number', index)
        if unresolved(blank):
            warnings.append(f'第 {number} 空的来源答案仍有冲突，不给出正确结论，也不计入自动评分。')
            continue
        parts = _blank_parts(blank)
        if not parts:
            warnings.append(f'第 {number} 空缺少可一致还原的已核验答案。')
            continue
        prefix, missing, suffix, full = parts
        expected_length = blank.get('missingLength', blank.get('length'))
        length_note = f'缺失片段 {len(missing)} 个字符'
        if expected_length and expected_length != len(missing):
            warnings.append(f'第 {number} 空记录的长度与参考片段不一致，请对照源题核验。')
            continue
        pieces = [f'已给「{prefix}」' if prefix else '无前缀', f'补入「{missing}」']
        if suffix:
            pieces.append(f'已给后缀「{suffix}」')
        evidence.append(f'第 {number} 空：' + ' + '.join(pieces) + f' → {full}（{length_note}）。')
    if not evidence:
        return unavailable(q, '没有可安全还原的已核验填词答案；请查看原题及冲突记录，不据此生成正确结论。', warnings)
    passage = q.get('passage')
    if isinstance(passage, str) and passage.strip():
        evidence.append('原题上下文片段（未改写）：' + passage.strip()[:500])
    return {'origin': 'local_assistance', 'label': '本地辅助 · 补字还原',
            'text': '以下是已给字母与资料参考答案的机械核对，不是原资料提供的词义或语法解析。请结合原题上下文检查词性、时态及搭配。',
            'evidence': evidence, 'warnings': warnings, 'source': source_info(q)}


def _fixed(slot):
    if isinstance(slot, str):
        return slot or None
    if isinstance(slot, dict):
        return slot.get('fixed') or slot.get('text') or None
    return None


def _sentence_normalize(text):
    text = re.sub(r'\s+([?.!,;:])', r'\1', normalize(text))
    return re.sub(r'[.!?]+$', '', text).rstrip()


def _token_order(q, expected, max_nodes=6000):
    tokens, slots = q.get('tokens') or [], q.get('slots') or []
    if not slots or not tokens or len(tokens) > 24:
        return None
    target, nodes = _sentence_normalize(expected), 0

    def search(position, used, chosen, parts):
        nonlocal nodes
        nodes += 1
        if nodes > max_nodes:
            return None
        prefix = _sentence_normalize(' '.join(parts))
        if prefix and not target.startswith(prefix):
            return None
        if position == len(slots):
            return chosen if prefix == target else None
        fixed = _fixed(slots[position])
        if fixed is not None:
            return search(position + 1, used, chosen, [*parts, str(fixed)])
        for index, token in enumerate(tokens):
            if index in used:
                continue
            result = search(position + 1, used | {index}, [*chosen, index], [*parts, str(token)])
            if result is not None:
                return result
        return None
    return search(0, set(), [], [])


def _sentence(q):
    raw_answer = q.get('answer')
    expected = raw_answer[0] if isinstance(raw_answer, list) and raw_answer else raw_answer
    if not isinstance(expected, str) or not expected.strip():
        expected = next((value for value in q.get('acceptedAnswers', []) if isinstance(value, str) and value.strip()), None)
    if not isinstance(expected, str) or not expected.strip():
        return unavailable(q, '此题没有可核验的参考句，不推断或另造标准答案。')
    evidence = ['资料参考句：' + expected]
    for variant in q.get('acceptedAnswers', []):
        if isinstance(variant, str) and _sentence_normalize(variant) != _sentence_normalize(expected):
            evidence.append('另一个有来源支持的参考变体：' + variant)
    fixed = [_fixed(slot) for slot in q.get('slots', []) if _fixed(slot) is not None]
    if fixed:
        evidence.append('原题固定词块：' + ' / '.join(str(part) for part in fixed))
    order = _token_order(q, expected)
    warnings = []
    if order is not None:
        tokens = q.get('tokens') or []
        evidence.append('一种与参考句一致的空格词序：' + ' → '.join(f'{tokens[index]}〔词块 {index + 1}〕' for index in order))
        unused = [f'{token}〔词块 {index + 1}〕' for index, token in enumerate(tokens) if index not in order]
        if unused:
            evidence.append('本排列未使用的词块：' + ' / '.join(unused))
    elif q.get('slots'):
        warnings.append('未能在有界搜索内用给定词块一致还原参考句；请查看原键与题面校核证据，不凭此推断词序。')
    words = normalize(expected).split()
    if len(words) >= 3 and words[0] in WH_WORDS and any(word in AUXILIARIES for word in words[1:4]):
        evidence.append('词序观察：参考句以疑问词开头，随后出现助动词；注意疑问词短语、助动词与主语的位置。')
    elif len(words) >= 3 and words[0] in AUXILIARIES and words[1] in {'i', 'you', 'he', 'she', 'it', 'we', 'they'}:
        evidence.append('词序观察：参考句把助动词或情态动词放在代词主语之前，符合这类一般疑问句的常见结构。')
    return {'origin': 'local_assistance', 'label': '本地辅助 · 词块与参考语序',
            'text': '只对照原题固定词、独立词块索引与已有参考句；相同拼写的不同词块仍是独立项目。句末句号/问号差异不单独判错。这里不是 ETS 官方语法解析。',
            'evidence': evidence, 'warnings': warnings, 'source': source_info(q)}


def _words(text):
    return {word for word in re.findall(r"[a-z0-9]+(?:'[a-z]+)?", normalize(text)) if word not in STOP_WORDS and (len(word) >= 3 or word.isdigit())}


def _choice(q):
    answer = q.get('answer')
    if isinstance(answer, list):
        answer = answer[0] if answer else None
    if answer is None and q.get('acceptedAnswers'):
        answer = q['acceptedAnswers'][0]
    selected = next((choice for choice in q.get('choices', []) if normalize(choice.get('id')) == normalize(answer)), None)
    if not selected:
        return unavailable(q, '参考键没有对应到当前选项，不生成选项成立的解释；请先核验来源。')
    label = str(selected.get('id'))
    option = str(selected.get('text') or '')
    source_text = q.get('transcript') or q.get('passage') or ''
    if not isinstance(source_text, str):
        source_text = ''
    option_words = _words(option)
    candidates = []
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', source_text):
        sentence = sentence.strip()
        if not sentence:
            continue
        matching = option_words & _words(sentence)
        full_match = len(normalize(option)) >= 12 and normalize(option) in normalize(sentence)
        if full_match or (len(matching) >= 2 and len(matching) / max(1, len(option_words)) >= .6):
            candidates.append((len(matching) + (10 if full_match else 0), sentence))
    candidates.sort(key=lambda item: item[0], reverse=True)
    source = source_info(q)
    warning = '原文关键词相同不等于完整逻辑证明；本工具不推断其他选项为何错误。'
    if q.get('transcript'):
        warning += ' 转写内容须与原音核对，不能把识别结果当作官方解析。'
    if not candidates:
        return {'origin': 'local_assistance', 'label': '本地辅助 · 参考键核对',
                'text': f'资料参考键为 {label}。原资料未提供可用解析，且本地关键词方法没有定位到可靠依据；请结合完整原文或原音自行核对，不据此补写理由。',
                'evidence': [], 'warnings': [warning], 'source': source}
    evidence = [item[1][:1000] for item in candidates[:2]]
    return {'origin': 'local_assistance', 'label': '本地辅助 · 已导入原文定位',
            'text': f'资料参考键为 {label}。下面逐字摘取本题已导入原文/转写中与该选项关键词相符的片段，作为复盘定位线索；不把机械匹配当作官方原因说明。',
            'evidence': evidence, 'warnings': [warning], 'source': source}


def explain(q):
    reviewed = reviewed_explanation(q)
    if reviewed is not None:
        return reviewed
    if unresolved(q):
        return unavailable(q, '此题的原键与题面尚有未解决冲突，暂不自动判定正确答案，也不生成正确性结论。')
    original = _original_explanation(q)
    if original:
        warnings = []
        if q.get('sourceReferenceAnswer') is not None and q.get('sourceReferenceAnswer') != q.get('answer'):
            warnings.append('原键与当前校核答案不同；原资料解析可能对应旧键，请同时查看答案冲突与校核证据。')
        if any(unresolved(blank) for blank in q.get('blanks', [])):
            warnings.append('部分空的答案仍有冲突；原资料解释仅供对照，不据此给冲突空判分。')
        conflict = q.get('explanationConflict') or {}
        if conflict:
            warnings.append('这段附带解析与原题或校核答案存在差异；评分不因附带解析而改写答案。')
            if isinstance(conflict.get('resolutionEvidence'), str):
                warnings.append('校核说明：' + conflict['resolutionEvidence'])
        source = source_info(q, explanation=True)
        label = '资料附带解析（非 ETS 官方）' if source.get('official') is False else '原资料解析'
        if conflict:
            label += ' · 存在校核差异'
        return {'origin': 'source', 'label': label, 'text': original, 'source': source, 'warnings': warnings}
    if grade(q, None) is None:
        return unavailable(q, '没有可自动核验的标准答案，或本题需要人工量表评分。保留原题、作文/录音及来源供复盘，不生成未经校准的自动结论。')
    kind = q.get('type')
    if kind in ['cloze', 'complete_words']:
        return _cloze(q)
    if kind == 'build_sentence':
        return _sentence(q)
    if kind == 'choice':
        return _choice(q)
    return unavailable(q, '已有参考键，但本地规则尚不能可靠说明本题理由。请对照原资料，不据此编造解释。')
