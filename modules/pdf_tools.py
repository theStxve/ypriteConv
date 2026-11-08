"""Combine images/PDFs into one PDF, split a PDF into single pages."""
import io
import os

from PIL import Image, ImageOps

from converters.image_converter import flatten_to_rgb, QUALITY
from modules.file_detect import detect

A4 = (595.28, 841.89)   # points
MARGIN = 28


def _image_bytes(path, quality):
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        img = flatten_to_rgb(img)
        buf = io.BytesIO()
        img.save(buf, 'JPEG', quality=QUALITY.get(quality, 85), optimize=True)
        return buf.getvalue(), img.size


def combine(paths, dest, page_size='fit', quality='medium', progress=None):
    """
    paths: images (any format Pillow/pillow-heif reads) and PDFs, in order.
    page_size: 'fit' (page = image size at 150 dpi) or 'a4' (image centred on A4).
    """
    import fitz
    out = fitz.open()
    for i, path in enumerate(paths):
        real = detect(path).effective
        if real == 'pdf':
            with fitz.open(path) as src:
                out.insert_pdf(src)
        else:
            data, (w, h) = _image_bytes(path, quality)
            if page_size == 'a4':
                pw, ph = A4 if h >= w else (A4[1], A4[0])   # landscape pages for wide images
                scale = min((pw - 2 * MARGIN) / w, (ph - 2 * MARGIN) / h)
                iw, ih = w * scale, h * scale
                page = out.new_page(width=pw, height=ph)
                rect = fitz.Rect((pw - iw) / 2, (ph - ih) / 2, (pw + iw) / 2, (ph + ih) / 2)
            else:
                pw, ph = w * 72 / 150, h * 72 / 150
                page = out.new_page(width=pw, height=ph)
                rect = page.rect
            page.insert_image(rect, stream=data)
        if progress:
            progress(i + 1, len(paths))
    out.save(dest, garbage=3, deflate=True)
    out.close()
    return dest


def split(path, out_dir, base=None):
    """Write every page as its own PDF. Returns the list of created files."""
    import fitz
    base = base or os.path.splitext(os.path.basename(path))[0]
    created = []
    with fitz.open(path) as src:
        if src.needs_pass:
            raise ValueError("PDF is password protected")
        digits = len(str(src.page_count))
        for i in range(src.page_count):
            page_doc = fitz.open()
            page_doc.insert_pdf(src, from_page=i, to_page=i)
            target = os.path.join(out_dir, f"{base}_page{str(i + 1).zfill(digits)}.pdf")
            n = 1
            while os.path.exists(target):
                target = os.path.join(out_dir, f"{base}_page{str(i + 1).zfill(digits)} ({n}).pdf")
                n += 1
            page_doc.save(target, garbage=3, deflate=True)
            page_doc.close()
            created.append(target)
    return created
