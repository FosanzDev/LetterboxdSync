"""Authentication state management."""
import reflex as rx
from .base_state import BaseState
from ..services.auth_service import AuthService

_auth_service = AuthService()

class AuthState(BaseState):
    """State for authentication."""

    username: str = ""
    password: str = ""
    is_authenticated: bool = False
    current_user: str = ""
    session_token: str = ""
    is_hydrated: bool = False
    redirect_to: str = ""

    def set_username(self, value: str):
        self.username = value

    def set_password(self, value: str):
        self.password = value

    def on_load(self):
        """Check authentication on page load."""
        # Clear any lingering messages when navigating to protected pages
        self.clear_messages()

        self.is_hydrated = True
        if not self.check_auth():
            # Clear any cached user data
            self._clear_user_data()
            # Redirect to login if not authenticated
            return rx.redirect("/login")

    def check_auth(self) -> bool:
        """Check if user is authenticated."""
        if self.session_token:
            # Use _auth_service
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
        self.session_token = ""
        self.username = ""
        self.password = ""

    def login(self):
        """Login or register user."""
        if not self.username or not self.password:
            self.set_error("Please fill in all fields")
            return

        self.set_loading(True)
        self.clear_messages()

        # Use _auth_service instead of self.auth_service
        success, session_token, message = _auth_service.register_or_login(
            self.username,
            self.password
        )

        self.set_loading(False)

        if success:
            self.is_authenticated = True
            self.current_user = self.username
            self.session_token = session_token
            self.set_success(message)
            self.password = ""
            # Clear the success message after a short delay before redirect
            return rx.redirect("/dashboard")
        else:
            self.set_error(message)

    def logout(self):
        """Logout user."""
        if self.session_token:
            # Use _auth_service
            _auth_service.logout(self.session_token)

        # Clear all user data and messages
        self._clear_user_data()
        self.clear_messages()

        # Redirect to login
        return rx.redirect("/login")

    def check_login_redirect(self):
        """Check if already logged in and redirect from login page."""
        # Clear messages when loading login page
        self.clear_messages()

        if self.is_authenticated:
            return rx.redirect("/dashboard")

    def clear_all_messages(self):
        """Manually clear all messages - can be called from UI."""
        self.clear_messages()