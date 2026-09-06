"""Local vocabulary routes, registered with the application's existing guards."""
import re
import unicodedata
import uuid

from fastapi import Request

from . import engine


LIMITS = {'word': 120, 'meaning': 2000, 'context': 4000, 'sourceLabel': 240,
          'sourceQuestionId': 128, 'sourceSessionId': 128}
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$')
CREATE_FIELDS = set(LIMITS)
UPDATE_FIELDS = {'word', 'meaning', 'context', 'status'}


def normalized_text(value, field, limit, *, required=False, single_line=False):
    if not isinstance(value, str):
        raise engine.ExamError(f'{field} must be text.', 422)
    # Validate both representations so compatibility normalization cannot hide
    # an oversized payload, and do not persist non-UTF-8 surrogate characters.
    if len(value) > limit:
        raise engine.ExamError(f'{field} must be at most {limit} characters.', 422)
    value = unicodedata.normalize('NFKC', value).replace('\r\n', '\n').replace('\r', '\n')
    if any(unicodedata.category(char) in {'Cc', 'Cs'} and char not in '\n\t' for char in value):
        raise engine.ExamError(f'{field} contains unsupported control characters.', 422)
    value = ' '.join(value.split()) if single_line else value.strip()
    if len(value) > limit or (required and not value):
        raise engine.ExamError(f'{field} must contain 1–{limit} characters.' if required
                               else f'{field} must be at most {limit} characters.', 422)
    return value


def word_text(value):
    word = normalized_text(value, 'word', LIMITS['word'], required=True, single_line=True)
    word = unicodedata.normalize('NFKC', word.casefold())
    if len(word) > LIMITS['word']:
        raise engine.ExamError('word must be at most 120 characters.', 422)
    return word


def identifier(value, field='id'):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise engine.ExamError(f'Invalid {field}.', 422)
    return value


def search_text(entry):
    text = '\n'.join(entry[key] for key in ['word', 'meaning', 'context', 'sourceLabel'])
    return unicodedata.normalize('NFKC', text.casefold())


def public_entry(row):
    entry = {'id': row['id'], 'word': row['word'], 'meaning': row['meaning'], 'context': row['context'],
             'sourceLabel': row['source_label'], 'status': row['status'],
             'createdAt': row['created_at'], 'updatedAt': row['updated_at']}
    for public, column in [('sourceQuestionId', 'source_question_id'), ('sourceSessionId', 'source_session_id')]:
        if row[column] is not None:
            entry[public] = row[column]
    return entry


def validate_fields(body, allowed):
    if set(body) - allowed:
        raise engine.ExamError('Unsupported vocabulary fields.', 422)


def parse_page(value, name, maximum):
    if not re.fullmatch(r'[0-9]{1,7}', value):
        raise engine.ExamError(f'{name} must be an integer from 1 to {maximum}.', 422)
    number = int(value)
    if not 1 <= number <= maximum:
        raise engine.ExamError(f'{name} must be an integer from 1 to {maximum}.', 422)
    return number


