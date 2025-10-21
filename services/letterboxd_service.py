"""Service for interacting with Letterboxd"""
import re
from bs4 import BeautifulSoup
from typing import Optional, List, Set
from LetterboxdScraper import LetterboxdScraper
from models.sync_models import ListInfo, GroupMember
import logging

logger = logging.getLogger(__name__)


class LetterboxdService:
    """Service for all Letterboxd operations"""

    def __init__(self):
        self.scrapers = {}  # Cache scrapers to maintain sessions

    async def get_scraper_for_member(self, member: GroupMember) -> Optional[LetterboxdScraper]:
        """Get or create a scraper for a member, maintaining login session"""
        member_id = member.id

        if member_id not in self.scrapers:
            scraper = LetterboxdScraper(
                username=member.username,
                password=member.password,
                list_url=member.list_url
            )

            # Login
            if not scraper.login():
                logger.error(f"Failed to login for member {member.display_name}")
                return None

            self.scrapers[member_id] = scraper
            logger.info(f"Created and logged in scraper for {member.display_name}")

        return self.scrapers[member_id]

    async def get_user_lists(self, username: str, password: str) -> List[ListInfo]:
        """Get all lists for a user"""
        scraper = LetterboxdScraper(username, password, "https://letterboxd.com")

        if not scraper.login():
            return []

        lists = scraper.get_all_lists(username)

        return [
            ListInfo(
                id=lst.get('id', ''),
                name=lst.get('name', ''),
                slug=lst.get('slug', ''),
                url=lst.get('url', ''),
                film_count=lst.get('film_count', '0'),
                description=lst.get('description', ''),
                owner=lst.get('owner', username)
            )
            for lst in lists
        ]

    async def get_movies_from_list(self, member: GroupMember) -> Set[str]:
        """Fetch current movies from a member's Letterboxd list"""
        scraper = await self.get_scraper_for_member(member)
        if not scraper:
            return set()

        try:
            movies = scraper.get_all_movies()
            film_ids = {movie['film_id'] for movie in movies if movie['film_id']}
            logger.info(f"Fetched {len(film_ids)} movies from {member.display_name}'s list")
            return film_ids
        except Exception as e:
            logger.error(f"Error fetching movies for {member.display_name}: {e}")
            # Remove failed scraper from cache to force re-login next time
            if member.id in self.scrapers:
                del self.scrapers[member.id]
            return set()

    def extract_list_id_from_page(self, scraper: LetterboxdScraper, list_url: str) -> Optional[str]:
        """Extract list ID by scraping the list page"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }

            response = scraper.session.get(list_url, headers=headers, verify=scraper.verify_ssl)
            if response.status_code != 200:
                logger.error(f"Failed to fetch list page, status: {response.status_code}")
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Method 1: Look for report link pattern
            report_span = soup.find('span', class_='report-link')
            if report_span:
                data_report_url = report_span.get('data-report-url')
                if data_report_url:
                    match = re.search(r'/ajax/filmlist:(\d+)/', data_report_url)
                    if match:
                        list_id = match.group(1)
                        logger.info(f"Extracted list ID {list_id} from report URL")
                        return list_id

            # Method 2: Look for popmenu ID pattern
            popmenu_div = soup.find('div', id=re.compile(r'report-member-.*-list-\d+'))
            if popmenu_div:
                div_id = popmenu_div.get('id')
                match = re.search(r'report-member-.*-list-(\d+)', div_id)
                if match:
                    list_id = match.group(1)
                    logger.info(f"Extracted list ID {list_id} from popmenu div ID")
                    return list_id

            # Method 3: Look for data-popmenu-id in links
            popmenu_link = soup.find('a', attrs={'data-popmenu-id': re.compile(r'report-member-.*-list-\d+')})
            if popmenu_link:
                popmenu_id = popmenu_link.get('data-popmenu-id')
                match = re.search(r'report-member-.*-list-(\d+)', popmenu_id)
                if match:
                    list_id = match.group(1)
                    logger.info(f"Extracted list ID {list_id} from popmenu link")
                    return list_id

            logger.warning(f"Could not extract list ID from {list_url}")
            return None

        except Exception as e:
            logger.error(f"Error extracting list ID from {list_url}: {e}")
            return None

    def get_list_info_from_url(self, list_url: str) -> dict:
        """Extract username and list slug from URL"""
        match = re.match(r'https://letterboxd\.com/([^/]+)/list/([^/]+)/?', list_url)
        if match:
            return {
                'username': match.group(1),
                'list_slug': match.group(2)
            }
        return {}

    async def get_list_id_for_member(self, member: GroupMember) -> Optional[str]:
        """Get list ID for a member"""
        scraper = await self.get_scraper_for_member(member)
        if not scraper:
            return None

        return self.extract_list_id_from_page(scraper, member.list_url)

    async def add_movie_to_list(self, member: GroupMember, film_id: str, list_id: str) -> bool:
        """Add a movie to a member's list"""
        scraper = await self.get_scraper_for_member(member)
        if not scraper:
            return False

        return scraper.add_movie(film_id, list_id)

    async def remove_movie_from_list(self, member: GroupMember, film_id: str) -> bool:
        """Remove a movie from a member's list"""
        scraper = await self.get_scraper_for_member(member)
        if not scraper:
            return False

        return scraper.remove_movie(film_id)

    def clear_scraper_cache(self):
        """Clear all cached scrapers"""
        self.scrapers.clear()