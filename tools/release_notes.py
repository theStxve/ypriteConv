"""Print the CHANGELOG.md section for a version (used as GitHub release notes / in-app update notes)."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    sys.stdout.reconfigure(encoding='utf-8')  # Windows consoles/CI default to cp1252
    version = sys.argv[1].lstrip('vV')
    text = open(os.path.join(ROOT, 'CHANGELOG.md'), encoding='utf-8').read()
    m = re.search(rf"^## {re.escape(version)}\s*\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    print(m.group(1).strip() if m else f"ypriteConvert {version}")


if __name__ == '__main__':
    main()