def install_vocabulary_routes(app, store, clock, read_json, reject_during_strict):
    """Install before the frontend catch-all; inherit host/origin middleware.

    The strict guard and each database operation share one transaction so a
    concurrent request cannot open strict practice between a check and a write.
    """
    @app.get('/api/vocabulary')
    def list_vocabulary(q: str = '', status: str = 'all', page: str = '1', pageSize: str = '24'):
        query = normalized_text(q, 'q', 200).casefold()
        query = unicodedata.normalize('NFKC', query)
        current_page = parse_page(page, 'page', 1_000_000)
        page_size = parse_page(pageSize, 'pageSize', 100)
        if status not in ['all', 'learning', 'mastered']:
            raise engine.ExamError('Choose a valid vocabulary status.', 422)
        with store.transaction() as db:
            reject_during_strict(db)
            counts = {row['status']: row['count'] for row in db.execute(
                'SELECT status, COUNT(*) AS count FROM vocabulary WHERE instr(search_text, ?) > 0 GROUP BY status',
                (query,))}
            summary = {'learning': counts.get('learning', 0), 'mastered': counts.get('mastered', 0)}
            total = sum(summary.values()) if status == 'all' else summary[status]
            rows = db.execute(
                'SELECT * FROM vocabulary WHERE instr(search_text, ?) > 0 AND (? = ? OR status = ?) '
                'ORDER BY updated_at DESC, id LIMIT ? OFFSET ?',
                (query, status, 'all', status, page_size, (current_page - 1) * page_size)).fetchall()
            return {'items': [public_entry(row) for row in rows], 'total': total,
                    'page': current_page, 'pageSize': page_size, 'summary': summary}

    @app.post('/api/vocabulary')
    async def create_vocabulary(request: Request):
        body = await read_json(request)
        with store.transaction() as db:
            reject_during_strict(db)
            validate_fields(body, CREATE_FIELDS)
            word = word_text(body.get('word'))
            entry = {'word': word}
            for field in ['meaning', 'context', 'sourceLabel']:
                entry[field] = normalized_text(body.get(field, ''), field, LIMITS[field])
            for field in ['sourceQuestionId', 'sourceSessionId']:
                value = body.get(field)
                entry[field] = identifier(value, field) if value is not None else None
            existing = db.execute('SELECT * FROM vocabulary WHERE word_key=?', (word,)).fetchone()
            if existing is not None:
                return {'entry': public_entry(existing), 'created': False}
            entry_id, now = 'vocab-' + uuid.uuid4().hex, clock()
            db.execute(
                'INSERT INTO vocabulary(id,word,word_key,meaning,context,source_label,source_question_id,'
                'source_session_id,status,search_text,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                (entry_id, word, word, entry['meaning'], entry['context'], entry['sourceLabel'],
                 entry['sourceQuestionId'], entry['sourceSessionId'], 'learning', search_text(entry), now, now))
            row = db.execute('SELECT * FROM vocabulary WHERE id=?', (entry_id,)).fetchone()
            return {'entry': public_entry(row), 'created': True}

    @app.patch('/api/vocabulary/{entry_id}')
    async def update_vocabulary(entry_id: str, request: Request):
        body = await read_json(request)
        with store.transaction() as db:
            reject_during_strict(db)
            identifier(entry_id)
            validate_fields(body, UPDATE_FIELDS)
            if not body:
                raise engine.ExamError('Provide at least one vocabulary field to update.', 422)
            row = db.execute('SELECT * FROM vocabulary WHERE id=?', (entry_id,)).fetchone()
            if row is None:
                raise engine.ExamError('Vocabulary entry not found.', 404)
            entry = public_entry(row)
            if 'word' in body:
                entry['word'] = word_text(body['word'])
            for field in ['meaning', 'context']:
                if field in body:
                    entry[field] = normalized_text(body[field], field, LIMITS[field])
            if 'status' in body:
                if body['status'] not in ['learning', 'mastered']:
                    raise engine.ExamError('Choose a valid vocabulary status.', 422)
                entry['status'] = body['status']
            duplicate = db.execute('SELECT id FROM vocabulary WHERE word_key=? AND id<>?',
                                   (entry['word'], entry_id)).fetchone()
            if duplicate is not None:
                raise engine.ExamError('That word is already in your vocabulary.', 409)
            db.execute('UPDATE vocabulary SET word=?, word_key=?, meaning=?, context=?, status=?, '
                       'search_text=?, updated_at=? WHERE id=?',
                       (entry['word'], entry['word'], entry['meaning'], entry['context'], entry['status'],
                        search_text(entry), clock(), entry_id))
            saved = db.execute('SELECT * FROM vocabulary WHERE id=?', (entry_id,)).fetchone()
            return {'entry': public_entry(saved)}

    @app.delete('/api/vocabulary/{entry_id}')
    def delete_vocabulary(entry_id: str):
        with store.transaction() as db:
            reject_during_strict(db)
            identifier(entry_id)
            result = db.execute('DELETE FROM vocabulary WHERE id=?', (entry_id,))
            if result.rowcount == 0:
                raise engine.ExamError('Vocabulary entry not found.', 404)
            return {'ok': True}
