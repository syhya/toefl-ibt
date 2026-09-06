"""Import portable, user-authored practice without the private PDF curation set.

Each import is a revisioned copy of the manifest and its referenced local files.
The registry is published last, so readers see either the old complete revision
or the new one. Existing sessions keep their original source and media URLs.
Portable packs are guided, untimed resources; they do not assert ETS validation.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import mimetypes
from pathlib import Path
import re
import threading
from urllib.parse import quote

from .engine import ExamError
from .presentation import content_digest, validate_question

_LOCK = threading.RLock()
ID = re.compile(r'^[a-z0-9][a-z0-9_-]{0,47}$')
TYPES = {
    'reading': {'choice', 'cloze'},
    'listening': {'choice'},
    'writing': {'build_sentence', 'email', 'academic_discussion', 'picture_writing'},
    'speaking': {'listen_repeat', 'interview', 'read_aloud'},
}
FIELDS = {'id', 'type', 'taskType', 'prompt', 'passage', 'passageTemplate', 'context', 'choices',
          'answer', 'blanks', 'tokens', 'slots', 'extraTokens', 'fixedTokens', 'recommendedWords',
          'wordLimit', 'interaction', 'stemBlocks', 'assets', 'audio', 'source', 'transcript'}
EXTENSIONS = {'.pdf', '.txt', '.json', '.png', '.jpg', '.jpeg', '.webp', '.mp3', '.wav', '.ogg', '.m4a', '.mp4', '.webm'}


def _json_bytes(value):
    try:
        return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode()
    except (TypeError, ValueError, RecursionError, UnicodeError) as error:
        raise ExamError('Resource pack must contain valid finite JSON values.', 422) from error


def _check_destination(root, path):
    """Reject symlinked parents as well as symlinked files before any writes."""
    if not path.is_relative_to(root):
        raise ExamError('Resource-pack destination is outside the project folder.', 422)
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise ExamError('Resource-pack destination cannot be a symbolic link.', 422)


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ExamError('Resource-pack destination cannot be a symbolic link.', 422)
    temporary = path.with_suffix(path.suffix + '.tmp')
    if temporary.is_symlink():
        raise ExamError('Resource-pack destination cannot be a symbolic link.', 422)
    temporary.write_bytes(data)
    temporary.replace(path)



def _validate_question_fields(question, kind):
    """Check input shapes before the shared renderer or grading engine sees them.

    User packs are untrusted JSON. The private curation pipeline supplies stronger
    guarantees, so its downstream validators are not a substitute for this boundary.
    """
    if 'taskType' in question and (not isinstance(question['taskType'], str) or not ID.fullmatch(question['taskType'])):
        raise ExamError('Question taskType must be a lowercase identifier.', 422)
    if 'choices' in question and kind != 'choice' or any(field in question for field in ['blanks', 'passageTemplate']) and kind != 'cloze' or any(field in question for field in ['tokens', 'slots', 'extraTokens', 'fixedTokens']) and kind != 'build_sentence':
        raise ExamError('Question fields must match their question type.', 422)
    if 'interaction' in question and (kind != 'choice' or question['interaction'] != 'select_sentence'):
        raise ExamError('Question interaction must be select_sentence when provided.', 422)
    for field in ['recommendedWords', 'wordLimit']:
        if field in question and (type(question[field]) is not int or not 1 <= question[field] <= 10000):
            raise ExamError('Writing word counts must be integers from 1 to 10000.', 422)
    if 'assets' in question and not isinstance(question['assets'], list):
        raise ExamError('Question assets must be a list.', 422)
    if 'source' in question and not isinstance(question['source'], dict):
        raise ExamError('Question source must be a local PDF reference object.', 422)
    for field in ['extraTokens', 'fixedTokens']:
        if field in question and (not isinstance(question[field], list) or not all(isinstance(token, str) for token in question[field])):
            raise ExamError('Sentence metadata must contain lists of words.', 422)
    if kind == 'build_sentence':
        slots = question.get('slots')
        if not isinstance(slots, list) or not slots or any(not isinstance(slot, dict) for slot in slots):
            raise ExamError('Sentence slots must be objects containing an id or a fixed word.', 422)
        seen, gaps = set(), 0
        for slot in slots:
            if set(slot) == {'fixed'} and isinstance(slot['fixed'], str) and slot['fixed'].strip():
                continue
            if set(slot) != {'id'} or not isinstance(slot['id'], str) or not ID.fullmatch(slot['id']) or slot['id'] in seen:
                raise ExamError('Sentence gaps require unique ids; fixed slots require nonempty fixed text.', 422)
            seen.add(slot['id']); gaps += 1
        tokens = question.get('tokens')
        if not gaps or not isinstance(tokens, list) or len(tokens) < gaps:
            raise ExamError('Sentence questions need at least one gap and enough individual word tokens.', 422)
        if 'answer' in question and (not isinstance(question['answer'], (str, list)) or isinstance(question['answer'], list) and not all(isinstance(answer, str) for answer in question['answer'])):
            raise ExamError('Sentence answers must be text or a list of accepted text answers.', 422)
    if kind == 'cloze' and isinstance(question.get('blanks'), list):
        for blank in question['blanks']:
            if not isinstance(blank, dict):
                continue  # The detailed cloze validator reports the missing object.
            if set(blank) - {'id', 'number', 'prefix', 'suffix', 'length', 'answer'}:
                raise ExamError('Cloze blank contains unsupported fields.', 422)
            if any(field in blank and not isinstance(blank[field], str) for field in ['prefix', 'suffix']):
                raise ExamError('Cloze prefixes and suffixes must be text.', 422)
            if 'number' in blank and (type(blank['number']) is not int or blank['number'] < 1):
                raise ExamError('Cloze blank numbers must be positive integers.', 422)
            if 'answer' in blank and (not isinstance(blank['answer'], str) or not re.fullmatch(r'[A-Za-z]+', blank['answer'])):
                raise ExamError('Cloze answers must contain only the missing English letters.', 422)


def import_pack(root: Path, manifest: dict, base: Path | None = None, replace=False):
    """Validate everything before publishing; ``base=None`` allows text-only UI imports."""
    with _LOCK:
        return _import_pack(root.resolve(), manifest, base.resolve() if base else None, replace)


def _import_pack(root, manifest, base, replace):
    if not isinstance(manifest, dict) or type(manifest.get('schemaVersion')) is not int or manifest['schemaVersion'] != 1:
        raise ExamError('Resource pack requires schemaVersion: 1.', 422)
    pack_id = manifest.get('id')
    if not isinstance(pack_id, str) or not ID.fullmatch(pack_id):
        raise ExamError('Pack id must use 1–48 lowercase letters, numbers, hyphens, or underscores.', 422)
    title = manifest.get('title')
    if not isinstance(title, str) or not title.strip() or len(title) > 200:
        raise ExamError('Resource pack requires a title of 1–200 characters.', 422)
    sections = manifest.get('sections')
    if not isinstance(sections, list) or not 1 <= len(sections) <= 4:
        raise ExamError('Resource pack requires 1–4 sections.', 422)
    raw = _json_bytes(manifest)
    if len(raw) > 2 * 1024 * 1024:
        raise ExamError('Resource-pack JSON must be smaller than 2 MB.', 413)
    # Hash both manifest and files so edited media gets a distinct revision URL.
    files = {}
    def collect(value):
        if isinstance(value, dict):
            if 'file' in value:
                relative = value['file']
                if not isinstance(relative, str) or not relative or '\\' in relative or '\x00' in relative or ':' in relative or Path(relative).is_absolute() or str(Path(relative)) != relative or '..' in Path(relative).parts or any(p.startswith('.') for p in Path(relative).parts) or Path(relative).parts[0] == 'pack.json':
                    raise ExamError('Resource files must use relative paths inside the pack folder.', 422)
                if base is None:
                    raise ExamError('This pack references media. Import it with npm run import:pack and its folder.', 422)
                path = base / relative
                if not path.resolve().is_relative_to(base) or any((base / Path(*Path(relative).parts[:index])).is_symlink() for index in range(1, len(Path(relative).parts) + 1)) or not path.is_file() or path.suffix.lower() not in EXTENSIONS:
                    raise ExamError('A resource file is missing, unsupported, or outside the pack folder.', 422)
                if path.stat().st_size > 100 * 1024 * 1024:
                    raise ExamError('Each resource file must be smaller than 100 MB.', 413)
                files[relative] = path.read_bytes()
                if sum(map(len, files.values())) > 200 * 1024 * 1024:
                    raise ExamError('Resource-pack files must total less than 200 MB.', 413)
            for child in value.values(): collect(child)
        elif isinstance(value, list):
            for child in value: collect(child)
    collect(sections)
    fingerprint = hashlib.sha256(raw + b''.join(name.encode() + hashlib.sha256(data).digest() for name, data in sorted(files.items()))).hexdigest()
    revision = fingerprint[:16]
    relative_root = f'data/user-packs/{pack_id}/{revision}'
    destination = root / relative_root
    if not destination.resolve().is_relative_to(root / 'data'):
        raise ExamError('Resource-pack destination is outside the local data folder.', 422)
    exam_id = 'user-' + pack_id
    registry = root / 'generated/pack-catalogs' / f'{pack_id}.json'
    # Validate every destination before copying even one file. This also prevents
    # a symlinked generated/ directory from redirecting writes outside the project.
    targets = [destination / 'pack.json', *(destination / name for name in files),
               root / 'generated/exams' / f'{exam_id}.json', registry, root / 'generated/catalog.json']
    for target in targets:
        _check_destination(root, target)
        _check_destination(root, target.with_suffix(target.suffix + '.tmp'))
    if registry.is_file():
        prior = json.loads(registry.read_text())
        if prior.get('packDigest') == fingerprint:
            return {'id': exam_id, 'packId': pack_id, 'unchanged': True, 'questions': prior['exams'][0]['screenCount']}
        if not replace:
            raise ExamError('A different pack with this id already exists. Use the CLI --replace option to update it.', 409)
    elif (root / 'generated/exams' / f'{exam_id}.json').exists():
        raise ExamError('This pack id conflicts with an existing test.', 409)
    materials = []
    def material(relative, data):
        mid = 'pack-' + hashlib.sha256((pack_id + revision + relative).encode()).hexdigest()[:20]
        mime = mimetypes.guess_type(relative)[0] or ''
        kind = 'pdf' if Path(relative).suffix.lower() == '.pdf' else 'audio' if mime.startswith('audio/') else 'video' if mime.startswith('video/') else 'image' if mime.startswith('image/') else 'document'
        url = '/materials/' + quote(f'user-packs/{pack_id}/{revision}/{relative}', safe='/')
        row = {'id': mid, 'path': f'user-packs/{pack_id}/{revision}/{relative}', 'url': url, 'name': relative,
               'category': 'user', 'kind': kind, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
               'examIds': [exam_id], 'supplemental': True}
        materials.append(row)
        return row
    # Pack answers remain in this original manifest and are protected by the same
    # original-material lock used for PDFs during active strict sessions.
    source_manifest = material('pack.json', raw)
    file_materials = {name: material(name, data) for name, data in files.items()}
    seen_sections, seen_questions, normalized_sections = set(), set(), []
    for section in sections:
        if not isinstance(section, dict) or not isinstance(section.get('id'), str) or section['id'] not in TYPES or section['id'] in seen_sections:
            raise ExamError('Sections must have unique reading, listening, writing, or speaking ids.', 422)
        sid = section['id']; seen_sections.add(sid)
        questions = section.get('questions')
        if not isinstance(questions, list) or not 1 <= len(questions) <= 200:
            raise ExamError('Each resource-pack section requires 1–200 questions.', 422)
        normalized = []
        for number, source in enumerate(questions, 1):
            if not isinstance(source, dict) or set(source) - FIELDS:
                raise ExamError('Resource question contains unknown fields. Check the import guide.', 422)
            qid, kind = source.get('id'), source.get('type')
            if not isinstance(qid, str) or not ID.fullmatch(qid) or qid in seen_questions or not isinstance(kind, str) or kind not in TYPES[sid]:
                raise ExamError('Question ids must be unique and question types must match their section.', 422)
            seen_questions.add(qid)
            _validate_question_fields(source, kind)
            q = deepcopy(source)
            q.update(id=f'{exam_id}-{qid}', number=number, taskType=source.get('taskType', kind),
                     presentationSchema='structured-v1', structuredContentStatus='source-verified',
                     sourcePromptAvailable=True, auditStatus='user-authored')
            if not isinstance(q.get('prompt'), str) or not q['prompt'].strip():
                raise ExamError('Every question requires a nonempty prompt.', 422)
            for name in ['passage', 'passageTemplate', 'context', 'transcript']:
                if name in q and not isinstance(q[name], str): raise ExamError('Question text fields must be strings.', 422)
            blocks = q.get('stemBlocks')
            if blocks is None:
                blocks = []
                if q.get('passage'): blocks.append({'type': 'paragraph', 'text': q['passage']})
                blocks.append({'type': 'question' if kind in ['choice', 'cloze'] else 'instruction', 'text': q['prompt']})
            q['stemBlocks'] = blocks
            q['assets'] = []
            for spec in source.get('assets', []):
                if not isinstance(spec, dict) or set(spec) != {'file', 'alt'} or not isinstance(spec.get('file'), str) or spec['file'] not in file_materials or not isinstance(spec.get('alt'), str):
                    raise ExamError('Each image needs a local file and descriptive alt text.', 422)
                try:
                    from PIL import Image
                except ImportError as error:
                    raise ExamError('Image imports require Pillow. Install requirements-import.txt first.', 422) from error
                from io import BytesIO
                try:
                    with Image.open(BytesIO(files[spec['file']])) as im:
                        im.verify()
                    with Image.open(BytesIO(files[spec['file']])) as im: width, height = im.size
                except Exception as error:
                    raise ExamError('A referenced image cannot be decoded.', 422) from error
                q['assets'].append({'url': file_materials[spec['file']]['url'], 'role': 'essentialVisual',
                                    'highResolution': True, 'width': width, 'height': height, 'alt': spec['alt']})
                # Images without a custom structured layout follow the source text.
                if source.get('stemBlocks') is None:
                    blocks.append({'type': 'essential_visual', 'assetIndex': len(q['assets'])-1, 'alt': spec['alt']})
            if 'audio' in source:
                spec = source['audio']
                if not isinstance(spec, dict) or set(spec) != {'file'} or not isinstance(spec.get('file'), str) or spec['file'] not in file_materials:
                    raise ExamError('Audio requires a local file.', 422)
                from .media import probe_duration
                duration = probe_duration(base / spec['file'])
                if not duration: raise ExamError('Audio duration could not be verified. Use a supported audio file.', 422)
                row = file_materials[spec['file']]
                if row['kind'] not in ['audio', 'video']: raise ExamError('Audio must reference an audio or video file.', 422)
                q['audio'] = {'url': row['url'], 'materialId': row['id'], 'durationSeconds': duration,
                              'mediaType': row['kind'], 'groupId': q['id'], 'kind': 'stimulus'}
            if sid in ['listening', 'speaking'] and 'audio' not in q:
                raise ExamError('Listening and speaking questions require an original audio or video file.', 422)
            source_file = source.get('source', {})
            if source_file:
                if not isinstance(source_file, dict) or set(source_file) != {'file', 'page'} or not isinstance(source_file.get('file'), str) or source_file['file'] not in file_materials or type(source_file.get('page')) is not int or source_file['page'] < 1:
                    raise ExamError('Question source requires a local PDF file and a positive page.', 422)
                row = file_materials[source_file['file']]
                if row['kind'] != 'pdf': raise ExamError('Question source must be a PDF.', 422)
                q['source'] = {'materialId': row['id'], 'url': row['url'] + f"#page={source_file['page']}", 'page': source_file['page']}
            else:
                q['source'] = {'materialId': source_manifest['id'], 'url': source_manifest['url'], 'page': 1}
            q['source'].update(section=sid, originalNumber=number)
            if kind == 'choice':
                choices = q.get('choices')
                if not isinstance(choices, list) or not 2 <= len(choices) <= 8 or any(not isinstance(c, dict) or set(c) != {'id','text'} or not isinstance(c['id'],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,47}', c['id']) or not isinstance(c['text'],str) or not c['text'].strip() for c in choices):
                    raise ExamError('Choice questions require 2–8 choices with id and text.', 422)
                ids = [c['id'] for c in choices]
                if len(set(ids)) != len(ids) or ('answer' in q and q['answer'] not in ids): raise ExamError('Choice answer must match a unique choice id.', 422)
            if kind == 'cloze':
                blanks = q.get('blanks')
                if not isinstance(blanks,list) or not blanks or not q.get('passageTemplate'): raise ExamError('Cloze questions require blanks and a passageTemplate.',422)
                ids=[]
                for blank in blanks:
                    if not isinstance(blank,dict) or not isinstance(blank.get('id'),str) or not ID.fullmatch(blank['id']) or type(blank.get('length')) is not int or not 1<=blank['length']<=30:
                        raise ExamError('Every cloze blank requires an id and length from 1 to 30.',422)
                    ids.append(blank['id'])
                    if 'answer' in blank and (not isinstance(blank['answer'],str) or len(blank['answer'])!=blank['length']): raise ExamError('Cloze answer length must match its missing-letter count.',422)
                if len(ids)!=len(set(ids)) or sorted(re.findall(r'\{\{([^{}]+)\}\}',q['passageTemplate']))!=sorted(ids):raise ExamError('Cloze placeholders must match each blank exactly once.',422)
            if kind == 'build_sentence':
                if not isinstance(q.get('tokens'),list) or not q['tokens'] or not all(isinstance(t,str) and t.strip() for t in q['tokens']) or not isinstance(q.get('slots'),list) or not q['slots']:
                    raise ExamError('Sentence questions require nonempty tokens and slots.',422)
            try:
                issues = validate_question(q, strict=True)
            except (TypeError, KeyError, AttributeError) as error:
                raise ExamError('Invalid structured question field types. Check the import guide.', 422) from error
            if issues: raise ExamError('Invalid structured question: ' + ', '.join(issues), 422)
            q['contentId'] = 'qcontent-' + content_digest(q)[:20]
            normalized.append(q)
        normalized_sections.append({'id': sid, 'title': sid.title(), 'modules': [{'id': f'{sid}-practice', 'title': sid.title(), 'questions': normalized}]})
    normalized_sections.sort(key=lambda s:list(TYPES).index(s['id']))
    all_questions = [q for s in normalized_sections for m in s['modules'] for q in m['questions']]
    count = sum(len(q['blanks']) if q['type']=='cloze' else 1 for q in all_questions)
    exam = {'schemaVersion':1, 'id':exam_id, 'title':title.strip(), 'family':'user', 'supplemental':True,
            'timingPolicy':'untimed', 'strictEligible':False, 'questionCount':count, 'screenCount':len(all_questions),
            'interactiveQuestionCount':count, 'sourceMaterialIds':[m['id'] for m in materials],
            'warnings':['User-authored resource pack · Untimed guided practice.'], 'sections':normalized_sections,
            'verificationInputs':{'curationSha256ByPath':{relative_root+'/pack.json':hashlib.sha256(raw).hexdigest()},
                'assetSha256ByUrl':{}, 'structuredContentSha256ByQuestionId':{q['id']:content_digest(q) for q in all_questions}}}
    # Copy immutable revision files before publishing the registry. No existing
    # source material or answer database is modified by an import.
    destination.mkdir(parents=True,exist_ok=True)
    _write(destination/'pack.json',raw)
    for name,data in files.items(): _write(destination/name,data)
    _write(root/'generated/exams'/f'{exam_id}.json',_json_bytes(exam))
    summary = {k:v for k,v in exam.items() if k!='sections'}
    registry_data={'schemaVersion':1,'packDigest':fingerprint,'generatedAt':datetime.now(timezone.utc).isoformat(),
                   'materials':materials,'exams':[summary]}
    if not (root/'generated/catalog.json').exists():
        _write(root/'generated/catalog.json',_json_bytes({'schemaVersion':1,'materials':[],'exams':[],'stats':{}}))
    _write(registry,_json_bytes(registry_data))
    return {'id':exam_id,'packId':pack_id,'unchanged':False,'questions':len(all_questions)}
