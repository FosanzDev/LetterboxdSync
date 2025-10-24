"""Login page."""
import reflex as rx
from ..states.auth_state import AuthState
from ..components.navbar import navbar


def login_page() -> rx.Component:
    """Login page component."""
    return rx.fragment(
        navbar(),
        rx.container(
            rx.center(
                rx.card(
                    rx.vstack(
                        rx.heading("Welcome to Letterboxd Sync", size="7"),
                        rx.text(
                            "Login with your Letterboxd credentials",
                            size="3",
                            color_scheme="gray",
                        ),

                        rx.vstack(
                            rx.input(
                                placeholder="Letterboxd Username",
                                value=AuthState.username,
                                on_change=AuthState.set_username,
                                size="3",
                                width="100%"
                            ),
                            rx.input(
                                placeholder="Password",
                                type="password",
                                value=AuthState.password,
                                on_change=AuthState.set_password,
                                size="3",
                                width="100%"
                            ),
                            rx.button(
                                rx.cond(
                                    AuthState.auth_loading,
                                    rx.hstack(
                                        rx.spinner(size="2"),
                                        rx.text("Connecting..."),
                                        spacing="2",
                                    ),
                                    "Login with Letterboxd"
                                ),
                                on_click=AuthState.login,
                                disabled=AuthState.auth_loading,
                                width="100%",
                                size="3",
                            ),
                            spacing="3",
                            width="100%",
                        ),

                        rx.cond(
                            AuthState.error_message != "",
                            rx.hstack(
                                rx.callout(
                                    AuthState.error_message,
                                    icon="triangle_alert",
                                    color_scheme="red",
                                ),
                                rx.button(
                                    rx.icon("x"),
                                    on_click=AuthState.clear_all_messages,
                                    variant="ghost",
                                    size="1",
                                ),
                                justify="between",
                                align="center",
                                width="100%",
                            ),
                            ),

                        rx.cond(
                            AuthState.success_message != "",
                            rx.hstack(
                                rx.callout(
                                    AuthState.success_message,
                                    icon="check",
                                    color_scheme="green",
                                ),
                                rx.button(
                                    rx.icon("x"),
                                    on_click=AuthState.clear_all_messages,
                                    variant="ghost",
                                    size="1",
                                ),
                                justify="between",
                                align="center",
                                width="100%",
                            ),
                            ),

                        rx.divider(),

                        rx.text(
                            "Your credentials are stored securely and encrypted.",
                            size="1",
                            color_scheme="gray",
                        ),

                        spacing="4",
                        width="100%",
                    ),
                    max_width="450px",
                    width="100%",
                ),
                min_height="80vh",
            ),
            padding="2rem",
        ),
        on_mount=[
            AuthState.on_load,
            AuthState.check_login_redirect,
            AuthState.set_loading(False)
        ]
    )