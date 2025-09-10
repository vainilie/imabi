from __future__ import annotations

import re

from bs4 import Tag, BeautifulSoup


class ContentFormatter:
    """Base class for content formatting."""

    LIST_PATTERN = re.compile(r"^(\d+\.|[ivxlcdm]+\.|※|・)")
    BR_REPLACEMENT_PATTERN = re.compile(r"(<br\s*/?>\s*){2,}")
    URL_REPLACEMENTS = {}

    def _wrap_xhtml(self, content: BeautifulSoup | str, title: str) -> str:
        """Wrap content in a standard XHTML structure for EPUB."""
        clean_title = title.replace(".xhtml", "").replace("-", " ").title()
        css_path = "https://imabi.org/Styles/base_style.css"

        body_content = str(content) if isinstance(content, BeautifulSoup) else content

        return f"""<?xml version="1.0" encoding="utf-8"?>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
        "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
        <head>
        <title>{clean_title}</title>
        <link href="{css_path}" rel="stylesheet" type="text/css"/>
        </head>
        {body_content}
        </html>"""

    def _process_common_formatting(self, content: Tag) -> None:
        """Apply common formatting rules to content."""
        self._strip_paragraphs(content)
        self._process_paragraphs(content)
        self._fix_links(content)

    def _strip_paragraphs(self, content: Tag) -> None:
        """Replace multiple BR tags with proper paragraph breaks."""
        for p in content.find_all("p"):
            self._replace_multiple_br_tags(p)

    def _replace_multiple_br_tags(self, paragraph: Tag) -> None:
        """Replace multiple <br> tags with paragraph breaks."""
        html = "".join(str(c) for c in paragraph.contents)
        html = self.BR_REPLACEMENT_PATTERN.sub("</p><p>", html)
        new_soup = BeautifulSoup(f"<p>{html}</p>", "html.parser")
        paragraph.replace_with(new_soup)

    def _process_paragraphs(self, content: Tag) -> None:
        """Process paragraphs for better formatting."""
        for p in content.find_all("p"):
            self._classify_paragraph(p)

    def _classify_paragraph(self, paragraph: Tag) -> None:
        """Add appropriate classes to paragraphs based on content."""
        text = paragraph.get_text(strip=True).lower()
        if self.LIST_PATTERN.match(text):
            paragraph["class"] = "numerada"
        if text.startswith("▼"):
            paragraph.name = "h6"

    def _fix_links(self, content: Tag) -> None:
        """Fix internal and external links."""
        for a in content.find_all("a"):
            href = a.get("href", "")
            if not href:
                continue
            if href.startswith("https://imabi.org/"):
                a["href"] = href.replace("https://imabi.org/", "../")
