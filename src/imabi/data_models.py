from __future__ import annotations

from enum import Enum
from pathlib import Path
from dataclasses import field, dataclass


# ─── Data Structures ───────────────────────────────────────────────────────────
class ContentType(Enum):
    """Enumeration for different types of content to process."""

    INDEX = "index"
    LESSON = "lesson"
    GLOSSARY = "glossary"


@dataclass
class LessonData:
    """Data structure for lesson information."""

    number: int
    lesson_number: str
    original_number: str
    title: str
    link_data: dict[str, str] | None = None

    @property
    def has_link(self) -> bool:
        """Check if the lesson has an associated web link."""
        return self.link_data is not None

    @property
    def id(self) -> str:
        """Generate a unique ID for the lesson file."""
        return f"lesson-{self.number:03d}"

    @property
    def filename(self) -> str:
        """Generate the output filename for the lesson."""
        return f"{self.id}.xhtml"


@dataclass
class ProcessingConfig:
    """Configuration for content processing."""

    base_url: str = "https://imabi.org"
    output_dir: Path = field(default_factory=lambda: Path("output"))
    images_dir_name: str = "Images"
    css_file: Path | None = None
    generate_epub: bool = True
    save_raw: bool = False
    test_mode: bool = False
    test_lessons: int = 5
    cover_image_path: Path | None = None
    fonts_dir: Path | None = None

    def __post_init__(self) -> None:
        """Create necessary directories after initialization."""
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.images_dir.mkdir(exist_ok=True)
        if self.save_raw:
            self.raw_dir.mkdir(exist_ok=True)

    @property
    def images_dir(self) -> Path:
        """Path to the directory for storing images."""
        return self.output_dir / self.images_dir_name

    @property
    def raw_dir(self) -> Path:
        """Path to the directory for storing raw HTML."""
        return self.output_dir / "raw"
