"""Database manager for the sync system"""
import sqlite3
import secrets
import string
import threading
import time
from typing import List, Optional, Tuple
from cryptography.fernet import Fernet
import os
from contextlib import contextmanager

from models.sync_models import SyncGroup, GroupMember, SyncMode, OperationType, SyncOperation


class DatabaseManager:
    def __init__(self, db_path: str = "letterboxd_sync.db"):
        self.db_path = db_path
        self.encryption_key = self._get_or_create_key()
        self.cipher = Fernet(self.encryption_key)
        self._lock = threading.RLock()  # Add thread lock
        self._init_database()

    @contextmanager
    def get_connection(self, timeout=30.0, retries=3):
        """Get a database connection with proper timeout and retry logic."""
        connection = None
        for attempt in range(retries):
            try:
                connection = sqlite3.connect(
                    self.db_path,
                    timeout=timeout,
                    check_same_thread=False  # Allow use across threads
                )
                connection.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode for better concurrency
                connection.execute("PRAGMA busy_timeout=30000")  # 30 second busy timeout
                yield connection
                break
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e).lower() and attempt < retries - 1:
                    time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    raise
            finally:
                if connection:
                    connection.close()

    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key for credentials"""
        key_file = "sync_key.key"
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key

    def _init_database(self):
        """Initialize database with required tables"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Sync groups table
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS sync_groups (
                                                                          id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                          sync_code VARCHAR(10) UNIQUE NOT NULL,
                                   group_name VARCHAR(100) NOT NULL,
                                   sync_mode VARCHAR(20) NOT NULL,
                                   master_user_id INTEGER,
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   last_sync TIMESTAMP,
                                   is_active BOOLEAN DEFAULT 1
                                   )
                               ''')

                # Group members table
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS sync_group_members (
                                                                                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                                 sync_group_id INTEGER NOT NULL,
                                                                                 username_encrypted TEXT NOT NULL,
                                                                                 password_encrypted TEXT NOT NULL,
                                                                                 list_url TEXT NOT NULL,
                                                                                 display_name VARCHAR(50),
                                   list_id VARCHAR(20),
                                   is_master BOOLEAN DEFAULT 0,
                                   joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   is_active BOOLEAN DEFAULT 1,
                                   FOREIGN KEY (sync_group_id) REFERENCES sync_groups(id) ON DELETE CASCADE
                                   )
                               ''')

                # Current state of movies in each user's list
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS user_movie_states (
                                                                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                                member_id INTEGER NOT NULL,
                                                                                film_id VARCHAR(20) NOT NULL,
                                   added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   is_present BOOLEAN DEFAULT 1,
                                   UNIQUE(member_id, film_id),
                                   FOREIGN KEY (member_id) REFERENCES sync_group_members(id) ON DELETE CASCADE
                                   )
                               ''')

                # Sync operations log
                cursor.execute('''
                               CREATE TABLE IF NOT EXISTS sync_operations (
                                                                              id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                                              sync_group_id INTEGER NOT NULL,
                                                                              operation_type VARCHAR(20) NOT NULL,
                                   film_id VARCHAR(20) NOT NULL,
                                   source_member_id INTEGER,
                                   target_member_id INTEGER,
                                   timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                   success BOOLEAN DEFAULT 1,
                                   error_message TEXT,
                                   FOREIGN KEY (sync_group_id) REFERENCES sync_groups(id) ON DELETE CASCADE,
                                   FOREIGN KEY (source_member_id) REFERENCES sync_group_members(id),
                                   FOREIGN KEY (target_member_id) REFERENCES sync_group_members(id)
                                   )
                               ''')

                conn.commit()

    def _encrypt_credential(self, credential: str) -> str:
        """Encrypt a credential string"""
        return self.cipher.encrypt(credential.encode()).decode()

    def _decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt a credential string"""
        return self.cipher.decrypt(encrypted_credential.encode()).decode()

    def generate_sync_code(self) -> str:
        """Generate a unique sync code"""
        with self._lock:
            while True:
                code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                if not self.sync_code_exists(code):
                    return code

    def sync_code_exists(self, sync_code: str) -> bool:
        """Check if sync code already exists"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM sync_groups WHERE sync_code = ? AND is_active = 1", (sync_code,))
            return cursor.fetchone() is not None

    def create_sync_group(self, group_name: str, sync_mode: SyncMode,
                          master_member: GroupMember = None) -> Tuple[int, str]:
        """Create a new sync group"""
        with self._lock:
            sync_code = self.generate_sync_code()

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Create the sync group
                cursor.execute('''
                               INSERT INTO sync_groups (sync_code, group_name, sync_mode)
                               VALUES (?, ?, ?)
                               ''', (sync_code, group_name, sync_mode.value))

                group_id = cursor.lastrowid

                # If master-slave mode and master provided, add the master user
                if sync_mode == SyncMode.MASTER_SLAVE and master_member:
                    master_id = self._add_member_to_group_internal(cursor, group_id, master_member)

                    # Update group with master_user_id
                    cursor.execute('''
                                   UPDATE sync_groups SET master_user_id = ? WHERE id = ?
                                   ''', (master_id, group_id))

                conn.commit()

            return group_id, sync_code

    def _add_member_to_group_internal(self, cursor, group_id: int, member: GroupMember) -> int:
        """Internal method to add member using existing cursor"""
        encrypted_username = self._encrypt_credential(member.username)
        encrypted_password = self._encrypt_credential(member.password)

        cursor.execute('''
                       INSERT INTO sync_group_members
                       (sync_group_id, username_encrypted, password_encrypted, list_url,
                        display_name, list_id, is_master)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ''', (group_id, encrypted_username, encrypted_password, member.list_url,
                             member.display_name, member.list_id, member.is_master))

        return cursor.lastrowid

    def add_member_to_group(self, group_id: int, member: GroupMember) -> int:
        """Add a member to a sync group"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                member_id = self._add_member_to_group_internal(cursor, group_id, member)
                conn.commit()
                return member_id

    def join_sync_group(self, sync_code: str, member: GroupMember) -> Optional[int]:
        """Join an existing sync group"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Check if sync group exists and is active
                cursor.execute('''
                               SELECT id, sync_mode FROM sync_groups
                               WHERE sync_code = ? AND is_active = 1
                               ''', (sync_code,))

                result = cursor.fetchone()
                if not result:
                    return None

                group_id, sync_mode = result
                member.sync_group_id = group_id
                member.is_master = False  # Never master when joining

                member_id = self._add_member_to_group_internal(cursor, group_id, member)
                conn.commit()
                return member_id

    def get_sync_group(self, sync_code: str) -> Optional[SyncGroup]:
        """Get sync group by code"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT id, sync_code, group_name, sync_mode, master_user_id,
                                  created_at, last_sync, is_active
                           FROM sync_groups
                           WHERE sync_code = ? AND is_active = 1
                           ''', (sync_code,))

            result = cursor.fetchone()
            if not result:
                return None

            return SyncGroup(
                id=result[0],
                sync_code=result[1],
                group_name=result[2],
                sync_mode=SyncMode(result[3]),
                master_user_id=result[4],
                created_at=result[5],
                last_sync=result[6],
                is_active=bool(result[7])
            )

    def is_list_already_shared(self, list_url: str) -> bool:
        """Check if a list URL is already shared in any active sync group"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT 1 FROM sync_group_members sgm
                                             JOIN sync_groups sg ON sgm.sync_group_id = sg.id
                           WHERE sgm.list_url = ? AND sgm.is_active = 1 AND sg.is_active = 1
                           ''', (list_url,))
            return cursor.fetchone() is not None

    def get_sync_group_by_list_url(self, list_url: str) -> Optional[dict]:
        """Get sync group information for a specific list URL"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT sg.id, sg.sync_code, sg.group_name, sg.sync_mode
                           FROM sync_groups sg
                                    JOIN sync_group_members sgm ON sg.id = sgm.sync_group_id
                           WHERE sgm.list_url = ? AND sgm.is_active = 1 AND sg.is_active = 1
                               LIMIT 1
                           ''', (list_url,))

            result = cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'sync_code': result[1],
                    'group_name': result[2],
                    'sync_mode': result[3]
                }
            return None

    def get_group_members(self, group_id: int) -> List[GroupMember]:
        """Get all active members of a sync group"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT id, sync_group_id, username_encrypted, password_encrypted,
                                  list_url, display_name, list_id, is_master, joined_at, is_active
                           FROM sync_group_members
                           WHERE sync_group_id = ? AND is_active = 1
                           ORDER BY is_master DESC, joined_at ASC
                           ''', (group_id,))

            members = []
            for row in cursor.fetchall():
                members.append(GroupMember(
                    id=row[0],
                    sync_group_id=row[1],
                    username=self._decrypt_credential(row[2]),
                    password=self._decrypt_credential(row[3]),
                    list_url=row[4],
                    display_name=row[5],
                    list_id=row[6],
                    is_master=bool(row[7]),
                    joined_at=row[8],
                    is_active=bool(row[9])
                ))

            return members

    def update_member_list_id(self, member_id: int, list_id: str):
        """Update the cached list ID for a member"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                               UPDATE sync_group_members
                               SET list_id = ?
                               WHERE id = ?
                               ''', (list_id, member_id))
                conn.commit()

    def get_member_list_id(self, member_id: int) -> Optional[str]:
        """Get cached list ID for a member"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT list_id FROM sync_group_members WHERE id = ?
                           ''', (member_id,))

            result = cursor.fetchone()
            return result[0] if result and result[0] else None

    def update_user_movie_state(self, member_id: int, film_id: str, is_present: bool = True):
        """Update the current state of a movie in a user's list"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_movie_states (member_id, film_id, is_present, added_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (member_id, film_id, is_present))
                conn.commit()

    def get_user_movie_states(self, member_id: int) -> List[str]:
        """Get all film IDs currently in a user's list"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT film_id FROM user_movie_states
                           WHERE member_id = ? AND is_present = 1
                           ''', (member_id,))

            return [row[0] for row in cursor.fetchall()]

    def log_sync_operation(self, sync_group_id: int, operation_type: OperationType,
                           film_id: str, source_member_id: int = None,
                           target_member_id: int = None, success: bool = True,
                           error_message: str = None):
        """Log a sync operation"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                               INSERT INTO sync_operations
                               (sync_group_id, operation_type, film_id, source_member_id,
                                target_member_id, success, error_message)
                               VALUES (?, ?, ?, ?, ?, ?, ?)
                               ''', (sync_group_id, operation_type.value, film_id, source_member_id,
                                     target_member_id, success, error_message))
                conn.commit()

    def update_last_sync(self, group_id: int):
        """Update the last sync timestamp for a group"""
        with self._lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                               UPDATE sync_groups SET last_sync = CURRENT_TIMESTAMP WHERE id = ?
                               ''', (group_id,))
                conn.commit()

    def get_all_active_sync_groups(self) -> List[SyncGroup]:
        """Get all active sync groups"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT id, sync_code, group_name, sync_mode, master_user_id,
                                  created_at, last_sync, is_active
                           FROM sync_groups
                           WHERE is_active = 1
                           ''')

            groups = []
            for row in cursor.fetchall():
                groups.append(SyncGroup(
                    id=row[0],
                    sync_code=row[1],
                    group_name=row[2],
                    sync_mode=SyncMode(row[3]),
                    master_user_id=row[4],
                    created_at=row[5],
                    last_sync=row[6],
                    is_active=bool(row[7])
                ))

            return groups