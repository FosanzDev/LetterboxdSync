"""Dashboard page."""
import reflex as rx
from ..states.auth_state import AuthState
from ..components.navbar import navbar


def dashboard_page() -> rx.Component:
    """Dashboard page component."""
    return rx.cond(
        AuthState.is_authenticated,
        # Authenticated content
        rx.fragment(
            navbar(),
            rx.container(
                rx.vstack(
                    rx.heading(
                        f"Welcome back, {AuthState.current_user}!",
                        size="8",
                    ),

                    rx.grid(
                        rx.card(
                            rx.vstack(
                                rx.heading("📋 My Lists", size="5"),
                                rx.text(
                                    "View and manage your Letterboxd lists",
                                    color_scheme="gray",
                                ),
                                rx.link(
                                    rx.button("Go to Lists", size="3"),
                                    href="/lists",
                                ),
                                spacing="3",
                                align="start",
                            ),
                        ),
                        rx.card(
                            rx.vstack(
                                rx.heading("🔄 Sync Groups", size="5"),
                                rx.text(
                                    "Create and manage sync groups",
                                    color_scheme="gray",
                                ),
                                rx.button(
                                    "Coming Soon",
                                    size="3",
                                    disabled=True,
                                ),
                                spacing="3",
                                align="start",
                            ),
                        ),
                        columns=rx.breakpoints(
                            initial="1",
                            sm="1",
                            md="2",
                            lg="2",
                        ),
                        spacing="4",
                        width="100%",
                    ),

                    spacing="5",
                    padding_y="2rem",
                ),
                max_width="1200px",
            ),
        ),
        # Fallback while checking authentication or redirecting
        rx.center(
            rx.vstack(
                rx.spinner(size="3"),
                rx.text("Loading...", size="3"),
                spacing="3",
            ),
            min_height="85vh",
        ),
    )