import reflex as rx

config = rx.Config(
    app_name="LetterboxdSync",
    db_url="sqlite:///letterboxd_sync.db",
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)