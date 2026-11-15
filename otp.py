import hmac
import random
import re
import sqlite3
from time import time
from contextlib import closing, contextmanager

EXPIRY = 300
COOLDOWN = 15
ATTEMPTS = 5


class OtpStore:
    def __init__(self, path, secret):
        self.path = path
        self.secret = secret.encode()
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS otp (
                    browser TEXT PRIMARY KEY, digest TEXT NOT NULL,
                    generated INTEGER NOT NULL, attempts INTEGER NOT NULL
                )
            """)

    @contextmanager
    def transaction(self):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            yield connection

    def digest(self, browser, code):
        return hmac.digest(self.secret, f"otp:{browser}:{code}".encode(), "sha256").hex()

    def issue(self, browser):
        with self.transaction() as connection:
            now = int(time())
            connection.execute("DELETE FROM otp WHERE generated <= ?", (now - EXPIRY,))
            previous = connection.execute(
                "SELECT generated FROM otp WHERE browser = ?", (browser,)
            ).fetchone()
            if previous and now - previous[0] < COOLDOWN:
                remaining = COOLDOWN - (now - previous[0])
                return None, f"Wait {remaining} seconds before generating another code."
            code = f"{random.SystemRandom().randrange(1_000_000):06d}"
            connection.execute("INSERT OR REPLACE INTO otp VALUES (?, ?, ?, ?)",
                               (browser, self.digest(browser, code), now, ATTEMPTS))
            return code, "A new demo code is ready."

    def verify(self, browser, code):
        if not re.fullmatch(r"[0-9]{6}", code):
            return False, "Enter exactly six digits, including any leading zero."
        with self.transaction() as connection:
            record = connection.execute(
                "SELECT digest, generated, attempts FROM otp WHERE browser = ?", (browser,)
            ).fetchone()
            if record is None:
                return False, "Generate a demo code first."
            digest, generated, attempts = record
            if int(time()) - generated >= EXPIRY:
                return False, "This code expired. Generate a new one."
            if attempts == 0:
                return False, "This code is closed. Generate a new one."
            if hmac.compare_digest(digest, self.digest(browser, code)):
                connection.execute("UPDATE otp SET attempts = 0 WHERE browser = ?", (browser,))
                return True, "Code verified successfully."
            attempts -= 1
            connection.execute("UPDATE otp SET attempts = ? WHERE browser = ?", (attempts, browser))
            if not attempts:
                return False, "No attempts left. Generate a new code."
            return False, f"Incorrect code. Attempts remaining: {attempts}."

