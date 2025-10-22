"""Centralized database configuration and path management."""
import os
from pathlib import Path


class DatabaseConfig:
    """Central configuration for all database paths and settings."""

    def __init__(self):
        # Simple approach: use environment variable or default to ./data
        data_path = os.getenv("DATABASE_PATH", "./data")
        self.base_path = Path(data_path)

        # Ensure data directory exists
        self.base_path.mkdir(exist_ok=True)

        # Database file paths
        self.sync_db_path = self.base_path / "letterboxd_sync.db"
        self.users_db_path = self.base_path / "letterboxd_users.db"

        # Key file paths (store keys with databases)
        self.sync_key_path = self.base_path / "sync_key.key"
        self.auth_key_path = self.base_path / "auth_key.key"

    def get_sync_db_path(self) -> str:
        """Get the sync database path as string."""
        return str(self.sync_db_path)

    def get_users_db_path(self) -> str:
        """Get the users database path as string."""
        return str(self.users_db_path)

    def get_sync_key_path(self) -> str:
        """Get the sync encryption key path as string."""
        return str(self.sync_key_path)

    def get_auth_key_path(self) -> str:
        """Get the auth encryption key path as string."""
        return str(self.auth_key_path)


# Global instance
db_config = DatabaseConfig()