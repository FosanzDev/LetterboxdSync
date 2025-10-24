"""Authentication state management."""
import reflex as rx
from .base_state import BaseState
from services.auth_service import AuthService

_auth_service = AuthService()

# Define the cookie name and persistence settings
COOKIE_NAME = "session_token"
COOKIE_MAX_AGE = 3600 * 24 * 7  # 7 days persistence

class AuthState(BaseState):
    """State for authentication."""

    username: str = ""
    password: str = ""
    is_authenticated: bool = False
    current_user: str = ""

    # 💡 FIX: Use rx.Cookie(...) as the default value to persist the token.
    # This automatically loads/saves the cookie data.
    session_token: str = rx.Cookie(
        name=COOKIE_NAME,
        max_age=COOKIE_MAX_AGE,
        path="/",
        same_site="lax"
    )

    is_hydrated: bool = False
    redirect_to: str = ""
    auth_loading: bool = False

    def set_loading(self, loading: bool):
        """Set loading state."""
        self.auth_loading = loading
        return

    def set_username(self, value: str):
        self.username = value

    def set_password(self, value: str):
        self.password = value

    @rx.event
    def on_load(self):
        """Check authentication on page load."""
        self.clear_messages()
        self.is_hydrated = True

        # The token is AUTOMATICALLY loaded into self.session_token by rx.Cookie.
        if not self.check_auth():
            self._clear_user_data()
            return rx.redirect("/login")

    def check_auth(self) -> bool:
        """Check if user is authenticated."""
        if self.session_token:
            valid, user_data = _auth_service.verify_session(self.session_token)

            if valid:
                self.is_authenticated = True
                self.current_user = user_data['username']
                return True

        self.is_authenticated = False
        return False

    def _clear_user_data(self):
        """Clear all user-related data from state."""
        self.is_authenticated = False
        self.current_user = ""
        # Setting this to "" automatically clears the cookie on the client.
        self.session_token = ""
        self.username = ""
        self.password = ""

    def login(self):
        """Login or register user."""
        if not self.username or not self.password:
            self.set_error("Please fill in all fields")
            return

        self.clear_messages()
        self.auth_loading = True
        yield

        try:
            success, session_token, message = _auth_service.register_or_login(
                self.username,
                self.password
            )

            if success:
                self.is_authenticated = True
                self.current_user = self.username
                # Setting the rx.Cookie var automatically saves it on the client
                self.session_token = session_token

                self.password = ""
                self.set_success(message)
                self.auth_loading = False
                yield rx.redirect("/dashboard")
            else:
                self.set_error(message)
                self.auth_loading = False
                yield

        except Exception as e:
            self.set_error(f"An error occurred: {str(e)}")
            self.auth_loading = False
            yield

    def logout(self):
        """Logout user."""
        if self.session_token:
            _auth_service.logout(self.session_token)

        # Clears user data and sets self.session_token = "" to clear the cookie.
        self._clear_user_data()
        self.clear_messages()

        return rx.redirect("/login")

    def check_login_redirect(self):
        """Check if already logged in and redirect from login page."""
        self.clear_messages()

        if self.is_authenticated:
            return rx.redirect("/dashboard")

    def clear_all_messages(self):
        """Manually clear all messages - can be called from UI."""
        self.clear_messages()