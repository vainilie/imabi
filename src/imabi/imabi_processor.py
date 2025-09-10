# ♥♥─── Imabi Content Processor ───────────────────────────
from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup
import typer

from .data_models import LessonData, ContentType, ProcessingConfig
from .content_fetcher import HTMLCleaner, ContentFetcher
from .image_processor import ImageProcessor
from .index_processor import IndexProcessor
from .lesson_processor import LessonFormatter


# ─── Main Orchestrator ─────────────────────────────────────────────────────────
class ImabiProcessor:
    """Main processor class that coordinates all operations."""

    def __init__(self, config: ProcessingConfig) -> None:
        """Initialize the main processor."""
        self.config = config
        self.fetcher = ContentFetcher()
        self.cleaner = HTMLCleaner()
        self.image_processor = ImageProcessor()
        self.lesson_formatter = LessonFormatter()
        self.index_processor = IndexProcessor()

        # Storage for processed content and images
        self.processed_content: dict[str, str] = {}
        self.all_processed_images: list[tuple[str, bytes]] = []

    def process_full_site(self) -> Path | None:
        """Process the entire Imabi site and optionally create an EPUB."""
        # Process index
        index_xhtml, lesson_data = self.process_content(
            url=self.config.base_url,
            content_type=ContentType.INDEX,
            selector="aside",
        )
        self.processed_content["index"] = index_xhtml

        # Process glossary
        glossary_xhtml, _ = self.process_content(
            url=f"{self.config.base_url}/glossary",
            content_type=ContentType.GLOSSARY,
            selector="article",
            chapter_str="glossary",
        )
        self.processed_content["glossary"] = glossary_xhtml

        # Process individual lessons
        self._process_lessons(lesson_data)

        # Save XHTML files to disk for debugging/backup
        self._save_xhtml_files()

        # Generate EPUB if requested
        if self.config.generate_epub:
            epub_generator = EPUBGenerator(self.config)
            return epub_generator.create_epub(lesson_data, self.processed_content, self.all_processed_images)

        return None

    def process_content(
        self,
        url: str,
        content_type: ContentType,
        selector: str,
        chapter_str: str = "unknown",
    ) -> tuple[str, dict[str, list[LessonData]]]:
        """Fetch, clean, and process content from a given URL."""
        typer.echo(f"🌐 Fetching: {url}")

        html_content, base_uri = self.fetcher.fetch_content(url)
        soup = BeautifulSoup(html_content, "html.parser")
        content_div = soup.select_one(selector)

        if not content_div:
            msg = f"No content found with selector '{selector}' at {url}"
            raise ValueError(msg)

        # Clean HTML structure
        content_div = self.cleaner.clean_structure(content_div)

        # Process images and collect them
        processed_images = self.image_processor.process_images(
            content_div,
            base_uri,
            self.config.images_dir,
            chapter_str,
        )
        self.all_processed_images.extend(processed_images)

        # Process content based on type
        lesson_data = {}
        if content_type == ContentType.INDEX:
            processed_xhtml, lesson_data = self.index_processor.process_index(content_div)
        elif content_type == ContentType.GLOSSARY:
            processed_xhtml = self.lesson_formatter.format_lesson(
                content=content_div,
                title="Glossary",
                chapter=0,
                path_part="glossary",
                is_glossary=True,
            )
        else:
            # For regular lessons, this is handled in _process_lessons
            processed_xhtml = str(content_div)

        return processed_xhtml, lesson_data

    def _process_lessons(self, lesson_dict: dict[str, list[LessonData]]) -> None:
        """Process all individual lessons from the lesson dictionary."""
        lessons_to_process = [lesson for lessons in lesson_dict.values() for lesson in lessons if lesson.has_link]

        if self.config.test_mode:
            lessons_to_process = lessons_to_process[: self.config.test_lessons]
            typer.echo(f"🧪 Test mode: processing {len(lessons_to_process)} lessons")

        for lesson in lessons_to_process:
            try:
                self._process_single_lesson(lesson)
            except Exception as e:
                typer.echo(f"❌ Error processing lesson {lesson.number} ({lesson.title}): {e}")

    def _process_single_lesson(self, lesson: LessonData) -> None:
        """Process a single lesson and store the result."""
        if lesson.has_link:
            url = lesson.link_data["web"]
            typer.echo(f"📖 Processing lesson: {lesson.original_number} - {lesson.title}")

            html_content, base_uri = self.fetcher.fetch_content(url)
            soup = BeautifulSoup(html_content, "html.parser")
            main_div = soup.select_one("article")

        if not main_div:
            typer.echo(f"⚠️  No article content found for lesson {lesson.number}")
            return

        # Save raw HTML if requested
        if self.config.save_raw:
            raw_path = self.config.raw_dir / f"raw-{lesson.id}.html"
            raw_path.write_text(str(main_div.prettify()), encoding="utf-8")

        # Clean and process
        main_div = self.cleaner.clean_structure(main_div)

        # Process images for this lesson
        processed_images = self.image_processor.process_images(
            main_div,
            base_uri,
            self.config.images_dir,
            lesson.id,
        )
        self.all_processed_images.extend(processed_images)

        # Format lesson content
        path_part = main_div.get("id", f"lesson-{lesson.id}")
        formatted_xhtml = self.lesson_formatter.format_lesson(
            main_div,
            lesson.title,
            lesson.original_number,
            path_part,
        )

        # Store processed content
        self.processed_content[lesson.id] = formatted_xhtml

    def _save_xhtml_files(self) -> None:
        """Save all processed XHTML files to disk for debugging/backup."""
        output_path = self.config.output_dir / "Text"
        output_path.mkdir(exist_ok=True)

        for content_id, xhtml_content in self.processed_content.items():
            filename = f"{content_id}.xhtml" if content_id in {"index", "glossary"} else f"{content_id}.xhtml"

            file_path = output_path / filename
            file_path.write_text(xhtml_content, encoding="utf-8")
            typer.echo(f"💾 Saved: {file_path}")
