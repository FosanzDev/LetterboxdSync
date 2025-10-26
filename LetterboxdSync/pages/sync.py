"""Sync page."""
import reflex as rx
from ..states.auth_state import AuthState
from ..states.sync_state import SyncState
from ..components.navbar import navbar


def sync_group_card(group) -> rx.Component:
    """Individual sync group card component."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading(group["group_name"], size="4"),
                rx.badge(
                    group["sync_code"],
                    variant="soft",
                    color_scheme="blue",
                    size="2",
                ),
                justify="between",
                align="center",
                width="100%",
            ),

            rx.grid(
                rx.vstack(
                    rx.text("Members", size="2", color_scheme="gray"),
                    rx.text(group['member_count'], size="3"),
                    align="center",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Mode", size="2", color_scheme="gray"),
                    rx.text(group['sync_mode'], size="3"),
                    align="center",
                    spacing="1",
                ),
                rx.vstack(
                    rx.text("Last Sync", size="2", color_scheme="gray"),
                    rx.text(group['last_sync'], size="3"),
                    align="center",
                    spacing="1",
                ),
                columns="3",
                spacing="3",
                width="100%",
            ),

            rx.hstack(
                rx.button(
                    rx.cond(
                        SyncState.is_loading,
                        rx.spinner(size="2"),
                        rx.hstack(
                            rx.icon("refresh-cw"),
                            rx.text("Sync Now"),
                            spacing="1",
                        ),
                    ),
                    on_click=lambda: SyncState.sync_group_now(group["id"]),
                    disabled=SyncState.is_loading,
                    size="2",
                    color_scheme="green",
                    flex="1",
                ),
                rx.button(
                    rx.hstack(
                        rx.icon("settings"),
                        rx.text("Manage"),
                        spacing="1",
                    ),
                    on_click=lambda: rx.redirect(f"/manage-sync/{group['sync_code']}"),
                    size="2",
                    variant="outline",
                    flex="1",
                ),
                spacing="2",
                width="100%",
            ),

            spacing="3",
            align="center",
            width="100%",
        ),
        width="100%",
        padding="1.5rem",
        height="100%",
    )


def sync_page() -> rx.Component:
    """Sync page component (fully responsive)."""
    return rx.cond(
        AuthState.is_authenticated,
        rx.fragment(
            navbar(),
            rx.center(
                rx.container(
                    rx.vstack(
                        # Header
                        rx.vstack(
                            rx.center(
                                rx.heading("Sync Groups", size="7", text_align="center"),
                                width="100%",
                            ),
                            rx.center(
                                rx.text(
                                    "Manage your shared Letterboxd lists",
                                    size="3",
                                    color_scheme="gray",
                                    text_align="center",
                                ),
                                width="100%",
                            ),
                            spacing="2",
                            width="100%",
                        ),

                        # Content
                        rx.cond(
                            SyncState.sync_groups.length() > 0,
                            rx.grid(
                                rx.foreach(SyncState.sync_groups, sync_group_card),
                                columns=rx.breakpoints(
                                    initial="1",
                                    sm="1",
                                    md="2",
                                ),
                                gap="1.5rem",
                                width="100%",
                            ),
                            rx.center(
                                rx.vstack(
                                    rx.icon("users", size=64, color="gray"),
                                    rx.text("No sync groups found", size="4", color_scheme="gray"),
                                    rx.text(
                                        "Share a list from the Lists page to create your first sync group",
                                        size="2",
                                        color_scheme="gray",
                                        text_align="center",
                                    ),
                                    rx.link(
                                        rx.button("Go to Lists", size="3"),
                                        href="/lists",
                                    ),
                                    spacing="3",
                                ),
                                min_height="40vh",
                                width="100%",
                            ),
                        ),

                        # Feedback
                        rx.cond(
                            SyncState.error_message != "",
                            rx.callout(
                                SyncState.error_message,
                                icon="triangle_alert",
                                color_scheme="red",
                            ),
                        ),
                        rx.cond(
                            SyncState.success_message != "",
                            rx.callout(
                                SyncState.success_message,
                                icon="check",
                                color_scheme="green",
                            ),
                        ),

                        spacing="5",
                        padding_y="2rem",
                        width="100%",
                    ),
                    # ✅ Responsive container
                    width="100%",
                    max_width="1400px",
                    mx="auto",
                    padding_x=["1rem", "2rem", "3rem"],
                ),
                width="100%",
            ),
            on_mount=[SyncState.load_sync_groups]
        ),
        # Fallback
        rx.center(
            rx.vstack(
                rx.spinner(size="3"),
                rx.text("Checking authentication...", size="3"),
                spacing="3",
            ),
            min_height="85vh",
        ),
    )
