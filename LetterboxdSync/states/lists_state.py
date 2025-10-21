"""Lists state management."""
import reflex as rx
from .auth_state import AuthState
from LetterboxdScraper import LetterboxdScraper


class ListsState(AuthState):
    """State for managing user lists."""

    user_lists: list[dict[str, str]] = []
    selected_list: dict[str, str] = {}

    def on_load(self):
        """Auto-load lists if none are cached."""
        if len(self.user_lists) == 0 and not self.is_loading:
            self.fetch_user_lists()

    def fetch_user_lists(self):
        """Fetch all lists for the current user."""
        if not self.is_authenticated:
            self.set_error("Please login first")
            return

        self.set_loading(True)
        self.clear_messages()

        try:
            # Use _auth_service (imported from auth_state)
            from .auth_state import _auth_service

            valid, user_data = _auth_service.verify_session(self.session_token)

            if not valid:
                self.set_error("Session expired. Please login again.")
                self.is_authenticated = False
                self.set_loading(False)
                return

            scraper = LetterboxdScraper(
                user_data['username'],
                user_data['password'],
                "https://letterboxd.com"
            )

            if not scraper.login():
                self.set_error("Failed to connect to Letterboxd")
                self.set_loading(False)
                return

            lists = scraper.get_all_lists(user_data['username'])

            if lists:
                converted_lists = []
                for list_item in lists:
                    converted_list = {
                        "id": str(list_item.get("id", "")),
                        "name": str(list_item.get("name", "")),
                        "slug": str(list_item.get("slug", "")),
                        "url": str(list_item.get("url", "")),
                        "film_count": str(list_item.get("film_count", "0")),
                        "description": str(list_item.get("description", "")),
                        "owner": str(list_item.get("owner", ""))
                    }
                    converted_lists.append(converted_list)

                self.user_lists = converted_lists

                # Trigger shared status check
                self.check_shared_status_for_lists()

                self.set_success(f"Found {len(lists)} lists!")
            else:
                self.set_error("No lists found")

            self.set_loading(False)

        except Exception as e:
            self.set_error(f"Error: {str(e)}")
            self.set_loading(False)

    def check_shared_status_for_lists(self):
        """Check shared status for all current lists and update SyncState"""
        try:
            from sync_manager import SyncManager
            sync_manager = SyncManager()
            db = sync_manager.db

            # Check shared status for each list
            status_dict = {}
            for list_item in self.user_lists:
                list_url = list_item.get("url", "")
                if list_url:
                    status_dict[list_url] = db.is_list_already_shared(list_url)

            # Update the shared status in the current state
            # We'll add this to our own state instead of trying to access SyncState
            self.update_shared_status(status_dict)

        except Exception as e:
            print(f"Error checking shared lists: {e}")

    def update_shared_status(self, status_dict: dict):
        """Update shared status - this will trigger SyncState update via event"""
        # We'll handle this through an event or direct state update
        pass  # For now, we'll handle this differently

    def select_list(self, list_id: str, list_name: str, list_url: str, film_count: str = "0"):
        """Select a list."""
        self.selected_list = {
            "id": list_id,
            "name": list_name,
            "url": list_url,
            "film_count": film_count
        }
        return rx.redirect(f"/lists/{list_id}")