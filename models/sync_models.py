"""Data models for the sync system"""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from enum import Enum

class SyncMode(Enum):
    MASTER_SLAVE = "master_slave"
    COLLABORATIVE = "collaborative"

class OperationType(Enum):
    ADD_MOVIE = "add_movie"
    REMOVE_MOVIE = "remove_movie"

@dataclass
class SyncGroup:
    id: int
    sync_code: str
    group_name: str
    sync_mode: SyncMode
    master_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    is_active: bool = True

@dataclass
class GroupMember:
    id: int
    sync_group_id: int
    username: str
    password: str
    list_url: str
    display_name: str
    list_id: Optional[str] = None
    is_master: bool = False
    joined_at: Optional[datetime] = None
    is_active: bool = True

@dataclass
class MovieState:
    member_id: int
    film_id: str
    is_present: bool = True
    added_at: Optional[datetime] = None

@dataclass
class SyncOperation:
    id: int
    sync_group_id: int
    operation_type: OperationType
    film_id: str
    source_member_id: Optional[int] = None
    target_member_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    success: bool = True
    error_message: Optional[str] = None

@dataclass
class SyncResult:
    success: bool
    group_id: int
    operations_count: int = 0
    errors_count: int = 0
    operations: List[str] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.operations is None:
            self.operations = []
        if self.errors is None:
            self.errors = []

@dataclass
class ListInfo:
    id: str
    name: str
    slug: str
    url: str
    film_count: str
    description: str
    owner: str