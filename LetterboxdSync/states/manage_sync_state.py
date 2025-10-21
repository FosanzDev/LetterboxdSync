"""Manage sync group state."""
import reflex as rx
from .auth_state import AuthState

class ManageSyncState(AuthState):
    """State for managing individual sync groups."""

    current_group_id: str = ""
    group_info: dict[str, str] = {}
    group_members: list[dict[str, str]] = []
    show_unshare_dialog: bool = False

    def on_load(self):
        """Load when page loads - get sync_code from route parameter."""
        # First do auth check
        self.clear_messages()
        self.is_hydrated = True

        if not self.check_auth():
            self._clear_user_data()
            return rx.redirect("/login")

        # The sync_code comes from the route parameter [sync_code]
        if hasattr(self, 'sync_code') and self.sync_code:
            self.load_group_by_sync_code(self.sync_code)

    def load_group_by_sync_code(self, sync_code: str):
        """Load sync group information by sync code."""
        try:
            from sync_manager import SyncManager
            sync_manager = SyncManager()
            db = sync_manager.db

            group = db.get_sync_group(sync_code)
            if not group:
                self.set_error("Sync group not found")
                return

            # Format dates properly
            created_at = str(group.created_at or "")
            last_sync = str(group.last_sync or "Never")

            if created_at and len(created_at) > 10:
                created_at = created_at[:10]
            if last_sync != "Never" and len(last_sync) > 10:
                last_sync = last_sync[:10]

            self.group_info = {
                "id": str(group.id),
                "sync_code": group.sync_code,
                "group_name": group.group_name,
                "sync_mode": group.sync_mode.value,
                "created_at": created_at,
                "last_sync": last_sync,
                "is_active": str(group.is_active)
            }
            self.current_group_id = str(group.id)

            # Get group members
            members = db.get_group_members(group.id)
            converted_members = []

            for member in members:
                joined_at = str(member.joined_at or "")
                if joined_at and len(joined_at) > 10:
                    joined_at = joined_at[:10]

                converted_member = {
                    "id": str(member.id),
                    "display_name": member.display_name or member.username,
                    "username": member.username,
                    "list_url": member.list_url,
                    "is_master": str(member.is_master),
                    "joined_at": joined_at,
                    "is_active": str(member.is_active)
                }
                converted_members.append(converted_member)

            self.group_members = converted_members

        except Exception as e:
            self.set_error(f"Error loading group: {str(e)}")

    def show_unshare_confirmation(self):
        self.show_unshare_dialog = True

    def hide_unshare_confirmation(self):
        self.show_unshare_dialog = False

    def confirm_unshare(self):
        """Confirm and execute unshare operation."""
        if not self.current_group_id:
            self.set_error("No group selected")
            return

        self.set_loading(True)
        self.clear_messages()
        self.hide_unshare_confirmation()

        try:
            from sync_manager import SyncManager
            sync_manager = SyncManager()
            db = sync_manager.db

            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                               UPDATE sync_groups SET is_active = 0 WHERE id = ?
                               ''', (int(self.current_group_id),))
                conn.commit()

            self.set_success("Sync group unshared successfully!")
            return rx.redirect("/lists")

        except Exception as e:
            self.set_error(f"Error unsharing group: {str(e)}")
        finally:
            self.set_loading(False)

    async def sync_now(self):
        """Trigger immediate sync of the current group."""
        if not self.current_group_id:
            self.set_error("No group selected")
            return

        self.set_loading(True)
        self.clear_messages()

        try:
            from sync_manager import SyncManager
            sync_manager = SyncManager()

            result = await sync_manager.sync_group_now(int(self.current_group_id))

            if result['success']:
                self.set_success(f"Sync completed! {result['operations_count']} operations performed.")
            else:
                self.set_error(f"Sync failed: {', '.join(result.get('errors', []))}")

        except Exception as e:
            self.set_error(f"Error syncing group: {str(e)}")
        finally:
            self.set_loading(False)