"""Sync state management."""
import reflex as rx
from .auth_state import AuthState

class SyncState(AuthState):
    """State for sync operations."""

    shared_lists: list[dict[str, str]] = []
    sync_groups: list[dict[str, str]] = []
    shared_list_status: dict[str, bool] = {}
    sync_loading: bool = False

    def _get_sync_manager(self):
        """Get a sync manager instance."""
        from sync_manager import SyncManager
        return SyncManager()

    def refresh_shared_status(self):
        """Refresh the shared status - simplified version"""
        # Don't try to access other states, just prepare empty dict
        # The status will be checked when share/unshare is clicked
        if not hasattr(self, 'shared_list_status') or not self.shared_list_status:
            self.shared_list_status = {}

    def refresh_shared_status_for_lists(self, user_lists: list[dict[str, str]]):
        """Refresh shared status for a batch of lists."""
        self.sync_loading = True
        yield  # allows the spinner to show

        try:
            sync_manager = self._get_sync_manager()
            db = sync_manager.db

            new_status = {}
            for list_item in user_lists:
                list_url = list_item.get("url", "")
                if list_url:
                    new_status[list_url] = db.is_list_already_shared(list_url)

            self.shared_list_status = new_status

        except Exception as e:
            print(f"Error refreshing shared list status: {e}")

        finally:
            self.sync_loading = False
            yield  # triggers a frontend re-render with new button states

    def check_if_list_shared(self, list_url: str) -> bool:
        """Check if a specific list is shared - called on demand"""
        try:
            sync_manager = self._get_sync_manager()
            db = sync_manager.db
            is_shared = db.is_list_already_shared(list_url)

            # Update the cache
            new_status = dict(self.shared_list_status)
            new_status[list_url] = is_shared
            self.shared_list_status = new_status

            return is_shared
        except Exception as e:
            print(f"Error checking if list is shared: {e}")
            return False

    def share_list(self, list_id: str, list_name: str, list_url: str):
        """Share a list by creating a sync group."""
        if not self.is_authenticated:
            self.set_error("Please login first")
            return

        # Check if already shared first
        if self.check_if_list_shared(list_url):
            self.set_error("This list is already shared!")
            return

        self.sync_loading = True
        self.clear_messages()
        yield

        try:
            # Use _auth_service to get credentials
            from .auth_state import _auth_service
            valid, user_data = _auth_service.verify_session(self.session_token)

            if not valid:
                self.set_error("Session expired. Please login again.")
                self.is_authenticated = False
                self.sync_loading = False
                return None

            sync_manager = self._get_sync_manager()

            # Create sync group with the user's list as master
            group_id, sync_code = sync_manager.create_sync_group(
                group_name=f"{list_name} - Shared",
                sync_mode="master_slave",
                master_username=user_data['username'],
                master_password=user_data['password'],
                master_list_url=list_url,
                master_display_name=user_data['username']
            )

            # Update the shared status
            new_status = dict(self.shared_list_status)
            new_status[list_url] = True
            self.shared_list_status = new_status

            self.set_success(f"List shared! Sync code: {sync_code}")

            # Refresh shared lists
            self.load_sync_groups()

            # Redirect to sync page
            return rx.redirect("/sync")

        except Exception as e:
            self.set_error(f"Error sharing list: {str(e)}")
        finally:
            self.sync_loading = False

    def navigate_to_manage(self, list_url: str):
        """Navigate to the manage page for a sync group."""
        try:
            from sync_manager import SyncManager
            sync_manager = SyncManager()
            db = sync_manager.db

            # Get sync group info by list URL
            sync_group_info = db.get_sync_group_by_list_url(list_url)

            if not sync_group_info:
                self.set_error("Sync group not found")
                return

            # Redirect to manage page with sync code
            return rx.redirect(f"/manage-sync/{sync_group_info['sync_code']}")

        except Exception as e:
            self.set_error(f"Error navigating to manage page: {str(e)}")

    def unshare_list(self, list_url: str):
        """Unshare a list by deactivating the sync group"""
        if not self.is_authenticated:
            self.set_error("Please login first")
            return

        self.sync_loading = True
        self.clear_messages()
        yield

        try:
            sync_manager = self._get_sync_manager()
            db = sync_manager.db

            # Get the sync group for this list
            sync_group_info = db.get_sync_group_by_list_url(list_url)

            if not sync_group_info:
                self.set_error("List is not shared")
                self.sync_loading = False
                return

            # Deactivate the sync group
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                               UPDATE sync_groups SET is_active = 0 WHERE id = ?
                               ''', (sync_group_info['id'],))
                conn.commit()

            # Update the shared status
            new_status = dict(self.shared_list_status)
            new_status[list_url] = False
            self.shared_list_status = new_status

            self.set_success("List unshared successfully!")

            # Refresh sync groups
            self.load_sync_groups()

        except Exception as e:
            self.set_error(f"Error unsharing list: {str(e)}")
        finally:
            self.sync_loading = False

    def load_sync_groups(self):
        """Load all sync groups for the current user."""
        try:
            sync_manager = self._get_sync_manager()
            sync_groups = sync_manager.get_all_sync_groups()

            converted_groups = []
            for group in sync_groups:
                converted_group = {
                    "id": str(group["id"]),
                    "sync_code": str(group["sync_code"]),
                    "group_name": str(group["group_name"]),
                    "sync_mode": str(group["sync_mode"]),
                    "member_count": str(group["member_count"]),
                    "created_at": str(group.get("created_at", "")),
                    "last_sync": str(group.get("last_sync", "") if group.get("last_sync") else "Never")
                }
                converted_groups.append(converted_group)

            self.sync_groups = converted_groups

        except Exception as e:
            self.set_error(f"Error loading sync groups: {str(e)}")

    async def sync_group_now(self, group_id: str):
        """Trigger immediate sync of a specific group."""
        self.sync_loading = True
        self.clear_messages()
        yield

        try:
            sync_manager = self._get_sync_manager()
            result = await sync_manager.sync_group_now(int(group_id))

            if result['success']:
                self.set_success(f"Sync completed! {result['operations_count']} operations performed.")
            else:
                self.set_error(f"Sync failed: {', '.join(result.get('errors', []))}")

        except Exception as e:
            self.set_error(f"Error syncing group: {str(e)}")
        finally:
            self.sync_loading = False
