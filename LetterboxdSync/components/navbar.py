"""Navigation component."""
import reflex as rx
from ..states.auth_state import AuthState


def navbar() -> rx.Component:
    """Create navigation bar with responsive visibility."""
    return rx.box(
        rx.hstack(
            # Left side — title + desktop links
            rx.hstack(
                # Title
                rx.link(
                    rx.heading(
                        "📽️ LB Sync",
                        size="5",
                        white_space="nowrap",
                    ),
                    href=rx.cond(
                        AuthState.is_authenticated,
                        "/dashboard",
                        "/",
                    ),
                ),

                # Desktop links
                rx.cond(
                    AuthState.is_authenticated,
                    rx.hstack(
                        rx.link(
                            rx.button(
                                rx.hstack(
                                    rx.icon("layout-dashboard", size=16),
                                    rx.text("Dashboard"),
                                    spacing="2",
                                    align_items="center",  # ✅ vertically center icon + text
                                ),
                                variant="ghost",
                                size="2",
                                height="100%",  # ensures button fills navbar height
                                display="flex",
                                align_items="center",  # ✅ vertically center content inside button
                            ),
                            href="/dashboard",
                        ),
                        rx.link(
                            rx.button(
                                rx.hstack(
                                    rx.icon("list", size=16),
                                    rx.text("My Lists"),
                                    spacing="2",
                                    align_items="center",
                                ),
                                variant="ghost",
                                size="2",
                                height="100%",
                                display="flex",
                                align_items="center",
                            ),
                            href="/lists",
                        ),
                        rx.link(
                            rx.button(
                                rx.hstack(
                                    rx.icon("refresh-cw", size=16),
                                    rx.text("My Sync Groups"),
                                    spacing="2",
                                    align_items="center",
                                ),
                                variant="ghost",
                                size="2",
                                height="100%",
                                display="flex",
                                align_items="center",
                            ),
                            href="/sync",
                        ),
                        spacing="5",  # gap between buttons
                        display=["none", "none", "flex", "flex"],
                    ),
                ),
                spacing="4",
                align="center",
            ),

            # Right side — user menu & color mode toggle
            rx.hstack(
                rx.cond(
                    AuthState.is_authenticated,
                    rx.menu.root(
                        rx.menu.trigger(
                            rx.button(
                                rx.icon("user", size=18),
                                rx.text(
                                    AuthState.current_user,
                                    size="2",
                                    display=["none", "none", "block", "block"],
                                ),
                                variant="soft",
                                size="2",
                            ),
                        ),
                        rx.menu.content(
                            # User info (always shown)
                            rx.menu.item(
                                rx.hstack(
                                    rx.icon("user", size=16),
                                    rx.text(AuthState.current_user),
                                    spacing="2",
                                ),
                                disabled=True,
                            ),
                            rx.menu.separator(),

                            # ✅ Mobile-only menu items (visible below md)
                            rx.menu.item(
                                rx.hstack(
                                    rx.icon("layout-dashboard", size=16),
                                    rx.text("Dashboard"),
                                    spacing="2",
                                ),
                                on_click=rx.redirect("/dashboard"),
                                display=["block", "block", "none", "none"],
                            ),
                            rx.menu.item(
                                rx.hstack(
                                    rx.icon("list", size=16),
                                    rx.text("My Lists"),
                                    spacing="2",
                                ),
                                on_click=rx.redirect("/lists"),
                                display=["block", "block", "none", "none"],
                            ),
                            rx.menu.item(
                                rx.hstack(
                                    rx.icon("refresh-cw", size=16),
                                    rx.text("My Sync Groups"),
                                    spacing="2",
                                ),
                                on_click=rx.redirect("/sync"),
                                display=["block", "block", "none", "none"],
                            ),
                            rx.menu.separator(display=["block", "block", "none", "none"]),

                            # Logout (always)
                            rx.menu.item(
                                rx.hstack(
                                    rx.icon("log-out", size=16),
                                    rx.text("Logout"),
                                    spacing="2",
                                ),
                                on_click=AuthState.logout,
                                color_scheme="red",
                            ),
                        ),
                    ),
                    # Not authenticated → Login button
                    rx.link(
                        rx.button(
                            rx.icon("log-in", size=18),
                            rx.text("Login", display=["none", "none", "block", "block"]),
                            size="2",
                        ),
                        href="/login",
                    ),
                ),
                rx.color_mode.button(size="2"),
                spacing="2",
                align="center",
            ),

            justify="between",
            align="center",
            width="100%",
        ),
        position="sticky",
        top="0",
        z_index="1000",
        padding_x="1rem",
        padding_y="0.75rem",
        backdrop_filter="blur(10px)",
        border_bottom="1px solid var(--gray-5)",
        width="100%",
        background="var(--color-panel-translucent)",
    )
