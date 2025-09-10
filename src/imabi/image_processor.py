from __future__ import annotations

from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import Tag
from PIL import Image
import typer
import requests
from wand.image import Image as wandImage
from wand.exceptions import WandException


# Importaciones opcionales: el programa no se detendrá si no están instaladas
try:
    import cairosvg
except (ImportError, OSError):
    cairosvg = None  # Si no se puede importar o le falta una dependencia, lo marcamos como no disponible

try:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM
except ImportError:
    svg2rlg = None  # Marcamos svglib como no disponible si no está instalada


class ImageProcessor:
    """Handles image processing, downloading, and format conversion."""

    def __init__(self, session: requests.Session | None = None) -> None:
        """Initialize the processor with a requests session."""
        self.session = session or requests.Session()

    def process_images(
        self,
        content_div: Tag,
        base_uri: str,
        output_dir: Path,
        chapter_str: str,
    ) -> list[tuple[str, bytes]]:
        """Process all images in content, returning list of (filename, data) tuples."""
        img_tags = content_div.find_all("img")
        processed_images = []

        for i, img_tag in enumerate(img_tags, 1):
            image_data = self._process_single_image(img_tag, base_uri, output_dir, chapter_str, i)
            if image_data:
                processed_images.append(image_data)

        return processed_images

    def _process_single_image(
        self,
        img_tag: Tag,
        base_uri: str,
        img_output_dir: Path,
        chapter_str: str,
        img_counter: int,
    ) -> tuple[str, bytes] | None:
        """Download and process a single image, converting to PNG if needed."""
        src = img_tag.get("src")
        if not src:
            return None

        try:
            full_src_url = urljoin(base_uri, src)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            }
            img_response = self.session.get(full_src_url, stream=True, headers=headers)
            img_response.raise_for_status()

            original_ext = Path(urlparse(full_src_url).path).suffix.lower()

            # Convert SVG and WebP to PNG
            if original_ext in {".svg", ".webp"}:
                new_name = f"chapter-{chapter_str}-img-{img_counter}.png"
                image_data = self._convert_to_png(img_response.content, original_ext)
            else:
                ext = original_ext or ".jpg"
                new_name = f"chapter-{chapter_str}-img-{img_counter}{ext}"
                image_data = img_response.content

            # Save to disk for debugging/backup
            dest_file = img_output_dir / new_name
            typer.echo(f"🖼️  Processing: {src[:30]}... -> {new_name}")
            dest_file.write_bytes(image_data)

            # Update img tag src
            img_tag["src"] = f"../{img_output_dir.name}/{new_name}"
            if img_tag.has_attr("srcset"):
                del img_tag["srcset"]

            return new_name, image_data

        except Exception as e:
            typer.echo(f"❌ Failed to process image {src}: {e}")
            return None

    def _convert_to_png(self, image_data: bytes, original_format: str) -> bytes:
        """Convert SVG or WebP image data to PNG format."""
        if original_format == ".svg":
            try:
                typer.echo("⚙️  Intentando convertir SVG con ImageMagick (Wand)...")
                # ImageMagick necesita saber que los datos de entrada son SVG
                # Usamos un bloque 'with' para asegurar que los recursos se liberen
                with wandImage(blob=image_data, format="svg") as img:
                    img.format = "png"
                    # Devuelve los datos de la imagen convertida en bytes
                    return img.make_blob()
            except WandException as e:
                # Capturamos excepciones específicas de Wand/ImageMagick
                typer.echo(f"❌ ImageMagick falló: {e}. No se pudo convertir el SVG.")
                return image_data

        # --- Bloque para otros formatos (WebP, etc.) usando Pillow ---
        try:
            with Image.open(BytesIO(image_data)) as img:
                # Convert to RGB if needed (for transparency support)
                if img.mode in {"RGBA", "LA", "P"}:
                    # Create white background for transparent images
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")

                    mask = img.split()[-1] if img.mode in {"RGBA", "LA"} else None
                    background.paste(img, mask=mask)
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Save as PNG
                png_buffer = BytesIO()
                img.save(png_buffer, format="PNG", optimize=True)
                return png_buffer.getvalue()
        except Exception as e:
            typer.echo(f"⚠️  Failed to convert image: {e}")
            return image_data  # Return original if conversion fails
