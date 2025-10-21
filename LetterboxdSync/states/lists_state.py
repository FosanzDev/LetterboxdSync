"""Lists state management."""
import reflex as rx
import sys
import os
from .auth_state import AuthState

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
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
                self.set_success(f"Found {len(lists)} lists!")
            else:
                self.set_error("No lists found")

            self.set_loading(False)

        except Exception as e:
            self.set_error(f"Error: {str(e)}")
            self.set_loading(False)

    def select_list(self, list_id: str, list_name: str, list_url: str, film_count: str = "0"):
        """Select a list."""
        self.selected_list = {
            "id": list_id,
            "name": list_name,
            "url": list_url,
            "film_count": film_count
        }
        # Set the list detail state info
        from .list_detail_state import ListDetailState
        detail_state = self.get_state(ListDetailState)
        detail_state.set_list_info(list_id, list_name, list_url, film_count)

        return rx.redirect(f"/list/{list_id}")