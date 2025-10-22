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
            rx.center(
                rx.container(
                    rx.vstack(
                        # Welcome header
                        rx.heading(
                            f"Welcome back, {AuthState.current_user}!",
                            size="8",
                            text_align="center",
                            width="100%",
                        ),

                        # Dashboard grid cards
                        # Dashboard grid cards
                        rx.grid(
                            rx.card(
                                rx.vstack(
                                    rx.heading("📋 My Lists", size="5"),
                                    rx.text(
                                        "View and manage your Letterboxd lists",
                                        color_scheme="gray",
                                    ),
                                    rx.link(
                                        rx.button("Go to Lists", size="3", width="100%"),  # ✅ full width
                                        href="/lists",
                                        width="100%",  # ensures link container stretches too
                                    ),
                                    spacing="3",
                                    align="start",
                                    height="100%",
                                    justify="between",
                                ),
                                width="100%",
                                height="100%",
                            ),
                            rx.card(
                                rx.vstack(
                                    rx.heading("🔄 Sync Groups", size="5"),
                                    rx.text(
                                        "Manage your shared lists and sync groups",
                                        color_scheme="gray",
                                    ),
                                    rx.link(
                                        rx.button("Manage Syncs", size="3", width="100%"),  # ✅ full width
                                        href="/sync",
                                        width="100%",
                                    ),
                                    spacing="3",
                                    align="start",
                                    height="100%",
                                    justify="between",
                                ),
                                width="100%",
                                height="100%",
                            ),
                            # ✅ Responsive grid layout
                            columns=rx.breakpoints(
                                initial="1",
                                sm="1",
                                md="2",
                                lg="2",
                            ),
                            gap="1.5rem",  # consistent spacing between cards
                            width="100%",
                            justify_items="center",
                            align_items="stretch",  # cards same height
                        ),
                        spacing="6",
                        padding_y="2rem",
                        width="100%",  # ensures vstack fills horizontally
                        align="center",
                    ),
                    # ✅ Responsive container
                    width="100%",
                    max_width="1400px",
                    mx="auto",  # center container horizontally
                    padding_x=["1rem", "2rem", "3rem"],  # responsive side padding
                ),
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
