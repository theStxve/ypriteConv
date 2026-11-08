"""
Tiny translation layer. UI strings are written in English and wrapped in tr();
German comes from the table below. Language: "System" (default), "en", "de".
"""
from PyQt6.QtCore import QLocale

_lang = "en"


def set_language(setting="System"):
    global _lang
    if setting in ("en", "de"):
        _lang = setting
    else:
        _lang = "de" if QLocale.system().language() == QLocale.Language.German else "en"
    return _lang


def language():
    return _lang


def tr(text, **kw):
    out = DE.get(text, text) if _lang == "de" else text
    return out.format(**kw) if kw else out


def trn(one, many, n, **kw):
    """Plural helper: trn("{n} file", "{n} files", 3)."""
    return tr(one if n == 1 else many, n=n, **kw)


DE = {
    # ---- header / main window
    "Add files": "Dateien hinzufügen",
    "Settings (Ctrl+,)": "Einstellungen (Strg+,)",
    "Update available": "Update verfügbar",
    "Update {v}": "Update {v}",
    "Drop files to convert": "Dateien zum Konvertieren hier ablegen",
    "or click to browse — folders, ZIPs and Ctrl+V work too": "oder klicken zum Auswählen – Ordner, ZIPs und Strg+V gehen auch",
    "Images": "Bilder", "Video": "Video", "Audio": "Audio", "Documents": "Dokumente", "PDF": "PDF",
    "{n} file": "{n} Datei", "{n} files": "{n} Dateien",
    "Convert all to": "Alle umwandeln in",
    "Set the target format for every file that supports it": "Zielformat für alle passenden Dateien setzen",
    "Choose…": "Wählen…",
    "Clear": "Leeren",
    "Remove all files from the list": "Alle Dateien aus der Liste entfernen",
    "Combine to PDF": "Zu PDF zusammenfügen",
    "Combine images and PDFs into one PDF": "Bilder und PDFs zu einer PDF zusammenfügen",
    "Save to": "Speichern in",
    "Quality": "Qualität",
    "Workflow": "Workflow",
    "Smaller": "Kleiner", "Balanced": "Ausgewogen", "Best": "Beste",
    "Compression for images, video and audio": "Kompression für Bilder, Video und Audio",
    "Build your own workflow": "Eigenen Workflow bauen",
    "Simple conversion": "Einfache Umwandlung",
    "Convert each file to the format chosen in its row": "Jede Datei in das Format aus ihrer Zeile umwandeln",
    "Convert": "Umwandeln",
    "Convert {n} file": "{n} Datei umwandeln", "Convert {n} files": "{n} Dateien umwandeln",
    "Cancel": "Abbrechen",
    "Stopping…": "Wird gestoppt…",
    "Open folder": "Ordner öffnen",
    "Same folder as original": "Gleicher Ordner wie Original",
    "Fixed folder": "Fester Ordner",
    "Choose folder…": "Ordner wählen…",
    "Open output folder": "Zielordner öffnen",
    "Converted files are saved next to the originals": "Umgewandelte Dateien landen neben den Originalen",
    "Choose output folder": "Zielordner wählen",
    "Skipped {n} file that can't be converted": "{n} nicht umwandelbare Datei übersprungen",
    "Skipped {n} files that can't be converted": "{n} nicht umwandelbare Dateien übersprungen",
    "{done} of {total}  ·  {name}": "{done} von {total}  ·  {name}",
    "{n} converted": "{n} umgewandelt",
    "{n} failed": "{n} fehlgeschlagen",
    "{n} cancelled": "{n} abgebrochen",
    "saved {size}": "{size} gespart",
    "Pasted image": "Eingefügtes Bild",
    "Nothing to paste — copy files or an image first": "Nichts zum Einfügen – kopiere zuerst Dateien oder ein Bild",
    # ---- context menu
    "Show original in Explorer": "Original im Explorer zeigen",
    "Show converted file": "Umgewandelte Datei zeigen",
    "Video options…": "Video-Optionen…",
    "Split PDF into pages": "PDF in Seiten aufteilen",
    "Remove selected": "Auswahl entfernen",
    "Remove finished": "Fertige entfernen",
    "Remove all": "Alle entfernen",
    "Remove from list": "Aus Liste entfernen",
    # ---- file row
    "Ready": "Bereit", "Queued": "Wartet", "Converting…": "Wandelt um…", "Done": "Fertig",
    "Done · Show": "Fertig · Zeigen", "Failed": "Fehler", "Cancelled": "Abgebrochen",
    "Unsupported": "Nicht unterstützt",
    "{fmt} detected": "{fmt} erkannt",
    "saved as .{ext}": "gespeichert als .{ext}",
    "no extension": "keine Endung",
    "can't be converted": "nicht umwandelbar",
    "{fmt} · restore": "{fmt} · Original",
    "{fmt} · keep format": "{fmt} · gleich lassen",
    "The content is {label}, even though the file is named .{ext}.\nPick “{fmt} · restore” to just fix the extension.":
        "Der Inhalt ist {label}, obwohl die Datei .{ext} heißt.\nWähle „{fmt} · Original“, um nur die Endung zu korrigieren.",
    "Click for details": "Klicken für Details",
    "Click to show in Explorer": "Klicken, um im Explorer zu zeigen",
    "Video options": "Video-Optionen",
    "Conversion failed": "Umwandlung fehlgeschlagen",
    "<b>{name}</b> couldn't be converted.": "<b>{name}</b> konnte nicht umgewandelt werden.",
    "Unknown error": "Unbekannter Fehler",
    "Conversion running": "Umwandlung läuft",
    "A conversion is still running. Stop it and quit?": "Es läuft noch eine Umwandlung. Stoppen und beenden?",
    "Workflow": "Workflow",
    "This workflow could not be loaded.": "Dieser Workflow konnte nicht geladen werden.",
    "Output folder": "Zielordner",
    "Can't write to {folder}:\n{err}": "Kann nicht nach {folder} schreiben:\n{err}",
    "Couldn't open {name}:\n{err}": "{name} konnte nicht geöffnet werden:\n{err}",
    # ---- video options
    "Rotate": "Drehen",
    "None": "Keine", "90° right": "90° rechts", "90° left": "90° links", "180°": "180°",
    "Mirror": "Spiegeln",
    "Resolution": "Auflösung",
    "Original": "Original",
    "Max. file size": "Max. Dateigröße",
    "Off": "Aus",
    "Custom…": "Eigene…",
    "Trim": "Zuschneiden",
    "Start": "Start", "End": "Ende",
    "e.g. 0:05": "z. B. 0:05",
    "Length: {t}": "Länge: {t}",
    "Remove audio": "Ton entfernen",
    "Apply to all videos in the list": "Auf alle Videos in der Liste anwenden",
    "Reset": "Zurücksetzen",
    "Apply": "Übernehmen",
    "Invalid time: {t}": "Ungültige Zeit: {t}",
    "End must be after start.": "Ende muss nach dem Start liegen.",
    "Size in MB": "Größe in MB",
    "rotated": "gedreht", "trimmed": "zugeschnitten", "no audio": "ohne Ton", "≤ {mb} MB": "≤ {mb} MB",
    # ---- combine / split
    "Combine into one PDF": "Zu einer PDF zusammenfügen",
    "Drag to change the order.": "Ziehen, um die Reihenfolge zu ändern.",
    "File name": "Dateiname",
    "Page size": "Seitengröße",
    "Fit to image": "An Bild anpassen",
    "A4": "A4",
    "Combine": "Zusammenfügen",
    "Combining…": "Wird zusammengefügt…",
    "Created {name}": "{name} erstellt",
    "Split into {n} pages": "In {n} Seiten aufgeteilt",
    "Couldn't create the PDF:\n{err}": "PDF konnte nicht erstellt werden:\n{err}",
    "Couldn't split the PDF:\n{err}": "PDF konnte nicht aufgeteilt werden:\n{err}",
    # ---- settings
    "Settings": "Einstellungen",
    "APPEARANCE": "DARSTELLUNG",
    "Theme": "Design",
    "System": "System", "Light": "Hell", "Dark": "Dunkel",
    "Language": "Sprache",
    "Language changes apply after a restart.": "Sprachänderungen gelten nach einem Neustart.",
    "CONVERSION": "UMWANDLUNG",
    "Open the output folder when a batch is finished": "Zielordner öffnen, wenn alles fertig ist",
    "Remove finished files from the list": "Fertige Dateien aus der Liste entfernen",
    "Show advanced formats (AVI, MOV, WMA, Opus, …)": "Erweiterte Formate anzeigen (AVI, MOV, WMA, Opus, …)",
    "WINDOWS": "WINDOWS",
    "Show “Convert with ypriteConvert” in the Explorer right-click menu": "„Mit ypriteConvert konvertieren“ im Explorer-Rechtsklickmenü zeigen",
    "Only available in the installed app": "Nur in der installierten App verfügbar",
    "UPDATES": "UPDATES",
    "Check for updates automatically": "Automatisch nach Updates suchen",
    "You're on version {v}": "Du nutzt Version {v}",
    "Check now": "Jetzt prüfen",
    "Checking…": "Wird geprüft…",
    "Couldn't reach GitHub": "GitHub nicht erreichbar",
    "Version {v} is available": "Version {v} ist verfügbar",
    "You're up to date ({v})": "Du bist auf dem neuesten Stand ({v})",
    "CONVERSION ENGINES": "UMWANDLUNGS-ENGINES",
    "FFmpeg ships with the app. LibreOffice, Pandoc and ImageMagick are optional — install them to unlock more document formats.":
        "FFmpeg ist dabei. LibreOffice, Pandoc und ImageMagick sind optional – installiere sie für mehr Dokumentformate.",
    "Found": "Gefunden", "Not found": "Nicht gefunden",
    "Video & audio": "Video & Audio", "Office → PDF": "Office → PDF",
    "Docs ↔ Markdown/HTML": "Dokumente ↔ Markdown/HTML", "Rare image formats": "Seltene Bildformate",
    "Browse…": "Durchsuchen…",
    "Select program": "Programm wählen",
    "ABOUT": "ÜBER",
    "What's new": "Was ist neu",
    "Data folder": "Datenordner",
    "Save": "Speichern",
    # ---- update dialog
    "Version {v} is available ": "Version {v} ist verfügbar",
    "You have {v}. The update installs in the background and the app restarts by itself.":
        "Du hast {v}. Das Update installiert sich im Hintergrund und die App startet von selbst neu.",
    "WHAT'S NEW": "WAS IST NEU",
    "Skip this version": "Diese Version überspringen",
    "Later": "Später",
    "Install update": "Update installieren",
    "Downloading…": "Wird heruntergeladen…",
    "Downloading…  {done} / {total} MB": "Wird heruntergeladen…  {done} / {total} MB",
    "Starting installer…": "Installer wird gestartet…",
    "Update failed": "Update fehlgeschlagen",
    "The update couldn't be downloaded.\n\n{err}": "Das Update konnte nicht heruntergeladen werden.\n\n{err}",
    "_No release notes._": "_Keine Versionshinweise._",
    # ---- what's new / about
    "What's new in {v}": "Neu in Version {v}",
    "Changelog": "Änderungsverlauf",
    "Close": "Schließen",
    "Got it": "Alles klar",
    # ---- onboarding
    "Welcome to ypriteConvert": "Willkommen bei ypriteConvert",
    "Convert images, videos, audio and documents — fast, private, right on your PC.":
        "Bilder, Videos, Audio und Dokumente umwandeln – schnell, privat, direkt auf deinem PC.",
    "Where should converted files go?": "Wohin sollen umgewandelte Dateien?",
    "Next to the original file": "Neben die Originaldatei",
    "Into one folder": "In einen festen Ordner",
    "Add “Convert with ypriteConvert” to the Explorer right-click menu": "„Mit ypriteConvert konvertieren“ zum Explorer-Rechtsklickmenü hinzufügen",
    "Check for updates automatically ": "Automatisch nach Updates suchen",
    "Get started": "Los geht's",
    "Convert with ypriteConvert": "Mit ypriteConvert konvertieren",
    "Tip: drop files anywhere in the window, or press Ctrl+V to paste.":
        "Tipp: Dateien einfach irgendwo ins Fenster ziehen oder mit Strg+V einfügen.",
}
