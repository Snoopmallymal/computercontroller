# database.py

# database.py

import sqlite3
from pathlib import Path
import json
import re
import threading

class Database:
    def __init__(self, db_path="mydata.db"):
        self.db_path = Path(db_path)
        self._lock = threading.Lock()

        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            self._create_tables(cursor)
            conn.commit()

    def _get_db_connection(self):
        # Use a 30s timeout to reduce "database is locked" race conditions
        conn = sqlite3.connect(self.db_path, timeout=30, detect_types=sqlite3.PARSE_DECLTYPES)
        # Enable WAL for better concurrent reads/writes across processes
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.row_factory = sqlite3.Row
        return conn

    def _create_tables(self, cursor):
        # table 1: timer
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timer (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                minutes_remaining INTEGER NOT NULL
            )
        """)
        cursor.execute("INSERT OR IGNORE INTO timer (id, minutes_remaining) VALUES (1, 0)")

        # table 2: timer_log
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS timer_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # table 3: schedule
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                weekday INTEGER UNIQUE NOT NULL,
                unlock_time TEXT NOT NULL,
                lock_time TEXT NOT NULL
            )
        """)

        # table 4: login_history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS login_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # table 5: app_state (NEW)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                lockmode TEXT,
                status TEXT NOT NULL
            )
        """)
        cursor.execute("INSERT OR IGNORE INTO app_state (id, lockmode, status) VALUES (1, NULL, 'Initializing...')")

    def get_state(self):
        with self._lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT lockmode, status FROM app_state WHERE id = 1")
            result = cursor.fetchone()
            return {"lockmode": result[0], "status": result[1]} if result else {"lockmode": None, "status": ""}

    def set_state(self, lockmode, status):
        with self._lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE app_state SET lockmode = ?, status = ? WHERE id = 1",
                (lockmode, status)
            )
            conn.commit()

    def get_time(self):
        with self._lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT minutes_remaining FROM timer WHERE id = 1")
            result = cursor.fetchone()
            return result[0] if result else 0

    def adjust_time(self, delta_minutes, reason=None):
        with self._lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT minutes_remaining FROM timer WHERE id = 1")
            current = cursor.fetchone()
            current_minutes = current[0] if current else 0
            new_minutes = max(0, current_minutes + delta_minutes)
            cursor.execute("UPDATE timer SET minutes_remaining = ? WHERE id = 1", (new_minutes,))
            cursor.execute("INSERT INTO timer_log (amount, reason) VALUES (?, ?)", (delta_minutes, reason))
            conn.commit()

    def get_timer_logs(self, limit: int = 25):
        with self._lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, amount, reason, created_at FROM timer_log ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [{"id": r[0], "amount": r[1], "reason": r[2], "created_at": r[3]} for r in rows]

    def get_schedule(self, as_json=False):
        with self._lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT weekday, unlock_time, lock_time FROM schedule ORDER BY weekday")
            rows = cursor.fetchall()
            schedule_list = [{"weekday": r[0], "unlock_time": r[1], "lock_time": r[2]} for r in rows]
            if as_json:
                return schedule_list
            return schedule_list
        
    def set_schedule(self, updates):
        with self._lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            if isinstance(updates, str):
                updates = json.loads(updates)
            time_pattern = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
            for weekday_str, times in updates.items():
                weekday = int(weekday_str)
                if not isinstance(times, (list, tuple)) or len(times) != 2:
                    raise ValueError(f"Invalid time tuple for weekday {weekday}: {times}")
                unlock_time, lock_time = times
                if not time_pattern.match(unlock_time):
                    raise ValueError(f"Invalid unlock_time '{unlock_time}' for weekday {weekday}")
                if not time_pattern.match(lock_time):
                    raise ValueError(f"Invalid lock_time '{lock_time}' for weekday {weekday}")
                cursor.execute("""
                    INSERT INTO schedule (weekday, unlock_time, lock_time) VALUES (?, ?, ?)
                    ON CONFLICT(weekday) DO UPDATE SET unlock_time=excluded.unlock_time, lock_time=excluded.lock_time
                """, (weekday, unlock_time, lock_time))
            conn.commit()

    def add_login_history(self, action: str):
        with self._lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            valid_actions = {"login", "logout"}
            if action.lower() not in valid_actions:
                raise ValueError(f"Invalid action '{action}'.")
            cursor.execute("INSERT INTO login_history (action) VALUES (?)", (action.lower(),))
            conn.commit()

    def get_login_history(self, limit: int = 10, as_json: bool = False):
        with self._lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, action, created_at FROM login_history ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            history = [{"id": r[0], "action": r[1], "created_at": r[2]} for r in rows]
            return json.dumps(history) if as_json else history

    def cleanup_timer_log(self, max_rows=1000):
        with self._lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM timer_log WHERE id NOT IN (SELECT id FROM timer_log ORDER BY id DESC LIMIT ?)", (max_rows,))
            conn.commit()

    def cleanup_login_history(self, max_rows=1000):
        with self._lock, self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM login_history WHERE id NOT IN (SELECT id FROM login_history ORDER BY id DESC LIMIT ?)", (max_rows,))
            conn.commit()

    def close(self):
        pass