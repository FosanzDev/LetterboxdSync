"""Base state with shared functionality."""
import reflex as rx


class BaseState(rx.State):
    """Base state with common functionality."""

    # Loading states
    is_loading: bool = False
    error_message: str = ""
    success_message: str = ""

    def set_loading(self, loading: bool):
        """Set loading state."""
        self.is_loading = loading

    def set_error(self, message: str):
        """Set error message."""
        self.error_message = message
        self.success_message = ""

    def set_success(self, message: str):
        """Set success message."""
        self.success_message = message
        self.error_message = ""

    def clear_messages(self):
        """Clear all messages."""
        self.error_message = ""
        self.success_message = ""