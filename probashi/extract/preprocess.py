"""Turn an uploaded photo, scan or PDF into clean JPEG pages for the LLM.

Everything stays in memory; nothing is written to disk.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps, ImageStat

from probashi.llm import ImageInput

MAX_LONG_EDGE = 1568  # px sent to the model; larger costs more, reads no better
MAX_PAGES = 3  # PDF pages read; offers put the key facts up front
MAX_PIXELS = 60_000_000  # refuse absurd uploads before decoding them
JPEG_QUALITY = 85
# Below this the page is treated as blurry. Calibrated only on the synthetic
# fixtures in tests/fixtures (sharp pages score 3.9 to 6.5, the blurred one
# 2.1); it has not been tuned on real phone photos yet.
BLUR_THRESHOLD = 3.0


class UnreadableInput(ValueError):
    """The bytes are not an image or PDF we can open."""


@dataclass
class PreparedDocument:
    pages: list[ImageInput]
    sharpness: float  # lowest page score; see `sharpness_score`
    truncated: bool = False  # PDF had more pages than MAX_PAGES

    @property
    def is_blurry(self) -> bool:
        return self.sharpness < BLUR_THRESHOLD


def sharpness_score(img: Image.Image) -> float:
    """How much edge detail is lost by blurring the image a little.

    A sharp page loses a lot (score well above 1); an already blurry page
    loses almost nothing (score near 1). Unlike plain edge variance this
    does not depend much on how much text is on the page.
    """
    gray = ImageOps.grayscale(img)
    gray.thumbnail((1024, 1024))
    edges = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES)).mean[0]
    blurred = gray.filter(ImageFilter.GaussianBlur(2))
    blurred_edges = ImageStat.Stat(blurred.filter(ImageFilter.FIND_EDGES)).mean[0]
    return edges / max(blurred_edges, 1e-6)


def _clean_page(img: Image.Image) -> tuple[ImageInput, float]:
    img = ImageOps.exif_transpose(img)  # phone photos carry rotation in EXIF
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        background = Image.new("RGB", rgba.size, "white")
        background.paste(rgba, mask=rgba.getchannel("A"))
        img = background
    else:
        img = img.convert("RGB")
    img.thumbnail((MAX_LONG_EDGE, MAX_LONG_EDGE), Image.LANCZOS)
    score = sharpness_score(img)
    img = ImageOps.autocontrast(img, cutoff=1)  # lift faded or dim photos
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=JPEG_QUALITY)
    return ImageInput(data=out.getvalue(), media_type="image/jpeg"), score


def _pdf_pages(data: bytes) -> tuple[list[Image.Image], bool]:
    try:
        import pypdfium2 as pdfium
    except ImportError as e:
        raise UnreadableInput("PDF support needs the 'pypdfium2' package") from e
    try:
        pdf = pdfium.PdfDocument(data)
        total = len(pdf)
        pages = []
        for i in range(min(total, MAX_PAGES)):
            page = pdf[i]
            scale = MAX_LONG_EDGE / max(page.get_size())
            pages.append(page.render(scale=scale).to_pil())
        pdf.close()
    except Exception as e:
        raise UnreadableInput("Could not read the PDF") from e
    if not pages:
        raise UnreadableInput("The PDF has no pages")
    return pages, total > MAX_PAGES


def prepare_document(data: bytes) -> PreparedDocument:
    """Decode a JPEG/PNG/WebP photo or a PDF and return model-ready pages."""
    truncated = False
    if data[:5] == b"%PDF-":
        images, truncated = _pdf_pages(data)
    else:
        try:
            img = Image.open(io.BytesIO(data))
            if img.width * img.height > MAX_PIXELS:
                raise UnreadableInput("Image is too large")
            img.load()
        except UnreadableInput:
            raise
        except Exception as e:
            raise UnreadableInput("Could not read the image") from e
        images = [img]
    cleaned = [_clean_page(img) for img in images]
    return PreparedDocument(
        pages=[page for page, _ in cleaned],
        sharpness=min(score for _, score in cleaned),
        truncated=truncated,
    )
