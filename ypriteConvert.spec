# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for ypriteConvert.
Build:  pyinstaller ypriteConvert.spec --clean --noconfirm
Output: dist/ypriteConvert/ (folder build; packaged by installer/ypriteConvert.iss)

FFmpeg is NOT bundled here; the installer copies bin/ffmpeg.exe next to the exe.
"""
import os
import sys
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable,
                                                 StringStruct, VarFileInfo, VarStruct)

sys.path.insert(0, os.path.abspath('.'))
from app_info import APP_NAME, VERSION, PUBLISHER, version_tuple  # noqa: E402

ver = version_tuple(VERSION) + (0,)
version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=ver, prodvers=ver),
    kids=[
        StringFileInfo([StringTable('040904B0', [
            StringStruct('CompanyName', PUBLISHER),
            StringStruct('FileDescription', APP_NAME),
            StringStruct('FileVersion', VERSION),
            StringStruct('InternalName', APP_NAME),
            StringStruct('OriginalFilename', f'{APP_NAME}.exe'),
            StringStruct('ProductName', APP_NAME),
            StringStruct('ProductVersion', VERSION),
        ])]),
        VarFileInfo([VarStruct('Translation', [0x0409, 1200])]),
    ],
)

datas = [('presets', 'presets'), ('assets', 'assets'), ('CHANGELOG.md', '.')]
datas += collect_data_files('pikepdf')
datas += collect_data_files('pillow_heif')

hiddenimports = ['pikepdf', 'fitz', 'pymupdf', 'pdf2docx', 'pillow_heif', 'PyQt6.QtSvg', 'PyQt6.QtNetwork']

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    # dev-only tools and big libs we never use (numpy/cv2 are NOT excluded: pdf2docx needs them)
    excludes=['openai', 'httpx', 'tkinter', 'matplotlib', 'pandas', 'scipy', 'IPython', 'pytest',
              'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtQml', 'PyQt6.QtQuick',
              'PyQt6.QtMultimedia', 'PyQt6.QtBluetooth', 'PyQt6.QtPdf', 'PyQt6.Qt3DCore'],
    noarchive=False,
)

# Strip big files the app never uses (~150 MB): Qt translations, software OpenGL,
# Qt PDF module, PyMuPDF developer headers/libs, OpenCV's own FFmpeg video backend.
DROP = ('qt6/translations', 'opengl32sw.dll', 'qt6pdf', 'mupdf-devel', 'opencv_videoio_ffmpeg',
        'qt6quick', 'qt6qml', 'qt6virtualkeyboard')


def _keep(entry):
    dest = entry[0].replace(os.sep, '/').lower()
    return not any(d in dest for d in DROP)


a.binaries = [b for b in a.binaries if _keep(b)]
a.datas = [d for d in a.datas if _keep(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    strip=False,
    upx=False,          # UPX-packed exes trigger antivirus false positives
    console=False,
    icon='assets/icon.ico',
    version=version_info,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name=APP_NAME)
