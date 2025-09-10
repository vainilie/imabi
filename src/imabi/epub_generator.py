# ─── EPUB Generation ───────────────────────────────────────────────────────────
from __future__ import annotations

import uuid
from pathlib import Path
from datetime import datetime

import typer
from ebooklib import epub

from .data_models import LessonData, ProcessingConfig
from .image_processor import ImageProcessor


class EPUBGenerator:
    """Generates EPUB files using ebooklib."""

    def __init__(self, config: ProcessingConfig) -> None:
        """Initialize the EPUB generator."""
        self.config = config
        self.book = epub.EpubBook()
        self._setup_metadata()

    def _setup_metadata(self) -> None:
        """Set up basic EPUB metadata."""
        self.book.set_identifier(str(uuid.uuid4()))
        self.book.set_title("IMABI 今日 - Guided Japanese Mastery")
        self.book.set_language("en")
        self.book.add_author("Seth Coonrod")
        self.book.add_author("Taylor V. Edwards")

    def create_epub(
        self,
        lesson_dict: dict[str, list[LessonData]],
        processed_content: dict[str, str],
        processed_images: list[tuple[str, bytes]],
    ) -> Path:
        """Create the complete EPUB file using ebooklib."""
        # Add CSS
        self._add_css()

        # Add images
        self._add_images(processed_images)

        # Add cover if specified
        if self.config.cover_image_path:
            self._add_cover()

        # Add special pages
        spine_items = []
        if self.config.cover_image_path:
            spine_items.append(self._create_cover_page())

        spine_items.extend([
            self._create_title_page(),
            self._create_credits_page(),
            self._create_toc_page(lesson_dict),
        ])

        # Add index and glossary
        if "index" in processed_content:
            spine_items.append(self._create_content_item("index", "IMABI Index", processed_content["index"]))

        # Add section pages and lessons
        for section_idx, (section, lessons) in enumerate(lesson_dict.items(), 1):
            # Section page
            section_item = self._create_section_page(section_idx, section)
            spine_items.append(section_item)

            # Lessons in this section
            for lesson in lessons:
                if lesson.has_link and lesson.id in processed_content:
                    lesson_item = self._create_content_item(
                        lesson.id,
                        f"{lesson.original_number} • {lesson.title}",
                        processed_content[lesson.id],
                    )
                    spine_items.append(lesson_item)

        # Add glossary
        if "glossary" in processed_content:
            spine_items.append(self._create_content_item("glossary", "Glossary", processed_content["glossary"]))

        # Set spine
        self.book.spine = spine_items

        # Add navigation
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())

        # Write EPUB
        epub_path = self.config.output_dir / "imabi.epub"
        epub.write_epub(str(epub_path), self.book, {})

        typer.echo(f"📚 EPUB created: {epub_path}")
        return epub_path

    def _add_css(self) -> None:
        """Add CSS stylesheet to the EPUB."""
        if self.config.css_file and self.config.css_file.exists():
            css_content = self.config.css_file.read_text()
        else:
            css_content = self._get_default_css()

        css_item = epub.EpubItem(
            uid="style_default",
            file_name="Styles/base_style.css",
            media_type="text/css",
            content=css_content,
        )
        self.book.add_item(css_item)

    def _add_images(self, processed_images: list[tuple[str, bytes]]) -> None:
        """Add all processed images to the EPUB."""
        for filename, image_data in processed_images:
            media_type = self._get_media_type(filename)
            img_item = epub.EpubItem(
                uid=f"img_{Path(filename).stem}",
                file_name=f"Images/{filename}",
                media_type=media_type,
                content=image_data,
            )
            self.book.add_item(img_item)

    def _add_cover(self) -> None:
        """Add cover image to the EPUB."""
        if not self.config.cover_image_path or not self.config.cover_image_path.exists():
            return

        cover_data = self.config.cover_image_path.read_bytes()
        cover_ext = self.config.cover_image_path.suffix

        # Convert cover to PNG if needed
        if cover_ext.lower() in [".svg", ".webp"]:
            processor = ImageProcessor()
            cover_data = processor._convert_to_png(cover_data, cover_ext.lower())
            cover_ext = ".png"

        self.book.set_cover(f"cover{cover_ext}", cover_data)

    def _create_content_item(self, uid: str, title: str, content: str) -> epub.EpubHtml:
        """Create a content item for the EPUB."""
        item = epub.EpubHtml(
            title=title,
            file_name=f"Text/{uid}.xhtml",
            lang="en",
        )
        item.content = content
        self.book.add_item(item)
        return item

    def _create_cover_page(self) -> epub.EpubHtml:
        """Create cover page."""
        cover_content = self._get_cover_page_content()
        return self._create_content_item("cover", "Cover", cover_content)

    def _create_title_page(self) -> epub.EpubHtml:
        """Create title page."""
        title_content = """<body class="justified">
            <p class="tit-publisher">Seth Coonrod<br/> Taylor V. Edwards</p>
            <p></p>
            <p class="half-title">IMABI 今日</p>
            <p class="half-subtitle">「いまび」<br/>Guided Japanese Mastery</p>
            <p class="tit-publisher1">From <a href="https://imabi.org">imabi.org</a></p>
            </body>"""
        return self._create_content_item("title", "Title Page", title_content)

    def _create_credits_page(self) -> epub.EpubHtml:
        """Create credits page."""
        credits_content = f"""<body class="align-right margin-right-xl dedication" role="doc-dedication">
                <p class="margin-top-xxl fs-xxl">❀ ┊ IMABI 今日</p>
                <p class="fs-xxl"><em>Guided Japanese Mastery</em></p>
                <div><br/>
                <dl class="align-right">
                <p><dt class="align-right">CREDITS ♡ˎˊ˗</dt></p>
                <p><dd>Original Content from <a href="https://imabi.org">imabi.org</a></dd></p>
                <p><dt class="align-right">IMABI's crew ♡ˎˊ˗</dt></p>
                <p><dd>Seth Coonrod (Creator/Author)</dd></p>
                <p><dd>Taylor V. Edwards (Editor)</dd></p>
                <p><dd><a href="https://imabi.org/about-us">About IMABI</a></dd></p>
                </dl><br/><br/>
                </div>
                <div class="hr align-right">
                <dl>
                <p><dt class="align-right"><strong>FOR PERSONAL USE ONLY</strong><br/></dt></p>
                <p><dd>EPUB generated on {datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")}</dd></p>
                <p>by <em>vainilie</em></p>
                </dl>
                </div>
                </body>"""
        return self._create_content_item("credits", "Credits", credits_content)

    def _create_toc_page(self, lesson_dict: dict[str, list[LessonData]]) -> epub.EpubHtml:
        """Create table of contents page."""
        toc_parts = ['<body class="justified"><h1>Table of Contents</h1>']
        lesson_counter = 0

        for section_idx, (section, lessons) in enumerate(lesson_dict.items(), 1):
            section_id = f"section-{section_idx}"
            toc_parts.extend((
                f'<h2 id="{section_id}">{section}</h2>',
                f'<ol start="{lesson_counter + 1}" class="no-list-type toc">',
            ))

            for lesson in lessons:
                lesson_counter += 1
                if lesson.has_link:
                    toc_parts.append(
                        f'<li><a href="{lesson.filename}">{lesson.original_number} • {lesson.title}</a></li>',
                    )
                else:
                    toc_parts.append(f"<li>{lesson.original_number} • {lesson.title}</li>")

            toc_parts.append("</ol>")

        toc_parts.append("</body>")
        toc_content = "".join(toc_parts)
        return self._create_content_item("toc_page", "Table of Contents", toc_content)

    def _create_section_page(self, section_idx: int, section_title: str) -> epub.EpubHtml:
        """Create a section divider page."""
        section_content = f"""<body class="justified">
        <div class="half-title align-center">
        <h1 class="section-title">{section_title}</h1></div></body>"""
        return self._create_content_item(f"section-{section_idx}", f"Section - {section_title}", section_content)

    def _get_cover_page_content(self) -> str:
        """Generate cover page HTML content."""
        if not self.config.cover_image_path:
            return "<body><h1>IMABI</h1></body>"

        cover_filename = f"cover{self.config.cover_image_path.suffix}"
        if self.config.cover_image_path.suffix.lower() in [".svg", ".webp"]:
            cover_filename = "cover.png"

        return f"""<body>
            <div style="height: 100vh; text-align: center; padding: 0pt; margin: 0pt;">
            <svg xmlns="http://www.w3.org/2000/svg" height="100%" preserveAspectRatio="xMidYMid meet" version="1.1" viewBox="0 0 1838 2725" width="100%" xmlns:xlink="http://www.w3.org/1999/xlink">
            <image width="1838" height="2725" xlink:href="../Images/{cover_filename}" role="doc-cover"/>
            </svg> </div> </body>"""

    def _get_media_type(self, filename: str) -> str:
        """Get MIME type for a file based on its extension."""
        ext = Path(filename).suffix.lower()
        return {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".webp": "image/webp",
        }.get(ext, "application/octet-stream")

    def _get_default_css(self) -> str:
        """Return default CSS styles."""
        return """
            body {
                font-family: sans-serif;
                line-height: 1.6;
                margin: 1em;
                text-align: justify;
            }
            .justified { text-align: justify; }
            .wrap-90 { max-width: 90%; margin: 0 auto; }
            .align-center { text-align: center; }
            .align-right { text-align: right; }
            .margin-right-xl { margin-right: 2em; }
            .margin-top-xxl { margin-top: 3em; }
            .fs-xxl { font-size: 1.5em; }
            .half-title { font-size: 2em; font-weight: bold; text-align: center; margin: 1em 0; }
            .half-subtitle { font-size: 1.2em; text-align: center; margin: 1em 0; }
            .tit-publisher, .tit-publisher1 { text-align: center; margin: 1em 0; }
            .section-title {
                text-align: center;
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 0.5em;
            }
            h1, h2, h3, h4, h5, h6 {
                margin-top: 1.5em;
                margin-bottom: 0.5em;
                text-align: left;
            }
            .chapter {
                font-size: 0.9em;
                color: #7f8c8d;
                font-style: italic;
                margin-bottom: 0.5em;
            }
            .numerada { margin-left: 1.5em; }
            .no-list-type { list-style-type: none; }
            .toc li { margin-bottom: 0.5em; }
            header {
                border-bottom: 2px solid #3498db;
                padding-bottom: 1em;
                margin-bottom: 2em;
            }
            footer, .footnote {
                border-top: 1px solid #bdc3c7;
                padding-top: 1em;
                margin-top: 2em;
                font-size: 0.9em;
            }
            .dedication { font-style: italic; }
            .hr { border-top: 1px solid #bdc3c7; padding-top: 1em; margin-top: 1em; }
            img {
                max-width: 100%;
                height: auto;
                display: block;
                margin: 1em auto;
            }
            ol, ul { margin-left: 1.5em; }
            """
