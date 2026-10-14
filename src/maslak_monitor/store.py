"""SQLite persistence; claims commit before any external SMS request."""
from datetime import date
import json
import sqlite3
from .site import Slot


class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path,timeout=15)
        self.db.execute('PRAGMA busy_timeout=15000')
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS openings (week TEXT PRIMARY KEY, slots TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS recipients (
            week TEXT NOT NULL, recipient TEXT NOT NULL, status TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0, provider_id TEXT,
            PRIMARY KEY(week,recipient));
        ''')

    def __enter__(self): return self

    def __exit__(self,*args): self.db.close()

    def record_opening(self, week_start: date, slots: list[Slot]):
        if not slots:
            raise ValueError('Cannot record an empty opening')
        payload=json.dumps([{'day':s.day.isoformat(),'label':s.label} for s in slots])
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO openings VALUES (?,?)',(week_start.isoformat(),payload))

    def opening(self, week_start: date) -> list[Slot] | None:
        row=self.db.execute('SELECT slots FROM openings WHERE week=?',(week_start.isoformat(),)).fetchone()
        return [Slot(date.fromisoformat(s['day']),s['label']) for s in json.loads(row[0])] if row else None

    def claim_recipient(self, week_start: date, recipient: str) -> bool:
        key=(week_start.isoformat(),recipient)
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO recipients(week,recipient,status) VALUES (?,?,\'pending\')',key)
            changed=self.db.execute('''UPDATE recipients SET status='sending',attempts=attempts+1
                WHERE week=? AND recipient=? AND status IN ('pending','rejected') AND attempts<3''',key)
        return changed.rowcount == 1

    def finish_recipient(self, week_start, recipient, status, provider_id):
        if status not in ('accepted','rejected','unknown'):
            raise ValueError('Invalid send result')
        with self.db:
            changed=self.db.execute('''UPDATE recipients SET status=?,provider_id=?
                WHERE week=? AND recipient=? AND status='sending' ''',
                (status,provider_id,week_start.isoformat(),recipient))
            if changed.rowcount != 1:
                raise ValueError('No active claim for recipient')

    def recipient_state(self, week_start, recipient) -> str:
        row=self.db.execute('SELECT status FROM recipients WHERE week=? AND recipient=?',
                            (week_start.isoformat(),recipient)).fetchone()
        return row[0] if row else 'pending'

    def recover_interrupted(self):
        # Caller must hold the process lock; another worker's live claim must never be reset.
        with self.db:
            self.db.execute("UPDATE recipients SET status='unknown' WHERE status='sending'")
