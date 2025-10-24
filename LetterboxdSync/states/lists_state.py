"""Lists state management."""
import reflex as rx
from .auth_state import AuthState
from LetterboxdScraper import LetterboxdScraper
from ..states.sync_state import SyncState


class ListsState(AuthState):
    """State for managing user lists."""

    user_lists: list[dict[str, str]] = []
    selected_list: dict[str, str] = {}
    sharing_status_loading: bool = False
    lists_loading: bool = False

    def set_loading(self, loading: bool):
        """Set loading state."""
        self.lists_loading = loading
        return

    def on_load(self):
        """Auto-load lists and refresh shared status."""
        if len(self.user_lists) == 0:
            # Return the event instead of calling it directly
            return ListsState.fetch_user_lists

        # Return an event to trigger a reactive SyncState call
        return SyncState.refresh_shared_status_for_lists(self.user_lists)

    def fetch_user_lists(self):
        """Fetch all lists for the current user."""
        if not self.is_authenticated:
            self.set_error("Please login first")
            return

        # Clear messages and set loading state
        self.clear_messages()
        self.set_loading(True)

        # Force UI update to show spinner
        yield

        try:
            # Use _auth_service (imported from auth_state)
            from .auth_state import _auth_service

            valid, user_data = _auth_service.verify_session(self.session_token)

            if not valid:
                self.set_error("Session expired. Please login again.")
                self.is_authenticated = False
                self.set_loading(False)
                yield
                return

            scraper = LetterboxdScraper(
                user_data['username'],
                user_data['password'],
                "https://letterboxd.com"
            )

            if not scraper.login():
                self.set_error("Failed to connect to Letterboxd")
                self.set_loading(False)
                yield
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
                yield

                # Trigger shared status check
                self.check_shared_status_for_lists()

                self.set_success(f"Found {len(lists)} lists!")
            else:
                self.set_error("No lists found")

            self.set_loading(False)
            yield

        except Exception as e:
            self.set_error(f"Error: {str(e)}")
            self.set_loading(False)
            yield

    def check_shared_status_for_lists(self):
        """Delegate to SyncState to refresh shared statuses."""
        from ..states.sync_state import SyncState
        yield from SyncState.refresh_shared_status_for_lists(self.user_lists)

    def select_list(self, list_id: str, list_name: str, list_url: str, film_count: str = "0"):
        """Select a list."""
        self.selected_list = {
            "id": list_id,
            "name": list_name,
            "url": list_url,
            "film_count": film_count
        }
        return rx.redirect(f"/lists/{list_id}")