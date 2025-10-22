import reflex as rx
from db.db_config import db_config

config = rx.Config(
    app_name="LetterboxdSync",
    db_url=f"sqlite:///{db_config.get_sync_db_path()}",
    api_url="https://lbsync.fosanz.dev",
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)