"""Safe release checks for HuMidi: Xingkong Edition.

The updater only checks this fork's GitHub Releases page. It never downloads
or replaces the running executable automatically.
"""

import json
import re
import sys
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal


REPOSITORY = "Xingkong3027/HuMidi-Xingkong-Edition"
RELEASES_API = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
_VERSION_PATTERN = re.compile(
    r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:-xk\.(?P<edition>\d+))?$",
    re.IGNORECASE,
)


def parse_version(tag: str) -> tuple[int, int, int, int, int]:
    """Return a comparable tuple for stable and ``-xk.N`` tags."""
    if not isinstance(tag, str):
        return ()
    match = _VERSION_PATTERN.fullmatch(tag.strip())
    if match is None:
        return ()
    edition = match.group("edition")
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        1 if edition is None else 0,
        0 if edition is None else int(edition),
    )


class UpdateChecker(QThread):
    update_available = pyqtSignal(str, str)  # (latest_tag, releases_url)
    no_update = pyqtSignal()
    check_failed = pyqtSignal()

    def __init__(self, current_version: str, force: bool = False):
        super().__init__()
        self._current_version = current_version
        self._force = force

    def run(self):
        if not self._force and not getattr(sys, "frozen", False):
            return
        try:
            request = urllib.request.Request(
                RELEASES_API,
                headers={
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "HuMidi-Xingkong-Edition-updater",
                },
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                data = json.loads(response.read().decode("utf-8"))

            latest_tag = str(data.get("tag_name", ""))
            latest_version = parse_version(latest_tag)
            current_version = parse_version(self._current_version)
            if not latest_version or not current_version:
                self.check_failed.emit()
                return
            if latest_version <= current_version:
                self.no_update.emit()
                return
            self.update_available.emit(latest_tag, RELEASES_URL)
        except Exception:
            self.check_failed.emit()
