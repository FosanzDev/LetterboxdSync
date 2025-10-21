"""List detail page."""
import reflex as rx
from ..states.auth_state import AuthState
from ..states.list_detail_state import ListDetailState
from ..components.navbar import navbar


def movie_list_item(movie) -> rx.Component:
    """Individual movie list item component."""
    return rx.card(
        rx.vstack(
            # Movie title at the top
            rx.heading(
                movie["name"],
                size="4",
                width="100%",
                margin_bottom="0.5rem",
            ),

            # Bottom section with year on left and rating on right
            rx.hstack(
                # Year badge on the left
                rx.hstack(
                    rx.cond(
                        movie["year"] != "",
                        rx.badge(
                            movie["year"],
                            variant="soft",
                            color_scheme="blue",
                        ),
                        ),
                    spacing="2",
                ),

                # Spacer to push rating to the right
                rx.spacer(),

                # Rating badge on the right
                rx.hstack(
                    rx.cond(
                        (movie["rating"] != "") & (movie["rating"] != "None"),
                        rx.badge(
                            f"⭐ {movie['rating']}/10",
                            variant="soft",
                            color_scheme="yellow",
                        ),
                        ),
                    spacing="2",
                ),

                width="100%",
                align="center",
                justify="between",
            ),

            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
        cursor="pointer",
        padding="1.5rem",
    )


def pagination_controls() -> rx.Component:
    """Pagination controls component."""
    return rx.hstack(
        rx.button(
            rx.icon("chevron-left"),
            on_click=ListDetailState.prev_page,
            disabled=rx.cond(
                ListDetailState.current_page == 1,
                True,
                ListDetailState.is_loading,
                ),
            variant="soft",
        ),
        rx.text(
            f"Page {ListDetailState.current_page} of {ListDetailState.total_pages}",
            size="3",
        ),
        rx.button(
            rx.icon("chevron-right"),
            on_click=ListDetailState.next_page,
            disabled=rx.cond(
                ~ListDetailState.has_more,
                True,
                ListDetailState.is_loading,
            ),
            variant="soft",
        ),
        spacing="3",
        align="center",
        justify="center",
        width="100%",
    )


def list_detail_page() -> rx.Component:
    """List detail page component."""
    return rx.cond(
        AuthState.is_authenticated,
        rx.fragment(
            navbar(),
            rx.center(  # Center the entire container on the page
                rx.container(
                    rx.vstack(
                        # Header with back button and title
                        rx.vstack(
                            rx.hstack(
                                rx.link(
                                    rx.button(
                                        rx.icon("arrow-left"),
                                        "Back to Lists",
                                        variant="soft",
                                    ),
                                    href="/lists",
                                ),
                                width="100%",
                            ),
                            rx.heading(
                                ListDetailState.list_name,
                                size="7",
                                text_align="center",
                                width="100%",
                            ),
                            spacing="3",
                            width="100%",
                        ),

                        rx.cond(
                            ListDetailState.is_loading & (ListDetailState.current_page == 1),
                            rx.center(
                                rx.vstack(
                                    rx.spinner(size="3"),
                                    rx.text("Loading movies...", size="3"),
                                    spacing="3",
                                ),
                                min_height="40vh",
                                width="100%",
                            ),
                            rx.cond(
                                ListDetailState.movies.length() > 0,
                                rx.vstack(
                                    # Movies list
                                    rx.vstack(
                                        rx.foreach(
                                            ListDetailState.movies,
                                            movie_list_item,
                                        ),
                                        spacing="2",
                                        width="100%",
                                    ),

                                    # Pagination controls
                                    pagination_controls(),

                                    # Results count
                                    rx.text(
                                        f"Showing {ListDetailState.movies.length()} of {ListDetailState.total_count} movies",
                                        size="2",
                                        color_scheme="gray",
                                        text_align="center",
                                        width="100%",
                                    ),

                                    spacing="4",
                                    width="100%",
                                ),
                                rx.center(
                                    rx.vstack(
                                        rx.icon("film", size=64, color="gray"),
                                        rx.text("No movies found", size="4", color_scheme="gray"),
                                        spacing="3",
                                    ),
                                    min_height="40vh",
                                    width="100%",
                                ),
                                ),
                            ),

                        rx.cond(
                            ListDetailState.error_message != "",
                            rx.callout(
                                ListDetailState.error_message,
                                icon="triangle_alert",
                                color_scheme="red",
                            ),
                            ),

                        spacing="5",
                        width="100%",
                        padding_y="2rem",
                    ),
                    max_width="800px",
                    width="100%",
                    padding_x=rx.breakpoints(initial="1rem", sm="2rem"),
                ),
                width="100%",  # Make the center container take full width
            ),
        ),
        rx.center(
            rx.vstack(
                rx.spinner(size="3"),
                rx.text("Checking authentication...", size="3"),
                spacing="3",
            ),
            min_height="85vh",
        ),
    )