"""GitHub Releases update checks for the installed application."""

import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

from config.version import APP_VERSION, GITHUB_RELEASES_API, GITHUB_RELEASE_PAGE


class UpdateManager:
    def __init__(self, current_version: str = APP_VERSION):
        self.current_version = current_version

    def latest_release(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        request = urllib.request.Request(
            GITHUB_RELEASES_API,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "NeuralEyeTracker"},
        )
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                release = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError):
            return None, None, None

        tag = str(release.get("tag_name", "")).lstrip("v")
        page = release.get("html_url") or GITHUB_RELEASE_PAGE
        setup_url = next(
            (
                asset.get("browser_download_url")
                for asset in release.get("assets", [])
                if str(asset.get("name", "")).lower().endswith(".exe")
                and "setup" in str(asset.get("name", "")).lower()
            ),
            None,
        )
        return tag or None, setup_url, page

    def check(self) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        latest, setup_url, page = self.latest_release()
        if latest is None:
            return False, None, None, None
        return self._version_key(latest) > self._version_key(self.current_version), latest, setup_url, page

    def download_and_launch(self, setup_url: str) -> Path:
        filename = Path(setup_url.split("?", 1)[0]).name or "NeuralEyeTracker-Setup.exe"
        target = Path(tempfile.gettempdir()) / filename
        request = urllib.request.Request(
            setup_url,
            headers={"User-Agent": "NeuralEyeTracker"},
        )
        with urllib.request.urlopen(request, timeout=30) as response, target.open("wb") as output:
            output.write(response.read())
        subprocess.Popen([str(target)], close_fds=True)
        return target

    @staticmethod
    def _version_key(version: str) -> tuple:
        numbers = []
        for part in version.split("."):
            digits = "".join(character for character in part if character.isdigit())
            numbers.append(int(digits or 0))
        return tuple((numbers + [0, 0, 0])[:3])
