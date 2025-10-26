"""Enhanced Sync Manager with automatic polling and better error handling"""
import asyncio
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from db.database_manager import DatabaseManager
from db.db_config import db_config
from services.sync_service import SyncService
from services.letterboxd_service import LetterboxdService
from models.sync_models import GroupMember, SyncMode
import logging

logger = logging.getLogger(__name__)


class SyncManager:
    """Main interface for the sync system with auto-polling support"""

    def __init__(self, db_path: str = None):
        # Use centralized config if no specific path provided
        if db_path is None:
            db_path = db_config.get_sync_db_path()

        self.db = DatabaseManager(db_path)
        self.sync_service = SyncService(self.db)
        self.letterboxd_service = LetterboxdService()
        self._polling_task = None
        self._is_polling = False

    # User Lists Operations
    async def get_user_lists(self, username: str, password: str) -> List[Dict]:
        """Get all lists for a user - returns simple dicts for UI"""
        try:
            lists = await self.letterboxd_service.get_user_lists(username, password)
            return [
                {
                    'id': lst.id,
                    'name': lst.name,
                    'slug': lst.slug,
                    'url': lst.url,
                    'film_count': lst.film_count,
                    'description': lst.description,
                    'owner': lst.owner
                }
                for lst in lists
            ]
        except Exception as e:
            logger.error(f"Error fetching user lists: {e}")
            return []

    async def validate_list_exists(self, username: str, password: str, list_url: str) -> bool:
        """Validate that a list exists and is accessible"""
        try:
            member = GroupMember(
                id=0, sync_group_id=0,
                username=username, password=password,
                list_url=list_url, display_name=username
            )
            movies = await self.letterboxd_service.get_movies_from_list(member)
            return movies is not None
        except Exception as e:
            logger.error(f"Error validating list: {e}")
            return False

    # Sync Group Operations
    def create_sync_group(
        self,
        group_name: str,
        sync_mode: str,
        master_username: str = None,
        master_password: str = None,
        master_list_url: str = None,
        master_display_name: str = None
    ) -> Tuple[int, str]:
        """
        Create a new sync group

        Args:
            group_name: Name of the sync group
            sync_mode: "master_slave" or "collaborative"
            master_username: Required for master_slave mode
            master_password: Required for master_slave mode
            master_list_url: Required for master_slave mode
            master_display_name: Optional display name for master

        Returns:
            Tuple of (group_id, sync_code)
        """
        mode = SyncMode.MASTER_SLAVE if sync_mode == "master_slave" else SyncMode.COLLABORATIVE

        master_member = None
        if mode == SyncMode.MASTER_SLAVE:
            if not all([master_username, master_password, master_list_url]):
                raise ValueError("Master credentials required for master_slave mode")

            master_member = GroupMember(
                id=0,
                sync_group_id=0,
                username=master_username,
                password=master_password,
                list_url=master_list_url,
                display_name=master_display_name or master_username,
                is_master=True
            )

        return self.db.create_sync_group(group_name, mode, master_member)

    def join_sync_group(
        self,
        sync_code: str,
        username: str,
        password: str,
        list_url: str,
        display_name: str = None
    ) -> Optional[int]:
        """
        Join an existing sync group

        Returns:
            Member ID if successful, None otherwise
        """
        # Validate sync code exists
        if not self.validate_sync_code(sync_code):
            logger.error(f"Invalid sync code: {sync_code}")
            return None

        member = GroupMember(
            id=0,
            sync_group_id=0,
            username=username,
            password=password,
            list_url=list_url,
            display_name=display_name or username,
            is_master=False
        )

        return self.db.join_sync_group(sync_code, member)

    def get_sync_group_info(self, sync_code: str) -> Optional[Dict]:
        """Get detailed sync group information"""
        group = self.db.get_sync_group(sync_code)
        if not group:
            return None

        members = self.db.get_group_members(group.id)

        return {
            'id': group.id,
            'sync_code': group.sync_code,
            'group_name': group.group_name,
            'sync_mode': group.sync_mode.value,
            'member_count': len(members),
            'created_at': group.created_at,
            'last_sync': group.last_sync,
            'members': [
                {
                    'id': m.id,
                    'display_name': m.display_name,
                    'list_url': m.list_url,
                    'is_master': m.is_master,
                    'joined_at': m.joined_at
                }
                for m in members
            ]
        }

    # Sync Operations
    async def sync_group_now(self, group_id: int) -> Dict:
        """Trigger immediate sync of a specific group"""
        try:
            result = await self.sync_service.sync_group(group_id)
            return {
                'success': result.success,
                'group_id': result.group_id,
                'operations_count': result.operations_count,
                'errors_count': result.errors_count,
                'operations': result.operations,
                'errors': result.errors,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error syncing group {group_id}: {e}")
            return {
                'success': False,
                'group_id': group_id,
                'operations_count': 0,
                'errors_count': 1,
                'operations': [],
                'errors': [str(e)],
                'timestamp': datetime.now().isoformat()
            }

    async def sync_all_groups_now(self) -> Dict:
        """Trigger immediate sync of all groups"""
        try:
            return await self.sync_service.sync_all_groups()
        except Exception as e:
            logger.error(f"Error syncing all groups: {e}")
            return {
                'success': False,
                'groups_processed': 0,
                'results': [],
                'error': str(e)
            }

    def get_all_sync_groups(self) -> List[Dict]:
        """Get all active sync groups"""
        groups = self.db.get_all_active_sync_groups()

        result = []
        for group in groups:
            members = self.db.get_group_members(group.id)
            result.append({
                'id': group.id,
                'sync_code': group.sync_code,
                'group_name': group.group_name,
                'sync_mode': group.sync_mode.value,
                'member_count': len(members),
                'created_at': group.created_at,
                'last_sync': group.last_sync
            })

        return result

    def get_sync_groups_for_user(self, username: str) -> List[Dict]:
        """Get all active sync groups for a specific user."""
        groups = self.db.get_sync_groups_for_user(username)

        result = []
        for group in groups:
            members = self.db.get_group_members(group.id)
            result.append({
                'id': group.id,
                'sync_code': group.sync_code,
                'group_name': group.group_name,
                'sync_mode': group.sync_mode.value,
                'member_count': len(members),
                'created_at': group.created_at,
                'last_sync': group.last_sync
            })

        return result

    # Automatic Polling
    async def start_auto_sync(self, interval_seconds: int = 300):
        """
        Start automatic syncing every X seconds

        Args:
            interval_seconds: Time between sync cycles (default: 300 = 5 minutes)
        """
        if self._is_polling:
            logger.warning("Auto-sync already running")
            return

        self._is_polling = True
        logger.info(f"Starting auto-sync with {interval_seconds}s interval")

        try:
            while self._is_polling:
                logger.info("Auto-sync cycle starting")
                result = await self.sync_all_groups_now()
                logger.info(f"Auto-sync cycle completed: {result.get('groups_processed', 0)} groups processed")

                await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("Auto-sync cancelled")
        finally:
            self._is_polling = False

    def stop_auto_sync(self):
        """Stop automatic syncing"""
        if not self._is_polling:
            logger.warning("Auto-sync not running")
            return

        logger.info("Stopping auto-sync")
        self._is_polling = False

    def is_auto_sync_running(self) -> bool:
        """Check if auto-sync is currently running"""
        return self._is_polling

    # Utility Methods
    def validate_sync_code(self, sync_code: str) -> bool:
        """Check if sync code exists"""
        return self.db.sync_code_exists(sync_code)

    def clear_all_caches(self):
        """Clear all caches (useful for testing)"""
        self.sync_service.list_id_cache.clear()
        self.letterboxd_service.clear_scraper_cache()

    async def get_sync_health_check(self) -> Dict:
        """Get health status of all sync groups"""
        groups = self.get_all_sync_groups()
        health = {
            'total_groups': len(groups),
            'groups': []
        }

        for group in groups:
            members = self.db.get_group_members(group['id'])
            group_health = {
                'group_id': group['id'],
                'group_name': group['group_name'],
                'member_count': len(members),
                'last_sync': group['last_sync'],
                'status': 'healthy' if members else 'no_members'
            }
            health['groups'].append(group_health)

        return health


# Example usage for background service
async def run_sync_service():
    """Run the sync service as a background task"""
    manager = SyncManager()

    # Start auto-sync with 5-minute intervals
    await manager.start_auto_sync(interval_seconds=300)


# Example usage for web framework (Reflex/FastAPI)
"""
from sync_manager import SyncManager

# In your application startup
sync_manager = SyncManager()

# Start background task
import asyncio
asyncio.create_task(sync_manager.start_auto_sync(interval_seconds=300))

# In your API/UI endpoints
@app.post("/create-group")
async def create_group(data: dict):
    group_id, sync_code = sync_manager.create_sync_group(
        group_name=data["group_name"],
        sync_mode=data["sync_mode"],
        master_username=data.get("master_username"),
        master_password=data.get("master_password"),
        master_list_url=data.get("master_list_url")
    )
    return {"group_id": group_id, "sync_code": sync_code}

@app.post("/join-group")
async def join_group(data: dict):
    member_id = sync_manager.join_sync_group(
        sync_code=data["sync_code"],
        username=data["username"],
        password=data["password"],
        list_url=data["list_url"],
        display_name=data.get("display_name")
    )
    return {"success": member_id is not None, "member_id": member_id}

@app.post("/sync-now/{group_id}")
async def sync_now(group_id: int):
    result = await sync_manager.sync_group_now(group_id)
    return result

@app.get("/groups")
def get_groups():
    return sync_manager.get_all_sync_groups()
"""