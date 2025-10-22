"""Manage sync group page."""
import reflex as rx
from ..states.auth_state import AuthState
from ..states.manage_sync_state import ManageSyncState
from ..components.navbar import navbar


def member_card(member) -> rx.Component:
    """Individual member card component."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.heading(member["display_name"], size="4"),
                rx.cond(
                    member["is_master"] == "True",
                    rx.badge("Master", variant="solid", color_scheme="gold", size="2"),
                    rx.badge("Member", variant="soft", color_scheme="blue", size="2"),
                ),
                spacing="2",
                align="center",
                justify="between",
                width="100%",
            ),
            rx.text(
                f"Joined: {member['joined_at']}",
                size="2",
                color_scheme="gray",
            ),
            rx.text(
                f"List: {member['list_url']}",
                size="2",
                color_scheme="gray",
                width="100%",
                word_break="break-all",
            ),
            align="start",
            spacing="2",
            width="100%",
        ),
        width="100%",
        padding="1.5rem",
        height="100%",
    )


def unshare_confirmation_dialog() -> rx.Component:
    """Unshare confirmation dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.dialog.title("Unshare Sync Group"),
                rx.dialog.description(
                    "Are you sure you want to unshare this sync group? This action cannot be undone and all members will lose access."
                ),
                rx.hstack(
                    rx.dialog.close(
                        rx.button("Cancel", variant="soft", color_scheme="gray"),
                    ),
                    rx.button(
                        rx.cond(
                            ManageSyncState.is_loading,
                            rx.spinner(size="2"),
                            "Confirm Unshare",
                        ),
                        on_click=ManageSyncState.confirm_unshare,
                        disabled=ManageSyncState.is_loading,
                        color_scheme="red",
                    ),
                    spacing="2",
                    justify="end",
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            max_width="500px",
        ),
        open=ManageSyncState.show_unshare_dialog,
        on_open_change=ManageSyncState.hide_unshare_confirmation,
    )


def manage_sync_page() -> rx.Component:
    """Manage sync group page component (responsive and consistent)."""
    return rx.cond(
        AuthState.is_authenticated,
        rx.fragment(
            navbar(),
            unshare_confirmation_dialog(),
            rx.script(
                "if (window.location.pathname.includes('/manage-sync/')) { "
                "const syncCode = window.location.pathname.split('/manage-sync/')[1]; "
                "fetch('/api/load_sync_group/' + syncCode); }"
            ),
            rx.center(
                rx.container(
                    rx.vstack(
                        # Back button
                        rx.hstack(
                            rx.link(
                                rx.button(
                                    rx.icon("arrow-left"),
                                    "Back to Syncs",
                                    variant="soft",
                                ),
                                href="/sync",
                            ),
                            width="100%",
                        ),

                        # Group info
                        rx.center(
                            rx.card(
                                rx.vstack(
                                    rx.center(
                                        rx.heading(
                                            ManageSyncState.group_info.get("group_name", "Loading..."),
                                            size="7",
                                            text_align="center",
                                        ),
                                        width="100%",
                                    ),
                                    rx.grid(
                                        rx.vstack(
                                            rx.text("Sync Code", size="2", color_scheme="gray"),
                                            rx.text(
                                                ManageSyncState.group_info.get("sync_code", ""),
                                                size="3",
                                                font_weight="bold",
                                            ),
                                            align="center",
                                            spacing="1",
                                        ),
                                        rx.vstack(
                                            rx.text("Sync Mode", size="2", color_scheme="gray"),
                                            rx.text(
                                                ManageSyncState.group_info.get("sync_mode", ""),
                                                size="3",
                                            ),
                                            align="center",
                                            spacing="1",
                                        ),
                                        rx.vstack(
                                            rx.text("Created", size="2", color_scheme="gray"),
                                            rx.text(
                                                ManageSyncState.group_info.get("created_at", ""),
                                                size="3",
                                            ),
                                            align="center",
                                            spacing="1",
                                        ),
                                        rx.vstack(
                                            rx.text("Last Sync", size="2", color_scheme="gray"),
                                            rx.text(
                                                ManageSyncState.group_info.get("last_sync", "Never"),
                                                size="3",
                                            ),
                                            align="center",
                                            spacing="1",
                                        ),
                                        columns=rx.breakpoints(initial="1", sm="2"),
                                        spacing="4",
                                        width="100%",
                                    ),

                                    # Buttons
                                    rx.box(
                                        rx.hstack(
                                            rx.button(
                                                rx.cond(
                                                    ManageSyncState.is_loading,
                                                    rx.spinner(size="2"),
                                                    rx.hstack(
                                                        rx.icon("eye"),
                                                        rx.text("View List"),
                                                        spacing="1",
                                                    ),
                                                ),
                                                on_click=lambda: rx.redirect(
                                                    f"/list/{ManageSyncState.group_info['id']}"),
                                                disabled=ManageSyncState.is_loading,
                                                color_scheme="blue",
                                                size="3",
                                                width="100%",
                                            ),
                                            rx.button(
                                                rx.cond(
                                                    ManageSyncState.is_loading,
                                                    rx.spinner(size="2"),
                                                    rx.hstack(
                                                        rx.icon("refresh-cw"),
                                                        rx.text("Sync Now"),
                                                        spacing="1",
                                                    ),
                                                ),
                                                on_click=ManageSyncState.sync_now,
                                                disabled=ManageSyncState.is_loading,
                                                color_scheme="green",
                                                size="3",
                                                width="100%",  # ✅ ensures button fits inside parent
                                            ),
                                            rx.button(
                                                rx.hstack(
                                                    rx.icon("trash"),
                                                    rx.text("Unshare Group"),
                                                    spacing="1",
                                                ),
                                                on_click=ManageSyncState.show_unshare_confirmation,
                                                color_scheme="red",
                                                variant="outline",
                                                size="3",
                                                width="100%",  # ✅ same width control
                                            ),
                                            spacing="3",
                                            wrap="wrap",
                                            justify="center",
                                            width="100%",
                                        ),
                                        width="100%",
                                        mt="1rem",
                                    ),
                                    spacing="4",
                                    align="center",
                                    width="100%",
                                ),
                                padding="2rem",
                                width="100%",
                            ),
                            width="100%",
                        ),

                        # Members list
                        rx.vstack(
                            rx.heading("Group Members", size="5"),
                            rx.cond(
                                ManageSyncState.group_members.length() > 0,
                                rx.grid(
                                    rx.foreach(ManageSyncState.group_members, member_card),
                                    columns=rx.breakpoints(initial="1", sm="2"),
                                    gap="1rem",
                                    width="100%",
                                ),
                                rx.center(
                                    rx.text(
                                        "No members found",
                                        size="4",
                                        color_scheme="gray",
                                    ),
                                    width="100%",
                                    padding="2rem",
                                ),
                            ),
                            spacing="3",
                            width="100%",
                        ),

                        # Feedback
                        rx.cond(
                            ManageSyncState.error_message != "",
                            rx.callout(
                                ManageSyncState.error_message,
                                icon="triangle_alert",
                                color_scheme="red",
                            ),
                        ),
                        rx.cond(
                            ManageSyncState.success_message != "",
                            rx.callout(
                                ManageSyncState.success_message,
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
