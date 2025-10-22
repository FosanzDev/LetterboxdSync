import requests
import json
from bs4 import BeautifulSoup
import urllib3
import time
import random

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LetterboxdScraper:
    def __init__(self, username, password, list_url, verify_ssl=False):
        """
        Initialize the Letterboxd scraper.

        Args:
            username (str): Letterboxd username
            password (str): Letterboxd password
            list_url (str): Full URL of the list to scrape (e.g., https://letterboxd.com/user/list/name/)
            verify_ssl (bool): Whether to verify SSL certificates (default: False)
        """
        self.session = requests.Session()
        self.username = username
        self.password = password
        self.list_url = list_url.rstrip('/')  # Remove trailing slash if present
        self.verify_ssl = verify_ssl

    def login(self):
        """Login to Letterboxd with rate limiting"""
        print("[*] Fetching homepage to get CSRF token...")

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        max_retries = 3
        base_delay = 5  # Start with 5 seconds

        for attempt in range(max_retries):
            try:
                # Add random delay to avoid hitting rate limits
                if attempt > 0:
                    delay = base_delay * (2 ** attempt) + random.uniform(1, 3)
                    print(f"[*] Rate limited, waiting {delay:.1f} seconds before retry {attempt + 1}/{max_retries}...")
                    time.sleep(delay)

                response = self.session.get(
                    "https://letterboxd.com/",
                    headers=headers,
                    verify=self.verify_ssl
                )

                if response.status_code == 429:
                    print(f"[-] Rate limited (429) on attempt {attempt + 1}")
                    continue

            except Exception as e:
                print(f"[-] Failed to fetch homepage: {e}")
                if attempt == max_retries - 1:
                    return False
                continue

            csrf_token = self.session.cookies.get("com.xk72.webparts.csrf")
            if not csrf_token:
                print("[-] Could not extract CSRF token")
                if attempt == max_retries - 1:
                    return False
                continue

            print(f"[+] CSRF token: {csrf_token}")

            login_data = {
                "__csrf": csrf_token,
                "authenticationCode": "",
                "username": self.username,
                "password": self.password
            }

            login_headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://letterboxd.com",
                "Referer": "https://letterboxd.com/",
            }

            print("[*] Sending login request...")
            try:
                # Add small delay before login request
                time.sleep(random.uniform(1, 2))

                login_response = self.session.post(
                    "https://letterboxd.com/user/login.do",
                    data=login_data,
                    headers=login_headers,
                    verify=self.verify_ssl
                )

                if login_response.status_code == 429:
                    print(f"[-] Login rate limited (429) on attempt {attempt + 1}")
                    continue

            except Exception as e:
                print(f"[-] Failed to login: {e}")
                if attempt == max_retries - 1:
                    return False
                continue

            if login_response.status_code == 200:
                try:
                    response_json = login_response.json()
                    result = response_json.get("result")

                    if result == "success":
                        print("[+] Login successful!")
                        return True
                    elif result == "error":
                        # Login failed - check if it's a credential error or retryable error
                        messages = response_json.get('messages', [])
                        error_message = messages[0] if messages else "Unknown error"
                        print(f"[-] Login failed: {messages}")

                        # Check if this is a credential/authentication error (don't retry these)
                        normalized_message = error_message.lower().replace("'", "'").replace("'", "'")

                        # Phrases that indicate credential/auth issues (non-retryable)
                        auth_error_phrases = [
                            "credentials don't match",
                            "credentials do not match",
                            "incorrect",
                            "invalid",
                            "wrong password",
                            "human error",  # Letterboxd's specific phrasing
                            "authentication failed"
                        ]

                        is_auth_error = any(phrase in normalized_message for phrase in auth_error_phrases)

                        if is_auth_error:
                            print("[-] Authentication error detected - not retrying")
                            return False

                        # For other errors (could be rate limiting, server issues, etc.), retry
                        print(f"[-] Non-authentication error, will retry if attempts remain")
                        if attempt == max_retries - 1:
                            return False
                        continue
                    else:
                        # Unexpected result value
                        print(f"[-] Unexpected result value: {result}")
                        if attempt == max_retries - 1:
                            return False
                        continue

                except json.JSONDecodeError:
                    print("[-] Could not parse login response")
                    if attempt == max_retries - 1:
                        return False
            else:
                print(f"[-] Login failed with status {login_response.status_code}")
                if attempt == max_retries - 1:
                    return False

        print("[-] All login attempts failed")
        return False

    def get_all_movies(self):
        """Fetch and parse all movies from all pages"""
        all_movies = []
        page = 1

        while True:
            if page == 1:
                url = f"{self.list_url}/"
            else:
                url = f"{self.list_url}/page/{page}/"

            print(f"\n[*] Fetching page {page}...")

            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Referer": self.list_url,
            }

            try:
                response = self.session.get(url, headers=headers, verify=self.verify_ssl)
            except Exception as e:
                print(f"[-] Failed to fetch page {page}: {e}")
                break

            if response.status_code != 200:
                print(f"[-] Failed to fetch page {page}. Status: {response.status_code}")
                break

            movies_on_page = self.parse_movies(response.text)

            if not movies_on_page:
                print(f"[*] No movies found on page {page}. End of list.")
                break

            all_movies.extend(movies_on_page)
            print(f"[+] Found {len(movies_on_page)} movies on page {page}")

            if not self.has_next_page(response.text):
                print("[*] No next page found.")
                break

            page += 1
            time.sleep(1)

        return all_movies

    def get_movies_by_page(self, page=1):
        """
        Fetch movies from a specific Letterboxd page (server-side pagination).

        Args:
            page (int): Page number (1-based)

        Returns:
            list: Movies from that specific page
        """
        if page == 1:
            url = f"{self.list_url}/"
        else:
            url = f"{self.list_url}/page/{page}/"

        print(f"\n[*] Fetching page {page}...")

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Referer": self.list_url,
        }

        try:
            response = self.session.get(url, headers=headers, verify=self.verify_ssl)
        except Exception as e:
            print(f"[-] Failed to fetch page {page}: {e}")
            return []

        if response.status_code != 200:
            print(f"[-] Failed to fetch page {page}. Status: {response.status_code}")
            return []

        movies_on_page = self.parse_movies(response.text)

        return movies_on_page

    def has_next_page(self, html):
        """Check if there's a next page button"""
        soup = BeautifulSoup(html, 'html.parser')
        next_button = soup.find('a', class_='next')
        return next_button is not None

    def parse_movies(self, html):
        """Parse movie data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        movies = []

        poster_items = soup.find_all('li', class_='posteritem')

        for item in poster_items:
            try:
                react_comp = item.find('div', class_='react-component')

                if not react_comp:
                    continue

                movie_data = {
                    'name': react_comp.get('data-item-name'),
                    'slug': react_comp.get('data-item-slug'),
                    'film_id': react_comp.get('data-film-id'),
                    'link': react_comp.get('data-item-link'),
                    'rating': item.get('data-owner-rating'),
                    'poster_url': react_comp.get('data-poster-url'),
                    'object_id': item.get('data-object-id')
                }

                movies.append(movie_data)
                print(f"  ✓ {movie_data['name']} (Rating: {movie_data['rating']}/10)")

            except Exception as e:
                print(f"  [!] Error parsing movie: {e}")
                continue

        return movies

    def display_movies(self, movies):
        """Display movies in a formatted table"""
        print("\n" + "=" * 80)
        print(f"{'Movie':<40} {'Rating':<10} {'Film ID':<10}")
        print("=" * 80)

        for movie in movies:
            name = movie['name'][:38] if movie['name'] else "Unknown"
            rating = f"{movie['rating']}/10" if movie['rating'] else "—"
            film_id = movie['film_id'] or "—"
            print(f"{name:<40} {rating:<10} {film_id:<10}")

        print("=" * 80)
        print(f"Total: {len(movies)} movies")

    def add_movie(self, film_id, list_id):
        """
        Add a movie to a Letterboxd list.

        Args:
            film_id (str): The Letterboxd film ID
            list_id (str): The Letterboxd list ID

        Returns:
            bool: True if successful, False otherwise
        """
        csrf_token = self.session.cookies.get("com.xk72.webparts.csrf")
        if not csrf_token:
            print("[-] No CSRF token available. Please login first.")
            return False

        data = {
            "__csrf": csrf_token,
            "filmId": film_id,
            "filmListId": list_id
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://letterboxd.com",
            "Referer": f"https://letterboxd.com/",
        }

        try:
            response = self.session.post(
                "https://letterboxd.com/s/add-film-to-list",
                data=data,
                headers=headers,
                verify=self.verify_ssl
            )

            if response.status_code == 200:
                try:
                    response_json = response.json()
                    if response_json.get("result") == True:
                        messages = response_json.get("messages", [])
                        if messages:
                            # Clean HTML tags from message
                            import re
                            clean_message = re.sub('<[^<]+?>', '', messages[0])
                            print(f"[+] {clean_message}")
                        return True
                    else:
                        error_codes = response_json.get("errorCodes", [])
                        print(f"[-] Failed to add movie: {error_codes}")
                        return False
                except json.JSONDecodeError:
                    print("[-] Could not parse response")
                    return False
            else:
                print(f"[-] Request failed with status {response.status_code}")
                return False

        except Exception as e:
            print(f"[-] Failed to add movie: {e}")
            return False

    def remove_movie(self, film_id, username=None, list_name=None):
        """
        Remove a movie from a Letterboxd list.

        Args:
            film_id (str): The Letterboxd film ID
            username (str, optional): Username (defaults to self.username)
            list_name (str, optional): List name extracted from self.list_url if not provided

        Returns:
            bool: True if successful, False otherwise
        """
        csrf_token = self.session.cookies.get("com.xk72.webparts.csrf")
        if not csrf_token:
            print("[-] No CSRF token available. Please login first.")
            return False

        # Use provided username or fall back to self.username
        if username is None:
            username = self.username

        # Extract list name from self.list_url if not provided
        if list_name is None:
            # Extract from URL like https://letterboxd.com/fosanz/list/pendienteeees
            try:
                list_name = self.list_url.split('/list/')[-1].split('/')[0]
            except (IndexError, AttributeError):
                print("[-] Could not extract list name from URL")
                return False

        data = {
            "__csrf": csrf_token,
            "filmId": film_id
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://letterboxd.com",
            "Referer": f"https://letterboxd.com/{username}/list/{list_name}/",
        }

        try:
            response = self.session.post(
                f"https://letterboxd.com/{username}/list/{list_name}/remove-film/",
                data=data,
                headers=headers,
                verify=self.verify_ssl
            )

            if response.status_code == 200:
                try:
                    response_json = response.json()
                    if response_json.get("result") == True:
                        messages = response_json.get("messages", [])
                        if messages:
                            # Clean HTML tags from message
                            import re
                            clean_message = re.sub('<[^<]+?>', '', messages[0])
                            print(f"[+] {clean_message}")
                        return True
                    else:
                        error_codes = response_json.get("errorCodes", [])
                        print(f"[-] Failed to remove movie: {error_codes}")
                        return False
                except json.JSONDecodeError:
                    print("[-] Could not parse response")
                    return False
            else:
                print(f"[-] Request failed with status {response.status_code}")
                return False

        except Exception as e:
            print(f"[-] Failed to remove movie: {e}")
            return False

    def get_all_lists(self, target_username=None):
        """
        Fetch and parse all lists from a user's profile.

        Args:
            target_username (str, optional): Username to fetch lists from (defaults to self.username)

        Returns:
            list: List of dictionaries containing list information
        """
        if target_username is None:
            target_username = self.username

        all_lists = []
        page = 1

        while True:
            if page == 1:
                url = f"https://letterboxd.com/{target_username}/lists/"
            else:
                url = f"https://letterboxd.com/{target_username}/lists/page/{page}/"

            print(f"\n[*] Fetching lists page {page}...")

            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Referer": f"https://letterboxd.com/{target_username}/lists/",
            }

            try:
                response = self.session.get(url, headers=headers, verify=self.verify_ssl)
            except Exception as e:
                print(f"[-] Failed to fetch page {page}: {e}")
                break

            if response.status_code != 200:
                print(f"[-] Failed to fetch page {page}. Status: {response.status_code}")
                break

            lists_on_page = self.parse_lists(response.text, target_username)

            if not lists_on_page:
                print(f"[*] No lists found on page {page}. End of list.")
                break

            all_lists.extend(lists_on_page)
            print(f"[+] Found {len(lists_on_page)} lists on page {page}")

            if not self.has_next_page(response.text):
                print("[*] No next page found.")
                break

            page += 1
            time.sleep(1)

        return all_lists

    def parse_lists(self, html, username):
        """Parse list data from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        lists = []

        # Find all list articles
        list_articles = soup.find_all('article', class_='list-summary')

        for article in list_articles:
            try:
                # Get list ID
                list_id = article.get('data-film-list-id')

                # Get list name and URL
                name_link = article.find('h2', class_='name').find('a') if article.find('h2', class_='name') else None
                if not name_link:
                    continue

                list_name = name_link.get_text(strip=True)
                list_url = name_link.get('href')

                # Extract list slug from URL
                list_slug = list_url.split('/list/')[-1].rstrip('/') if '/list/' in list_url else ""

                # Get film count
                film_count = "0"
                reactions_strip = article.find('div', class_='content-reactions-strip')
                if reactions_strip:
                    value_span = reactions_strip.find('span', class_='value')
                    if value_span:
                        film_count = value_span.get_text(strip=True).replace('films', '').replace('film', '').replace('\xa0', ' ').strip()

                # Get description
                description = ""
                notes_div = article.find('div', class_='notes')
                if notes_div:
                    # Get text content, removing HTML tags
                    description = notes_div.get_text(strip=True)
                    # Limit description length
                    if len(description) > 150:
                        description = description[:147] + "..."

                list_data = {
                    'id': list_id,
                    'name': list_name,
                    'slug': list_slug,
                    'url': f"https://letterboxd.com{list_url}",
                    'film_count': film_count,
                    'description': description,
                    'owner': username
                }

                lists.append(list_data)
                print(f"  ✓ {list_data['name']} ({list_data['film_count']} films)")

            except Exception as e:
                print(f"  [!] Error parsing list: {e}")
                continue

        return lists

    def display_lists(self, lists):
        """Display lists in a formatted table"""
        print("\n" + "=" * 100)
        print(f"{'List Name':<40} {'Films':<10} {'ID':<12} {'Description':<38}")
        print("=" * 100)

        for list_item in lists:
            name = list_item['name'][:38] if list_item['name'] else "Unknown"
            film_count = list_item['film_count'] or "—"
            list_id = list_item['id'] or "—"
            description = list_item['description'][:36] if list_item['description'] else "—"
            print(f"{name:<40} {film_count:<10} {list_id:<12} {description:<38}")

        print("=" * 100)
        print(f"Total: {len(lists)} lists")
