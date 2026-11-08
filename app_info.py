"""Central app metadata. VERSION is rewritten by tools/set_version.py during release builds."""

APP_NAME = "ypriteConvert"
APP_ID = "ypriteConvert.App"          # Windows AppUserModelID (taskbar grouping/icon)
VERSION = "1.1.0"
PUBLISHER = "theStxve"
GITHUB_REPO = "theStxve/ypriteConv"
GITHUB_URL = f"https://github.com/{GITHUB_REPO}"


def version_tuple(v: str):
    """'v1.2.3' / '1.2' -> (1, 2, 3) / (1, 2, 0). Non-numeric parts count as 0."""
    parts = v.strip().lstrip('vV').split('-')[0].split('.')
    nums = []
    for p in parts[:3]:
        digits = ''.join(ch for ch in p if ch.isdigit())
        nums.append(int(digits) if digits else 0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)
