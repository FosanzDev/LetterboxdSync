"""Authentication service with database operations."""
import sqlite3
import hashlib
import secrets
from typing import Optional, Tuple
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import os
import sys

# Add parent directory to path to import LetterboxdScraper
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from LetterboxdScraper import LetterboxdScraper
from db.db_config import db_config


class AuthService:
    """Service for authentication and user management."""

    def __init__(self, db_path: str = None):
        # Use centralized config if no specific path provided
        if db_path is None:
            db_path = db_config.get_users_db_path()

        self.db_path = db_path

        # Ensure the directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)
        self._init_database()

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for credentials."""
        key_file = db_config.get_auth_key_path()

        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Ensure directory exists
            os.makedirs(os.path.dirname(key_file), exist_ok=True)
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key

    # ... rest of the methods remain exactly the same ...
    def _encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential string."""
        return self.cipher.encrypt(credential.encode()).decode()

    def _decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential string."""
        return self.cipher.decrypt(encrypted_credential.encode()).decode()

    def _init_database(self):
        """Initialize database with users table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS users (
                                                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                username VARCHAR(100) UNIQUE NOT NULL,
                               password_hash TEXT NOT NULL,
                               salt TEXT NOT NULL,
                               password_encrypted TEXT NOT NULL,
                               letterboxd_session TEXT,
                               session_token TEXT UNIQUE,
                               session_expires TIMESTAMP,
                               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                               last_login TIMESTAMP
                               )
                           ''')
            conn.commit()

    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using PBKDF2."""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        ).hex()

    def _generate_salt(self) -> str:
        """Generate a random salt."""
        return secrets.token_hex(32)

    def _generate_session_token(self) -> str:
        """Generate a session token."""
        return secrets.token_urlsafe(64)

    def verify_letterboxd_credentials(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Verify credentials with Letterboxd."""
        try:
            scraper = LetterboxdScraper(username, password, "https://letterboxd.com")

            if scraper.login():
                session_data = scraper.session.cookies.get_dict()
                return True, str(session_data)
            return False, None
        except Exception as e:
            print(f"Error verifying Letterboxd credentials: {e}")
            return False, None

    def register_or_login(self, username: str, password: str) -> Tuple[bool, Optional[str], str]:
        """Register or login user."""
        letterboxd_verified, letterboxd_session = self.verify_letterboxd_credentials(username, password)

        if not letterboxd_verified:
            return False, None, "Invalid Letterboxd credentials"

        password_encrypted = self._encrypt_credential(password)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password_hash, salt FROM users WHERE username = ?", (username,))
            result = cursor.fetchone()

            if result:
                user_id, stored_hash, salt = result
                password_hash = self._hash_password(password, salt)

                if password_hash == stored_hash:
                    session_token = self._generate_session_token()
                    session_expires = datetime.now() + timedelta(days=7)

                    cursor.execute('''
                                   UPDATE users
                                   SET session_token = ?, session_expires = ?,
                                       last_login = CURRENT_TIMESTAMP,
                                       letterboxd_session = ?,
                                       password_encrypted = ?
                                   WHERE id = ?
                                   ''', (session_token, session_expires, letterboxd_session, password_encrypted, user_id))
                    conn.commit()

                    return True, session_token, "Login successful"
                else:
                    return False, None, "Invalid credentials"
            else:
                salt = self._generate_salt()
                password_hash = self._hash_password(password, salt)
                session_token = self._generate_session_token()
                session_expires = datetime.now() + timedelta(days=7)

                cursor.execute('''
                               INSERT INTO users
                               (username, password_hash, salt, password_encrypted, session_token,
                                session_expires, last_login, letterboxd_session)
                               VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                               ''', (username, password_hash, salt, password_encrypted, session_token,
                                     session_expires, letterboxd_session))
                conn.commit()

                return True, session_token, "Account created successfully"

    def verify_session(self, session_token: str) -> Tuple[bool, Optional[dict]]:
        """Verify session token."""
        if not session_token:
            return False, None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT id, username, session_expires, letterboxd_session, password_encrypted
                           FROM users
                           WHERE session_token = ?
                           ''', (session_token,))

            result = cursor.fetchone()

            if not result:
                return False, None

            user_id, username, session_expires, letterboxd_session, password_encrypted = result

            if datetime.fromisoformat(session_expires) < datetime.now():
                return False, None

            password = self._decrypt_credential(password_encrypted)

            return True, {
                'id': user_id,
                'username': username,
                'password': password,
                'letterboxd_session': letterboxd_session
            }

    def logout(self, session_token: str) -> bool:
        """Logout user."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           UPDATE users
                           SET session_token = NULL, session_expires = NULL
                           WHERE session_token = ?
                           ''', (session_token,))
            conn.commit()
            return cursor.rowcount > 0