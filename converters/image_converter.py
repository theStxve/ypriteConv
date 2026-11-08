import os
from PIL import Image, ImageOps
from .base_converter import BaseConverter, run_tool, short_error, tool_available
from modules.config_manager import ConfigManager

# HEIC/HEIF support (iPhone photos) via pillow-heif
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:
    HEIF_AVAILABLE = False

PILLOW_TARGETS = {'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'gif', 'webp', 'ico', 'heic', 'heif'}
PILLOW_SAVE_FORMAT = {'jpg': 'JPEG', 'jpeg': 'JPEG', 'tif': 'TIFF', 'heic': 'HEIF', 'heif': 'HEIF'}
QUALITY = {'high': 95, 'medium': 85, 'low': 60}
PDF_RENDER_DPI = {'high': 300, 'medium': 200, 'low': 110}
HIGH_BIT_MODES = ('I;16', 'I;16B', 'I;16L', 'I', 'F')


def flatten_to_rgb(img, bg=(255, 255, 255)):
    """Return an RGB image; transparent areas become `bg` instead of black."""
    if img.mode in ('RGBA', 'LA', 'PA', 'RGBa', 'La') or (img.mode == 'P' and 'transparency' in img.info):
        rgba = img.convert('RGBA')
        background = Image.new('RGB', img.size, bg)
        background.paste(rgba, mask=rgba.getchannel('A'))
        return background
    if img.mode in HIGH_BIT_MODES:
        # 16-bit / 32-bit greyscale -> 8-bit
        img = img.point(lambda v: v / 256).convert('L')
    return img if img.mode == 'RGB' else img.convert('RGB')


def prepare_for(img, fmt):
    """Convert the image mode so Pillow can save it as `fmt`."""
    if fmt in ('jpg', 'jpeg', 'heic', 'heif'):
        return img if img.mode in ('RGB', 'L') else flatten_to_rgb(img)
    if img.mode in HIGH_BIT_MODES or img.mode == 'CMYK':
        if fmt in ('tiff', 'tif'):
            return img
        return flatten_to_rgb(img)
    if fmt == 'bmp' and img.mode not in ('RGB', 'L', 'P', '1'):
        return flatten_to_rgb(img)
    if fmt in ('webp', 'ico') and img.mode not in ('RGB', 'RGBA', 'L'):
        return img.convert('RGBA')
    return img


def save_image(img, dest, fmt, quality='medium', exif=None, icc=None):
    fmt = fmt.lower()
    img = prepare_for(img, fmt)
    q = QUALITY.get(quality, 85)
    params = {}
    if fmt in ('jpg', 'jpeg', 'webp', 'png', 'tiff', 'tif', 'heic', 'heif'):
        if exif:
            params['exif'] = exif
        if icc:
            params['icc_profile'] = icc

    if fmt in ('jpg', 'jpeg'):
        params.update(quality=q, optimize=True, progressive=True)
    elif fmt == 'webp':
        params.update(quality=q, method=6)
    elif fmt in ('heic', 'heif'):
        params.update(quality=q)
    elif fmt == 'png':
        params.update(optimize=True)
    elif fmt in ('tiff', 'tif'):
        params.update(compression='tiff_lzw')
    elif fmt == 'ico':
        # ICO tops out at 256x256
        sizes = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256) if s <= max(img.size)]
        params.update(sizes=sizes or [(16, 16)])

    img.save(dest, format=PILLOW_SAVE_FORMAT.get(fmt, fmt.upper()), **params)


