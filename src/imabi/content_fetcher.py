# ♥♥─── Imabi Content Fetcher ───────────────────────────
from __future__ import annotations

from bs4 import Tag, BeautifulSoup
import requests


class ContentFetcher:
    """Handles fetching content from URLs."""

    def __init__(self, session: requests.Session | None = None) -> None:
        """Initialize the fetcher with a requests session."""
        self.session = session or requests.Session()

    def fetch_content(self, url: str) -> tuple[bytes, str]:
        """Fetch content and return it with its base URI."""
        response = self.session.get(url)
        response.raise_for_status()
        return response.content, url


class HTMLCleaner:
    """Cleans and preprocesses HTML content."""

    UNWANTED_SELECTORS = ["div.sharedaddy", "nav.entry-breadcrumbs", "div.wp-block-buttons"]
    URL_REPLACEMENTS: dict[str, str] = {
        "https://www.imabi.net/timei.htm": "https://imabi.org/counters-iii-time-part-i-%e6%97%a5-%e9%80%b1%e9%96%93-%e6%9c%88-%e5%b9%b4-etc/",
        "https://www.imabi.net/theseasons.htm": "https://imabi.org/the-seasons%e3%80%80%e6%98%a5%e5%a4%8f%e7%a7%8b%e5%86%ac/",
        "https://www.imabi.net/the-affix-gu": "https://imabi.org/the-verbal-affix-%ef%bd%9e%e3%81%90-%ef%bd%9e%e3%82%89%e3%81%90%e3%83%bb%e3%82%84%e3%81%90/",
        "https://www.imabi.net/nivskara.htm": "https://imabi.org/the-particle-%e3%81%8b%e3%82%89/",
        "https://www.imabi.net/l55theparticlenagara.htm": "https://imabi.org/the-particles-%e3%81%a4%e3%81%a4-%e3%81%aa%e3%81%8c%e3%82%89/",
        "https://www.imabi.net/l279yotsugana.htm": "https://imabi.org/yotsugana/",
        "https://www.imabi.net/l216nounspronouns.htm#825855643": "https://imabi.org/reflexive-pronouns/",
        "https://www.imabi.net/l171kimigayoiroha.htm": "https://imabi.org/the-%e5%90%9b%e3%81%8c%e4%bb%a3-%e3%81%84%e3%82%8d%e3%81%af/",
        "https://www.imabi.net/l12regularverbs.htm": "https://imabi.org/class-regular-verbs-i/",
        "https://www.imabi.net/l116numbersviicountersii.htm": "https://imabi.org/counters-vi/",
        "https://www.imabi.net/holidays": "https://imabi.org/holidays%e3%80%80%e6%97%a5%e6%9c%ac%e3%81%ae%e7%a5%9d%e6%97%a5/",
        "https://www.imabi.net/hatsuon.htm": "https://imabi.org/hatsuon/",
        "https://www.imabi.net/funeral.htm": "https://imabi.org/japanese-ceremony-customs-%e5%86%a0%e5%a9%9a%e8%91%ac%e7%a5%ad/",
        "https://www.imabi.net/dailyexpressionsii.htm": "https://imabi.org/the-particle-ka-%e3%81%8b-i-basic-questions/",
        "https://www.imabi.net/classicaladjectivesii.htm": "https://imabi.org/classical-adjectives-ii/",
        "https://www.imabi.net/barecoveredforms.htm": "https://imabi.org/bare-covered-forms/",
        "https://www.imabi.net/adjectivesii.htm": "https://imabi.org/adjectival-nouns-i%e3%80%80%e5%bd%a2%e5%ae%b9%e5%8b%95%e8%a9%9e%e2%91%a0/",
        "https://imabi.org/wp-admin/post.php?post=221&amp;action=edit#cc836554-5736-4e48-aef9-2765fc98fcd9-link": "",
    }

    def clean_structure(self, content_div: Tag) -> Tag:
        """Remove unwanted elements and clean HTML structure."""
        self._remove_unwanted_elements(content_div)
        self._fix_br_tags_in_links(content_div)
        self._remove_empty_links(content_div)
        return content_div

    def _remove_unwanted_elements(self, content_div: Tag) -> None:
        """Remove unwanted HTML elements based on CSS selectors."""
        for selector in self.UNWANTED_SELECTORS:
            for element in content_div.select(selector):
                element.decompose()

    def _fix_br_tags_in_links(self, content_div: Tag) -> None:
        """Move <br> tags outside of their parent <a> tags."""
        for a_tag in content_div.find_all("a"):
            for br_tag in a_tag.find_all("br"):
                new_br = BeautifulSoup("", "html.parser").new_tag("br")
                a_tag.insert_after(new_br)
                br_tag.decompose()

    def _remove_empty_links(self, content_div: Tag) -> None:
        """Remove empty or whitespace-only <a> tags."""
        for a_tag in content_div.find_all("a"):
            if not a_tag.get_text(strip=True):
                a_tag.decompose()

    def _replace_links(self, content_div: Tag) -> None:
        for a_tag in content_div.find_all("a"):
            href = a_tag.get("href")
            if href is None:
                continue
            if href in self.URL_REPLACEMENTS:
                a_tag["href"] = self.URL_REPLACEMENTS[href]
