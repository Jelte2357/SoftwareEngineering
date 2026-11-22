"""SQLite persistence for prediction-score caching and user flags.

Database creates and accesses the hash_scores and hash_flags tables. Scores
are keyed by a 128-character hexadecimal text hash, while flags record a
boolean user-provided label associated with a hash. A threading lock is
exposed for callers that coordinate access through this Database instance."""

import sqlite3
import threading
from config import DB_PATH

class Database:
    """Small SQLite access layer for prediction scores and feedback flags.

    Each method opens its own SQLite connection. The instance-level lock is
    provided for callers that need to serialize a sequence of database/cache
    operations; individual methods do not acquire that lock themselves."""
    def __init__(self, db_path=DB_PATH):
        """Create a database accessor and ensure the required tables exist.

        Args:
            db_path: SQLite database file path. Defaults to DB_PATH from config.py."""
        self.db_path = db_path
        self.lock = threading.Lock()
        self.initialize()

    def initialize(self):
        """Create the score-cache and user-flag tables if they do not exist.

        The hash_scores table enforces a 128-character lowercase hexadecimal hash
        and a score between 0.0 and 1.0. The hash_flags table applies the same hash
        constraint and restricts flags to integer values 0 or 1."""
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
        """Open and return a new SQLite connection.

        Returns:
            sqlite3.Connection connected to this instance's database path."""
        return sqlite3.connect(self.db_path)
        
    def insert_scores(self, text_scores: dict[str, float]):
        # Requires no hashes to already exist in the database, otherwise it will throw an error
        """Insert prediction scores without overwriting existing hashes.

        Args:
            text_scores: Mapping of 128-character hexadecimal hashes to scores.

        Notes:
            Uses INSERT ... ON CONFLICT(hash) DO NOTHING, so existing cached scores
            are retained. The method relies on the table constraints for validation."""
        with self.connect() as conn:
            conn.executemany(
                "INSERT INTO hash_scores (hash, score) VALUES (?, ?) ON CONFLICT(hash) DO NOTHING",
                list(text_scores.items())
            )
            
    def insert_flag(self, hash, flag: bool):
        """Insert one user-provided flag associated with a text hash.

        Args:
            hash: BLAKE2b hexadecimal digest identifying the text.
            flag: Boolean value converted to SQLite integer 0 or 1.

        Notes:
            Each call inserts a new row; this table does not declare hash as unique."""
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO hash_flags (hash, flag) VALUES (?, ?)",
                (hash, int(flag))
            )
            
    def get_scores(self, hashes: list[str]):
        """Look up cached scores and identify hashes that are not cached.

        Args:
            hashes: List of hashes to look up.

        Returns:
            A tuple containing a dictionary of found hash-to-score entries and a
            list of hashes for which no score row exists. An empty input returns
            ``({}, [])``.

        Notes:
            A temporary table is populated with the requested hashes and left-joined
            to hash_scores so missing entries can be returned explicitly."""
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
        """Retrieve all stored user flags.

        Returns:
            List of ``(hash, flag)`` tuples, with the stored integer flag converted
            to a Python bool. Rows are returned without an explicit ordering."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT hash, flag FROM hash_flags"
            ).fetchall()
            return [(hash_value, bool(flag)) for hash_value, flag in rows]
