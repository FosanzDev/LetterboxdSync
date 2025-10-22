"""Lists page."""
import reflex as rx
from ..states.lists_state import ListsState
from ..states.auth_state import AuthState
from ..states.list_detail_state import ListDetailState
from ..states.sync_state import SyncState
from ..components.navbar import navbar


def lists_page() -> rx.Component:
    """Lists page component."""
    return rx.cond(
        AuthState.is_authenticated,
        # Authenticated content
        rx.fragment(
            navbar(),
            rx.center(
                rx.container(
                    rx.vstack(
                        rx.hstack(
                            rx.heading("My Letterboxd Lists", size="7"),
                            rx.button(
                                rx.cond(
                                    ListsState.is_loading,
                                    rx.hstack(
                                        rx.spinner(size="2"),
                                        rx.text("Loading..."),
                                        spacing="2",
                                    ),
                                    rx.hstack(
                                        rx.icon("refresh-cw"),
                                        rx.text("Refresh"),
                                        spacing="2",
                                    ),
                                ),
                                on_click=ListsState.fetch_user_lists,
                                disabled=ListsState.is_loading,
                                variant="soft",
                            ),
                            justify="between",
                            align="center",
                            width="100%",
                        ),

                        rx.cond(
                            ListsState.user_lists.length() > 0,
                            rx.grid(
                                rx.foreach(
                                    ListsState.user_lists,
                                    lambda list_item: rx.card(
                                        rx.vstack(
                                            rx.hstack(
                                                rx.heading(list_item["name"], size="4"),
                                                rx.badge(
                                                    f"🎬 {list_item['film_count']}",
                                                    variant="soft",
                                                    size="2",
                                                ),
                                                justify="between",
                                                align="center",
                                                width="100%",
                                            ),
                                            rx.cond(
                                                list_item["description"] != "",
                                                rx.text(
                                                    list_item["description"],
                                                    size="2",
                                                    color_scheme="gray",
                                                    max_height="3em",
                                                    overflow="hidden",
                                                ),
                                                ),

                                            rx.hstack(
                                                rx.button(
                                                    "View List",
                                                    on_click=lambda: [
                                                        ListDetailState.set_list_info(
                                                            list_item["id"],
                                                            list_item["name"],
                                                            list_item["url"],
                                                            list_item["film_count"]
                                                        ),
                                                        rx.redirect(f"/list/{list_item['id']}")
                                                    ],
                                                    size="2",
                                                    flex="1",
                                                ),

                                                # Conditional Share/Manage button
                                                rx.cond(
                                                    SyncState.shared_list_status.get(list_item["url"], False),
                                                    # Manage button (list is already shared)
                                                    rx.button(
                                                        rx.cond(
                                                            SyncState.sync_loading,
                                                            rx.spinner(size="2"),
                                                            rx.hstack(
                                                                rx.icon("settings"),
                                                                rx.text("Manage"),
                                                                spacing="1",
                                                            ),
                                                        ),
                                                        on_click=lambda: SyncState.navigate_to_manage(list_item["url"]),
                                                        disabled=SyncState.sync_loading,
                                                        size="2",
                                                        variant="outline",
                                                        color_scheme="green",
                                                        flex="1",
                                                    ),
                                                    # Share button (list is not shared)
                                                    rx.button(
                                                        rx.cond(
                                                            SyncState.sync_loading,
                                                            rx.spinner(size="2"),
                                                            rx.hstack(
                                                                rx.icon("share"),
                                                                rx.text("Share"),
                                                                spacing="1",
                                                            ),
                                                        ),
                                                        on_click=lambda: SyncState.share_list(
                                                            list_item["id"],
                                                            list_item["name"],
                                                            list_item["url"]
                                                        ),
                                                        disabled=SyncState.sync_loading,
                                                        size="2",
                                                        variant="outline",
                                                        color_scheme="blue",
                                                        flex="1",
                                                    ),
                                                ),

                                                spacing="2",
                                                width="100%",
                                            ),
                                            spacing="3",
                                            align="start",
                                            width="100%",
                                        ),
                                        width="100%",
                                    ),
                                ),
                                columns=rx.breakpoints(
                                    initial="1",
                                    sm="2",
                                    md="2",
                                    lg="2",
                                ),
                                width="100%",
                            ),
                            rx.center(
                                rx.vstack(
                                    rx.icon("inbox", size=64, color="gray"),
                                    rx.text(
                                        "No lists found",
                                        size="4",
                                        color_scheme="gray",
                                    ),
                                    spacing="3",
                                ),
                                min_height="40vh",
                            ),
                            ),

                        rx.cond(
                            ListsState.error_message != "",
                            rx.callout(
                                ListsState.error_message,
                                icon="triangle_alert",
                                color_scheme="red",
                            ),
                            ),

                        rx.cond(
                            ListsState.success_message != "",
                            rx.callout(
                                ListsState.success_message,
                                icon="check",
                                color_scheme="green",
                            ),
                            ),

                        spacing="5",
                        padding_y="2rem",
                    ),
                    max_width="1400px",
                    on_mount=ListsState.on_load,
                ),
            )
        ),
        # Fallback while checking authentication or redirecting
        rx.center(
            rx.vstack(
                rx.spinner(size="3"),
                rx.text("Checking authentication...", size="3"),
                spacing="3",
            ),
            min_height="85vh",
        ),
    )