from __future__ import annotations

import re

from bs4 import Tag, BeautifulSoup

from .data_models import LessonData
from .text_processor import ContentFormatter


class IndexProcessor(ContentFormatter):
    """Processes index content and extracts lesson information."""

    def process_index(self, content_div: Tag) -> tuple[str, dict[str, list[LessonData]]]:
        """Process index content, returning XHTML and lesson data."""
        lesson_dict = self._extract_sectioned_index(content_div)
        index_xhtml = self._create_index_xhtml(lesson_dict)
        return index_xhtml, lesson_dict

    def _extract_sectioned_index(self, content_div: Tag) -> dict[str, list[LessonData]]:
        """Extract lessons organized by sections from the main content."""
        sections = {}
        current_section = "Uncategorized"
        overall_lesson_counter = 1

        for element in content_div.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p"]):
            if element.name.startswith("h"):
                current_section = element.get_text(strip=True)
                if current_section not in sections:
                    sections[current_section] = []
            elif element.name == "p":
                paragraphs = self._break_paragraph_by_br(element)
                lessons = self._extract_links_from_paragraphs(paragraphs, start_number=overall_lesson_counter)
                if current_section in sections:
                    sections[current_section].extend(lessons)
                overall_lesson_counter += len(lessons)

        return {k: v for k, v in sections.items() if v}

    def _break_paragraph_by_br(self, paragraph: Tag) -> BeautifulSoup:
        """Break paragraph content by <br> tags into new <p> tags."""
        content = paragraph.decode_contents()
        children = re.split(r"<br\s*/?>", content)
        new_content = "".join(f"<p>{child.strip()}</p>" for child in children if child.strip())
        return BeautifulSoup(new_content, "html.parser")

    def _extract_links_from_paragraphs(self, paragraphs: BeautifulSoup, start_number: int) -> list[LessonData]:
        """Extract lesson data from a collection of paragraph elements."""
        lessons = []
        for idx, element in enumerate(paragraphs.find_all("p"), start=start_number):
            link_data = self._extract_link_data(element)
            lesson_info = self._parse_lesson_text(element.get_text(strip=True))
            lesson = LessonData(
                number=idx,
                lesson_number=lesson_info["number"],
                original_number=lesson_info["original"],
                title=lesson_info["title"],
                link_data=link_data,
            )
            lessons.append(lesson)
        return lessons

    def _extract_link_data(self, element: Tag) -> dict[str, str] | None:
        """Extract link information from a paragraph element."""
        if not element.a:
            return None
        web_link = element.a["href"]
        relative_path = web_link.split(".org/")[1].strip("/") if ".org/" in web_link else web_link
        element.a.unwrap()
        for em_tag in element.find_all("em"):
            if not em_tag.get_text(strip=True):
                em_tag.decompose()
        return {"web": web_link, "relative": relative_path}

    def _parse_lesson_text(self, text: str) -> dict[str, str]:
        """Parse lesson number and title from text."""
        parts = text.split("課:", 1)
        if len(parts) < 2:
            return {"number": "N/A", "original": text.strip(), "title": text.strip()}
        original_number_part = parts[0].strip()
        title = parts[1].strip()
        number = original_number_part.replace("第", "")
        original = f"{original_number_part}課"
        return {"number": number, "original": original, "title": title}

    def _create_index_xhtml(self, lesson_dict: dict[str, list[LessonData]]) -> str:
        """Create a structured XHTML index from the lesson dictionary."""
        html_parts = ['<body class="justified"><h1>IMABI - Table of Contents 目次</h1>']
        lesson_counter = 0

        for section, lessons in lesson_dict.items():
            html_parts.append(f"<h2>{section}</h2><ol start='{lesson_counter + 1}' class='no-list-type'>")
            for lesson in lessons:
                lesson_counter += 1
                if lesson.has_link and lesson.link_data:
                    link_html = f'<a href="../Text/{lesson.filename}">{lesson.title}</a>'
                    html_parts.append(f"<li>{lesson.original_number} • {link_html}</li>")
                else:
                    html_parts.append(f"<li>{lesson.original_number} • {lesson.title}</li>")
            html_parts.append("</ol>")

        html_parts.append("</body>")
        body_content = "".join(html_parts)
        return self._wrap_xhtml(body_content, "IMABI Index")
