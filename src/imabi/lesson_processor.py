# ♥♥─── Imabi Content Processor ───────────────────────────
from __future__ import annotations

import re

from bs4 import Tag, BeautifulSoup

from .text_processor import ContentFormatter


class LessonFormatter(ContentFormatter):
    """Formats lesson content according to specific rules."""

    def format_lesson(
        self,
        content: Tag,
        title: str,
        chapter: str | int,
        path_part: str,
        is_glossary: bool = False,
    ) -> str:
        """Format lesson content with proper structure."""
        if not is_glossary and content.header:
            content.header.extract()

        self._adjust_heading_levels(content)
        self._setup_headers(content, title, chapter, is_glossary)
        self._process_common_formatting(content)

        final_content = self._wrap_final_content(content, path_part)
        return self._wrap_xhtml(final_content, title)

    def _setup_headers(self, content: Tag, title: str, chapter: str | int, is_glossary: bool) -> None:
        """Set up header structure based on content type."""
        headers = content.find_all(re.compile(r"^h\d"))
        if not headers:
            return

        first_header = headers[0]
        if is_glossary:
            first_header.name = "h1"
            first_header["id"] = "glossary"
        else:
            first_header.name = "h2"
            first_header["id"] = f"chapter-{chapter[1:-1] if isinstance(chapter, str) else chapter}"
            header_content = f'<header><p class="chapter">{chapter}</p>{first_header}</header>'
            content.insert(0, BeautifulSoup(header_content, "html.parser"))
            first_header.extract()

    def _adjust_heading_levels(self, content: Tag) -> None:
        """Adjust heading levels to maintain hierarchy."""
        for i in range(6, 1, -1):
            for tag in content.find_all(f"h{i}"):
                new_level = min(i + 1, 6)
                tag.name = f"h{new_level}"

    def _wrap_final_content(self, content: Tag, path_part: str) -> BeautifulSoup:
        """Wrap content in final <body> structure."""
        footer = content.find("footer")
        footnotes = content.find("ol", class_="wp-block-footnotes")

        footer_content = f'<hr/><footer class="footnote">{footnotes}</footer>' if footnotes else "<footer></footer>"

        if footnotes:
            footnotes.extract()
        if footer:
            footer.extract()

        if not content.find("body"):
            content.name = "body"
            if "class" in content.attrs:
                del content["class"]
            content["class"] = "justified"
            content["id"] = path_part
        else:
            content.body["class"] = "justified"

        final_html = f"{content}{footer_content}"
        return BeautifulSoup(final_html, features="html.parser")
