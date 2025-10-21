"""Navigation component."""
import reflex as rx
from ..states.auth_state import AuthState


def navbar() -> rx.Component:
    """Create navigation bar with mobile support."""
    return rx.box(
        rx.hstack(
            # Left side - Logo/Title (responsive)
            rx.hstack(
                rx.link(
                    rx.heading(
                        rx.desktop_only("📽️ Letterboxd Sync"),
                        rx.mobile_only("📽️ LB Sync"),
                        size="5",  # Reduced from 6
                    ),
                    href=rx.cond(
                        AuthState.is_authenticated,
                        "/dashboard",
                        "/",
                    ),
                ),
                # Desktop navigation links (only on desktop)
                rx.desktop_only(
                    rx.cond(
                        AuthState.is_authenticated,
                        rx.hstack(
                            rx.link(
                                rx.button("Dashboard", variant="ghost", size="2"),
                                href="/dashboard"
                            ),
                            rx.link(
                                rx.button("My Lists", variant="ghost", size="2"),
                                href="/lists"
                            ),
                            spacing="2",
                        ),
                    ),
                ),
                spacing="4",
            ),

            # Right side - User menu and color mode
            rx.hstack(
                rx.cond(
                    AuthState.is_authenticated,
                    rx.menu.root(
                        rx.menu.trigger(
                            rx.button(
                                rx.icon("user", size=18),
                                rx.desktop_only(
                                    rx.text(AuthState.current_user, size="2"),
                                ),
                                variant="soft",
                                size="2",
                            ),
                        ),
                        rx.menu.content(
                            # User info (always shown in menu)
                            rx.menu.item(
                                rx.hstack(
                                    rx.icon("user", size=16),
                                    rx.text(AuthState.current_user),
                                    spacing="2",
                                ),
                                disabled=True,
                            ),
                            rx.menu.separator(),

                            # Mobile-only Menu Items (use display array to avoid wrappers)
                            # display array uses responsive breakpoints: [base, sm, md, lg, ...]
                            # Show only at base/mobile -> ["block", "none", "none", "none"]
                            rx.menu.item(
                                rx.hstack(
                                    rx.icon("layout-dashboard", size=16),
                                    rx.text("Dashboard"),
                                    spacing="2",
                                ),
                                on_click=rx.redirect("/dashboard"),
                                display=["block", "none", "none", "none"],
                            ),
                            rx.menu.item(
                                rx.hstack(
                                    rx.icon("list", size=16),
                                    rx.text("My Lists"),
                                    spacing="2",
                                ),
                                on_click=rx.redirect("/lists"),
                                display=["block", "none", "none", "none"],
                            ),
                            rx.menu.separator(
                                display=["block", "none", "none", "none"],
                            ),

                            # Logout (always shown)
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
                            rx.desktop_only(rx.text("Login")),
                            size="2"
                        ),
                        href="/login"
                    ),
                ),
                rx.color_mode.button(size="2"),
                spacing="2",
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