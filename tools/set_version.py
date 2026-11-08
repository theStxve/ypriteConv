"""Set app_info.VERSION, e.g. from a git tag:  python tools/set_version.py v1.2.3"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: set_version.py <version|tag>")
    version = sys.argv[1].strip().lstrip('vV')
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        sys.exit(f"invalid version: {version!r} (expected X.Y.Z)")
    path = os.path.join(ROOT, 'app_info.py')
    src = open(path, encoding='utf-8').read()
    src, n = re.subn(r'^VERSION = ".*"$', f'VERSION = "{version}"', src, flags=re.M)
    if n != 1:
        sys.exit("VERSION line not found in app_info.py")
    open(path, 'w', encoding='utf-8').write(src)
    print(version)


if __name__ == '__main__':
    main()
