from config import DB_PATH
import sqlite3
import threading

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.initialize()

    def initialize(self):
        with self.connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS hash_scores (
                    hash TEXT PRIMARY KEY,
                    score REAL NOT NULL CHECK (score >= 0.0 AND score <= 1.0),
                    CHECK (
                        length(hash) = 128
                        AND hash NOT GLOB '*[^0-9a-f]*'
                    )
                ) WITHOUT ROWID"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS hash_flags (
                    id INTEGER PRIMARY KEY,
                    hash TEXT NOT NULL,
                    flag INTEGER NOT NULL CHECK (flag IN (0, 1)),
                    CHECK (
                        length(hash) = 128
                        AND hash NOT GLOB '*[^0-9a-f]*'
                    )
                )"""
            )

    def connect(self):
        return sqlite3.connect(self.db_path)
        
    def insert_scores(self, text_scores: dict[str, float]):
        # Requires no hashes to already exist in the database, otherwise it will throw an error
        with self.connect() as conn:
            conn.executemany(
                "INSERT INTO hash_scores (hash, score) VALUES (?, ?) ON CONFLICT(hash) DO NOTHING",
                list(text_scores.items())
            )
            
    def insert_flag(self, hash, flag: bool):
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO hash_flags (hash, flag) VALUES (?, ?)",
                (hash, int(flag))
            )
            
    def get_scores(self, hashes: list[str]):
        if not hashes:
            return {}, []
        
        with self.connect() as conn:
            conn.execute(
                "CREATE TEMP TABLE IF NOT EXISTS request_hashes (hash TEXT PRIMARY KEY) WITHOUT ROWID",
            )
            conn.execute("DELETE FROM request_hashes")
            conn.executemany(
                "INSERT INTO request_hashes (hash) VALUES (?)",
                [(h,) for h in hashes]
            )
            rows = conn.execute(
                "SELECT h.hash, hs.score FROM request_hashes AS h LEFT JOIN hash_scores AS hs ON h.hash = hs.hash"
            ).fetchall()
            
            found = {}
            missing = []
            
            for hash_value, score in rows:
                if score is None:
                    missing.append(hash_value)
                else:
                    found[hash_value] = score
            return found, missing
        
    def get_all_flags(self):
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT hash, flag FROM hash_flags"
            ).fetchall()
            return [(hash_value, bool(flag)) for hash_value, flag in rows]
