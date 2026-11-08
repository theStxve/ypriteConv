import os
import shutil
import tempfile

from .base_converter import BaseConverter, run_tool, short_error, tool_available
from modules.config_manager import ConfigManager

# Pandoc output writers for our target extensions
PANDOC_WRITERS = {
    'docx': 'docx', 'odt': 'odt', 'rtf': 'rtf', 'txt': 'plain',
    'md': 'gfm', 'html': 'html',
}


class DocConverter(BaseConverter):
    def convert(self, source, dest, target_format, **kwargs):
        config = ConfigManager()
        ext = os.path.splitext(source)[1].lower().lstrip('.')
        fmt = target_format.lower()

        try:
            # PDF -> DOCX: pure Python first
            if ext == 'pdf' and fmt == 'docx':
                try:
                    from pdf2docx import Converter
                    cv = Converter(source)
                    try:
                        cv.convert(dest, start=0, end=None)
                    finally:
                        cv.close()
                    if os.path.exists(dest):
                        return True, "Success (via pdf2docx)"
                except ImportError:
                    pass
                except Exception as e:
                    print(f"pdf2docx failed: {e}, trying LibreOffice...")

            # PDF -> txt: PyMuPDF text extraction, no external tools needed
            if ext == 'pdf' and fmt in ('txt', 'md'):
                try:
                    import fitz
                    with fitz.open(source) as doc:
                        text = "\n\n".join(page.get_text() for page in doc)
                    with open(dest, 'w', encoding='utf-8') as f:
                        f.write(text)
                    return True, "Success (via PyMuPDF)"
                except ImportError:
                    pass

            # Anything -> PDF, and PDF -> office formats: LibreOffice
            if fmt == 'pdf' or ext == 'pdf':
                if ext in ('md', 'txt') and fmt == 'pdf' and tool_available(config.get('pandoc_path')):
                    # LibreOffice renders markdown as raw text; go md -> html -> pdf
                    return self._via_pandoc_html_to_pdf(source, dest, config)
                return self._libreoffice(source, dest, fmt, ext == 'pdf', config)

            # Everything else: Pandoc
            pandoc = config.get('pandoc_path')
            if not tool_available(pandoc):
                # LibreOffice can handle most office<->office conversions too
                if tool_available(config.get('soffice_path')) and ext not in ('md',):
                    return self._libreoffice(source, dest, fmt, False, config)
                return False, f"Pandoc not found ({pandoc}). Install Pandoc or set the path in Settings."

            cmd = [pandoc, source, '-o', dest, '--standalone']
            writer = PANDOC_WRITERS.get(fmt)
            if writer:
                cmd += ['-t', writer]
            code, out = run_tool(cmd)
            if code != 0:
                return False, f"Pandoc Error:\n{short_error(out)}"
            return True, "Success"

        except Exception as e:
            return False, f"Error: {e}"

    def _libreoffice(self, source, dest, fmt, pdf_import, config):
        soffice = config.get('soffice_path')
        if not tool_available(soffice):
            return False, f"LibreOffice not found ({soffice}). Install LibreOffice or set the path in Settings."

        # Separate temp profile + out dir: works even while LibreOffice is open,
        # and the output name never collides with other files.
        work = tempfile.mkdtemp(prefix="yprite_lo_")
        try:
            profile = 'file:///' + os.path.join(work, 'profile').replace('\\', '/')
            out_dir = os.path.join(work, 'out')
            os.makedirs(out_dir)
            cmd = [soffice, f'-env:UserInstallation={profile}', '--headless']
            if pdf_import:
                cmd.append('--infilter=writer_pdf_import')
            cmd += ['--convert-to', fmt, '--outdir', out_dir, source]

            code, out = run_tool(cmd, timeout=600)
            produced = [f for f in os.listdir(out_dir)]
            if not produced:
                return False, f"LibreOffice Error:\n{short_error(out)}"

            if os.path.exists(dest):
                os.remove(dest)
            shutil.move(os.path.join(out_dir, produced[0]), dest)
            return True, "Success (via LibreOffice)"
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def _via_pandoc_html_to_pdf(self, source, dest, config):
        work = tempfile.mkdtemp(prefix="yprite_md_")
        try:
            html = os.path.join(work, os.path.splitext(os.path.basename(source))[0] + '.html')
            code, out = run_tool([config.get('pandoc_path'), source, '-o', html, '--standalone',
                                  '--metadata', 'title= '])
            if code != 0:
                return False, f"Pandoc Error:\n{short_error(out)}"
            return self._libreoffice(html, dest, 'pdf', False, config)
        finally:
            shutil.rmtree(work, ignore_errors=True)
