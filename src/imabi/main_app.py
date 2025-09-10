# ♥♥─── Imabi Content Processor ───────────────────────────
from __future__ import annotations

from pathlib import Path

from rich.console import Console

import typer

from .data_models import ProcessingConfig
from .imabi_processor import ImabiProcessor


# ─── CLI Application ───────────────────────────────────────────────────────────
app = typer.Typer()
console = Console()


@app.command()
def process(
    output_dir: Path = typer.Option("output", "--output", "-o", help="Output directory"),
    css_file: Path = typer.Option(None, "--css", "-c", help="Custom CSS file path"),
    test_mode: bool = typer.Option(False, "--test", "-t", help="Test mode (process only a few lessons)"),
    test_lessons: int = typer.Option(5, "--test-lessons", help="Number of lessons to process in test mode"),
    save_raw: bool = typer.Option(False, "--save-raw", "-r", help="Save raw, unprocessed HTML for debugging"),
    no_epub: bool = typer.Option(False, "--no-epub", help="Skip generating the final EPUB file"),
    cover_image: Path = typer.Option(None, "--cover-image", help="Path to a custom cover image"),
    fonts_dir: Path = typer.Option(None, "--fonts-dir", help="Directory with custom fonts to embed"),
) -> None:
    """Process IMABI content and generate an EPUB using ebooklib."""
    # Check dependencies

    config = ProcessingConfig(
        output_dir=output_dir,
        css_file=css_file,
        generate_epub=not no_epub,
        save_raw=save_raw,
        test_mode=test_mode,
        test_lessons=test_lessons,
        cover_image_path=cover_image,
        fonts_dir=fonts_dir,
    )
    processor = ImabiProcessor(config)
    try:
        epub_path = processor.process_full_site()
        console.print("🎉 Processing complete!", style="bold green")
        if epub_path:
            console.print(f"📚 EPUB created: {epub_path}", style="bold cyan")
        if save_raw:
            console.print(f"💾 Raw HTML saved in: {config.raw_dir}", style="yellow")
    except KeyboardInterrupt:
        console.print("\n⚠️ Processing interrupted by user.", style="yellow")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"💥 An unexpected error occurred: {e}", style="bold red")
        raise typer.Exit(code=1)
