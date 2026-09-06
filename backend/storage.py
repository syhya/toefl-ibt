"""SQLite persistence for sessions, vocabulary, ratings and audio chunks.

Session JSON freezes the selected plan and deadline; append-only recording rows
refer to separately stored chunk files. Transactions serialize competing browser
requests so retries cannot submit or advance the same question twice.
"""
from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3


class Storage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.directory = self.root / 'storage'
        self.directory.mkdir(mode=0o700, exist_ok=True)
        if self.directory.is_symlink() or not self.directory.resolve().is_relative_to(self.root):
            raise ValueError('Storage must be a private project directory.')
        self.path = self.directory / 'practice.sqlite3'
        if self.path.is_symlink():
            raise ValueError('The database must not be a symbolic link.')
        with self.connect() as db:
            db.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, body TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS requests (
                    session_id TEXT NOT NULL, request_id TEXT NOT NULL, payload_hash TEXT NOT NULL,
                    PRIMARY KEY(session_id, request_id)
                );
                CREATE TABLE IF NOT EXISTS recordings (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL, question_id TEXT NOT NULL,
                    take_id TEXT NOT NULL, chunk_index INTEGER NOT NULL, relative_path TEXT NOT NULL,
                    sha256 TEXT NOT NULL, mime_type TEXT NOT NULL, size INTEGER NOT NULL, created_at INTEGER NOT NULL,
                    UNIQUE(session_id, take_id, chunk_index)
                );
                CREATE TABLE IF NOT EXISTS recording_takes (
                    session_id TEXT NOT NULL, take_id TEXT NOT NULL, question_id TEXT NOT NULL,
                    expected_count INTEGER NOT NULL, ended_reason TEXT NOT NULL, mime_type TEXT,
                    finalized_at INTEGER NOT NULL,
                    PRIMARY KEY(session_id, take_id)
                );
                CREATE TABLE IF NOT EXISTS ratings (
                    session_id TEXT NOT NULL, question_id TEXT NOT NULL, value INTEGER NOT NULL,
                    notes TEXT NOT NULL, updated_at INTEGER NOT NULL,
                    PRIMARY KEY(session_id, question_id)
                );
                CREATE TABLE IF NOT EXISTS vocabulary (
                    id TEXT PRIMARY KEY, word TEXT NOT NULL, word_key TEXT NOT NULL UNIQUE,
                    meaning TEXT NOT NULL, context TEXT NOT NULL, source_label TEXT NOT NULL,
                    source_question_id TEXT, source_session_id TEXT,
                    status TEXT NOT NULL CHECK(status IN ('learning', 'mastered')),
                    search_text TEXT NOT NULL, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS vocabulary_updated_at ON vocabulary(updated_at DESC, id);
            ''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA busy_timeout=15000')
        return db

    @contextmanager
    def transaction(self):
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def get(db, session_id):
        row = db.execute('SELECT body FROM sessions WHERE id=?', (session_id,)).fetchone()
        return json.loads(row['body']) if row else None

    @staticmethod
    def save(db, session):
        db.execute('INSERT INTO sessions(id,body,created_at,updated_at) VALUES(?,?,?,?) '
                   'ON CONFLICT(id) DO UPDATE SET body=excluded.body, updated_at=excluded.updated_at',
                   (session['id'], json.dumps(session, ensure_ascii=False), session['startedAt'], session['updatedAt']))

    @staticmethod
    def all(db):
        return [json.loads(row['body']) for row in db.execute('SELECT body FROM sessions ORDER BY updated_at DESC')]
