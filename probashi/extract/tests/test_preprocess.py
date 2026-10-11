"""Image and PDF preparation on the synthetic fixtures. No API needed."""
import io

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

from probashi.extract.preprocess import (  # noqa: E402
    MAX_LONG_EDGE,
    MAX_PAGES,
    UnreadableInput,
    prepare_document,
)
from probashi.extract.tests.accuracy import FIXTURES, load  # noqa: E402

IMAGE_FIXTURES = load("image_fixtures.json")


def _bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_there_are_at_least_eight_sample_documents():
    assert len(IMAGE_FIXTURES) >= 8
    for fx in IMAGE_FIXTURES:
        assert (FIXTURES / fx["file"]).is_file()


@pytest.mark.parametrize("fx", IMAGE_FIXTURES, ids=[fx["file"] for fx in IMAGE_FIXTURES])
def test_fixture_becomes_small_jpeg_pages(fx):
    doc = prepare_document(_bytes(fx["file"]))
    assert 1 <= len(doc.pages) <= MAX_PAGES
    for page in doc.pages:
        assert page.media_type == "image/jpeg"
        img = Image.open(io.BytesIO(page.data))
        assert img.format == "JPEG"
        assert max(img.size) <= MAX_LONG_EDGE


def test_only_the_blurry_fixture_is_flagged_blurry():
    flagged = {fx["file"] for fx in IMAGE_FIXTURES if prepare_document(_bytes(fx["file"])).is_blurry}
    assert flagged == {"09_en_offer_blurry.jpg"}


def test_pdf_pages_are_rendered():
    pytest.importorskip("pypdfium2")
    doc = prepare_document(_bytes("10_en_offer_two_pages.pdf"))
    assert len(doc.pages) == 2
    assert not doc.truncated


def test_long_pdf_is_truncated():
    pytest.importorskip("pypdfium2")
    pages = [Image.new("RGB", (200, 280), "white") for _ in range(MAX_PAGES + 2)]
    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:])
    doc = prepare_document(buf.getvalue())
    assert len(doc.pages) == MAX_PAGES
    assert doc.truncated


def test_exif_rotation_is_applied():
    img = Image.new("RGB", (400, 200), "white")  # landscape pixels...
    exif = Image.Exif()
    exif[0x0112] = 6  # ...that the camera says to show rotated by 90 degrees
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    page = prepare_document(buf.getvalue()).pages[0]
    out = Image.open(io.BytesIO(page.data))
    assert out.height > out.width


def test_transparent_png_gets_a_white_background():
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    page = prepare_document(buf.getvalue()).pages[0]
    assert Image.open(io.BytesIO(page.data)).getpixel((50, 50))[0] > 240


@pytest.mark.parametrize("data", [b"not an image", b"%PDF-1.4 broken", b"\x89PNG\r\n\x1a\n"])
def test_bad_bytes_raise_unreadable(data):
    with pytest.raises(UnreadableInput):
        prepare_document(data)
