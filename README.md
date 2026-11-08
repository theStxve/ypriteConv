<p align="center">
  <img src="assets/icon.png" width="96" alt="ypriteConvert icon">
</p>

<h1 align="center">ypriteConvert</h1>

<p align="center">
  A fast, private file converter for Windows. Everything runs on your PC, nothing is uploaded.<br>
  <a href="https://github.com/theStxve/ypriteConv/releases/latest"><b>Download the latest version</b></a>
</p>

---

## What it does

- **Images**: JPG, PNG, WebP, HEIC (iPhone photos), TIFF, GIF, BMP, ICO → each other or to PDF.
  Keeps EXIF data, fixes photo rotation, and keeps animated GIFs animated when converting to WebP.
- **Video**: MP4, MKV, WebM, MOV, AVI, … → MP4/MKV/WebM, plus **video → MP3/WAV/M4A or GIF**.
- **Audio**: MP3, WAV, FLAC, AAC, OGG, M4A, Opus, …
- **PDF**: PDF → Word, text or images (every page, up to 300 DPI). Images → PDF/A.
- **Documents**: DOCX, ODT, RTF, Markdown, HTML, TXT (with LibreOffice/Pandoc installed).
- **Detects the real file type**: files with a wrong or made-up extension (`photo.yprite`,
  `clip.xyz`, a `.jpg` that is actually HEIC) are recognised by their content.
  You can convert them, or restore the correct extension without re-encoding.
- **Workflows**: multi-step presets such as *Podcast Publisher* (extract audio → normalize to −16 LUFS → MP3),
  and you can build your own.
- **Explorer integration**: right-click → *Convert with ypriteConvert*, works with many files at once.
- **Automatic updates** from GitHub Releases.
- **Light and dark mode** that follows Windows.

## Install

1. Download `ypriteConvert-Setup-x.y.z.exe` from [Releases](https://github.com/theStxve/ypriteConv/releases/latest).
2. Run it. No admin rights are needed, because it installs for the current user.

FFmpeg is included. For document conversions (DOCX → PDF, …), optionally install
[LibreOffice](https://www.libreoffice.org/) and/or [Pandoc](https://pandoc.org/); the app finds them automatically.

## Command line

The installed `ypriteConvert.exe` also works as a CLI:

```bat
ypriteConvert.exe -i video.mp4 --to mp3 --quality high
ypriteConvert.exe --batch "C:\Photos\*.heic" --to jpg -o C:\Converted
ypriteConvert.exe -i interview.mov --preset "Podcast Publisher"
ypriteConvert.exe --list-presets
```

## Development

```bat
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python main.py
```

| Path | Purpose |
| --- | --- |
| `app_info.py` | Name, version, GitHub repo |
| `ui/` | Qt interface (`theme.py` holds all colours and styles) |
| `converters/` | Image, video/audio (FFmpeg), document and PDF converters |
| `modules/file_detect.py` | Content-based file type detection |
| `modules/updater.py` | GitHub-release auto-updater |
| `pipeline_steps/`, `presets/` | Workflow system and built-in workflows |
| `installer/ypriteConvert.iss` | Inno Setup installer |

### Build locally

```bat
build.bat            :: builds dist\ypriteConvert\ and Output\ypriteConvert-Setup-<version>.exe
build.bat 1.2.0      :: same, but sets the version first
```

You need [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`) to build the installer.
FFmpeg is copied from your PATH or downloaded automatically.

### Release a new version

1. Add a section for the new version to `CHANGELOG.md`.
2. Tag and push:
   ```bat
   git tag v1.2.0
   git push origin v1.2.0
   ```
3. The GitHub Action builds the installer and publishes the release.
   Installed apps offer the update automatically.

## Licenses

ypriteConvert uses PyQt6 (GPL v3), PyMuPDF (AGPL v3), pdf2docx, Pillow, pillow-heif, pikepdf and
FFmpeg (GPL build). Check these licenses before distributing the app commercially.
