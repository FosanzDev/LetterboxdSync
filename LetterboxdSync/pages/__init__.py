"""Pages module."""
from .login import login_page
from .dashboard import dashboard_page
from .lists import lists_page
from .list_detail import list_detail_page
from .sync import sync_page
from .manage import manage_sync_page

__all__ = ["login_page", "dashboard_page", "lists_page", "list_detail_page", "sync_page", "manage_sync_page"]