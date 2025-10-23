"""Main application file."""
import reflex as rx
from .pages.login import login_page
from .pages.dashboard import dashboard_page
from .pages.lists import lists_page
from .pages.list_detail import list_detail_page
from .pages.sync import sync_page
from .pages.manage import manage_sync_page
from .states.manage_sync_state import ManageSyncState
from .states.sync_state import SyncState
from .states import ListsState
from .states.auth_state import AuthState
from .states.list_detail_state import ListDetailState


def index() -> rx.Component:
    """Index page."""
    return rx.fragment(
        rx.container(
            rx.center(
                rx.vstack(
                    rx.heading("📽️ Letterboxd Sync", size="9"),
                    rx.text(
                        "Sync movies between Letterboxd lists",
                        size="5",
                        color_scheme="gray",
                    ),
                    rx.link(
                        rx.button("Get Started", size="4"),
                        href="/login",
                    ),
                    spacing="5",
                ),
                min_height="85vh",
            ),
        ),
    )


# Create app
app = rx.App(
    stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap",
    ]
)

# Add pages - Note: Protected pages now use on_load for auth checking
app.add_page(index, route="/")
app.add_page(login_page, route="/login", on_load=AuthState.check_login_redirect)
app.add_page(dashboard_page, route="/dashboard", on_load=AuthState.on_load)
app.add_page(lists_page, route="/lists", on_load=[AuthState.on_load, ListsState.on_load, SyncState.refresh_shared_status])
app.add_page(list_detail_page, route="/list/[list_id]", on_load=ListDetailState.on_load)
app.add_page(sync_page, route="/sync", on_load=[AuthState.on_load, SyncState.load_sync_groups])
app.add_page(manage_sync_page, route="/manage-sync/[sync_code]", on_load=ManageSyncState.on_load)