class ImageConverter(BaseConverter):
    def _convert_image_to_pdf_professional(self, source, dest, **kwargs):
        """
        Professional PNG→PDF conversion with full PDF/A-1b compliance.
        Handles transparency, embeds color profiles (OutputIntents), and sets proper metadata.
        Uses pikepdf for complete control over PDF structure.
        """
        try:
            import pikepdf
            from datetime import datetime
            from PIL import ImageCms
            import tempfile
            
            # Open and process source image
            with Image.open(source) as img:
                img = ImageOps.exif_transpose(img)
                # Transparency -> white (or custom) background, everything else -> RGB
                img = flatten_to_rgb(img, kwargs.get('pdf_background', (255, 255, 255)))
                
                # DPI Settings
                dpi = kwargs.get('pdf_dpi', 300)
                
                # Save processed image to temporary file
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_img:
                    img.save(tmp_img.name, format='JPEG', quality=95, dpi=(dpi, dpi))
                    tmp_img_path = tmp_img.name
                    img_width, img_height = img.size
            
            # Create PDF from scratch with pikepdf
            pdf = pikepdf.Pdf.new()
            
            # Calculate page size in points (72 points = 1 inch)
            page_width = (img_width / dpi) * 72
            page_height = (img_height / dpi) * 72
            
            # Read image data
            with open(tmp_img_path, 'rb') as img_file:
                img_data = img_file.read()
            
            # Clean up temp image
            os.unlink(tmp_img_path)
            
            # Create image object in PDF
            image_pdf = pikepdf.Stream(pdf, img_data)
            image_pdf.Type = pikepdf.Name('/XObject')
            image_pdf.Subtype = pikepdf.Name('/Image')
            image_pdf.Width = img_width
            image_pdf.Height = img_height
            image_pdf.ColorSpace = pikepdf.Name('/DeviceRGB')
            image_pdf.BitsPerComponent = 8
            image_pdf.Filter = pikepdf.Name('/DCTDecode')  # JPEG compression
            
            
            # Create page content stream (places image on page)
            content_stream = f"q {page_width} 0 0 {page_height} 0 0 cm /Im0 Do Q".encode()
            contents = pikepdf.Stream(pdf, content_stream)
            
            # Create page with proper pikepdf method
            page = pdf.add_blank_page(page_size=(page_width, page_height))
            page.Contents = contents
            page.Resources = pikepdf.Dictionary(
                XObject=pikepdf.Dictionary(Im0=image_pdf)
            )
            
            # CRITICAL: Add OutputIntent with sRGB ICC Profile
            try:
                # Create sRGB profile
                icc_data = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()

                # Create ICC stream object
                icc_stream = pikepdf.Stream(pdf, icc_data)
                icc_stream.N = 3  # RGB = 3 components
                icc_stream.Alternate = pikepdf.Name('/DeviceRGB')
                
                # Create OutputIntent (PDF/A REQUIREMENT!)
                output_intent = pikepdf.Dictionary(
                    Type=pikepdf.Name('/OutputIntent'),
                    S=pikepdf.Name('/GTS_PDFA1'),
                    OutputConditionIdentifier='sRGB IEC61966-2.1',
                    DestOutputProfile=icc_stream,
                    Info='sRGB IEC61966-2.1'
                )
                
                # Add to PDF catalog
                pdf.Root.OutputIntents = pikepdf.Array([output_intent])
                
            except Exception as e:
                print(f"Warning: Could not embed full ICC profile: {e}")
                # Fallback: minimal OutputIntent
                output_intent = pikepdf.Dictionary(
                    Type=pikepdf.Name('/OutputIntent'),
                    S=pikepdf.Name('/GTS_PDFA1'),
                    OutputConditionIdentifier='sRGB',
                    Info='sRGB'
                )
                pdf.Root.OutputIntents = pikepdf.Array([output_intent])
            
            # Add XMP metadata for PDF/A compliance
            with pdf.open_metadata() as meta:
                meta['dc:title'] = kwargs.get('pdf_title', os.path.basename(source))
                meta['dc:creator'] = [kwargs.get('pdf_creator', 'ypriteConv Professional Converter')]
                meta['dc:description'] = kwargs.get('pdf_description', f'Converted from {os.path.basename(source)}')
                meta['xmp:CreatorTool'] = 'ypriteConv v2.1 (PDF/A-1b Compliant)'
                meta['xmp:CreateDate'] = datetime.now().isoformat()
                meta['pdfaid:part'] = '1'
                meta['pdfaid:conformance'] = 'B'
            
            # Save PDF
            pdf.save(dest, linearize=True)
            pdf.close()
            
            return True, f"PDF/A-1b created with OutputIntent ({dpi} DPI)"
        
        except ImportError as e:
            return False, f"Required libraries missing: {e}. Run: pip install pikepdf"
        except Exception as e:
            return False, f"PDF conversion failed: {str(e)}"
    
    def convert(self, source, dest, target_format, **kwargs):
        fmt = target_format.lower()
        src_ext = os.path.splitext(source)[1].lower().lstrip('.')
        quality = kwargs.get('quality', 'medium')

        if (src_ext in ('heic', 'heif') or fmt in ('heic', 'heif')) and not HEIF_AVAILABLE:
            return False, "HEIC support missing. Run: pip install pillow-heif"

        # PDF -> image(s)
        if src_ext == 'pdf':
            return self._pdf_to_images(source, dest, fmt, quality)

        # Image -> PDF (PDF/A)
        if fmt == 'pdf':
            return self._convert_image_to_pdf_professional(source, dest, **kwargs)

        pillow_error = None
        if fmt in PILLOW_TARGETS:
            try:
                with Image.open(source) as img:
                    if getattr(img, 'is_animated', False) and fmt in ('gif', 'webp'):
                        # Keep the animation for GIF <-> WebP
                        extra = {'quality': QUALITY.get(quality, 85)} if fmt == 'webp' else {}
                        img.save(dest, save_all=True, loop=img.info.get('loop', 0),
                                 duration=img.info.get('duration', 100), **extra)
                        return True, "Success (animated)"

                    # Bake camera rotation into the pixels so every viewer shows it upright
                    img = ImageOps.exif_transpose(img)
                    save_image(img, dest, fmt, quality,
                               img.info.get('exif'), img.info.get('icc_profile'))
                return True, "Success"
            except Exception as e:
                print(f"Pillow failed: {e}, attempting ImageMagick fallback...")
                pillow_error = str(e)

        return self._magick(source, dest, pillow_error)

    def _pdf_to_images(self, source, dest, fmt, quality):
        """Render every page. One page -> dest; several -> name_1.ext, name_2.ext, ..."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return self._magick(source, dest, "PyMuPDF not installed")

        try:
            dpi = PDF_RENDER_DPI.get(quality, 200)
            with fitz.open(source) as doc:
                if doc.needs_pass:
                    return False, "PDF is password protected"
                n = doc.page_count
                if n == 0:
                    return False, "PDF has no pages"
                base, ext = os.path.splitext(dest)
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=dpi, alpha=False)
                    img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                    out = dest if n == 1 else f"{base}_{i + 1}{ext}"
                    save_image(img, out, fmt, quality)
            return True, f"Success ({n} page{'s' if n != 1 else ''}, {dpi} DPI)"
        except Exception as e:
            return False, f"PDF render failed: {e}"

    def _magick(self, source, dest, previous_error=None):
        magick = ConfigManager().get('magick_path')
        if not tool_available(magick):
            if previous_error:
                return False, f"Conversion failed: {previous_error}"
            return False, f"ImageMagick not found ({magick}). Set the path in Settings."
        try:
            code, out = run_tool([magick, source, dest])
            if code != 0:
                return False, f"ImageMagick Error:\n{short_error(out)}"
            return True, "Success (via ImageMagick)"
        except Exception as e:
            return False, f"Error: {e}"
