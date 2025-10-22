"""List detail state management."""
import reflex as rx
from LetterboxdScraper import LetterboxdScraper
from .auth_state import AuthState
import math

class ListDetailState(AuthState):
    """State for list detail page."""

    current_list_id: str = ""
    list_name: str = ""
    list_url: str = ""
    movies: list[dict[str, str]] = []  # Added proper typing
    current_page: int = 1
    total_count: int = 0
    total_pages: int = 0
    has_more: bool = False
    movies_per_letterboxd_page: int = 100
    list_detail_loading: bool = False

    def set_loading(self, loading: bool):
        """Set loading state."""
        self.list_detail_loading = loading
        return

    def set_list_info(self, list_id: str, list_name: str, list_url: str, film_count: str = "0"):
        """Set the current list information."""
        self.current_list_id = list_id
        self.list_name = list_name
        self.list_url = list_url
        self.current_page = 1
        self.movies = []

        # Use the film count from the lists API
        try:
            self.total_count = int(film_count)
            self.total_pages = math.ceil(self.total_count / self.movies_per_letterboxd_page)
            self.has_more = self.total_pages > 1
        except (ValueError, TypeError):
            self.total_count = 0
            self.total_pages = 0
            self.has_more = False

    def on_load(self):
        """Load list details when page loads."""
        # First check authentication like other pages
        self.clear_messages()
        self.is_hydrated = True
        self.set_loading(True)

        yield

        if not self.check_auth():
            self._clear_user_data()
            return rx.redirect("/login")

        # Get the list_id from the route parameter
        # In Reflex, dynamic route parameters are automatically available
        route_list_id = getattr(self, 'list_id', None)  # This comes from the route [list_id]

        if route_list_id and not self.list_url:
            # We need to get list info from somewhere - maybe from ListsState
            # For now, let's trigger an error to load from lists page
            return rx.redirect("/lists")

        # If we have list info, load the movies
        if self.list_url:
            self.load_movies_page()

    def load_movies_page(self, page: int = 1):
        """Load movies for a specific Letterboxd page (server-side pagination)."""
        if not self.is_authenticated:
            self.set_error("Please login first")
            return

        if not self.list_url:
            self.set_error("No list selected")
            return

        self.set_loading(True)
        self.clear_messages()

        try:
            # Use _auth_service (imported from auth_state) - same pattern as ListsState
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
                self.list_url
            )

            if not scraper.login():
                self.set_error("Failed to connect to Letterboxd")
                self.set_loading(False)
                return

            # Get movies from specific page (server-side pagination)
            movies_on_page = scraper.get_movies_by_page(page)

            if movies_on_page:
                # Convert movies to the format expected by the frontend
                converted_movies = []
                for movie in movies_on_page:
                    converted_movie = {
                        "name": str(movie.get("name", "")),
                        "slug": str(movie.get("slug", "")),
                        "film_id": str(movie.get("film_id", "")),
                        "link": str(movie.get("link", "")),
                        "rating": str(movie.get("rating", "") if movie.get("rating") else ""),
                        "poster_url": str(movie.get("poster_url", "")),
                        "object_id": str(movie.get("object_id", ""))
                    }
                    converted_movies.append(converted_movie)

                self.movies = converted_movies
                self.current_page = page
                self.has_more = page < self.total_pages

                self.set_success(f"Loaded {len(self.movies)} movies (Page {page} of {self.total_pages})")
            else:
                # If no movies on this page, we might be at the end
                if page == 1:
                    self.movies = []
                    self.set_error("No movies found in this list")
                else:
                    self.set_error(f"No movies found on page {page}")

        except Exception as e:
            self.set_error(f"Error loading movies: {str(e)}")
        finally:
            self.set_loading(False)

    def next_page(self):
        """Load next page of movies."""
        if self.has_more and not self.list_detail_loading:
            self.load_movies_page(self.current_page + 1)

    def prev_page(self):
        """Load previous page of movies."""
        if self.current_page > 1 and not self.list_detail_loading:
            self.load_movies_page(self.current_page - 1)

    def go_to_page(self, page: int):
        """Go to specific page."""
        if 1 <= page <= self.total_pages and not self.list_detail_loading:
            self.load_movies_page(page)